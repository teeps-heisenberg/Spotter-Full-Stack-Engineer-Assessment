# Spotter ELD — Trip Planner & Electronic Logbook

A full-stack app for property-carrying truck drivers. Enter a trip and it returns:

- an **interactive route map** with fuel stops, rest breaks, pickup and drop-off, and
- **filled-in ELD daily log sheets** — one per day — drawn to the standard FMCSA
  record-of-duty-status format and obeying federal **Hours-of-Service** rules
  (70 hr / 8 day, property carrier).

> **Live demo:** _frontend_ → `<your-vercel-url>` · _API_ → `<your-render-url>`
>
> _(fill these in after deploying — see [Deployment](#deployment))_

---

## Inputs & outputs

**Inputs:** current location · pickup location · drop-off location · current cycle used (hours).

**Outputs:** a driving route + stops on a map, and a generated multi-day ELD log book.

The Hours-of-Service rules enforced (property-carrying driver, no adverse conditions):

| Rule | Limit |
|---|---|
| Driving limit | 11 hours per 14-hour window |
| Driving window | no driving after the 14th hour (off-duty breaks don't pause it) |
| 30-minute break | required once 8 cumulative driving hours pass since the last ≥30-min off-duty/sleeper |
| Cycle | 70 hours on-duty / 8 days; a 34-hour restart resets it |
| Daily reset | 10 consecutive hours off opens a fresh window |
| Fuel | a stop at least every 1,000 miles |
| Pickup / drop-off | 1 hour on-duty each |

The clock starts at **8:00 AM** on day 1. Times are computed exactly (not snapped to the
15-minute grid). When the 70-hour cycle is exhausted mid-trip, a **34-hour restart** is
inserted so the trip can complete.

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Django + Django REST Framework | HOS planner in testable Python; a thin proxy that keeps the map API key server-side and caches/minimizes calls |
| Frontend | React + TypeScript (Vite) | Fast dev/build; types keep the route + log data safe |
| Styling | Tailwind CSS v4 | Consistent data-dense dashboard design system |
| Map | Leaflet + OpenStreetMap | Free, no key for display |
| Geocoding / routing | Geoapify (free tier) | Geocode + driving route, called server-side |
| Log sheets | Custom SVG | Form-accurate, scalable, printable |

---

## How it works

```
Browser (React)
   │  POST /api/trip/  { current, pickup, dropoff, current_cycle_used }
   ▼
Django
   ├─ 1. geocode the 3 locations              (Geoapify, cached)
   ├─ 2. driving route through them           (Geoapify, cached) → polyline + per-leg distance/time
   ├─ 3. HOS planner  (pure Python)           → minute-accurate duty-status timeline
   ├─ 4. split timeline at midnight           → one log sheet per day (each totals 24h)
   └─ 5. reverse-geocode each stop            (Geoapify, cached) → "City, ST" labels
   ▼
JSON  { route, stops[], days[], summary }
   ▼
React renders the Leaflet map + SVG log sheets
```

Only the route work is per-request; everything else is computed from that one route, and
all Geoapify calls are cached — keeping us well within the free tier.

---

## Project structure

```
.
├── backend/                 # Django project
│   ├── config/              # settings, urls, wsgi
│   ├── trips/
│   │   ├── services/
│   │   │   ├── geoapify.py  # geocode / route / reverse-geocode (+ caching)
│   │   │   ├── planner.py   # pure HOS simulator → duty Segments
│   │   │   └── logsheet.py  # split timeline → per-day sheets + stops + summary
│   │   ├── views.py         # /api/health, /api/route, /api/trip
│   │   ├── serializers.py
│   │   └── tests*.py        # 32 tests
│   ├── requirements.txt
│   └── .env.example
├── frontend/                # React + TypeScript (Vite)
│   ├── src/
│   │   ├── components/      # TripForm, RouteMap, SummaryBar, StopsList, LogSheet(s)
│   │   ├── lib/             # api client, formatters, stop metadata
│   │   └── types.ts
│   └── .env.example
├── render.yaml              # backend deploy blueprint
└── README.md
```

---

## Running locally

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows  (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
copy .env.example .env             # then set GEOAPIFY_API_KEY
python manage.py migrate
python manage.py runserver 8001    # http://127.0.0.1:8001
```

> **Note:** port `8000` is reserved on some Windows machines; this project uses **8001**.

- Health check: `GET http://127.0.0.1:8001/api/health/`
- Run tests: `python manage.py test`

### Frontend

```bash
cd frontend
npm install
copy .env.example .env.local       # VITE_API_BASE_URL=http://127.0.0.1:8001
npm run dev                        # http://localhost:5173
```

---

## Environment variables

**Backend (`backend/.env`)**

| Variable | Purpose |
|---|---|
| `GEOAPIFY_API_KEY` | Geoapify key (free tier, no card) |
| `DJANGO_SECRET_KEY` | Django secret (set a long random value in production) |
| `DJANGO_DEBUG` | `True` locally, `False` in production |
| `DJANGO_ALLOWED_HOSTS` | comma-separated hosts (Render's host is auto-added) |
| `CORS_ALLOWED_ORIGINS` | comma-separated frontend origins (`*.vercel.app` allowed by default) |

**Frontend (`frontend/.env.local`)**

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | backend base URL (e.g. `http://127.0.0.1:8001` or your Render URL) |

---

## API

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health/` | liveness check |
| POST | `/api/route/` | geocode + driving route only |
| POST | `/api/trip/` | full plan: route + HOS schedule + per-day log sheets |

`POST /api/trip/` body:

```json
{
  "current_location": "Chicago, IL",
  "pickup_location": "Des Moines, IA",
  "dropoff_location": "Denver, CO",
  "current_cycle_used": 14
}
```

Returns `{ input, locations, route, stops, days, summary }`.

---

## Testing

```bash
cd backend
python manage.py test        # 32 tests: route service, HOS planner (rules + invariants), day splitter, endpoints
```

The HOS planner is pure Python and fully unit-tested, including an invariant sweep that
checks no generated plan ever violates the 11h / 14h / 8h-break / 70h limits and that every
day's four duty statuses sum to 24 hours.

---

## Deployment

Frontend → **Vercel**, backend → **Render**. Both deploy from this repo.

### 1. Backend on Render

Option A — **Blueprint** (uses `render.yaml`): New → *Blueprint* → pick this repo → it reads
`render.yaml`. Then set the **`GEOAPIFY_API_KEY`** env var in the dashboard.

Option B — **manual Web Service**:
- Root directory: `backend`
- Build: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
- Start: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
- Env vars: `DJANGO_DEBUG=False`, `DJANGO_SECRET_KEY=<long random>`, `GEOAPIFY_API_KEY=<your key>`, `PYTHON_VERSION=3.12.2`

Render's host is added to `ALLOWED_HOSTS` automatically. Note the free tier **cold-starts**
after inactivity (first request may take ~30–50s).

### 2. Frontend on Vercel

- Import this repo, set **Root Directory** to `frontend` (framework auto-detects as Vite)
- Add env var **`VITE_API_BASE_URL`** = your Render URL (e.g. `https://spotter-eld-backend.onrender.com`)
- Deploy. `vercel.json` handles SPA routing.

### 3. Lock down CORS (optional)

`*.vercel.app` origins are allowed by default. For a custom domain, set
`CORS_ALLOWED_ORIGINS` on Render to your exact frontend URL.

---

## Assumptions & notes

- Property-carrying driver, 70 hr / 8 day, no adverse driving conditions.
- Average speed is derived per leg from Geoapify's distance ÷ time (not hard-coded).
- Daily rests are logged as **sleeper berth**; the 34-hour restart as **off-duty**.
- A fuel stop is skipped if it would land within ~30 mi of the destination.
- Log times use the home-terminal local time zone.

---

## Credits

Routing & geocoding by [Geoapify](https://www.geoapify.com/). Map tiles ©
[OpenStreetMap](https://www.openstreetmap.org/copyright) contributors. HOS rules per the
FMCSA *Interstate Truck Driver's Guide to Hours of Service*.
