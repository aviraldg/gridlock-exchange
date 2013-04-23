__author__ = 'aviraldg'

from . import app
from flask import request, jsonify
from .utils import ItemQuery
from .models import Item

@app.route('/webservices/search')
def search():
    try:
        query = request.args['query']
    except KeyError:
        # needs a query
        return jsonify(success=False, message='no query provided')

    limit = int(request.args.get('limit', 10))
    if limit > 1000: limit = 1000

    offset = int(request.args.get('offset', 0))

    ordering = Item.get_search_orderings().get('created (descending)')
    iq = ItemQuery.search(query.strip().lower(), ordering)
    items, cursor, more = iq.fetch(count=limit, offset=offset)
    return jsonify(items=[item.as_pyo() for item in items])

