from flask.ext.wtf import Form, TextField, PasswordField, TextAreaField, \
    BooleanField, email, required, length
from flask.ext.wtf import html5, file
from flask.ext.login import current_user
from wtforms import ValidationError
from wtforms.validators import number_range
from flask.ext.babel import gettext as _T, lazy_gettext as _LT
from google.appengine.api import images

__author__ = 'aviraldg'

class RegisterForm(Form):
    username = TextField(_LT('Username'), validators=[required()])
    name = TextField(_LT('Name'), validators=[required()])
    email = html5.EmailField(_LT('Email'), validators=(email(), required()))
    password = PasswordField(_LT('Password'), validators=[length(min=10)])


class LoginForm(Form):
    username = TextField(_LT('Username'), validators=[required()])
    password = PasswordField(_LT('Password'), validators=[required()])
    remember = BooleanField(_LT('Remember me'))


class LogoutForm(Form):
    pass # This form is only used for CSRF protection.


class UserProfileForm(Form):
    bio = TextAreaField("bio")


class ItemForm(Form):
    title = TextField(_LT('Title'), validators=[required()])
    description = TextAreaField(_LT('Description'), validators=[required()], description='(markdown supported)')
    price = html5.IntegerField(_LT('Price'), validators=[required(),
                                                    number_range(min=1)])
    image = file.FileField(_LT('Image'))
    active = BooleanField(_LT('Active'), default=True)


class ItemDeleteForm(Form):
    pass # This form is only used for CSRF protection.

class UserDeactivateForm(Form):
    pass # This form is only used for CSRF protection.

class UserDeleteForm(Form):
    username = TextField(_LT('Username'), validators=[required()])

    def validate_username(self, field):
        if field.data != current_user.username:
            raise ValidationError(_LT('The username entered must match your username exactly.'))

class MessageSendForm(Form):
    to = TextField(_LT('To'), validators=[required()])
    message = TextAreaField(_LT('Message'))
