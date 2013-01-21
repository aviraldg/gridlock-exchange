from __future__ import division

__author__ = 'aviraldg'

from google.appengine.ext import ndb

class UserProfile(ndb.Model):
    user_id = ndb.StringProperty(indexed=True)
    bio = ndb.StringProperty(default="")

def price_value_validator(property, value):
    if value <= 0:
        raise ValueError('Price value must be nonzero')

    return int(value)

class Price(ndb.Model):
    # Fixed-point price
    fixed_value = ndb.IntegerProperty(required=True,
        validator=price_value_validator)
    value = ndb.ComputedProperty(lambda self: self.fixed_value/100)
    currency = ndb.TextProperty()

class Item(ndb.Model):
    title = ndb.StringProperty(required=True)
    slug = ndb.StringProperty(required=True, indexed=True)
    seller_id = ndb.StringProperty(required=True)
    description = ndb.StringProperty(default=u'')
    created = ndb.DateTimeProperty(auto_now_add=True)
    expiry = ndb.DateTimeProperty()
    price = ndb.StructuredProperty(Price, required=True)
