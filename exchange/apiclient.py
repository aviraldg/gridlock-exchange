__author__ = 'aviraldg'

from google.appengine.api import urlfetch
from models import Item
import urllib
import json
import logging

TIMEOUT = 2

def search(baseurl, token, query, offset=0, limit=10):
    url = baseurl + '/webservices/search'
    rpc = urlfetch.create_rpc(TIMEOUT)

    data = {
        'auth_token': token,
        'query': query,
        'offset': offset,
        'limit': limit,
    }

    urlfetch.make_fetch_call(rpc, url, urllib.urlencode(data),
                             method=urlfetch.POST,
                             headers={'Content-Type': 'application/x-www-form-urlencoded'})

    return rpc

def user_import_client(baseurl, token, user_profile):
    url = baseurl + '/webservices/user_import'

    up_pyo = user_profile.as_pyo()
    up_pyo['items'] = [item.as_pyo() for item in Item.query(Item.seller_id == user_profile.get_id())]

    up_pyo = {
        'user_data': json.dumps(up_pyo)
    }

    logging.error(json.dumps(up_pyo))

    result = urlfetch.fetch(url, payload=urllib.urlencode(up_pyo), method=urlfetch.POST,
                   headers={'Content-Type': 'application/x-www-form-urlencoded'})

    logging.error(result.content)

    result = json.loads(result.content)
    if result['success']:
        pass # delete

    suggestions_client(baseurl, token, 'item')

def suggestions_client(baseurl, token, query):
    url = baseurl + '/webservices/search_suggestions'

    data = {
        'auth_token': token,
        'query': query
    }

    result = urlfetch.fetch(url, payload=urllib.urlencode(data), method=urlfetch.POST,
                            headers={'Content-Type': 'application/x-www-form-urlencoded'})

    logging.error(result.content)
