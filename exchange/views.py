from exchange.forms import ItemForm
from wtforms import ValidationError

__author__ = 'aviraldg'

from flask import request, render_template, flash, redirect, url_for, abort
from flask.ext.login import login_user, logout_user, current_user, login_required
from google.appengine.api import search
from google.appengine.ext import ndb
from . import app
from .models import User, Item, Price, Conversation, Message
from .utils import slugify, ItemQuery
from .decorators import role_required, condition_required
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
            if not login_user(user, login_form.remember.data):
                flash('You cannot login using this account as it has been deactivated.', 'warning')
            else:
                flash('You\'ve successfully been logged in!', 'success')
            return redirect(request.args.get('next') or url_for('index'))


    context = {
        'form': login_form
    }

    return render_template('auth/login.html', **context)

@app.route('/auth/logout', methods=['POST'])
@login_required
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


@app.route('/item/create', methods=['GET', 'POST'])
@login_required
def item_create():
    form = ItemForm()

    if form.validate_on_submit():
        item = Item()
        item.title = form.title.data
        item.seller_id = current_user.get_id()
        item.slug = slugify(form.title.data)
        item.description = form.description.data
        item.price = Price(fixed_value=form.price.data*100, currency='USD')
        item.active = form.active.data
        item.put()

    return render_template('item/create.html', form=form)

@app.route('/item/')
def item_index():
    # TODO Paginate results properly, and add restrictions on kinds of queries possible.
    # TODO Partial-match search

    if 'q' in request.args:
        iq = ItemQuery.search(request.args['q'].strip().lower())
    else:
        iq = ItemQuery.query()

    items, cursor, more = iq.fetch()

    # def _active_items(items):
    #     for item in items:
    #         if item.active or item.seller_id == current_user.get_id():
    #             yield item
    #
    # if 'q' in request.args:
    #     query = request.args['q'].strip().lower()
    #
    #     try:
    #         results = Item.index.search(search.Query(query))
    #     except search.QueryError:
    #         flash('Sorry, but your query failed.', 'error')
    #         return redirect(url_for('index'))
    #
    #     import itertools
    #     items = itertools.islice(_active_items(results.results), 10)
    #     cursor, more = results.cursor, True
    #     items = ndb.get_multi([ndb.Key(Item, long(result.doc_id)) for result in items])
    #     #query = ndb.gql('SELECT * FROM Item WHERE keywords.keyword=:1', request.args['q'].strip().lower())
    # else:
    #     query = Item.query(ndb.OR(Item.active == True, Item.seller_id == current_user.get_id()))
    #     items, cursor, more = query.fetch_page(10)
    return render_template('item/index.html', items=items)

@app.route('/item/<int:id>/<string:slug>')
def item(id, slug):
    item = Item.get_or_404(id, slug)

    return render_template('item/item.html', item=item)

@app.route('/item/<int:id>/<string:slug>/update', methods=['GET', 'POST'])
@login_required
def item_update(id, slug):
    item = Item.get_or_404(id, slug)

    if not item.editable_by(current_user):
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

@app.route('/item/<int:id>/<string:slug>/delete', methods=['POST'])
@login_required
def item_delete(id, slug):
    item = Item.get_or_404(id, slug)

    if not item.editable_by(current_user):
        abort(403)

    form = forms.ItemDeleteForm()
    if form.validate_on_submit():
        item.key.delete()
        flash('The item has been deleted successfully.', 'success')
        return redirect(url_for('item_index'))
    else:
        abort(403)


@app.route('/user/')
@role_required('admin')
@login_required
def user_index():
    users = User.query().fetch(10)

    return render_template('user/index.html', users=users)

@app.route('/user/<int:id>/<string:username>/')
def user(id, username):
    user_object = User.get_or_404(id, username)

    return render_template('user/user.html', user=user_object)

@app.route('/user/<int:id>/<string:username>/deactivate', methods=['POST'])
@condition_required(lambda id, username: User.get_or_404(id, username).editable_by(current_user))
def user_deactivate(id, username):
    form = forms.UserDeactivateForm()
    user = User.get_or_404(id, username)

    if current_user.has_role('admin') and user == current_user:
        flash('Sorry, but administrators cannot deactivate their own accounts.', 'error')
        flash('Please ask another administrator to deactivate your account.', 'info')
        return redirect(url_for('user', id=id, username=username))

    if form.validate_on_submit():
        user.active = not user.active
        user.put()

        # flipped, because we've just activated/deactivated
        flash('%s has successfully been %sactivated!' % (username, '' if user.active else 'de'), 'success')

        return redirect(url_for('user', id=id, username=username))
    else:
        abort(403)

@app.route('/user/<int:id>/<string:username>/delete', methods=['GET', 'POST'])
@condition_required(lambda id, username: User.get_or_404(id, username).get_id() == current_user.get_id())
def user_delete(id, username):
    form = forms.UserDeleteForm()
    user = User.get_or_404(id, username)

    if current_user.has_role('admin'):
        flash('Sorry, but administrators cannot delete their accounts.', 'error')
        flash('Please ask another administrator to deactivate your account, or make you a regular user.', 'info')
        return redirect(url_for('user', id=id, username=username))

    if form.validate_on_submit():
        logout_user()
        user.delete()

        flash('Your account has successfully been deleted.')

        return redirect(url_for('index'))

    return render_template('user/delete.html', user=user, user_delete_form=form)

@app.route('/message')
@login_required
def message_index():
    c_page = Conversation.list_query(current_user).fetch_page(10)
    return render_template('message/index.html', conversations=c_page[0], cursor=c_page[1], has_more=c_page[2])

@app.route('/message/send', methods=['GET', 'POST'])
@login_required
def message_send():
    form = forms.MessageSendForm()

    if form.validate_on_submit():
        to = User.query(User.username.IN(map(lambda un: un.strip(), form.to.data.split(',')))).fetch(1000)
        Message.send(current_user, to, '', form.message.data)

    return render_template('message/send.html', message_send_form=form)


@app.route('/message/conversation/<int:id>')
@login_required
def message_conversation(id):
    c = Conversation.get_by_id(id)

    if not c:
        abort(404)

    if current_user.key not in c.participant_keys:
        abort(403)

    page = Message.query(Message.to == c.key).fetch_page(10)

    return render_template('message/conversation.html', conversation=c, messages=page[0], cursor=page[1],
                           has_more=page[2], message_send_form=forms.MessageSendForm())
