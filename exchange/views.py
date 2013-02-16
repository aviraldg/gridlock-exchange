__author__ = 'aviraldg'

from flask import request, render_template, flash, redirect, url_for, abort, make_response
from flask.ext.login import login_user, logout_user, current_user, login_required
from google.appengine.api import search
import datetime
from . import app
from .models import User, Item, Price, Conversation, Message, Feedback, FeedbackAggregate, Collection
from .utils import slugify, ItemQuery, to_fieldstorage, TEAPOT
from .decorators import role_required, condition_required
import forms
from flask.ext.babel import gettext as _T, lazy_gettext as _LT
from exchange.forms import ItemForm
from wtforms import ValidationError
from google.appengine.ext import blobstore, ndb
import urllib


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
        flash(_T('You\'ve been registered!'))
        return redirect(url_for('login'))

    return render_template('auth/register.html', form=form)

@app.route('/auth/login', methods=('GET', 'POST'))
def login():
    login_form = forms.LoginForm()

    if login_form.validate_on_submit():
        user = User.authenticate(login_form.username.data,
            login_form.password.data)
        if not user:
            flash(_T('Incorrect username or password'), 'error')
        else:
            if not login_user(user, login_form.remember.data):
                flash(_T('You cannot login using this account as it has been deactivated.'), 'warning')
            else:
                flash(_T('You\'ve successfully been logged in!'), 'success')
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

    flash(_T('You have successfully been logged out.'), 'success')
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
        if form.image.has_file():
            blob = blobstore.parse_blob_info(to_fieldstorage(form.image.data))
            item.image = blob.key()
        item.youtube = form.youtube.data
        item.active = form.active.data
        private_viewer_usernames = [_.strip() for _ in form.private_viewers.data.split(',')]
        item.private_viewer_keys = [user.key for user in User.query(User.username.IN(private_viewer_usernames))]
        k = item.put()

        flash(_T('Your item has been created!'), 'success')
        return redirect(url_for('item', id=k.id(), slug=item.slug))

    return render_template('item/create.html', form=form,
                           action=blobstore.create_upload_url(url_for('item_create')))

@app.route('/item/')
def item_index():
    # TODO Paginate results properly, and add restrictions on kinds of queries possible.
    # TODO Partial-match search

    orderings = Item.get_orderings()
    current_ordering = orderings[request.args.get('o', '-created')]

    if 'q' in request.args:
        if request.args['q'].strip().lower() == 'htcpcp':
            abort(418, TEAPOT)
        elif request.args['q'].strip().lower() == 'about:credits':
            return redirect('/humans.txt')
        iq = ItemQuery.search(request.args['q'].strip().lower(), current_ordering)
    else:
        iq = ItemQuery.query(None, current_ordering, request.args.get('c'))

    try:
        items, cursor, more = iq.fetch(10)
    except search.QueryError:
        flash(_T('Sorry, but your query failed.'), 'error')
        return redirect(url_for('index'))

    return render_template('item/index.html', items=items, cursor=urllib.quote_plus(cursor) if cursor else None,
                           has_more=more, item_orderings=orderings.keys())

@app.route('/item/<int:id>/<string:slug>')
def item(id, slug):
    item = Item.get_or_404(id, slug)
    feedback_form = forms.FeedbackForm()
    return render_template('item/item.html', item=item, feedback_form=feedback_form)

@app.route('/item/<int:id>/<string:slug>/update', methods=['GET', 'POST'])
@login_required
def item_update(id, slug):
    item = Item.get_or_404(id, slug)

    if not item.editable_by(current_user):
        abort(403)

    form = ItemForm(title=item.title, description=item.description,
        price=item.price.fixed_value/100, youtube=item.youtube,
        private_viewers=','.join([user.username for user in ndb.get_multi(item.private_viewer_keys)]))

    if form.validate_on_submit():
        item.title = form.title.data
        item.description = form.description.data
        item.price = Price(fixed_value=form.price.data*100, currency='USD')
        private_viewer_usernames = [_.strip() for _ in form.private_viewers.data.split(',')]
        item.private_viewer_keys = [user.key for user in User.query(User.username.IN(private_viewer_usernames))]
        if form.image.has_file():
            app.logger.debug(form.image.data)
            app.logger.debug(dir(form.image.data))
            app.logger.debug(form.image.data.mimetype_params)
            blob = blobstore.parse_blob_info(to_fieldstorage(form.image.data))
            item.image = blob.key()
        item.put()

        flash(_T('Item updated'), 'success')

        return redirect(url_for('item', id=id, slug=slug))

    return render_template('item/update.html', form=form, id=id, slug=slug,
                           action=blobstore.create_upload_url(url_for('item_update', id=id, slug=slug)))

