"""Shared PySide6 parking lot simulator UI and MQTT integration."""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from functools import partial

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import paho.mqtt.client as mqtt


PREDEFINED_GUEST_IDS = [f"GUEST-{i:03d}" for i in range(1, 11)]


class MqttEventBridge(QObject):
    """Bridge MQTT callback thread to Qt UI thread."""

    notification_received = Signal(str)
    status_message = Signal(str, int)


class ParkingSimulatorWindow(QMainWindow):
    def __init__(self, lot_name: str, broker_host: str = "127.0.0.1", broker_port: int = 1883) -> None:
        super().__init__()
        self.lot_name = lot_name
        self.broker_host = broker_host
        self.broker_port = broker_port

        self.notification_topic = f"notification/{self.lot_name}"
        self.parking_topic = f"parking-{self.lot_name}-sensor"

        self.slot_states: dict[str, bool] = {}
        self.slot_buttons: dict[str, QPushButton] = {}
        self._is_closing = False

        self.mqtt_bridge = MqttEventBridge()
        self.mqtt_bridge.notification_received.connect(self.show_notification)
        self.mqtt_bridge.status_message.connect(self._show_status_message)

        self.mqtt_client: mqtt.Client | None = None
        self.notification_hide_timer = QTimer(self)
        self.notification_hide_timer.setSingleShot(True)

        self.setWindowTitle(f"Parking Lot Simulator - {self.lot_name}")
        self.resize(1200, 760)

        self._build_ui()
        self.notification_hide_timer.timeout.connect(self.notification_label.hide)
        self._init_mqtt()

    def _build_ui(self) -> None:
        root = QWidget(self)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        sidebar = self._build_sidebar()
        parking_panel = self._build_parking_panel()

        sidebar.setFixedWidth(380)
        root_layout.addWidget(sidebar)
        root_layout.addWidget(parking_panel, 1)

        self.setCentralWidget(root)

    def _build_sidebar(self) -> QWidget:
        panel = QWidget(self)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setSpacing(12)

        scan_group = QGroupBox("Scan System")
        scan_layout = QVBoxLayout(scan_group)
        scan_layout.setSpacing(10)

        member_group = QGroupBox("Member")
        member_layout = QGridLayout(member_group)
        self.member_id_input = QLineEdit()
        self.member_id_input.setPlaceholderText("Member ID")
        self.member_role_combo = QComboBox()
        self.member_role_combo.addItems(["student", "teacher"])

        self.member_in_button = QPushButton("Member In")
        self.member_out_button = QPushButton("Member Out")
        self.member_in_button.clicked.connect(partial(self.handle_member_action, "checkin"))
        self.member_out_button.clicked.connect(partial(self.handle_member_action, "checkout"))

        member_layout.addWidget(QLabel("Member ID"), 0, 0)
        member_layout.addWidget(self.member_id_input, 0, 1)
        member_layout.addWidget(QLabel("Role"), 1, 0)
        member_layout.addWidget(self.member_role_combo, 1, 1)
        member_layout.addWidget(self.member_in_button, 2, 0)
        member_layout.addWidget(self.member_out_button, 2, 1)

        guest_group = QGroupBox("Guest")
        guest_layout = QGridLayout(guest_group)
        self.guest_id_input = QLineEdit()
        self.guest_id_input.setPlaceholderText("Guest Card ID")
        self.guest_id_dropdown = QComboBox()
        self.guest_id_dropdown.addItems(PREDEFINED_GUEST_IDS)

        self.guest_in_button = QPushButton("Guest In")
        self.guest_out_button = QPushButton("Guest Out")
        self.guest_in_button.clicked.connect(partial(self.handle_guest_action, "checkin"))
        self.guest_out_button.clicked.connect(partial(self.handle_guest_action, "checkout"))

        guest_layout.addWidget(QLabel("Guest ID"), 0, 0)
        guest_layout.addWidget(self.guest_id_input, 0, 1)
        guest_layout.addWidget(QLabel("Quick Select"), 1, 0)
        guest_layout.addWidget(self.guest_id_dropdown, 1, 1)
        guest_layout.addWidget(self.guest_in_button, 2, 0)
        guest_layout.addWidget(self.guest_out_button, 2, 1)

        notification_group = QGroupBox("Notification")
        notification_layout = QVBoxLayout(notification_group)
        self.notification_label = QLabel("")
        self.notification_label.setAlignment(Qt.AlignCenter)
        self.notification_label.setMinimumHeight(42)
        self.notification_label.hide()
        notification_layout.addWidget(self.notification_label)

        scan_layout.addWidget(member_group)
        scan_layout.addWidget(guest_group)
        scan_layout.addWidget(notification_group)

        panel_layout.addWidget(scan_group)
        panel_layout.addStretch()
        return panel

    def _build_parking_panel(self) -> QWidget:
        parking_group = QGroupBox(f"Parking Place - Lot {self.lot_name}")
        layout = QVBoxLayout(parking_group)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        rows = 10
        cols = 5
        for row in range(rows):
            for col in range(cols):
                slot_number = row * cols + col + 1
                slot_name = f"{self.lot_name}-{slot_number}"

                button = QPushButton(slot_name)
                button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                button.setMinimumSize(88, 44)
                button.clicked.connect(partial(self.handle_slot_click, slot_name))

                self.slot_states[slot_name] = False
                self.slot_buttons[slot_name] = button
                self._update_slot_color(slot_name)
                grid.addWidget(button, row, col)

        layout.addLayout(grid)
        return parking_group

    def _init_mqtt(self) -> None:
        client_id = f"sim-{self.lot_name.lower()}-{uuid.uuid4().hex[:8]}"
        try:
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=client_id)
        except Exception:
            self.mqtt_client = mqtt.Client(client_id=client_id)

        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message

        self.mqtt_client.connect_async(self.broker_host, self.broker_port, keepalive=60)
        self.mqtt_client.loop_start()

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        if self._is_closing:
            return

        if rc == 0:
            client.subscribe(self.notification_topic)
            self.mqtt_bridge.status_message.emit(
                f"Connected to MQTT: {self.broker_host}:{self.broker_port} | Subscribed: {self.notification_topic}",
                5000,
            )
        else:
            self.mqtt_bridge.status_message.emit(f"MQTT connection failed with code {rc}", 5000)

    def _on_mqtt_message(self, client, userdata, msg):
        if self._is_closing:
            return

        if msg.topic != self.notification_topic:
            return

        value = msg.payload.decode("utf-8", errors="ignore").strip().upper()
        if value in {"VALID", "INVALID"}:
            self.mqtt_bridge.notification_received.emit(value)

    def show_notification(self, value: str) -> None:
        if self._is_closing:
            return

        if value == "VALID":
            style = "background-color: #2e7d32; color: white; border-radius: 4px; padding: 8px;"
        else:
            style = "background-color: #c62828; color: white; border-radius: 4px; padding: 8px;"

        self.notification_label.setText(value)
        self.notification_label.setStyleSheet(style)
        self.notification_label.show()
        self.notification_hide_timer.start(1000)

    def _show_status_message(self, message: str, timeout_ms: int = 3000) -> None:
        if self._is_closing:
            return
        self.statusBar().showMessage(message, timeout_ms)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _publish(self, topic: str, payload: dict) -> None:
        if not self.mqtt_client:
            self.statusBar().showMessage("MQTT client is not ready.", 3000)
            return

        message = json.dumps(payload)
        info = self.mqtt_client.publish(topic, message)
        if info.rc == mqtt.MQTT_ERR_SUCCESS:
            self.statusBar().showMessage(f"Published to {topic}: {message}", 3000)
        else:
            self.statusBar().showMessage(f"Publish failed on {topic} (code={info.rc})", 5000)

    def handle_member_action(self, status: str) -> None:
        member_id = self.member_id_input.text().strip()
        role = self.member_role_combo.currentText().strip()

        if not member_id:
            QMessageBox.warning(self, "Missing input", "Please enter member ID.")
            return

        payload = {
            "type": "member_scan",
            "lot": self.lot_name,
            "member_id": member_id,
            "role": role,
            "status": status,
            "timestamp": self._now(),
        }
        self._publish("MEMBER", payload)

    def handle_guest_action(self, status: str) -> None:
        guest_id = self.guest_id_input.text().strip() or self.guest_id_dropdown.currentText().strip()
        if not guest_id:
            QMessageBox.warning(self, "Missing input", "Please enter guest ID.")
            return

        payload = {
            "type": "guest_scan",
            "lot": self.lot_name,
            "guest_id": guest_id,
            "status": status,
            "timestamp": self._now(),
        }
        self._publish("GUEST", payload)

    def handle_slot_click(self, slot_name: str) -> None:
        is_occupied = self.slot_states[slot_name]
        action = "vehicle exit" if is_occupied else "vehicle entry"

        reply = QMessageBox.question(
            self,
            "Confirm slot update",
            f"Confirm selecting slot {slot_name} for {action}?",
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if reply != QMessageBox.Yes:
            return

        self.slot_states[slot_name] = not is_occupied
        self._update_slot_color(slot_name)

        status = "occupied" if self.slot_states[slot_name] else "empty"
        payload = {
            "type": "parking_sensor",
            "lot": self.lot_name,
            "slot": slot_name,
            "status": status,
            "timestamp": self._now(),
        }
        self._publish(self.parking_topic, payload)

    def _update_slot_color(self, slot_name: str) -> None:
        is_occupied = self.slot_states[slot_name]
        color = "#d32f2f" if is_occupied else "#2e7d32"
        self.slot_buttons[slot_name].setStyleSheet(
            f"QPushButton {{ background-color: {color}; color: white; font-weight: 600; border-radius: 6px; padding: 8px; }}"
        )

    def closeEvent(self, event):
        self._is_closing = True
        self.notification_hide_timer.stop()

        if self.mqtt_client:
            self.mqtt_client.on_connect = None
            self.mqtt_client.on_message = None
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        super().closeEvent(event)


def run_simulator(lot_name: str, broker_host: str, broker_port: int) -> int:
    app = QApplication(sys.argv)
    window = ParkingSimulatorWindow(lot_name=lot_name, broker_host=broker_host, broker_port=broker_port)
    window.show()
    return app.exec()
