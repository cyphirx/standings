from flask.ext.wtf import Form
from wtforms import TextAreaField, SubmitField, PasswordField, TextField, validators
import os

import ConfigParser

def ConfigSectionMap(section):
    dict1 = {}
    options = Config.options(section)
    for option in options:
        try:
            dict1[option] = Config.get(section, option)
            if dict1[option] == -1:
                print("skip: %s" % option)
        except:
            print("exception on %s!" % option)
            dict1[option] = None
    return dict1


Config = ConfigParser.ConfigParser()
Config.read("settings.ini")

if os.path.isfile('settings.ini'):
    # stopgap until we can get connected to Auth
    global_user =  ConfigSectionMap("users")['user']
    global_password = ConfigSectionMap("users")['password']
else:
    # stopgap until we can get connected to Auth
    global_user = os.environ['app_admin_user']
    global_password = os.environ['app_admin_password']



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

        if self.name.data.lower() == global_user and self.password.data == global_password:
            return True



# vim: set ts=4 sw=4 et :
