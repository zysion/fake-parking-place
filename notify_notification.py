"""Small PySide6 GUI for publishing VALID/INVALID to notification topics."""

from __future__ import annotations

import sys
import uuid

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import paho.mqtt.client as mqtt


class NotificationPublisherWindow(QMainWindow):
    def __init__(self, broker_host: str = "127.0.0.1", broker_port: int = 1883) -> None:
        super().__init__()
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.mqtt_client: mqtt.Client | None = None

        self.setWindowTitle("Notification Publisher")
        self.resize(420, 220)

        self._build_ui()
        self._init_mqtt()

    def _build_ui(self) -> None:
        root = QWidget(self)
        root_layout = QVBoxLayout(root)

        group = QGroupBox("Send Notification")
        layout = QGridLayout(group)

        self.lot_combo = QComboBox()
        self.lot_combo.addItems(["A", "B", "C"])

        self.status_label = QLabel("Ready to publish notification messages.")
        self.status_label.setAlignment(Qt.AlignCenter)

        self.valid_button = QPushButton("VALID")
        self.invalid_button = QPushButton("INVALID")
        self.valid_button.clicked.connect(lambda: self.publish_notification("VALID"))
        self.invalid_button.clicked.connect(lambda: self.publish_notification("INVALID"))

        layout.addWidget(QLabel("Target lot"), 0, 0)
        layout.addWidget(self.lot_combo, 0, 1)
        layout.addWidget(self.valid_button, 1, 0)
        layout.addWidget(self.invalid_button, 1, 1)

        root_layout.addWidget(group)
        root_layout.addWidget(self.status_label)

        self.setCentralWidget(root)

    def _init_mqtt(self) -> None:
        client_id = f"notification-publisher-{uuid.uuid4().hex[:8]}"
        try:
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=client_id)
        except Exception:
            self.mqtt_client = mqtt.Client(client_id=client_id)

        self.mqtt_client.connect(self.broker_host, self.broker_port, keepalive=60)
        self.mqtt_client.loop_start()

    def publish_notification(self, value: str) -> None:
        if not self.mqtt_client:
            self.status_label.setText("MQTT client is not ready.")
            return

        lot = self.lot_combo.currentText().strip()
        topic = f"notification/{lot}"
        info = self.mqtt_client.publish(topic, value)

        if info.rc == mqtt.MQTT_ERR_SUCCESS:
            self.status_label.setText(f"Published {value} to {topic}")
        else:
            self.status_label.setText(f"Publish failed on {topic} (code={info.rc})")

    def closeEvent(self, event) -> None:
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    window = NotificationPublisherWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
