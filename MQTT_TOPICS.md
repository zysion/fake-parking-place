# MQTT Topics Overview

This document lists the MQTT topics used by the parking simulator and describes the purpose of each topic.

## Topics

### Publish topics

- `MEMBER`
  - Carries member scan events for check-in and check-out actions.
  - Payload fields: `member_id`, `role`, `status`, `lot`, `timestamp`.

- `GUEST`
  - Carries guest scan events for check-in and check-out actions.
  - Payload fields: `guest_id`, `status`, `lot`, `timestamp`.

- `parking-A-sensor`
  - Reports the state of parking slots in lot A.
  - Payload fields: `slot`, `status` (`occupied` or `empty`), `lot`, `timestamp`.

- `parking-B-sensor`
  - Reports the state of parking slots in lot B.
  - Payload fields: `slot`, `status` (`occupied` or `empty`), `lot`, `timestamp`.

- `parking-C-sensor`
  - Reports the state of parking slots in lot C.
  - Payload fields: `slot`, `status` (`occupied` or `empty`), `lot`, `timestamp`.

### Subscribe topics

- `notification/A`
  - Sends validation feedback for parking lot A.
  - The UI displays `VALID` or `INVALID` for a short time and then hides the message.

- `notification/B`
  - Sends validation feedback for parking lot B.
  - The UI displays `VALID` or `INVALID` for a short time and then hides the message.

- `notification/C`
  - Sends validation feedback for parking lot C.
  - The UI displays `VALID` or `INVALID` for a short time and then hides the message.

## Payload Notes

Suggested JSON payload structure:

- `MEMBER`:

```json
{
  "type": "member_scan",
  "lot": "A",
  "member_id": "M001",
  "role": "student",
  "status": "checkin",
  "timestamp": "2026-04-26T10:00:00Z"
}
```

- `GUEST`:

```json
{
  "type": "guest_scan",
  "lot": "A",
  "guest_id": "GUEST-001",
  "status": "checkout",
  "timestamp": "2026-04-26T10:00:00Z"
}
```

- `parking-<lot>-sensor`:

```json
{
  "type": "parking_sensor",
  "lot": "A",
  "slot": "A-13",
  "status": "occupied",
  "timestamp": "2026-04-26T10:00:00Z"
}
```

## Notes

- Each parking lot has its own notification topic.
- The simulator uses the broker running in `MQTT_broker.py`.
- The UI publishes scan and parking state data, while it subscribes to notification topics.
