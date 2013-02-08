from flask.ext.wtf import Form, TextField, PasswordField, TextAreaField, \
    BooleanField, email, required, length
from flask.ext.wtf import html5
from flask.ext.login import current_user
from wtforms import ValidationError
from wtforms.validators import number_range

__author__ = 'aviraldg'

class RegisterForm(Form):
    username = TextField('Username', validators=[required()])
    name = TextField('Name', validators=[required()])
    email = html5.EmailField('Email', validators=(email(), required()))
    password = PasswordField('Password', validators=[length(min=10)])


class LoginForm(Form):
    username = TextField('Username', validators=[required()])
    password = PasswordField('Password', validators=[required()])
    remember = BooleanField('Remember me')


class LogoutForm(Form):
    pass # This form is only used for CSRF protection.


class UserProfileForm(Form):
    bio = TextAreaField("bio")


class ItemForm(Form):
    title = TextField('Title', validators=[required()])
    description = TextAreaField('Description', validators=[required()])
    price = html5.IntegerField('Price', validators=[required(),
                                                    number_range(min=1)])

class ItemDeleteForm(Form):
    pass # This form is only used for CSRF protection.

class UserDeactivateForm(Form):
    pass # This form is only used for CSRF protection.

class UserDeleteForm(Form):
    username = TextField('Username', validators=[required()])

    def validate_username(self, field):
        if field.data != current_user.username:
            raise ValidationError('The username entered must match your username exactly.')

class MessageSendForm(Form):
    to = TextField('To', validators=[required()])
    message = TextAreaField('Message')
