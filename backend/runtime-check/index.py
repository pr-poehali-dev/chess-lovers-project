import os, json, subprocess

def handler(event, context):
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': {'Access-Control-Allow-Origin': '*'}, 'body': ''}
    
    checks = {}
    for cmd in ['java -version', 'node -v', 'python3 --version', 'psql --version']:
        name = cmd.split()[0]
        try:
            out = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=5)
            checks[name] = (out.stdout + out.stderr).strip().split('\n')[0]
        except:
            checks[name] = 'not found'
    
    checks['cwd'] = os.getcwd()
    checks['uid'] = os.getuid()
    
    return {
        'statusCode': 200,
        'headers': {'Access-Control-Allow-Origin': '*'},
        'body': json.dumps(checks)
    }
