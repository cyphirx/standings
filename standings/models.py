from flask.ext.sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class CharacterInfo(db.Model):
    created = db.Column(db.DateTime, unique=False)
    modified = db.Column(db.DateTime, unique=False)
    characterID = db.Column(db.Integer, primary_key=True)
    characterName = db.Column(db.Text, unique=False)
    corporation = db.Column(db.Text, unique=False)
    corporationID = db.Column(db.Integer, unique=False)
    corporationDate =db.Column(db.DateTime, unique=False)
    alliance =db.Column(db.Text, unique=False)
    allianceID =db.Column(db.Integer, unique=False)
    allianceDate =db.Column(db.DateTime, unique=False)
    securityStatus =db.Column(db.Float, unique=False)

class ContactList(db.Model):
    created =db.Column(db.DateTime, unique=False)
    modified =db.Column(db.DateTime, unique=False)
    contactID =db.Column(db.Integer, primary_key=True)
    contactName =db.Column(db.Text, unique=True)
    standing =db.Column(db.Integer, unique=False)







def initial_db():
    from flask import Flask
    from sqlalchemy import exists
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cache.db'
    db.init_app(app)
    with app.test_request_context():
        db.create_all(app=app)
        db.session.commit()
        
# vim: set ts=4 sw=4 et :