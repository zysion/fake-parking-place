First, run the MQTT_broker.py file in the terminal: `python MQTT_broker.py`
Then, open another terminal to run fake_parking, which has 3 parking areas (A, B, C): (first, navigate to the Fake_parking directory) `python lot_a.py` (or `lot_b.py`; `lot_c.py`)

The Python script `notify_notification.py` simulates the web application sending back scan results.

Once the web application is complete, we can use this repository to check if we did everything correctly.

We are using the MQTT protocol, so the backend can receive data through the threads I listed and described in `MQTT_TOPICS.md`.
