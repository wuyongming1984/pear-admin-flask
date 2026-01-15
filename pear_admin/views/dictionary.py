from flask import Blueprint, render_template

dictionary_bp = Blueprint('dictionary', __name__, url_prefix='/system/dictionary')

@dictionary_bp.route('/')
def index():
    return render_template('system/dictionary/index.html')
