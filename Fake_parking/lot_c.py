"""Run parking simulator for lot C."""

import argparse
import sys

from simulator_app import run_simulator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parking lot simulator for lot C")
    parser.add_argument("--host", default="127.0.0.1", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sys.exit(run_simulator("C", broker_host=args.host, broker_port=args.port))


if __name__ == "__main__":
    main()
