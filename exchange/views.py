__author__ = 'aviraldg'

from flask import request, render_template, flash, redirect, url_for, abort, make_response
from flask.ext.login import login_user, logout_user, current_user, login_required
from google.appengine.api import users
from google.appengine.api.search import QueryError
from google.appengine.api.mail import InboundEmailMessage
import datetime
from . import app
from .models import UserProfile, Item, Price, Conversation, Message, Feedback, FeedbackAggregate, Collection
from .utils import slugify, ItemQuery, to_fieldstorage, TEAPOT
from .decorators import role_required, condition_required
import forms
from flask.ext.babel import gettext as _T, lazy_gettext as _LT
from exchange.forms import ItemForm
from wtforms import ValidationError
from google.appengine.ext import blobstore, ndb
import notify
import logging
import apiclient


@app.route('/')
def index():
    return redirect(request.args.get('next') or url_for('item_index'))

# @app.route('/auth/register', methods=('GET', 'POST'))
# def register():
#     form = forms.RegisterForm()
#
#     if form.validate_on_submit():
#         user = User()
#         user.username = form.username.data
#         user.name = form.name.data
#         user.email = form.email.data
#         user.set_password(form.password.data)
#         user.put()
#         flash(_T('You\'ve been registered!'))
#         return redirect(url_for('login'))
#
#     return render_template('auth/register.html', form=form)

# No longer used, now that we've switched to Google's User Service.
#
# @app.route('/auth/login', methods=('GET', 'POST'))
# def login():
#     login_form = forms.LoginForm()
#
#     if login_form.validate_on_submit():
#         user = User.authenticate(login_form.username.data,
#             login_form.password.data)
#         if not user:
#             flash(_T('Incorrect username or password'), 'error')
#         else:
#             if not login_user(user, login_form.remember.data):
#                 flash(_T('You cannot login using this account as it has been deactivated.'), 'warning')
#             else:
#                 flash(_T('You\'ve successfully been logged in!'), 'success')
#             return redirect(request.args.get('next') or url_for('index'))
#
#
#     context = {
#         'form': login_form
#     }
#
#     return render_template('auth/login.html', **context)

# This controller maintains the old "interface" while using Google's Login Service.
@app.route('/auth/login')
def login():
    user = users.get_current_user()
    if user is not None:
        user_profile = UserProfile.for_user(user)
        if login_user(user_profile):
            flash(_T('You\'ve successfully been logged in!'), 'success')
        else:
            flash(_T('You cannot login using this account as it has been deactivated.'), 'warning')
            return redirect(users.create_logout_url(url_for('index')))

        return redirect(url_for('index'))
    else:
        return redirect(users.create_login_url(url_for('login')))

@app.route('/auth/logout', methods=['POST'])
@login_required
def logout():
    form = forms.LogoutForm()
    try:
        if form.validate_on_submit():
            logout_user()
            flash(_T('You have successfully been logged out.'), 'success')
            return redirect(users.create_logout_url(url_for('index')))
        else:
            abort(403)
    except ValidationError:
        abort(403)

# @app.route('/profile')
# @app.route('/profile/<int:profile_id>')
# def profile(profile_id = None):
#     """
#     Shows the profile associated with profile_id, or for the current user if
#     that is None. In case no profile exists, a profile creation form is shown.
#     """
#
#     content = {
#         'form': forms.UserProfileForm()
#     }
#
#     return render_template('profile.html', **content)


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
        item.expiry = datetime.datetime.now() + datetime.timedelta(days=form.expires_in.data)
        private_viewer_emails = [_.strip() for _ in form.private_viewers.data.split(',')]
        item.private_viewer_keys = [user.key for user in UserProfile.query(UserProfile.email.IN(private_viewer_emails))]
        k = item.put()

        flash(_T('Your item has been created!'), 'success')
        return redirect(url_for('item', id=k.id(), slug=item.slug))

    return render_template('item/create.html', form=form,
                           action=blobstore.create_upload_url(url_for('item_create')),
                           title=_T('Create Item'))

