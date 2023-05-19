import asyncio
import json
import time

from homeassistant import config_entries
from homeassistant.components import mqtt
from homeassistant.helpers import entity_registry as er
from homeassistant.util.json import json_loads_object

from .const import (
    _LOGGER,
    BUY_ORDER_CREATED_TYPE,
    COMMAND_TOPIC,
    CONF_STATUS_UPDATE_FREQUENCY,
    CONF_STRATEGY_NAME_HELPER,
    DEFAULT_STATUS_UPDATE_INTERVAL,
    INSTANCE_TIMEOUT_SECONDS,
    ORDER_CREATED_TYPES,
    ORDER_TYPES,
    TYPE_ENTITY_ACTIVE_ORDERS,
    TYPE_ENTITY_STRATEGY_IMPORTED,
    TYPE_ENTITY_STRATEGY_RUNNING,
    TYPE_ENTITY_STRATEGY_STATUS,
)


class HbotBalanceItem:
    def __init__(self):
        self._base = 0
        self._quote = 0

    @property
    def base(self):
        return self._base

    @base.setter
    def base(self, value):
        try:
            self._base = float(value)
        except Exception:
            pass

    @property
    def quote(self):
        return self._quote

    @quote.setter
    def quote(self, value):
        try:
            self._quote = float(value)
        except Exception:
            pass

    @property
    def data_dict(self):
        return {
            "base": self.base,
            "quote": self.quote,
        }


class HbotBalances:
    def __init__(self):
        self._total = HbotBalanceItem()
        self._available = HbotBalanceItem()

    @property
    def total(self):
        return self._total

    @property
    def available(self):
        return self._available

    @property
    def data_dict(self):
        return {
            "total": self.total.data_dict,
            "available": self.available.data_dict,
        }


class HbotMarketPrices:
    def __init__(self):
        self._bid = 0
        self._ask = 0
        self._mid = 0

    @property
    def bid(self):
        return self._bid

    @bid.setter
    def bid(self, value):
        try:
            self._bid = float(value)
        except Exception:
            pass

    @property
    def ask(self):
        return self._ask

    @ask.setter
    def ask(self, value):
        try:
            self._ask = float(value)
        except Exception:
            pass

    @property
    def mid(self):
        return self._mid

    @mid.setter
    def mid(self, value):
        try:
            self._mid = float(value)
        except Exception:
            pass

    @property
    def data_dict(self):
        return {
            "bid": self.bid,
            "ask": self.ask,
            "mid": self.mid,
        }


