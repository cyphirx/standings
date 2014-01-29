from pprint import pprint
from flask import Flask, render_template, Markup, request
import xml.etree.ElementTree as ET
from collections import OrderedDict
from datetime import datetime
import urllib2
from urllib import quote_plus
from forms import CheckerForm
from flask.ext.sqlalchemy import SQLAlchemy
import ConfigParser
from sqlalchemy import Column, Integer, Text, DateTime

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


app = Flask(__name__)
app.secret_key = 'development key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cache.db'
db = SQLAlchemy(app)
Config = ConfigParser.ConfigParser()


class Record(db.Model):
    pid = Column(Integer, primary_key=True)
    name = Column(Text, unique=False)
    corp = Column(Text, unique=False)
    corpID = Column(Integer, unique=False)
    alliance = Column(Text, unique=False)
    allianceID = Column(Integer, unique=False)
    added = Column(DateTime, unique=False)


# Read in configuration settings
Config.read("settings.ini")

keyID = ConfigSectionMap("api")['keyid']
vCode = ConfigSectionMap("api")['vcode']

#TODO Build in retrieval of this so it doesn't need to be stored first
#Retrieve from https://api.eveonline.com/corp/ContactList.xml.aspx?keyid=xxxxxxxx&vcode=xxxxxxxxxx
datasource = "standings.xml"

corpID = ConfigSectionMap("general")['corpid']
apiURL = ConfigSectionMap("general")['apiurl']
debug = ConfigSectionMap("general")['debug']
interface = ConfigSectionMap("general")['interface']

root = ""
tree = ""

db.create_all()

# Complete all base settings


# API Call to retrieve consolidated API call listing for cid,
# followup call to hit http://wiki.eve-id.net/APIv2_Eve_CharacterInfo_XML
# to retrieve corp/alliance


def check_cache():
    # Let's check if cache is older than time limit
    cached = tree.find('./cachedUntil')
    cached_timestamp = datetime.strptime(str(cached.text), "%Y-%m-%d %H:%M:%S")
    if cached_timestamp < datetime.utcnow():
        return False
    else:
        return True


def standings_bgcolor(value):
    if value <= -10:
        bgcolor = "terrible"
    elif value < 0:
        bgcolor = "bad"
    elif 5 <= value < 10:
        bgcolor = "good"
    elif value >= 10:
        bgcolor = "excellent"
    else:
        bgcolor = "neutral"
    return bgcolor

def check_friendlies(name):
    for child in root.findall('./result/rowset/[@name="corporateContactList"]/*'):
        contact = child.get('contactName')
        standing = int(child.get('standing'))

        if contact == name:
            if standing > 0:
                return True
            else:
                return False
    return False


def get_contacts():
    global tree
    url = apiURL + "/corp/ContactList.xml.aspx?keyID=" + str(keyID) + "&vCode=" + vCode
    url_request = urllib2.Request(url, headers={"Accept": "application/xml"})
    try:
        f = urllib2.urlopen(url_request)
    except:
        return "Error opening url"

    tree = ET.parse(f)
    tree.write(datasource)
    print "Retrieved tree and updated"


def lookup_player_id(child_id):
    url = apiURL + "/eve/CharacterInfo.xml.aspx?characterID=" + str(child_id)
    url_request = urllib2.Request(url, headers={"Accept": "application/xml"})
    try:
        f = urllib2.urlopen(url_request)
    except:
        return "Error opening url"
    lookup_tree = ET.parse(f)
    lookup_root = lookup_tree.getroot()

    alliance_id = "0"
    alliance = ""

    result = lookup_root.findall('./result/*')
    for child in result:
        if child.tag == "corporation":
            corporation = child.text
        if child.tag == "corporationID":
            corp_id = child.text
        if child.tag == "allianceID":
            alliance_id = child.text
        if child.tag == "alliance":
            alliance = child.text
        if child.tag == "characterName":
            characterName = child.text

    return {"corporation": corporation, "corp_id": corp_id, "alliance_id": alliance_id, "alliance": alliance, "characterName": characterName }


