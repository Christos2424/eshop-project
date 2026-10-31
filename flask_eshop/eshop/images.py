import ipaddress
import os
import socket
import uuid
import urllib.request
from urllib.error import URLError
from urllib.parse import urlparse

from flask import current_app, flash
from werkzeug.utils import secure_filename


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def is_public_url(url):
    """Only allow http(s) URLs whose host resolves to public internet addresses.

    Blocks localhost, private networks (192.168.x.x, 10.x.x.x, ...), link-local
    and cloud metadata addresses, so the server can't be used to reach them.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        return False

    try:
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        addresses = socket.getaddrinfo(parsed.hostname, port, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, ValueError):
        return False

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0].split('%')[0])
        if ip.version == 6 and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        if not ip.is_global or ip.is_multicast:
            return False
    return bool(addresses)


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Re-check every redirect target so a public URL can't bounce to an internal one"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not is_public_url(newurl):
            raise URLError(f"Redirect to a disallowed address: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_image_from_url(url, product_id):
    """Download image from URL and save it locally"""
    try:
        if not is_public_url(url):
            current_app.logger.warning(f"Refused to download image from non-public URL: {url}")
            return None

        # Get file extension from URL
        path = urlparse(url).path
        ext = path.rsplit('.', 1)[-1].lower() if '.' in path else 'jpg'
        if ext not in current_app.config['ALLOWED_EXTENSIONS']:
            ext = 'jpg'

        # Generate unique filename
        filename = f"product_{product_id}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        max_size = current_app.config['MAX_CONTENT_LENGTH']

        opener = urllib.request.build_opener(SafeRedirectHandler)
        with opener.open(url, timeout=current_app.config['IMAGE_DOWNLOAD_TIMEOUT']) as response:
            if not response.headers.get_content_type().startswith('image/'):
                current_app.logger.warning(f"URL is not an image: {url}")
                return None

            # Read with a size cap so a huge file can't fill the disk
            data = response.read(max_size + 1)
            if len(data) > max_size:
                current_app.logger.warning(f"Image at {url} is larger than 16MB")
                return None

        with open(filepath, 'wb') as f:
            f.write(data)

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
