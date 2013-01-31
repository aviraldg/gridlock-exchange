__author__ = 'aviraldg'

from flask.ext.login import current_user
from . import app
from .forms import LogoutForm, ItemDeleteForm

@app.context_processor
def inject_globals():
    return {
        'logout_form': LogoutForm(),
        'item_delete_form': ItemDeleteForm()
    } if current_user.is_authenticated() else {}
