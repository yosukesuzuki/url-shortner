from models import Team
from wtforms import Form, StringField, validators, ValidationError


class RegistrationForm(Form):
    user_name = StringField('User Name', [validators.Length(min=1, max=25)])
    team_name = StringField('Team Name', [validators.Length(min=1, max=25)])
    team_domain = StringField('Team Domain', [validators.Length(min=1, max=10)])

    def validate_team_domain(form, field):
        if len(field.data) > 0:
            v_team_domain = Team.get_by_id(field.data)
            if v_team_domain is not None:
                raise ValidationError('Team Domain already used')
