from flask import Flask

app = Flask(__name__)

app.secret_key = "Some key used for creating hidden tags"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cache.db'

from models import db
db.init_app(app)

import standings.routes


