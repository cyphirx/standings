from flask.ext.sqlalchemy import SQLAlchemy

db = SQLAlchemy(app)


class CharacterInfo(db.Model):
    created = db.Column(db.DateTime, unique=False)
    modified = db.Column(db.DateTime, unique=False)
    characterID = db.Column(db.Integer, primary_key=True)
    characterName = db.Column(db.Text, unique=False)
    corporation = db.Column(db.Text, unique=False)
    corporationID = db.Column(db.Integer, unique=False)
    corporationDate = db.Column(db.DateTime, unique=False)
    alliance = db.Column(db.Text, unique=False)
    allianceID = db.Column(db.Integer, unique=False)
    allianceDate = db.Column(db.DateTime, unique=False)
    securityStatus = db.Column(db.Float, unique=False)


class Standing(db.Model):
    name = db.Column(db.Text, primary_key=True)
    value = db.Column(db.Integer, unique=False)
    added = db.Column(db.DateTime, unique=False)

# vim: set ts=4 sw=4 et :
