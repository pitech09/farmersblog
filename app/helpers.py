"""Helper functions for media handling with conditional Cloudinary support."""
import os
from flask import current_app


def get_media_url(filename):
    """
    Generate the appropriate URL for a media file based on configuration.
    
    In development: returns local URL (/uploads/<type>/<filename>)
    In production: returns Cloudinary URL if we detect it's a public_id,
                   otherwise constructs local URL
    
    Args:
        filename: Either a local filename or Cloudinary public_id
        
    Returns:
        str: URL to the media file
    """
    if not filename:
        return None
    
    # Check if we're in production with Cloudinary enabled
    cloudinary_enabled = current_app.config.get('CLOUDINARY_ENABLED', False)
    
    if cloudinary_enabled:
        # In production, filename is stored as Cloudinary public_id
        try:
            import cloudinary
            cloudinary.config(
                cloud_name=current_app.config['CLOUDINARY_CLOUD_NAME'],
                api_key=current_app.config['CLOUDINARY_API_KEY'],
                api_secret=current_app.config['CLOUDINARY_API_SECRET']
            )
            # Build Cloudinary URL with optimizations
            url, _ = cloudinary.utils.cloudinary_url(
                filename,
                width=800,
                crop="limit",
                quality="auto"
            )
            return url
        except Exception as e:
            current_app.logger.error(f"Error building Cloudinary URL: {e}")
            return None
    
    # Development: return local URL (filename already includes subfolder path in DB)
    # The filename stored in DB is like: posts/uuid_file.jpg or avatars/uuid_file.jpg or marketplace/uuid_file.jpg
    return f"/uploads/{filename}"


def get_avatar_url(filename):
    """Get URL for user avatar."""
    if not filename:
        return '/static/img/default-avatar.png'
    
    if current_app.config.get('CLOUDINARY_ENABLED'):
        try:
            import cloudinary
            cloudinary.config(
                cloud_name=current_app.config['CLOUDINARY_CLOUD_NAME'],
                api_key=current_app.config['CLOUDINARY_API_KEY'],
                api_secret=current_app.config['CLOUDINARY_API_SECRET']
            )
            url, _ = cloudinary.utils.cloudinary_url(
                filename,
                width=200,
                height=200,
                crop="fill",
                gravity="face",
                quality="auto"
            )
            return url
        except Exception as e:
            current_app.logger.error(f"Error building Cloudinary avatar URL: {e}")
            return '/static/img/default-avatar.png'
    
    return f"/uploads/{filename}"


def upload_to_cloudinary(file, resource_type="auto"):
    """
    Upload a file to Cloudinary and return the public_id.
    
    Args:
        file: FileStorage object
        resource_type: 'image', 'video', or 'auto'
        
    Returns:
        str: Cloudinary public_id or None if upload fails
    """
    try:
        import cloudinary
        import cloudinary.uploader
        cloudinary.config(
            cloud_name=current_app.config['CLOUDINARY_CLOUD_NAME'],
            api_key=current_app.config['CLOUDINARY_API_KEY'],
            api_secret=current_app.config['CLOUDINARY_API_SECRET']
        )
        
        result = cloudinary.uploader.upload(file, resource_type=resource_type)
        return result.get('public_id')
    except Exception as e:
        current_app.logger.error(f"Cloudinary upload error: {e}")
        return None