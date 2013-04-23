__author__ = 'aviraldg'

from . import app
from flask import request, jsonify
from flask.ext.login import current_user
from .utils import ItemQuery, split_xid
from .models import Item, UserProfile
from google.appengine.ext import ndb


@app.route('/webservices/')
def webservices():
    return jsonify(version=1, methods=['search', 'item'])

@app.route('/webservices/search')
def search():
    # TODO XXX Check if this auth token has required permissions/rate limit.
    if 'auth_token' not in request.args:
        return jsonify(success=False, message='0 access denied (bad auth token or rate limit reached)')

    try:
        query = request.args['query']
    except KeyError:
        # needs a query
        return jsonify(success=False, message='1 no query provided')

    limit = int(request.args.get('limit', 10))
    if limit > 1000: limit = 1000

    offset = int(request.args.get('offset', 0))

    ordering = Item.get_search_orderings().get('created (descending)')
    iq = ItemQuery.search(query.strip().lower(), ordering)
    items, cursor, more = iq.fetch(count=limit, offset=offset)
    return jsonify(success=True, items=[item.as_pyo() for item in items])

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

