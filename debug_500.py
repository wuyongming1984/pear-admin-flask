import sys
import os
sys.path.append(os.getcwd())

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import SysConfigORM

app = create_app('dev')

with app.app_context():
    print("Attempting to query SysConfigORM...")
    try:
        res = db.session.execute(db.select(SysConfigORM)).scalars().all()
        print(f"Query successful. Found {len(res)} records.")
    except Exception as e:
        print(f"Query FAILED: {e}")
        import traceback
        traceback.print_exc()

    print("\nAttempting to render template...")
    try:
        from flask import render_template
        render_template("system/backup/index.html")
        print("Template render successful.")
    except Exception as e:
        # Template rendering might fail without request context, but finding it should work
        print(f"Template render check (might fail due to context): {e}")
