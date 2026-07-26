from functools import wraps
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import User, Post, Comment, Message, Listing, Group, Notification, post_likes, group_members

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """Decorator to restrict access to admin users only."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('You do not have permission to access the admin panel.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/')
@admin_required
def dashboard():
    """Admin dashboard home with site statistics."""
    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)
    twenty_four_hours_ago = now - timedelta(hours=24)

    stats = {
        'total_users': User.query.count(),
        'total_posts': Post.query.count(),
        'total_comments': Comment.query.count(),
        'total_messages': Message.query.count(),
        'total_listings': Listing.query.count(),
        'active_listings': Listing.query.filter_by(is_sold=False).count(),
        'sold_listings': Listing.query.filter_by(is_sold=True).count(),
        'total_groups': Group.query.count(),
        'new_users_7d': User.query.filter(User.created_at >= seven_days_ago).count(),
        'new_posts_24h': Post.query.filter(Post.created_at >= twenty_four_hours_ago).count(),
    }

    return render_template('admin/dashboard.html', stats=stats)


@admin_bp.route('/users')
@admin_required
def users():
    """Paginated user management."""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search = request.args.get('search', '').strip()

    query = User.query
    if search:
        query = query.filter(
            db.or_(
                User.username.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%')
            )
        )

    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    users_list = pagination.items

    return render_template('admin/users.html', users=users_list, pagination=pagination, search=search)


@admin_bp.route('/users/<int:user_id>/toggle-admin', methods=['POST'])
@admin_required
def toggle_admin(user_id):
    """Promote or demote a user as admin."""
    user = User.query.get_or_404(user_id)

    # Prevent self-demotion
    if user.id == current_user.id:
        flash('You cannot change your own admin status.', 'danger')
        return redirect(url_for('admin.users'))

    user.is_admin = not user.is_admin
    db.session.commit()
    status = 'promoted to' if user.is_admin else 'demoted from'
    flash(f'User {user.username} {status} admin.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete a user and all associated content."""
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash('You cannot delete your own account from the admin panel.', 'danger')
        return redirect(url_for('admin.users'))

    username = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f'User {username} and all associated content deleted.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/posts')
@admin_required
def posts():
    """Paginated post management."""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    sort = request.args.get('sort', 'newest')

    query = Post.query

    if sort == 'most_liked':
        # Get all posts ordered by like count (requires subquery)
        from sqlalchemy import func, desc
        like_counts = db.session.query(
            post_likes.c.post_id,
            func.count(post_likes.c.user_id).label('cnt')
        ).group_by(post_likes.c.post_id).subquery()
        query = query.outerjoin(
            like_counts, Post.id == like_counts.c.post_id
        ).order_by(desc(like_counts.c.cnt)).order_by(Post.created_at.desc())
    elif sort == 'most_commented':
        from sqlalchemy import func, desc
        comment_counts = db.session.query(
            Comment.post_id,
            func.count(Comment.id).label('cnt')
        ).group_by(Comment.post_id).subquery()
        query = query.outerjoin(
            comment_counts, Post.id == comment_counts.c.post_id
        ).order_by(desc(comment_counts.c.cnt)).order_by(Post.created_at.desc())
    else:
        query = query.order_by(Post.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    posts_list = pagination.items

    return render_template('admin/posts.html', posts=posts_list, pagination=pagination, sort=sort)


@admin_bp.route('/posts/<int:post_id>/delete', methods=['POST'])
@admin_required
def delete_post(post_id):
    """Delete a post."""
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash('Post deleted successfully.', 'success')
    return redirect(url_for('admin.posts'))


@admin_bp.route('/listings')
@admin_required
def listings():
    """Paginated marketplace listing management."""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    pagination = Listing.query.order_by(Listing.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    listings_list = pagination.items

    return render_template('admin/listings.html', listings=listings_list, pagination=pagination)


@admin_bp.route('/listings/<int:listing_id>/toggle-sold', methods=['POST'])
@admin_required
def toggle_listing_sold(listing_id):
    """Toggle a listing's sold status."""
    listing = Listing.query.get_or_404(listing_id)
    listing.is_sold = not listing.is_sold
    db.session.commit()
    status = 'marked as sold' if listing.is_sold else 'marked as active'
    flash(f'Listing "{listing.title}" {status}.', 'success')
    return redirect(url_for('admin.listings'))


@admin_bp.route('/listings/<int:listing_id>/delete', methods=['POST'])
@admin_required
def delete_listing(listing_id):
    """Delete a marketplace listing."""
    listing = Listing.query.get_or_404(listing_id)
    db.session.delete(listing)
    db.session.commit()
    flash('Listing deleted successfully.', 'success')
    return redirect(url_for('admin.listings'))


@admin_bp.route('/groups')
@admin_required
def groups():
    """Paginated group management."""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    pagination = Group.query.order_by(Group.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    groups_list = pagination.items

    return render_template('admin/groups.html', groups=groups_list, pagination=pagination)


@admin_bp.route('/groups/<int:group_id>/delete', methods=['POST'])
@admin_required
def delete_group(group_id):
    """Delete a group."""
    group = Group.query.get_or_404(group_id)
    db.session.delete(group)
    db.session.commit()
    flash('Group deleted successfully.', 'success')
    return redirect(url_for('admin.groups'))


@admin_bp.route('/groups/<int:group_id>/members')
@admin_required
def group_members(group_id):
    """View members of a group."""
    group = Group.query.get_or_404(group_id)
    members = group.members.order_by(User.username).all()
    return render_template('admin/group_members.html', group=group, members=members)