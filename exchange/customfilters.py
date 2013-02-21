__author__ = 'aviraldg'

from . import app
from hashlib import md5

@app.template_filter('gravatar_url')
def gravatar_url(email, size=32):
    return '//www.gravatar.com/avatar/%s?s=%s&d=retro' % (md5(email.lower().strip()).hexdigest(), size)
