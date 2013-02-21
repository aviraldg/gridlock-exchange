__author__ = 'aviraldg'

from flask import Flask
from flask.ext.login import LoginManager
from flask.ext.babel import Babel

app = Flask('exchange')
app.config.from_object('exchange.settings')
login_manager = LoginManager()
login_manager.init_app(app)
babel = Babel()
babel.init_app(app)

from .models import CustomAnonymousUserProfile
login_manager.anonymous_user = CustomAnonymousUserProfile

import customfilters
import contextproc
import views