@app.route('/item/<int:id>/<string:slug>/delete', methods=['POST'])
@login_required
def item_delete(id, slug):
    item = Item.get_or_404(id, slug)

    if not item.editable_by(current_user):
        abort(403)

    form = forms.ItemDeleteForm()
    if form.validate_on_submit():
        item.key.delete()
        flash(_T('The item has been deleted successfully.'), 'success')
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
        flash(_T('Sorry, but administrators cannot deactivate their own accounts.'), 'error')
        flash(_T('Please ask another administrator to deactivate your account.'), 'info')
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
        flash(_T('Sorry, but administrators cannot delete their accounts.'), 'error')
        flash(_T('Please ask another administrator to deactivate your account, or to make you a regular user.'), 'info')
        return redirect(url_for('user', id=id, username=username))

    if form.validate_on_submit():
        logout_user()
        user.delete()

        flash(_T('Your account has successfully been deleted.'))

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

@app.route('/feedback/<string:key>/add', methods=['POST'])
@login_required
def feedback_add(key):
    k = ndb.Key(urlsafe=key)

    form = forms.FeedbackForm()

    if form.validate_on_submit():
        Feedback.add_or_update(k, current_user.key, form.rating.data, form.feedback.data)
        flash(_LT('Your feedback has been submitted. Thanks!'), 'success')
        return redirect(request.args.get('next', url_for('item_index')))

@app.route('/collection/')
def collection_index():
    cq = Collection.query(Collection.author_key == current_user.key)
    collections, cursor, has_more = cq.fetch_page(10)
    return render_template('collection/index.html', collections=collections, cursor=cursor, has_more=has_more)

@app.route('/collection/<int:id>/')
def collection(id):
    collection = Collection.get_by_id(id)
    return render_template('collection/collection.html', collection=collection)

@app.route('/collection/create', methods=['GET', 'POST'])
def collection_create():
    collection_form = forms.CollectionForm()
    # XXX This could potentially be a problem, but given the current scale of the app, it shouldn't
    # cause much trouble.
    # NOTE: Because we populate the choices here and validate_on_submit later, even if the user
    # modifies the options by hand, they'll still be verified against these choices.
    collection_form.item_ids.choices = [(item.key.id(), '#%s - %s' % (item.key.id(), item.title)) for item in
                                        Item.query(Item.seller_id == current_user.get_id()).fetch(100000)]

    if collection_form.validate_on_submit():
        c = Collection()
        c.title = collection_form.title.data
        c.description = collection_form.description.data
        c.author = current_user
        c.item_keys = [ndb.Key(Item, id) for id in collection_form.item_ids.data]
        k = c.put()

        flash(_LT('Your collection has been created successfully!'), 'success')
        return redirect(url_for('collection', id=k.id()))

    return render_template('collection/create.html', collection_form=collection_form)


@app.route('/user/data-liberation/')
@app.route('/user/data-liberation/<string:filename>')
@login_required
def data_liberation(filename=None):
    if not filename:
        return redirect(url_for('data_liberation',
                                filename=datetime.datetime.now().ctime().replace(' ', '-').replace(':', '-') +
                                         '-%s.zip' % current_user.username))
    # XXX Do this in a background task, cache, etc.
    from datalib import generate_zip
    zip = generate_zip(current_user.username)
    resp = make_response(zip)
    resp.headers['Content-Type'] = 'application/zip'
    return resp

@app.route('/blob/<string:key>')
def blob(key):
    # TODO Limit this on the basis of whether the user can actually access the blob.
    bi = blobstore.BlobInfo.get(blobstore.BlobKey(key))
    if bi == None:
        abort(404)
    resp = make_response()
    resp.mimetype = bi.content_type
    resp.headers['X-AppEngine-BlobKey'] = key
    return resp
