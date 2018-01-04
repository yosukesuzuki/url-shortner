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
from google.appengine.ext import deferred
from main import app
from mock import patch
from models import User, Team, ShortURL, Click


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
        response_strip = self.app.post('/api/v1/shorten',
                                       data=json.dumps(
                                           {'url': 'https://github.com/yosukesuzuki/url-shortner', 'domain': 'jmpt.me',
                                            'custom_path': 'jmptme1\n'}),
                                       content_type='application/json',
                                       follow_redirects=False)
        self.assertEqual(response_strip.status_code, 200)
        self.assertEqual(json.loads(response_strip.data)['short_url'], 'jmpt.me/jmptme1')
        response_detail = self.app.get('/page/detail/jmpt.me_jmptme1')
        self.assertEqual(response_detail.status_code, 200)

    @patch('opengraph.OpenGraph')
    def testPatch(self, OpenGraph):
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
        patch_response = self.app.patch('/api/v1/short_urls/jmpt.me/jmptme',
                                        data=json.dumps({'tag': 'testtag', 'memo': 'memo for test'}),
                                        content_type='application/json',
                                        follow_redirects=False)
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(json.loads(patch_response.data)['tags'], ['testtag'])
        self.assertEqual(json.loads(patch_response.data)['memo'], 'memo for test')
        bad_response = self.app.patch('/api/v1/short_urls/jmpt.me/jmptme',
                                      data=json.dumps({'tag': '', 'memo': ''}),
                                      content_type='application/json',
                                      follow_redirects=False)
        self.assertEqual(bad_response.status_code, 400)
        self.assertEqual(json.loads(bad_response.data)['errors'],
                         ['At least one of Tag and Memo must be set'])
        patch_response2 = self.app.patch('/api/v1/short_urls/jmpt.me/jmptme',
                                         data=json.dumps({'tag': 'testtag2'}),
                                         content_type='application/json',
                                         follow_redirects=False)
        self.assertEqual(json.loads(patch_response2.data)['tags'], ['testtag', 'testtag2'])
        tag_delete_response = self.app.delete('/api/v1/short_urls/jmpt.me/jmptme/tags/testtag2',
                                              content_type='application/json',
                                              follow_redirects=False)
        self.assertEqual(json.loads(tag_delete_response.data)['tags'], ['testtag'])

    @patch('opengraph.OpenGraph')
    def testDelete(self, OpenGraph):
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
        delete_response = self.app.delete('/api/v1/short_urls/jmpt.me/jmptme')
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(json.loads(delete_response.data)['success'], 'the url was deleted')


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
        self.assertEqual(json.loads(response.data)['results'][0]['short_url'], 'jmpt.me/02')

    def testCursor(self):
        for i in range(100, 0, -1):
            ShortURL(id='jmpt.me_{0:03d}'.format(i), long_url='https://github.com',
                     short_url='jmpt.me/{0:03d}'.format(i),
                     team=self.team_key, created_by=self.user_key,
                     title='test title', description='test description',
                     site_name='test site', image='').put()
        self.app.set_cookie('localhost', 'team', str(self.team_id))
        response = self.app.get('/api/v1/short_urls',
                                follow_redirects=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data)['results'][0]['short_url'], 'jmpt.me/001')
        self.assertEqual(len(json.loads(response.data)['results']), 10)
        self.assertEqual(json.loads(response.data)['more'], True)
        cursor = json.loads(response.data)['next_cursor']
        next_response = self.app.get('/api/v1/short_urls?cursor={}'.format(cursor),
                                     follow_redirects=False)
        self.assertEqual(json.loads(next_response.data)['results'][0]['short_url'], 'jmpt.me/011')


class RedirectLoggingTest(unittest.TestCase):
    def setUp(self):
        self.policy = datastore_stub_util.PseudoRandomHRConsistencyPolicy(probability=1)
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_taskqueue_stub(root_path='.')
        self.taskqueue_stub = self.testbed.get_stub(testbed.TASKQUEUE_SERVICE_NAME)
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
        response = self.app.get('/01',
                                follow_redirects=False,
                                headers={'Host': 'jmpt.me',
                                         'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 11_2_1 like Mac OS X) ' +
                                                       'AppleWebKit/604.4.7 (KHTML, like Gecko) ' +
                                                       'Version/11.0 Mobile/15C153 Safari/604.1',
                                         'X-AppEngine-Country': 'JP',
                                         'X-AppEngine-Region': '13',
                                         'X-AppEngine-City': 'shinjuku',
                                         'X-AppEngine-CityLatLong': '35.693840,139.703549'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, 'https://github.com')
        tasks = self.taskqueue_stub.get_filtered_tasks()
        self.assertEqual(1, len(tasks))
        task = tasks[0]
        deferred.run(task.payload)
        click_results = Click.query().fetch(1000)
        self.assertEquals(click_results[0].short_url.id(), 'jmpt.me_01')
        self.assertEquals(click_results[0].ip_address, '127.0.0.1')
        self.assertEquals(click_results[0].location_country, 'JP')
        self.assertEquals(click_results[0].location_region, '13')
        self.assertEquals(click_results[0].location_city, 'shinjuku')
        self.assertEquals(click_results[0].location_lat_long, '35.693840,139.703549')
        self.assertEquals(click_results[0].user_agent_device, 'iPhone')
        self.assertEquals(click_results[0].user_agent_device_brand, 'Apple')
        self.assertEquals(click_results[0].user_agent_device_model, 'iPhone')
        self.assertEquals(click_results[0].user_agent_os, 'iOS')
        self.assertEquals(click_results[0].user_agent_os_version, '11.2.1')
        self.assertEquals(click_results[0].user_agent_browser, 'Mobile Safari')
        self.assertEquals(click_results[0].user_agent_browser_version, '11')
