import os
import json
import logging
import uuid
import random
import datetime

from user_agents import parse
from oauth2client.service_account import ServiceAccountCredentials
from bigquery import get_client, BIGQUERY_SCOPE
from google.appengine.api import app_identity
from google.appengine.ext import deferred
import sendgrid
from referer_parser import Referer

from models import Click, User, Invitation, Team, ShortURL

# change this
LOG_DATASET_NAME = 'jmptme'


def get_bq_client():
    app_id = app_identity.get_application_id()
    credential_file = os.path.join(os.path.dirname(__file__), 'credential.json')
    with open(credential_file, 'r') as dataFile:
        credential_dict = json.loads(dataFile.read())
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(credential_dict,
                                                                   scopes=BIGQUERY_SCOPE)
    client = get_client(project_id=app_id, credentials=credentials, readonly=False)
    return client


def write_click_log(short_url_key, referrer, ip_address,
                    location_country, location_region, location_city, location_lat_long,
                    user_agent, get_parameters):
    user_agent_raw = str(user_agent)
    user_agent = parse(user_agent_raw)
    try:
        referrer_parsed = Referer(referrer)
        referrer_name = referrer_parsed.referer
        referrer_medium = referrer_parsed.medium
    except AttributeError:
        referrer_name = None
        referrer_medium = None
    click = Click(short_url=short_url_key,
                  referrer=referrer,
                  referrer_name=referrer_name,
                  referrer_medium=referrer_medium,
                  ip_address=ip_address,
                  location_country=location_country,
                  location_region=location_region,
                  location_city=location_city,
                  location_lat_long=location_lat_long,
                  user_agent_raw=user_agent_raw,
                  user_agent_device=user_agent.device.family,
                  user_agent_device_brand=user_agent.device.brand,
                  user_agent_device_model=user_agent.device.model,
                  user_agent_os=user_agent.os.family,
                  user_agent_os_version=user_agent.os.version_string,
                  user_agent_browser=user_agent.browser.family,
                  user_agent_browser_version=user_agent.browser.version_string,
                  custom_code=get_parameters.get('c'))
    result = click.put()
    deferred.defer(write_click_log_to_bq, result.id())


def create_dataset():
    client = get_bq_client()
    if client.check_dataset(LOG_DATASET_NAME) is False:
        dataset = client.create_dataset(LOG_DATASET_NAME, friendly_name="jmpt.me url shortner click log",
                                        description="")
        if dataset:
            success_message = 'dataset successfully created: {}'.format(LOG_DATASET_NAME)
            logging.info(success_message)
            return success_message
    else:
        already_message = '"{}" dataset already exists'.format(LOG_DATASET_NAME)
        logging.info(already_message)
        return already_message


def create_click_log_table(table_name):
    """
    create table with YYYYMMDD suffix
    -> https://qiita.com/sinmetal/items/63207fe9d74547f986e0#_reference-2f7da1581b396526e6df
    """
    schema = [
        {'name': 'id', 'type': 'INTEGER', 'mode': 'required'},
        {'name': 'short_url_id', 'type': 'STRING', 'mode': 'required'},
        {'name': 'referrer', 'type': 'STRING', 'mode': 'nullable'},
        {'name': 'referrer_name', 'type': 'STRING', 'mode': 'nullable'},
        {'name': 'referrer_medium', 'type': 'STRING', 'mode': 'nullable'},
        {'name': 'ip_address', 'type': 'STRING', 'mode': 'nullable'},
        {'name': 'location_country', 'type': 'STRING', 'mode': 'nullable'},
        {'name': 'location_region', 'type': 'STRING', 'mode': 'nullable'},
        {'name': 'location_city', 'type': 'STRING', 'mode': 'nullable'},
        {'name': 'location_lat_long', 'type': 'STRING', 'mode': 'nullable'},
        {'name': 'user_agent_raw', 'type': 'STRING', 'mode': 'nullable'},
        {'name': 'user_agent_device', 'type': 'STRING', 'mode': 'nullable'},
        {'name': 'user_agent_device_brand', 'type': 'STRING', 'mode': 'nullable'},
        {'name': 'user_agent_device_model', 'type': 'STRING', 'mode': 'nullable'},
        {'name': 'user_agent_os', 'type': 'STRING', 'mode': 'nullable'},
        {'name': 'user_agent_os_version', 'type': 'STRING', 'mode': 'nullable'},
        {'name': 'user_agent_browser', 'type': 'STRING', 'mode': 'nullable'},
        {'name': 'user_agent_browser_version', 'type': 'STRING', 'mode': 'nullable'},
        {'name': 'custom_code', 'type': 'STRING', 'mode': 'nullable'},
    ]
    client = get_bq_client()
    if client.check_table(LOG_DATASET_NAME, table_name) is False:
        click_table = client.create_table(LOG_DATASET_NAME, table_name, schema)
        if click_table:
            success_message = 'table successfully created: {}'.format(table_name)
            logging.info(success_message)
            return success_message
    else:
        already_message = '"{}" table already exists'.format(table_name)
        logging.info(already_message)
        return already_message


