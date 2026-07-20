import math
from flask import Blueprint, render_template, redirect, url_for, request, jsonify, abort
from flask_login import login_required, current_user
from extensions import db
from models import Place, PlaceImage, Category, Review, Favorite

places = Blueprint('places', __name__)


# ── helpers ──────────────────────────────────────────────────────────────────
def _avg_ratings(place_list):
    return {p.id: p.avg_rating for p in place_list}

def _favorites():
    if not current_user.is_authenticated:
        return set()
    return {f.place_id for f in Favorite.query.filter_by(user_id=current_user.id).all()}


# ── Home ──────────────────────────────────────────────────────────────────────
@places.route('/')
def home():
    all_places = Place.query.all()
    categories = Category.query.all()

    def sort_key(p):
        return p.avg_rating if p.avg_rating is not None else -1

    sorted_places = sorted(all_places, key=sort_key, reverse=True)

    places_by_cat = {}
    for c in categories:
        cat_places = [p for p in all_places if p.category_id == c.id]
        places_by_cat[c.id] = sorted(cat_places, key=sort_key, reverse=True)

    return render_template('places/home.html',
                           places=sorted_places,
                           places_by_cat=places_by_cat,
                           avg_ratings=_avg_ratings(all_places),
                           favorites=_favorites(),
                           categories=categories)


# ── List + Search ─────────────────────────────────────────────────────────────
@places.route('/places')
def list_places():
    q = request.args.get('q', '').strip()
    cat = request.args.get('cat', type=int)

    query = Place.query
    if q:
        query = query.filter(
            Place.name.ilike(f'%{q}%') |
            Place.location.ilike(f'%{q}%')
        )
    if cat:
        query = query.filter_by(category_id=cat)

    all_places = query.all()
    # เรียงคะแนนสูง→ต่ำ, ไม่มีคะแนนไว้ท้าย
    all_places = sorted(all_places, key=lambda p: p.avg_rating if p.avg_rating is not None else -1, reverse=True)
    categories = Category.query.all()
    return render_template('places/list.html',
                           places=all_places,
                           avg_ratings=_avg_ratings(all_places),
                           favorites=_favorites(),
                           categories=categories,
                           q=q, active_cat=cat)


# ── Detail + Review ───────────────────────────────────────────────────────────
@places.route('/place/<int:id>', methods=['GET', 'POST'])
def detail(id):
    place = Place.query.get_or_404(id)
    reviews = place.reviews

    is_favorite   = False
    user_reviewed = False
    if current_user.is_authenticated:
        is_favorite   = Favorite.query.filter_by(user_id=current_user.id, place_id=id).first() is not None
        user_reviewed = Review.query.filter_by(user_id=current_user.id, place_id=id).first() is not None

    if request.method == 'POST':
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not user_reviewed:
            comment = request.form.get('comment','').strip()
            rating_raw = request.form.get('rating','').strip()
            # ต้องมีอย่างน้อย comment หรือ rating
            if comment or rating_raw:
                r = Review(comment=comment or '-',
                           rating=int(rating_raw) if rating_raw else 0,
                           user_id=current_user.id, place_id=id)
                db.session.add(r); db.session.commit()
        return redirect(url_for('places.detail', id=id))

    # หาสถานที่ใกล้เคียง (ใช้ Haversine formula)
    nearby_places = []
    if place.latitude and place.longitude:
        all_others = Place.query.filter(
            Place.id != id,
            Place.latitude.isnot(None),
            Place.longitude.isnot(None)
        ).all()

        def haversine(lat1, lon1, lat2, lon2):
            R = 6371  # km
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
            return R * 2 * math.asin(math.sqrt(a))

        with_dist = [(p, haversine(place.latitude, place.longitude, p.latitude, p.longitude))
                     for p in all_others]
        with_dist.sort(key=lambda x: x[1])
        # เอาสถานที่ที่อยู่ภายใน 100 กม. สูงสุด 6 แห่ง
        nearby_places = [(p, round(d, 1)) for p, d in with_dist if d <= 100][:6]

    return render_template('places/detail.html',
                           place=place, reviews=reviews,
                           is_favorite=is_favorite, user_reviewed=user_reviewed,
                           nearby_places=nearby_places)


