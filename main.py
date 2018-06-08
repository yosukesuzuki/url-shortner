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
import os
import logging
import datetime
import uuid
from functools import wraps
from urllib2 import HTTPError
from urlparse import urlparse
from StringIO import StringIO

import opengraph
import wtforms_json
from flask import Flask, render_template, request, redirect, url_for, make_response, jsonify, send_file
import qrcode

from forms import RegistrationForm, LongURLForm, UpdateShortURLForm, InvitationForm, RoleForm
from google.appengine.api import users, memcache
from google.appengine.ext import ndb, deferred
from google.appengine.datastore.datastore_query import Cursor
from models import Team, User, ShortURL, ShortURLID, Invitation, Click, APIToken
from tasks import write_click_log, send_invitation

wtforms_json.init()
app = Flask(__name__)


def validate_team_user(team_id, user_id):  # type(str, str) -> bool
    team_user_id = "{}_{}".format(team_id, user_id)
    memcache_key = "validation-{}".format(team_user_id)
    validation_result = memcache.get(memcache_key)
    if validation_result:
        return validation_result
    team_user = User.get_by_id(team_user_id)
    if team_user and team_user.in_use is True:
        team = team_user.team.get()
        team_name = team.team_name
        memcache.set(memcache_key, team_name)
        return team_name
    logging.info('validation failed: team_id = {}, user_id = {}'.format(team_id, user_id))
    return False


def team_id_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        team_id = request.cookies.get('team', False)
        team_name = validate_team_user(team_id, users.get_current_user().user_id())
        if team_name is False:
            return make_response(jsonify({'errors': ['bad request, should have team session data']}), 401)
        return f(team_id, team_name, *args, **kwargs)

    return decorated_function


def strip_scheme(url):
    parsed = urlparse(url)
    scheme = "%s://" % parsed.scheme
    return parsed.geturl().replace(scheme, '', 1).rstrip('/')


def is_local():
    return os.environ["SERVER_NAME"] in ("localhost", "www.lexample.com")


@app.route('/')
def index():
    team_id = request.cookies.get('team', False)
    team_setting_id = request.args.get('team', False)
    if team_id is False and team_setting_id is False:
        logging.info('team_id(cookie) and team_setting_id(GET parameter) are both empty. Render index.html')
        return render_template('index.html')
    domain_settings = [strip_scheme(request.base_url)]
    if is_local():
        domain_settings = ['jmpt.me'] + domain_settings
    if team_id is False and team_setting_id:
        team_name = validate_team_user(team_setting_id, users.get_current_user().user_id())
        if team_name:
            logging.info(
                'user validation from team_setting_id(GET parameter) is successfully done. Render shorten.html')
            response = make_response(render_template('shorten.html', domain_settings=domain_settings,
                                                     team_name=team_name))
            response.set_cookie('team', value=team_setting_id)
            return response
    if team_id and users.get_current_user():
        team_name = validate_team_user(team_id, users.get_current_user().user_id())
        if team_name:
            logging.info(
                'user validation from team_id(cookie) is successfully done. Render shorten.html')
            return render_template('shorten.html', domain_settings=domain_settings, team_name=team_name)
    return render_template('index.html')


