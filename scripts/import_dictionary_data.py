import os
import re
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms.dictionary import DictionaryORM, DictionaryDetailORM

app = create_app("dev")

SQL_FILE_PATH = r"d:\pear_admin\pear-admin-flask\旧数据库sf_db_prod.sql"

def parse_and_import():
    with app.app_context():
        # Create tables if not exist
        db.create_all()
        
        # Clear existing data to avoid duplicates (Optional, or just skip existing)
        # DictionaryDetailORM.query.delete()
        # DictionaryORM.query.delete()
        # db.session.commit()

        print(f"Reading SQL file: {SQL_FILE_PATH}")
        with open(SQL_FILE_PATH, 'r', encoding='utf-8') as f:
            content = f.read()

        # Regex for base_dic INSERTs
        # INSERT INTO `base_dic` VALUES ('25', 'gyslx', '供应商类型', 'Y', null, null, null, null);
        dic_pattern = re.compile(r"INSERT INTO `base_dic` VALUES \('(\d+)', '([^']*)', '([^']*)', '([^']*)',.*?\);")
        
        dic_matches = dic_pattern.findall(content)
        print(f"Found {len(dic_matches)} dictionary types.")

        for m in dic_matches:
            id_val, code, name, valid = m
            # Check if exists
            if not DictionaryORM.query.get(int(id_val)):
                dic = DictionaryORM(
                    id=int(id_val),
                    code=code,
                    name=name,
                    valid_mark=valid
                )
                db.session.add(dic)
        
        db.session.commit()
        print("Dictionary types imported.")


        # Regex for base_dic_detail INSERTs
        # INSERT INTO `base_dic_detail` VALUES ('106', '25', '1', '单位', '1', 'Y', null, null, null, null);
        # Note: value might contain spaces or other chars, so use [^']* is risky if value has escaped quotes.
        # But looking at the file content shown previously, values seem simple.
        # Let's try a bit more robust regex.
        detail_pattern = re.compile(r"INSERT INTO `base_dic_detail` VALUES \('(\d+)', '(\d+)', '([^']*)', '([^']*)', '(\d+)', '([^']*)',.*?\);")

        detail_matches = detail_pattern.findall(content)
        print(f"Found {len(detail_matches)} dictionary details.")

        for m in detail_matches:
            id_val, dic_id, code, value, order, valid = m
            
            if not DictionaryDetailORM.query.get(int(id_val)):
                detail = DictionaryDetailORM(
                    id=int(id_val),
                    dic_id=int(dic_id),
                    code=code,
                    value=value,
                    order_no=int(order),
                    valid_mark=valid
                )
                db.session.add(detail)
        
        db.session.commit()
        print("Dictionary details imported.")

if __name__ == '__main__':
    parse_and_import()
