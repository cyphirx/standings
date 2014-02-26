from flask import Flask
import os

app = Flask(__name__)

app.secret_key = "Some key used for creating hidden tags"
# Heroku specific thing, needs correct formatting
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///cache.db')

from models import db
db.init_app(app)

import standings.routes