def write_click_log_to_bq(click_key_id):
    click = Click.get_by_id(click_key_id)
    table_name = 'click{}'.format(click.created_at.strftime('%Y%m%d'))
    client = get_bq_client()
    if client.check_table(LOG_DATASET_NAME, table_name) is False:
        create_click_log_table(table_name)
    rows = [{
        'id': click.key.id(),
        'short_url_id': click.short_url.id(),
        'referrer': click.referrer,
        'referrer_name': click.referrer_name,
        'referrer_medium': click.referrer_medium,
        'ip_address': click.ip_address,
        'location_country': click.location_country,
        'location_region': click.location_region,
        'location_city': click.location_city,
        'location_lat_long': click.location_lat_long,
        'user_agent_raw': click.user_agent_raw,
        'user_agent_device': click.user_agent_device,
        'user_agent_device_brand': click.user_agent_device_brand,
        'user_agent_device_model': click.user_agent_device_model,
        'user_agent_os': click.user_agent_os,
        'user_agent_os_version': click.user_agent_os_version,
        'user_agent_browser': click.user_agent_browser,
        'user_agent_browser_version': click.user_agent_browser_version,
        'custom_code': click.custom_code,
    }]
    client.push_rows(LOG_DATASET_NAME, table_name, rows, 'id')
    logging.info('bq insertion done')


def send_invitation(email, team_id, user_id, host):
    user_key_name = "{}_{}".format(team_id, user_id)
    user_entity = User.get_by_id(user_key_name)
    team = Team.get_by_id(int(team_id))
    key_name = uuid.uuid4().hex
    Invitation(id=key_name, sent_to=email, team=team.key, created_by=user_entity.key).put()
    invitation_link = "https://{}/page/invitation/{}".format(host, key_name)
    config_file = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_file, 'r') as configFile:
        config_dict = json.loads(configFile.read())
    sg = sendgrid.SendGridAPIClient(apikey=config_dict['sendgrid_api_key'])
    payload = {
        "personalizations": [
            {
                "to": [
                    {
                        "email": email
                    }
                ],
                "substitutions": {
                    "%team_name%": team.team_name,
                    "%invitation_link%": invitation_link
                },
                "subject": "jmpt.me invitation to {} team".format(team.team_name)
            }
        ],
        "from": {
            "email": config_dict['sendgrid_from_email'],
            "name": "jmpt.me invitation"
        },
        "template_id": config_dict['sendgrid_template_id']
    }
    try:
        response = sg.client.mail.send.post(request_body=payload)
    except Exception as e:
        logging.error(e.body)
        return False
    if response.status_code != 202:
        logging.error(response.body)
        return False
    else:
        return True


def create_click_log_data(team):
    q = ShortURL.query()
    q = q.filter(ShortURL.team == team).order(-ShortURL.created_at)
    short_url = q.fetch(1)[0]
    refferrers = [
        'https://www.google.co.jp/search',
        'https://twitter.com/',
        'https://www.facebook.com/',
    ]
    uas = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_3) AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/63.0.3239.132 Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 11_2_1 like Mac OS X) AppleWebKit/604.4.7 (KHTML, like Gecko) '
        'Version/11.0 Mobile/15C153 Safari/604.1',
    ]
    for i in range(200):
        user_agent_raw = random.choice(uas)
        user_agent = parse(user_agent_raw)
        referrer = random.choice(refferrers)
        referrer_parsed = Referer(referrer)
        click = Click(short_url=short_url.key,
                      referrer=referrer,
                      referrer_name=referrer_parsed.referer,
                      referrer_medium=referrer_parsed.medium,
                      ip_address='192.168.0.200',
                      location_country='JP',
                      location_region='13',
                      location_city='shinjuku',
                      location_lat_long='35.693840,139.703549',
                      user_agent_raw=user_agent_raw,
                      user_agent_device=user_agent.device.family,
                      user_agent_device_brand=user_agent.device.brand,
                      user_agent_device_model=user_agent.device.model,
                      user_agent_os=user_agent.os.family,
                      user_agent_os_version=user_agent.os.version_string,
                      user_agent_browser=user_agent.browser.family,
                      user_agent_browser_version=user_agent.browser.version_string,
                      custom_code=None,
                      created_at=datetime.datetime.now() + datetime.timedelta(days=random.randint(-90, 0)))
        click.put()
    return True
