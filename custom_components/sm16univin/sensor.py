"""Shared sensor platform for the card."""

import logging

from SMcommonHA.config_support import async_setup_entities
from SMcommonHA.const import CONF_CHAN, CONF_NAME, CONF_STACK, CONF_TYPE, CONF_UPDATE_INTERVAL
from SMcommonHA.sensor import Sensor

from . import CARD

_LOGGER = logging.getLogger(__name__)


class CardSensor(Sensor):
    """Report the configured electrical input's actual unit on V3 cards."""

    def update(self):
        if self._type != "u" or self._SM._card_rev_major < 3:
            super().update()
            return
        try:
            input_type = self._SM.get_input_type(self._chan)
        except (OSError, ValueError) as err:
            _LOGGER.error("Cannot read input type for channel %s: %s", self._chan, err)
            self._attr_native_value = None
            return
        if input_type in {"r1k", "r10k"}:
            self._attr_native_value = None
            return
        if input_type not in {"0_10V", "0_3V3", "4_20mA"}:
            _LOGGER.error("Invalid input type %r for channel %s", input_type, self._chan)
            self._attr_native_value = None
            return
        self._attr_native_unit_of_measurement = "mA" if input_type == "4_20mA" else "V"
        super().update()


async def async_setup_entry(hass, entry, async_add_entities):
    def create(config):
        return CardSensor(
            hass=hass, name=config[CONF_NAME], stack=config[CONF_STACK], type=config[CONF_TYPE],
            chan=config[CONF_CHAN], update_interval=config.get(CONF_UPDATE_INTERVAL, 30),
            card=CARD,
        )

    await async_setup_entities(hass, entry, async_add_entities, "sensor", create, CARD)
