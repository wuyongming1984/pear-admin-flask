from flask import Blueprint, jsonify, request
from pear_admin.extensions import db
from pear_admin.orms.nursery import NurseryPlantORM, NurseryTransactionORM
import datetime
import uuid

nursery_api = Blueprint("nursery_api", __name__, url_prefix="/nursery")

@nursery_api.get("/inventory")
def get_inventory():
    """获取苗圃库存列表"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    
    query = NurseryPlantORM.query.filter(NurseryPlantORM.quantity > 0)
    
    # 简单的搜索支持
    search_name = request.args.get('name')
    if search_name:
        query = query.filter(NurseryPlantORM.name.like(f"%{search_name}%"))
        
    pagination = query.order_by(NurseryPlantORM.update_at.desc()).paginate(
        page=page, per_page=limit, error_out=False
    )
    
    return jsonify({
        "code": 0,
        "msg": "",
        "count": pagination.total,
        "data": [item.json() for item in pagination.items]
    })

@nursery_api.get("/transactions")
def get_transactions():
    """获取入出库流水"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    
    query = NurseryTransactionORM.query
    
    type_filter = request.args.get('type')
    if type_filter:
        query = query.filter(NurseryTransactionORM.type == type_filter)
        
    pagination = query.order_by(NurseryTransactionORM.create_at.desc()).paginate(
        page=page, per_page=limit, error_out=False
    )
    
    return jsonify({
        "code": 0,
        "msg": "",
        "count": pagination.total,
        "data": [item.json() for item in pagination.items]
    })

@nursery_api.post("/inbound")
def inbound():
    """
    入库接口
    核心逻辑:
    1. 查找是否存在同名、同规格、同单位的苗木
    2. 如果存在，计算加权平均价: (旧量*旧价 + 新量*新价) / 总量
    3. 更新库存 or 新增库存记录
    4. 记录流水
    """
    data = request.json
    name = data.get('name')
    category = data.get('category')
    spec = data.get('spec', '')
    unit = data.get('unit', '')
    quantity = float(data.get('quantity', 0))
    price = float(data.get('price', 0)) # 进价
    location = data.get('location', '')
    operator = data.get('operator', 'Admin')
    remark = data.get('remark', '')
    
    if not name or quantity <= 0:
        return jsonify({"success": False, "msg": "名称和数量必填且数量需大于0"})

    # 生成单号
    order_no = "IN" + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    
    # 查找库存
    existing = NurseryPlantORM.query.filter_by(
        name=name, spec=spec, unit=unit
    ).first()
    
    plant_id = None
    
    if existing:
        old_qty = float(existing.quantity)
        old_price = float(existing.price)
        
        new_total_qty = old_qty + quantity
        new_total_value = (old_qty * old_price) + (quantity * price)
        new_avg_price = new_total_value / new_total_qty if new_total_qty > 0 else 0
        
        existing.quantity = new_total_qty
        existing.price = new_avg_price
        existing.location = location or existing.location
        existing.update_at = datetime.datetime.now()
        plant_id = existing.id
    else:
        new_plant = NurseryPlantORM(
            name=name,
            category=category,
            spec=spec,
            unit=unit,
            quantity=quantity,
            price=price,
            location=location,
            remark=remark,
            create_at=datetime.datetime.now(),
            update_at=datetime.datetime.now()
        )
        db.session.add(new_plant)
        db.session.flush() # 获取ID
        plant_id = new_plant.id
        
    # 记录流水
    tx = NurseryTransactionORM(
        order_no=order_no,
        type='in',
        plant_id=plant_id,
        plant_name=name,
        spec=spec,
        unit=unit,
        quantity=quantity,
        price=price,
        total_price=quantity * price,
        operator=operator,
        location=location,
        remark=remark,
        create_at=datetime.datetime.now()
    )
    db.session.add(tx)
    db.session.commit()
    
    return jsonify({"success": True, "msg": "入库成功", "order_no": order_no})

