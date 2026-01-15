
import sqlite3
import sys
import os

DB_FILE = r'd:\pear_admin\pear-admin-flask\instance\pear_admin.db'

def add_column():
    print(f"Adding column supplier_contact_person to ums_order in {DB_FILE}...")
    
    if not os.path.exists(DB_FILE):
        print(f"Database file not found: {DB_FILE}")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(ums_order)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'supplier_contact_person' in columns:
             print("Column 'supplier_contact_person' already exists.")
        else:
            try:
                cursor.execute("ALTER TABLE ums_order ADD COLUMN supplier_contact_person VARCHAR(64)")
                conn.commit()
                print("Successfully added column 'supplier_contact_person'.")
            except Exception as e:
                print(f"Error adding column: {e}")
                
    except Exception as e:
        print(f"Error checking table info: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    add_column()