@ndb.transactional(xg=True)
def insert_user_and_team(user, form_data):
    new_team = Team(team_name=form_data.team_name.data, billing_plan='trial',
                    team_domain=form_data.team_domain.data)
    new_team_key = new_team.put()
    new_team = new_team_key.get()
    new_team_key_id = new_team_key.id()
    user_key_name = "{}_{}".format(new_team_key_id, user.user_id())
    new_team_user = User(id=user_key_name,
                         user_name=form_data.user_name.data,
                         email=user.email(),
                         team=new_team.key,
                         role='primary_owner',
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
    q = User.query()
    q = q.filter(User.user == users.get_current_user())
    result = q.fetch(1000)
    if len(result) == 1:
        team_id = result[0].key.id().split('_')[:1][0]
        response = make_response(redirect(url_for('index')))
        if validate_team_user(team_id, users.get_current_user().user_id()):
            logging.info('set cookie, {}'.format(team_id))
            response.set_cookie('team', value=team_id)
        return response
    elif len(result) > 1:
        team_keys = [r.team for r in result]
        teams = ndb.get_multi(team_keys)
        return render_template('signin.html', teams=teams)
    response = make_response(redirect(url_for('index', message='not_registered')))
    return response


@app.route('/page/signout', methods=['GET'])
@team_id_required
def signout(team_id, team_name):
    response = make_response(redirect(url_for('index')))
    logging.info('remove cookie "team":{}'.format(team_id))
    response.set_cookie('team', '', expires=0)
    return response


@app.route('/page/settings', methods=['GET', 'POST'])
@team_id_required
def settings(team_id, team_name):
    form = InvitationForm(request.form)
    messages = []
    errors = []
    team_users = User.query().filter(User.team == Team.get_by_id(int(team_id)).key).order(-Team.created_at).fetch()
    team_user_dic = {u.key.id(): u.user_name for u in team_users}
    user_key_name = "{}_{}".format(team_id, users.get_current_user().user_id())
    user_entity = User.get_by_id(user_key_name)
    if request.method == 'POST' and form.validate():
        if is_local():
            host_name = 'jmpt.me'
        else:
            host_name = request.host
        result = send_invitation(form.email.data, team_id, users.get_current_user().user_id(), host_name)
        if result:
            messages.append('Invitation sent')
        else:
            errors.append('Invitation sent failed')
    api_token_query_results = APIToken.query().filter(APIToken.team == Team.get_by_id(int(team_id)).key).order(
        -APIToken.created_at).fetch()
    api_tokens = [{'token': t.key.id(), 'created_by': team_user_dic[t.created_by.id()], 'created_at': str(t.created_at)}
                  for t in api_token_query_results]
    return render_template('team_settings.html',
                           team_name=team_name,
                           team_users=team_users,
                           api_tokens=api_tokens,
                           current_user=user_entity,
                           form=form,
                           messages=messages,
                           errors=errors)


@app.route('/page/token', methods=['POST'])
@team_id_required
def generate_token(team_id, team_name):
    user_key_name = "{}_{}".format(team_id, users.get_current_user().user_id())
    user_entity = User.get_by_id(user_key_name)
    key_name = uuid.uuid4().hex
    APIToken(id=key_name, team=user_entity.team, created_by=user_entity.key).put()
    response = make_response(redirect(url_for('settings')))
    return response


@app.route('/page/token/<token_id>', methods=['DELETE'])
@team_id_required
def delete_token(team_id, team_name, token_id):
    user_key_name = "{}_{}".format(team_id, users.get_current_user().user_id())
    user_entity = User.get_by_id(user_key_name)
    if user_entity.role in ['primary_owner', 'admin']:
        api_token = APIToken.get_by_id(token_id)
        api_token.key.delete()
    response = make_response(redirect(url_for('settings')))
    return response


@app.route('/page/role', methods=['POST'])
@team_id_required
def change_role(team_id, team_name):
    user_key_name = "{}_{}".format(team_id, users.get_current_user().user_id())
    user_entity = User.get_by_id(user_key_name)
    form = RoleForm(request.form)
    if request.method == 'POST' and form.validate():
        if user_entity.role in ['admin', 'primary_owner']:
            if form.user_id.data.startswith(str(user_entity.team.id())):
                target_user = User.get_by_id(form.user_id.data)
                target_user.role = form.role.data
                target_user.put()
                response = make_response(redirect(url_for('settings')))
                return response
            logging.info('user_id does not match to operater team id')
        logging.info('operater role is not enough')
        return render_template('invalid.html'), 400
    else:
        logging.info('form validation failed')
        return render_template('invalid.html'), 400


@app.route('/page/invitation/<invitation_id>', methods=['GET'])
def accept_invitation(invitation_id):
    invitation = Invitation.get_by_id(invitation_id)
    if datetime.datetime.now() > invitation.expired_at:
        errors = ['Invitaiton was expired']
        return render_template('invitation_error.html', errors=errors), 400
    if invitation.accepted is True:
        errors = ['Invitaiton was already used']
        return render_template('invitation_error.html', errors=errors), 400
    user_key_name = "{}_{}".format(invitation.team.id(), users.get_current_user().user_id())
    q = User.query()
    q = q.filter(User.team == Team.get_by_id(invitation.team.id()).key)
    q = q.filter(User.email == users.get_current_user().email())
    results = q.fetch(1000)
    if len(results) > 0:
        errors = ['Your email account already exist in team']
        return render_template('invitation_error.html', errors=errors), 400
    User(id=user_key_name,
         user_name=users.get_current_user().nickname(),
         email=users.get_current_user().email(),
         team=invitation.team,
         role='normal',
         user=users.get_current_user()).put()
    invitation.accepted = True
    invitation.put()
    response = make_response(redirect(url_for('index')))
    response.set_cookie('team', value=str(invitation.team.id()))
    return response


@app.route('/page/detail/<short_url_domain>/<short_url_path>', methods=['GET'])
@team_id_required
def detail(team_id, team_name, short_url_domain, short_url_path):
    user_key_name = "{}_{}".format(team_id, users.get_current_user().user_id())
    user_entity = User.get_by_id(user_key_name)
    short_url = ShortURL.get_by_id("{}_{}".format(short_url_domain, short_url_path))
    if short_url is None:
        return make_response(render_template('404.html'), 404)
    if short_url.team != user_entity.team:
        return make_response(jsonify({'errors': ['you can not edit this short url']}), 401)
    return render_template('detail.html', short_url=short_url, team_name=team_name, short_url_domain=short_url_domain,
                           short_url_path=short_url_path)


@app.route('/image/qr/<short_url_domain>/<short_url_path>', methods=['GET'])
@team_id_required
def generate_qrcode(team_id, team_name, short_url_domain, short_url_path):
    short_url = ShortURL.get_by_id("{}_{}".format(short_url_domain, short_url_path))
    if short_url is None:
        return make_response(render_template('404.html'), 404)
    qrcode_image = qrcode.make('https://{}/{}'.format(short_url_domain, short_url_path))
    image_io = StringIO()
    qrcode_image.save(image_io)
    image_io.seek(0)
    return send_file(image_io, mimetype='image/png')


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
def shorten(team_id, team_name):
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
        except KeyError:
            ogp = {'title': '', 'description': '', 'site_name': '', 'image': ''}
            warning = 'cannot parse OGP data'
        short_url_string = "{}/{}".format(form.domain.data, path)
        short_url = ShortURL(id=key_name, long_url=form.url.data, short_url=short_url_string,
                             team=user_entity.team, updated_by=user_entity.key, created_by=user_entity.key,
                             title=ogp.get('title', ''), description=ogp.get('description', ''),
                             site_name=ogp.get('site_name', ''), image=ogp.get('image', '')
                             )
        short_url.put()
        result = {'short_url': short_url_string,
                  'title': short_url.title,
                  'long_url': short_url.long_url,
                  'description': short_url.description,
                  'image': short_url.image,
                  'created_at': short_url.created_at.strftime('%Y-%m-%d %H:%M:%S%Z'),
                  'id': short_url.key.id(),
                  'warning': warning,
                  }
        return jsonify(result)
    errors = []
    for field in form:
        if len(field.errors) > 0:
            for e in field.errors:
                errors.append(e)
    return make_response(jsonify({'errors': errors}), 400)


@app.route('/api/v1/short_urls/<short_url_domain>/<short_url_path>', methods=['GET', 'PATCH'])
@team_id_required
def update_shorten_url(team_id, team_name, short_url_domain, short_url_path):
    user_key_name = "{}_{}".format(team_id, users.get_current_user().user_id())
    user_entity = User.get_by_id(user_key_name)
    short_url = ShortURL.get_by_id("{}_{}".format(short_url_domain, short_url_path))
    if short_url is None:
        return make_response(jsonify({'errors': ['the short url was not found']}), 404)
    if str(short_url.team.id()) != str(team_id):
        return make_response(jsonify({'errors': ['you can not update the short url']}), 400)
    form = UpdateShortURLForm.from_json(request.get_json())
    if form.validate():
        if form.tag.data is not None:
            tags = short_url.tags
            tags.append(form.tag.data)
            short_url.tags = set(tags)
        if form.memo.data is not None:
            short_url.memo = form.memo.data
        short_url.updated_by = user_entity.key
        short_url.put()
        result = {'short_url': '{}/{}'.format(short_url_domain, short_url_path), 'title': short_url.title,
                  'description': short_url.description,
                  'image': short_url.image, 'tags': short_url.tags, 'memo': short_url.memo}
        return jsonify(result)
    errors = []
    for field in form:
        if len(field.errors) > 0:
            for e in field.errors:
                errors.append(e)
    return make_response(jsonify({'errors': errors}), 400)


@app.route('/api/v1/short_urls/<short_url_domain>/<short_url_path>/tags/<tag>', methods=['DELETE'])
@team_id_required
def delete_shorten_url_tag(team_id, team_name, short_url_domain, short_url_path, tag):
    user_key_name = "{}_{}".format(team_id, users.get_current_user().user_id())
    user_entity = User.get_by_id(user_key_name)
    short_url = ShortURL.get_by_id("{}_{}".format(short_url_domain, short_url_path))
    if short_url is None:
        return make_response(jsonify({'errors': ['the short url was not found']}), 404)
    if str(short_url.team.id()) != str(team_id):
        return make_response(jsonify({'errors': ['you can not update the short url']}), 400)
    tags = short_url.tags
    tags.remove(tag)
    short_url.tags = set(tags)
    short_url.updated_by = user_entity.key
    short_url.put()
    result = {'short_url': '{}/{}'.format(short_url_domain, short_url_path), 'title': short_url.title,
              'description': short_url.description,
              'image': short_url.image, 'tags': short_url.tags, 'memo': short_url.memo}
    return jsonify(result)


@app.route('/api/v1/short_urls/<short_url_domain>/<short_url_path>', methods=['DELETE'])
@team_id_required
def delete_shorten_url(team_id, team_name, short_url_domain, short_url_path):
    short_url = ShortURL.get_by_id("{}_{}".format(short_url_domain, short_url_path))
    if short_url is None:
        return make_response(jsonify({'errors': ['the short url was not found']}), 404)
    if str(short_url.team.id()) != str(team_id):
        return make_response(jsonify({'errors': ['you can not delete the short url']}), 400)
    short_url.key.delete()
    return jsonify({'success': 'the url was deleted'})


@app.route('/api/v1/short_urls', methods=['GET'])
@team_id_required
def shorten_urls(team_id, team_name):
    user_key_name = "{}_{}".format(team_id, users.get_current_user().user_id())
    user_entity = User.get_by_id(user_key_name)
    q = ShortURL.query()
    q = q.filter(ShortURL.team == user_entity.team).order(-ShortURL.created_at)
    cursor = Cursor(urlsafe=request.args.get('cursor'))
    entities, next_cursor, more = q.fetch_page(10, start_cursor=cursor)
    results = [{'short_url': e.short_url,
                'title': e.title,
                'long_url': e.long_url,
                'image': e.image,
                'description': e.description,
                'memo': e.memo,
                'tags': e.tags,
                'created_at': e.created_at.strftime('%Y-%m-%d %H:%M:%S%Z'),
                'id': e.key.id()} for e in entities]
    return jsonify({'results': results, 'next_cursor': next_cursor.urlsafe() if next_cursor else None, 'more': more})


@app.route('/api/v1/data/<short_url_domain>/<short_url_path>', methods=['GET'])
@team_id_required
def data_short_url(team_id, team_name, short_url_domain, short_url_path):
    short_url = ShortURL.get_by_id("{}_{}".format(short_url_domain, short_url_path))
    if short_url is None:
        return make_response(jsonify({'errors': ['data not found']}), 404)
    if str(short_url.team.id()) != str(team_id):
        return make_response(jsonify({'errors': ['you can not access to this data']}), 400)
    q = Click.query()
    q = q.filter(Click.short_url == short_url.key).order(Click.created_at)
    clicks = q.fetch(1000)
    results = [{
        'referrer_medium': c.referrer_medium,
        'location_country': c.location_country,
        'user_agent_device': c.user_agent_device,
        'user_agent_browser': c.user_agent_browser,
        'short_url': c.short_url.id(),
        'created_at': c.created_at.isoformat(),
    } for c in clicks]
    aggregated_dic = {}
    for r in results:
        date = r['created_at'][:10]
        if date in aggregated_dic:
            aggregated_dic[date].append(r)
        else:
            aggregated_dic[date] = [r]
    aggregated = []
    for key, value in aggregated_dic.iteritems():
        aggregated.append({'date': key, 'data': value, 'count': len(value)})
    return make_response(jsonify({'results': sorted(aggregated, key=lambda x: x['date'])}), 200)


@app.route('/page/terms', methods=['GET'])
def terms():
    return render_template('terms.html')


@app.route('/page/privacy', methods=['GET'])
def privacy():
    return render_template('privacy.html')


@app.route('/<short_url_path>', methods=['GET'])
def extract_short_url(short_url_path):
    if is_local():
        host_name = 'jmpt.me'
    else:
        host_name = request.host
    short_url = ShortURL.get_by_id("{}_{}".format(host_name, short_url_path))
    if short_url is None:
        response = make_response(render_template('404.html'), 404)
        return response
    deferred.defer(write_click_log,
                   short_url.key,
                   request.referrer,
                   request.remote_addr,
                   request.headers.get('X-AppEngine-Country'),
                   request.headers.get('X-AppEngine-Region'),
                   request.headers.get('X-AppEngine-City'),
                   request.headers.get('X-AppEngine-CityLatLong'),
                   request.user_agent,
                   request.args)
    return redirect(short_url.long_url, code=302)


@app.errorhandler(404)
def handle_404_page(e):
    return render_template('404.html')


@app.errorhandler(500)
def server_error(e):
    # Log the error and stacktrace.
    logging.exception('An error occurred during a request.')
    return 'An internal error occurred.', 500

# [END app]
