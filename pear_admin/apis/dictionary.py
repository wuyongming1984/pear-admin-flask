from flask import jsonify, request, Blueprint
from flask_jwt_extended import jwt_required, get_jwt_identity
from pear_admin.extensions import db
from pear_admin.orms.dictionary import DictionaryORM, DictionaryDetailORM

dictionary_api_bp = Blueprint('dictionary_api', __name__, url_prefix='/dictionary')

@dictionary_api_bp.route('/list', methods=['GET'])
@jwt_required()
def dictionary_list():
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    code_desc = request.args.get('code_desc', '')

    query = DictionaryORM.query
    if code_desc:
        query = query.filter(
            db.or_(
                DictionaryORM.code.like(f'%{code_desc}%'),
                DictionaryORM.name.like(f'%{code_desc}%')
            )
        )
    
    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    
    return jsonify({
        'code': 0,
        'msg': '',
        'count': pagination.total,
        'data': [item.json() for item in pagination.items]
    })

@dictionary_api_bp.route('/', methods=['POST'])
@jwt_required()
def add_dictionary():
    data = request.json
    code = data.get('code')
    name = data.get('name')
    
    if not code or not name:
        return jsonify({'success': False, 'msg': '代码和描述不能为空'})
        
    if DictionaryORM.query.filter_by(code=code).first():
        return jsonify({'success': False, 'msg': '字典代码已存在'})

    new_dic = DictionaryORM(
        code=code,
        name=name,
        create_user=get_jwt_identity()
    )
    db.session.add(new_dic)
    db.session.commit()
    return jsonify({'success': True, 'msg': '添加成功'})

@dictionary_api_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def update_dictionary(id):
    dic = DictionaryORM.query.get_or_404(id)
    data = request.json
    
    dic.code = data.get('code', dic.code)
    dic.name = data.get('name', dic.name)
    dic.update_user = get_jwt_identity()
    
    db.session.commit()
    return jsonify({'success': True, 'msg': '修改成功'})

@dictionary_api_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_dictionary(id):
    dic = DictionaryORM.query.get_or_404(id)
    
    # Check if has details
    if dic.details.count() > 0:
         return jsonify({'success': False, 'msg': '该字典下有明细数据，无法删除'})

    db.session.delete(dic)
    db.session.commit()
    return jsonify({'success': True, 'msg': '删除成功'})


# --- Dictionary Detail APIs ---

@dictionary_api_bp.route('/detail/list', methods=['GET'])
@jwt_required()
def detail_list():
    dic_id = request.args.get('dic_id')
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    
    if not dic_id:
        return jsonify({'code': 0, 'msg': '', 'count': 0, 'data': []})

    query = DictionaryDetailORM.query.filter_by(dic_id=dic_id).order_by(DictionaryDetailORM.order_no.asc())
    
    pagination = query.paginate(page=page, per_page=limit, error_out=False)

    return jsonify({
        'code': 0,
        'msg': '',
        'count': pagination.total,
        'data': [item.json() for item in pagination.items]
    })

@dictionary_api_bp.route('/detail', methods=['POST'])
@jwt_required()
def add_detail():
    data = request.json
    dic_id = data.get('dic_id')
    code = data.get('code')
    value = data.get('value')
    order_no = data.get('order_no', 0)
    
    if not dic_id or not code or not value:
         return jsonify({'success': False, 'msg': '参数不完整'})

    new_detail = DictionaryDetailORM(
        dic_id=dic_id,
        code=code,
        value=value,
        order_no=order_no,
        create_user=get_jwt_identity()
    )
    db.session.add(new_detail)
    db.session.commit()
    return jsonify({'success': True, 'msg': '添加成功'})

@dictionary_api_bp.route('/detail/<int:id>', methods=['PUT'])
@jwt_required()
def update_detail(id):
    detail = DictionaryDetailORM.query.get_or_404(id)
    data = request.json
    
    detail.code = data.get('code', detail.code)
    detail.value = data.get('value', detail.value)
    detail.order_no = data.get('order_no', detail.order_no)
    detail.update_user = get_jwt_identity()
    
    db.session.commit()
    return jsonify({'success': True, 'msg': '修改成功'})

@dictionary_api_bp.route('/detail/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_detail(id):
    detail = DictionaryDetailORM.query.get_or_404(id)
    db.session.delete(detail)
    db.session.commit()
    return jsonify({'success': True, 'msg': '删除成功'})
