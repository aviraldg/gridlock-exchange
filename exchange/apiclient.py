__author__ = 'aviraldg'

from google.appengine.api import urlfetch
import urllib

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