@nursery_api.post("/outbound")
def outbound():
    """
    批量出库接口
    核心逻辑:
    1. 遍历所有出库项目
    2. 对于库存项目：检查库存是否充足，扣减库存
    3. 对于非入库项目：直接记录流水
    4. 记录流水
    """
    data = request.json
    items = data.get('items', [])
    destination = data.get('destination', '')
    operator = data.get('operator', 'Admin')
    remark = data.get('remark', '')
    
    if not items or len(items) == 0:
        return jsonify({"success": False, "msg": "请添加出库项目"})
    
    # 生成单号
    order_no = "OUT" + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    
    try:
        for item in items:
            plant_id = item.get('plant_id')
            quantity = float(item.get('quantity', 0))
            price = float(item.get('price', 0))
            is_non_inventory = item.get('is_non_inventory', False)
            item_name = item.get('name', '')
            
            if quantity <= 0:
                continue
            
            if is_non_inventory or not plant_id:
                # 非入库项目 - 直接记录流水
                tx = NurseryTransactionORM(
                    order_no=order_no,
                    type='out',
                    plant_id=None,
                    plant_name=item_name,
                    spec=item.get('spec', '-'),
                    unit=item.get('unit', '株'),
                    quantity=quantity,
                    price=price,
                    total_price=quantity * price,
                    operator=operator,
                    destination=destination,
                    location='非入库',
                    remark=remark + ' [非入库]',
                    create_at=datetime.datetime.now()
                )
                db.session.add(tx)
            else:
                # 库存项目
                plant = NurseryPlantORM.query.get(plant_id)
                if not plant:
                    return jsonify({"success": False, "msg": f"库存项目 {item_name} 不存在"})
                
                if float(plant.quantity) < quantity:
                    return jsonify({"success": False, "msg": f"{plant.name} 库存不足! 当前: {plant.quantity}"})
                
                # 扣减库存
                plant.quantity = float(plant.quantity) - quantity
                plant.update_at = datetime.datetime.now()
                
                # 记录流水
                tx = NurseryTransactionORM(
                    order_no=order_no,
                    type='out',
                    plant_id=plant.id,
                    plant_name=plant.name,
                    spec=plant.spec,
                    unit=plant.unit,
                    quantity=quantity,
                    price=price,
                    total_price=quantity * price,
                    operator=operator,
                    destination=destination,
                    location=plant.location,
                    remark=remark,
                    create_at=datetime.datetime.now()
                )
                db.session.add(tx)
        
        db.session.commit()
        return jsonify({"success": True, "msg": "出库成功", "order_no": order_no})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "msg": f"出库失败: {str(e)}"})

@nursery_api.get("/dashboard/stats")
def dashboard_stats():
    """仪表盘统计数据"""
    from sqlalchemy import func
    
    # 库存总品种数
    total_varieties = NurseryPlantORM.query.filter(NurseryPlantORM.quantity > 0).count()
    
    # 本月出库次数
    now = datetime.datetime.now()
    first_day = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_outbound = NurseryTransactionORM.query.filter(
        NurseryTransactionORM.type == 'out',
        NurseryTransactionORM.create_at >= first_day
    ).count()
    
    # 在库大类数量
    categories = db.session.query(NurseryPlantORM.category).filter(
        NurseryPlantORM.quantity > 0, NurseryPlantORM.category.isnot(None)
    ).distinct().all()
    category_count = len([c for c in categories if c[0]])
    
    # 低库存预警 (数量 < 50)
    low_stock = NurseryPlantORM.query.filter(
        NurseryPlantORM.quantity > 0, NurseryPlantORM.quantity < 50
    ).count()
    
    # 分类分布
    category_distribution = db.session.query(
        NurseryPlantORM.category, func.count(NurseryPlantORM.id)
    ).filter(NurseryPlantORM.quantity > 0).group_by(NurseryPlantORM.category).all()
    
    # TOP5 库存
    top5 = NurseryPlantORM.query.filter(NurseryPlantORM.quantity > 0).order_by(
        NurseryPlantORM.quantity.desc()
    ).limit(5).all()
    
    # 最新动态
    recent = NurseryTransactionORM.query.order_by(
        NurseryTransactionORM.create_at.desc()
    ).limit(10).all()
    
    return jsonify({
        "code": 0,
        "data": {
            "total_varieties": total_varieties,
            "month_outbound": month_outbound,
            "category_count": category_count,
            "low_stock": low_stock,
            "category_distribution": [
                {"category": c[0] or "未分类", "count": c[1]} for c in category_distribution
            ],
            "top5": [{"name": p.name, "quantity": float(p.quantity)} for p in top5],
            "recent_activities": [t.json() for t in recent]
        }
    })

