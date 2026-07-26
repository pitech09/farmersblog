import os
import uuid
import re
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, abort, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import magic
from app.forms import ListingForm
from app.extensions import db, cache
from app.models import Listing, User
from app.helpers import get_media_url, upload_to_cloudinary

marketplace_bp = Blueprint('marketplace', __name__)


def allowed_image_file(filename):
    """Check if file extension is allowed for images."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def validate_image_mime(file_path):
    """Validate that the file is actually an image."""
    try:
        mime = magic.Magic(mime=True)
        file_mime = mime.from_file(file_path)
        # from_file returns bytes (e.g. b'image/jpeg'), decode to str for comparison
        if isinstance(file_mime, bytes):
            file_mime = file_mime.decode('utf-8')
        return file_mime in ['image/jpeg', 'image/png', 'image/gif', 'image/jpg']
    except Exception:
        return False


@marketplace_bp.route('/')
@cache.cached(timeout=120, query_string=True)
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 12
    category = request.args.get('category')
    
    query = Listing.query.filter_by(is_sold=False)
    if category:
        query = query.filter_by(category=category)
    query = query.order_by(Listing.created_at.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    listings = pagination.items
    categories = db.session.query(Listing.category).distinct().all()
    categories = [c[0] for c in categories]
    
    return render_template('marketplace/index.html',
                         listings=listings,
                         pagination=pagination,
                         categories=categories,
                         current_category=category)


@marketplace_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    categories = ['Seeds', 'Equipment', 'Livestock', 'Produce', 'Other']
    
    form = ListingForm(categories=categories)
    if form.validate_on_submit():
        # Sanitize inputs
        from bleach import clean
        title = clean(form.title.data, tags=[], strip=True)[:200]
        description = clean(form.description.data, tags=[], strip=True)[:5000]
        location = clean(form.location.data or '', tags=[], strip=True)[:200]
        price = form.price.data
        category = form.category.data

        # Handle image upload
        image_filename = None
        image_file = form.image.data
        if image_file and image_file.filename:
            if not allowed_image_file(image_file.filename):
                flash('Invalid image type. Allowed: PNG, JPG, JPEG, GIF', 'danger')
                return render_template('marketplace/create.html', form=form, categories=categories)
            
            # Check file size
            image_file.seek(0, os.SEEK_END)
            file_size = image_file.tell()
            image_file.seek(0)
            
            if file_size > current_app.config['MAX_CONTENT_LENGTH']:
                flash('Image too large. Maximum size is 50MB.', 'danger')
                return render_template('marketplace/create.html', form=form, categories=categories)
            
            unique_name = f"{uuid.uuid4().hex}_{secure_filename(image_file.filename)}"
            
            # Determine storage based on configuration
            if current_app.config.get('CLOUDINARY_ENABLED'):
                public_id = upload_to_cloudinary(image_file, resource_type='image')
                if not public_id:
                    flash('Failed to upload image to cloud storage.', 'danger')
                    return render_template('marketplace/create.html', form=form, categories=categories)
                image_filename = public_id
            else:
                upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'marketplace')
                os.makedirs(upload_path, exist_ok=True)
                full_path = os.path.join(upload_path, unique_name)
                image_file.save(full_path)
                
                if not validate_image_mime(full_path):
                    os.remove(full_path)
                    flash('Invalid image file.', 'danger')
                    return render_template('marketplace/create.html', form=form, categories=categories)
                
                image_filename = f"marketplace/{unique_name}"
        else:
            # Use placeholder if no image uploaded
            image_filename = 'placeholder.jpg'
        
        listing = Listing(
            seller_id=current_user.id,
            title=title,
            description=description,
            price=price,
            category=category,
            location=location,
            image_filename=image_filename
        )
        db.session.add(listing)
        db.session.commit()
        
        flash('Listing created successfully!', 'success')
        return redirect(url_for('marketplace.index'))
    
    return render_template('marketplace/create.html', form=form, categories=categories)


@marketplace_bp.route('/<int:listing_id>')
def detail(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    return render_template('marketplace/detail.html', listing=listing)


@marketplace_bp.route('/my-listings')
@login_required
def my_listings():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    pagination = Listing.query.filter_by(seller_id=current_user.id)\
        .order_by(Listing.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('marketplace/my_listings.html',
                         listings=pagination.items,
                         pagination=pagination)


@marketplace_bp.route('/<int:listing_id>/sold', methods=['POST'])
@login_required
def mark_sold(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    
    # Authorization check
    if listing.seller_id != current_user.id:
        flash('You can only modify your own listings.', 'danger')
        return redirect(url_for('marketplace.index'))
    
    listing.is_sold = not listing.is_sold
    db.session.commit()
    
    status = 'sold' if listing.is_sold else 'available'
    flash(f'Listing marked as {status}.', 'success')
    return redirect(url_for('marketplace.my_listings'))


@marketplace_bp.route('/<int:listing_id>/delete', methods=['POST'])
@login_required
def delete(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    
    # Authorization check
    if listing.seller_id != current_user.id:
        flash('You can only delete your own listings.', 'danger')
        return redirect(url_for('marketplace.index'))
    
    db.session.delete(listing)
    db.session.commit()
    
    flash('Listing deleted successfully.', 'success')
    return redirect(url_for('marketplace.my_listings'))


# Secure media serving route
@marketplace_bp.route('/media/<path:filename>')
def media(filename):
    """Securely serve uploaded media files."""
    # Prevent directory traversal
    if '..' in filename or filename.startswith('/'):
        abort(404)
    
    upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'marketplace')
    file_path = os.path.join(upload_folder, filename)
    
    if not os.path.exists(file_path):
        abort(404)
    
    # Set appropriate content type
    from flask import send_from_directory
    return send_from_directory(upload_folder, filename)
