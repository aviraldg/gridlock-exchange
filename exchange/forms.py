__author__ = 'aviraldg'

from flask.ext import wtf

class UserProfileForm(wtf.Form):
    bio = wtf.TextAreaField("bio")
