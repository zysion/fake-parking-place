"""Run a local MQTT broker on laptop.

Dependencies:
- amqtt

Usage:
    python MQTT_broker.py
"""

import asyncio
from amqtt.broker import Broker
import paho.mqtt.client as mqtt


BROKER_CONFIG = {
    "listeners": {
        "default": {
            "type": "tcp",
            "bind": "0.0.0.0:1883",
        }
    },
    "sys_interval": 10,
    "auth": {
        "allow-anonymous": True,
        "password-file": None,
    },
}


def create_payload_logger(host: str = "127.0.0.1", port: int = 1883) -> mqtt.Client:
    """Create a local MQTT subscriber that prints all incoming payloads."""

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            client.subscribe("#")
            print("Payload monitor subscribed to topic: #")
        else:
            print(f"Payload monitor connection failed with code {rc}")

    def on_message(client, userdata, msg):
        payload_text = msg.payload.decode("utf-8", errors="replace")
        print(f"[RECV] topic={msg.topic} payload={payload_text}")

    logger_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="broker-payload-monitor")
    logger_client.on_connect = on_connect
    logger_client.on_message = on_message
    logger_client.connect_async(host, port, keepalive=60)
    logger_client.loop_start()
    return logger_client


async def run_broker() -> None:
    broker = Broker(BROKER_CONFIG)
    await broker.start()
    payload_logger = create_payload_logger(host="127.0.0.1", port=1883)
    print("MQTT broker is running on 0.0.0.0:1883")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        payload_logger.loop_stop()
        payload_logger.disconnect()
        await broker.shutdown()
        print("MQTT broker stopped.")


def main() -> None:
    try:
        asyncio.run(run_broker())
    except KeyboardInterrupt:
        print("Stopping broker...")


if __name__ == "__main__":
    main()
