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
    long_url = ndb.StringProperty()
    custom_rule = ndb.JsonProperty()
    updated_at = ndb.DateTimeProperty(auto_now=True)
    created_at = ndb.DateTimeProperty(auto_now_add=True)


class ShortURLID(ndb.Model):
    created_at = ndb.DateTimeProperty(auto_now_add=True)

    KEY_BASE = "0123456789abcdefghijklmnopqrstuvwxyz"
    BASE = 36

    @property
    def path(self):
        """Return our path, our base-36 encoded id"""
        if not self.is_saved():
            return None
        nid = self.key().id()
        s = []
        while nid:
            nid, c = divmod(nid, ShortURLID.BASE)
            s.append(ShortURLID.KEY_BASE[c])
        s.reverse()
        return "".join(s)