@app.route('/item/')
def item_index():
    # TODO Paginate results properly, and add restrictions on kinds of queries possible.
    # TODO Partial-match search

    orderings = Item.get_orderings()
    # HACK
    ordering = request.args.get('o', 'created (descending)')
    if ordering not in orderings.keys():
        ordering = 'created (descending)'

    ext_results = []

    if 'q' in request.args:
        orderings = Item.get_search_orderings()
        current_ordering = [orderings.get(ordering)]
        if request.args['q'].strip().lower() == 'htcpcp':
            abort(418, TEAPOT)
        elif request.args['q'].strip().lower() == 'about:credits':
            return redirect('/humans.txt')
        iq = ItemQuery.search(request.args['q'].strip().lower(), current_ordering)

        # external results
        # TODO FIXME
        r = apiclient.search('https://syscan-buybase.appspot.com',
                         '11BB3F480D328E6190ECE40CC19965D29A84139996C6B0FD00BF2A34155E4BB7',
                         query='abyss', limit=1)

        logging.error(r.get_result().content)

    else:
        current_ordering = orderings.get(ordering)
        iq = ItemQuery.query(None, current_ordering, request.args.get('c'))

    try:
        items, cursor, more = iq.fetch(10)
    except QueryError:
        flash(_T('Sorry, but your query failed.'), 'error')
        return redirect(url_for('index'))

    return render_template('item/index.html', items=items, cursor=cursor,
                           has_more=more, item_orderings=orderings.keys(),
                           title=_T('Items'))

@app.route('/item/<int:id>/<string:slug>')
def item(id, slug):
    item = Item.get_or_404(id, slug)
    if current_user.is_authenticated():
        feedback = Feedback.get_or_create(item.key, current_user.key)
        feedback_form = forms.FeedbackForm(rating=feedback.rating, feedback=feedback.feedback)
    else:
        feedback_form = None
    return render_template('item/item.html', item=item, feedback_form=feedback_form,
                           user_track=item.seller.ga_id,
                           title=item.title)

@app.route('/item/<int:id>/<string:slug>/update', methods=['GET', 'POST'])
@login_required
def item_update(id, slug):
    item = Item.get_or_404(id, slug)

    if not item.editable_by(current_user):
        abort(403)

    form = ItemForm()
    if form.validate_on_submit():
        item.title = form.title.data
        item.description = form.description.data
        item.price = Price(fixed_value=form.price.data*100, currency='USD')
        item.active = form.active.data
        item.expiry = datetime.datetime.now() + datetime.timedelta(days=form.expires_in.data)
        private_viewer_emails = [_.strip() for _ in form.private_viewers.data.split(',')]
        item.private_viewer_keys = [user.key for user in UserProfile.query(UserProfile.email.IN(private_viewer_emails))]
        if form.image.has_file():
            app.logger.debug(form.image.data)
            app.logger.debug(dir(form.image.data))
            app.logger.debug(form.image.data.mimetype_params)
            blob = blobstore.parse_blob_info(to_fieldstorage(form.image.data))
            item.image = blob.key()
        item.put()

        flash(_T('Item updated'), 'success')

        return redirect(url_for('item', id=id, slug=slug))

    form = ItemForm(title=item.title, description=item.description,
                    price=item.price.fixed_value / 100, youtube=item.youtube,
                    private_viewers=','.join([user.username for user in ndb.get_multi(item.private_viewer_keys)]),
                    active=item.active)

    return render_template('item/update.html', form=form, id=id, slug=slug,
                           action=blobstore.create_upload_url(url_for('item_update', id=id, slug=slug)),
                           title=_T('Update Item') + ' %s' % item.title)

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
    users_profiles = UserProfile.query().fetch(10)
    return render_template('user/index.html', user_profiles=users_profiles, title=_T('Users'))

