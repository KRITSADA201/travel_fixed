from flask import Blueprint, render_template, redirect, url_for, request, abort
from flask_login import login_required, current_user
from extensions import db
from models import User, Place, Category, Review

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def _admin_required():
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(403)


@admin_bp.route('/')
@login_required
def dashboard():
    _admin_required()
    return render_template('admin/dashboard.html',
                           users=User.query.all(),
                           places=Place.query.all(),
                           categories=Category.query.all())


@admin_bp.route('/category/add', methods=['POST'])
@login_required
def add_category():
    _admin_required()
    name = request.form.get('name', '').strip()
    if name and not Category.query.filter_by(name=name).first():
        db.session.add(Category(name=name))
        db.session.commit()
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/category/delete/<int:id>', methods=['POST'])
@login_required
def delete_category(id):
    _admin_required()
    cat = Category.query.get_or_404(id)
    # ถ้ามีสถานที่ในหมวดนี้ให้ set เป็น null ก่อน
    for p in Place.query.filter_by(category_id=id).all():
        p.category_id = None
    db.session.delete(cat)
    db.session.commit()
    return redirect(url_for('admin.dashboard'))
