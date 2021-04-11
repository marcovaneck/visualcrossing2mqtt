import json
import logging
import time
from datetime import datetime, timedelta
from threading import Thread

import requests

from cfg_loader import retrieve_cfg
from mqtthandler import MqttHandler

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

apikey = retrieve_cfg('visualcrossing_apikey')
location = retrieve_cfg('visualcrossing_location')

fromweb = 1

name = retrieve_cfg(key='mqtt.name', optional=True)

mqtthost = retrieve_cfg(key='mqtt.host', default='127.0.0.1')
mqttport = int(retrieve_cfg(key='mqtt.port', default='1883'))

REFRESH_TIME = 60 * 60  # 1 hour

# Start MQTT handler
client = MqttHandler(host=mqtthost, port=mqttport, name=name)  # connect to broker


def from_url():
    url = f'https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{location}'
    headers = {'Content-type': 'application/json', 'User-agent': 'visualcrossing2mqtt'}
    params = {'key': apikey, 'unitGroup': 'metric', 'include': 'fcst,hours'}

    logging.debug(f'url: {url} headers:{headers} params:{params}')
    req = requests.get(url, params=params, headers=headers)
    logging.info('url:' + req.url + ' status:' + str(req.status_code))
    # logging.debug(req.text)
    return json.loads(req.text)


def from_file():
    with open('../visualcrossing.json') as json_file:
        return json.load(json_file)


def refresh():
    global client
    if fromweb:
        root = from_url()
    else:
        root = from_file()

    payload = dict()

    # day=root['days'][0]
    for day in root['days']:
        for hour in day['hours']:
            if hour['temp'] is None:
                continue

            date = datetime.utcfromtimestamp(hour['datetimeEpoch']).strftime('%Y-%m-%d %H:%M:%SZ')

            write = dict()
            # write['date'] = date
            write['temp'] = hour['temp']
            write['feelslike'] = hour['feelslike']
            write['humidity'] = hour['humidity']
            write['dew'] = hour['dew']
            write['precip'] = hour['precip']
            write['precipprob'] = hour['precipprob']
            write['snow'] = hour['snow']
            write['snowdepth'] = hour['snowdepth']
            write['windgust'] = hour['windgust']
            write['windspeed'] = hour['windspeed']
            write['winddir'] = hour['winddir']
            write['pressure'] = hour['pressure']
            write['visibility'] = hour['visibility']
            write['cloudcover'] = hour['cloudcover']
            write['solarradiation'] = hour['solarradiation']
            write['solarenergy'] = hour['solarenergy']
            write['moonphase'] = hour['moonphase']
            write['daytime'] = day['sunriseEpoch'] < hour['datetimeEpoch'] < day['sunsetEpoch']

            # # preciptype = hour['preciptype']
            # # conditions = hour['conditions']
            # # icon = hour['icon']
            # # stations = hour['stations']
            # # source = hour['source']

            if datetime.now() < datetime.utcfromtimestamp(hour['datetimeEpoch']):
                if 'future' in payload:
                    payload['future'].append(write)
                else:
                    payload['future'] = [write]
            else:
                payload = write

    # refresh-function

    client.publish_status_json(payload)
    # logging.debug(json.dumps(payload, indent=4, sort_keys=True))


client.register_refresh(func=refresh)

client.add_sensor('temp', 'C', 'temp')
client.add_sensor('feelslike', 'C', 'feelslike')
client.add_sensor('humidity', 'pct', 'humidity')
client.add_sensor('dew', 'C', 'dew')
client.add_sensor('precip', 'pct', 'precip')
client.add_sensor('precipprob', 'pct', 'precipprob')
client.add_sensor('snow', 'pct', 'snow')
client.add_sensor('snowdepth', 'pct', 'snowdepth')
client.add_sensor('windgust', 'm/s', 'windgust')
client.add_sensor('windspeed', 'm/s', 'windspeed')
client.add_sensor('winddir', 'degree', 'winddir')
client.add_sensor('pressure', 'mbar', 'pressure')
client.add_sensor('visibility', 'pct', 'visibility')
client.add_sensor('cloudcover', 'pct', 'cloudcover')
client.add_sensor('solarradiation', 'W/m2', 'solarradiation')
client.add_sensor('solarenergy', 'kWh', 'solarenergy')
client.add_sensor('moonphase', 'pct', 'moonphase')
client.add_binary_sensor('daytime', 'daytime')


def auto_refresh():
    while True:
        call_started = datetime.now().timestamp()
        refresh()
        dt = datetime.now()
        seconds = (dt.replace(tzinfo=None) - dt.min).seconds
        rounding = (seconds + REFRESH_TIME)
        nh = (dt + timedelta(0, rounding - seconds, -dt.microsecond)).timestamp()
        time.sleep(nh - call_started)


def start():
    logging.info('Starting auto-refresh thread')
    refresh_thread = Thread(target=auto_refresh, daemon=True)
    refresh_thread.start()

    client.loop_forever()

    logging.info('Ended')
