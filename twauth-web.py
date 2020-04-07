import os
from flask import Flask, redirect, session, render_template, request, url_for, jsonify, make_response, flash
import oauth2 as oauth
import urllib.request
import urllib.parse
import urllib.error
import json
import urllib.parse
import urllib
from flask_restful import Resource, Api
import re
import base64 
import time
import babel
from babel.dates import format_date, format_datetime
from datetime import datetime
from wtforms import Form, BooleanField, TextField, StringField, IntegerField, validators
from wtforms.validators import DataRequired, NumberRange
from flask_cors import CORS
from flask_dance.contrib.twitter import make_twitter_blueprint, twitter
from flask_dance.consumer import oauth_authorized
from werkzeug.contrib.fixers import ProxyFix
from werkzeug.datastructures import MultiDict
from operator import itemgetter, attrgetter
app = Flask(__name__, static_url_path="", static_folder="static")
app.wsgi_app = ProxyFix(app.wsgi_app)

random_bytes = os.urandom(64)
secret = base64.b64encode(random_bytes).decode('utf-8')
app.secret_key = secret #os.getenv('TWAUTH_APP_SESSION_SECRET', secret)

CORS(app)
#app.debug = True

# get_current_user() is a function that returns the current logged in user

request_token_url = 'https://api.twitter.com/oauth/request_token'
access_token_url = 'https://api.twitter.com/oauth/access_token'
authorize_url = 'https://api.twitter.com/oauth/authorize'
show_user_url = 'https://api.twitter.com/1.1/users/show.json'
search_tweets_url = "https://api.twitter.com/1.1/search/tweets.json"

# Support keys from environment vars (Heroku).
app.config['APP_CONSUMER_KEY'] = os.getenv(
    'TWAUTH_APP_CONSUMER_KEY', 'API_Key_from_Twitter')
app.config['APP_CONSUMER_SECRET'] = os.getenv(
    'TWAUTH_APP_CONSUMER_SECRET', 'API_Secret_from_Twitter')

# alternatively, add your key and secret to config.cfg
# config.cfg should look like:
# APP_CONSUMER_KEY = 'API_Key_from_Twitter'
# APP_CONSUMER_SECRET = 'API_Secret_from_Twitter'
app.config.from_pyfile('config.cfg', silent=True)

twitter_bp =  make_twitter_blueprint(
    api_key=app.config['APP_CONSUMER_KEY'],
    api_secret=app.config['APP_CONSUMER_SECRET'],
    redirect_url="/twitter_api"
)
app.register_blueprint(twitter_bp, url_prefix="/login")



oauth_store = {}

class TweetForm(Form):
    hashtag  = TextField(u'Hashtag(s)', validators=[DataRequired()], render_kw={"placeholder": "#Cool #Pictures @twitterhandle"})
    count = IntegerField(u'How Many?', validators=[DataRequired(), NumberRange(min=1, max=100, message='Must be between 1 and 100')], render_kw={"placeholder": "Think of a number 1-100"})

class UserForm(Form):
    screenName  = TextField(u'Screen Name', validators=[DataRequired()], render_kw={"placeholder": "@twitterhandle"})
    

###format date - http://babel.pocoo.org/en/latest/dates.html
@app.template_filter('datetime')
def format_datetime(value, format='medium'):
    if format == 'full':
        format="EEEE, d. MMMM y 'at' HH:mm"
    elif format == 'medium':
        format="EE dd.MM.y HH:mm"
    elif format == 'shorttime':
        format="M/d/y @ h:mm a"
    return babel.dates.format_datetime(value, format)


def set_date(date_str):
        """Convert twitter datestring to datetime
        """
        time_struct = time.strptime(date_str, "%a %b %d %H:%M:%S +0000 %Y")#Tue Apr 26 08:57:55 +0000 2011
        return datetime.fromtimestamp(time.mktime(time_struct))

class Tweet():
    media_id = ""
    media_url = ""
    text = ""
    src = ""
    media_url_lg = ""
  

    
    def __init__(self, media_id, media_url, text, src):
        self.media_id = media_id
        self.media_url = media_url
        self.text = text
        self.src = src
        self.media_url_lg = self.media_url + ":large"


    def __hash__(self):
        return hash(('media_id', self.media_id,
                 'media_url', self.media_url,
                 'text', self.text,
                 'src', self.src))

    def __eq__(self, other):
        return self.media_id == other.media_id


