import sqlite3
import os

def migrate_data():
    db_path = r"d:\pear_admin\pear-admin-flask\instance\pear_admin.db"
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all outbound records that need syncing
    # We sync if any of the snapshot fields are NULL
    cursor.execute("""
        SELECT mo.id, mi.project_id, mi.material_unit, mi.material_spec
        FROM material_outbound mo
        JOIN material_inventory mi ON mo.inventory_id = mi.id
        WHERE mo.project_id IS NULL OR mo.material_unit IS NULL OR mo.material_spec IS NULL
    """)
    records = cursor.fetchall()
    print(f"Found {len(records)} records to sync.")

    updated_count = 0
    for mo_id, p_id, m_unit, m_spec in records:
        cursor.execute("""
            UPDATE material_outbound
            SET project_id = ?, material_unit = ?, material_spec = ?
            WHERE id = ?
        """, (p_id, m_unit, m_spec, mo_id))
        updated_count += 1

    conn.commit()
    conn.close()
    print(f"Data migration completed. Updated {updated_count} records.")

if __name__ == "__main__":
    migrate_data()
