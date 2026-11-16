"""Verify revision-gated input configuration against the published driver."""

import pytest

import lib16univin
from SMcommonHA import Card
from custom_components.sm16univin.data import SM_MAP
from custom_components.sm16univin.select import InputTypeSelect
from custom_components.sm16univin.sensor import CardSensor


class FakeBus:
    def __init__(self, _bus):
        self.values = {lib16univin.I2C_MEM.REVISION_HW_MAJOR_ADD: 3}
        self.writes = []

    def read_byte_data(self, _address, register):
        return self.values.get(register, 0)

    def write_byte_data(self, _address, register, value):
        self.writes.append((register, value))
        self.values[register] = value

    def read_word_data(self, _address, _register):
        return 12500


@pytest.fixture
def driver(monkeypatch):
    bus = FakeBus(1)
    monkeypatch.setattr(lib16univin, "SMBus", lambda _: bus)
    monkeypatch.setattr("time.sleep", lambda _: None)
    return bus, Card("test", "Test", "test", "Test", SM_MAP, lib16univin.SM16univin)


def test_v3_input_type_controls_and_sensor_units(hass, driver):
    bus, card = driver
    select = InputTypeSelect("type", 0, "input_type", 2, card)
    sensor = CardSensor(hass, "input", 0, "u", 2, 30, card)
    select.update()
    assert select.current_option == "0-10 V"
    select.select_option("4-20 mA")
    assert bus.writes[-1][1] == 0x30
    sensor.update()
    assert sensor.native_value == 12.5
    assert sensor.native_unit_of_measurement == "mA"
    select.select_option("0-3.3 V")
    sensor.update()
    assert sensor.native_unit_of_measurement == "V"
    select.select_option("1k thermistor")
    sensor.update()
    assert sensor.native_value is None


def test_old_card_never_reads_or_writes_input_type(driver):
    bus, card = driver
    bus.values[lib16univin.I2C_MEM.REVISION_HW_MAJOR_ADD] = 2
    select = InputTypeSelect("type", 0, "input_type", 1, card)
    assert not select.available
    select.update()
    with pytest.raises(ValueError, match="V3"):
        select.select_option("4-20 mA")
    assert not bus.writes
