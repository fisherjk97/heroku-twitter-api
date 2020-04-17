import sys
import os
from flask import Flask, redirect, session, render_template, request, url_for, jsonify, make_response, flash
import oauth2 as oauth
import urllib.request
import urllib.parse
import urllib.error
import json
import urllib.parse
import urllib
import re
import base64 
from flask_restful import Resource, Api
from static.modules import utils
from static.modules.models import Account, Tweet
from static.modules.forms import UserForm, TweetForm
from flask_cors import CORS
from flask_dance.contrib.twitter import make_twitter_blueprint, twitter
from flask_dance.consumer import oauth_authorized
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.datastructures import MultiDict
from operator import itemgetter, attrgetter
from flask_fontawesome import FontAwesome

app = Flask(__name__, static_url_path="", static_folder="static")
app.wsgi_app = ProxyFix(app.wsgi_app)

random_bytes = os.urandom(64)
secret = base64.b64encode(random_bytes).decode('utf-8')
app.secret_key = secret #os.getenv('TWAUTH_APP_SESSION_SECRET', secret)

CORS(app)
#app.debug = True
fa = FontAwesome(app)
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
    redirect_url="/api"
)
app.register_blueprint(twitter_bp, url_prefix="/login")

oauth_store = {}

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

@app.route('/api', methods=['GET', 'POST'])
def twitter_api():
    form = TweetForm(request.form)
    return render_template('twitter_api.html', form=form)


@app.route("/api/user", methods=['GET', 'POST'])
def api_user():
    message = ""
    user_message = ""
    friend_message = ""
    follower_message = ""
    count = 20
    try:
        if request.method == 'GET' and request.args:
            screen_name = request.args.get('screenName')

            cleaned_screen_name = screen_name.replace("@", "")
            queryString = "?screen_name=" + cleaned_screen_name + "&count=" + str(count)
            
            user = None
            friends = []
            followers = []
        
            resp_screenName = twitter.get("users/show.json" + "?screen_name=" + cleaned_screen_name) 
            if(resp_screenName.ok):
                user = get_user_info(resp_screenName)
            else:
                user_message = resp_screenName.reason
        
            resp_friends = twitter.get("friends/list.json" + queryString)
            if(resp_friends.ok):
                friends = get_accounts(resp_friends)
            else:
                friend_message = resp_friends.reason
            
            resp_followers = twitter.get("followers/list.json" + queryString)
            if(resp_followers.ok):
                followers = get_accounts(resp_followers)
            else:
                follower_message = resp_followers.reason

            return render_template('api/user.html', formSubmitted=True, user=user, friends=friends, followers=followers, user_message = user_message, friend_message = friend_message, follower_message = follower_message)
        else:
            return render_template('api/user.html', formSubmitted=False, user_message = user_message, friend_message = friend_message, follower_message = follower_message)
    except:
        print( sys.exc_info()[0])
        return render_template('api/user.html', formSubmitted=False,user_message = user_message, friend_message = friend_message, follower_message = follower_message)


@app.route("/api/pictures", methods=['GET', 'POST'])
def api_pictures():
    formSubmitted = False
    try:
        if request.method == 'GET' and request.args:
            q = request.args.get('hashtag')
            count = request.args.get('count')
            
            response = search_tweets(q, count)
            ##data = jsonify(response.text).json
            media = get_hashtag_media(response.content)

            nFound = len(media)
            formSubmitted = True
            message = "Found " + str(len(media)) + "/" + str(count) + " image(s) with search '" + q + "'"
            return render_template('api/pictures.html', images=media,message = "", formSubmitted=formSubmitted, q=q, count=count, nFound=nFound)
        
        else:
            return render_template('api/pictures.html', formSubmitted=False, message = "")
    except:
        return render_template('api/pictures.html', formSubmitted=False, message="Oops! Too many requests. Please wait a few minutes and try again")


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', error_message='uncaught exception'), 500

@app.template_filter('datetime')
def format_twitter_date(value, format='default'):
    """format datetime"""
    return utils.format_twitter_date(value, format)

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
        response_account = parse_account(a, False)
        response_dict[response_account.account_id] = response_account

    response_accounts = [ v for v in response_dict.values() ]

    return response_accounts

def parse_account(account, oembed_enabled):
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
            profile_image_banner_url = "https://via.placeholder.com/1500x500.png/007BFF/FFFFFF/?text=Image%20Not%20Found"
        #profile_image_banner_url = account['profile_banner_url'] if account['profile_banner_url'] != None else ""
        friends_count = account['friends_count']
        followers_count = account['followers_count']

        create_date = ""
        oembed = ""
        if 'status' in account:
            tweet = account["status"]
            create_date = tweet['created_at']
            if(oembed_enabled):
                last_tweet_id = tweet['id']
                oembed = get_tweet_oembed(last_tweet_id)

        
        return Account(account_id, screen_name, name, description, profile_url, profile_image_url, profile_image_banner_url, friends_count, followers_count, create_date, oembed)
    else:
        return None

def get_user_info(response):
    a = json.loads(response.content)
    response_user = parse_account(a, True)
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


def get_status(id):
    queryString = "?id=" + str(id)
    response = twitter.get("statuses/show.json" + queryString)
    return response



def get_tweet_oembed(id):
    try:
        url = "https://publish.twitter.com/oembed"
        queryString = "?url=https://twitter.com/Interior/status/" + str(id)
        response = twitter.get(url + queryString)
        if(response.ok):
            oembed = json.loads(response.content)
            return oembed["html"]
        else:
            return ""
    except:
        return ""
 
if __name__ == '__main__':
    app.run()
