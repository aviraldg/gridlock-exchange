from __future__ import division

__author__ = 'aviraldg'

from google.appengine.ext import ndb
from pbkdf2 import crypt
from flask import config
from . import login_manager

class UserProfile(ndb.Model):
    bio = ndb.StringProperty(default="")


class User(ndb.Model):
    CRYPTO_ITER = 10000

    username = ndb.StringProperty(indexed=True)
    password = ndb.StringProperty()
    name = ndb.StringProperty()
    email = ndb.StringProperty()
    active = ndb.BooleanProperty()
    profile = ndb.StructuredProperty(UserProfile)

    @staticmethod
    def authenticate(username, password):
        """
        Tries to authenticate with the given username and password and returns
        a User instance if successful, None otherwise.
        """

        user = User.query(User.username == username).get()
        if not user:
            return None

        if user.check_password(password):
            return user
        else:
            return None

    def is_authenticated(self):
        return

    def is_active(self):
        return self.active

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.key)

    def set_password(self, raw_password):
        """
        Hash, salt and save raw_password for the user using PBKDF2.
        """

        salt = crypt(config.SECRET_KEY, iterations=self.CRYPTO_ITER)
        self.password = crypt(raw_password, salt, self.CRYPTO_ITER)

    def check_password(self, raw_password):
        """
        Check if raw_password matches the user's current password.
        """
        from .utils import secure_compare

        algo, iterations, salt = self.password.split('$')[1:4]

        if algo != 'p5k2':
            raise ValueError('check_password can\'t handle %s' % algo)

        return secure_compare(self.password, crypt(raw_password,
            salt, iterations))

@login_manager.user_loader
def load_user(user_key):
    return User.get(user_key)


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
