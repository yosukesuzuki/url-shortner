# Copyright 2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# [START app]
import logging

from flask import Flask, render_template, request, redirect, url_for, make_response
from forms import RegistrationForm
from google.appengine.api import users
from google.appengine.ext import ndb
from models import Team, User

app = Flask(__name__)


def validate_team_user(team_id, user_id):
    user_id = "{}_{}".format(team_id, user_id)
    team_user = User.get_by_id(user_id)
    if team_user and team_user.in_use is True:
        return True
    return False


@app.route('/')
def index():
    team_id = request.cookies.get('team', False)
    team_setting_id = request.args.get('team', False)
    if team_id is False and team_setting_id is False:
        return render_template('index.html')
    if team_id is False and team_setting_id:
        if validate_team_user(team_setting_id, users.get_current_user().user_id()):
            response = make_response(render_template('shorten.html'))
            response.set_cookie('team', value=team_setting_id)
            return response
    if team_id and users.get_current_user():
        if validate_team_user(team_id, users.get_current_user().user_id()):
            return render_template('shorten.html')
    return render_template('index.html')


@ndb.transactional(xg=True)
def insert_user_and_team(new_user, form_data):
    new_team = Team(team_name=form_data.team_name.data, billing_plan='trial',
                    team_domain=form_data.team_domain.data)
    new_team_key = new_team.put()
    new_team = new_team_key.get()
    new_team_key_id = new_team_key.id()
    user_key_name = "{}_{}".format(new_team_key_id, new_user.user_id())
    new_user = User(id=user_key_name, user_name=form_data.user_name.data, team=new_team.key, role='primary_owner',
                    user=new_user)
    new_user_key = new_user.put()
    new_user_key.get()
    new_team.primary_owner = new_user_key
    new_team.put()
    return new_team_key_id


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm(request.form)
    if request.method == 'POST' and form.validate():
        result = insert_user_and_team(users.get_current_user(), form)
        if result:
            return redirect(url_for('index', team=result))
    google_account = users.get_current_user()
    return render_template('register.html', google_account=google_account, form=form)


@app.errorhandler(500)
def server_error(e):
    # Log the error and stacktrace.
    logging.exception('An error occurred during a request.')
    return 'An internal error occurred.', 500


# [END app]
