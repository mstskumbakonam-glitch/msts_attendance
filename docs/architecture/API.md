# REST API Specification & Endpoint Catalog

**Base Path:** `/api/v1`  
**Authentication Standard:** HTTP Bearer JSON Web Token (JWT)  
**Response Format:** JSON (except binary streams/exports)  
**Error Schema:** Uniform JSON error representation  
**Validation:** Pydantic v2 schemas  

---

## 1. Uniform Error Response Schema

All non-2xx API responses return a structured error body:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Student with ID STU001 was not found.",
    "request_id": "req-9a8b7c6d5e"
  }
}
```

### Standard HTTP Status Codes
- `200 OK`: Request succeeded.
- `201 Created`: Resource created successfully.
- `204 No Content`: Action executed successfully; no response body.
- `400 Bad Request`: Invalid request formatting or parameters.
- `401 Unauthorized`: Authentication token missing or invalid.
- `403 Forbidden`: Authenticated user lacks required role (`ADMIN` vs `OPERATOR`).
- `404 Not Found`: Target resource does not exist.
- `409 Conflict`: Business rule or unique constraint violation.
- `422 Unprocessable Entity`: Request body failed Pydantic validation.
- `429 Too Many Requests`: Rate limit exceeded.
- `500 Internal Server Error`: Generic internal error (stack traces hidden).

---

## 2. Authorization Legend

- `—`: Public endpoint (no token required).
- `AO`: Accessible by `ADMIN` or `OPERATOR` roles.
- `A`: Accessible strictly by `ADMIN` role.
- `ticket`: Accessible via short-lived camera stream ticket.

---

## 3. Endpoint Catalog

### 3.1 Health & Auth Endpoints

| Method | Path | Auth | Request Body | Success Response | Validation / Errors | DB Effect | Mandatory Test Name |
|---|---|---|---|---|---|---|---|
| GET | `/health` | — | — | `{status, version}` | — | None | `health_ok` |
| GET | `/health/db` | — | — | `{db:"ok", pgvector:"ok"}` | 503 if DB unreachable | `SELECT 1`, vector extension check | `health_db_ok`, `health_db_down` |
| POST | `/auth/login` | — | `{username, password}` | `{access_token, token_type, expires_in, user}` | 401 generic message; 429 after N attempts | Updates `last_login_at`; writes audit log | `login_ok`, `login_bad_pw`, `login_rate_limit` |
| POST | `/auth/logout` | AO | — | `204 No Content` | 401 | Inserts `jti` into `revoked_tokens` | `logout_revokes` |
| GET | `/auth/me` | AO | — | Profile object | 401 | None | `me_ok` |
| POST | `/stream/ticket` | AO | `{camera_id}` | `{ticket, expires_in}` | 404 camera | Memory/Redis ticket registration | `ticket_scope`, `ticket_expiry` |

### 3.2 Users & Settings Endpoints

| Method | Path | Auth | Request Body | Success Response | Validation / Errors | DB Effect | Mandatory Test Name |
|---|---|---|---|---|---|---|---|
| GET | `/users` | A | Query filters | Paged user list | — | None | `users_list_admin_only` |
| POST | `/users` | A | `{username, password, role}` | User object | Password policy ≥12 chars; 409 dup | Inserts `users` row + audit log | `users_create` |
| PATCH | `/users/{id}` | A | `{role?, is_active?}` | User object | Cannot demote/deactivate last admin | Updates `users` row + audit log | `users_last_admin` |
| GET | `/settings` | A | — | Settings object | — | Reads `system_settings` | `settings_read` |
| PUT | `/settings` | A | Thresholds & alert policy | Updated settings | Threshold range 0.2–0.9 | Upserts `system_settings` + audit log | `settings_validation` |

### 3.3 Students & Face Registration Endpoints

| Method | Path | Auth | Request Body | Success Response | Validation / Errors | DB Effect | Mandatory Test Name |
|---|---|---|---|---|---|---|---|
| POST | `/students` | A | `{student_id, name, department, year, consent}` | Student object | ID regex `^[A-Za-z0-9_-]{1,32}$`; 409 dup | Inserts `students` row + audit log | `student_create`, `student_dup` |
| GET | `/students` | AO | Query filters | Paged student list | `size <= 100` | Reads `students` | `student_search` |
| GET | `/students/{id}` | AO | — | Student object | 404 | None | `student_get` |
| PATCH | `/students/{id}` | A | Partial updates | Student object | Same validation | Updates `students` + audit log | `student_update` |
| DELETE | `/students/{id}` | A | — | `204 No Content` | 404 | Soft deletes student (`INACTIVE`), deactivates embeddings | `student_deactivate` |
| POST | `/students/{id}/face/session` | A | `{target_samples?}` | `{session_id, required, expires_in}` | Requires consent; 409 if active | In-memory session creation | `face_session_requires_consent` |
| POST | `/students/{id}/face/session/{sid}/capture` | A | `{camera_id?}` | `{accepted, count, required, quality}` | Rejects no face/blur/small face | In-memory frame collection | `capture_rejects_blur` |
| POST | `/students/{id}/face/session/{sid}/commit` | A | — | `{embeddings_stored, rejected}` | Requires ≥ `FACE_MIN_SAMPLES`; consistency check | Deactivates old + inserts new `face_embeddings` in one transaction + audit log | `commit_ok`, `commit_too_few` |
| GET | `/students/{id}/face/status` | AO | — | `{registered, sample_count, model}` | — | Reads `face_embeddings` metadata | `face_status_no_vectors` |
| DELETE | `/students/{id}/face` | A | — | `204 No Content` | — | Hard-deletes `face_embeddings` + audit log | `face_delete` |

### 3.4 Recognition, Attendance & Dashboard Endpoints

| Method | Path | Auth | Request Body | Success Response | Validation / Errors | DB Effect | Mandatory Test Name |
|---|---|---|---|---|---|---|---|
| POST | `/recognition/identify` | A | Multipart image (≤5MB) | `{faces:[{recognized, kind, student_id, name, similarity, bbox}]}` | Magic-byte check; 422 if no face | None | `identify_known`, `identify_unknown`, `identify_bad_image` |
| POST | `/recognition/workers/{id}/start` | A | — | Worker state | 404/409 | Updates camera status | `worker_start_stop` |
| POST | `/recognition/workers/{id}/stop` | A | — | Worker state | 404/409 | Updates camera status | `worker_start_stop` |
| GET | `/recognition/workers` | AO | — | Worker states & FPS | — | None | `workers_list` |
| GET | `/stream/{camera_id}` | ticket | Query `ticket` | MJPEG video stream | 401 invalid/expired ticket | None | `stream_requires_ticket` |
| GET | `/attendance` | AO | Date & filter query | Paged records | Date range ≤ 366 days | Reads `attendance_records` | `attendance_filters` |
| GET | `/attendance/recent` | AO | `limit<=50` | Recent records | — | Reads `attendance_records` | `attendance_recent` |
| POST | `/attendance/manual` | A | `{student_id, date, session_label, reason}` | Attendance record | 409 duplicate | Inserts `attendance_records` (method=MANUAL) + audit log | `attendance_manual_audit` |
| GET | `/dashboard/summary` | AO | — | Total summary metrics | — | Reads aggregates | `summary_real_values` |

### 3.5 Cameras, Events, Alerts, Blacklist, Tracking & Reports Endpoints

| Method | Path | Auth | Request Body | Success Response | Validation / Errors | DB Effect | Mandatory Test Name |
|---|---|---|---|---|---|---|---|
| GET | `/cameras` | AO | Query filters | Camera list | — | Reads `cameras` | `camera_list` |
| POST | `/cameras` | A | `{name, location, source_type, source_url, credentials_ref, enabled}` | Camera object | RTSP URL must not expose credentials; video file must resolve inside `data/videos` | Inserts `cameras` + audit log | `camera_create`, `camera_rejects_creds_in_url` |
| GET | `/cameras/{id}` | AO | — | Camera object | 404 | None | `camera_get` |
| PATCH | `/cameras/{id}` | A | Partial camera object | Camera object | 404 | Updates `cameras` + audit log | `camera_update` |
| DELETE | `/cameras/{id}` | A | — | `204 No Content` | 404 | Disables camera | `camera_disable` |
| POST | `/cameras/{id}/test` | A | — | `{ok, width, height, fps, error?}` | Timeout 5s | Updates camera status | `camera_test_failure` |
| GET | `/events` | AO | Event filters | Paged events | — | Reads `detection_events` | `events_filters` |
| GET | `/alerts` | AO | Alert filters | Paged alerts | — | Reads `security_alerts` | `alerts_filters` |
| POST | `/alerts/{id}/acknowledge` | AO | `{note?}` | Alert object | 409 if RESOLVED | Status -> ACKNOWLEDGED + audit log | `alert_ack` |
| POST | `/alerts/{id}/resolve` | AO | `{resolution_note}` | Alert object | Note required | Status -> RESOLVED + audit log | `alert_resolve` |
| GET | `/blacklist` | A | Query filters | Blacklist entries | — | Reads `blacklist_entries` | `blacklist_list` |
| POST | `/blacklist` | A | `{full_name, reason, category, severity, notes}` | Blacklist entry | — | Inserts `blacklist_entries` + audit log | `blacklist_create` |
| PATCH | `/blacklist/{id}` | A | Partial entry | Blacklist entry | — | Updates `blacklist_entries` + audit log | `blacklist_update` |
| POST | `/blacklist/{id}/deactivate` | A | — | Blacklist entry | — | Deactivates entry and vectors | `blacklist_deactivate_excludes` |
| POST | `/blacklist/{id}/face/session` | A | Registration parameters | Session object | Same as student face session | In-memory session | `blacklist_face_session` |
| POST | `/blacklist/{id}/face/session/{sid}/capture` | A | Capture payload | Capture response | Same image checks | In-memory capture | `blacklist_face_capture` |
| POST | `/blacklist/{id}/face/session/{sid}/commit` | A | — | Commit status | Same quality checks | Inserts `face_embeddings` with `blacklist_entry_id` | `blacklist_face_register` |
| GET | `/tracking/persons` | AO | `q=` search string | Person matches | `q >= 2` chars | Reads `students` / `blacklist_entries` | `tracking_search` |
| GET | `/tracking/persons/{student_id}/history` | AO | `from, to, camera_id` | Timeline of sightings | — | Queries `detection_events` | `tracking_history` |
| GET | `/tracking/persons/{student_id}/last-seen` | AO | — | `{camera, location, time, similarity}` | 404 if never seen | Queries latest `detection_events` | `tracking_last_seen` |
| GET | `/reports/attendance` | A | Filters | JSON report | — | Reads aggregates | `report_attendance` |
| GET | `/reports/attendance.csv` | A | Filters | CSV file stream | Formula-injection safe | Writes audit log `EXPORT_CSV` | `csv_export_safe` |
| GET | `/reports/security` | A | Filters | JSON report | — | Reads aggregates | `report_security` |
| GET | `/reports/security.csv` | A | Filters | CSV file stream | Formula-injection safe | Writes audit log `EXPORT_CSV` | `report_security_csv` |
| GET | `/audit-logs` | A | Log filters | Paged audit logs | Restricted to ADMIN | Reads `audit_logs` | `audit_admin_only` |
