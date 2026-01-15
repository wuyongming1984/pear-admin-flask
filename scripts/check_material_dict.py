import sys
import os
sys.path.append(os.getcwd())

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import DictionaryORM, DictionaryDetailORM

app = create_app()

with app.app_context():
    print("查询字典类型...")
    try:
        # 查询所有字典类型
        dictionaries = DictionaryORM.query.all()
        for dic in dictionaries:
            print(f"  - {dic.code}: {dic.name} (ID: {dic.id})")
        
        print(f"\n找到 {len(dictionaries)} 个字典类型")
        
        # 查找材料相关的字典
        print("\n查找材料名称相关的字典...")
        material_dict = DictionaryORM.query.filter(
            db.or_(
                DictionaryORM.name.like('%材料%'),
                DictionaryORM.code.like('%cl%')
            )
        ).all()
        
        if material_dict:
            print(f"找到 {len(material_dict)} 个相关字典:")
            for dic in material_dict:
                print(f"\n  字典: {dic.name} (code: {dic.code})")
                details = DictionaryDetailORM.query.filter_by(dic_id=dic.id).all()
                print(f"  明细数量: {len(details)}")
                for detail in details[:5]:  # 只显示前5个
                    print(f"    - {detail.code}: {detail.value}")
        else:
            print("未找到材料相关的字典")
            print("\n建议创建材料名称字典...")
            
    except Exception as e:
        print(f"查询失败: {e}")
        import traceback
        traceback.print_exc()
