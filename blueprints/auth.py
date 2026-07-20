import secrets
import requests as http
from urllib.parse import urlencode
from flask import Blueprint, render_template, redirect, url_for, request, session, current_app
from flask_login import login_user, logout_user, login_required
from extensions import db, bcrypt
from models import User

auth = Blueprint('auth', __name__, url_prefix='/auth')


def _get_or_create_user(username, email=None):
    user = User.query.filter_by(email=email).first() if email else None
    if not user:
        base = username.replace(' ', '_')
        uname = base
        i = 1
        while User.query.filter_by(username=uname).first():
            uname = f"{base}_{i}"; i += 1
        pw = bcrypt.generate_password_hash(secrets.token_hex(16)).decode()
        user = User(username=uname, email=email, password=pw)
        db.session.add(user)
        db.session.commit()
    return user


@auth.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        email    = request.form.get('email',  '').strip() or None
        phone    = request.form.get('phone',  '').strip() or None
        if User.query.filter_by(username=username).first():
            error = 'ชื่อผู้ใช้นี้มีแล้ว'
        elif email and User.query.filter_by(email=email).first():
            error = 'อีเมลนี้ถูกใช้แล้ว'
        elif phone and User.query.filter_by(phone=phone).first():
            error = 'เบอร์โทรนี้ถูกใช้แล้ว'
        else:
            pw   = bcrypt.generate_password_hash(request.form['password']).decode()
            user = User(username=username, password=pw, email=email, phone=phone)
            db.session.add(user); db.session.commit()
            return redirect(url_for('auth.login'))
    return render_template('auth/register.html', error=error)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        ident = request.form['identifier'].strip()
        pw    = request.form['password']
        user  = (User.query.filter_by(username=ident).first() or
                 User.query.filter_by(email=ident).first()    or
                 User.query.filter_by(phone=ident).first())
        if user is None:
            error = 'ไม่พบชื่อผู้ใช้ อีเมล หรือเบอร์โทรนี้ในระบบ'
        elif not bcrypt.check_password_hash(user.password, pw):
            error = 'รหัสผ่านไม่ถูกต้อง'
        else:
            login_user(user)
            return redirect(url_for('places.home'))
    return render_template('auth/login.html', error=error)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('places.home'))


# ── Google ──
@auth.route('/google')
def google_login():
    state = secrets.token_urlsafe(16)
    session['oauth_state'] = state
    cfg = current_app.config
    params = dict(client_id=cfg['GOOGLE_CLIENT_ID'], redirect_uri=cfg['GOOGLE_REDIRECT_URI'],
                  response_type='code', scope='openid email profile', state=state)
    return redirect('https://accounts.google.com/o/oauth2/v2/auth?' + urlencode(params))

@auth.route('/google/callback')
def google_callback():
    cfg  = current_app.config
    code = request.args.get('code')
    if not code: return redirect(url_for('auth.login'))
    tok  = http.post('https://oauth2.googleapis.com/token', data=dict(
        code=code, client_id=cfg['GOOGLE_CLIENT_ID'],
        client_secret=cfg['GOOGLE_CLIENT_SECRET'],
        redirect_uri=cfg['GOOGLE_REDIRECT_URI'], grant_type='authorization_code')).json()
    token = tok.get('access_token')
    if not token: return redirect(url_for('auth.login'))
    info  = http.get('https://www.googleapis.com/oauth2/v2/userinfo',
                     headers={'Authorization': f'Bearer {token}'}).json()
    email = info.get('email')
    name  = info.get('name') or (email.split('@')[0] if email else 'google_user')
    login_user(_get_or_create_user(name, email=email))
    return redirect(url_for('places.home'))


# ── LINE ──
@auth.route('/line')
def line_login():
    state = secrets.token_urlsafe(16)
    session['oauth_state'] = state
    cfg = current_app.config
    params = dict(response_type='code', client_id=cfg['LINE_CHANNEL_ID'],
                  redirect_uri=cfg['LINE_REDIRECT_URI'], state=state, scope='profile openid email')
    return redirect('https://access.line.me/oauth2/v2.1/authorize?' + urlencode(params))

@auth.route('/line/callback')
def line_callback():
    cfg  = current_app.config
    code = request.args.get('code')
    if not code: return redirect(url_for('auth.login'))
    tok  = http.post('https://api.line.me/oauth2/v2.1/token', data=dict(
        grant_type='authorization_code', code=code,
        redirect_uri=cfg['LINE_REDIRECT_URI'],
        client_id=cfg['LINE_CHANNEL_ID'], client_secret=cfg['LINE_CHANNEL_SECRET'])).json()
    token = tok.get('access_token')
    if not token: return redirect(url_for('auth.login'))
    profile = http.get('https://api.line.me/v2/profile',
                       headers={'Authorization': f'Bearer {token}'}).json()
    login_user(_get_or_create_user(profile.get('displayName', 'LINE_User')))
    return redirect(url_for('places.home'))


# ── Facebook ──
@auth.route('/facebook')
def facebook_login():
    state = secrets.token_urlsafe(16)
    session['oauth_state'] = state
    cfg = current_app.config
    params = dict(client_id=cfg['FB_APP_ID'], redirect_uri=cfg['FB_REDIRECT_URI'],
                  state=state, scope='email,public_profile')
    return redirect('https://www.facebook.com/v18.0/dialog/oauth?' + urlencode(params))

@auth.route('/facebook/callback')
def facebook_callback():
    cfg  = current_app.config
    code = request.args.get('code')
    if not code: return redirect(url_for('auth.login'))
    tok  = http.get('https://graph.facebook.com/v18.0/oauth/access_token', params=dict(
        client_id=cfg['FB_APP_ID'], client_secret=cfg['FB_APP_SECRET'],
        redirect_uri=cfg['FB_REDIRECT_URI'], code=code)).json()
    token = tok.get('access_token')
    if not token: return redirect(url_for('auth.login'))
    info  = http.get('https://graph.facebook.com/me',
                     params=dict(fields='id,name,email', access_token=token)).json()
    login_user(_get_or_create_user(info.get('name', 'FB_User'), email=info.get('email')))
    return redirect(url_for('places.home'))
