# End-to-End Data Flow Specifications

This document defines the complete data flows for frame processing, attendance marking, security alerts, and movement tracking.

---

## 1. Frame Processing & Identity Decision Flow

```mermaid
sequenceDiagram
    autonumber
    participant Cam as Camera Worker (OpenCV)
    participant Pipe as Vision Pipeline
    participant Reg as ModelRegistry (buffalo_l)
    participant DB as PostgreSQL + pgvector
    participant Bus as EventBus

    Cam->>Cam: Read frame (BGR image)
    Cam->>Pipe: Process frame (frame, camera_id)
    Pipe->>Pipe: Validate format, resolution & blur
    Pipe->>Reg: Detect faces & 5-point landmarks (SCRFD)
    Reg-->>Pipe: Return bboxes & landmarks
    loop For each detected face
        Pipe->>Pipe: Align face crop (norm_crop)
        Pipe->>Reg: Extract 512-d embedding (ArcFace)
        Reg-->>Pipe: Return L2-normalized vector
        Pipe->>DB: HNSW Cosine Search (1 - (a <=> b))
        DB-->>Pipe: Return top-1 vector match (id, distance, type)
        alt Similarity >= RECOGNITION_THRESHOLD (0.45)
            alt Entity Type == STUDENT
                Pipe->>Pipe: Decision: RECOGNIZED (Student)
            else Entity Type == BLACKLISTED
                Pipe->>Pipe: Decision: BLACKLISTED
            end
        else Similarity < RECOGNITION_THRESHOLD
            Pipe->>Pipe: Decision: UNKNOWN
        end
        Pipe->>Bus: Publish DetectionEvent(camera_id, identity, bbox, similarity)
    end
```

---

## 2. Attendance Marking Data Flow

```mermaid
sequenceDiagram
    autonumber
    participant Bus as EventBus
    participant AttService as Attendance Service
    participant Guard as Cooldown Guard (In-Memory)
    participant DB as PostgreSQL (sas_db)

    Bus->>AttService: Event: RECOGNIZED (Student_ID, Camera_ID, Timestamp)
    AttService->>Guard: Check cooldown (Student_ID, ATTENDANCE_COOLDOWN_SECONDS=300)
    alt Student in Cooldown Period
        Guard-->>AttService: Active Cooldown -> Skip DB Write
    else Cooldown Expired or First Sight
        Guard->>Guard: Update last_seen timestamp
        AttService->>DB: INSERT INTO attendance_records (student_id, camera_id, date, session_label, similarity, status) ON CONFLICT DO NOTHING
        DB-->>AttService: Row inserted (or conflict ignored)
        AttService->>DB: INSERT INTO detection_events (...)
    end
```

---

## 3. Unknown Person Security Alert Data Flow

```mermaid
sequenceDiagram
    autonumber
    participant Bus as EventBus
    participant AlertService as Alert Service
    participant DB as PostgreSQL (sas_db)
    participant UI as Streamlit Security Dashboard

    Bus->>AlertService: Event: UNKNOWN (Camera_ID, Timestamp, BBox)
    AlertService->>AlertService: Evaluate ALERT_POLICY_UNKNOWN (MEDIUM)
    alt Alert Policy Enabled (LOW / MEDIUM / HIGH)
        AlertService->>DB: Check active unresolved alert with dedup_key (camera_id + unknown + date_hour)
        alt Active Alert Exists
            AlertService->>DB: UPDATE security_alerts SET occurrence_count = occurrence_count + 1, last_seen_at = now()
        else No Active Alert
            AlertService->>DB: INSERT INTO security_alerts (alert_type='UNKNOWN_PERSON', severity='MEDIUM', status='NEW', ...)
        end
        AlertService->>UI: Push alert notification
    end
```

---

## 4. Blacklisted Person Immediate Alert Data Flow

```mermaid
sequenceDiagram
    autonumber
    participant Bus as EventBus
    participant AlertService as Alert Service
    participant DB as PostgreSQL (sas_db)
    participant UI as Streamlit Security Dashboard

    Bus->>AlertService: Event: BLACKLISTED (Blacklist_ID, Camera_ID, Similarity, Timestamp)
    AlertService->>AlertService: Evaluate ALERT_POLICY_BLACKLIST (CRITICAL / HIGH)
    AlertService->>DB: INSERT INTO security_alerts (alert_type='BLACKLISTED_PERSON', severity='CRITICAL', status='NEW', dedup_key=...) ON CONFLICT DO UPDATE
    AlertService->>DB: INSERT INTO audit_logs (action='BLACKLIST_MATCH_ALERT', ...)
    AlertService->>UI: Raise High-Priority Alert Banner & Visual Flash
```

---

## 5. Movement Tracking & Sightings Query Flow

```mermaid
sequenceDiagram
    autonumber
    participant Admin as Admin / Operator
    participant UI as Streamlit Tracking Page
    participant API as FastAPI Tracking Router
    participant Service as Tracking Service
    participant DB as PostgreSQL (sas_db)

    Admin->>UI: Enter Student ID / Name search
    UI->>API: GET /api/v1/tracking/persons/{student_id}/history?from=...&to=...
    API->>Service: QueryRecordedSightings(student_id, time_range)
    Service->>DB: Query detection_events grouped by camera_id & SIGHTING_GAP_SECONDS (60s)
    DB-->>Service: Return grouped sighting clusters
    Service-->>API: Format chronological timeline array
    API-->>UI: Return JSON payload
    UI-->>Admin: Render "Recorded Sightings" timeline & last known camera location
```
