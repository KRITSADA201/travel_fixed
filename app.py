from flask import Flask
from config import Config
from extensions import db, bcrypt, login_manager
from models import User


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # init extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # register blueprints
    from blueprints.auth     import auth
    from blueprints.places   import places
    from blueprints.admin_bp import admin_bp
    from blueprints.user_bp  import user_bp

    app.register_blueprint(auth)       # /auth/...
    app.register_blueprint(places)     # /, /places, /place/...
    app.register_blueprint(admin_bp)   # /admin/...
    app.register_blueprint(user_bp)    # /user/...

    # template filter แปลง URL รูปเป็น proxy
    @app.template_filter('proxy_url')
    def proxy_url_filter(url):
        if not url:
            return ''
        import re
        from urllib.parse import quote

        # แปลง Google Drive URL อัตโนมัติ
        # รูปแบบ: /file/d/ID/view หรือ /file/d/ID
        match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
        if match:
            file_id = match.group(1)
            url = f'https://drive.google.com/uc?export=view&id={file_id}'

        # รูปแบบ: /open?id=ID
        match2 = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', url)
        if 'drive.google.com/open' in url and match2:
            file_id = match2.group(1)
            url = f'https://drive.google.com/uc?export=view&id={file_id}'

        # ส่งผ่าน proxy ถ้าเป็น Google Drive หรือ OneDrive
        if 'drive.google.com' in url or '1drv.ms' in url or 'onedrive' in url:
            return f'/proxy-image?url={quote(url)}'

        return url

    return app


app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        # สร้าง admin อัตโนมัติถ้ายังไม่มี
        from extensions import bcrypt as bc
        from models import User, Category
        if not User.query.filter_by(username='admin').first():
            admin_user = User(
                username='admin',
                password=bc.generate_password_hash('admin123').decode(),
                is_admin=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print('✅ admin created  |  username: admin  |  password: admin123')

        # สร้างหมวดหมู่ถ้ายังไม่มี
        if Category.query.count() == 0:
            for name in ['ธรรมชาติ', 'คาเฟ่', 'วัด']:
                db.session.add(Category(name=name))
            db.session.commit()
            print('✅ categories created')

    app.run(debug=True)
