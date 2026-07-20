from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from models import User, Review, Favorite, Place

user_bp = Blueprint('user', __name__, url_prefix='/user')


@user_bp.route('/profile')
@login_required
def profile():
    return _show_profile(current_user)


@user_bp.route('/profile/<int:user_id>')
@login_required
def profile_user(user_id):
    if not current_user.is_admin and current_user.id != user_id:
        abort(403)
    user = User.query.get_or_404(user_id)
    return _show_profile(user)


def _show_profile(user):
    reviews    = Review.query.filter_by(user_id=user.id).all()
    fav_places = [f.place for f in Favorite.query.filter_by(user_id=user.id).all()]
    return render_template('user/profile.html',
                           user=user, reviews=reviews, fav_places=fav_places)
