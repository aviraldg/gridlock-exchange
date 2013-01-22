__author__ = 'aviraldg'

from flask.ext import wtf

class LoginForm(wtf.Form):
    username = wtf.TextField('Username')
    password = wtf.PasswordField('Password')
    remember = wtf.BooleanField('Remember me')


class UserProfileForm(wtf.Form):
    bio = wtf.TextAreaField("bio")
