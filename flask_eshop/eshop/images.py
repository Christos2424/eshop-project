import io
import ipaddress
import os
import socket
import uuid
import urllib.request
from urllib.error import URLError
from urllib.parse import urlparse

from flask import current_app, flash, url_for
from PIL import Image, ImageOps, UnidentifiedImageError

from .i18n import gettext


# Icon and colour (hue) shown instead of a photo, by category
CATEGORY_ART = {
    'electronics': ('fa-laptop', 235),
    'books': ('fa-book-open', 28),
    'home & kitchen': ('fa-couch', 172),
    'sports & outdoors': ('fa-dumbbell', 145),
    'fashion': ('fa-tshirt', 330),
    'beauty & care': ('fa-spa', 285),
    'toys & games': ('fa-puzzle-piece', 45),
    'food': ('fa-apple-alt', 95),
    'pet supplies': ('fa-paw', 15),
    'garden & diy': ('fa-seedling', 120),
    'office & stationery': ('fa-pen', 260),
    'automotive': ('fa-car', 200),
}
DEFAULT_ART = ('fa-box-open', 210)


def placeholder_art(category):
    """{'icon', 'hue'} for products without an image"""
    icon, hue = CATEGORY_ART.get((category or '').strip().casefold(), DEFAULT_ART)
    return {'icon': icon, 'hue': hue}


# Stored images are re-encoded as WebP: a full size one and a small one for lists
IMAGE_MAX_SIZE = 1200
THUMB_MAX_SIZE = 400
MAX_PIXELS = 40_000_000  # refuse decompression bombs
THUMB_SUFFIX = '_thumb'


def thumb_path(image_url):
    return image_url.removesuffix('.webp') + THUMB_SUFFIX + '.webp'


def image_src(image_url, thumb=False):
    """URL to show a product image (the small version when thumb is set); None when the product has no image"""
    if not image_url:
        return None

    # If it starts with uploads/, it's a local file
    if image_url.startswith('uploads/'):
        # Images stored before re-encoding was added (not .webp) have no thumbnail
        if thumb and image_url.endswith('.webp'):
            image_url = thumb_path(image_url)
        return url_for('uploaded_file', filename=image_url.removeprefix('uploads/'))

    # Otherwise, it's an external URL
    return image_url


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


def store_image(data, product_id):
    """Check that data is a real image, then save it re-encoded as WebP (plus a thumbnail).

    Returns the "uploads/..." path, or None if data isn't a usable image.
    """
    try:
        Image.MAX_IMAGE_PIXELS = MAX_PIXELS
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()
        # verify() leaves the image unusable, so open it again
        with Image.open(io.BytesIO(data)) as image:
            image = ImageOps.exif_transpose(image)  # phone photos carry their rotation in EXIF
            image = image.convert('RGBA' if 'A' in image.getbands() or 'transparency' in image.info else 'RGB')

            name = f"product_{product_id}_{uuid.uuid4().hex[:8]}"
            folder = current_app.config['UPLOAD_FOLDER']
            os.makedirs(folder, exist_ok=True)

            for size, suffix, quality in ((IMAGE_MAX_SIZE, '', 82), (THUMB_MAX_SIZE, THUMB_SUFFIX, 78)):
                version = image.copy()
                version.thumbnail((size, size))
                version.save(os.path.join(folder, f"{name}{suffix}.webp"), 'WEBP', quality=quality)
        return f"uploads/{name}.webp"
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError, SyntaxError):
        current_app.logger.warning('Rejected a file that is not a valid image', exc_info=True)
        return None


def delete_image(image_url):
    """Remove a product's stored image files (an external URL has nothing to remove)"""
    if not image_url or not image_url.startswith('uploads/'):
        return
    folder = current_app.config['UPLOAD_FOLDER']
    for path in {image_url, thumb_path(image_url)}:
        # basename keeps a bad value from pointing outside the uploads folder
        file = os.path.join(folder, os.path.basename(path))
        try:
            os.remove(file)
        except FileNotFoundError:
            pass
        except OSError:
            current_app.logger.warning('Could not delete %s', file, exc_info=True)


def download_image_from_url(url, product_id):
    """Download image from URL and save it locally"""
    try:
        if not is_public_url(url):
            current_app.logger.warning(f"Refused to download image from non-public URL: {url}")
            return None

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

        return store_image(data, product_id)
    except Exception as e:
        current_app.logger.warning(f"Error downloading image from URL: {e}")
        return None


def save_uploaded_file(file, product_id):
    """Check an uploaded image and save it to the uploads folder"""
    try:
        if not file or file.filename == '':
            return None

        if not allowed_file(file.filename):
            flash(gettext('Unsupported image format. Use PNG, JPG, GIF or WEBP.'), 'danger')
            return None

        # Check file size
        file.seek(0, os.SEEK_END)
        file_length = file.tell()
        file.seek(0)

        if file_length > current_app.config['MAX_CONTENT_LENGTH']:
            flash(gettext('File too large. Maximum size is 16MB.'), 'danger')
            return None

        path = store_image(file.read(), product_id)
        if path is None:
            flash(gettext('Unsupported image format. Use PNG, JPG, GIF or WEBP.'), 'danger')
        return path
    except Exception:
        current_app.logger.exception('Saving an uploaded image failed')
        flash(gettext('An unexpected error occurred. Please try again.'), 'danger')
        return None
