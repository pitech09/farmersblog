import os
import uuid
import re
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import magic
from app.forms import PostForm
from app.extensions import db, limiter
from app.models import Post, Media, Comment, Group, User, Notification
from app.helpers import get_media_url, upload_to_cloudinary

posts_bp = Blueprint('posts', __name__)


def allowed_file(filename, allowed_extensions=None):
    if allowed_extensions is None:
        allowed_extensions = current_app.config['ALLOWED_EXTENSIONS']
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in allowed_extensions


def get_media_type(filename):
    ext = filename.rsplit('.', 1)[1].lower()
    if ext in current_app.config['ALLOWED_EXTENSIONS']:
        return 'image'
    if ext in current_app.config.get('ALLOWED_VIDEO_EXTENSIONS', {'mp4', 'webm', 'mov'}):
        return 'video'
    return None


def validate_mime_type(file_path, expected_type):
    """Validate file MIME type using python-magic."""
    try:
        mime = magic.Magic(mime=True)
        file_mime = mime.from_file(file_path)
        # from_file returns bytes (e.g. b'image/jpeg'), decode to str for comparison
        if isinstance(file_mime, bytes):
            file_mime = file_mime.decode('utf-8')
        
        if expected_type == 'image':
            return file_mime in ['image/jpeg', 'image/png', 'image/gif', 'image/jpg']
        elif expected_type == 'video':
            return file_mime in ['video/mp4', 'video/webm', 'video/quicktime']
    except Exception:
        # If magic fails, fall back to extension check
        return True
    return False


@posts_bp.route('/create', methods=['GET', 'POST'])
@login_required
@limiter.limit("10 per minute")
def create():
    groups = Group.query.filter(Group.members.any(id=current_user.id)).all()
    preselected_group = request.args.get('group')

    form = PostForm()
    form.group_id.choices = [('', '— Public Feed —')] + [(g.id, g.name) for g in groups]

    if form.validate_on_submit():
        caption = form.caption.data.strip() if form.caption.data else ''
        from bleach import clean
        caption = clean(caption, tags=[], strip=True)[:5000]
        group_id = form.group_id.data or None

        # If posting to a group, verify membership
        if group_id:
            group = Group.query.get_or_404(group_id)
            if not group.has_member(current_user):
                flash('You are not a member of this group.', 'danger')
                return redirect(url_for('main.index'))

        files = request.files.getlist('media')
        # Filter out empty filenames
        files = [f for f in files if f.filename]

        post = Post(
            author_id=current_user.id,
            caption=caption,
            group_id=group_id if group_id else None
        )
        db.session.add(post)
        db.session.flush()

        for idx, file in enumerate(files):
            if file.filename == '':
                continue
                
            ext = file.filename.rsplit('.', 1)[1].lower()
            allowed_exts = current_app.config['ALLOWED_EXTENSIONS'].union(
                current_app.config.get('ALLOWED_VIDEO_EXTENSIONS', {'mp4', 'webm', 'mov'})
            )
            if ext not in allowed_exts:
                flash(f'Invalid file type: .{ext}. Allowed: png, jpg, jpeg, gif, mp4, webm, mov', 'danger')
                db.session.rollback()
                return render_template('posts/create.html', form=form, groups=groups, preselected_group=preselected_group)

            # Check file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            
            if file_size > current_app.config['MAX_CONTENT_LENGTH']:
                flash(f'File too large: {file.filename}. Maximum size is 50MB.', 'danger')
                db.session.rollback()
                return render_template('posts/create.html', form=form, groups=groups, preselected_group=preselected_group)

            media_type = 'image' if ext in current_app.config['ALLOWED_EXTENSIONS'] else 'video'
            unique_name = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
            
            # Determine storage based on configuration
            if current_app.config.get('CLOUDINARY_ENABLED'):
                # Upload to Cloudinary in production
                public_id = upload_to_cloudinary(file, resource_type=media_type)
                if not public_id:
                    flash(f'Failed to upload {file.filename} to cloud storage.', 'danger')
                    db.session.rollback()
                    return render_template('posts/create.html', groups=groups)
                stored_filename = public_id
            else:
                # Save locally in development
                upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'posts')
                os.makedirs(upload_path, exist_ok=True)
                full_path = os.path.join(upload_path, unique_name)
                file.save(full_path)

                # Validate MIME type
                if not validate_mime_type(full_path, media_type):
                    os.remove(full_path)
                    flash(f'Invalid file content: {file.filename}', 'danger')
                    db.session.rollback()
                    return render_template('posts/create.html', form=form, groups=groups)

                # Store relative path for dev
                stored_filename = f"posts/{unique_name}"

            media = Media(
                post_id=post.id,
                filename=stored_filename,
                media_type=media_type,
                position=idx
            )
            db.session.add(media)

        db.session.commit()
        flash('Post created successfully!', 'success')
        if group_id:
            group = Group.query.get(group_id)
            return redirect(url_for('groups.detail', group_name=group.name))
        return redirect(url_for('main.index'))

    return render_template('posts/create.html', groups=groups, form=form, preselected_group=preselected_group)


@posts_bp.route('/<int:post_id>/like', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def like(post_id):
    post = Post.query.get_or_404(post_id)

    if post.is_liked_by(current_user):
        post.likes.remove(current_user)
        db.session.commit()
        liked = False
    else:
        post.likes.append(current_user)
        db.session.commit()
        liked = True
        # Notify the post owner if not the liker
        if post.author_id != current_user.id:
            notification = Notification(
                recipient_id=post.author_id,
                actor_id=current_user.id,
                type='like',
                message=f'{current_user.username} liked your post',
                link=url_for('main.post_detail', post_id=post.id)
            )
            db.session.add(notification)
            db.session.commit()

    return jsonify({
        'liked': liked,
        'like_count': post.like_count
    })


@posts_bp.route('/<int:post_id>/comment', methods=['POST'])
@login_required
@limiter.limit("20 per minute")
def comment(post_id):
    post = Post.query.get_or_404(post_id)
    text = request.form.get('text', '').strip()

    if not text:
        return jsonify({'error': 'Comment text is required.'}), 400
    
    # Sanitize comment text
    from bleach import clean
    text = clean(text, tags=[], strip=True)[:5000]

    comment = Comment(
        post_id=post.id,
        author_id=current_user.id,
        text=text
    )
    db.session.add(comment)
    db.session.commit()

    # Notify the post owner if not the commenter
    if post.author_id != current_user.id:
        notification = Notification(
            recipient_id=post.author_id,
            actor_id=current_user.id,
            type='comment',
            message=f'{current_user.username} commented on your post',
            link=url_for('main.post_detail', post_id=post.id)
        )
        db.session.add(notification)
        db.session.commit()

    return jsonify({
        'id': comment.id,
        'text': comment.text,
        'author': comment.author.username,
        'created_at': comment.created_at.strftime('%b %d, %Y at %I:%M %p')
    })
