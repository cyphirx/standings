from pprint import pprint
from flask import Flask, render_template, Markup, request, flash, url_for, redirect
import xml.etree.ElementTree as ET
from collections import OrderedDict
from datetime import datetime, timedelta, date
import urllib2
from urllib import quote_plus
from forms import CheckerForm
from flask.ext.sqlalchemy import SQLAlchemy
import ConfigParser
from sqlalchemy import Column, Integer, Text, DateTime, exists, or_
from functions import GMT, standings_bgcolor


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


class Standing(db.Model):
    name = Column(Text, primary_key=True)
    value = Column(Integer, unique=False)
    added = Column(DateTime, unique=False)

# Read in configuration settings
Config.read("settings.ini")

keyID = ConfigSectionMap("api")['keyid']
vCode = ConfigSectionMap("api")['vcode']

corpID = ConfigSectionMap("general")['corpid']
apiURL = ConfigSectionMap("general")['apiurl']
debug = ConfigSectionMap("general")['debug']
interface = ConfigSectionMap("general")['interface']

root = ""
tree = ""
contacts_cached = ""

db.create_all()

# All global pieces set, let's build some code

def get_contacts():
    global tree, root
    global contacts_cached

    if contacts_cached != "":
        time_var = datetime.now(tz=GMT()) - timedelta(hour=1)
        if time_var < contacts_cached:
            print time_var, contacts_cached
            return

    url = apiURL + "/corp/ContactList.xml.aspx?keyID=" + str(keyID) + "&vCode=" + vCode
    url_request = urllib2.Request(url, headers={"Accept": "application/xml"})
    try:
        f = urllib2.urlopen(url_request)
    except:
        return "Error opening contact list retrieval URL"
    tree = ET.parse(f)
    root = tree.getroot()
    Standing.query.delete()
    db.session.commit()

    contacts_cached = datetime.now(tz=GMT())

    for child in root.findall('./result/rowset/[@name="corporateContactList"]/*'):
        standings_corp = child.get('contactName')
        standings = int(child.get('standing'))
        # Take out TEST addition to standings
        if standings_corp == "Test Alliance Please Ignore":
            continue
        s = Standing(name=standings_corp, value=standings, added=contacts_cached)
        db.session.add(s)
        db.session.commit()
    print "Retrieved tree and updated"


def lookup_player_id(child_id):
    expire_records = date.today() - timedelta(days=5)

    player_exists = db.session.query(exists().where(Record.pid == child_id)).scalar()

    if player_exists:
        player = Record.query.filter_by(pid=child_id).first()

        if player.added.date() < expire_records:
            db.session.delete(player)
            db.session.commit()
            player_exists = False

    if not player_exists:
        print "adding id " + child_id
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

        u = Record(pid=child_id, name=characterName, corp=corporation, corpID=corp_id, alliance=alliance,
                   allianceID=alliance_id, added=datetime.now(tz=GMT()))
        db.session.add(u)
        db.session.commit()

    else:
        corporation = player.corp
        corp_id = player.corpID
        alliance = player.alliance
        alliance_id = player.allianceID
        characterName = player.name

    return {"corporation": corporation, "corp_id": corp_id, "alliance_id": alliance_id, "alliance": alliance,
            "characterName": characterName}

#TODO: Increase usefulness of this, maybe a way to manually update or add notes on individuals, up in the air right now
@app.route('/player/<name>')
def display_player(name):
    player = Record.query.filter_by(name=name).first_or_404()
    if player is None:
        flash('Player ' + name + ' not found!.')
        return redirect(url_for('index'))

    return render_template('player.html', player=player)


@app.route('/check', methods=['GET', 'POST'])
def check():
    form = CheckerForm()
    get_contacts()
    if request.method == 'POST':
        block = form.players.data.split('\r\n')
        unaffiliated = ""
        player_name = ""
        players = []

        # Retrieve every playerid in system and compare to what we have locally
        for value in block[:]:
            if value == "":
                continue
            players.append(value)
            # Build comma-separated list of names to retrieve from CCP API
            player_name += value + ","
            #TODO Redo this to remove check if no one hasn't already been added to records table
        # Build URL and retrieve from API
        url = apiURL + "/eve/CharacterID.xml.aspx?names=" + quote_plus(player_name, ",")
        request_api = urllib2.Request(url, headers={"Accept": "application/xml"})
        try:
            f = urllib2.urlopen(request_api)
        except:
            print url
            return "Error retrieving character ids url"

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
                u = db.session.query(Standing).filter(or_(Standing.name == returned_player['characterName'],
                                                          Standing.name == returned_player['corporation'],
                                                          Standing.name == returned_player['alliance'])).first()
                if u:
                    bgcolor = standings_bgcolor(u.value)
                else:
                    bgcolor = "neutral"
                if returned_player['corp_id'] == 98255477:
                    bgcolor = "excellent"

                #TODO Link in player page to here
                unaffiliated += "<tr id=" + bgcolor + ">\n" \
                                + "<td>" + contact + '</td>' \
                                + "<td>" + returned_player['corporation'] + "</td>" \
                                + "<td>" + returned_player['alliance'] + "</td>" \
                                + '<td><a href=\"https://zkillboard.com/character/' + child_id + '/\" target=\"_blank\">' \
                                + '<img src="/static/img/zkillboard.ico" width="16" height="16"> </a>' \
                                + '<a href="http://evewho.com/pilot/' + returned_player['characterName'].replace(" ",
                                                                                                                 "+") \
                                + '" target=\"_blank\"><img src="/static/img/evewho.ico" width="16" height="16"></a></td></td>\n'

        if unaffiliated == "":
            unaffiliated = "<tr><td colspan=2>No unaffiliated people!</td></tr>\n\r"

        return render_template('check.html', data=Markup(unaffiliated), form=form, success=True)

    return render_template('check.html', form=form)


@app.route('/')
def home():
    global root, tree

    lists = OrderedDict({})

    get_contacts()

    #TODO Redo this to use db instead
    for child in root.findall('./result/rowset/[@name="corporateContactList"]/*'):
        contact = child.get('contactName')
        standing = int(child.get('standing'))
        lists.update({contact: standing})

    contents = ""
    for key, value in sorted(lists.iteritems(), key=lambda (k, v): (v, k)):
        bgcolor = standings_bgcolor(value)
        contents += "<tr id='%s'><td> %s </td><td> %s </td></tr>\n" % (bgcolor, key, str(value))

    return render_template("index.html", contacts=Markup(contents), cached=contacts_cached)


if __name__ == '__main__':
    get_contacts()
    app.run(host=interface, debug=True)

# vim: set ts=4 sw=4 et :
