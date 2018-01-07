import os
import json
import logging

from user_agents import parse
from oauth2client.service_account import ServiceAccountCredentials
from bigquery import get_client, BIGQUERY_SCOPE
from google.appengine.api import app_identity

from models import Click

# change this
LOG_DATASET_NAME = 'jmptme'


def write_click_log(short_url_key, referrer, ip_address,
                    location_country, location_region, location_city, location_lat_long,
                    user_agent, get_parameters):
    user_agent_raw = str(user_agent)
    user_agent = parse(user_agent_raw)
    click = Click(short_url=short_url_key,
                  referrer=referrer,
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
    click.put()


def get_bq_client():
    app_id = app_identity.get_application_id()
    credential_file = os.path.join(os.path.dirname(__file__), 'credential.json')
    with open(credential_file, 'r') as dataFile:
        credential_dict = json.loads(dataFile.read())
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(credential_dict,
                                                                   scopes=BIGQUERY_SCOPE)
    client = get_client(project_id=app_id, credentials=credentials, readonly=False)
    return client


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


def create_click_log_table():
    table_name = 'click'
    schema = [
        {'name': 'short_url_id', 'type': 'STRING', 'mode': 'required'},
        {'name': 'referrer', 'type': 'STRING', 'mode': 'nullable'},
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
