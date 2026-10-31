from urllib.parse import urlparse, urljoin

from flask import request, url_for

from .i18n import category_label, localized
from .images import image_src, placeholder_art


def is_ajax():
    """True for requests sent by our JavaScript (fetch with X-Requested-With)"""
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def is_safe_redirect(target):
    """True if target points to this site, so ?next= can't send users elsewhere"""
    if not target or '\\' in target:
        return False
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return redirect_url.scheme in ('http', 'https') and redirect_url.netloc == host_url.netloc


def product_to_dict(product):
    """JSON-friendly version of a products row (in the current language), for the JavaScript front end"""
    return {
        'id': product['product_id'],
        'name': localized(product, 'name'),
        'price': product['price'],
        'category': category_label(product['category']),
        'stock': product['stock_quantity'],
        'image': image_src(product['image_url']),
        'art': placeholder_art(product['category']),
        'url': url_for('main.product_detail', product_id=product['product_id']),
    }
