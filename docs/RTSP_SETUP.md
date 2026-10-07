# RTSP Camera Setup

## Camera Configuration

RTSP credentials must never be stored in source_url, database records, logs, or Git.

Store only the RTSP source URL without credentials:

- ENTER: rtsp://192.168.1.59:554/Streaming/Channels/101
- EXIT: rtsp://192.168.1.90:554/Streaming/Channels/101

Use environment credential references:

- CAMERA_1_CREDENTIALS
- CAMERA_2_CREDENTIALS

## Environment

Required variables:

RTSP_OPEN_TIMEOUT_MS=5000
RTSP_RECONNECT_MAX_SECONDS=30

CAMERA_1_CREDENTIALS=username:password
CAMERA_2_CREDENTIALS=username:password

Never commit `.env`.

## Adding an RTSP Camera from the Dashboard

Sign in as ADMIN and open **SYSTEM → Cameras → Add Camera**:

1. Source type: **RTSP / CCTV**.
2. RTSP URL: the URL **without** username/password, e.g. `rtsp://192.168.1.10:554/Streaming/Channels/101`.
3. Credentials reference: the environment variable **name**, e.g. `CAMERA_1_CREDENTIALS` (its value `username:password` lives only in the server `.env`).
4. Use **Manage Camera → Test Connection** to verify.

The dashboard never asks for or displays camera passwords. A URL containing `user:pass@` is rejected before it is sent to the backend. OPERATOR users see a read-only camera list.

## Verification

### Unit tests

python -m pytest backend\tests\cameras\test_rtsp_source.py -v

### Live camera test

The project was live-tested against two RTSP cameras.

ENTER:
- connection successful
- 10-second stability test: 214 frames
- reconnect observed

EXIT:
- connection successful
- 10-second stability test: 255 frames
- reconnect observed

HEVC decoder warnings were observed during testing; streams continued successfully.

## Security

- Reject embedded credentials in RTSP URLs.
- Resolve credentials using credentials_ref.
- Build authenticated URLs only in memory.
- Mask authenticated URLs in logs.
- Do not commit `.env`.

## Troubleshooting

If RTSP cannot open:
- verify IP address and RTSP path
- verify credentials
- verify TCP connectivity
- verify camera firewall/network access

High latency:
- reduce camera resolution
- keep buffer size low
- drop stale frames