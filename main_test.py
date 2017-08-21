# Copyright 2016 Google Inc. All Rights Reserved.
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

import json
import logging
import unittest
from urlparse import urlparse

from google.appengine.api import users
from google.appengine.datastore import datastore_stub_util
from google.appengine.ext import ndb
from google.appengine.ext import testbed
from main import app
from mock import patch
from models import User, Team, ShortURL


class MainHandlerTest(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.app = app.test_client()
        ndb.get_context().clear_cache()

    def tearDown(self):
        self.testbed.deactivate()

    def testIndex(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)


class RegisterHandlerTest(unittest.TestCase):
    def setUp(self):
        self.policy = datastore_stub_util.PseudoRandomHRConsistencyPolicy(probability=1)
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub(consistency_policy=self.policy)
        self.testbed.init_memcache_stub()
        self.testbed.setup_env(
            user_email='example@example.com',
            user_id='1234567890',
            user_is_admin='1',
            overwrite=True)
        self.app = app.test_client()
        ndb.get_context().clear_cache()

    def tearDown(self):
        self.testbed.deactivate()

    def testRegisterGet(self):
        response = self.app.get('/page/register')
        self.assertEqual(response.status_code, 200)

    def testRegisterPost(self):
        response = self.app.post('/page/register',
                                 data={'user_name': 'test user', 'team_name': 'test team', 'team_domain': 'test'},
                                 follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.headers.get('Location')).path, '/')
        team_results = Team.query().fetch(1000)
        self.assertEqual(len(team_results), 1)
        self.assertEqual(team_results[0].team_name, 'test team')
        self.assertEqual(team_results[0].billing_plan, 'trial')
        self.assertEqual(team_results[0].team_domain, 'test')
        user_results = User.query().fetch(1000)
        self.assertEqual(len(user_results), 1)
        self.assertEqual(user_results[0].user_name, 'test user')
        self.assertEqual(user_results[0].team, team_results[0].key)
        self.assertEqual(user_results[0].role, 'primary_owner')
        self.assertEqual(user_results[0].key.id(), '{}_{}'.format(team_results[0].key.id(), '1234567890'))


class ShortenHandlerTest(unittest.TestCase):
    def setUp(self):
        self.policy = datastore_stub_util.PseudoRandomHRConsistencyPolicy(probability=1)
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub(consistency_policy=self.policy)
        self.testbed.init_memcache_stub()
        self.testbed.setup_env(
            user_email='example@example.com',
            user_id='1234567890',
            user_is_admin='1',
            overwrite=True)
        self.app = app.test_client()
        ndb.get_context().clear_cache()
        new_team = Team(team_name='hoge', billing_plan='trial',
                        team_domain='ysk')
        new_team_key = new_team.put()
        new_team = new_team_key.get()
        new_team_key_id = new_team_key.id()
        self.team_id = new_team_key_id
        user_key_name = "{}_{}".format(new_team_key_id, users.get_current_user().user_id())
        logging.info(user_key_name)
        new_team_user = User(id=user_key_name, user_name='hoge', team=new_team.key, role='primary_owner',
                             user=users.get_current_user())
        new_team_user.put()
        self.user_id = user_key_name

    def tearDown(self):
        self.testbed.deactivate()

    @patch('opengraph.OpenGraph')
    def testShortenPost(self, OpenGraph):
        OpenGraph.return_value = {'title': 'GitHub', 'description': 'GitHub is where people build software',
                                  'site_name': 'GitHub',
                                  'image': 'https://assets-cdn.github.com/images/modules/open_graph/github-logo.png'}
        bad_response = self.app.post('/api/v1/shorten',
                                     data=json.dumps({'url': 'http://github.com', 'domain': 'jmpt.me'}),
                                     content_type='application/json',
                                     follow_redirects=False)
        self.assertEqual(bad_response.status_code, 401)
        self.assertEqual(json.loads(bad_response.data)['errors'], ['bad request, should have team session data'])
        self.app.set_cookie('localhost', 'team', str(self.team_id))
        response = self.app.post('/api/v1/shorten',
                                 data=json.dumps({'url': 'http://github.com', 'domain': 'jmpt.me'}),
                                 content_type='application/json',
                                 follow_redirects=False)
        self.assertEqual(response.status_code, 200)
        short_urls = ShortURL.query().fetch(1000)
        self.assertEqual(short_urls[0].long_url, 'http://github.com')
        self.assertEqual(short_urls[0].created_by, User.get_by_id(self.user_id).key)
        self.assertEqual(short_urls[0].key.id().startswith('jmpt.me_'), True)
        self.assertEqual(short_urls[0].team.id(), self.team_id)
        self.assertEqual(short_urls[0].title, 'GitHub')
        self.assertEqual(short_urls[0].image,
                         'https://assets-cdn.github.com/images/modules/open_graph/github-logo.png')
        self.assertEqual(short_urls[0].site_name, 'GitHub')
        self.assertEqual(short_urls[0].description, 'GitHub is where people build software')
        bad_request = self.app.post('/api/v1/shorten',
                                    data=json.dumps({'url': 'hoge.hage', 'domain': 'jmpt.me'}),
                                    content_type='application/json',
                                    follow_redirects=False)
        self.assertEqual(json.loads(bad_request.data)['errors'], ['String posted was not valid URL'])
        bad_request_longdomain = self.app.post('/api/v1/shorten',
                                               data=json.dumps({'url': 'https://github.com',
                                                                'domain': 'jjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjmpt.me'}),
                                               content_type='application/json',
                                               follow_redirects=False)
        self.assertEqual(json.loads(bad_request_longdomain.data)['errors'],
                         ['Domain name should be between 1 and 25 characters'])

    @patch('opengraph.OpenGraph')
    def testCustomeShortenPost(self, OpenGraph):
        OpenGraph.return_value = {'title': 'GitHub', 'description': 'GitHub is where people build software',
                                  'site_name': 'GitHub',
                                  'image': 'https://assets-cdn.github.com/images/modules/open_graph/github-logo.png'}
        self.app.set_cookie('localhost', 'team', str(self.team_id))
        response = self.app.post('/api/v1/shorten',
                                 data=json.dumps(
                                     {'url': 'https://github.com/yosukesuzuki/url-shortner', 'domain': 'jmpt.me',
                                      'custom_path': 'jmptme'}),
                                 content_type='application/json',
                                 follow_redirects=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data)['short_url'], 'jmpt.me/jmptme')
        short_urls = ShortURL.query().order(-ShortURL.created_at).fetch(1000)
        self.assertEqual(short_urls[0].key.id(), 'jmpt.me_jmptme')
        self.assertEqual(short_urls[0].team.id(), self.team_id)
        bad_response = self.app.post('/api/v1/shorten',
                                     data=json.dumps(
                                         {'url': 'https://github.com/yosukesuzuki/url-shortner', 'domain': 'hoge.hoge',
                                          'custom_path': 'HOGE'}),
                                     content_type='application/json',
                                     follow_redirects=False)
        self.assertEqual(bad_response.status_code, 400)
        self.assertEqual(json.loads(bad_response.data)['errors'],
                         ['Invalid custom path name, should be lower case alphabet and number'])
        bad_response_domain = self.app.post('/api/v1/shorten',
                                            data=json.dumps({'url': 'https://github.com/yosukesuzuki/url-shortner',
                                                             'domain': 'hoge.1',
                                                             'custom_path': 'hoge'}),
                                            content_type='application/json',
                                            follow_redirects=False)
        self.assertEqual(bad_response_domain.status_code, 400)
        self.assertEqual(json.loads(bad_response_domain.data)['errors'],
                         ['Invalid domain name'])
        bad_response_duplication = self.app.post('/api/v1/shorten',
                                                 data=json.dumps({'url': 'https://github.com/yosukesuzuki/url-shortner',
                                                                  'domain': 'jmpt.me',
                                                                  'custom_path': 'jmptme'}),
                                                 content_type='application/json',
                                                 follow_redirects=False)
        self.assertEqual(bad_response_duplication.status_code, 400)
        self.assertEqual(json.loads(bad_response_duplication.data)['errors'],
                         ['The short URL path exists already'])


