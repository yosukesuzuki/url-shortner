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
    tags = ndb.ComputedProperty(lambda e: ShortURL.tags.get_value_for_datastore(e.short_url))
    referrer = ndb.StringProperty()
    ip_address = ndb.StringProperty()
    user_agent = ndb.StringProperty()
    get_parameters = ndb.JsonProperty()
    created_at = ndb.DateTimeProperty(auto_now_add=True)
