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
from functools import wraps
from urllib2 import HTTPError
from urlparse import urlparse

import opengraph
import wtforms_json
from flask import Flask, render_template, request, redirect, url_for, make_response, jsonify
from forms import RegistrationForm, LongURLForm
from google.appengine.api import users
from google.appengine.ext import ndb
from models import Team, User, ShortURL, ShortURLID

wtforms_json.init()
app = Flask(__name__)


def validate_team_user(team_id, user_id):  # type(str, str) -> bool
    team_user_id = "{}_{}".format(team_id, user_id)
    team_user = User.get_by_id(team_user_id)
    if team_user and team_user.in_use is True:
        return True
    logging.info('validation failed: team_id = {}, user_id = {}'.format(team_id, user_id))
    return False


def team_id_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        team_id = request.cookies.get('team', False)
        if validate_team_user(team_id, users.get_current_user().user_id()) is False:
            return make_response(jsonify({'errors': ['bad request, should have team session data']}), 401)
        return f(team_id, *args, **kwargs)

    return decorated_function


def strip_scheme(url):
    parsed = urlparse(url)
    scheme = "%s://" % parsed.scheme
    return parsed.geturl().replace(scheme, '', 1).rstrip('/')


@app.route('/')
def index():
    team_id = request.cookies.get('team', False)
    team_setting_id = request.args.get('team', False)
    if team_id is False and team_setting_id is False:
        return render_template('index.html')
    domain_settings = ['jmpt.me', strip_scheme(request.base_url)]
    if team_id is False and team_setting_id:
        if validate_team_user(team_setting_id, users.get_current_user().user_id()):
            response = make_response(render_template('shorten.html', domain_settings=domain_settings))
            response.set_cookie('team', value=team_setting_id)
            return response
    if team_id and users.get_current_user():
        if validate_team_user(team_id, users.get_current_user().user_id()):
            domain_settings = ['jmpt.me', strip_scheme(request.base_url)]
            return render_template('shorten.html', domain_settings=domain_settings)
    return render_template('index.html')


@ndb.transactional(xg=True)
def insert_user_and_team(user, form_data):
    new_team = Team(team_name=form_data.team_name.data, billing_plan='trial',
                    team_domain=form_data.team_domain.data)
    new_team_key = new_team.put()
    new_team = new_team_key.get()
    new_team_key_id = new_team_key.id()
    user_key_name = "{}_{}".format(new_team_key_id, user.user_id())
    new_team_user = User(id=user_key_name, user_name=form_data.user_name.data, team=new_team.key, role='primary_owner',
                         user=user)
    new_user_key = new_team_user.put()
    new_user_key.get()
    new_team.primary_owner = new_user_key
    new_team.put()
    return new_team_key_id


@app.route('/page/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm(request.form)
    if request.method == 'POST' and form.validate():
        result = insert_user_and_team(users.get_current_user(), form)
        if result:
            return redirect(url_for('index', team=result))
    google_account = users.get_current_user()
    return render_template('register.html', google_account=google_account, form=form)


@app.route('/page/signin', methods=['GET'])
def signin():
    response = make_response(redirect(url_for('index')))
    q = User.query()
    q = q.filter(User.user == users.get_current_user())
    result = q.fetch(1000)
    if len(result) == 1:
        team_id = result[0].key.id().split('_')[:1][0]
        if validate_team_user(team_id, users.get_current_user().user_id()):
            logging.info('set cookie, {}'.format(team_id))
            response.set_cookie('team', value=team_id)
        return response
    elif len(result) > 1:
        team_keys = [r.team for r in result]
        teams = ndb.get_multi(team_keys)
        return render_template('signin.html', teams=teams)
    return response


@app.route('/page/signout', methods=['GET'])
@team_id_required
def signout(team_id):
    response = make_response(redirect(url_for('index')))
    logging.info('remove cookie "team":{}'.format(team_id))
    response.set_cookie('team', '', expires=0)
    return response


def generate_short_url_path(long_url):  # type: (str) -> str
    KEY_BASE = "0123456789abcdefghijklmnopqrstuvwxyz"
    BASE = 36
    short_url_id = ShortURLID(long_url=long_url).put()

    nid = short_url_id.id()
    s = []
    while nid:
        nid, c = divmod(nid, BASE)
        s.append(KEY_BASE[c])
    s.reverse()
    return "".join(s)


@app.route('/api/v1/shorten', methods=['POST'])
@team_id_required
def shorten(team_id):
    user_key_name = "{}_{}".format(team_id, users.get_current_user().user_id())
    user_entity = User.get_by_id(user_key_name)
    form = LongURLForm.from_json(request.get_json())
    if form.validate():
        if form.custom_path.data is None or (form.custom_path.data) == 0:
            path = generate_short_url_path(form.url.data)
        else:
            path = form.custom_path.data.strip()
        key_name = "{}_{}".format(form.domain.data, path)
        try:
            ogp = opengraph.OpenGraph(url=form.url.data)
            warning = None
        except HTTPError:
            ogp = {'title': '', 'description': '', 'site_name': '', 'image': ''}
            warning = 'cannot look up URL, is this right URL?'
        short_url_string = "{}/{}".format(form.domain.data, path)
        short_url = ShortURL(id=key_name, long_url=form.url.data, short_url=short_url_string,
                             team=user_entity.team, created_by=user_entity.key,
                             title=ogp.get('title', ''), description=ogp.get('description', ''),
                             site_name=ogp.get('site_name', ''), image=ogp.get('image', '')
                             )
        short_url.put()
        result = {'short_url': short_url_string, 'title': short_url.title,
                  'description': short_url.description,
                  'image': short_url.image, 'warning': warning}
        return jsonify(result)
    errors = []
    for field in form:
        if len(field.errors) > 0:
            for e in field.errors:
                errors.append(e)
    return make_response(jsonify({'errors': errors}), 400)


@app.route('/api/v1/short_urls/<short_url_domain>/<short_url_path>', methods=['DELETE'])
@team_id_required
def delete_shorten_url(team_id, short_url_domain, short_url_path):
    short_url = ShortURL.get_by_id("{}_{}".format(short_url_domain, short_url_path))
    if short_url is None:
        return make_response(jsonify({'errors': ['the short url was not found']}), 404)
    if str(short_url.team.id()) != str(team_id):
        return make_response(jsonify({'errors': ['you can not delete the short url']}), 400)
    short_url.key.delete()
    return jsonify({'success': 'the url was deleted'})


@app.route('/api/v1/short_urls', methods=['GET'])
@team_id_required
def shorten_urls(team_id):
    user_key_name = "{}_{}".format(team_id, users.get_current_user().user_id())
    user_entity = User.get_by_id(user_key_name)
    q = ShortURL.query()
    q = q.filter(ShortURL.team == user_entity.team).order(-ShortURL.created_at)
    entities = q.fetch(1000)
    results = [{'short_url': e.short_url,
                'title': e.title,
                'long_url': e.long_url,
                'image': e.image,
                'description': e.description,
                'created_at': e.created_at.strftime('%Y-%m-%d %H:%M:%S%Z')} for e in entities]
    return jsonify({'results': results})


@app.errorhandler(500)
def server_error(e):
    # Log the error and stacktrace.
    logging.exception('An error occurred during a request.')
    return 'An internal error occurred.', 500

# [END app]
