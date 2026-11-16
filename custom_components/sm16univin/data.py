FULL_NAME = "Sixteen Analog/Digital Inputs"
LINK = "https://sequentmicrosystems.com/products/sixteen-analog-digital-inputs-8-layer-stackable-hat-for-raspberry-pi"

import lib16univin
API = lib16univin.SM16univin
DOMAIN = "sm16univin"
NAME_PREFIX = "sm16ui"
SM_MAP = {
    "select": {
        "input_type": {
            "chan_no": 16,
            "optional": True,
            "com": {"get": "get_input_type", "set": "cfg_input_type"},
            "option_map": {
                "0-10 V": "0_10V",
                "1k thermistor": "r1k",
                "10k thermistor": "r10k",
                "4-20 mA": "4_20mA",
                "0-3.3 V": "0_3V3",
            },
        },
    },
    "binary_sensor": {
        "dig": {
                "chan_no": 16,
                "com": {
                    "get": "get_dig_in",
                },
        },
    },
    "button": {
        "dig_rst": {
                "chan_no": 16,
                "com": {
                    "set": "reset_dig_in_counter",
                },
        },
        "watchdog_reload": {
                "chan_no": 1, "optional": True, "com": {"set": "wdt_reload"},
        },
    },
    "datetime": {
        "rtc": {
                "chan_no": 1,
                "com": {
                    "get": "get_rtc",
                    "set": "set_rtc",
                },
        },
    },
    "switch": {
        "led": {
                "chan_no": 16,
                "optional": True,
                "com": {"get": "get_led", "set": "set_led"},
        },
        "dig_cnt_en": {
                "chan_no": 16,
                "com": {
                    "get": "get_dig_in_cnt_en",
                    "set": "set_dig_in_cnt_en",
                },
        },
    },
    "sensor":  {
        "watchdog_count": {
                "chan_no": 1, "optional": True, "com": {"get": "wdt_get_reset_count"},
        },
        "dig_cnt": {
                "chan_no": 16,
                "com": {
                    "get": "get_dig_in_counter",
                },
        },
        "u": {
                "chan_no": 16,
                "uom": "V",
                "com": {
                    "get": "get_u_in",
                },
        },
        "r1k": {
                "chan_no": 16,
                "uom": "Ohm",
                "com": {
                    "get": "get_r1k_in",
                },
        },
        "r10k": {
                "chan_no": 16,
                "uom": "Ohm",
                "com": {
                    "get": "get_r10k_in",
                },
        },
    },
    "number": {
        "watchdog_period": {
            "chan_no": 1, "optional": True, "uom": "s",
            "min_value": 1, "max_value": 65535, "step": 1,
            "com": {"get": "wdt_get_period", "set": "wdt_set_period"},
        },
        "watchdog_initial": {
            "chan_no": 1, "optional": True, "uom": "s",
            "min_value": 1, "max_value": 65535, "step": 1,
            "com": {"get": "wdt_get_init_period", "set": "wdt_set_init_period"},
        },
    },
}
