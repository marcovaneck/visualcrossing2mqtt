import json
import logging
import sys

import paho.mqtt.client as mqtt


class mqtthandler(object):

    def __init__(self, host: str = 'localhost', port=1883, name=None):
        if name is None:
            self.name = str(sys.argv[0]).replace(".py", "").replace('./', '')
        else:
            self.name = name

        self.mqtt_client = mqtt.Client(client_id=self.name, protocol=5)

        self.connect_topic = self.compose_topic('connected')
        self.state_topic = self.compose_topic('state')

        self.mqtt_host = host
        self.mqtt_port = port
        self.mqtt_client.will_set(self.connect_topic, 0, 1, retain=True)

        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_disconnect = self.on_disconnect
        self.mqtt_client.on_message = self.on_message

        self.callbacks = dict()

        logging.info(f'Connecting to {self.mqtt_host}:{self.mqtt_port}')
        self.mqtt_client.connect(self.mqtt_host, self.mqtt_port)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.mqtt_client.disconnect()

    def on_connect(self, client, userdata, flags_dict, reason, properties):
        # print(f'Connected!, {userdata},{flags_dict}, {reason}, {properties}')
        self.mqtt_client.publish(self.connect_topic, 1, 1, retain=True)

    def compose_topic(self, spec_name):
        return f"{self.name}/{spec_name}"

    def on_disconnect(self):
        logging.info('DisConnected!')

    def publish(self, topic, payload=None):
        # print('publish!')
        if payload is None:
            self.mqtt_client.publish(topic)
        else:
            self.mqtt_client.publish(topic, f'{payload}')

    def publish_state(self, payload: dict):
        self.publish(self.state_topic, json.dumps(payload))

    def on_message(self, client, userdata, message):
        # print(f'on_message!  {userdata} {message.topic}')
        if message.topic in self.callbacks:
            self.callbacks[message.topic](topic=message.topic, payload=message.payload)

    def register_callback(self, topic, func):
        if topic in self.callbacks:
            raise Exception(f'{topic} is already defined')
        self.callbacks[topic] = func
        self.mqtt_client.subscribe(topic)

    def loop_forever(self):
        self.mqtt_client.loop_forever()

    def create_device(self):
        return {
            "model": 'Python',
            "name": self.name,
            "sw_version": "GIT_TAG"
        }

    def add_sensor(self, sensor_name: str, unit_of_measurement: str, value_name: str, change_topic: str = None):
        payload = {
            "device": self.create_device(),
            "name": sensor_name,
            "deviceName": self.name,
            "state_topic": self.state_topic,
            "unit_of_measurement": unit_of_measurement,
            "value_template": f'{{ value_json.{value_name} }}'
        }
        if change_topic is not None:
            payload['command_topic'] = self.compose_topic(change_topic)
        topic = f'homeassistant/sensor/{self.name}/{sensor_name}/config'
        self.mqtt_client.publish(topic, f'{json.dumps(payload)}', 1, retain=True)

    def add_binary_sensor(self, sensor_name: str, value_name: str, change_topic: str = None):
        payload = {
            "device": self.create_device(),
            "name": sensor_name,
            "deviceName": self.name,
            "state_topic": self.state_topic,
            "value_template": f'{{ value_json.{value_name} }}'
        }
        if change_topic is not None:
            payload['command_topic'] = self.compose_topic(change_topic)
        topic = f'homeassistant/binary_sensor/{self.name}/{sensor_name}/config'
        self.mqtt_client.publish(topic, f'{json.dumps(payload)}', 1, retain=True)