@nursery_api.delete("/order/<order_no>")
def delete_order(order_no):
    """
    删除出库单并回退库存
    核心逻辑:
    1. 查找该单号的所有流水
    2. 对于库存项目:将数量退回库存
    3. 删除所有相关流水记录
    """
    try:
        transactions = NurseryTransactionORM.query.filter_by(
            order_no=order_no, type='out'
        ).all()
        
        if not transactions:
            return jsonify({"success": False, "msg": "订单不存在"})
        
        # 回退库存
        for tx in transactions:
            if tx.plant_id:
                plant = NurseryPlantORM.query.get(tx.plant_id)
                if plant:
                    plant.quantity = float(plant.quantity) + float(tx.quantity)
                    plant.update_at = datetime.datetime.now()
            
            db.session.delete(tx)
        
        db.session.commit()
        return jsonify({"success": True, "msg": "订单已删除，库存已回退"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "msg": f"删除失败: {str(e)}"})

@nursery_api.put("/order/<order_no>")
def update_order(order_no):
    """
    更新出库单信息
    支持修改: 操作员、去向、备注、各项目的数量和价格
    """
    data = request.json
    operator = data.get('operator')
    destination = data.get('destination')
    remark = data.get('remark')
    items = data.get('items', [])  # [{id, quantity, price}, ...]
    
    try:
        transactions = NurseryTransactionORM.query.filter_by(
            order_no=order_no, type='out'
        ).all()
        
        if not transactions:
            return jsonify({"success": False, "msg": "订单不存在"})
        
        # 更新基础信息
        for tx in transactions:
            if operator:
                tx.operator = operator
            if destination is not None:
                tx.destination = destination
            if remark is not None:
                tx.remark = remark
        
        # 更新各项目
        for item_update in items:
            tx_id = item_update.get('id')
            new_qty = item_update.get('quantity')
            new_price = item_update.get('price')
            
            if not tx_id:
                continue
            
            tx = NurseryTransactionORM.query.get(tx_id)
            if not tx or tx.order_no != order_no:
                continue
            
            # 处理数量变化 - 调整库存
            if new_qty is not None and tx.plant_id:
                old_qty = float(tx.quantity)
                new_qty = float(new_qty)
                qty_diff = old_qty - new_qty  # 正数=减少出库=退回库存
                
                plant = NurseryPlantORM.query.get(tx.plant_id)
                if plant:
                    new_plant_qty = float(plant.quantity) + qty_diff
                    if new_plant_qty < 0:
                        return jsonify({"success": False, "msg": f"{plant.name} 库存不足以支持此修改"})
                    plant.quantity = new_plant_qty
                    plant.update_at = datetime.datetime.now()
                
                tx.quantity = new_qty
                tx.total_price = new_qty * float(tx.price)
            
            # 更新价格
            if new_price is not None:
                tx.price = float(new_price)
                tx.total_price = float(tx.quantity) * float(new_price)
        
        db.session.commit()
        return jsonify({"success": True, "msg": "订单更新成功"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "msg": f"更新失败: {str(e)}"})

@nursery_api.get("/orders")
def get_orders():
    """获取出库单列表 (按订单号分组)"""
    from sqlalchemy import func
    
    # 获取所有出库单号
    order_nos = db.session.query(
        NurseryTransactionORM.order_no,
        func.sum(NurseryTransactionORM.total_price).label('total'),
        func.max(NurseryTransactionORM.create_at).label('create_at'),
        func.max(NurseryTransactionORM.operator).label('operator'),
        func.max(NurseryTransactionORM.destination).label('destination'),
        func.count(NurseryTransactionORM.id).label('item_count')
    ).filter(
        NurseryTransactionORM.type == 'out',
        NurseryTransactionORM.order_no.isnot(None)
    ).group_by(NurseryTransactionORM.order_no).order_by(
        func.max(NurseryTransactionORM.create_at).desc()
    ).all()
    
    orders = []
    for row in order_nos:
        # 获取该订单的所有项目
        items = NurseryTransactionORM.query.filter_by(
            order_no=row.order_no, type='out'
        ).all()
        
        orders.append({
            "order_no": row.order_no,
            "total": float(row.total or 0),
            "create_at": row.create_at.strftime("%Y-%m-%d %H:%M") if row.create_at else "",
            "operator": row.operator or "",
            "destination": row.destination or "",
            "item_count": row.item_count,
            "items": [item.json() for item in items]
        })
    
    return jsonify({"code": 0, "data": orders})

