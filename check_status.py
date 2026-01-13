import sys
import os
sys.path.append(os.getcwd())

from pear_admin import create_app
from pear_admin.extensions import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    rows = db.session.execute(text("SELECT DISTINCT payment_status FROM ums_pay")).fetchall()
    print("Distinct payment_status values:", [r[0] for r in rows])
