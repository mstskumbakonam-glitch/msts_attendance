# Frontend Architecture (Streamlit Dashboard)

**Framework:** Streamlit Multi-Page Application (`frontend/`)  
**Server Port:** 8501  
**State Management:** `st.session_state`  
**API Integration:** Centralized API Client (`frontend/api_client.py`)  

---

## 1. Page Map & Navigation Structure

The Streamlit dashboard uses a single unified navigation sidebar matching system functional areas:

```text
[ LOGIN PAGE ] (st.session_state["token"] check)
  │
  ├── 📊 Dashboard              (7 Real KPIs, recent attendance, active alerts, live tile)
  │
  ├── 🎓 ATTENDANCE MODULE
  │   ├── Live Attendance       (Webcam / camera live stream with recognized overlay)
  │   ├── Students              (Student directory, CRUD, consent tracking)
  │   ├── Attendance Records    (Filterable attendance history table)
  │   └── Reports               (Attendance analytics & CSV export)
  │
  ├── 🛡️ SECURITY MODULE
  │   ├── Live Monitoring       (Multi-camera view & real-time alert feed)
  │   ├── Alerts                (Alert management lifecycle: NEW -> ACK -> RESOLVED)
  │   ├── Blacklist             (Blacklist directory & face registration)
  │   ├── Detection Events      (Full log of all detections: Recognized/Unknown/Blacklisted)
  │   └── Movement Tracking     (Person search & recorded sightings timeline)
  │
  └── ⚙️ SYSTEM MODULE
      ├── Cameras               (Camera registry, connection test, stream config)
      ├── Users                 (Admin account management & role assignment)
      └── Settings              (Threshold tuning & alert policy configuration)
```

---

## 2. Authentication & State Management

1. **Session State Initialization:** JWT bearer token, user role (`ADMIN` vs `OPERATOR`), and username are stored strictly in `st.session_state`.
2. **Login Gate:** Every page checks `st.session_state.get("token")`. If missing or expired, execution halts and redirects to `frontend/pages/login.py`.
3. **Role-Based UI Rendering:** UI elements for administrative actions (e.g. User creation, Settings update, Student deletion, CSV export) check the logged-in user role. Read-only views remain accessible to `OPERATOR`. The backend API strictly enforces RBAC independently.

---

## 3. Centralized API Client (`api_client.py`)

All HTTP communication between Streamlit pages and the FastAPI backend (`http://localhost:8000/api/v1`) passes through `frontend/api_client.py`:

```python
class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    def _get_headers(self) -> dict:
        token = st.session_state.get("token")
        return {"Authorization": f"Bearer {token}"} if token else {}
    
    def get(self, endpoint: str, params: dict = None): ...
    def post(self, endpoint: str, json: dict = None, files: dict = None): ...
    def patch(self, endpoint: str, json: dict = None): ...
    def delete(self, endpoint: str): ...
```

---

## 4. Live Video Streaming & Bounding Box Rendering

Live video streams are served by FastAPI as `multipart/x-mixed-replace` MJPEG HTTP streams and rendered inside Streamlit via raw HTML `<img>` tags:

```html
<img src="http://localhost:8000/api/v1/stream/CAM_ID?ticket=SHORT_LIVED_TICKET" width="100%" />
```

### Visual Bounding Box Conventions
- **Recognized Student:** **Green** bounding box with student name and similarity score (e.g. `STU001 - John Doe (0.94)`).
- **Unknown Person:** **Red** bounding box with `UNKNOWN` label.
- **Blacklisted Person:** **Thick Solid Red** bounding box with `CRITICAL: BLACKLISTED` label.

---

## 5. UI Honest Reporting Standards

1. **No Fabricated Numbers:** If database has zero records, metric cards display `0` or `No data yet`. Empty states are explicitly shown.
2. **Similarity Labeling:** Match confidence is explicitly labeled as **"Similarity"** (cosine score between 0.00 and 1.00), **NEVER called "Accuracy"**.
3. **Sightings Labeling:** Person movement history is explicitly labeled as **"Recorded Sightings"**, never "Continuous Tracking".
