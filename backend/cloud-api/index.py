import json
import os
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
        save_diagnostics(ctx_dir, ctx_attrs, raw_token, 'context.token is None — no service account attached')
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'context.token is None',
                'hint': 'No service account attached to the function',
                'context_dir': ctx_dir,
                'context_attrs': ctx_attrs,
            }),
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
