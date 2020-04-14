from datetime import datetime, timezone
import babel
from babel.dates import format_date, format_datetime, format_time
import os
import json

def twitter_date_to_datetime(value):
    return datetime.strptime(value,'%a %b %d %H:%M:%S +0000 %Y')

def utc_to_local(utc_dt):
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)

###format date - http://babel.pocoo.org/en/latest/dates.html
def format_twitter_date(value, format='default'):
    """format datetime"""
    ts = twitter_date_to_datetime(value)
    local_ts = utc_to_local(ts)
    
    if format == 'full':
        format ="EEEE, d. MMMM y 'at' HH:mm zzzz"
    elif format == 'medium':
        format ="EE dd.MM.y HH:mm zzzz"
    else:
        format="M/d/y @ h:mm a zzzz"

    return babel.dates.format_datetime(local_ts, format)

def to_json(content):
    response = content
    try:
        response = content.decode('utf-8')
    except:
        print("Exception")
    finally:
        return json.loads(response)
  

def write_to_json_file(name, data):
     with open(name, 'w') as f:
        json.dump(data, f)
        