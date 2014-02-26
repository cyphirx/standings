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
    created = db.Column(db.DateTime, unique=False)
    modified = db.Column(db.DateTime, unique=False)
    contactID = db.Column(db.Integer, primary_key=True)
    contactName = db.Column(db.Text, unique=True)
    standing = db.Column(db.Integer, unique=False)


class WalletJournal(db.Model):
    date = db.Column(db.DateTime, unique=False)
    refID = db.Column(db.Integer, unique=True, primary_key=True)
    refTypeID = db.Column(db.Integer, unique=False)
    ownerName1 = db.Column(db.Text, unique=False)
    ownerID1 = db.Column(db.Integer, unique=False)
    ownerName2 = db.Column(db.Text, unique=False)
    ownerID2 = db.Column(db.Integer, unique=False)
    argName1 = db.Column(db.Text, unique=False)
    argID1 = db.Column(db.Integer, unique=False)
    amount = db.Column(db.Float, unique=False)
    balance = db.Column(db.Float, unique=False)
    reason = db.Column(db.Text, unique=False)
    owner1TypeID = db.Column(db.Integer, unique=False)
    owner2TypeID = db.Column(db.Integer, unique=False)
    wallet = db.Column(db.Integer, unique=False)


# Setting table name because table does not have a primary key
class Notes(db.Model):
    noteID = db.Column(db.Integer, unique=True, primary_key=True)
    contactID = db.Column(db.Integer, unique=False)
    note = db.Column(db.Text, unique=False)
    added = db.Column(db.DateTime, unique=False)


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