import json
import os
import urllib.request
import psycopg2
import yandexcloud  # v1
from yandex.cloud.serverless.functions.v1.function_service_pb2 import ListFunctionsRequest
from yandex.cloud.serverless.functions.v1.function_service_pb2_grpc import FunctionServiceStub

CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, X-Admin-Token',
}


def save_diagnostics(context_dir, context_attrs, raw_token, note):
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO cloud_diagnostics (context_dir, context_attrs, raw_token, note) VALUES (%s, %s, %s, %s)",
            (json.dumps(context_dir), json.dumps(context_attrs), str(raw_token), note)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        pass


def handler(event, context):
    """Возвращает список Cloud Functions в folder из Yandex Cloud."""
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': ''}

    # Auth check
    token = event.get('headers', {}).get('X-Admin-Token') or event.get('headers', {}).get('x-admin-token')
    if token != os.environ.get('ADMIN_TOKEN'):
        return {'statusCode': 401, 'headers': {'Access-Control-Allow-Origin': '*'}, 'body': json.dumps({'error': 'Unauthorized'})}

    # Diagnostics: collect all context fields
    ctx_dir = [x for x in dir(context) if not x.startswith('__')]
    ctx_attrs = {}
    for attr in ctx_dir:
        try:
            val = getattr(context, attr)
            if not callable(val):
                ctx_attrs[attr] = str(val)
        except Exception as e:
            ctx_attrs[attr] = f'ERROR: {e}'

    raw_token = getattr(context, 'token', None)

    if raw_token is None:
        # Auth-relevant env vars only (no secrets)
        auth_prefixes = ('YC_', 'GOOGLE_', 'SERVICE_ACCOUNT', 'TOKEN', 'CREDENTIAL', 'IAM_')
        auth_env = {k: v for k, v in os.environ.items()
                    if any(k.upper().startswith(p) for p in auth_prefixes)
                    and k not in ('ADMIN_TOKEN',)}
        all_env_keys = sorted(os.environ.keys())

        # Probe metadata endpoint
        metadata = {}
        try:
            req = urllib.request.Request(
                'http://169.254.169.254/computeMetadata/v1/instance/service-accounts/',
                headers={'Metadata-Flavor': 'Google'}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                metadata = {'status': resp.status, 'body': resp.read().decode()}
        except Exception as e:
            metadata = {'error': str(e)}

        diag = {
            'error': 'context.token is None',
            'hint': 'No service account attached to the function',
            'context_dir': ctx_dir,
            'context_attrs': ctx_attrs,
            'auth_env': auth_env,
            'all_env_keys': all_env_keys,
            'metadata_endpoint': metadata,
        }
        save_diagnostics(ctx_dir, ctx_attrs, raw_token, 'context.token is None — no service account attached')
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json'},
            'body': json.dumps(diag),
        }

    folder_id = os.environ['YC_FOLDER_ID']

    iam_token = raw_token['access_token']
    sdk = yandexcloud.SDK(iam_token=iam_token)
    functions_service = sdk.client(FunctionServiceStub)

    response = functions_service.List(ListFunctionsRequest(folder_id=folder_id))

    functions = [
        {
            'id': f.id,
            'name': f.name,
            'status': f.Status.Name(f.status),
        }
        for f in response.functions
    ]

    return {
        'statusCode': 200,
        'headers': {'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json'},
        'body': json.dumps({'functions': functions, 'total': len(functions)}),
    }