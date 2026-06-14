# Spotter ELD Trip Planner

A full-stack app that takes trip details (current location, pickup, dropoff, current
cycle hours used) and produces:

- An **interactive map** of the route with fuel stops, rest breaks, pickup and dropoff.
- **Filled-in ELD daily log sheets** drawn to the standard FMCSA format — one sheet per
  day, as many as the trip needs — obeying federal Hours-of-Service rules for a
  property-carrying driver (70 hr / 8 day).

> Status: **project scaffold** (Part 0). Route service, HOS planner, map, and log
> rendering are built in later parts.

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Django + Django REST Framework | Houses the HOS planner (testable Python) and a thin proxy that keeps the map API key server-side and minimizes/caches calls. |
| Frontend | React + TypeScript (Vite) | Fast dev/build; types keep route GeoJSON and log data safe. |
| Map | Leaflet + OpenStreetMap tiles | Free, no key for display; route GeoJSON + markers drop straight on. |
| Routing/Geocoding | Geoapify (free tier) | Geocode + driving route; called server-side. |
| Logs | Custom SVG | Form-accurate, scalable, printable, fully programmatic. |

## Repository layout

```
.
├── backend/          # Django project (config/) + trips app, Python venv in .venv/
│   ├── config/       # settings, urls, wsgi/asgi
│   ├── trips/        # API app (health check today; route + planner later)
│   ├── .env.example  # copy to .env and fill in
│   └── requirements.txt
└── frontend/         # React + TypeScript (Vite)
```

## Running locally

### Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate          # Windows  (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
cp .env.example .env            # then fill in values
python manage.py migrate
python manage.py runserver      # http://127.0.0.1:8000
```

Health check: `GET http://127.0.0.1:8000/api/health/` → `{"status": "ok", ...}`

Run tests: `python manage.py test`

### Frontend

```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

## Deployment (planned)

- Frontend → Vercel
- Backend → Render (free tier; note: free instances cold-start after inactivity)
