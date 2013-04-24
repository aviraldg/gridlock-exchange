__author__ = 'aviraldg'

from . import app
from flask import request, jsonify
from flask.ext.login import current_user
from .utils import ItemQuery, split_xid, conv_ext_ordering
from .models import Item, UserProfile, Message, ExternalUserProfile
from google.appengine.ext import ndb
from google.appengine.api.search import SortExpression
from google.appengine.api import memcache
import json
import time


def can_do(method, auth_token):
    try:
        appconfig = UserProfile.query(UserProfile.raw_app_key == auth_token).fetch(1)[0].appconfig
    except: # FIXME
        return False

    leftquota = memcache.get('$'.join([auth_token, method, 'leftquota']))
    if leftquota == None:
        leftquota = appconfig.get(method, 0)
        memcache.set('$'.join([auth_token, method, 'leftquota']), leftquota)
    else:
        leftquota = int(leftquota)

    lastcall = memcache.get('$'.join([auth_token, method, 'lastcall']))
    if lastcall:
        lastcall = int(lastcall)

    if lastcall == None or (time.time() - lastcall) >= 60:
        leftquota = int(appconfig.get(method, 0))
        memcache.set('$'.join([auth_token, method, 'leftquota']), leftquota)

    if lastcall == None:
        lastcall = time.time()
        memcache.set('$'.join([auth_token, method, 'lastcall']), lastcall)

    if leftquota <= 0:
        return False
    else:
        return True

@app.route('/webservices/')
def webservices():
    return jsonify(version=1, methods=['search', 'item', 'user_import', 'send_message', 'search_suggestions'])

@app.route('/webservices/search')
def search():
    # TODO XXX Check if this auth token has required permissions/rate limit.
    if ('auth_token' not in request.args) or (not can_do('search', request.args['auth_token'])):
        return jsonify(success=False, message='0 access denied (bad auth token or rate limit reached)')

    try:
        query = request.args['query']
    except KeyError:
        # needs a query
        return jsonify(success=False, message='1 no query provided')

    limit = int(request.args.get('limit', 10))
    if limit > 1000: limit = 1000

    offset = int(request.args.get('offset', 0))

    so = request.args.get('sort_options')
    if so:
        things = []
        for thing in conv_ext_ordering(json.loads(so)):
            if thing.startswith('-'):
                dir = SortExpression.DESCENDING
                attr = thing[1:]
            else:
                dir = SortExpression.ASCENDING
                attr = thing
            things.append(SortExpression(expression=attr, direction=dir))
        ordering = things
    else:
        ordering = [SortExpression(expression='created', direction=SortExpression.DESCENDING)]
        #ordering = Item.get_search_orderings().get('created (descending)')
    iq = ItemQuery.search(query.strip().lower(), ordering)
    items, cursor, more = iq.fetch(count=limit, offset=offset)
    return jsonify(total=offset+len(items)+limit*(1 if more else 0),
                   success=True,
                   message='- success',
                   items=[item.as_pyo() for item in items])

@app.route('/webservices/item')
def item():
    # TODO XXX Check if this auth token has required permissions/rate limit.
    if 'auth_token' not in request.args:
        return jsonify(success=False, message='0 access denied (bad auth token or rate limit reached)')

    try:
        item_id = request.args['item_id']
    except KeyError:
        # needs an item_id
        return jsonify(success=False, message='1 no item id provided')

    item = Item.get_or_404(*(split_xid(item_id)))

    if not item.viewable_by(current_user):
        return jsonify(success=False, message='0 access denied (item cannot be viewed by current client)')

    return jsonify(success=True, **(item.as_pyo()))

@app.route('/webservices/user_import', methods=['GET', 'POST'])
def user_import():
    # TODO XXX Check if this auth token has required permissions/rate limit.
    if 'auth_token' not in request.args:
        return jsonify(success=False, message='0 access denied (bad auth token or rate limit reached)')

    if 'user_data' not in request.args:
        return jsonify(success=False, message='1 no user data provided')

    # TODO XXX Run this in a transaction.
    data = request.args.get('user_data')

    # create user
    # NOTE We're trusting that the values from the remote service will be correct ie. no validation here
    # This is probably less robust than it should be. TODO Clarify & modify?
    profile = UserProfile.for_user(data['user_id'])
    profile.bio = data['bio']
    profile.name = data['name']
    profile.ga_id = data['ga_id']
    # other user props
    profile.put_async()

    items = []

    for item_desc in data['items']:
        item = Item(**item_desc)
        item.seller_id = profile.get_id()
        items.append(item)

    ndb.put_multi_async(items)

    # if everything above succeeded
    return jsonify(success=True)

@app.route('/webservices/send_message', methods=['GET', 'POST'])
def send_message():
    # TODO XXX Check if this auth token has required permissions/rate limit.
    if 'auth_token' not in request.args:
        return jsonify(success=False, message='0 access denied (bad auth token or rate limit reached)')

    auth_token = request.args['auth_token']

    topic_item = request.args.get('item_id', None)
    topic_item = int(topic_item) if topic_item != None else None

    try:
        source_user_id = request.args['source_user_id']
        source_user_name = request.args['source_user_name']
        destination_user_id = request.args['destination_user_id']
        subject = request.args.get('subject', '')
        message = request.args['message']
        source_conversation_id = request.args['source_conversation_id']
        destination_conversation_id = request.args['destination_conversation_id']
    except KeyError:
        return jsonify(success=False, message='1 required argument missing')

    author = ExternalUserProfile.for_ext_id(auth_token, source_user_id, source_user_name)
    to = [UserProfile.get_or_404(destination_user_id)]

    message_key, conv_key = Message.send(author=author, subject=topic_item, content=message,
                                         to=to, do_notify=False, extra=source_conversation_id)

    return jsonify(dict(success=True, conversation_id=str(conv_key)))


@app.route('/webservices/search_suggestions')
def search_suggestions():
    # TODO XXX Check if this auth token has required permissions/rate limit.
    if 'auth_token' not in request.args:
        return jsonify(success=False, message='0 access denied (bad auth token or rate limit reached)')

    auth_token = request.args['auth_token']

    try:
        query = request.args['query']
    except KeyError:
        # needs a query
        return jsonify(success=False, message='1 no query provided')

    # TODO limit
    results = Item.query(ndb.AND(Item.title >= query.upper(), Item.title < query+unichr(0xFFFF))).fetch(10)

    return jsonify({
        'success': True,
        'items': [result.as_pyo() for result in results]
    })
