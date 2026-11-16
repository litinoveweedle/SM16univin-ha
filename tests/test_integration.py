"""Card setup and published driver contract tests without hardware."""

import importlib
import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry, entity_registry
from homeassistant.loader import async_clear_custom_components_cache
from homeassistant.setup import async_setup_component

from custom_components.sm16univin.data import API, SM_MAP

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "sm16univin"
LEGACY_DOMAIN = "SM16univin"


@pytest.fixture
def hass_config_dir(tmp_path):
    custom = tmp_path / "custom_components"
    custom.mkdir()
    (custom / DOMAIN).symlink_to(ROOT / "custom_components" / DOMAIN)
    return str(tmp_path)


@pytest.fixture
def hardware(hass, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT))
    monkeypatch.setattr("time.sleep", lambda _: None)
    async_clear_custom_components_cache(hass)
    integration = importlib.import_module(f"custom_components.{DOMAIN}")
    methods = {}

    def getter_one(_stack):
        return 0

    def getter_channel(_stack, _channel):
        return 0

    def getter_rtc(_stack):
        return (2026, 1, 1, 0, 0, 0)

    def setter_one(_stack, _value):
        pass

    def setter_channel(_stack, _channel, _value):
        pass

    def setter_rtc(_stack, _year, _month, _day, _hour, _minute, _second):
        pass

    def button_no_channel(_stack):
        pass

    for platform, types in SM_MAP.items():
        for metadata in types.values():
            for operation, name in metadata["com"].items():
                if name == "__NOGET__":
                    continue
                count = len(inspect.signature(getattr(API, name)).parameters)
                if platform == "datetime":
                    method = getter_rtc if operation == "get" else setter_rtc
                elif platform == "button":
                    method = button_no_channel if count == 1 else setter_one
                elif operation == "get":
                    method = getter_one if count == 1 else getter_channel
                else:
                    method = setter_one if count == 2 else setter_channel
                methods[name] = method

    if inspect.isclass(API):
        class FakeCard:
            def __init__(self, stack):
                self.stack = stack
                self._card_rev_major = 2

        for name, method in methods.items():
            setattr(FakeCard, name, method)
        fake = FakeCard
    else:
        fake = SimpleNamespace(**methods)
    monkeypatch.setattr(integration.CARD, "api", fake)
    return integration


def first_entity():
    for platform, types in SM_MAP.items():
        for kind, metadata in types.items():
            if not metadata.get("optional"):
                return platform, kind, f"{kind}_1"
    raise AssertionError("No default entity")


async def test_yaml_migration_and_configuration(hass, hardware):
    platform, kind, key = first_entity()
    registry = entity_registry.async_get(hass)
    unique_id = f"{platform}.{DOMAIN}0_{kind}_1"
    old = registry.async_get_or_create(
        platform, LEGACY_DOMAIN, unique_id, suggested_object_id="existing_card_entity"
    )
    registry.async_update_entity(old.entity_id, name="Custom name")
    assert await async_setup_component(hass, DOMAIN, {DOMAIN: [{"stack": "0", key: None}]})
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.state is config_entries.ConfigEntryState.LOADED
    migrated = registry.async_get(old.entity_id)
    assert migrated.platform == DOMAIN
    assert migrated.unique_id == unique_id
    assert migrated.config_entry_id == entry.entry_id
    assert migrated.name == "Custom name"
    assert migrated.device_id is not None
    assert key in entry.data["entities"]
    assert hass.states.get(old.entity_id) is not None

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"entities": [key]}
    )
    if platform in ("sensor", "binary_sensor", "datetime"):
        assert result["step_id"] == "intervals"
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {key: 5.0}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert registry.async_get(old.entity_id).config_entry_id == entry.entry_id


async def test_import_preserves_suffixed_legacy_unique_id(hass, hardware):
    platform, kind, key = first_entity()
    registry = entity_registry.async_get(hass)
    base = f"{platform}.{DOMAIN}0_{kind}_1"
    old = registry.async_get_or_create(
        platform, LEGACY_DOMAIN, base + "_2",
        original_name=f"{hardware.CARD.name_prefix}0_{key}",
    )
    registry.async_update_entity(
        old.entity_id, disabled_by=entity_registry.RegistryEntryDisabler.USER
    )
    assert await async_setup_component(hass, DOMAIN, {DOMAIN: [{"stack": "0", key: None}]})
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    restored = registry.async_get(old.entity_id)
    assert restored.unique_id == base + "_2"
    assert restored.platform == DOMAIN
    assert restored.config_entry_id == entry.entry_id
    assert restored.disabled_by == entity_registry.RegistryEntryDisabler.USER
    assert registry.async_get_entity_id(platform, DOMAIN, base) is None


