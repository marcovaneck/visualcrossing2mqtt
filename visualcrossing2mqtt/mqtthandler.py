import json
import logging
import sys
from collections.abc import Callable

import paho.mqtt.client as mqtt

log = logging.getLogger('MqttHandler')


# log.setLevel(logging.DEBUG)


class MqttHandler(object):

    def __init__(self, host: str = '127.0.0.1', port=1883, name: str = None):
        if name is None:
            self.name = str(sys.argv[0]).replace(".py", "").replace('./', '')
        else:
            self.name = name

        self.mqtt_client = mqtt.Client(client_id=self.name, protocol=5)

        self.connect_topic = self.compose_topic('connected')
        self.status_topic = self.compose_topic('status')

        self.mqtt_host = host
        self.mqtt_port = port
        self.mqtt_client.will_set(self.connect_topic, 0, 1, retain=True)

        self.mqtt_client.on_connect = self.__on_connect
        self.mqtt_client.on_disconnect = self.__on_disconnect
        self.mqtt_client.on_message = self.__on_message
        self.connected_state = 0

        self.refresh_function: Callable[[],] = None

        self.callbacks = dict()

        log.info(f'Connecting to {self.mqtt_host}:{self.mqtt_port}')
        self.mqtt_client.connect(self.mqtt_host, self.mqtt_port)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.mqtt_client.disconnect()

    def __on_connect(self, client, userdata, flags_dict, reason, properties):
        log.debug(f'Connected!, {userdata},{flags_dict}, {reason}, {properties}')

    def publish_connected(self, val: int):
        if self.connected_state != val:
            log.debug(f'Connected!, ({val})')
            self.publish(self.connect_topic, payload=val, retain=True)
            self.connected_state = val
        else:
            log.debug(f'Already!, {self.connected_state}->({val})')

    def __on_disconnect(self, client, userdata, reasonCode):
        log.debug(f'DisConnected! userdata:{userdata}, reasonCode:{reasonCode}')
        self.publish_connected(0)

    def compose_topic(self, spec_name: str):
        return f"{self.name}/{spec_name}"

    def publish(self, topic: str, payload=None, retain: bool = False):
        if payload is None:
            log.debug(f'Publish empty {topic}')
            res = self.mqtt_client.publish(topic, qos=1, retain=retain)
        else:
            log.debug(f'Publish {topic} with payload {payload}')
            res = self.mqtt_client.publish(topic, f'{payload}', qos=1, retain=retain)
        if res:
            log.debug(f'Publish result {res}')
        else:
            log.debug('No result Publish result')

    def __on_message(self, client, userdata, message):
        log.debug(f'on_message!  {userdata} {message.topic} {message}')
        if message.topic in self.callbacks:
            self.callbacks[message.topic](message.topic, str(message.payload, 'utf-8'))

    def register_callback(self, func: Callable[[str, str],], full_topic: str = None, partial_topic: str = None):
        if full_topic:
            __topic = full_topic
        elif partial_topic:
            __topic = self.compose_topic(partial_topic)
        else:
            raise RuntimeError('Please supply a full or a partial topic')

        if __topic in self.callbacks:
            raise Exception(f'{__topic} is already defined')

        self.callbacks[__topic] = func
        result, mid = self.mqtt_client.subscribe(__topic)
        log.debug(f'Subscribed {__topic} with result {result} and mid {mid}')

    def __static_refresh_function(self, topic: str, payload: str):
        if self.refresh_function is not None:
            self.refresh_function()

    def register_refresh(self, func: Callable[[],]):
        self.refresh_function = func
        self.register_callback(partial_topic=self.compose_topic('get'), func=self.__static_refresh_function)

    def loop_forever(self):
        try:
            self.mqtt_client.loop_forever()
        except KeyboardInterrupt:
            log.info('Exit requested')

    def publish_error(self, error_message: str):
        topic = self.compose_topic('error')
        self.publish(topic, f'{error_message}', retain=False)

    def publish_status_json(self, payload: dict):
        self.publish(self.status_topic, f'{json.dumps(payload)}', retain=True)

    def publish_status_raw(self, payload):
        self.publish(self.status_topic, f'{payload}', retain=True)

    def __create_device(self):
        return {
            "model": 'Python',
            "name": self.name,
            "sw_version": "GIT_TAG"
        }

    def add_sensor(self, sensor_name: str, unit_of_measurement: str, value_name: str, change_topic: str = None):
        payload = {
            "device": self.__create_device(),
            "name": sensor_name,
            "deviceName": self.name,
            "state_topic": self.status_topic,
            "unit_of_measurement": unit_of_measurement,
            "value_template": f'{{ value_json.{value_name} }}'
        }
        if change_topic is not None:
            payload['command_topic'] = self.compose_topic(change_topic)
        topic = f'homeassistant/sensor/{self.name}/{sensor_name}/config'
        self.publish(topic, f'{json.dumps(payload)}', retain=True)

    def add_binary_sensor(self, sensor_name: str, value_name: str, change_topic: str = None):
        payload = {
            "device": self.__create_device(),
            "name": sensor_name,
            "deviceName": self.name,
            "state_topic": self.status_topic,
            "value_template": f'{{ value_json.{value_name} }}'
        }
        if change_topic is not None:
            payload['command_topic'] = self.compose_topic(change_topic)
        topic = f'homeassistant/binary_sensor/{self.name}/{sensor_name}/config'
        self.publish(topic, f'{json.dumps(payload)}', retain=True)
