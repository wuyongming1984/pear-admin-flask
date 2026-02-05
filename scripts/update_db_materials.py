import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import MaterialPlanningORM, MaterialInboundORM, MaterialInventoryORM, MaterialOutboundORM, MaterialInvoiceORM

app = create_app('dev')

with app.app_context():
    print("Creating database tables for Material Control module...")
    db.create_all()
    print("Tables created successfully.")