async def test_ui_setup_duplicate_and_unload(hass, hardware):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"stack": 1})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.state is config_entries.ConfigEntryState.LOADED
    devices = device_registry.async_entries_for_config_entry(
        device_registry.async_get(hass), entry.entry_id
    )
    assert len(devices) == 1
    platform, kind, _ = first_entity()
    registry = entity_registry.async_get(hass)
    entity_id = registry.async_get_entity_id(platform, DOMAIN, f"{platform}.{DOMAIN}1_{kind}_1")
    assert entity_id is not None
    for entity_platform, types in SM_MAP.items():
        for entity_type, metadata in types.items():
            if metadata.get("optional"):
                continue
            for channel in range(1, metadata["chan_no"] + 1):
                unique_id = f"{entity_platform}.{DOMAIN}1_{entity_type}_{channel}"
                registered_id = registry.async_get_entity_id(entity_platform, DOMAIN, unique_id)
                assert registered_id is not None, unique_id
                assert registry.async_get(registered_id).config_entry_id == entry.entry_id
    duplicate = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    duplicate = await hass.config_entries.flow.async_configure(
        duplicate["flow_id"], {"stack": 1}
    )
    assert duplicate["reason"] == "already_configured"
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert await hass.config_entries.async_setup(entry.entry_id)
    assert registry.async_get_entity_id(platform, DOMAIN, f"{platform}.{DOMAIN}1_{kind}_1") == entity_id


async def test_reset_button_calls_the_selected_channel(hass, hardware):
    calls = []

    class FakeCard:
        def __init__(self, stack):
            self.stack = stack

        def reset_dig_in_counter(self, channel):
            calls.append((self.stack, channel))

    hardware.CARD.api = FakeCard
    assert await async_setup_component(hass, DOMAIN, {DOMAIN: [{"stack": "2", "dig_rst_3": None}]})
    await hass.async_block_till_done()
    registry = entity_registry.async_get(hass)
    entity_id = registry.async_get_entity_id("button", DOMAIN, "button.sm16univin2_dig_rst_3")
    assert entity_id is not None
    await hass.services.async_call("button", "press", {"entity_id": entity_id}, blocking=True)
    assert calls == [(2, 3)]


async def test_input_type_updates_real_sensor_state_and_units(hass, hardware):
    class FakeCard:
        _card_rev_major = 3
        input_type = "0_10V"

        def __init__(self, _stack):
            pass

        def get_input_type(self, _channel):
            return self.input_type

        def cfg_input_type(self, _channel, value):
            type(self).input_type = value

        def get_u_in(self, _channel):
            return 12.5

    hardware.CARD.api = FakeCard
    assert await async_setup_component(hass, "homeassistant", {})
    assert await async_setup_component(
        hass, DOMAIN, {DOMAIN: [{"stack": "0", "input_type_2": None, "u_2": None}]}
    )
    await hass.async_block_till_done()
    registry = entity_registry.async_get(hass)
    select_id = registry.async_get_entity_id("select", DOMAIN, "select.sm16univin0_input_type_2")
    sensor_id = registry.async_get_entity_id("sensor", DOMAIN, "sensor.sm16univin0_u_2")
    assert select_id and sensor_id

    for option, expected in [("4-20 mA", "mA"), ("0-3.3 V", "V")]:
        await hass.services.async_call(
            "select", "select_option", {"entity_id": select_id, "option": option}, blocking=True
        )
        await hass.services.async_call(
            "homeassistant", "update_entity", {"entity_id": sensor_id}, blocking=True
        )
        state = hass.states.get(sensor_id)
        assert state.state == "12.5"
        assert state.attributes["unit_of_measurement"] == expected

    await hass.services.async_call(
        "select", "select_option", {"entity_id": select_id, "option": "1k thermistor"}, blocking=True
    )
    await hass.services.async_call(
        "homeassistant", "update_entity", {"entity_id": sensor_id}, blocking=True
    )
    assert hass.states.get(sensor_id).state == "unknown"


@pytest.mark.parametrize(
    ("platform", "kind", "operation", "method"),
    [
        (platform, kind, operation, method)
        for platform, types in SM_MAP.items()
        for kind, metadata in types.items()
        for operation, method in metadata["com"].items()
        if method != "__NOGET__"
    ],
)
def test_real_driver_contract(platform, kind, operation, method):
    function = getattr(API, method)
    assert callable(function), f"{platform}.{kind}: {method} is not callable"
    signature = inspect.signature(function)
    count = len(signature.parameters)
    if platform == "datetime":
        args = [0] if operation == "get" else [0, 2026, 1, 1, 0, 0, 0]
    elif platform == "button":
        assert count in (1, 2)
        args = [0] if count == 1 else [0, 1]
    elif operation == "get":
        assert count in (1, 2)
        args = [0] if count == 1 else [0, 1]
    else:
        assert count in (2, 3)
        args = [0, 1] if count == 2 else [0, 1, 1]
    signature.bind(*args)
