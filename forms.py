import re

import validators as altvalidator
from models import Team, ShortURL
from wtforms import Form, StringField, validators, ValidationError, TextAreaField


class RegistrationForm(Form):
    user_name = StringField('User Name', [
        validators.Length(min=1, max=25, message='User Name should be between 1 and 25 characters')])
    team_name = StringField('Team Name', [
        validators.Length(min=1, max=25, message='Team Name should be between 1 and 25 characters')])
    team_domain = StringField('Team Domain', [
        validators.Length(min=1, max=10, message='Team Domain should be between 1 and 10 characters')])

    def validate_team_domain(form, field):
        if len(field.data) > 0:
            q = Team.query()
            q = q.filter(Team.team_domain == field.data)
            v_team_domain = q.fetch(10)
            if len(v_team_domain) > 0:
                raise ValidationError('Team Domain already used')


class LongURLForm(Form):
    url = StringField('Long URL', [validators.URL(message='String posted was not valid URL')])
    domain = StringField('Domain Name', [
        validators.Length(min=1, max=25, message='Domain name should be between 1 and 25 characters')])
    custom_path = StringField('Custom Path')

    def validate_domain(form, field):
        if len(field.data) > 0 and altvalidator.domain(field.data) is not True:
            raise ValidationError(message='Invalid domain name')

    def validate_custom_path(form, field):
        if field.data is not None and (field.data) > 0 and re.match(ur'^[a-z0-9]*$', field.data) is None:
            raise ValidationError(message='Invalid custom path name, should be lower case alphabet and number')
        key_name = "{}_{}".format(form.domain.data, field.data)
        short_url = ShortURL.get_by_id(key_name)
        if short_url is not None:
            raise ValidationError(message='The short URL path exists already')


class UpdateShortURLForm(Form):
    tag = StringField('Tag',
                      [validators.optional(),
                       validators.Length(min=1, max=25, message='Tag name should be between 1 and 25 characters')])
    memo = TextAreaField('Memo for short url', [validators.optional(), validators.length(max=500)])

    def validate(self):
        if not self.tag.data and not self.memo.data:
            message = 'At least one of Tag and Memo must be set'
            self.tag.errors = [message]
            return False
        return True


class InvitationForm(Form):
    email = StringField('Email', [
        validators.Email('Invalid email address')])


class RoleForm(Form):
    role = StringField('Role', [validators.AnyOf(values=['admin', 'normal'], message='role should be admin or normal')])
    user_id = StringField('User ID', [validators.Length(min=3, message='User ID too short')])
