import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from pear_admin.extensions import db
from pear_admin import create_app
from pear_admin.orms import MaterialOutboundORM, MaterialInventoryORM
from sqlalchemy import text

def debug_data():
    app = create_app()
    with app.app_context():
        print("Checking material_outbound schema...")
        columns_info = db.session.execute(text("PRAGMA table_info(material_outbound)")).fetchall()
        for info in columns_info:
            print(f"Col: {info[1]}, Type: {info[2]}")
            
        print("\nChecking last 5 material_outbound records:")
        records = MaterialOutboundORM.query.order_by(MaterialOutboundORM.id.desc()).limit(5).all()
        for r in records:
            inv = r.inventory
            print(f"ID: {r.id}, Name: {r.material_name}, Tax Rate: {r.tax_rate}, Inv Tax Rate: {inv.tax_rate if inv else 'N/A'}")

if __name__ == "__main__":
    debug_data()
