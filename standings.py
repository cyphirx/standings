from flask import Flask, render_template, Markup, request
import xml.etree.ElementTree as ET
from collections import OrderedDict
from datetime import datetime
import urllib2
from urllib import quote_plus
from forms import CheckerForm
from flask.ext.sqlalchemy import SQLAlchemy

from sqlalchemy import Column, Integer, Text, DateTime

app = Flask(__name__)
app.secret_key = 'development key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cache.db'
db = SQLAlchemy(app)

class Record(db.Model):
    pid = Column(Integer, primary_key=True)
    name = Column(Text, unique=False)
    corp = Column(Text, unique=False)
    corpID = Column(Integer, unique=False)
    alliance = Column(Text, unique=False)
    allianceID = Column(Integer, unique=False)
    added = Column(DateTime, unique=False)

db.create_all()


# Changeme settings
keyID = 111111
vCode = "fsdfdsfd"
datasource = "C:\BECAUSE\DANTE\YELLED\AT\ME\standings.xml"


apiURL = "https://api.eveonline.com"

iskhr_id = 98255477

debug = True

root = ""
tree = ""

"""
Text box that allows someone to paste entire listing of players in system
User hits submit, list is iterated through and array is created to gather list of users
call is made to http://wiki.eve-id.net/APIv2_Eve_CharacterID_XML to retrieve ID's
Results are iterated through to build dict containing name, corp, alliance from
http://wiki.eve-id.net/APIv2_Eve_CharacterInfo_XML


Faer Kado
GunfighterAK47
Henrietta Morkeheim
Johnny Hammersticks
Kelenia Taranogas
Kliedar
Luffy999
Malkador Sigillit
Oolon Rockefeller
Rowan Crendraven
Unit 1138
Weli Gaterau
Yornum Haree
ZavoDiK

"""

def checkCache():

    # Let's check if cache is older than timelimit
    cached = tree.find('./cachedUntil')

    cachedTstamp = datetime.strptime(cached.text, "%Y-%m-%d %H:%M:%S")

    if (cachedTstamp < datetime.utcnow()):
        return False
    else:
        return True
    return False

def checkFriendlies(name):
    if debug:
        print "Checking " + name

    for child in root.findall('./result/rowset/[@name="corporateContactList"]/*'):
        contact = child.get('contactName')
        standing = int(child.get('standing'))

        if contact == name:
            if standing > 0:
                return True
            else:
                return False
    return False

def getContacts():
    url = apiURL + "/corp/ContactList.xml.aspx?keyID=" + str(keyID) + "&vCode=" + vCode
    request = urllib2.Request(url, headers={"Accept" : "application/xml"})

    try:
        f = urllib2.urlopen(request)
    except:
        return "Error opening url"

    tree = ET.parse(f)
    tree.write(datasource)
    print "Retrieved tree and updated"

    return tree

@app.route('/check', methods=['GET', 'POST'])
def check():
    form = CheckerForm()
    if request.method == 'POST':
        block = form.players.data.split('\r\n')
        unaffiliated = ""
        pname = ""
        players = []

        # Start Iterating through players and compare against friendlies list, add to list to query CCP API
        for player in block[:]:
            if player == "":
                continue
            # stub here for a checkbox later to list everyone in system, including friendlies with colorcode
            if checkFriendlies(player):
                continue

            # Rough and dirty listing
            players.append(player)
            # unaffiliated += "<tr><td>" + player + "</td></tr>"

            # Build comma-separated list of names to retrieve from CCP API
            pname += player + ","

        # Build URL and retrieve from API
        url = apiURL + "/eve/CharacterID.xml.aspx?names=" + quote_plus(pname, ",")
        if debug:
            print url

        requestAPI = urllib2.Request(url, headers={"Accept" : "application/xml"})
        try:
            f = urllib2.urlopen(requestAPI)
        except:
            return "Error opening url"

        uid_tree = ET.parse(f)
        uid_root = uid_tree.getroot()

        # Iterate through ID's and names to start forming next API call
        for child in uid_root.findall('./result/rowset/[@name="characters"]/*'):
            contact = child.get('name')
            cID = child.get('characterID')
            if int(cID) == 0:
                 unaffiliated += "<tr><td>" + contact + "</td><td>Bad name</tr>"
            else:
                # Check if ISKHR corpid(98255477) is same as players
 #               if int(corpID) == iskhr_id:
 #                   continue

                # Placement for CCP API call for individual

                unaffiliated += "<tr><td><a href=\"https://zkillboard.com/character/" + cID + "/\">" + contact + "</a></td><td>&nbsp;</tr>"

            if debug:
                print contact, cID



        if unaffiliated == "":
            unaffiliated = "<tr><td colspan=2>No unaffiliated people!</td></tr>\n\r"


        return render_template('check.html', data = Markup(unaffiliated), form=form, success=True)


    if request.method == 'GET':
        print "page get"


    return render_template('check.html', form=form)


@app.route('/')
def home():
    global root, tree

    lists = OrderedDict({})

    cached = tree.find('./cachedUntil')

    if (checkCache() == False):
        getContacts()
        tree = ET.parse(datasource)
        print("Reloaded xml")
        root = tree.getroot()
        cached = tree.find('./cachedUntil')

    else:
        print "Cache has been updated recently"

    for child in root.findall('./result/rowset/[@name="corporateContactList"]/*'):
        contact = child.get('contactName')
        standing = int(child.get('standing'))
        lists.update({contact: standing})

    contents = ""
    for key, value in sorted(lists.iteritems(), key=lambda (k,v): (v,k)):
        if value <= -10:
            bgcolor = "terrible"
        elif value < 0:
            bgcolor = "bad"
        elif value >= 5 and value < 10:
            bgcolor = "good"
        elif value >= 10:
            bgcolor = "excellent"
        else:
            bgcolor = "neutral"
        contents += "<tr id='%s'><td> %s </td><td> %s </td></tr>\n" % (bgcolor, key, str(value))

    return render_template("index.html",contacts=Markup(contents),cached=cached.text)


if __name__ == '__main__':
    tree = ET.parse(datasource)
    root = tree.getroot()

    app.run(host='192.168.1.6', debug=True)