class Account():
    account_id = ""
    screen_name = ""
    name = ""
    description = ""
    profile_url = ""
    profile_image_url = "" 
    profile_image_url_lg = "" 
    profile_image_banner_url = ""
    friends_count = 0
    followers_count = 0
    last_tweeted = ""
    
    def __init__(self, account_id, screen_name, name, description, profile_url, profile_image_url, profile_image_banner_url, friends_count, followers_count, last_tweeted):
        self.account_id = account_id
        self.screen_name = screen_name
        self.name = name
        self.description = description
        self.profile_url = profile_url
        self.profile_image_url = profile_image_url
        self.profile_image_url_lg = self.profile_image_url.replace("_normal", "_bigger")
        self.profile_image_banner_url = profile_image_banner_url
        self.friends_count = friends_count
        self.followers_count = followers_count
        self.last_tweeted = set_date(last_tweeted)
       


    def __hash__(self):
        return hash(
                ('account_id', self.account_id,
                 'screen_name', self.screen_name,
                 'name', self.name,
                 'description',self.description,
                'profile_url', self.profile_url,
                'profile_image_url', self.profile_image_url,
                'profile_image_banner_url', self.profile_image_banner_url,
                'friends_count', self.friends_count,
                'followers_count',  self.followers_count
                 ))

    def __eq__(self, other):
        return self.account_id == other.account_id



@app.route("/")
def index():
    return render_template('index.html')

@app.route("/start")
def start():
    if not twitter.authorized:
        return redirect(url_for("twitter.login"))
    resp = twitter.get("account/verify_credentials.json")
    screen_name = resp.json()["screen_name"]
    name = resp.json()["name"]
    assert resp.ok
    return redirect(url_for('twitter_api'))

@app.route("/api_user", methods=['GET', 'POST'])
def api_user():
    form = UserForm(request.form)
    if request.method == 'POST' and form.validate():
        screen_name = form.screenName.data

        ###resp = twitter.get("account/verify_credentials.json")
        ##screen_name = resp.json()["screen_name"]
        #name = resp.json()["name"]
        #count = 20
        cleaned_screen_name = screen_name.replace("@", "")
        queryString = "?screen_name=" + cleaned_screen_name + "&count=20"

        resp_friends = twitter.get("friends/list.json" + queryString)
        resp_followers = twitter.get("followers/list.json" + queryString)
 
        resp_screenName = twitter.get("users/show.json" + "?screen_name=" + cleaned_screen_name) 
        user = get_user_info(resp_screenName)
        friends = get_accounts(resp_friends)
        followers = get_accounts(resp_followers)

        form = UserForm()

        return render_template('api_user.html', form=form, formSubmitted=True, screen_name=screen_name, user=user, friends=friends, followers=followers)
    else:
        return render_template('api_user.html', form=form, formSubmitted=False)

@app.route("/api_pictures", methods=['GET', 'POST'])
def api_pictures():
    form = TweetForm(request.form)
    formSubmitted = False
    if request.method == 'POST' and form.validate():
        q = form.hashtag.data
        count = form.count.data
        
        response = search_tweets(q, count)
        ##data = jsonify(response.text).json
        media = get_hashtag_media(response.content)

        nFound = len(media)
        formSubmitted = True
        message = "Found " + str(len(media)) + "/" + str(count) + " image(s) with search '" + q + "'"
        form = TweetForm()
        return render_template('api_pictures.html', images=media, form=form, formSubmitted=formSubmitted, q=q, count=count, nFound=nFound)
    
    else:
        return render_template('api_pictures.html', form=form)
    
@app.route('/twitter_api', methods=['GET', 'POST'])
def twitter_api():
    form = TweetForm(request.form)
    return render_template('twitter_api.html', form=form)

@app.route('/twitter_image', methods=['GET', 'POST'])
def twitter_image():
    form = TweetForm(request.form)
    formSubmitted = False
    if request.method == 'POST' and form.validate():
        q = form.hashtag.data
        count = form.count.data
        
        response = search_tweets(q, count)
        ##data = jsonify(response.text).json
        media = get_hashtag_media(response.content)

        nFound = len(media)
        formSubmitted = True
        message = "Found " + str(len(media)) + "/" + str(count) + " image(s) with search '" + q + "'"
        form = TweetForm()
        return render_template('twitter_api_full.html', images=media, form=form, formSubmitted=formSubmitted, q=q, count=count, nFound=nFound)
    
    else:
        return render_template('twitter_api_full.html', form=form)

