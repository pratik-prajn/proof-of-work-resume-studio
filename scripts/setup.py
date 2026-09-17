"""Standard-library-only secret generation. Never prints secret values."""
from pathlib import Path
import argparse
import base64
import os
import secrets

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--force', action='store_true', help='Replace local config. This invalidates sessions and changes the history key.')
args = parser.parse_args()
root_env, web_env = ROOT / '.env', ROOT / 'apps/web/.env.local'
if (root_env.exists() or web_env.exists()) and not args.force:
    raise SystemExit('Configuration exists. Edit it directly, or use --force only before storing real history. Back up encryption keys.')
values = {
    'APP_ENV':'development', 'APP_ORIGIN':'http://localhost:3000', 'API_BASE_URL':'http://127.0.0.1:8000',
    'INTERNAL_API_KEY':secrets.token_urlsafe(48), 'API_TOKEN_SECRET':secrets.token_urlsafe(48),
    'AUTH_SECRET':secrets.token_urlsafe(48), 'AUTH_URL':'http://localhost:3000', 'AUTH_TRUST_HOST':'true',
    'AUTH_GITHUB_ID':'', 'AUTH_GITHUB_SECRET':'', 'PDF_ENGINE':'typst', 'ENABLE_HISTORY':'false',
    'DATABASE_URL':'sqlite:///./studio.db', 'HISTORY_ENCRYPTION_KEY':base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
    'POSTGRES_PASSWORD':secrets.token_urlsafe(24), 'ENABLE_GITHUB_INSPECTOR':'false',
    'LLM_BASE_URL':'', 'LLM_API_KEY':'', 'LLM_MODEL':'',
}
web_keys = {'APP_ORIGIN','API_BASE_URL','INTERNAL_API_KEY','API_TOKEN_SECRET','AUTH_SECRET','AUTH_URL','AUTH_TRUST_HOST','AUTH_GITHUB_ID','AUTH_GITHUB_SECRET'}
for destination, keys in [(root_env, values.keys()), (web_env, [k for k in values if k in web_keys])]:
    destination.write_text(''.join(f'{k}={values[k]}\n' for k in keys))
    try: os.chmod(destination, 0o600)
    except OSError: pass
print('Created .env and apps/web/.env.local with independent random secrets.')
print('Guest mode is enabled. No model provider, GitHub inspector or saved history is enabled.')
print('Next: docker compose up --build, then open http://localhost:3000.')
