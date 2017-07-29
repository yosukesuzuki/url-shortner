from models import Team
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