@app.route('/twitter_api_full', methods=['GET', 'POST'])
def twitter_api_full():
    form = TweetForm(request.form)
    formSubmitted = False
    if request.method == 'POST' and form.validate():
        q = form.hashtag.data
        count = form.count.data
        
        response = search_tweets(q, count)
        ##data = jsonify(response.text).json
        media = get_hashtag_media(response.content)

        nFound = len(media)
        formSubmitted = True
        message = "Found " + str(len(media)) + "/" + str(count) + " image(s) with search '" + q + "'"
        form = TweetForm()
        return render_template('twitter_api_full.html', images=media, form=form, formSubmitted=formSubmitted, q=q, count=count, nFound=nFound)
    
    else:
        return render_template('twitter_api_full.html', form=form)
   

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', error_message='uncaught exception'), 500


def write_to_json_file(name, data):
     with open(name, 'w') as f:
        
        json.dump(data, f)
        

def get_hashtag_media(response):
    tweets = json.loads(response)

    response_dict = {}
    
    for status in tweets["statuses"]:
        text = status['text']
        has_standard_entities = (status.get('entities', None) != None)
        has_extended_entities = (status.get('extended_entities', None) != None)
        if(has_standard_entities and  has_extended_entities):
            if("extended_entities" in status and "media" in status["extended_entities"]):
                extended_media = status["extended_entities"].get('media', [])
                for media in extended_media:
                    t = parse_media_tweet(media, text)
                    if(t.media_id not in response_dict):
                        response_dict[t.media_id] = t
        

    response_tweets = [ v for v in response_dict.values() ]
    return response_tweets


def parse_media_tweet(media, text):
    src_url = media['url'] if("url" in media) else ""
    media_url = media['media_url'] if("media_url" in media) else ""
    media_id = media['id'] if("id" in media) else ""
    if(text != ""):
        text = text.replace(src_url, '')
        text = re.sub(r'^https?:\/\/.*[\r\n]*', '', text, flags=re.MULTILINE)
        text = text.rstrip("\n\r")
        text = text.replace("&amp;", "&")
    

    return Tweet(media_id, media_url, text, src_url)




def get_accounts(response):
    accounts = json.loads(response.content)

    response_dict = {}
    
    for a in accounts["users"]:
        response_account = parse_account(a)
        response_dict[response_account.account_id] = response_account

    response_accounts = [ v for v in response_dict.values() ]

    return response_accounts

def parse_account(account):
    if(account):
        account_id = account['id']
        screen_name = account['screen_name']
        name = account['name']
        description = account['description']
        profile_url = account['url'] if account['url'] != None else ""
        profile_image_url = account['profile_image_url_https']
        profile_image_banner_url = ""
        if('profile_banner_url' in account):
            profile_image_banner_url = account['profile_banner_url']
        else:
            profile_image_banner_url = account['profile_background_image_url_https']
        #profile_image_banner_url = account['profile_banner_url'] if account['profile_banner_url'] != None else ""
        friends_count = account['friends_count']
        followers_count = account['followers_count']

        last_tweeted = None
        if 'status' in account:
            tweet = account["status"]
            last_tweeted = tweet['created_at']

        response_account = Account(account_id, screen_name, name, description, profile_url, profile_image_url, profile_image_banner_url, friends_count, followers_count, last_tweeted)

    return response_account

def get_user_info(response):
    a = json.loads(response.content)
    response_user = parse_account(a)
    return response_user



def search_tweets(q, count):
    params = {'q': q, 'count': count, "lang": "en"}
    encoded = urllib.parse.urlencode(params)
    print(encoded)
    url = search_tweets_url + '?' + encoded
    print(url)
    return twitter.get(url)

def get_user(user_id):
    url = show_user_url + '?user_id=' + user_id
    return twitter.get(url)

def to_json(content):
    response = content
    try:
        response = content.decode('utf-8')
    except:
        print("Exception")
    finally:
        return json.loads(response)
  

 
if __name__ == '__main__':
    app.run()