@app.route('/user/u/<string:id>/', methods=['GET', 'POST'])
def user(id):
    user_profile = UserProfile.get_or_404(id)
    app_config_form = None
    if current_user.has_role('admin'):
        app_config_form = forms.AppConfigForm(search_rate=user_profile.appconfig.get('search'))
        app_config_form.itemfetch_rate.data = user_profile.appconfig.get('item')
        app_config_form.migrate_rate.data = user_profile.appconfig.get('user_import')
        app_config_form.message_rate.data = user_profile.appconfig.get('send_message')
        app_config_form.suggest_rate.data = user_profile.appconfig.get('search_suggestions')
        app_config_form.ratings_rate.data = user_profile.appconfig.get('review')


    if user_profile.editable_by(current_user):
        user_profile_form = forms.UserProfileForm(name=user_profile.display_name,
                                                  bio=user_profile.bio or '',
                                                  ga_id=user_profile.ga_id,
                                                  app_key=user_profile.app_key)
        if user_profile_form.validate_on_submit():
            user_profile.name = user_profile_form.name.data
            user_profile.bio = user_profile_form.bio.data
            user_profile.ga_id = user_profile_form.ga_id.data
            if user_profile.app_key != user_profile_form.app_key.data:
                user_profile.reset_app_key()
                user_profile_form.app_key.data = user_profile.app_key
            user_profile.put()
            flash(_LT('Your profile has been updated!'), 'success')
    else:
        user_profile_form = None

    return render_template('user/user.html', user_profile=user_profile, user_profile_form=user_profile_form,
                           title=user_profile.display_name, app_config_form=app_config_form)

@app.route('/user/u/<string:id>/appconfig', methods=['POST'])
def user_appconfig(id):
    if not current_user.has_role('admin'):
        return redirect(url_for('index'))

    user_profile = UserProfile.get_or_404(id)

    appconfig_form = forms.AppConfigForm()

    if appconfig_form.validate_on_submit():

        user_profile.appconfig = {
            'search': appconfig_form.search_rate.data,
            'item': appconfig_form.itemfetch_rate.data,
            'user_import': appconfig_form.migrate_rate.data,
            'send_message': appconfig_form.message_rate.data,
            'search_suggestions': appconfig_form.suggest_rate.data,
            'review': appconfig_form.ratings_rate.data
        }
        user_profile.put()

        return redirect(url_for('index'))


# TODO FIXME make this POST only + CSRF PROTECTION
@app.route('/user/u/<string:id>/migrate', methods=['GET', 'POST'])
@condition_required(lambda id: UserProfile.get_or_404(id).editable_by(current_user))
def user_migrate(id):
    user_profile = UserProfile.get_or_404(id)
    apiclient.user_import_client('https://ceciliasecucsb.appspot.com',
                                 'fa2a4c3ecf732d15b32df246371d69cb94bd4679',
                                 user_profile)

    # apiclient.user_import_client('https://syscan-buybase.appspot.com',
    #                              '11BB3F480D328E6190ECE40CC19965D29A84139996C6B0FD00BF2A34155E4BB7',
    #                              user_profile)




@app.route('/user/u/<string:id>/deactivate', methods=['POST'])
@condition_required(lambda id: UserProfile.get_or_404(id).editable_by(current_user))
def user_deactivate(id):
    form = forms.UserDeactivateForm()
    user_profile = UserProfile.get_or_404(id)

    if current_user.has_role('admin') and user_profile == current_user:
        flash(_T('Sorry, but administrators cannot deactivate their own accounts.'), 'error')
        flash(_T('Please ask another administrator to deactivate your account.'), 'info')
        return redirect(user_profile.url())

    if form.validate_on_submit():
        user_profile.active = not user_profile.active
        user_profile.put()

        # flipped, because we've just activated/deactivated
        flash('%s has successfully been %sactivated!' %
              (user_profile.display_name, '' if user_profile.active else 'de'), 'success')

    if user_profile != current_user:
        logging.info('%s\'s account has been deactivated', user_profile.display_name)

        return redirect(user_profile.url())
    else:
        abort(403)

@app.route('/user/u/<string:id>/delete', methods=['GET', 'POST'])
@condition_required(lambda id: UserProfile.get_or_404(id) == current_user)
def user_delete(id):
    form = forms.UserDeleteForm()
    user_profile = UserProfile.get_or_404(id)

    if current_user.has_role('admin'):
        flash(_T('Sorry, but administrators cannot delete their accounts.'), 'error')
        flash(_T('Please ask another administrator to deactivate your account, or to make you a regular user.'), 'info')
        return redirect(url_for('user', id=id))

    if form.validate_on_submit():
        logout_user()
        user.delete()

        flash(_T('Your account has successfully been deleted.'))

        if user_profile != current_user:
            logging.info('%s\'s account has been deleted', user_profile.display_name)

        return redirect(url_for('index'))

    return render_template('user/delete.html', user_profile=user_profile, user_delete_form=form,
                           title=_T('Delete User'))

