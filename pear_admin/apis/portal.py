import secrets
from flask import Blueprint, render_template, abort
from pear_admin.extensions import db
from pear_admin.orms import SupplierORM, OrderORM, PayORM

portal_bp = Blueprint('portal', __name__, url_prefix='/portal')

from sqlalchemy import func

@portal_bp.route('/reconcile/<token>')
def reconcile(token):
    # 1. Validate Token & Identify Anchor
    anchor_supplier = db.session.scalar(
        db.select(SupplierORM).where(SupplierORM.access_token == token)
    )
    
    if not anchor_supplier:
        abort(404)  # Not found or invalid token
        
    # Standardize the target contact name (remove whitespace)
    target_contact = anchor_supplier.contact_person.strip() if anchor_supplier.contact_person else ""
        
    # 2. Find All Related Suppliers (Same Contact Name - Robust with Trim)
    # Virtual Identity Aggregation
    related_suppliers = db.session.scalars(
        db.select(SupplierORM).where(
            func.trim(SupplierORM.contact_person) == target_contact
        )
    ).all()
    
    related_ids = [s.id for s in related_suppliers]
    
    # 3. Fetch Data (Transactional)
    # Fetch Orders with their Payments (Eager Load)
    # Note: Use joinedload to avoid N+1 queries when accessing order.pays and order.project
    orders = db.session.scalars(
        db.select(OrderORM)
        .where(
            db.or_(
                OrderORM.supplier_id.in_(related_ids),
                # Use trim for the text-based order lookup as well
                func.trim(OrderORM.supplier_contact_person) == target_contact
            )
        )
        .options(
            db.joinedload(OrderORM.pays).joinedload(PayORM.payee_supplier),
            db.joinedload(OrderORM.pays).joinedload(PayORM.payer),
            db.joinedload(OrderORM.project)
        )
        .order_by(OrderORM.create_at.desc())
    ).unique().all()
    
    # Fetch Unlinked Payments (Payments associated with these suppliers but NO Order ID)
    unlinked_payments = db.session.scalars(
        db.select(PayORM)
        .where(
            PayORM.payee_supplier_id.in_(related_ids),
            PayORM.order_id == None
        )
        .order_by(PayORM.create_at.desc())
    ).all()
    
    
    # 3.5 Group Orders by Project
    # Sort first: Project Name (ASC) -> Order Date (DESC)
    def file_sort_key(o):
        p_name = o.project.project_name if o.project and o.project.project_name else " ⚠️ 未归类项目 (Uncategorized)"
        return (p_name, o.create_at)

    orders.sort(key=file_sort_key, reverse=True) # Sort by date desc (secondary)
    # Actually we want Project ASC, Date DESC. 
    # Let's use a simple dictionary grouping to control sort order explicitly.
    
    from collections import defaultdict
    grouped_orders_dict = defaultdict(list)
    for o in orders:
        p_name = o.project.project_name if o.project and o.project.project_name else "⚠️ 未归类项目 (Uncategorized)"
        grouped_orders_dict[p_name].append(o)
        
    # Convert to list of tuples for template iteration: [(ProjectName, [Orders...]), ...]
    # Sort projects alphabetically (or however desired), put Uncategorized last if possible, but alphabetically it works ok.
    # New: Calculate stats for each project
    grouped_orders = []
    for p_name, p_orders in sorted(grouped_orders_dict.items(), key=lambda x: x[0]):
        p_total_orders = sum(float(o.order_amount or 0) for o in p_orders)
        # Sum payments linked to these orders
        p_total_paid = sum(float(p.current_payment_amount or 0) for o in p_orders for p in o.pays)
        p_balance = p_total_orders - p_total_paid
        
        stats = {
            "total_orders": p_total_orders,
            "total_paid": p_total_paid,
            "balance": p_balance
        }
        grouped_orders.append((p_name, p_orders, stats))

    # 4. Calculate Totals
    total_orders = 0
    total_received_linked = 0
    total_received_unlinked = 0
    
    for o in orders:
        o_amt = float(o.order_amount or 0)
        total_orders += o_amt
        # Calculate paid amount for this order
        paid_amt = sum(float(p.current_payment_amount or 0) for p in o.pays)
        total_received_linked += paid_amt
        
        # Attach temporary attributes for template usage (to avoid logic in template)
        o.temp_paid_amount = paid_amt
        o.temp_balance = o_amt - paid_amt
        
    for p in unlinked_payments:
        total_received_unlinked += float(p.current_payment_amount or 0)
        
    total_received = total_received_linked + total_received_unlinked
    outstanding_balance = total_orders - total_received

    # 5. Render Template
    return render_template(
        'portal/reconcile.html',
        supplier=anchor_supplier,
        related_suppliers=related_suppliers,
        grouped_orders=grouped_orders, # Pass grouped structure
        # orders=orders, # No longer needed as flat list for main loop, but maybe for stats? Stats used 'orders' list above which is fine.
        unlinked_payments=unlinked_payments,
        analysis={
            "total_orders": total_orders,
            "total_received": total_received,
            "outstanding_balance": outstanding_balance
        }
    )
