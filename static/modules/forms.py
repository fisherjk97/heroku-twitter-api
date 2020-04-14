from wtforms import Form, BooleanField, TextField, StringField, IntegerField, validators
from wtforms.validators import DataRequired, NumberRange

class TweetForm(Form):
    hashtag  = TextField(u'Hashtag(s)', validators=[DataRequired()], render_kw={"placeholder": "#Cool #Pictures @twitterhandle"})
    count = IntegerField(u'How Many?', validators=[DataRequired(), NumberRange(min=1, max=100, message='Must be between 1 and 100')], render_kw={"placeholder": "Think of a number 1-100"})

class UserForm(Form):
    screenName  = TextField(u'Screen Name', validators=[DataRequired()], render_kw={"placeholder": "@twitterhandle"})
    