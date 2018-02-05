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
from flask import Flask, request
from google.appengine.api import users
from models import User
from tasks import create_dataset, create_click_log_data
from main import team_id_required

app = Flask(__name__)


@app.route('/_admin/createbq', methods=['GET'])
def create_bq():
    result = create_dataset()
    return result, 200


@app.route('/_admin/createtestdata', methods=['GET'])
def create_test_data():
    team_id = request.cookies.get('team', False)
    user_key_name = "{}_{}".format(team_id, users.get_current_user().user_id())
    user_entity = User.get_by_id(user_key_name)
    result = create_click_log_data(user_entity)
    return result, 200


# [END app]
