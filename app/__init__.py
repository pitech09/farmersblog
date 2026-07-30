import os
import traceback
from flask import Flask, render_template
from app.config import get_config
from app.extensions import db, login_manager, limiter, csrf, cache
from flask_migrate import Migrate


def create_app(config_class=None):
    """Application factory with security hardening and environment-based configuration."""
    if config_class is None:
        config_class = get_config()
    
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure upload directories exist (only in development)
    if not app.config.get('CLOUDINARY_ENABLED'):
        base_upload = app.config['UPLOAD_FOLDER']
        if not os.path.isabs(base_upload):
            base_upload = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', base_upload)
        app.config['UPLOAD_FOLDER'] = base_upload

        posts_dir = os.path.join(base_upload, 'posts')
        avatars_dir = os.path.join(base_upload, 'avatars')
        marketplace_dir = os.path.join(base_upload, 'marketplace')
        os.makedirs(posts_dir, exist_ok=True)
        os.makedirs(avatars_dir, exist_ok=True)
        os.makedirs(marketplace_dir, exist_ok=True)
    
    # Create instance directory if using instance folder
    instance_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'instance')
    os.makedirs(instance_dir, exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    
    # Initialize rate limiter
    limiter.init_app(app)
    
    # Initialize CSRF protection
    if app.config.get('WTF_CSRF_ENABLED'):
        csrf.init_app(app)
    
    # Initialize Flask-Caching
    cache.init_app(app)
    
    # Initialize Flask-Migrate for database migrations
    migrate = Migrate(app, db)
    
    # Initialize Cloudinary (production only)
    if app.config.get('CLOUDINARY_ENABLED'):
        try:
            import cloudinary
            cloudinary.config(
                cloud_name=app.config['CLOUDINARY_CLOUD_NAME'],
                api_key=app.config['CLOUDINARY_API_KEY'],
                api_secret=app.config['CLOUDINARY_API_SECRET']
            )
            app.logger.info("Cloudinary initialized successfully")
        except Exception as e:
            app.logger.error(f"Failed to initialize Cloudinary: {e}")
    
    # Register blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.main import main_bp
    from app.blueprints.posts import posts_bp
    from app.blueprints.profile import profile_bp
    from app.blueprints.messages import messages_bp
    from app.blueprints.groups import groups_bp
    from app.blueprints.marketplace import marketplace_bp
    from app.blueprints.notifications import notifications_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.search import search_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(posts_bp, url_prefix='/posts')
    app.register_blueprint(profile_bp, url_prefix='/user')
    app.register_blueprint(messages_bp, url_prefix='/messages')
    app.register_blueprint(groups_bp, url_prefix='/groups')
    app.register_blueprint(marketplace_bp, url_prefix='/marketplace')
    app.register_blueprint(notifications_bp)
    app.register_blueprint(admin_bp)

    # Context processor for unread messages, notifications count, and recent notifications
    @app.context_processor
    def inject_unread_count():
        from flask_login import current_user
        if current_user.is_authenticated:
            from app.models import User, Notification
            user = User.query.get(current_user.id)
            recent_notifications = Notification.query.filter_by(
                recipient_id=current_user.id
            ).order_by(Notification.created_at.desc()).limit(5).all()
            return {
                'unread_count': user.unread_message_count,
                'notification_unread_count': Notification.query.filter_by(
                    recipient_id=current_user.id, read=False
                ).count(),
                'notifications': recent_notifications
            }
        return {'unread_count': 0, 'notification_unread_count': 0, 'notifications': []}
    
    
    # CSRF token context processor - provides raw token value for meta tag and AJAX
    @app.context_processor
    def inject_csrf_token():
        from flask_wtf.csrf import generate_csrf
        return dict(csrf_token=generate_csrf)

    # Media URL context processor and template filter
    @app.context_processor
    def inject_media_helpers():
        from app.helpers import get_media_url, get_avatar_url
        return dict(media_url=get_media_url, avatar_url=get_avatar_url)
    
    @app.template_filter('media_url')
    def media_url_filter(filename):
        from app.helpers import get_media_url
        return get_media_url(filename)

    # Apply security headers
    @app.after_request
    def apply_security_headers(response):
        headers = app.config.get('SECURITY_HEADERS', {})
        for header, value in headers.items():
            if value:
                response.headers[header] = value
        return response

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden_error(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error(f'Internal error: {e}\n{traceback.format_exc()}')
        return render_template('errors/500.html'), 500

    # Create tables (safe to call repeatedly - uses IF NOT EXISTS internally)
    with app.app_context():
        db.create_all()

    return app
