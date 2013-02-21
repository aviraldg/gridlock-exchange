__author__ = 'aviraldg'

from flask import session, request, flash
from flask.ext.login import current_user
from . import app, babel
from .forms import LogoutForm, ItemDeleteForm, UserDeactivateForm
from babel import Locale
from .models import Item
from bootstrap import do_bootstrap
import os
from flask.ext.babel import gettext as _T, lazy_gettext as _LT

_langs = None

def list_langs():
    """
    Returns a list of all available languages.
    """
    global _langs
    if not _langs:
        _langs = os.listdir(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'translations'))
        _langs = {lang: Locale.parse(lang).display_name for lang in _langs}
    return _langs

@app.before_request
def change_lang():
    lang = request.args.get('lang', None) or session.get('lang', 'en')
    session['lang'] = lang

@app.before_first_request
def bootstrap():
    if not Item.query().get():
        do_bootstrap()

    flash(_T('The app was bootstrapped (first run only); please reload the page.'))

@app.context_processor
def inject_globals():
    inject = {
        'logout_form': LogoutForm(),
        'item_delete_form': ItemDeleteForm(),
        'user_deactivate_form': UserDeactivateForm()
    } if current_user.is_authenticated() else {}

    inject.update({
        'lang': Locale.parse(session.get('lang', 'en')),
        'langs': list_langs()
    })

    return inject

@babel.localeselector
def get_locale():
    return session.get('lang', 'en')
