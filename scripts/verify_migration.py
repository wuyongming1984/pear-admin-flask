import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pear_admin import create_app
from pear_admin.extensions import db
from pear_admin.orms import ProjectORM, AttachmentORM
import json

app = create_app()

def verify():
    with app.app_context():
        projects_with_attachments = ProjectORM.query.filter(ProjectORM.attachments.isnot(None)).all()
        print(f"Projects with attachments (legacy column): {len(projects_with_attachments)}")
        
        attachments_count = AttachmentORM.query.count()
        print(f"Total AttachmentORM records: {attachments_count}")
        
        if len(projects_with_attachments) > 0:
            p = projects_with_attachments[0]
            print(f"Sample Project: {p.project_name}")
            print(f"Attachments JSON: {p.attachments}")
            
            print("Associated AttachmentORM records:")
            for att in p.attachment_list:
                print(f"  - {att.original_filename} ({att.file_path})")

if __name__ == "__main__":
    verify()
