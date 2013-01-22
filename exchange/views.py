__author__ = 'aviraldg'

import flask
from flask import request, render_template, flash, redirect, url_for
from flask.ext.login import login_user
from google.appengine.api import users
from . import app
from .models import User
import forms

@app.route('/')
def index():
    content = {
        'signin': users.create_login_url('/'),
        'signout': users.create_logout_url('/'),
        'name': getattr(flask.g, "user", None)
    }

    return render_template('index.html', **content)

@app.route('/auth/login', methods=('GET', 'POST'))
def login():
    login_form = forms.LoginForm()

    if login_form.validate_on_submit():
        user = User.authenticate(login_form.username.data,
            login_form.password.data)
        if not user:
            flash('Incorrect username or password')
        else:
            login_user(user, login_form.remember.data)
            flash('You\'ve successfully been logged in!')
            return redirect(request.args.get('next') or url_for('index'))


    context = {
        'form': login_form
    }

    return render_template('auth/login.html', **context)

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
