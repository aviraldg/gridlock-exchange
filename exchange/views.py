__author__ = 'aviraldg'

import flask
from flask import render_template
from google.appengine.api import users
from . import app
import forms

@app.route('/')
def index():
    content = {
        'signin': users.create_login_url('/'),
        'signout': users.create_logout_url('/'),
        'name': getattr(flask.g, "user", None)
    }

    return render_template('index.html', **content)

@app.route('/profile')
@app.route('/profile/<int:profile_id>')
def profile(profile_id = None):
    """
    Shows the profile associated with profile_id, or for the current user if
    that is None. In case no profile exists, a profile creation form is shown.
    """

    content = {
        'form': forms.UserProfileForm()
    }

    return render_template("profile.html", **content)
