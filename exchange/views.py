from exchange.forms import ItemForm
from wtforms import ValidationError

__author__ = 'aviraldg'

import flask
from flask import request, render_template, flash, redirect, url_for, abort
from flask.ext.login import login_user, logout_user, current_user, login_required
from google.appengine.api import users
from google.appengine.ext import ndb
from . import app
from .models import User, Item, Price
from .utils import slugify
import forms

@app.route('/')
def index():
    return redirect(url_for('item_index'))

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
            flash('Incorrect username or password', 'error')
        else:
            login_user(user, login_form.remember.data)
            flash('You\'ve successfully been logged in!', 'success')
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
        if form.validate_on_submit():
            logout_user()
        else:
            abort(403)
    except ValidationError:
        abort(403)

    flash('You have successfully been logged out.', 'success')
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

    return render_template('profile.html', **content)


@login_required
@app.route('/item/create', methods=['GET', 'POST'])
def item_create():
    form = ItemForm()

    if form.validate_on_submit():
        item = Item()
        item.title = form.title.data
        item.seller_id = current_user.get_id()
        item.slug = slugify(form.title.data)
        item.description = form.description.data
        item.price = Price(fixed_value=form.price.data*100, currency='USD')
        item.put()

    return render_template('item/create.html', form=form)

@app.route('/item/')
def item_index():
    if 'q' in request.args:
        query = ndb.gql('SELECT * FROM Item WHERE keywords.keyword=:1', request.args['q'].strip().lower())
    else:
        query = Item.query()
    items, cursor, more = query.fetch_page(10)
    return render_template('item/index.html', items=items)

@app.route('/item/<int:id>/<string:slug>')
def item(id, slug):
    item = Item.get_by_id(id)

    if item is None or item.slug != slug:
        # TODO: need a better (specific) page for item/404
        abort(404)

    return render_template('item/item.html', item=item)

@login_required
@app.route('/item/<int:id>/<string:slug>/update', methods=['GET', 'POST'])
def item_update(id, slug):
    item = Item.get_by_id(id)

    if item is None or item.slug != slug:
        abort(404)

    if item.seller_id != current_user.get_id():
        abort(403)

    form = ItemForm(title=item.title, description=item.description,
        price=item.price.fixed_value/100)

    if form.validate_on_submit():
        item.title = form.title.data
        item.description = form.description.data
        item.price = Price(fixed_value=form.price.data*100, currency='USD')
        item.put()

        flash('Item updated', 'success')

        return redirect(url_for('item', id=id, slug=slug))

    return render_template('item/update.html', form=form, id=id, slug=slug)
