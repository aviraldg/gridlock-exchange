__author__ = 'aviraldg'

from flask import Flask

app = Flask('exchange')
app.config.from_object('exchange.settings')

import hooks
import views
