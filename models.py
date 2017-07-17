import validators
from google.appengine.api import datastore_errors
from google.appengine.ext import ndb


def fqdn_validator(prop, value):
    if validators.domain(value) is not True:
        raise datastore_errors.BadValueError(prop._name)


class CustomDomain(ndb.Model):
    fqdn = ndb.StringProperty(validator=fqdn_validator)
    verified = ndb.BooleanProperty(default=False)
    updated_at = ndb.DateTimeProperty(auto_now=True)
    created_at = ndb.DateTimeProperty(auto_now_add=True)


class Team(ndb.Model):
    """
    team_domain is the sub domain for each team
    """
    team_name = ndb.StringProperty(required=True)
    billing_plan = ndb.KeyProperty(required=True)
    primary_owner = ndb.KeyProperty(required=True)
    team_domain = ndb.StringProperty(required=True)
    custom_domain = ndb.StructuredProperty(CustomDomain, repeated=True)
    updated_at = ndb.DateTimeProperty(auto_now=True)
    created_at = ndb.DateTimeProperty(auto_now_add=True)


class User(ndb.Model):
    """
    key_name = team_name + "_" + user_no

    """
    user = ndb.UserProperty()
    user_id = ndb.StringProperty()  # user can set
    user_name = ndb.StringProperty()  # display name
    team = ndb.KeyProperty()
    role = ndb.StringProperty(choices=('primary_owner', 'admin', 'normal'))
    updated_at = ndb.DateTimeProperty(auto_now=True)
    created_at = ndb.DateTimeProperty(auto_now_add=True)
