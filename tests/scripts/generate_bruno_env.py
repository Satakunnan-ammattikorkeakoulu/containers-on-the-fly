"""
Generate a Bruno environment file from test credentials.

Reads tests/.test_credentials.json and writes tests/api/environments/test.bru
so that `bru run --env test` uses the temporary test accounts.

Usage:
    cd webapp/backend && python ../../tests/scripts/generate_bruno_env.py
"""

import os
import json

CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), '..', '.test_credentials.json')
BRUNO_ENV_FILE = os.path.join(os.path.dirname(__file__), '..', 'api', 'environments', 'test.bru')

def generate():
    if not os.path.exists(CREDENTIALS_FILE):
        print("No credentials file found. Run setup_test_users.py first.")
        raise SystemExit(1)

    with open(CREDENTIALS_FILE, "r") as f:
        creds = json.load(f)

    content = f"""vars {{
  root_url: http://localhost:8000/api
  admin_email: {creds['admin_email']}
  admin_password: {creds['admin_password']}
  user_email: {creds['user_email']}
  user_password: {creds['user_password']}
  auth_token:
  admin_token:
  user_token:
}}
"""

    with open(BRUNO_ENV_FILE, "w") as f:
        f.write(content)

    print(f"Generated Bruno test environment: {os.path.abspath(BRUNO_ENV_FILE)}")

if __name__ == "__main__":
    generate()
