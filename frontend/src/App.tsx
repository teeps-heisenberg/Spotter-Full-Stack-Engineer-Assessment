import { useState } from 'react'
import { Truck } from 'lucide-react'
import { TripForm } from './components/TripForm'
import { SummaryBar } from './components/SummaryBar'
import { StopsList } from './components/StopsList'
import { RouteMap } from './components/RouteMap'
import { ApiError, planTrip } from './lib/api'
import type { TripFormValues, TripResponse } from './types'

export default function App() {
  const [trip, setTrip] = useState<TripResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<{ message: string; field?: string } | null>(null)

  async function handleSubmit(values: TripFormValues) {
    setLoading(true)
    setError(null)
    try {
      const result = await planTrip(values)
      setTrip(result)
    } catch (err) {
      if (err instanceof ApiError) {
        setError({ message: err.message, field: err.field })
      } else {
        setError({ message: 'Something went wrong. Please try again.' })
      }
      setTrip(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-line bg-surface/85 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center gap-3 px-4 py-3 lg:px-6">
          <span className="flex size-9 items-center justify-center rounded-lg bg-brand-800 text-white shadow-sm">
            <Truck className="size-5" />
          </span>
          <div className="leading-tight">
            <h1 className="text-base font-bold tracking-tight text-ink">
              Spotter <span className="text-brand-700">ELD</span>
            </h1>
            <p className="text-xs text-muted">Trip planner &amp; electronic logbook</p>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-7xl gap-5 px-4 py-6 lg:grid-cols-[minmax(340px,380px)_1fr] lg:px-6">
        <aside className="flex flex-col gap-5">
          <section className="rounded-xl border border-line bg-surface p-5 shadow-sm">
            <h2 className="mb-1 text-sm font-semibold text-ink">Plan a trip</h2>
            <p className="mb-4 text-xs text-muted">
              Property-carrying driver · 70 hr / 8 day cycle
            </p>
            <TripForm onSubmit={handleSubmit} loading={loading} error={error} />
          </section>

          {trip && <SummaryBar trip={trip} />}
          {trip && trip.stops.length > 0 && <StopsList stops={trip.stops} />}
        </aside>

        <section className="flex flex-col gap-5">
          <div className="h-[60vh] lg:sticky lg:top-[4.75rem] lg:h-[calc(100vh-6.5rem)]">
            <RouteMap trip={trip} />
          </div>
        </section>
      </main>
    </div>
  )
}