class HbotInstance:
    def __init__(self, manager, instance_id, hass):
        self._manager = manager
        self._hass = hass
        self._instance_id = instance_id
        self._last_imported_strategy = None
        self._all_entities = dict()
        self._entities_binary_sensor = list()
        self._entities_button = list()
        self._entities_sensor = list()
        self._order_tracker = dict()
        self._binary_sensor_data = dict()
        self._button_data = dict()
        self._base_asset = None
        self._quote_asset = None
        self._balances = HbotBalances()
        self._market_prices = HbotMarketPrices()
        self._last_status_update_interval = 0
        self._cmd_topic_import = COMMAND_TOPIC.format(self._instance_id, "import")
        self._cmd_topic_status = COMMAND_TOPIC.format(self._instance_id, "status")
        self._strategy_is_imported = None
        self._strategy_is_running = None
        self._ent_registry = er.async_get(self._hass)
        self._is_available = None
        self._last_event_received = None
        self._health_check_task = None

    @property
    def status_update_frequency(self):
        return self._manager.status_update_frequency

    @property
    def ent_registry(self):
        return self._ent_registry

    @property
    def should_update_status(self):
        time_now = int(time.time())
        should_update = (
            (time_now - self.status_update_frequency > self._last_status_update_interval) or
            ((time_now - 5 > self._last_status_update_interval) and
             self._market_prices.mid == 0)
        )
        if should_update:
            self._last_status_update_interval = time_now

        return should_update

    @property
    def balances(self):
        return self._balances

    @property
    def market_prices(self):
        return self._market_prices

    @property
    def strategy_name_helper(self):
        return self._manager.strategy_name_helper

    @property
    def instance_id(self):
        return self._instance_id

    def unload(self):
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()

    def async_update_last_received(self):
        self._last_event_received = int(time.time())
        self._async_start_health_check_task()

    async def _async_health_check(self):
        while True:
            await asyncio.sleep(10)

            if not self._last_event_received or int(time.time()) - INSTANCE_TIMEOUT_SECONDS > self._last_event_received:
                self.update_strategy_running_state(False)
                self.set_unavailable()
                break

    def _async_start_health_check_task(self):
        if self._health_check_task is None or self._health_check_task.done():
            self._health_check_task = self._hass.async_create_task(
                self._async_health_check()
            )

    def get_cmd_payload(self, reply_endpoint="hass_replies", data=dict()):
        return json.dumps({
            "timestamp": int(time.time() * 1e3),
            "header": {
                "reply_to": COMMAND_TOPIC.format(self._instance_id, reply_endpoint)
            },
            "data": data,
        })

    def set_last_imported_strategy(self, strategy_name):
        self._last_imported_strategy = strategy_name

    def publish_mqtt(self, topic, payload):
        mqtt.publish(self._hass, topic, payload, 0)

    def send_status_command(self):
        self.publish_mqtt(self._cmd_topic_status, self.get_cmd_payload())

    def send_import_command(self, strategy_name):
        self.set_last_imported_strategy(strategy_name)
        data_dict = {"strategy": strategy_name}
        self.publish_mqtt(self._cmd_topic_import, self.get_cmd_payload("hass_replies_import", data_dict))

    def check_status_command(self):
        if self._strategy_is_running and self.should_update_status:
            self.send_status_command()

    def reset_strategy_status(self, with_balances=True):
        self._balances = HbotBalances()
        self._market_prices = HbotMarketPrices()
        self.update_status_sensor_data()

    def reset_order_tracker(self):
        self._order_tracker = dict()
        self.update_active_order_sensor_data()

    def reset_instance_on_stop(self):
        _LOGGER.debug("Received stop, resetting.")
        self.reset_strategy_status(False)

    def reset_instance_on_start(self):
        _LOGGER.debug("Received start, resetting.")
        self.reset_strategy_status()
        self.reset_order_tracker()
        self.update_strategy_imported_state(True)

    def reset_instance_on_connected(self):
        _LOGGER.debug("Received connected, resetting.")
        self.reset_strategy_status()
        self.reset_order_tracker()
        self.update_strategy_imported_state(False)

    def update_active_order_sensor_data(self):
        entity = self.get_sensor(TYPE_ENTITY_ACTIVE_ORDERS)

        if entity is None:
            return

        if not entity.check_ready():
            return

        entity_update_data = {
            "_state": len(self._order_tracker),
            "orders": self.get_orders_data(),
        }
        entity.set_event(entity_update_data)

    def update_status_sensor_data(self):
        entity = self.get_sensor(TYPE_ENTITY_STRATEGY_STATUS)

        if entity is None:
            return

        if not entity.check_ready():
            return

        entity_update_data = {
            "_state": f"{self._base_asset}-{self._quote_asset}",
            "asset_base": self._base_asset,
            "asset_quote": self._quote_asset,
            "balances": self.balances.data_dict,
            "market_prices": self.market_prices.data_dict,
            "strategy_name_helper": self.strategy_name_helper,
            "instance_id": self._instance_id,
            "last_imported_strategy": self._last_imported_strategy,
        }

        entity.set_event(entity_update_data)

    def get_sensor(self, sensor_type):
        return self._all_entities.get(sensor_type)

    def add_sensor(self, ent):
        self._all_entities[ent._hbot_entity_type] = ent
        self._entities_sensor.append(ent._hbot_entity_type)

    def get_binary_sensor(self, sensor_type):
        return self._all_entities.get(sensor_type)

    def add_binary_sensor(self, ent):
        self._all_entities[ent._hbot_entity_type] = ent
        self._entities_binary_sensor.append(ent._hbot_entity_type)

    def get_button(self, sensor_type):
        return self._all_entities.get(sensor_type)

    def add_button(self, ent):
        self._all_entities[ent._hbot_entity_type] = ent
        self._entities_button.append(ent._hbot_entity_type)

    def set_available(self):
        if not self._is_available:
            self.reset_instance_on_connected()

        self._is_available = True

        for i, s in self._all_entities.items():
            s.set_available()

    def set_unavailable(self):
        self._is_available = False

        for i, s in self._all_entities.items():
            s.set_unavailable()

    def get_orders_data(self):
        orders_list = dict()
        for oid, o in self._order_tracker.items():
            orders_list[oid] = {
                "t": o["type"].split(".")[1],
                "tp": o["trading_pair"],
                "a": o["amount"],
                "p": o["price"],
                "s": o["order_side"],
                "ts": o["creation_timestamp"],
            }
        return orders_list

    def update_strategy_running_state(self, new_state):
        entity = self.get_binary_sensor(TYPE_ENTITY_STRATEGY_RUNNING)

        if entity is None:
            return

        if not entity.check_ready():
            return

        if self._strategy_is_running == new_state:
            return

        self._strategy_is_running = new_state

        if not new_state:
            self.reset_instance_on_stop()

        else:
            self.reset_instance_on_start()

        entity.set_event({"_state": self._strategy_is_running})

    def update_strategy_imported_state(self, new_state):
        entity = self.get_binary_sensor(TYPE_ENTITY_STRATEGY_IMPORTED)

        if entity is None:
            return

        if not entity.check_ready():
            return

        if self._strategy_is_imported == new_state:
            return

        self._strategy_is_imported = new_state

        entity.set_event({"_state": self._strategy_is_imported})

    def update_data(self, endpoint, payload):
        if not isinstance(payload, dict):
            _LOGGER.warning(f"Unknown data received: {type(payload)} - {payload}.")
            return

        # _LOGGER.debug("Updating Data.")
        if endpoint == "events":
            if payload.get("type") in ORDER_TYPES:
                known_orders = self._order_tracker.keys()
                order_type = payload.get("type")
                order_id = payload["data"]["order_id"]
                if order_type in ORDER_CREATED_TYPES and order_id not in known_orders:
                    order_side = "buy" if order_type == BUY_ORDER_CREATED_TYPE else "sell"
                    self._order_tracker[order_id] = {
                        **payload["data"],
                        "order_side": order_side
                    }
                elif order_type not in ORDER_CREATED_TYPES and order_id in known_orders:
                    del self._order_tracker[order_id]

                self.update_active_order_sensor_data()
                self.update_strategy_imported_state(True)
                self.update_strategy_running_state(True)

        elif endpoint == "notify":
            if 'strategy started' in payload.get("msg", ""):
                self.update_strategy_running_state(True)

            elif '\\nWinding down...' == payload.get("msg", ""):
                self.update_strategy_running_state(False)

            elif 'file is imported.' in payload.get("msg", ""):
                msg_parts = payload.get("msg", "").split("Configuration from ")
                strategy_name = msg_parts[1].split(" file is")[0].split(".yml")[0] if len(msg_parts) >= 2 else ""
                self._last_imported_strategy = strategy_name
                self.update_strategy_imported_state(True)

            elif 'Strategy import error' in payload.get("msg", ""):
                self.update_strategy_imported_state(False)

            elif 'Total Balance' in payload.get("msg", ""):
                status_lines = [line.strip().split() for line in payload.get("msg", "").split("\n") if len(line)]
                for i, cols in enumerate(status_lines):

                    if cols[0] == "Assets:":
                        self._base_asset = status_lines[i + 1][0]
                        self._quote_asset = status_lines[i + 1][1]

                    if len(cols) < 2:
                        continue

                    if cols[0] == "Total":
                        self.balances.total.base = cols[2]
                        self.balances.total.quote = cols[3]

                    elif cols[0] == "Available":
                        self.balances.available.base = cols[2]
                        self.balances.available.quote = cols[3]

                    elif cols[0] == "Exchange" and self._strategy_is_running:
                        cols = status_lines[i + 1]
                        self.market_prices.bid = cols[2]
                        self.market_prices.ask = cols[3]
                        self.market_prices.mid = cols[4]

        elif endpoint == "log":
            if 'start command initiated.' == payload.get("msg", ""):
                self.update_strategy_running_state(True)
            elif 'stop command initiated.' == payload.get("msg", ""):
                self.update_strategy_running_state(False)

        elif endpoint == "hass_replies":
            if str(payload.get("data", {}).get("msg")) == "No strategy is currently running!":
                self.update_strategy_running_state(False)

        elif endpoint == "hass_replies_import":
            if str(payload.get("data", {}).get("status")) == "200":
                self.update_strategy_imported_state(True)
            elif str(payload.get("data", {}).get("status")) == "400" or "No such file or directory" in payload.get("data", ""):
                self.update_strategy_imported_state(False)

        self.update_status_sensor_data()

    def check_availability(self, endpoint, payload):
        if endpoint in ["hb", "status_updates"]:

            if endpoint == "status_updates" and payload.get("type") == "availability":
                if payload.get("msg") == "online":
                    self.set_available()
                else:
                    self.set_unavailable()

                return False

            else:
                if payload.get("ts") is not None:
                    self.set_available()
                else:
                    self.set_unavailable()

                return False

        return True


