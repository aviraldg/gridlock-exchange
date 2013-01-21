__author__ = 'aviraldg'

from google.appengine.api import users
import flask
from flask import request, redirect, url_for
from . import app


@app.before_request
def user_prep():
    """
    Get the current User and stash it.
    If the User's logged in, and doesn't have a profile, redirect them to the
    profile creation page.
    """

    user = users.get_current_user()
    if user:
        from .models import UserProfile

        flask.g.user = user

        profile = UserProfile.query(UserProfile.user_id == user.user_id()).get()
        if profile:
            flask.g.user_profile = profile
        else:
            # TODO: Add a note to indicate why the User's being redirected?
            if request.endpoint != "profile":
                return redirect(url_for('profile'))

