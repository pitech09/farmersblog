import os
from dotenv import load_dotenv

load_dotenv()


class BaseConfig:
    """Base application configuration with security hardening."""
    # SECRET_KEY must be set via environment variable in production
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY:
        import secrets
        if os.getenv('FLASK_ENV') == 'production':
            raise ValueError("SECRET_KEY environment variable must be set in production!")
        SECRET_KEY = secrets.token_hex(32)
        print("WARNING: Using auto-generated SECRET_KEY. Set SECRET_KEY env var in production!")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Security: Limit upload size to 50MB
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 50 * 1024 * 1024))
    
    # Allowed extensions
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'mov'}
    
    # Session Security Settings
    SESSION_COOKIE_HTTPONLY = True  # Prevent JS access
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
    
    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    
    # Cloudinary settings (disabled by default, enable via env var)
    CLOUDINARY_ENABLED = os.getenv('CLOUDINARY_ENABLED', 'false').lower() == 'true'
    CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME', '')
    CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY', '')
    CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET', '')
    
    # Media URL helper
    @property
    def MEDIA_URL(self):
        """Return base URL for media serving."""
        return '/uploads'


class DevConfig(BaseConfig):
    """Development configuration with local storage."""
    DEBUG = True
    
    # SQLite database in instance folder
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///farmersblog_dev.db')
    
    # Local upload folder
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'app/instance/uploads')
    
    # Simple in-memory cache for development
    CACHE_TYPE = os.getenv('CACHE_TYPE', 'SimpleCache')
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Rate limiting with in-memory storage
    RATELIMIT_STORAGE_URI = os.getenv('RATELIMIT_STORAGE_URI', 'memory://')
    
    # Session cookies (no HTTPS requirement in dev)
    SESSION_COOKIE_SECURE = False
    
    # Security headers (less strict for dev)
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
    }


class ProdConfig(BaseConfig):
    """Production configuration with PostgreSQL, Cloudinary, and Redis."""
    DEBUG = False
    
    # PostgreSQL database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', '')
    
    # Cloudinary enabled in production (overrides BaseConfig default)
    CLOUDINARY_ENABLED = True
    
    # Redis for caching and rate limiting
    REDIS_URL = os.getenv('REDIS_URL', '')
    
    CACHE_TYPE = 'RedisCache'
    CACHE_REDIS_URL = REDIS_URL
    CACHE_DEFAULT_TIMEOUT = 600
    
    RATELIMIT_STORAGE_URI = REDIS_URL
    
    # Secure cookies in production
    SESSION_COOKIE_SECURE = True
    
    # Strict security headers for production
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://res.cloudinary.com; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://res.cloudinary.com; media-src 'self' https://res.cloudinary.com; font-src 'self' https://cdn.jsdelivr.net; connect-src 'self'; frame-ancestors 'none';",
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
    }


def get_config():
    """Return configuration class based on FLASK_ENV."""
    env = os.getenv('FLASK_ENV', 'development').lower()
    if env == 'production':
        # Validate production settings
        config = ProdConfig
        missing = []
        if not os.getenv('DATABASE_URL'):
            missing.append('DATABASE_URL')
        if not all([os.getenv('CLOUDINARY_CLOUD_NAME'), os.getenv('CLOUDINARY_API_KEY'), os.getenv('CLOUDINARY_API_SECRET')]):
            missing.append('Cloudinary credentials (CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET)')
        if not os.getenv('REDIS_URL'):
            missing.append('REDIS_URL')
        if missing:
            raise ValueError(f"Production environment requires: {', '.join(missing)}")
        return config
    return DevConfig
