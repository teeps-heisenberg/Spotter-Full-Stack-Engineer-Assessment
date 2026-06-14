import { useEffect, useMemo } from 'react'
import L from 'leaflet'
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from 'react-leaflet'
import type { Stop, TripResponse } from '../types'
import { STOP_META, markerHtml } from '../lib/stops'
import { fmtDateTime } from '../lib/format'

const US_CENTER: [number, number] = [39.5, -98.35]

function stopIcon(stop: Stop) {
  return L.divIcon({
    html: markerHtml(stop.kind),
    className: 'spotter-marker',
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    popupAnchor: [0, -16],
  })
}

function FitBounds({ positions }: { positions: [number, number][] }) {
  const map = useMap()
  useEffect(() => {
    if (positions.length > 1) {
      map.fitBounds(L.latLngBounds(positions), { padding: [48, 48] })
    }
  }, [map, positions])
  return null
}

export function RouteMap({ trip }: { trip: TripResponse | null }) {
  const positions = useMemo<[number, number][]>(
    () => (trip ? trip.route.geometry.map(([lon, lat]) => [lat, lon]) : []),
    [trip],
  )
  const markers = useMemo(
    () => (trip ? trip.stops.filter((s) => s.lat != null && s.lon != null) : []),
    [trip],
  )

  return (
    <div className="relative h-full w-full overflow-hidden rounded-xl border border-line shadow-sm">
      <MapContainer
        center={US_CENTER}
        zoom={4}
        scrollWheelZoom
        className="h-full w-full"
        style={{ background: '#aadaff' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {positions.length > 1 && (
          <>
            <Polyline positions={positions} pathOptions={{ color: '#1d4ed8', weight: 5, opacity: 0.85 }} />
            <FitBounds positions={positions} />
          </>
        )}
        {markers.map((stop, i) => (
          <Marker
            key={`${stop.kind}-${stop.time}-${i}`}
            position={[stop.lat as number, stop.lon as number]}
            icon={stopIcon(stop)}
          >
            <Popup>
              <div className="min-w-[150px]">
                <div className="flex items-center gap-1.5">
                  <span
                    className="inline-block size-2.5 rounded-full"
                    style={{ background: STOP_META[stop.kind].color }}
                  />
                  <strong className="text-ink">{STOP_META[stop.kind].label}</strong>
                </div>
                {stop.label && <div className="mt-1 text-ink-soft">{stop.label}</div>}
                <div className="tnum mt-0.5 text-muted">{fmtDateTime(stop.time)}</div>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>

      {!trip && (
        <div className="pointer-events-none absolute inset-0 z-[400] flex items-center justify-center">
          <div className="rounded-xl bg-surface/90 px-5 py-4 text-center shadow-md backdrop-blur-sm">
            <p className="text-sm font-semibold text-ink">No trip planned yet</p>
            <p className="mt-0.5 text-xs text-muted">
              Enter trip details to draw the route and stops.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
