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

from flask import Flask, render_template, request, Response
from forms import RegistrationForm
from google.appengine.api import users
from google.appengine.ext import ndb
from models import Team, User

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@ndb.transactional(xg=True)
def insert_user_and_team(new_user, form_data):
    new_team = Team(id=form_data.team_domain.data, team_name=form_data.team_name.data, billing_plan='trial',
                    team_domain=form_data.team_domain.data)
    new_team_key = new_team.put()
    new_team = new_team_key.get()
    user_key_name = form_data.team_domain.data + "_" + new_user.user_id()
    new_user = User(id=user_key_name, user_name=form_data.user_name.data, team=new_team.key, role='primary_owner',
                    user=new_user)
    new_user_key = new_user.put()
    new_user_key.get()
    new_team.primary_owner = new_user_key
    new_team.put()


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm(request.form)
    if request.method == 'POST' and form.validate():
        insert_user_and_team(users.get_current_user(), form)
        return Response('ok')
    google_account = users.get_current_user()
    return render_template('register.html', google_account=google_account, form=form)


@app.errorhandler(500)
def server_error(e):
    # Log the error and stacktrace.
    logging.exception('An error occurred during a request.')
    return 'An internal error occurred.', 500

# [END app]
