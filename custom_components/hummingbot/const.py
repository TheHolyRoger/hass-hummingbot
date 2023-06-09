"""Constants for the Hummingbot integration."""
import logging

from homeassistant.const import Platform

_LOGGER = logging.getLogger(__name__)

DOMAIN = "hummingbot"

TOPIC = "hbot/#"
COMMAND_TOPIC = "hbot/{0}/{1}"

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SENSOR,
]

CONF_STATUS_UPDATE_FREQUENCY = "status_update_frequency"
CONF_STRATEGY_NAME_HELPER = "strategy_name_helper"

ATTR_INSTANCE_ID = "instance_id"
ATTR_STRATEGY_NAME = "strategy_name"

TYPE_ENTITY_ACTIVE_ORDERS = "Active Orders"
TYPE_ENTITY_STRATEGY_RUNNING = "Strategy Running"
TYPE_ENTITY_STRATEGY_IMPORTED = "Strategy Imported"
TYPE_ENTITY_STRATEGY_START = "Strategy Start"
TYPE_ENTITY_STRATEGY_STATUS = "Strategy Status"
TYPE_ENTITY_STRATEGY_GET_STATUS = "Strategy Get Status"
TYPE_ENTITY_STRATEGY_STOP = "Strategy Stop"
TYPE_ENTITY_STRATEGY_IMPORT = "Strategy Import"

TYPES_BINARY_SENSORS = [
    TYPE_ENTITY_STRATEGY_RUNNING,
    TYPE_ENTITY_STRATEGY_IMPORTED,
]

TYPES_BUTTONS = [
    TYPE_ENTITY_STRATEGY_START,
    TYPE_ENTITY_STRATEGY_GET_STATUS,
    TYPE_ENTITY_STRATEGY_STOP,
    TYPE_ENTITY_STRATEGY_IMPORT,
]

TYPES_SENSORS = [
    TYPE_ENTITY_ACTIVE_ORDERS,
    TYPE_ENTITY_STRATEGY_STATUS,
]

TOTAL_INSTANCE_ENTITIES = 8

DEFAULT_STATUS_UPDATE_INTERVAL = 10

BUY_ORDER_CREATED_TYPE = "BuyOrderCreated"
SELL_ORDER_CREATED_TYPE = "SellOrderCreated"

ORDER_CREATED_TYPES = [
    BUY_ORDER_CREATED_TYPE,
    SELL_ORDER_CREATED_TYPE,
]

ORDER_TYPES = [
    BUY_ORDER_CREATED_TYPE,
    SELL_ORDER_CREATED_TYPE,
    "OrderCancelled"
]

VALID_ENTITY_ENDPOINTS = [
    "hb",
    "hass_replies",
    "hass_replies_import",
    "notify",
    "events",
    "log",
]

INSTANCE_TIMEOUT_SECONDS = 120
