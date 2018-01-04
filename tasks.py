from user_agents import parse
from models import Click


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
