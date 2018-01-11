import datetime

import validators
from google.appengine.api import datastore_errors
from google.appengine.ext import ndb


def domain_validator(prop, value):
    if validators.domain(value) is not True:
        raise datastore_errors.BadValueError(prop._name)
    return value.lower()


class CustomDomain(ndb.Model):
    domain = ndb.StringProperty(validator=domain_validator)
    verified = ndb.BooleanProperty(default=False)
    updated_at = ndb.DateTimeProperty(auto_now=True)
    created_at = ndb.DateTimeProperty(auto_now_add=True)


class User(ndb.Model):
    """
    key_name = team_name + "_" + user_no

    """
    user = ndb.UserProperty(required=True)
    user_name = ndb.StringProperty(required=True)  # display name
    team = ndb.KeyProperty(required=True)
    role = ndb.StringProperty(choices=('primary_owner', 'admin', 'normal'))
    in_use = ndb.BooleanProperty(default=True, required=True)
    updated_at = ndb.DateTimeProperty(auto_now=True)
    created_at = ndb.DateTimeProperty(auto_now_add=True)


class Team(ndb.Model):
    """
    team_domain is the sub domain for each team
    primary domain is the first one in custom domain
    key_name == team_domain
    """
    team_name = ndb.StringProperty(required=True)
    billing_plan = ndb.StringProperty(choices=('trial', 'free', 'silver', 'gold', 'platinum'), required=True)
    primary_owner = ndb.KeyProperty(kind=User)
    team_domain = ndb.StringProperty(required=True)
    custom_domain = ndb.StructuredProperty(CustomDomain, repeated=True)
    in_use = ndb.BooleanProperty(default=True, required=True)
    updated_at = ndb.DateTimeProperty(auto_now=True)
    created_at = ndb.DateTimeProperty(auto_now_add=True)


class Invitation(ndb.Model):
    """
    key_name = uuid

    """
    sent_to = ndb.StringProperty(required=True)
    team = ndb.KeyProperty(required=True)
    created_by = ndb.KeyProperty(kind=User)
    accepted = ndb.BooleanProperty(default=False)
    updated_at = ndb.DateTimeProperty(auto_now=True)
    created_at = ndb.DateTimeProperty(auto_now_add=True)
    expired_at = ndb.ComputedProperty(lambda self: self.created_at + datetime.timedelta(days=7))


class ShortURL(ndb.Model):
    """
    key_name == domain name + "_" + short url path

    """
    long_url = ndb.StringProperty(required=True)
    short_url = ndb.StringProperty(required=True)
    custom_rule = ndb.JsonProperty()
    team = ndb.KeyProperty(required=True, kind=Team)
    updated_by = ndb.KeyProperty(kind=User)
    created_by = ndb.KeyProperty(kind=User)
    title = ndb.StringProperty()
    site_name = ndb.StringProperty()
    description = ndb.TextProperty()
    memo = ndb.TextProperty()
    image = ndb.StringProperty()
    tags = ndb.StringProperty(repeated=True)
    updated_at = ndb.DateTimeProperty(auto_now=True)
    created_at = ndb.DateTimeProperty(auto_now_add=True)


class ShortURLID(ndb.Model):
    long_url = ndb.StringProperty()
    created_at = ndb.DateTimeProperty(auto_now_add=True)


class Click(ndb.Model):
    short_url = ndb.KeyProperty(required=True, kind=ShortURL)
    referrer = ndb.StringProperty()
    ip_address = ndb.StringProperty()
    location_country = ndb.StringProperty()
    location_region = ndb.StringProperty()
    location_city = ndb.StringProperty()
    location_lat_long = ndb.StringProperty()
    user_agent_raw = ndb.TextProperty()
    user_agent_device = ndb.StringProperty()
    user_agent_device_brand = ndb.StringProperty()
    user_agent_device_model = ndb.StringProperty()
    user_agent_os = ndb.StringProperty()
    user_agent_os_version = ndb.StringProperty()
    user_agent_browser = ndb.StringProperty()
    user_agent_browser_version = ndb.StringProperty()
    custom_code = ndb.StringProperty()
    created_at = ndb.DateTimeProperty(auto_now_add=True)