class ShortURLAPITest(unittest.TestCase):
    def setUp(self):
        self.policy = datastore_stub_util.PseudoRandomHRConsistencyPolicy(probability=1)
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub(consistency_policy=self.policy)
        self.testbed.init_memcache_stub()
        self.testbed.setup_env(
            user_email='example@example.com',
            user_id='1234567890',
            user_is_admin='1',
            overwrite=True)
        self.app = app.test_client()
        ndb.get_context().clear_cache()
        new_team = Team(team_name='hoge', billing_plan='trial',
                        team_domain='ysk')
        new_team_key = new_team.put()
        self.team_key = new_team_key
        new_team = new_team_key.get()
        new_team_key_id = new_team_key.id()
        self.team_id = new_team_key_id
        user_key_name = "{}_{}".format(new_team_key_id, users.get_current_user().user_id())
        logging.info(user_key_name)
        new_team_user = User(id=user_key_name, user_name='hoge', team=new_team.key, role='primary_owner',
                             user=users.get_current_user())
        new_team_user_key = new_team_user.put()
        self.user_key = new_team_user_key
        self.user_id = user_key_name

    def tearDown(self):
        self.testbed.deactivate()

    def testGet(self):
        ShortURL(id='jmpt.me_01', long_url='https://github.com', short_url='jmpt.me/01',
                 team=self.team_key, created_by=self.user_key,
                 title='test title', description='test description',
                 site_name='test site', image='').put()
        ShortURL(id='jmpt.me_02', long_url='https://github.com', short_url='jmpt.me/02',
                 team=self.team_key, created_by=self.user_key,
                 title='test title', description='test description',
                 site_name='test site', image='').put()
        bad_response = self.app.get('/api/v1/short_urls',
                                    follow_redirects=False)
        self.assertEqual(bad_response.status_code, 401)
        self.assertEqual(json.loads(bad_response.data)['errors'], ['bad request, should have team session data'])
        self.app.set_cookie('localhost', 'team', str(self.team_id))
        response = self.app.get('/api/v1/short_urls',
                                follow_redirects=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data)['results'][0]['short_url'], 'jmpt.me/01')
