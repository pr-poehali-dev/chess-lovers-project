import os
import json
import subprocess


def handler(event, context):
    """Проверяет доступные инструменты в Cloud Functions runtime."""
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': ''
        }

    checks = {}
    for cmd in ['java -version', 'node -v', 'python3 --version', 'psql --version']:
        name = cmd.split()[0]
        try:
            out = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=5)
            checks[name] = (out.stdout + out.stderr).strip().split('\n')[0]
        except Exception as e:
            checks[name] = f'not found ({type(e).__name__})'

    checks['cwd'] = os.getcwd()
    checks['uid'] = os.getuid()
    checks['env_keys'] = list(os.environ.keys())

    return {
        'statusCode': 200,
        'headers': {'Access-Control-Allow-Origin': '*'},
        'body': json.dumps(checks, ensure_ascii=False)
    }
