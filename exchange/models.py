# coding=utf-8
from __future__ import division

__author__ = 'aviraldg'

from google.appengine.ext import ndb
from google.appengine.api import search
from pbkdf2 import crypt
from flask import config, url_for, abort
from babel.numbers import format_currency
from flask.ext.login import AnonymousUser
from hashlib import sha512
from . import app, login_manager


class UserProfile(ndb.Model):
    bio = ndb.StringProperty(default='')


class User(ndb.Model):
    CRYPTO_ITER = 10000

    username = ndb.StringProperty(indexed=True)
    password = ndb.StringProperty()
    name = ndb.StringProperty()
    email = ndb.StringProperty()
    active = ndb.BooleanProperty(default=True)
    profile = ndb.StructuredProperty(UserProfile)
    roles = ndb.StringProperty(repeated=True)

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

    @staticmethod
    def get_or_404(id, username):
        """
        Get the User if it exists, otherwise abort with a 404
        :param id:
        :param username:
        :return: the user object
        """

        user = User.get_by_id(id)

        if not user or user.username != username:
            abort(404)

        return user

    def __str__(self):
        return self.username

    def __repr__(self):
        return 'User: %s' % str(self)

    def is_authenticated(self):
        return True

    def is_active(self):
        return self.active

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.key.id())

    def set_password(self, raw_password):
        """
        Hash, salt and save raw_password for the user using PBKDF2.
        """

        salt = crypt(app.config['SECRET_KEY'], iterations=self.CRYPTO_ITER)
        self.password = crypt(raw_password, salt, self.CRYPTO_ITER)

    def check_password(self, raw_password):
        """
        Check if raw_password matches the user's current password.
        """
        from .utils import secure_compare

        algo, iterations, salt = self.password.split('$')[1:4]
        # the number of iterations is stored in base16
        iterations = int(iterations, 16)

        if algo != 'p5k2':
            raise ValueError('check_password can\'t handle %s' % algo)

        return secure_compare(self.password, crypt(raw_password,
                                                   salt, iterations))

    def has_role(self, role):
        """
        Checks if a user has a particular role.
        """
        return role in self.roles

    def editable_by(self, user):
        return user.get_id() == self.get_id() or user.has_role('admin')

    def url(self):
        return url_for('user', id=self.get_id(), username=self.username)

    def delete(self):
        self.key.delete()


class CustomAnonymousUser(AnonymousUser):
    def has_role(self, role):
        return False

    def editable_by(self, user):
        return False


@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(int(user_id))


def price_value_validator(property, value):
    if int(value) <= 0:
        raise ValueError('Price value must be > 0')

    return int(value)


class Keyword(ndb.Model):
    keyword = ndb.StringProperty(required=True)


class Price(ndb.Model):
    # Fixed-point price
    fixed_value = ndb.IntegerProperty(required=True,
                                      validator=price_value_validator)
    value = ndb.ComputedProperty(lambda self: self.fixed_value / 100)
    currency = ndb.TextProperty()

    def __str__(self):
        return self.get_formatted_value()

    def get_formatted_value(self):
        # TODO: Don't hardcode the locale
        return format_currency(self.value, self.currency, locale='en_US')


