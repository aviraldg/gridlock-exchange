__author__ = 'aviraldg'

from . import app
from flask import request, jsonify
from flask.ext.login import current_user
from .utils import ItemQuery, split_xid
from .models import Item


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
