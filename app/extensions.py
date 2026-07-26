from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from flask_caching import Cache

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

# Rate limiter (disabled - set to extremely high limits)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100000 per minute"],
    storage_uri="memory://"
)

# CSRF Protection
csrf = CSRFProtect()

# Caching
cache = Cache()

def init_extensions(app):
    """Initialize all extensions with the app."""
    db.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    
    # Enable CSRF protection in production
    if app.config.get('WTF_CSRF_ENABLED'):
        csrf.init_app(app)
    
    # Initialize caching
    cache.init_app(app)
    
    # Add security headers
    @app.after_request
    def add_security_headers(response):
        headers = app.config.get('SECURITY_HEADERS', {})
        for header, value in headers.items():
            if value:
                response.headers[header] = value
        return response
