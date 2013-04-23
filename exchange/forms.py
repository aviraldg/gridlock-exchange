from flask.ext.wtf import Form, TextField, PasswordField, TextAreaField, \
    BooleanField, email, required, length, SelectMultipleField
from flask.ext.wtf import html5, file
from flask.ext.login import current_user
from wtforms import ValidationError
from wtforms.widgets import TextInput
from wtforms.fields.core import SelectField
from wtforms.fields.simple import HiddenField
from wtforms.validators import number_range, required, equal_to, regexp, optional
from flask.ext.babel import gettext as _T, lazy_gettext as _LT

__author__ = 'aviraldg'

class RegisterForm(Form):
    username = TextField(_LT('Username'), validators=[required()])
    name = TextField(_LT('Name'), validators=[required()])
    email = html5.EmailField(_LT('Email'), validators=(email(), required()))
    password = PasswordField(_LT('Password'), validators=[required(), length(min=10)])
    confirm = PasswordField(_LT('Confirm Password'), validators=[
        required(),
        equal_to('password', _LT('Passwords must match!'))
    ])

    def validate_username(self, field):
        from models import User
        u = User.query(User.username == field.data).get()
        if u:
            raise ValidationError(_LT('Sorry, but this username is already in use.'))

    def validate_email(self, field):
        from models import User
        u = User.query(User.email == field.data).get()
        if u:
            raise ValidationError(_LT('Sorry, but this email is already in use'))


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
    youtube = TextField(_LT('Youtube Video URL'))
    private_viewers = TextField(_LT('Private Viewers'), description='(comma separated emails)')
    active = BooleanField(_LT('Active'), default=True)
    expires_in = html5.IntegerField(_LT('Expires In'), validators=[required(),
                                                                   number_range(min=1)],
                                    default=1, description=_LT('day(s)'))


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
    subject = HiddenField(_LT('Subject'), default='')
    to = TextField(_LT('To'), validators=[required()], description=(_LT('(comma separated emails)')))
    message = TextField(_LT('Message'))


class FeedbackForm(Form):
    rating = SelectField(_LT('Rating'), choices=zip(range(1, 6), range(1, 6)), validators=[required()], coerce=int)
    feedback = TextAreaField(_LT('Feedback'))


class CollectionForm(Form):
    title = TextField(_LT('Title'), validators=[required()])
    description = TextAreaField(_LT('Description'))
    item_ids = SelectMultipleField(_LT('Items'), choices=[], coerce=int)


class UserProfileForm(Form):
    name = TextField(_LT('Name'), validators=[required()],)
    bio = TextAreaField(_LT('Bio'), description='(markdown supported)')
    ga_id = TextField(_LT('Google Analytics ID'), description='eg. UA-XXXXX-X',
                      validators=[optional(), regexp(r'^UA\-\d+\-\d+$',
                                                     message='Please enter a valid GA ID (UA-XXXXXX-YY)')])
    app_key = TextField(_LT('App Key'), description='(edit to reset)')
