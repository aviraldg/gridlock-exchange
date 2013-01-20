from __future__ import division

__author__ = 'aviraldg'

from google.appengine.ext import ndb

class Price(ndb.model):
    # Fixed-point price
    fixed_value = ndb.IntegerProperty(required=True,
        validator=Price.value_validator)
    value = ndb.ComputedProperty(lambda self: self.fixed_value/100)
    currency = ndb.TextProperty()

    @staticmethod
    def value_validator(property, value):
        if value <= 0:
            raise ValueError('Price value must be nonzero')

        return int(value)

class Item(ndb.Model):
    title = ndb.StringProperty()
    slug = ndb.StringProperty(required=True, indexed=True)
    description = ndb.StringProperty()
    created = ndb.DateTimeProperty(auto_now_add=True)
    price = ndb.StructuredProperty(Price)
