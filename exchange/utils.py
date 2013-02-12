__author__ = 'aviraldg'

import re
from unicodedata import normalize
from .models import Item
from flask.ext.login import current_user
from google.appengine.api import search
from google.appengine.ext import ndb
from google.appengine.datastore.datastore_query import Cursor
from cgi import FieldStorage


class ItemQuery:
    """
    Unified interface for searching and querying Items.
    """

    FETCH_BATCH_SIZE = 20

    def __init__(self, query, type, cursor_string):
        self.query = query
        self.type = type
        self.cursor_string = cursor_string

    @staticmethod
    def search(query, cursor_string=None):
        return ItemQuery(query, 'search', cursor_string)

    @staticmethod
    def query(query=None, cursor_string=None):
        return ItemQuery(query, 'query', cursor_string)


    def fetch(self, count=10):
        """
        Fetch `count` items from the query/search results.

        :returns (items, cursor, has_more)
        """

        if self.type == 'search':
            items = []
            cursor = search.Cursor(self.cursor_string, per_result=True)

            while count > 0:
                results = Item.index.search(search.Query(self.query,
                                                         options=search.QueryOptions(
                                                             limit=ItemQuery.FETCH_BATCH_SIZE,
                                                             cursor=cursor
                                                         )))
                if len(results.results) == 0:
                    return items, None, False
                r_items = ndb.get_multi([ndb.Key(Item, long(result.doc_id)) for result in results.results])

                for i, item in enumerate(r_items):
                    if item.active or item.seller_id == current_user.get_id():
                        items.append(item)
                        count -= 1
                        if count == 0:
                            break

                cursor = results.results[i].cursor

            return items, cursor.web_safe_string, True
        elif self.type == 'query':
            items = []
            results = Item.query(*(self.query if self.query else []),
                                 default_options=ndb.QueryOptions(start_cursor=Cursor(urlsafe=self.cursor_string)))
            r_iter = results.iter(produce_cursors=True)
            cursor_string = None
            for item in r_iter:
                if item.active or item.seller_id == current_user.get_id():
                    items.append(item)
                    count -= 1
                if count == 0:
                    if r_iter.has_next():
                        cursor_string = r_iter.cursor_after().urlsafe()
                    break
            return items, cursor_string, r_iter.has_next()


def secure_compare(s1, s2):
    """
    Avoid timing attacks by taking constant time for compares.
    """

    if len(s1) != len(s2):
        return False

    eq = True
    for i, j in zip(s1, s2):
        if i != j:
            eq = False
    return eq

punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')

def slugify(text, delim=u'-'):
    result = []
    for word in punct_re.split(text.lower()):
        word = normalize('NFKD', word).encode('ascii', 'ignore')
        if word:
            result.append(word)
    return unicode(delim.join(result))

def to_fieldstorage(f):
    fs = FieldStorage()
    fs.file = f
    fs.type = f.mimetype
    opt = f.mimetype_params
    opt['filename'] = f.filename
    fs.disposition_options = opt
    fs.type_options = opt
    return fs
