"""
Support for MQTT thermostats.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/thermostat.mqtt/
"""
import logging

import homeassistant.components.mqtt as mqtt
from homeassistant.components.thermostat import (
    ATTR_MIN_TEMP, ATTR_MAX_TEMP, ThermostatDevice)
from homeassistant.const import CONF_VALUE_TEMPLATE, STATE_UNKNOWN, TEMP_CELCIUS
from homeassistant.helpers.entity import Entity
from homeassistant.helpers import template
from homeassistant.helpers.event import track_state_change

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "MQTT Thermostat"
DEFAULT_QOS = 0
DEFAULT_PAYLOAD_ON = 'ON'
DEFAULT_PAYLOAD_OFF = 'OFF'
DEFAULT_RETAIN = False

DEPENDENCIES = ['mqtt']


def setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """Setup the MQTT thermostat."""
    if config.get('target_temperature_topic') is None:
        _LOGGER.error("Missing required variable: target_temperature_topic")
        return False

    if config.get('state_topic') is None:
        _LOGGER.error("Missing required variable: state_topic")
        return False

    if config.get('temperature_sensor') is None:
        _LOGGER.error("Missing required variable: temperature_sensor")
        return False

    add_devices_callback([MqttThermostat(
        hass,
        config.get('name', DEFAULT_NAME),
        config.get('state_topic'),
        config.get('target_temperature_topic'),
        config.get('temperature_sensor'),
        config.get('command_topic'),
        config.get('payload_on', DEFAULT_PAYLOAD_ON),
        config.get('payload_off', DEFAULT_PAYLOAD_OFF),
        config.get('fan_payload_on', DEFAULT_PAYLOAD_ON),
        config.get('fan_payload_off', DEFAULT_PAYLOAD_OFF),
        config.get(ATTR_MIN_TEMP),
        config.get(ATTR_MAX_TEMP),
        config.get('qos', DEFAULT_QOS),
        config.get('retain', DEFAULT_RETAIN),
        config.get('unit_of_measurement'),
        config.get(CONF_VALUE_TEMPLATE))])


class MqttThermostat(ThermostatDevice):
    """Representation of an MQTT thermostat."""

    def __init__(self, hass, name, state_topic, target_temperature_topic, temperature_sensor, command_topic,
                 payload_on, payload_off, fan_payload_on, fan_payload_off,
                 min_temp, max_temp,
                 qos, retain, unit_of_measurement, value_template):
        """Initialize the thermostat."""
        self._hass = hass
        self._name = name
        self._state_topic = state_topic
        self._target_temperature_topic = target_temperature_topic
        self._temperature_sensor = temperature_sensor
        self._command_topic = command_topic
        self._payload_on = payload_on
        self._payload_off = payload_off
        self._fan_payload_on = fan_payload_on
        self._fan_payload_off = fan_payload_off
        self._min_temp = min_temp
        self._max_temp = max_temp
        self._qos = qos
        self._retain = retain
        self._unit_of_measurement = unit_of_measurement
        self._value_template = value_template

        self._state = STATE_UNKNOWN
        self._target_temperature = None
        try:
            self._temperature = float(self._hass.states.get(self._temperature_sensor).state)
        except:
            self._temperature = None

        def state_received(topic, payload, qos):
            """A new MQTT message has been received."""
            if payload == self._payload_on:
                self._state = True
                self.update_ha_state()
            elif payload == self._payload_off:
                self._state = False
                self.update_ha_state()

        mqtt.subscribe(self._hass, self._state_topic, state_received, self._qos)

        def target_temperature_received(topic, payload, qos):
            """A new MQTT message has been received."""
            self._target_temperature = float(payload)
            self.update_ha_state()

        mqtt.subscribe(self._hass, self._target_temperature_topic, target_temperature_received, self._qos)

        def temperature_changed(entity_id, old_state, new_state):
            """The temperature changed."""
            self._temperature = float(new_state.state)
            self.update_ha_state()

        track_state_change(self._hass, self._temperature_sensor, temperature_changed)

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def name(self):
        """Return the name of the thermostat."""
        return self._name

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return self._min_temp

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return self._max_temp

    @property
    def state(self):
        """Return the state of the entity."""
        return self._state

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    def set_temperature(self, temperature):
        """Set new target temperature."""

        if self._value_template is not None:
            temperature = template.render_with_possible_json_value(self._hass, self._value_template, str(temperature))

        mqtt.publish(self._hass, self._command_topic, temperature,
                     self._qos, self._retain)

    @property
    def is_fan_on(self):
        """Return true if the fan is on."""
        return self._state

    def turn_fan_on(self):
        """Turn fan on."""
        if self._value_template is not None:
            payload = template.render_with_possible_json_value(self._hass, self._value_template, str(self._temperature))

        mqtt.publish(self._hass, self._command_topic, payload,
                     self._qos, self._retain)

    def turn_fan_off(self):
        """Turn fan off."""
        mqtt.publish(self._hass, self._command_topic, self._fan_payload_off,
                     self._qos, self._retain)
