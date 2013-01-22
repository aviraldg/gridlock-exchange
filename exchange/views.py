from wtforms import ValidationError

__author__ = 'aviraldg'

import flask
from flask import request, render_template, flash, redirect, url_for, abort
from flask.ext.login import login_user, logout_user, current_user, login_required
from google.appengine.api import users
from . import app
from .models import User
import forms

@app.route('/')
def index():
    content = {
        'login': url_for('login', next=request.url),
        'logout_form': forms.LogoutForm(),
        'name': current_user.username
    }

    return render_template('index.html', **content)

@app.route('/auth/register', methods=('GET', 'POST'))
def register():
    form = forms.RegisterForm()

    if form.validate_on_submit():
        user = User()
        user.username = form.username.data
        user.name = form.name.data
        user.email = form.email.data
        user.set_password(form.password.data)
        user.put()
        flash('You\'ve been registered!')
        return redirect(url_for('login'))

    return render_template('auth/register.html', form=form)

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

@login_required
@app.route('/auth/logout', methods=['POST'])
def logout():
    form = forms.LogoutForm()
    try:
        if form.validate_csrf_token(form.csrf_token):
            logout_user()
    except ValidationError:
        abort(403)

    flash('You have successfully been logged out.')
    return redirect(url_for('login'))

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
