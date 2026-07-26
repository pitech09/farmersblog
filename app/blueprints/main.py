import os
from flask import Blueprint, render_template, request, abort, send_from_directory, current_app
from flask_login import current_user
from app.extensions import cache
from app.models import Post, Comment, User, Media

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    feed_type = request.args.get('feed', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = 10

    if feed_type == 'following' and current_user.is_authenticated:
        # Get posts from users the current user follows
        followed_ids = [u.id for u in current_user.followed.all()]
        if followed_ids:
            pagination = Post.query.filter(
                Post.author_id.in_(followed_ids),
                Post.group_id.is_(None)  # Only public posts
            ).order_by(Post.created_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
        else:
            pagination = Post.query.filter(False).paginate(page=page, per_page=per_page, error_out=False)
    else:
        # All public posts (no group_id)
        pagination = Post.query.filter(Post.group_id.is_(None)).order_by(
            Post.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)

    posts = pagination.items

    # Attach like status for current user
    for post in posts:
        post.user_has_liked = post.is_liked_by(current_user)

    return render_template('index.html', posts=posts, pagination=pagination, feed_type=feed_type)


@main_bp.route('/post/<int:post_id>')
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    post.user_has_liked = post.is_liked_by(current_user)
    comments = post.comments.order_by(Comment.created_at.asc()).all()
    all_media = post.media.order_by(Media.position).all()

    return render_template('post_detail.html', post=post, comments=comments, all_media=all_media)


@main_bp.route('/uploads/<path:filename>')
def serve_upload(filename):
    """Serve uploaded media files in development mode."""
    # Prevent directory traversal
    if '..' in filename or filename.startswith('/'):
        abort(404)

    upload_folder = current_app.config['UPLOAD_FOLDER']
    file_path = os.path.join(upload_folder, filename)

    if not os.path.exists(file_path):
        abort(404)

    return send_from_directory(upload_folder, filename)