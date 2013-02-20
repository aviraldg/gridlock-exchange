__author__ = 'aviraldg'

from flask.ext.login import current_user
from . import app, babel
from .forms import LogoutForm, ItemDeleteForm, UserDeactivateForm

@app.context_processor
def inject_globals():
    return {
        'logout_form': LogoutForm(),
        'item_delete_form': ItemDeleteForm(),
        'user_deactivate_form': UserDeactivateForm()
    } if current_user.is_authenticated() else {}

@babel.localeselector
def get_locale():
    return 'en'
