import os
import uuid
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.forms import ProfileForm, AccountForm
from app.extensions import db, cache
from app.models import User, Post, Notification
from app.helpers import get_avatar_url, upload_to_cloudinary

profile_bp = Blueprint('profile', __name__)


def allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


@profile_bp.route('/<username>')
@cache.cached(timeout=300, query_string=True)
def public_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    per_page = 12

    pagination = Post.query.filter_by(author_id=user.id).order_by(Post.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
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

    is_following = current_user.is_following(user)

    if is_following:
        current_user.unfollow(user)
        following = False
    else:
        current_user.follow(user)
        following = True
        notification = Notification(
            recipient_id=user.id,
            actor_id=current_user.id,
            type='follow',
            message=f'{current_user.username} started following you',
            link=url_for('profile.public_profile', username=current_user.username)
        )
        db.session.add(notification)
        db.session.commit()

    return jsonify({
        'following': following,
        'follower_count': user.follower_count
    })


@profile_bp.route('/settings/profile', methods=['GET', 'POST'])
@login_required
def settings():
    profile_form = ProfileForm(current_user_id=current_user.id)
    account_form = AccountForm()
    if request.method == 'GET':
        profile_form.username.data = current_user.username
        profile_form.bio.data = current_user.bio or ''
        profile_form.location.data = current_user.location or ''
        account_form.email.data = current_user.email or ''
    if request.method == 'POST':
        if 'submit' in request.form and profile_form.validate():
            current_user.username = profile_form.username.data.strip()
            current_user.bio = (profile_form.bio.data or '')[:300]
            current_user.location = (profile_form.location.data or '')[:120]
            file = profile_form.avatar.data
            if file and file.filename:
                if allowed_image(file.filename):
                    ext = file.filename.rsplit('.', 1)[1].lower()
                    unique_name = f"avatar_{uuid.uuid4().hex}.{ext}"
                    if current_app.config.get('CLOUDINARY_ENABLED'):
                        public_id = upload_to_cloudinary(file, resource_type='image')
                        if not public_id:
                            flash('Failed to upload avatar to cloud storage.', 'danger')
                            return render_template('profile/settings.html', profile_form=profile_form, account_form=account_form)
                        current_user.avatar_filename = public_id
                    else:
                        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'avatars')
                        os.makedirs(upload_path, exist_ok=True)
                        file.save(os.path.join(upload_path, unique_name))
                        current_user.avatar_filename = f"avatars/{unique_name}"
                else:
                    flash('Invalid avatar file type. Allowed: png, jpg, jpeg, gif', 'danger')
                    return render_template('profile/settings.html', profile_form=profile_form, account_form=account_form)
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile.public_profile', username=current_user.username))
        elif 'save' in request.form and account_form.validate():
            current_user.email = account_form.email.data.strip()
            if account_form.new_password.data:
                if not account_form.current_password.data:
                    flash('Current password is required to set a new password.', 'danger')
                    return render_template('profile/settings.html', profile_form=profile_form, account_form=account_form)
                if not current_user.check_password(account_form.current_password.data):
                    flash('Current password is incorrect.', 'danger')
                    return render_template('profile/settings.html', profile_form=profile_form, account_form=account_form)
                current_user.set_password(account_form.new_password.data)
            db.session.commit()
            flash('Account settings updated successfully!', 'success')
            return redirect(url_for('profile.public_profile', username=current_user.username))
    return render_template('profile/settings.html', profile_form=profile_form, account_form=account_form)


@profile_bp.route('/settings/account', methods=['GET', 'POST'])
@login_required
def account():
    form = AccountForm()
    if request.method == 'GET':
        form.email.data = current_user.email or ''
    if form.validate_on_submit():
        current_user.email = form.email.data.strip()
        if form.new_password.data:
            if not form.current_password.data:
                flash('Current password is required to set a new password.', 'danger')
                return render_template('profile/account.html', form=form)
            if not current_user.check_password(form.current_password.data):
                flash('Current password is incorrect.', 'danger')
                return render_template('profile/account.html', form=form)
            current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Account settings updated successfully!', 'success')
        return redirect(url_for('profile.public_profile', username=current_user.username))
    return render_template('profile/account.html', form=form)