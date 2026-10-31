"""English / Greek translations.

Texts are written in English in the code and templates. translations/<code>.json maps
each English text to its translation; anything missing is shown in English.

    Python:     _('Only {n} left', n=3)          (from .i18n import gettext as _)
    Templates:  {{ _('Only {n} left', n=3) }}
    JavaScript: t('Only {n} left', { n: 3 })     (catalog served by main.translations_js)
"""
import json
import os
import unicodedata

from flask import g, has_request_context, request, session
from markupsafe import Markup

LANGUAGES = {'en': 'English', 'el': 'Ελληνικά'}
DEFAULT_LANGUAGE = 'en'

catalogs = {}


def load_catalogs(app):
    folder = os.path.join(app.root_path, 'translations')
    for code in LANGUAGES:
        path = os.path.join(folder, f'{code}.json')
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                catalogs[code] = json.load(f)


def catalog_version(app):
    """Changes whenever a translation file changes, to refresh the browser's cached copy"""
    folder = os.path.join(app.root_path, 'translations')
    return int(max((os.path.getmtime(os.path.join(folder, f)) for f in os.listdir(folder)), default=0))


def get_locale():
    """Language chosen in the language menu, else the browser's preference"""
    if not has_request_context():
        return DEFAULT_LANGUAGE
    if 'lang' not in g:
        lang = session.get('lang')
        if lang not in LANGUAGES:
            lang = request.accept_languages.best_match(LANGUAGES.keys()) or DEFAULT_LANGUAGE
        g.lang = lang
    return g.lang


def translate(text):
    return catalogs.get(get_locale(), {}).get(text, text)


def gettext(text, **params):
    """Translated text as a plain string, for flash messages and JSON"""
    text = translate(text)
    return text.format(**params) if params else text


def ngettext(singular, plural, n, **params):
    return gettext(singular if n == 1 else plural, n=n, **params)


# Template versions: the translation is trusted HTML, the params are escaped
def template_gettext(text, **params):
    text = Markup(translate(text))
    return text.format(**params) if params else text


def template_ngettext(singular, plural, n, **params):
    return template_gettext(singular if n == 1 else plural, n=n, **params)


def localized(product, field):
    """A product's name or description in the current language, falling back to English"""
    lang = get_locale()
    if lang != DEFAULT_LANGUAGE:
        key = f'{field}_{lang}'
        if key in product.keys() and product[key]:
            return product[key]
    return product[field]


def category_label(category):
    """Display name of a category; categories are stored in English"""
    return translate(category) if category else translate('General')


def name_sql(table=''):
    """SQL expression for the product name in the current language (table: e.g. 'p.')"""
    if get_locale() == 'el':
        return f"COALESCE(NULLIF({table}name_el, ''), {table}name)"
    return f"{table}name"


def fold(text):
    """Lowercase without accents, so 'Λάπτοπ' matches 'λαπτοπ' and 'LAPTOP' matches 'laptop'"""
    if text is None:
        return None
    decomposed = unicodedata.normalize('NFD', text.casefold())
    return ''.join(ch for ch in decomposed if unicodedata.category(ch) != 'Mn')
