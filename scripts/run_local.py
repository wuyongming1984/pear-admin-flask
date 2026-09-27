"""Run the existing SQLite database locally without cloud service credentials."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

if not (ROOT / "instance" / "pear_admin.db").is_file():
    raise SystemExit("Local database instance/pear_admin.db is missing; initialization was not run.")

# Override .env only inside this process; keep production settings untouched.
os.environ["MYSQL_HOST"] = "127.0.0.1"
os.environ["FLASK_DEBUG"] = "0"
for key in (
    "ALIYUN_ACCESS_KEY_ID", "ALIYUN_ACCESS_KEY_SECRET",
    "ALIYUN_OSS_BUCKET_NAME", "ALIYUN_OSS_ENDPOINT",
    "BAIDU_OCR_API_KEY", "BAIDU_OCR_SECRET_KEY",
):
    os.environ[key] = ""

from pear_admin import create_app
from pear_admin.extensions import db, scheduler

app = create_app("dev")
# Local editing must not trigger configured backup emails.
scheduler.shutdown(wait=False)
with app.app_context():
    if db.engine.url.get_backend_name() != "sqlite":
        raise SystemExit("Local runner requires SQLite.")
    print(f"Local database: {db.engine.url.database}", flush=True)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False, use_reloader=True, use_debugger=False)