# ── Add ───────────────────────────────────────────────────────────────────────
@places.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if not current_user.is_admin:
        abort(403)

    categories = Category.query.all()
    if request.method == 'POST':
        lat = request.form.get('latitude',  '').strip()
        lng = request.form.get('longitude', '').strip()

        place = Place(
            name        = request.form['name'],
            detail      = request.form['detail'],
            location    = request.form['location'],
            category_id = request.form['category_id'],
            user_id     = current_user.id,
            latitude    = float(lat) if lat else None,
            longitude   = float(lng) if lng else None,
        )
        db.session.add(place)
        db.session.flush()   # ได้ place.id ก่อน commit

        # บันทึกภาพหลายรูป
        for i, url in enumerate(request.form.getlist('image_urls')):
            url = url.strip()
            if url:
                caption = request.form.getlist('image_captions')[i] if i < len(request.form.getlist('image_captions')) else ''
                db.session.add(PlaceImage(url=url, caption=caption, order=i, place_id=place.id))

        db.session.commit()
        return redirect(url_for('places.detail', id=place.id))

    return render_template('places/add.html', categories=categories)


# ── Edit ──────────────────────────────────────────────────────────────────────
@places.route('/place/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    if not current_user.is_admin:
        abort(403)
    place = Place.query.get_or_404(id)
    categories = Category.query.all()

    if request.method == 'POST':
        lat = request.form.get('latitude',  '').strip()
        lng = request.form.get('longitude', '').strip()

        place.name        = request.form['name']
        place.detail      = request.form['detail']
        place.location    = request.form['location']
        place.category_id = request.form['category_id']
        place.latitude    = float(lat) if lat else None
        place.longitude   = float(lng) if lng else None

        # ลบภาพที่ถูกทำเครื่องหมายลบ
        delete_ids = request.form.getlist('delete_images')
        for img_id in delete_ids:
            img = PlaceImage.query.get(int(img_id))
            if img and img.place_id == place.id:
                db.session.delete(img)

        # เพิ่มภาพใหม่
        new_urls     = request.form.getlist('new_image_urls')
        new_captions = request.form.getlist('new_image_captions')
        existing_count = PlaceImage.query.filter_by(place_id=place.id).count()
        for i, url in enumerate(new_urls):
            url = url.strip()
            if url:
                cap = new_captions[i] if i < len(new_captions) else ''
                db.session.add(PlaceImage(url=url, caption=cap, order=existing_count + i, place_id=place.id))

        db.session.commit()
        return redirect(url_for('places.detail', id=place.id))

    return render_template('places/edit.html', place=place, categories=categories)


# ── Delete ────────────────────────────────────────────────────────────────────
@places.route('/place/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    if not current_user.is_admin:
        abort(403)
    place = Place.query.get_or_404(id)
    db.session.delete(place)
    db.session.commit()
    return redirect(url_for('places.list_places'))


# ── Favorites ─────────────────────────────────────────────────────────────────
@places.route('/favorite/<int:place_id>')
@login_required
def toggle_favorite(place_id):
    fav = Favorite.query.filter_by(user_id=current_user.id, place_id=place_id).first()
    if fav:
        db.session.delete(fav)
    else:
        db.session.add(Favorite(user_id=current_user.id, place_id=place_id))
    db.session.commit()
    return redirect(request.args.get('next', url_for('places.detail', id=place_id)))


@places.route('/favorites')
@login_required
def my_favorites():
    fav_places = [f.place for f in Favorite.query.filter_by(user_id=current_user.id).all()]
    return render_template('places/favorites.html',
                           places=fav_places,
                           avg_ratings=_avg_ratings(fav_places))


# ── Review delete ─────────────────────────────────────────────────────────────
@places.route('/review/<int:id>/delete')
@login_required
def delete_review(id):
    r = Review.query.get_or_404(id)
    if r.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    place_id = r.place_id
    db.session.delete(r); db.session.commit()
    return redirect(url_for('places.detail', id=place_id))



# ── Nearby places by user GPS ─────────────────────────────────────────────────
@places.route('/api/nearby')
def api_nearby():
    import math
    try:
        user_lat = float(request.args.get('lat'))
        user_lng = float(request.args.get('lng'))
        exclude_id = request.args.get('exclude', type=int)
    except (TypeError, ValueError):
        return jsonify([])

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        return R * 2 * math.asin(math.sqrt(a))

    candidates = Place.query.filter(
        Place.latitude.isnot(None),
        Place.longitude.isnot(None)
    ).all()
    if exclude_id:
        candidates = [p for p in candidates if p.id != exclude_id]

    with_dist = [(p, haversine(user_lat, user_lng, p.latitude, p.longitude))
                 for p in candidates]
    with_dist.sort(key=lambda x: x[1])
    nearby = [(p, round(d, 1)) for p, d in with_dist if d <= 100][:6]

    result = []
    for p, dist in nearby:
        result.append({
            'id': p.id,
            'name': p.name,
            'location': p.location,
            'image_url': p.primary_image or '',
            'avg_rating': p.avg_rating,
            'dist': dist,
        })
    return jsonify(result)


# ── Nearby hotels/accommodations ──────────────────────────────────────────────
@places.route('/api/nearby-hotels')
def api_nearby_hotels():
    import math
    try:
        user_lat = float(request.args.get('lat'))
        user_lng = float(request.args.get('lng'))
        exclude_id = request.args.get('exclude', type=int)
    except (TypeError, ValueError):
        return jsonify([])

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        return R * 2 * math.asin(math.sqrt(a))

    from models import Category
    # หาหมวดหมู่ที่ชื่อมีคำว่า ห้องพัก หรือ โรงแรม หรือ ที่พัก
    hotel_cats = Category.query.filter(
        Category.name.ilike('%ห้องพัก%') |
        Category.name.ilike('%โรงแรม%') |
        Category.name.ilike('%ที่พัก%') |
        Category.name.ilike('%รีสอร์ท%') |
        Category.name.ilike('%เกสต์เฮ้าส์%')
    ).all()

    if not hotel_cats:
        return jsonify([])

    hotel_cat_ids = [cat.id for cat in hotel_cats]
    candidates = Place.query.filter(
        Place.latitude.isnot(None),
        Place.longitude.isnot(None),
        Place.category_id.in_(hotel_cat_ids)
    ).all()

    if exclude_id:
        candidates = [p for p in candidates if p.id != exclude_id]

    with_dist = [(p, haversine(user_lat, user_lng, p.latitude, p.longitude))
                 for p in candidates]
    with_dist.sort(key=lambda x: x[1])
    nearby = [(p, round(d, 1)) for p, d in with_dist if d <= 100][:6]

    result = []
    for p, dist in nearby:
        result.append({
            'id': p.id,
            'name': p.name,
            'location': p.location,
            'image_url': p.primary_image or '',
            'avg_rating': p.avg_rating,
            'dist': dist,
            'category': p.category.name if p.category else '',
        })
    return jsonify(result)

# ── Map ───────────────────────────────────────────────────────────────────────
@places.route('/map')
def map_view():
    focus_id = request.args.get('id', type=int)
    return render_template('places/map.html', focus_id=focus_id)


@places.route('/api/places')
def api_places():
    result = []
    for p in Place.query.filter(Place.latitude.isnot(None)).all():
        result.append({
            'id': p.id, 'name': p.name, 'location': p.location,
            'image_url': p.primary_image or '',
            'latitude': p.latitude, 'longitude': p.longitude,
            'avg_rating': p.avg_rating,
        })
    return jsonify(result)


# ── Image Proxy (แก้ปัญหา hotlink block) ─────────────────────────────────────
import requests as http
from flask import Response

@places.route('/proxy-image')
def proxy_image():
    import re
    url = request.args.get('url', '')
    if not url:
        return '', 400

    # แปลง Google Drive URL อัตโนมัติถ้ายังไม่ได้แปลง
    match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
    if match:
        url = f'https://drive.google.com/uc?export=view&id={match.group(1)}'

    try:
        resp = http.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://drive.google.com/',
        }, timeout=15, allow_redirects=True)
        content_type = resp.headers.get('Content-Type', 'image/jpeg')
        # ถ้า Google Drive redirect ไปหน้า confirm ให้ดึง confirm link
        if 'text/html' in content_type and 'drive.google.com' in url:
            confirm = re.search(r'href="(/uc[?]export=download[^"]+)"', resp.text)
            if confirm:
                confirm_url = 'https://drive.google.com' + confirm.group(1).replace('&amp;', '&')
                resp = http.get(confirm_url, headers={
                    'User-Agent': 'Mozilla/5.0',
                    'Referer': 'https://drive.google.com/',
                }, timeout=15)
                content_type = resp.headers.get('Content-Type', 'image/jpeg')
        return Response(resp.content, content_type=content_type,
                       headers={'Cache-Control': 'public, max-age=3600'})
    except Exception:
        return '', 404


# ── Tile Proxy (แก้ปัญหา OpenStreetMap บล็อก Referer) ──────────────────────
@places.route('/tile/<int:z>/<int:x>/<int:y>.png')
def tile_proxy(z, x, y):
    """Flask ไปดึง tile จาก OSM แทนเบราว์เซอร์ → ไม่ถูกบล็อก"""
    url = f'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
    try:
        resp = http.get(url, headers={
            'User-Agent': 'TravelApp/1.0 (educational project)',
            'Referer': 'https://www.openstreetmap.org/',
        }, timeout=10)
        return Response(
            resp.content,
            content_type=resp.headers.get('Content-Type', 'image/png'),
            headers={'Cache-Control': 'public, max-age=86400'}  # cache 1 วัน
        )
    except Exception:
        return '', 404
