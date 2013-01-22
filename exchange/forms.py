__author__ = 'aviraldg'

from flask.ext import wtf

class LoginForm(wtf.Form):
    username = wtf.TextField('Username', validators=(wtf.required(),))
    password = wtf.PasswordField('Password', validators=(wtf.required(),))
    remember = wtf.BooleanField('Remember me')


class UserProfileForm(wtf.Form):
    bio = wtf.TextAreaField("bio")
