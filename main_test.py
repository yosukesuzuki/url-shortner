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

import logging
import unittest
from urlparse import urlparse

from google.appengine.api import users
from google.appengine.datastore import datastore_stub_util
from google.appengine.ext import ndb
from google.appengine.ext import testbed
from main import app
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
        response = self.app.get('/register')
        self.assertEqual(response.status_code, 200)

    def testRegisterPost(self):
        response = self.app.post('/register',
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

    def tearDown(self):
        self.testbed.deactivate()

    def testShortenPost(self):
        new_team = Team(team_name='hoge', billing_plan='trial',
                        team_domain='ysk')
        new_team_key = new_team.put()
        new_team = new_team_key.get()
        new_team_key_id = new_team_key.id()
        user_key_name = "{}_{}".format(new_team_key_id, users.get_current_user().user_id())
        logging.info(user_key_name)
        new_team_user = User(id=user_key_name, user_name='hoge', team=new_team.key, role='primary_owner',
                             user=users.get_current_user())
        new_team_user.put()
        self.app.set_cookie('localhost', 'team', '1')
        response = self.app.post('/shorten',
                                 data={'url': 'http://github.com', 'domain': 'jmpt.me'},
                                 follow_redirects=False)
        self.assertEqual(response.status_code, 200)
        short_urls = ShortURL.query().fetch(1000)
        self.assertEqual(short_urls[0].long_url, 'http://github.com')
