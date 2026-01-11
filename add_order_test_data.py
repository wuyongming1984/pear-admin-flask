import sys
import argparse
from datetime import date, datetime
from decimal import Decimal

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import OrderORM, SupplierORM

app = create_app()

# 解决 UnicodeEncodeError
sys.stdout.reconfigure(encoding='utf-8')

# 测试数据
test_orders = [
    {
        "order_number": "D20240101001",
        "material_name": "钢筋HRB400",
        "project_name": "智慧城市建设项目",
        "contact_phone": "13800138001",
        "cutting_time": date(2024, 1, 15),
        "estimated_arrival_time": date(2024, 1, 25),
        "material_details": "HRB400级钢筋，直径12mm，数量500吨",
        "order_amount": Decimal("2500000.00"),
        "material_manager": "张三",
        "sub_project_manager": "李四"
    },
    {
        "order_number": "D20240102002",
        "material_name": "混凝土C30",
        "project_name": "办公楼装修工程",
        "contact_phone": "13800138002",
        "cutting_time": date(2024, 3, 20),
        "estimated_arrival_time": date(2024, 3, 30),
        "material_details": "C30商品混凝土，数量1000立方米",
        "order_amount": Decimal("450000.00"),
        "material_manager": "王五",
        "sub_project_manager": "赵六"
    },
    {
        "order_number": "D20240103003",
        "material_name": "水泥P.O42.5",
        "project_name": "道路改造项目",
        "contact_phone": "13800138003",
        "cutting_time": date(2023, 6, 10),
        "estimated_arrival_time": date(2023, 6, 20),
        "material_details": "普通硅酸盐水泥P.O42.5，数量2000吨",
        "order_amount": Decimal("800000.00"),
        "material_manager": "孙七",
        "sub_project_manager": "周八"
    },
    {
        "order_number": "D20240104004",
        "material_name": "钢材Q235",
        "project_name": "IT系统升级",
        "contact_phone": "13800138004",
        "cutting_time": date(2024, 2, 5),
        "estimated_arrival_time": date(2024, 2, 15),
        "material_details": "Q235钢材，规格多样，数量300吨",
        "order_amount": Decimal("1500000.00"),
        "material_manager": "吴九",
        "sub_project_manager": "郑十"
    },
    {
        "order_number": "D20240105005",
        "material_name": "砂石料",
        "project_name": "环保设备采购",
        "contact_phone": "13800138005",
        "cutting_time": date(2024, 4, 1),
        "estimated_arrival_time": date(2024, 4, 10),
        "material_details": "中粗砂、碎石，各5000立方米",
        "order_amount": Decimal("600000.00"),
        "material_manager": "张三",
        "sub_project_manager": "李四"
    },
    {
        "order_number": "D20240106006",
        "material_name": "防水材料",
        "project_name": "办公楼装修工程",
        "contact_phone": "13800138006",
        "cutting_time": date(2024, 3, 25),
        "estimated_arrival_time": date(2024, 4, 5),
        "material_details": "SBS防水卷材，厚度4mm，面积5000平方米",
        "order_amount": Decimal("250000.00"),
        "material_manager": "王五",
        "sub_project_manager": "赵六"
    },
    {
        "order_number": "D20240107007",
        "material_name": "保温材料",
        "project_name": "智慧城市建设项目",
        "contact_phone": "13800138007",
        "cutting_time": date(2024, 2, 1),
        "estimated_arrival_time": date(2024, 2, 10),
        "material_details": "聚苯乙烯泡沫板，厚度50mm，数量1000平方米",
        "order_amount": Decimal("180000.00"),
        "material_manager": "孙七",
        "sub_project_manager": "周八"
    },
    {
        "order_number": "D20240108008",
        "material_name": "电线电缆",
        "project_name": "IT系统升级",
        "contact_phone": "13800138008",
        "cutting_time": date(2024, 2, 10),
        "estimated_arrival_time": date(2024, 2, 20),
        "material_details": "BV线、YJV电缆，各种规格，总长度50000米",
        "order_amount": Decimal("320000.00"),
        "material_manager": "吴九",
        "sub_project_manager": "郑十"
    },
    {
        "order_number": "D20240109009",
        "material_name": "管道材料",
        "project_name": "道路改造项目",
        "contact_phone": "13800138009",
        "cutting_time": date(2023, 7, 1),
        "estimated_arrival_time": date(2023, 7, 10),
        "material_details": "HDPE给水管、PVC排水管，各种规格",
        "order_amount": Decimal("480000.00"),
        "material_manager": "张三",
        "sub_project_manager": "李四"
    },
    {
        "order_number": "D20240110010",
        "material_name": "门窗材料",
        "project_name": "办公楼装修工程",
        "contact_phone": "13800138010",
        "cutting_time": date(2024, 4, 1),
        "estimated_arrival_time": date(2024, 4, 15),
        "material_details": "铝合金门窗、塑钢门窗，数量200套",
        "order_amount": Decimal("560000.00"),
        "material_manager": "王五",
        "sub_project_manager": "赵六"
    },
    {
        "order_number": "D20240111011",
        "material_name": "瓷砖",
        "project_name": "办公楼装修工程",
        "contact_phone": "13800138011",
        "cutting_time": date(2024, 4, 5),
        "estimated_arrival_time": date(2024, 4, 18),
        "material_details": "800x800mm地砖、300x600mm墙砖，数量各5000片",
        "order_amount": Decimal("420000.00"),
        "material_manager": "孙七",
        "sub_project_manager": "周八"
    },
    {
        "order_number": "D20240112012",
        "material_name": "涂料",
        "project_name": "智慧城市建设项目",
        "contact_phone": "13800138012",
        "cutting_time": date(2024, 2, 15),
        "estimated_arrival_time": date(2024, 2, 25),
        "material_details": "内墙乳胶漆、外墙真石漆，数量各5000升",
        "order_amount": Decimal("280000.00"),
        "material_manager": "吴九",
        "sub_project_manager": "郑十"
    },
    {
        "order_number": "D20240113013",
        "material_name": "石材",
        "project_name": "道路改造项目",
        "contact_phone": "13800138013",
        "cutting_time": date(2023, 8, 1),
        "estimated_arrival_time": date(2023, 8, 15),
        "material_details": "花岗岩、大理石，数量各1000平方米",
        "order_amount": Decimal("1200000.00"),
        "material_manager": "张三",
        "sub_project_manager": "李四"
    },
    {
        "order_number": "D20240114014",
        "material_name": "玻璃",
        "project_name": "办公楼装修工程",
        "contact_phone": "13800138014",
        "cutting_time": date(2024, 4, 10),
        "estimated_arrival_time": date(2024, 4, 22),
        "material_details": "钢化玻璃、中空玻璃，数量各500平方米",
        "order_amount": Decimal("350000.00"),
        "material_manager": "王五",
        "sub_project_manager": "赵六"
    },
    {
        "order_number": "D20240115015",
        "material_name": "五金配件",
        "project_name": "IT系统升级",
        "contact_phone": "13800138015",
        "cutting_time": date(2024, 2, 20),
        "estimated_arrival_time": date(2024, 3, 1),
        "material_details": "螺丝、螺栓、合页等五金配件，数量5000套",
        "order_amount": Decimal("150000.00"),
        "material_manager": "孙七",
        "sub_project_manager": "周八"
    }
]

