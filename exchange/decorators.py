__author__ = 'aviraldg'

from flask import abort
from flask.ext.login import current_user
from functools import wraps

def role_required(role):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if (not current_user.is_authenticated()) or (not current_user.has_role(role)):
                abort(401)
            return fn(*args, **kwargs)
        return wrapped
    return decorator

def condition_required(validator):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if not validator(*args, **kwargs):
                abort(401)
            return fn(*args, **kwargs)
        return wrapped
    return decorator
