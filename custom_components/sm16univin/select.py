"""V3 input configuration using the shared select platform."""

from SMcommonHA.config_support import async_setup_entities
from SMcommonHA.const import CONF_CHAN, CONF_NAME, CONF_STACK, CONF_TYPE
from SMcommonHA.select import Select

from . import CARD


class InputTypeSelect(Select):
    """Make input-type configuration unavailable on pre-V3 cards."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._supported = self._get.__self__._card_rev_major >= 3
        self._attr_available = self._supported

    def update(self):
        if self._supported:
            super().update()

    def select_option(self, option):
        if not self._supported:
            raise ValueError("Input type configuration requires a V3 or newer card")
        super().select_option(option)


async def async_setup_entry(hass, entry, async_add_entities):
    def create(config):
        return InputTypeSelect(
            name=config[CONF_NAME], stack=config[CONF_STACK], type=config[CONF_TYPE],
            chan=config[CONF_CHAN], card=CARD,
        )

    await async_setup_entities(hass, entry, async_add_entities, "select", create, CARD)
