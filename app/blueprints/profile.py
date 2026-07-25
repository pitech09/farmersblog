import os
import uuid
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.extensions import db, cache
from app.models import User, Post, Media
from app.helpers import get_avatar_url, upload_to_cloudinary

profile_bp = Blueprint('profile', __name__)


def allowed_image(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


@profile_bp.route('/<username>')
@cache.cached(timeout=300, query_string=True)
def public_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    per_page = 12

    pagination = Post.query.filter_by(author_id=user.id).order_by(
        Post.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    posts = pagination.items

    for post in posts:
        post.user_has_liked = post.is_liked_by(current_user)

    is_following = False
    if current_user.is_authenticated and current_user != user:
        is_following = current_user.is_following(user)

    return render_template('profile/public.html',
                         profile_user=user,
                         posts=posts,
                         pagination=pagination,
                         is_following=is_following)


@profile_bp.route('/<username>/follow', methods=['POST'])
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first_or_404()

    if user == current_user:
        return jsonify({'error': 'You cannot follow yourself.'}), 400

    if current_user.is_following(user):
        current_user.unfollow(user)
        following = False
    else:
        current_user.follow(user)
        following = True

    return jsonify({
        'following': following,
        'follower_count': user.follower_count
    })


@profile_bp.route('/settings/profile', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        bio = request.form.get('bio', '').strip()

        if not username:
            flash('Username is required.', 'danger')
            return render_template('profile/settings.html')

        # Check username uniqueness
        existing = User.query.filter_by(username=username).first()
        if existing and existing.id != current_user.id:
            flash('Username already taken.', 'danger')
            return render_template('profile/settings.html')

        current_user.username = username
        current_user.bio = bio[:300]  # Max 300 chars

        # Handle avatar upload
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file.filename:
                if allowed_image(file.filename):
                    ext = file.filename.rsplit('.', 1)[1].lower()
                    unique_name = f"avatar_{uuid.uuid4().hex}.{ext}"
                    
                    if current_app.config.get('CLOUDINARY_ENABLED'):
                        # Upload to Cloudinary in production
                        public_id = upload_to_cloudinary(file, resource_type='image')
                        if not public_id:
                            flash('Failed to upload avatar to cloud storage.', 'danger')
                            return render_template('profile/settings.html')
                        current_user.avatar_filename = public_id
                    else:
                        # Save locally in development
                        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'avatars')
                        os.makedirs(upload_path, exist_ok=True)
                        file.save(os.path.join(upload_path, unique_name))
                        current_user.avatar_filename = f"avatars/{unique_name}"
                else:
                    flash('Invalid avatar file type. Allowed: png, jpg, jpeg, gif', 'danger')
                    return render_template('profile/settings.html')

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile.public_profile', username=current_user.username))

    return render_template('profile/settings.html')