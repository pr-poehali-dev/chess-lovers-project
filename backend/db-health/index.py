import json, os, subprocess, psycopg2

def handler(event, context):
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type'}, 'body': ''}

    result = {}

    # 1. Database health
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        cur = conn.cursor()
        cur.execute('SELECT version(), current_database(), current_user')
        row = cur.fetchone()
        result['db_version'] = row[0]
        result['db_name'] = row[1]
        result['db_user'] = row[2]
        cur.close()
        conn.close()
        result['db_status'] = 'ok'
    except Exception as e:
        result['db_status'] = str(type(e).__name__)

    # 2. Runtime checks for build pipeline
    for cmd in ['java -version', 'node -v', 'python3 --version', 'psql --version']:
        name = cmd.split()[0]
        try:
            out = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=5)
            result[name] = (out.stdout + out.stderr).strip().split('\n')[0]
        except:
            result[name] = 'not found'

    return {'statusCode': 200, 'headers': {'Access-Control-Allow-Origin': '*'}, 'body': json.dumps(result)}
