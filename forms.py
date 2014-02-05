from flask.ext.wtf import Form
from wtforms import TextAreaField, SubmitField, PasswordField, TextField, validators
import standings

class CheckerForm(Form):
    players = TextAreaField("Players")
    submit = SubmitField("Check")


class SigninForm(Form):
    name = TextField("Username", [validators.Required("Please enter username")])
    password = PasswordField("Password", [validators.Required("Please enter a password")])
    submit = SubmitField("Login")

    def validate(self):
        if not Form.validate(self):
            return False

        if self.name.data.lower() == standings.user and self.password.data == standings.password:
            return True



# vim: set ts=4 sw=4 et :
