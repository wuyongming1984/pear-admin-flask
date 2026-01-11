import sys
import argparse
from datetime import datetime
from decimal import Decimal

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import PayORM, OrderORM, SupplierORM

app = create_app()

# 解决 UnicodeEncodeError
sys.stdout.reconfigure(encoding='utf-8')

# 付款用途模板
payment_purposes = [
    "材料款首付款",
    "材料款进度款",
    "材料款尾款",
    "设备采购款",
    "工程进度款",
    "质保金",
    "预付款",
    "材料款结算",
    "设备款结算",
    "工程款结算"
]

# 付款状态
payment_statuses = ["pending", "partial", "paid"]

# 经办人列表
handlers = ["张三", "李四", "王五", "赵六", "孙七", "周八", "吴九", "郑十"]

def add_test_data(force=False):
    with app.app_context():
        if force:
            print("强制模式：正在清空现有付款单数据...")
            try:
                num_deleted = db.session.query(PayORM).delete()
                db.session.commit()
                print(f"已清空 {num_deleted} 条现有付款单数据。")
            except Exception as e:
                db.session.rollback()
                print(f"清空数据失败: {e}")
                return

        try:
            # 检查是否已有数据
            if PayORM.query.count() > 0 and not force:
                print("数据库中已有付款单数据，跳过添加。如需强制添加，请使用 --force 参数。")
                return

            # 获取订单列表
            orders = OrderORM.query.all()
            if not orders:
                print("错误：数据库中没有订单数据，请先添加订单数据。")
                return

            # 获取供应商列表
            suppliers = SupplierORM.query.all()
            if not suppliers:
                print("错误：数据库中没有供应商数据，请先添加供应商数据。")
                return

            supplier_ids = [s.id for s in suppliers]
            
            # 生成付款单数据
            pay_records = []
            pay_number_counter = 1
            
            # 为每个订单创建1-3个付款单
            for order in orders:
                # 随机决定为这个订单创建几个付款单（1-3个）
                import random
                num_pays = random.randint(1, 3)
                
                # 获取订单金额
                order_amount = float(order.order_amount) if order.order_amount else 0
                
                # 为每个付款单分配金额
                remaining_amount = order_amount
                
                for i in range(num_pays):
                    # 生成付款单编号
                    pay_number = f"P{datetime.now().strftime('%Y%m%d')}{str(pay_number_counter).zfill(4)}"
                    pay_number_counter += 1
                    
                    # 如果是最后一个付款单，使用剩余金额
                    if i == num_pays - 1:
                        current_amount = remaining_amount
                    else:
                        # 随机分配金额（不超过剩余金额的70%）
                        max_amount = remaining_amount * 0.7
                        current_amount = random.uniform(order_amount * 0.1, max_amount)
                        remaining_amount -= current_amount
                    
                    # 开票金额通常是付款金额的1.0-1.1倍（含税）
                    invoice_amount = current_amount * random.uniform(1.0, 1.1)
                    
                    # 随机选择付款单位和收款单位（不能相同）
                    payer_id = random.choice(supplier_ids)
                    payee_id = random.choice([sid for sid in supplier_ids if sid != payer_id])
                    
                    # 随机选择付款状态
                    payment_status = random.choice(payment_statuses)
                    
                    # 随机选择付款用途
                    payment_purpose = random.choice(payment_purposes)
                    
                    # 随机选择经办人
                    handler = random.choice(handlers)
                    
                    pay_record = {
                        "pay_number": pay_number,
                        "order_id": order.id,
                        "payer_supplier_id": payer_id,
                        "payee_supplier_id": payee_id,
                        "payment_purpose": f"{payment_purpose} - {order.order_number}",
                        "current_payment_amount": Decimal(str(round(current_amount, 2))),
                        "invoice_amount": Decimal(str(round(invoice_amount, 2))),
                        "payment_status": payment_status,
                        "handler": handler,
                        "create_at": datetime.now()
                    }
                    
                    pay_records.append(pay_record)

            # 批量插入数据
            for pay_data in pay_records:
                pay = PayORM(**pay_data)
                db.session.add(pay)

            db.session.commit()
            print(f"成功添加 {len(pay_records)} 条付款单测试数据！")

            # 统计信息
            total_payment = db.session.query(db.func.sum(PayORM.current_payment_amount)).scalar()
            total_invoice = db.session.query(db.func.sum(PayORM.invoice_amount)).scalar()
            
            print(f"\n付款总金额: {total_payment:,.2f} 元")
            print(f"开票总金额: {total_invoice:,.2f} 元")
            
            # 按付款状态统计
            status_stats = db.session.query(
                PayORM.payment_status,
                db.func.count(PayORM.id).label('count'),
                db.func.sum(PayORM.current_payment_amount).label('total')
            ).group_by(PayORM.payment_status).all()
            
            print("\n按付款状态统计：")
            status_map = {
                "pending": "待付款",
                "partial": "部分付款",
                "paid": "已付款"
            }
            for status, count, total in status_stats:
                status_name = status_map.get(status, status)
                print(f"  {status_name}: {count} 条, 总金额 {total:,.2f} 元")
            
            # 按订单统计
            order_stats = db.session.query(
                PayORM.order_id,
                db.func.count(PayORM.id).label('pay_count'),
                db.func.sum(PayORM.current_payment_amount).label('total')
            ).group_by(PayORM.order_id).all()
            
            print("\n按订单统计（前10条）：")
            for order_id, pay_count, total in order_stats[:10]:
                order = db.session.get(OrderORM, order_id)
                order_num = order.order_number if order else f"订单ID:{order_id}"
                print(f"  {order_num}: {pay_count} 个付款单, 总金额 {total:,.2f} 元")

        except Exception as e:
            db.session.rollback()
            print(f"添加数据失败: {e}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add test data to ums_pay table.")
    parser.add_argument("--force", action="store_true", help="Force add data, clearing existing data first.")
    args = parser.parse_args()

    add_test_data(force=args.force)
