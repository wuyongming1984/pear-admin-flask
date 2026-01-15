import sys
import os
sys.path.append(os.getcwd())

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import OrderORM, DictionaryDetailORM

app = create_app()

with app.app_context():
    print("检查订单数据中的材料名称...")
    try:
        # 查询前5个订单
        orders = OrderORM.query.limit(5).all()
        
        if orders:
            print(f"\n找到 {len(orders)} 个订单样本:")
            for order in orders:
                print(f"\n订单ID: {order.id}")
                print(f"  订单编号: {order.order_number}")
                print(f"  材料名称(当前): {order.material_name}")
                print(f"  材料名称类型: {type(order.material_name)}")
                
                # 尝试查找对应的字典明细
                if order.material_name and order.material_name.isdigit():
                    detail = DictionaryDetailORM.query.get(int(order.material_name))
                    if detail:
                        print(f"  → 对应的字典值: {detail.value} (code: {detail.code})")
                    else:
                        print(f"  → 未找到ID={order.material_name}的字典明细")
        else:
            print("没有找到订单数据")
            
    except Exception as e:
        print(f"查询失败: {e}")
        import traceback
        traceback.print_exc()
