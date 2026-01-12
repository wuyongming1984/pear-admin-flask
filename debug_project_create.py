from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import ProjectORM
from datetime import datetime

app = create_app()

def debug_create():
    with app.app_context():
        # Simulate data from frontend
        data = {
            "id": None,
            "project_name": "Debug Project",
            "project_full_name": "Debug Full Name",
            "project_scale": "Large",
            "start_date": "2025-01-01",
            "end_date": "2026-01-01",
            "project_status": "进行中",
            "project_amount": 1000.0,
            "attachments": "[]"
        }
        
        print(f"Original Data: {data}")

        # Simulate create_project logic
        if data.get("id"):
            del data["id"]
        
        # Check if 'id' is still in data (it will be if it was None)
        print(f"Data after id check: keys={list(data.keys())}, id_value={data.get('id')}")

        if "attachments" in data:
            data.pop("attachments")
            
        if data.get("start_date"):
            data["start_date"] = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
        if data.get("end_date"):
            data["end_date"] = datetime.strptime(data["end_date"], "%Y-%m-%d").date()
            
        if data.get("project_amount"):
            data["project_amount"] = float(data["project_amount"])
            
        print(f"Data before ORM init: {data}")
        
        try:
            project = ProjectORM(**data)
            print("ORM Inited.")
            db.session.add(project)
            db.session.commit()
            print("Save Success!")
        except Exception as e:
            print(f"Save Failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_create()
