import os
from dotenv import load_dotenv

load_dotenv()

# สร้างโฟลเดอร์ instance อัตโนมัติถ้ายังไม่มี
_base     = os.path.abspath(os.path.dirname(__file__))
_instance = os.path.join(_base, 'instance')
os.makedirs(_instance, exist_ok=True)

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'secret123')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(_instance, 'site.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Google OAuth
    GOOGLE_CLIENT_ID     = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_REDIRECT_URI  = os.getenv('GOOGLE_REDIRECT_URI', 'http://127.0.0.1:5000/auth/google/callback')

    # LINE OAuth
    LINE_CHANNEL_ID      = os.getenv('LINE_CHANNEL_ID')
    LINE_CHANNEL_SECRET  = os.getenv('LINE_CHANNEL_SECRET')
    LINE_REDIRECT_URI    = os.getenv('LINE_REDIRECT_URI', 'http://127.0.0.1:5000/auth/line/callback')

    # Facebook OAuth
    FB_APP_ID            = os.getenv('FB_APP_ID')
    FB_APP_SECRET        = os.getenv('FB_APP_SECRET')
    FB_REDIRECT_URI      = os.getenv('FB_REDIRECT_URI', 'http://127.0.0.1:5000/auth/facebook/callback')
