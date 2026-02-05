from flask import Blueprint, render_template, request
from pear_admin.orms import MaterialPlanningORM, MaterialInboundORM, MaterialInventoryORM, MaterialOutboundORM, MaterialInvoiceORM, ProjectORM

material_bp = Blueprint("material", __name__)

@material_bp.route("/view/material/dashboard")
def dashboard():
    return render_template("material/dashboard.html")

@material_bp.route("/view/material/invoice")
def invoice():
    return render_template("material/invoice.html")

@material_bp.route("/view/material/planning")
def planning():
    projects = ProjectORM.query.all()
    from pear_admin.orms import SupplierORM
    suppliers = SupplierORM.query.all()
    return render_template("material/planning.html", projects=projects, suppliers=suppliers)

@material_bp.route("/view/material/inbound")
def inbound():
    projects = ProjectORM.query.all()
    from pear_admin.orms import SupplierORM
    suppliers = SupplierORM.query.all()
    return render_template("material/inbound.html", projects=projects, suppliers=suppliers)

@material_bp.route("/view/material/inventory")
def inventory():
    projects = ProjectORM.query.all()
    return render_template("material/inventory.html", projects=projects)

@material_bp.route("/view/material/outbound")
def outbound():
    projects = ProjectORM.query.all()
    return render_template("material/outbound.html", projects=projects)

@material_bp.route("/view/material/outbound_records")
def outbound_records():
    projects = ProjectORM.query.all()
    return render_template("material/outbound_records.html", projects=projects)

@material_bp.route("/view/material/planning/add")
def planning_add():
    projects = ProjectORM.query.all()
    return render_template("material/planning_add.html", projects=projects)

@material_bp.route("/view/material/inbound/add")
def inbound_add():
    projects = ProjectORM.query.all()
    from pear_admin.orms import SupplierORM
    suppliers = SupplierORM.query.all()
    return render_template("material/inbound_add.html", projects=projects, suppliers=suppliers)

@material_bp.route("/view/material/outbound/add")
def outbound_add():
    projects = ProjectORM.query.all()
    inventory_id = request.args.get('inventory_id')
    target_inventory = None
    if inventory_id:
        target_inventory = MaterialInventoryORM.query.get(inventory_id)
    return render_template("material/outbound_add.html", projects=projects, target_inventory=target_inventory)
    
@material_bp.route("/view/material/outbound/batch_add")
def outbound_batch_add():
    """批量出库页面"""
    ids_str = request.args.get('ids', '')
    ids = [int(i) for i in ids_str.split(',') if i.strip()]
    
    inventory_items = []
    if ids:
        inventory_items = MaterialInventoryORM.query.filter(MaterialInventoryORM.id.in_(ids)).all()
        
    return render_template("material/outbound_batch_add.html", inventory_items=inventory_items)

@material_bp.route("/view/material/invoice/add")
def invoice_add():
    return render_template("material/invoice_add.html")

@material_bp.route("/view/material/inbound/edit/<int:id>")
def inbound_edit(id):
    from pear_admin.orms import MaterialInboundORM, ProjectORM, SupplierORM
    inbound = MaterialInboundORM.query.get(id)
    projects = ProjectORM.query.all()
    suppliers = SupplierORM.query.all()
    return render_template("material/inbound_edit.html", inbound=inbound, projects=projects, suppliers=suppliers)
