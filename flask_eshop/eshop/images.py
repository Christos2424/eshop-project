import os
import uuid
import urllib.request
from urllib.parse import urlparse

from flask import current_app, flash
from werkzeug.utils import secure_filename


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def download_image_from_url(url, product_id):
    """Download image from URL and save it locally"""
    try:
        # Validate URL
        parsed_url = urlparse(url)
        if parsed_url.scheme not in ['http', 'https']:
            return None

        # Get file extension from URL
        path = parsed_url.path
        ext = path.rsplit('.', 1)[-1].lower() if '.' in path else 'jpg'
        if ext not in current_app.config['ALLOWED_EXTENSIONS']:
            ext = 'jpg'

        # Generate unique filename
        filename = f"product_{product_id}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

        # Download and save image
        urllib.request.urlretrieve(url, filepath)

        return f"uploads/{filename}"
    except Exception as e:
        current_app.logger.warning(f"Error downloading image from URL: {e}")
        return None


def save_uploaded_file(file, product_id):
    """Save uploaded file to the uploads folder"""
    try:
        if file and file.filename != '' and allowed_file(file.filename):
            # Check file size
            file.seek(0, os.SEEK_END)
            file_length = file.tell()
            file.seek(0)

            if file_length > current_app.config['MAX_CONTENT_LENGTH']:
                raise ValueError("File too large (max 16MB)")

            # Generate secure filename with unique identifier
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"product_{product_id}_{uuid.uuid4().hex[:8]}.{ext}"
            filename = secure_filename(filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

            # Ensure upload directory exists
            os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)

            # Save file
            file.save(filepath)
            return f"uploads/{filename}"
        return None
    except Exception as e:
        flash(f"Error processing image: {str(e)}", "danger")
        return None
