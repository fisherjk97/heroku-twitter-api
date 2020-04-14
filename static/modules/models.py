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
    create_date = ""
    
    def __init__(self, account_id, screen_name, name, description, profile_url, profile_image_url, profile_image_banner_url, friends_count, followers_count, create_date):
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
        self.create_date = create_date

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
                'followers_count',  self.followers_count,
                'create_date', self.create_date
                 ))

    def __eq__(self, other):
        return self.account_id == other.account_id


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
