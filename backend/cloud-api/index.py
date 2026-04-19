import json
import os
import yandexcloud  # v1
from yandex.cloud.serverless.functions.v1.function_service_pb2 import ListFunctionsRequest
from yandex.cloud.serverless.functions.v1.function_service_pb2_grpc import FunctionServiceStub

CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, X-Admin-Token',
}


def handler(event, context):
    """Возвращает список Cloud Functions в folder из Yandex Cloud."""
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': ''}

    # Auth check
    token = event.get('headers', {}).get('X-Admin-Token') or event.get('headers', {}).get('x-admin-token')
    if token != os.environ.get('ADMIN_TOKEN'):
        return {'statusCode': 401, 'headers': {'Access-Control-Allow-Origin': '*'}, 'body': json.dumps({'error': 'Unauthorized'})}

    folder_id = os.environ['YC_FOLDER_ID']

    iam_token = context.token['access_token']
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