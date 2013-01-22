__author__ = 'aviraldg'

from flask import Flask
from flask.ext.login import LoginManager

app = Flask('exchange')
app.config.from_object('exchange.settings')
login_manager = LoginManager()
login_manager.init_app(app)

import views
