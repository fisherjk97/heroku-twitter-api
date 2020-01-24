import os
from flask import Flask, redirect, session, render_template, request, url_for,jsonify, make_response
import oauth2 as oauth
import urllib.request
import urllib.parse
import urllib.error
import json
import urllib.parse
import urllib
from flask_restful import Resource, Api
import base64 
from wtforms import Form, BooleanField, TextField, StringField, IntegerField, validators
from wtforms.validators import DataRequired, NumberRange
from flask_cors import CORS

app = Flask(__name__, static_url_path="", static_folder="static")

random_bytes = os.urandom(64)
secret = base64.b64encode(random_bytes).decode('utf-8')
app.secret_key = secret #os.getenv('TWAUTH_APP_SESSION_SECRET', secret)


CORS(app)
#app.debug = True

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

oauth_store = {}

class TweetForm(Form):
    hashtag  = TextField(u'Hashtag(s)', validators=[DataRequired()])
    count = IntegerField(u'How Many?', validators=[DataRequired(), NumberRange(min=1, max=20, message='Must be between 1 and 20')])
   

@app.route('/')
def index():
    #return redirect(url_for('start'))
    return render_template('index.html')


@app.route('/start')
def start():
    session.clear()
    # note that the external callback URL must be added to the whitelist on
    # the developer.twitter.com portal, inside the app settings
    app_callback_url = url_for('callback', _external=True)

    # Generate the OAuth request tokens, then display them
    consumer = oauth.Consumer(
        app.config['APP_CONSUMER_KEY'], app.config['APP_CONSUMER_SECRET'])
    client = oauth.Client(consumer)
    resp, content = client.request(request_token_url, "POST", body=urllib.parse.urlencode({
                                   "oauth_callback": app_callback_url}))

    if resp['status'] != '200':
        error_message = 'Invalid response, status {status}, {message}'.format(
            status=resp['status'], message=content.decode('utf-8'))
        return render_template('error.html', error_message=error_message)

    request_token = dict(urllib.parse.parse_qsl(content))
    oauth_token = request_token[b'oauth_token'].decode('utf-8')
    oauth_token_secret = request_token[b'oauth_token_secret'].decode('utf-8')

    session[oauth_token] = oauth_token_secret
    print(session[oauth_token])
    oauth_store[oauth_token] = oauth_token_secret
    return render_template('start.html', authorize_url=authorize_url, oauth_token=oauth_token, request_token_url=request_token_url)


@app.route('/callback')
def callback():
    #if we haven't already stored session data
 
    if not (session.get('real_oauth_token')  and session.get('real_oauth_token_secret')):

        # Accept the callback params, get the token and call the API to
        # display the logged-in user's name and handle
        oauth_token = request.args.get('oauth_token')
        oauth_verifier = request.args.get('oauth_verifier')
        oauth_denied = request.args.get('denied')

        #oauth_store[oauth_token] = oauth_token_secret
        oauth_token_secret = session[oauth_token]
        # if the OAuth request was denied, delete our local token
        # and show an error message
        if oauth_denied:
            if oauth_denied in oauth_store:
                del oauth_store[oauth_denied]
            return render_template('error.html', error_message="the OAuth request was denied by this user")

        if not oauth_token or not oauth_verifier:
            return render_template('error.html', error_message="callback param(s) missing")

        # unless oauth_token is still stored locally, return error
        if oauth_token not in oauth_store:
            return render_template('error.html', error_message="oauth_token not found locally")

        oauth_token_secret = oauth_store[oauth_token]

        # if we got this far, we have both callback params and we have
        # found this token locally

        consumer = oauth.Consumer(app.config['APP_CONSUMER_KEY'], app.config['APP_CONSUMER_SECRET'])
        token = oauth.Token(oauth_token, oauth_token_secret)
        token.set_verifier(oauth_verifier)
        client = oauth.Client(consumer, token)

        resp, content = client.request(access_token_url, "POST")
        access_token = dict(urllib.parse.parse_qsl(content))

        # These are the tokens you would store long term, someplace safe
        real_oauth_token = access_token[b'oauth_token'].decode('utf-8')
        real_oauth_token_secret = access_token[b'oauth_token_secret'].decode('utf-8')



        # don't keep this token and secret in memory any longer
        del oauth_store[oauth_token]
        #oauth_store['real_oauth_token'] = real_oauth_token
        #oauth_store['real_oauth_token_secret'] = real_oauth_token_secret
        #oauth_store['consumer'] = consumer

        session['real_oauth_token'] = real_oauth_token
        session['real_oauth_token_secret'] = real_oauth_token_secret
        #session['consumer'] = consumer

    return render_template('callback-success.html', access_token_url=access_token_url)


@app.route('/twitter', methods=['GET', 'POST'])
def twitter():
    form = TweetForm(request.form)
    if request.method == 'POST' and form.validate():
        q = form.hashtag.data
        count = form.count.data

        real_oauth_token = session['real_oauth_token']
        real_oauth_token_secret = session['real_oauth_token_secret']

        media_content = search_tweets(real_oauth_token, real_oauth_token_secret, q, count)

        media = get_hashtag_media(media_content)
        message = "Found " + str(len(media)) + "/" + str(count) + " image(s) with search '" + q + "'"
        return render_template('twitter.html', images=media, form=form, message=message)
    else:
        return render_template('twitter.html', form=form)
   
   

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', error_message='uncaught exception'), 500


def get_hashtag_media(response):
    tweets = json.loads(response)
    media_files = set()
    for status in tweets["statuses"]:
        # print("Status: %s" % status)
        if("media" in status["entities"]):
            media = status["entities"].get('media', [])
            if(len(media) > 0):
                media_files.add(media[0]['media_url'])
                print("Media: %s" % media[0]['media_url'])

    return media_files


def oauth_get(real_oauth_token, real_oauth_token_secret, request_url):
    consumer = oauth.Consumer(app.config['APP_CONSUMER_KEY'], app.config['APP_CONSUMER_SECRET'])

    real_token = oauth.Token(real_oauth_token, real_oauth_token_secret)
    real_client = oauth.Client(consumer, real_token)
    real_resp, real_content = real_client.request(request_url, "GET")


    if real_resp['status'] != '200':
        error_message = "Invalid response from Twitter API GET search/tweets: {status}".format(
            status=real_resp['status'])
        return render_template('error.html', error_message=error_message)

    return real_content


def search_tweets(real_oauth_token, real_oauth_token_secret, q, count):
    params = {'q': q, 'count': count}
    encoded = urllib.parse.urlencode(params)
    print(encoded)
    url = search_tweets_url + '?' + encoded
    print(url)
    return oauth_get(real_oauth_token, real_oauth_token_secret, url)

def get_user(real_oauth_token, real_oauth_token_secret, user_id):
    url = show_user_url + '?user_id=' + user_id
    return oauth_get(real_oauth_token, real_oauth_token_secret, url)

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
