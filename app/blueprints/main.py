import os
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, abort, send_from_directory, current_app, flash, Response
from flask_login import current_user
from app.extensions import db, cache
from app.models import Post, Comment, User, Media, followers, post_likes

main_bp = Blueprint('main', __name__)


def calculate_post_score(post, current_user):
    """
    Calculate a relevance score for a post for the current user.
    Higher score = more relevant.
    """
    score = 0
    
    now = datetime.utcnow()
    hours_old = (now - post.created_at).total_seconds() / 3600.0
    recency_score = max(0, 100 - hours_old)  # 100 for new, decays to 0 over ~100 hours
    score += recency_score

    engagement_score = (post.like_count * 2) + (post.comment_count * 3)
    score += engagement_score

    followed_users = [u.id for u in current_user.followed.all()]
    if post.author_id in followed_users:
        score += 50

    if post.group_id:
        group = post.group
        if group and group.is_member(current_user):
            score += 20

    if current_user.location and post.author.location:
        if current_user.location.strip().lower() == post.author.location.strip().lower():
            score += 10

    if post.media_count > 0:
        score += 5

    if current_user.is_authenticated:
        has_interacted = post.likes.filter(
            post_likes.c.user_id == current_user.id
        ).count() > 0
        if has_interacted:
            score += 15

    return score


def invalidate_for_you_cache(user_id):
    """Invalidate the For You cache for a user."""
    cache_key = f"for_you_feed_{user_id}"
    cache.delete(cache_key)


@main_bp.route('/')
def index():
    feed_type = request.args.get('feed', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Default to 'for_you' for logged-in users
    if not current_user.is_authenticated and feed_type == 'for_you':
        feed_type = 'all'

    message = None
    if feed_type == 'following' and current_user.is_authenticated:
        followed_ids = [u.id for u in current_user.followed.all()]
        if followed_ids:
            pagination = Post.query.filter(
                Post.author_id.in_(followed_ids),
                Post.group_id.is_(None)
            ).order_by(Post.created_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
        else:
            pagination = Post.query.filter(False).paginate(page=page, per_page=per_page, error_out=False)

    elif feed_type == 'for_you' and current_user.is_authenticated:
        cache_key = f"for_you_feed_{current_user.id}"
        cached = cache.get(cache_key)
        if cached:
            posts = cached
        else:
            followed_ids = [u.id for u in current_user.followed.all()]
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)

            query = Post.query.filter(
                Post.group_id.is_(None),
                Post.created_at >= thirty_days_ago
            )
            posts_query = query.all()

            scored_posts = []
            for post in posts_query:
                score = calculate_post_score(post, current_user)
                if score > 0:
                    scored_posts.append((score, post.created_at, post))

            scored_posts.sort(key=lambda x: (-x[0], -x[1].timestamp()))
            posts = [item[2] for item in scored_posts]
            cache.set(cache_key, posts, timeout=300)

            class MockPagination:
                def __init__(self, items, page, per_page):
                    self.items = items[(page-1)*per_page : page*per_page]
                    self.has_prev = page > 1
                    self.has_next = (page * per_page) < len(items)
                    self.prev_num = page - 1 if page > 1 else None
                    self.next_num = page + 1 if (page * per_page) < len(items) else None
                    self.total = len(items)
                    self.page = page
                    self.pages = (len(items) + per_page - 1) // per_page
            pagination = MockPagination(posts, page, per_page)

        if 'pagination' not in locals():
            class MockPagination:
                def __init__(self, items, page, per_page):
                    self.items = items[(page-1)*per_page : page*per_page]
                    self.has_prev = page > 1
                    self.has_next = (page * per_page) < len(items)
                    self.prev_num = page - 1 if page > 1 else None
                    self.next_num = page + 1 if (page * per_page) < len(items) else None
                    self.total = len(items)
                    self.page = page
                    self.pages = (len(items) + per_page - 1) // per_page
            pagination = MockPagination(posts, page, per_page)
        current_items = pagination.items

    else:
        pagination = Post.query.filter(Post.group_id.is_(None)).order_by(
            Post.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        current_items = pagination.items

    if feed_type == 'for_you' and current_user.is_authenticated and not current_items:
        message = "No posts to show yet. Follow more farmers or check out the 'All Posts' tab."
    for post in current_items:
        post.user_has_liked = post.is_liked_by(current_user)

    if message and not current_items:
        flash(message, 'info')

    return render_template(
        'index.html',
        posts=current_items,
        pagination=pagination,
        feed_type=feed_type
    )


@main_bp.route('/robots.txt')
def robots_txt():
    base_url = request.url_root.rstrip('/')
    content = f"""User-agent: *
Allow: /
Disallow: /admin
Disallow: /messages
Disallow: /settings
Sitemap: {base_url}/sitemap.xml
"""
    return Response(content, mimetype='text/plain')


@main_bp.route('/post/<int:post_id>')
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    post.user_has_liked = post.is_liked_by(current_user)
    comments = post.comments.order_by(Comment.created_at.asc()).all()
    all_media = post.media.order_by(Media.position).all()

    return render_template('post_detail.html', post=post, comments=comments, all_media=all_media)


@main_bp.route('/sitemap.xml')
def sitemap_xml():
    from app.extensions import db
    from app.models import User, Post, Listing, Group
    base_url = request.url_root.rstrip('/')

    urls = [base_url]

    users = User.query.filter_by(is_admin=False).all()
    for user in users:
        urls.append(f"{base_url}/user/{user.username}")

    posts = Post.query.filter(Post.group_id.is_(None)).all()
    for post in posts:
        urls.append(f"{base_url}/post/{post.id}")

    listings = Listing.query.filter_by(is_sold=False).all()
    for listing in listings:
        urls.append(f"{base_url}/marketplace/{listing.id}")

    groups = Group.query.all()
    for group in groups:
        urls.append(f"{base_url}/groups/{group.name}")

    xml = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for url in urls:
        xml.append('<url>')
        xml.append(f'<loc>{url}</loc>')
        xml.append('<changefreq>daily</changefreq>')
        xml.append('<priority>0.8</priority>')
        xml.append('</url>')
    xml.append('</urlset>')
    return Response('\n'.join(xml), mimetype='application/xml')