def add_test_data(force=False):
    with app.app_context():
        if force:
            print("强制模式：正在清空现有订单数据...")
            try:
                num_deleted = db.session.query(OrderORM).delete()
                db.session.commit()
                print(f"已清空 {num_deleted} 条现有订单数据。")
            except Exception as e:
                db.session.rollback()
                print(f"清空数据失败: {e}")
                return

        try:
            # 检查是否已有数据
            if OrderORM.query.count() > 0 and not force:
                print("数据库中已有订单数据，跳过添加。如需强制添加，请使用 --force 参数。")
                return

            # 获取供应商列表，随机分配给订单
            suppliers = SupplierORM.query.all()
            supplier_ids = [s.id for s in suppliers] if suppliers else [None]
            
            # 如果没有供应商，使用 None
            if not supplier_ids:
                supplier_ids = [None]

            for i, order_data in enumerate(test_orders):
                # 随机分配供应商（如果有的话）
                if supplier_ids and supplier_ids[0] is not None:
                    order_data["supplier_id"] = supplier_ids[i % len(supplier_ids)]
                else:
                    order_data["supplier_id"] = None
                
                order = OrderORM(**order_data)
                db.session.add(order)

            db.session.commit()
            print(f"成功添加 {len(test_orders)} 条订单测试数据！")

            # 统计信息
            total_amount = db.session.query(db.func.sum(OrderORM.order_amount)).scalar()
            print(f"\n订单总金额: {total_amount:,.2f} 元")
            
            # 按项目统计
            project_stats = db.session.query(
                OrderORM.project_name,
                db.func.count(OrderORM.id).label('count'),
                db.func.sum(OrderORM.order_amount).label('total')
            ).group_by(OrderORM.project_name).all()
            
            print("\n按项目统计：")
            for project_name, count, total in project_stats:
                print(f"  {project_name or '未指定'}: {count} 条订单, 总金额 {total:,.2f} 元")

        except Exception as e:
            db.session.rollback()
            print(f"添加数据失败: {e}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add test data to ums_order table.")
    parser.add_argument("--force", action="store_true", help="Force add data, clearing existing data first.")
    args = parser.parse_args()

    add_test_data(force=args.force)

