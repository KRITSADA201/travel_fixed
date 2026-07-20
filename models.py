from extensions import db
from flask_login import UserMixin


class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email    = db.Column(db.String(200), unique=True, nullable=True)
    phone    = db.Column(db.String(20),  unique=True, nullable=True)
    is_admin = db.Column(db.Boolean, default=False)

    reviews   = db.relationship('Review',   backref='user', lazy=True)
    favorites = db.relationship('Favorite', backref='user', lazy=True)


class Category(db.Model):
    __tablename__ = 'category'
    id   = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    places = db.relationship('Place', backref='category', lazy=True)


class Place(db.Model):
    __tablename__ = 'place'
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(200), nullable=False)
    detail      = db.Column(db.Text,        nullable=False)
    location    = db.Column(db.String(200), nullable=False)
    latitude    = db.Column(db.Float,       nullable=True)
    longitude   = db.Column(db.Float,       nullable=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))

    images    = db.relationship('PlaceImage', backref='place', lazy=True, cascade='all, delete-orphan')
    reviews   = db.relationship('Review',     backref='place', lazy=True, cascade='all, delete-orphan')
    favorites = db.relationship('Favorite',   backref='place', lazy=True, cascade='all, delete-orphan')

    @property
    def primary_image(self):
        return self.images[0].url if self.images else None

    @property
    def avg_rating(self):
        if not self.reviews:
            return None
        return round(sum(r.rating for r in self.reviews) / len(self.reviews), 1)


class PlaceImage(db.Model):
    """รองรับหลายภาพต่อสถานที่"""
    __tablename__ = 'place_image'
    id       = db.Column(db.Integer, primary_key=True)
    url      = db.Column(db.String(500), nullable=False)
    caption  = db.Column(db.String(200), nullable=True)
    order    = db.Column(db.Integer, default=0)
    place_id = db.Column(db.Integer, db.ForeignKey('place.id'), nullable=False)


class Review(db.Model):
    __tablename__ = 'review'
    id       = db.Column(db.Integer, primary_key=True)
    comment  = db.Column(db.Text,    nullable=False)
    rating   = db.Column(db.Integer, nullable=False)
    user_id  = db.Column(db.Integer, db.ForeignKey('user.id'),  nullable=False)
    place_id = db.Column(db.Integer, db.ForeignKey('place.id'), nullable=False)


class Favorite(db.Model):
    __tablename__ = 'favorite'
    id       = db.Column(db.Integer, primary_key=True)
    user_id  = db.Column(db.Integer, db.ForeignKey('user.id'),  nullable=False)
    place_id = db.Column(db.Integer, db.ForeignKey('place.id'), nullable=False)
