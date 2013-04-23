__author__ = 'aviraldg'

import re
from unicodedata import normalize
from .models import Item
from flask.ext.login import current_user
from google.appengine.api import search
from google.appengine.ext import ndb
from google.appengine.datastore.datastore_query import Cursor
from cgi import FieldStorage

# Why is this here? (who knows?)

TEAPOT = '''I'm a little teapot,
Short and stout,
Here is my handle,
Here is my spout,
When I get all steamed up,
Hear me shout,
Tip me over and pour me out!
'''.replace('\n', '<br>')


class ItemQuery:
    """
    Unified interface for searching and querying Items.
    """

    FETCH_BATCH_SIZE = 20

    def __init__(self, query, ordering, type, cursor_string):
        self.query = query
        self.ordering = ordering
        self.type = type
        self.cursor_string = cursor_string

    @staticmethod
    def search(query, ordering=[], cursor_string=None):
        return ItemQuery(query, ordering, 'search', cursor_string)

    @staticmethod
    def query(query=None, ordering=[], cursor_string=None):
        return ItemQuery(query, ordering, 'query', cursor_string)


    def fetch(self, count=10, offset=None):
        """
        Fetch `count` items from the query/search results.

        :returns (items, cursor, has_more)
        """

        if self.type == 'search':
            items = []
            cursor = search.Cursor(web_safe_string=self.cursor_string, per_result=True)

            while count > 0:
                if offset:
                    results = Item.index.search(search.Query(self.query,
                                                             options=search.QueryOptions(
                                                                 limit=ItemQuery.FETCH_BATCH_SIZE,
                                                                 offset=offset,
                                                                 sort_options=search.SortOptions(
                                                                     [self.ordering], limit=1000
                                                                 )
                                                             )))
                else:
                    results = Item.index.search(search.Query(self.query,
                                                             options=search.QueryOptions(
                                                                 limit=ItemQuery.FETCH_BATCH_SIZE,
                                                                 cursor=cursor,
                                                                 sort_options=search.SortOptions(
                                                                     [self.ordering], limit=1000
                                                                 )
                                                             )))
                if len(results.results) == 0:
                    return items, None, False
                r_items = ndb.get_multi([ndb.Key(Item, long(result.doc_id)) for result in results.results])

                for i, item in enumerate(r_items):
                    if item.viewable_by(current_user):
                        items.append(item)
                        count -= 1
                        if count == 0:
                            break

                cursor = results.results[i].cursor

            return items, cursor.web_safe_string if cursor else None, True
        elif self.type == 'query':
            items = []
            results = Item.query(*(self.query if self.query else []),
                                 default_options=ndb.QueryOptions(start_cursor=Cursor(urlsafe=self.cursor_string)))
            results = results.order(self.ordering)
            r_iter = results.iter(produce_cursors=True)
            cursor_string = None
            for item in r_iter:
                if item.viewable_by(current_user):
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
    text = unicode(text)
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

def split_xid(xid):
    """
    Splits an external ID into an id, slug pair
    :param xid:
    :return:
    """

    id_end = xid.find('$')
    return int(xid[:id_end]), xid[id_end+1:]