@app.route('/check', methods=['GET', 'POST'])
def check():
    form = CheckerForm()
    if request.method == 'POST':
        block = form.players.data.split('\r\n')
        unaffiliated = ""
        player_name = ""
        players = []

        # Start Iterating through players and compare against friendlies list, add to list to query CCP API
        for value in block[:]:
            if value == "":
                continue
                # stub here for a checkbox later to list everyone in system, including friendlies with colorcode
            if check_friendlies(value):
                continue

            # Rough and dirty listing
            players.append(value)
            # unaffiliated += "<tr><td>" + player + "</td></tr>"

            # Build comma-separated list of names to retrieve from CCP API
            player_name += value + ","

        # Build URL and retrieve from API
        url = apiURL + "/eve/CharacterID.xml.aspx?names=" + quote_plus(player_name, ",")

        request_api = urllib2.Request(url, headers={"Accept": "application/xml"})
        try:
            f = urllib2.urlopen(request_api)
        except:
            print url
            return "Error opening url"

        uid_tree = ET.parse(f)
        uid_root = uid_tree.getroot()

        # Iterate through ID's and names to start forming next API call
        for child in uid_root.findall('./result/rowset/[@name="characters"]/*'):
            contact = child.get('name')
            child_id = child.get('characterID')
            if int(child_id) == 0:
                unaffiliated += "<tr><td>" + contact + "</td><td>Bad name</tr>"
            else:
                returned_player = lookup_player_id(child_id)
                if returned_player['corp_id'] == "98255477":
                    continue

                bgcolor = "neutral"
                # Base entry for standings check, needs to be tweaked to properly skip folks, readme updated with test check
                for child in root.findall('./result/rowset/[@name="corporateContactList"]/*'):
                    standings_corp = child.get('contactName')
                    standings = int(child.get('standing'))
                    if standings_corp == returned_player['corporation'] or standings_corp == returned_player['alliance']:
                        bgcolor = standings_bgcolor(standings)



                #TODO Check current list of standings and compare alliance/corp to mark friendlies
                unaffiliated += "<tr id=" + bgcolor + ">" \
                                + "<td>" + contact + '</td>' \
                                + "<td>" + returned_player['corporation'] + "</td>" \
                                + "<td>" + returned_player['alliance'] + "</td>" \
                                + '<td><a href=\"https://zkillboard.com/character/' + child_id + '/\" target=\"_blank\">' \
                                + '<img src="/static/img/zkillboard.ico" width="16" height="16"> </a>' \
                                + '<a href="http://evewho.com/pilot/' + returned_player['characterName'].replace(" ", "+") \
                                + '" target=\"_blank\"><img src="/static/img/evewho.ico" width="16" height="16"></a></td></td>'

        if unaffiliated == "":
            unaffiliated = "<tr><td colspan=2>No unaffiliated people!</td></tr>\n\r"

        return render_template('check.html', data=Markup(unaffiliated), form=form, success=True)

    if request.method == 'GET':
        print "page get"

    return render_template('check.html', form=form)


@app.route('/')
def home():
    global root, tree

    lists = OrderedDict({})

    cached = tree.find('./cachedUntil')

    if not check_cache():
        get_contacts()
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
    for key, value in sorted(lists.iteritems(), key=lambda (k, v): (v, k)):
        bgcolor = standings_bgcolor(value)
        contents += "<tr id='%s'><td> %s </td><td> %s </td></tr>\n" % (bgcolor, key, str(value))

    return render_template("index.html", contacts=Markup(contents), cached=cached.text)


if __name__ == '__main__':
    tree = ET.parse(datasource)
    root = tree.getroot()
    app.run(host=interface, debug=True)

# vim: set ts=4 sw=4 et :
