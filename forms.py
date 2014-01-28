from flask.ext.wtf import Form
from wtforms import TextAreaField, SubmitField

class CheckerForm(Form):
    players = TextAreaField("Players")
    submit = SubmitField("Check")


# vim: set ts=4 sw=4 et :
