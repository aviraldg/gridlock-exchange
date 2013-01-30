__author__ = 'aviraldg'

from flask.ext.login import current_user
from . import app
from .forms import LogoutForm

@app.context_processor
def inject_globals():
    return {'logout_form': LogoutForm()} if current_user.is_authenticated() \
        else {}