@app.route('/message/')
@login_required
def message_index():
    c_page = Conversation.list_query(current_user).fetch_page(10)
    return render_template('message/index.html', conversations=c_page[0], cursor=c_page[1], has_more=c_page[2],
                           title=_T('Messages'))

@app.route('/message/send', methods=['GET', 'POST'])
@login_required
def message_send():
    form = forms.MessageSendForm(to=request.args.get('to', ''),
                                 subject=request.args.get('subject', ''))

    if form.validate_on_submit():
        to = UserProfile.query(UserProfile.email.IN(map(lambda un: un.strip(), form.to.data.split(',')))).fetch(1000)

        if form.subject.data:
            item = None
            try:
                item = Item.get_by_id(long(form.subject.data))
            except ValueError: pass
            if not item:
                flash(_LT('Subject must be a valid item ID.'), 'error')
                return redirect(url_for('message_send'))

            if item.seller_id != to[0].get_id() or len(to) > 1:
                flash(_LT('Messages about items can only be sent to their sellers!'), 'error')
                return redirect(item.url())

        message_key, conv_key = Message.send(current_user, to, form.subject.data, form.message.data)
        return redirect(url_for('message_conversation', id=conv_key.id()) + '#message_%s' % message_key.id())

    return render_template('message/send.html', message_send_form=form,
                           title=_T('Send Message'))


@app.route('/message/conversation/<int:id>')
@login_required
def message_conversation(id):
    c = Conversation.get_by_id(id)
    form = forms.MessageSendForm(to=', '.join([p.display_name for p in c.participants if p != current_user]),
                                 subject=c.subject)

    if not c:
        abort(404)

    if current_user.key not in c.participant_keys:
        abort(403)

    page = Message.query(Message.to == c.key).fetch_page(10)

    return render_template('message/conversation.html', conversation=c, messages=page[0], cursor=page[1],
                           has_more=page[2], message_send_form=form,
                           title=c.readable_subject)

@app.route('/feedback/<string:key>/add', methods=['POST'])
@login_required
def feedback_add(key):
    k = ndb.Key(urlsafe=key)

    form = forms.FeedbackForm()

    if form.validate_on_submit():
        Feedback.add_or_update(k, current_user.key, form.rating.data, form.feedback.data)
        flash(_LT('Your feedback has been submitted. Thanks!'), 'success')
        return redirect(request.args.get('next', url_for('item_index')))

    return redirect(url_for('item', id=k.id(), slug=k.get().slug))

@app.route('/collection/')
def collection_index():
    cq = Collection.query(Collection.author_key == current_user.key)
    collections, cursor, has_more = cq.fetch_page(10)
    return render_template('collection/index.html', collections=collections, cursor=cursor, has_more=has_more,
                           title=_T('Collections'))

@app.route('/collection/<int:id>/')
def collection(id):
    c = Collection.get_by_id(id)
    return render_template('collection/collection.html', collection=c,
                           user_track=item.seller.ga_id,
                           title=c.title)

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

    return render_template('collection/create.html', collection_form=collection_form,
                           title=_T('Create Collection'))


@app.route('/user/data-liberation/')
@app.route('/user/data-liberation/<string:filename>')
@login_required
def data_liberation(filename=None):
    if not filename:
        return redirect(url_for('data_liberation',
                                filename=datetime.datetime.now().ctime().replace(' ', '-').replace(':', '-') +
                                         '-%s.zip' % current_user.display_name))
    # XXX Do this in a background task, cache, etc.
    from datalib import generate_zip
    zip = generate_zip(current_user.get_id())
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

@app.route('/_ah/mail/<string:address>', methods=['POST'])
def mail(address):
    message = InboundEmailMessage(request.data)
    return '' if notify.handle_inbound_email(address, message) else abort(500)

from api import *
