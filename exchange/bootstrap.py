__author__ = 'aviraldg'

from google.appengine.ext.ndb import put_multi_async, put_multi, Key
from .models import UserProfile, Item, Price
from .utils import slugify

def do_bootstrap(item_count=250, user_count=25):
    user_keys = put_multi_async(_gen_users(user_count))
    put_multi(_gen_items(user_keys, item_count))

def _gen_users(user_count):
    for i in xrange(user_count):
        # AppEngine behaves in a rather funny way if you try to mix numerical IDs, string IDs, and numerical IDs in
        # strings
        user = UserProfile(id='testuser%s' % i)
        user.name = 'Test User %s' % i
        user.username = 'testuser%s' % i
        user.email = user.username + '@test.com'
        user.active = True
        yield user

def _gen_items(user_keys, item_count):
    user_keys_len = len(user_keys)
    for i in xrange(item_count):
        u = i % user_keys_len
        user_key = user_keys[u]
        if not isinstance(user_key, Key):
            user_key = user_keys[u] = user_keys[u].get_result()

        item = Item()
        item.title = 'Item %s' % i
        item.seller_id = unicode(user_key.id())
        item.slug = slugify(item.title)
        item.description = 'Description for item %s' % i
        item.price = Price(fixed_value=(i + 1) * 100, currency='USD')
        yield item
