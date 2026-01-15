import sys
import os
sys.path.append(os.getcwd())
from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import RightsORM

app = create_app()
with app.app_context():
    try:
        # 查询顶级菜单
        q = db.select(RightsORM).where(
            (RightsORM.pid == 0) | (RightsORM.pid.is_(None))
        ).order_by(RightsORM.sort, RightsORM.id)
        
        # 模仿分页
        pages = db.paginate(q, page=1, per_page=10, error_out=False)
        print(f"Total rights (top level): {pages.total}")
        
        ret = []
        for rights_item in pages.items:
            print(f"Processing right: {rights_item.id} - {rights_item.name}")
            data = rights_item.json()
            data["children"] = []
            
            # 访问子节点
            print(f"  Children count: {len(rights_item.children)}")
            for child in rights_item.children:
                child_data = child.json()
                child_data["children"] = []
                
                # 访问孙节点
                if child.children:
                    print(f"    Grandchildren count: {len(child.children)}")
                    child_data["children"] = [
                        sub_child.json() for sub_child in child.children
                    ]
                    child_data["isParent"] = True

                data["children"].append(child_data)
            
            if data["children"]:
                data["isParent"] = True
            ret.append(data)
            
        print("Successfully structured rights data.")
    except Exception as e:
        print("Error encountered:")
        import traceback
        traceback.print_exc()
