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

import unittest
from urlparse import urlparse

from google.appengine.datastore import datastore_stub_util
from google.appengine.ext import ndb
from google.appengine.ext import testbed
from main import app


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
        self.policy = datastore_stub_util.PseudoRandomHRConsistencyPolicy(probability=0)
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