class HbotManager:
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()

        return cls._instance

    @classmethod
    def unload(cls):
        if cls._instance:
            cls._instance.unload_instances()
            cls._instance = None
        _LOGGER.debug("Hummingbot unloaded")

    def __init__(self):
        self._instances = dict()
        self._config_entry = config_entries.current_entry.get()
        self._entity_endpoints = [
            "hb",
            "hass_replies",
            "hass_replies_import",
            "notify",
            "events",
            "log",
        ]
        self._services_registered = False
        self._status_update_frequency = DEFAULT_STATUS_UPDATE_INTERVAL
        self._strategy_name_helper = None

    @property
    def status_update_frequency(self):
        return self._status_update_frequency

    @property
    def should_register_services(self):
        if self._services_registered:
            return False

        self._services_registered = True

        return True

    @property
    def strategy_name_helper(self):
        return self._strategy_name_helper

    def unload_instances(self):
        for _id, instance in self._instances.items():
            instance.unload()

    def extract_instance_id_endpoint(self, topic):
        topic_split = topic.split("/")

        if len(topic_split) >= 3:
            return topic_split[1], topic_split[-1]

        return None

    def send_import_command(self, hass, instance_id, strategy_name):
        hbot_instance = self.get_hbot_instance(hass, instance_id)
        hbot_instance.send_import_command(strategy_name)

    def get_hbot_instance(self, hass, instance_id):
        if instance_id not in self._instances.keys():
            self._instances[instance_id] = HbotInstance(self, instance_id, hass)

        return self._instances[instance_id]

    def get_hbot_instance_and_endpoint(self, hass, topic):

        instance_id, endpoint = self.extract_instance_id_endpoint(topic)

        if instance_id is None:
            return None, None

        hbot_instance = self.get_hbot_instance(hass, instance_id)
        hbot_instance.async_update_last_received()

        return hbot_instance, endpoint

    def endpoint_loads_entities(self, endpoint):
        return endpoint in self._entity_endpoints

    def extract_event_payload(self, hbot_instance, endpoint, payload):
        event = json_loads_object(payload)

        hbot_instance.check_availability(endpoint, event)

        hbot_instance.check_status_command()

        if not self.endpoint_loads_entities(endpoint):
            return None

        return event

    def update_with_config_entry(self):
        _LOGGER.debug(f"Received config update: {self._config_entry.data} {self._config_entry.options}")

        if CONF_STATUS_UPDATE_FREQUENCY in self._config_entry.options:
            self.set_status_update_frequency(self._config_entry.options[CONF_STATUS_UPDATE_FREQUENCY])

        if CONF_STRATEGY_NAME_HELPER in self._config_entry.options:
            self.set_strategy_name_helper(self._config_entry.options[CONF_STRATEGY_NAME_HELPER])

    def set_strategy_name_helper(self, strategy_name_helper):
        self._strategy_name_helper = strategy_name_helper

    def set_status_update_frequency(self, value):
        if value is None:
            return

        if self._status_update_frequency == value:
            return

        try:
            self._status_update_frequency = int(value)
        except Exception:
            _LOGGER.warning(f"Invalid status update frequency: {value}")
