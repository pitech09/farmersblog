from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app.models import Post, User
from app.extensions import db

search_bp = Blueprint('search', __name__, url_prefix='/search')


@search_bp.route('/posts')
def search_posts():
    """Search public posts by caption text (public, no login required)."""
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 10

    if query:
        pagination = Post.query.filter(
            Post.group_id.is_(None),
            Post.caption.ilike(f'%{query}%')
        ).order_by(Post.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
    else:
        pagination = Post.query.filter(
            Post.group_id.is_(None)
        ).order_by(Post.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

    posts = pagination.items
    for post in posts:
        post.user_has_liked = post.is_liked_by(current_user)

    return render_template('search/posts.html',
                         posts=posts,
                         pagination=pagination,
                         query=query)


@search_bp.route('/users')
@login_required
def search_users():
    """Search for users by username or location (login required redirect handled optionally)."""
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20

    if query:
        pagination = User.query.filter(
            User.id != (current_user.id if current_user.is_authenticated else 0),
            User.is_admin == False,
            (
                User.username.ilike(f'%{query}%') |
                User.location.ilike(f'%{query}%')
            )
        ).order_by(User.username.asc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
    else:
        # Show all users except current, ordered by newest first
        if current_user.is_authenticated:
            pagination = User.query.filter(
                User.id != current_user.id,
                User.is_admin == False
            ).order_by(User.created_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
        else:
            pagination = User.query.filter(
                User.is_admin == False
            ).order_by(
                User.created_at.desc()
            ).paginate(
                page=page, per_page=per_page, error_out=False
            )

    users = pagination.items

    # Attach follow status for current user
    for user in users:
        user.current_user_is_following = (
            current_user.is_following(user) if current_user.is_authenticated else False
        )

    return render_template('search/users.html',
                         users=users,
                         pagination=pagination,
                         query=query)