class Item(ndb.Model):
    index = search.Index(name='Item')

    title = ndb.StringProperty(required=True)
    slug = ndb.StringProperty(required=True, indexed=True)
    seller_id = ndb.StringProperty(required=True)
    description = ndb.StringProperty(default=u'')
    created = ndb.DateTimeProperty(auto_now_add=True)
    expiry = ndb.DateTimeProperty(default=None)
    price = ndb.StructuredProperty(Price, required=True)
    active = ndb.BooleanProperty(default=True)

    _search_fields = ('title', 'description')
    keywords = ndb.StructuredProperty(Keyword, repeated=True)

    @staticmethod
    def _keywordize(value):
        from .utils import punct_re

        value = str(value)
        return punct_re.split(value.strip().lower())

    @staticmethod
    def get_or_404(id, slug):
        """
        Get the Item if it exists, or abort with a 404.
        :param id:
        :param slug:
        :return: the item
        """
        item = Item.get_by_id(id)

        if item is None or item.slug != slug:
            abort(404)

        return item

    def _pre_put_hook(self):
        keywords = set()
        for field in self._search_fields:
            keywords = keywords.union(Item._keywordize(getattr(self, field)))
        self.keywords = [Keyword(keyword=__) for __ in keywords]

    def _post_put_hook(self, future):
        app.logger.info('Item %s/%s updated.' % (self.key.id(), self.slug))

        Item.index.put(self._to_document(id=str(future.get_result().id())))

    @classmethod
    def _post_delete_hook(cls, key, future):
        Item.index.delete(str(key.id()))

    def __str__(self):
        return str(self.slug)

    def __repr__(self):
        return 'Item: %s' % str(self)

    def url(self):
        return url_for('item', id=self.key.id(), slug=self.slug)

    def editable_by(self, user):
        return user.get_id() == unicode(self.seller_id) or user.has_role('admin')

    def _to_document(self, id=None):
        """
        Returns a Search API document for (the current property values of) this Item.
        :return: an :py:class:`appengine.api.search.Document`
        """

        return search.Document(
            doc_id=id if id else self.key.id(),
            fields=[
                search.TextField(name='title', value=self.title),
                search.TextField(name='description', value=self.description),
                search.TextField(name='price', value=self.price.get_formatted_value())
            ]
        )


class Conversation(ndb.Model):
    """
    A conversation is a group of messages exchanged between a number of participants on a specific topic.
    """

    # The validator is used to make this behave like a Set
    participant_keys = ndb.KeyProperty(repeated=True, kind=User)#, validator=lambda prop, value: sorted(set(value)))
    # Since we can't do exact queries on repeated properties, this sounds like a good workaround.
    phash = ndb.ComputedProperty(lambda self: Conversation._gen_phash(self.participant_keys))
    # This can either be the ID of an Item (if the conversation is about an item) or empty (if it's a direct message)
    readable_subject = ndb.StringProperty(default='')
    subject = ndb.StringProperty(default='')
    messages = ndb.KeyProperty(repeated=True, kind='Message')
    updated = ndb.DateTimeProperty(auto_now=True)

    def _pre_put_hook(self):
        if self.readable_subject == '':
            self.readable_subject = 'With %s' % ', '.join(map(lambda u: u.username,
                                                              ndb.get_multi(self.participant_keys)))
            if self.subject != '':
                self.readable_subject += ' about %s' % str(Item.get_by_id(self.subject))
            else:
                self.readable_subject += ' (direct message)'

    @staticmethod
    def _gen_phash(participant_keys):
        return sha512(','.join(map(lambda k: str(k.id()), participant_keys))).hexdigest()

    @staticmethod
    def get_or_create(participant_keys, subject):
        p_keys = list(sorted(set(participant_keys)))
        phash = Conversation._gen_phash(p_keys)
        q = Conversation.query(ndb.AND(Conversation.phash == phash, Conversation.subject == subject))
        q = q.fetch(1)

        if not q:
            q = Conversation()
            q.participant_keys = p_keys
            q.subject = subject
            q.put()
        else:
            q = q[0]

        return q

    @staticmethod
    def list_query(user):
        c_query = Conversation.query(Conversation.participant_keys == user.key)
        return c_query


class Message(ndb.Model):
    author_key = ndb.KeyProperty(kind=User)

    @property
    def author(self):
        return self.author_key.get()

    content = ndb.TextProperty()
    to = ndb.KeyProperty(kind=Conversation)
    sent = ndb.DateTimeProperty(auto_now_add=True)

    @staticmethod
    def send(author, to, subject, content):
        author_key = author.key
        to_keys = set(map(lambda t: t.key, to))

        conversation = Conversation.get_or_create(to_keys.union({author_key}), subject)

        message = Message(author_key=author_key, to=conversation.key, content=content)
        message.put()

        conversation.messages.append(message.key)
        conversation.put()

