import re

import validators as altvalidater
from models import Team, ShortURL
from wtforms import Form, StringField, validators, ValidationError


class RegistrationForm(Form):
    user_name = StringField('User Name', [validators.Length(min=1, max=25)])
    team_name = StringField('Team Name', [validators.Length(min=1, max=25)])
    team_domain = StringField('Team Domain', [validators.Length(min=1, max=10)])

    def validate_team_domain(form, field):
        if len(field.data) > 0:
            q = Team.query()
            q = q.filter(Team.team_domain == field.data)
            v_team_domain = q.fetch(10)
            if len(v_team_domain) > 0:
                raise ValidationError('Team Domain already used')


class LongURLForm(Form):
    url = StringField('Long URL', [validators.URL('String posted was not valid URL')])
    domain = StringField('Domain Name', [validators.Length(min=1, max=25)])
    custom_path = StringField('Custom Path')

    def validate_domain(form, field):
        if len(field.data) > 0 and altvalidater.domain(field.data) is False:
            raise ValidationError('invalid domain name')

    def validate_custom_path(form, field):
        if len(field.data) > 0 and re.match('^[a-z0-9]*$', field.data) is False:
            raise ValidationError('invalid custom path name, should be lower case alphabet and number')
        key_name = "{}_{}".format(form.domain.data, field.data)
        short_url = ShortURL.get_by_id(key_name)
        if short_url is not None:
            raise ValidationError('the Short URL path exists already')
