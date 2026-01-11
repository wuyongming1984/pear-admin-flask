from datetime import date
from decimal import Decimal

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import ProjectORM

app = create_app()

# 测试数据
test_projects = [
    {
        "project_name": "智慧城市建设项目",
        "project_full_name": "XX市智慧城市基础设施建设项目",
        "project_scale": "大型",
        "start_date": date(2024, 1, 1),
        "end_date": date(2025, 12, 31),
        "project_status": "进行中",
        "project_amount": Decimal("50000000.00"),
        "attachments": "项目合同.pdf,技术方案.docx,预算表.xlsx"
    },
    {
        "project_name": "办公楼装修工程",
        "project_full_name": "XX公司总部办公楼室内装修工程",
        "project_scale": "中型",
        "start_date": date(2024, 3, 15),
        "end_date": date(2024, 8, 30),
        "project_status": "进行中",
        "project_amount": Decimal("3500000.00"),
        "attachments": "装修合同.pdf,设计图纸.dwg"
    },
    {
        "project_name": "道路改造项目",
        "project_full_name": "XX区主干道路面改造及配套设施建设项目",
        "project_scale": "大型",
        "start_date": date(2023, 6, 1),
        "end_date": date(2024, 5, 31),
        "project_status": "已完成",
        "project_amount": Decimal("12000000.00"),
        "attachments": "施工合同.pdf,施工图纸.dwg,验收报告.pdf"
    },
    {
        "project_name": "IT系统升级",
        "project_full_name": "企业信息化管理系统升级改造项目",
        "project_scale": "中型",
        "start_date": date(2024, 2, 1),
        "end_date": date(2024, 6, 30),
        "project_status": "已完成",
        "project_amount": Decimal("2800000.00"),
        "attachments": "技术合同.pdf,需求文档.docx"
    },
    {
        "project_name": "环保设备采购",
        "project_full_name": "XX工厂环保设备采购及安装项目",
        "project_scale": "中型",
        "start_date": date(2024, 4, 1),
        "end_date": date(2024, 10, 31),
        "project_status": "进行中",
        "project_amount": Decimal("8500000.00"),
        "attachments": "采购合同.pdf,设备清单.xlsx"
    },
    {
        "project_name": "员工培训计划",
        "project_full_name": "2024年度员工技能提升培训计划项目",
        "project_scale": "小型",
        "start_date": date(2024, 1, 1),
        "end_date": date(2024, 12, 31),
        "project_status": "进行中",
        "project_amount": Decimal("500000.00"),
        "attachments": "培训计划.docx,培训协议.pdf"
    },
    {
        "project_name": "数据中心建设",
        "project_full_name": "XX公司数据中心机房建设及设备采购项目",
        "project_scale": "大型",
        "start_date": date(2023, 9, 1),
        "end_date": date(2024, 8, 31),
        "project_status": "已完成",
        "project_amount": Decimal("25000000.00"),
        "attachments": "建设合同.pdf,设备清单.xlsx,验收报告.pdf"
    },
    {
        "project_name": "品牌推广活动",
        "project_full_name": "2024年度品牌推广及市场营销活动项目",
        "project_scale": "小型",
        "start_date": date(2024, 5, 1),
        "end_date": date(2024, 11, 30),
        "project_status": "进行中",
        "project_amount": Decimal("1200000.00"),
        "attachments": "活动方案.docx,合作协议.pdf"
    },
    {
        "project_name": "仓库扩建工程",
        "project_full_name": "XX物流中心仓库扩建及配套设施建设项目",
        "project_scale": "大型",
        "start_date": date(2024, 7, 1),
        "end_date": date(2025, 6, 30),
        "project_status": "进行中",
        "project_amount": Decimal("18000000.00"),
        "attachments": "施工合同.pdf,施工图纸.dwg,预算表.xlsx"
    },
    {
        "project_name": "安全监控系统",
        "project_full_name": "XX园区安全监控系统安装及调试项目",
        "project_scale": "中型",
        "start_date": date(2024, 3, 1),
        "end_date": date(2024, 7, 31),
        "project_status": "已暂停",
        "project_amount": Decimal("3200000.00"),
        "attachments": "采购合同.pdf,技术方案.docx"
    },
    {
        "project_name": "产品研发项目",
        "project_full_name": "新一代智能产品研发及测试项目",
        "project_scale": "中型",
        "start_date": date(2023, 12, 1),
        "end_date": date(2024, 11, 30),
        "project_status": "进行中",
        "project_amount": Decimal("15000000.00"),
        "attachments": "研发计划.docx,技术文档.pdf"
    },
    {
        "project_name": "网络升级改造",
        "project_full_name": "企业网络基础设施升级改造项目",
        "project_scale": "中型",
        "start_date": date(2024, 1, 15),
        "end_date": date(2024, 5, 15),
        "project_status": "已完成",
        "project_amount": Decimal("4500000.00"),
        "attachments": "改造合同.pdf,网络拓扑图.dwg"
    },
    {
        "project_name": "绿化景观工程",
        "project_full_name": "XX公园绿化景观提升改造工程",
        "project_scale": "中型",
        "start_date": date(2024, 4, 1),
        "end_date": date(2024, 9, 30),
        "project_status": "进行中",
        "project_amount": Decimal("6800000.00"),
        "attachments": "施工合同.pdf,设计图纸.dwg"
    },
    {
        "project_name": "设备维护保养",
        "project_full_name": "2024年度生产设备维护保养服务项目",
        "project_scale": "小型",
        "start_date": date(2024, 1, 1),
        "end_date": date(2024, 12, 31),
        "project_status": "进行中",
        "project_amount": Decimal("800000.00"),
        "attachments": "服务合同.pdf,维护计划.xlsx"
    },
    {
        "project_name": "质量认证项目",
        "project_full_name": "ISO9001质量管理体系认证及咨询服务项目",
        "project_scale": "小型",
        "start_date": date(2024, 2, 1),
        "end_date": date(2024, 8, 31),
        "project_status": "已完成",
        "project_amount": Decimal("350000.00"),
        "attachments": "咨询合同.pdf,认证证书.pdf"
    }
]

def add_test_data(force=False):
    with app.app_context():
        try:
            # 检查是否已有数据
            existing_count = ProjectORM.query.count()
            if existing_count > 0 and not force:
                print(f"数据库中已有 {existing_count} 条项目数据。")
                print("如需强制添加，请使用: python add_project_test_data.py --force")
                return
            
            # 如果强制添加，先清空现有数据
            if force and existing_count > 0:
                ProjectORM.query.delete()
                db.session.commit()
                print(f"已清空 {existing_count} 条现有数据。")
            
            for project_data in test_projects:
                project = ProjectORM(**project_data)
                db.session.add(project)
            
            db.session.commit()
            print(f"成功添加 {len(test_projects)} 条项目测试数据！")
            
            # 显示添加的数据统计
            status_count = {}
            for p in test_projects:
                status = p.get("project_status", "未知")
                status_count[status] = status_count.get(status, 0) + 1
            
            print("\n数据统计：")
            for status, count in status_count.items():
                print(f"  {status}: {count} 条")
                
        except Exception as e:
            db.session.rollback()
            print(f"添加数据失败: {e}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv or "-f" in sys.argv
    add_test_data(force=force)

