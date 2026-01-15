import sys
import os
sys.path.append(os.getcwd())

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import DictionaryORM, DictionaryDetailORM

app = create_app()

with app.app_context():
    print("查询付款状态字典...")
    try:
        # 查找付款状态字典
        payment_status_dict = DictionaryORM.query.filter_by(code='fkzt').first()
        
        if payment_status_dict:
            print(f"\n找到字典: {payment_status_dict.name} (code: {payment_status_dict.code}, ID: {payment_status_dict.id})")
            
            # 查询所有明细
            details = DictionaryDetailORM.query.filter_by(dic_id=payment_status_dict.id).order_by(DictionaryDetailORM.order_no).all()
            print(f"\n付款状态选项（共 {len(details)} 个）:")
            for detail in details:
                print(f"  - ID: {detail.id}, Code: {detail.code}, Value: {detail.value}, Order: {detail.order_no}")
        else:
            print("❌ 未找到付款状态字典 (code='fkzt')")
            
    except Exception as e:
        print(f"查询失败: {e}")
        import traceback
        traceback.print_exc()
