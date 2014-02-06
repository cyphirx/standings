from flask import Flask, render_template, Markup, request, flash, url_for, redirect, session
import xml.etree.ElementTree as ET
from collections import OrderedDict
from datetime import datetime, timedelta, date
import urllib2
import os
from urllib import quote_plus
from flask.ext.sqlalchemy import SQLAlchemy
import ConfigParser
from sqlalchemy import Column, Integer, Text, DateTime, Float, exists, or_
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
Config = ConfigParser.ConfigParser()

# Read in configuration settings
Config.read("settings.ini")

# Heroku specific thing, needs correct formatting
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///cache.db')

db = SQLAlchemy(app)

class CharacterInfo(db.Model):
    created = Column(DateTime, unique=False)
    modified = Column(DateTime, unique=False)
    characterID = Column(Integer, primary_key=True)
    characterName = Column(Text, unique=False)
    corporation = Column(Text, unique=False)
    corporationID = Column(Integer, unique=False)
    corporationDate = Column(DateTime, unique=False)
    alliance = Column(Text, unique=False)
    allianceID = Column(Integer, unique=False)
    allianceDate = Column(DateTime, unique=False)
    securityStatus = Column(Float, unique=False)

class Standing(db.Model):
    name = Column(Text, primary_key=True)
    value = Column(Integer, unique=False)
    added = Column(DateTime, unique=False)

keyID = ConfigSectionMap("api")['keyid']
vCode = ConfigSectionMap("api")['vcode']

corpID = ConfigSectionMap("general")['corpid']
apiURL = ConfigSectionMap("general")['apiurl']
debug = ConfigSectionMap("general")['debug']
interface = ConfigSectionMap("general")['interface']
port = int(os.environ.get("PORT", 5000))

# stopgap until we can get connected to Auth
user = ConfigSectionMap("users")['user']
password = ConfigSectionMap("users")['password']

root = ""
tree = ""
contacts_cached = ""

db.create_all()

# All global pieces set, let's build some code

def get_contacts():
    global tree, root
    global contacts_cached

    if contacts_cached != "":
        time_var = datetime.now(tz=GMT()) - timedelta(hours=1)
        if time_var < contacts_cached:
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

    player_exists = db.session.query(exists().where(CharacterInfo.characterID == child_id)).scalar()

    if player_exists:
        player = CharacterInfo.query.filter_by(characterID=child_id).first()

        if player.modified.date() < expire_records:
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
                corporationID = child.text
            if child.tag == "allianceID":
                allianceID = child.text
            if child.tag == "alliance":
                alliance = child.text
            if child.tag == "characterName":
                characterName = child.text

        now = datetime.now(tz=GMT())
        u = CharacterInfo(characterID=child_id, characterName=characterName, corporation=corporation, corporationID=corporationID, alliance=alliance,
                   allianceID=allianceID, modified=now, created=now)
        db.session.add(u)
        db.session.commit()

    else:
        corporation = player.corporation
        corporationID = player.corporationID
        alliance = player.alliance
        allianceID = player.allianceID
        characterName = player.characterName

    return {"corporation": corporation, "corporationID": corporationID, "allianceID": allianceID, "alliance": alliance,
            "characterName": characterName}

#TODO: Increase usefulness of this, maybe a way to manually update or add notes on individuals, up in the air right now
@app.route('/player/<name>')
def display_player(name):
    player = CharacterInfo.query.filter_by(characterName=name).first_or_404()
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
        if len(block) > 50:
            return "Queries are capped at 50 lines for now. Noncompliance will be met with deadly force and/or ponies."

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
                    if 'name' not in session:
                        if u.value >= 0:
                            continue
                    bgcolor = standings_bgcolor(u.value)
                else:
                    bgcolor = "neutral"

                if returned_player['corporation'] == "Isk Efficiency" and 'name' in session:
                    bgcolor = "excellent"
                elif returned_player['corporation'] == "Isk Efficiency" and 'name' not in session:
                    continue



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
        # Minor kludge, but commit any db adds from lookup_player
        db.session.commit()
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
        if 'name' not in session and value >= 0:
            continue
        else:
            bgcolor = standings_bgcolor(value)
            contents += "<tr id='%s'><td> %s </td><td> %s </td></tr>\n" % (bgcolor, key, str(value))

    return render_template("index.html", contacts=Markup(contents), cached=contacts_cached)


@app.route('/signin', methods=['GET', 'POST'])
def signin():
    form = SigninForm()

    if request.method == 'POST':
        print "Page POST'd"
        print user, password
        if form.validate() == False:
            return render_template('signin.html', form=form)
        else:
            session['name'] = form.name.data
            print session['name']
            return redirect(url_for('home'))

    elif request.method == 'GET':
        return render_template('signin.html', form=form)

    print "what method is this?!"
if __name__ == '__main__':
    from forms import CheckerForm, SigninForm
    get_contacts()
    app.run(host=interface, port=port, debug=True)

# vim: set ts=4 sw=4 et :
