import { Printer } from 'lucide-react'
import type { LogDay, TripResponse } from '../types'
import { fmtDayLong, fmtHours } from '../lib/format'
import { LogSheet } from './LogSheet'

export function LogSheets({ trip }: { trip: TripResponse }) {
  const { days } = trip
  return (
    <section className="print-area mx-auto max-w-7xl px-4 pb-10 lg:px-6">
      <div className="mb-4 flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold tracking-tight text-ink">Daily log sheets</h2>
          <p className="text-sm text-muted">
            {days.length} {days.length === 1 ? 'sheet' : 'sheets'} · record of duty status
          </p>
        </div>
        <button
          type="button"
          onClick={() => window.print()}
          className="no-print flex cursor-pointer items-center gap-2 rounded-lg border border-line bg-surface px-3.5 py-2 text-sm font-medium text-ink-soft shadow-sm transition-colors hover:bg-brand-50 hover:text-brand-800"
        >
          <Printer className="size-4" /> Print / Save PDF
        </button>
      </div>

      <div className="flex flex-col gap-6">
        {days.map((day, i) => (
          <LogCard key={day.date} day={day} index={i} total={days.length} trip={trip} />
        ))}
      </div>
    </section>
  )
}

function LogCard({
  day,
  index,
  total,
  trip,
}: {
  day: LogDay
  index: number
  total: number
  trip: TripResponse
}) {
  const totalOnDuty = day.totals.driving + day.totals.on_duty
  return (
    <article className="log-sheet overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-line px-5 py-4">
        <div>
          <h3 className="text-sm font-bold uppercase tracking-wide text-ink">
            Driver&apos;s Daily Log
          </h3>
          <p className="text-xs text-muted">(one calendar day — 24 hours)</p>
          <p className="mt-1 text-sm font-semibold text-brand-800">{fmtDayLong(day.date)}</p>
        </div>
        <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs">
          <HeaderField label="Miles driving today" value={`${day.total_miles}`} mono />
          <HeaderField label="Sheet" value={`${index + 1} / ${total}`} mono />
          <HeaderField label="Carrier" value="Spotter ELD" />
          <HeaderField label="From → To" value={routeLabel(trip)} />
        </div>
      </div>

      {/* Grid */}
      <div className="overflow-x-auto px-5 py-4">
        <LogSheet day={day} index={index} total={total} />
      </div>

      {/* Recap */}
      <div className="flex flex-wrap gap-x-8 gap-y-2 border-t border-line bg-canvas/60 px-5 py-3 text-xs">
        <Recap label="Off duty" value={fmtHours(day.totals.off_duty)} />
        <Recap label="Sleeper berth" value={fmtHours(day.totals.sleeper)} />
        <Recap label="Driving" value={fmtHours(day.totals.driving)} />
        <Recap label="On duty (not driving)" value={fmtHours(day.totals.on_duty)} />
        <Recap label="Total on-duty today" value={fmtHours(totalOnDuty)} highlight />
      </div>
    </article>
  )
}

function HeaderField({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="leading-tight">
      <div className="text-[10px] uppercase tracking-wide text-muted">{label}</div>
      <div className={`font-semibold text-ink ${mono ? 'tnum' : ''}`}>{value}</div>
    </div>
  )
}

function Recap({
  label,
  value,
  highlight,
}: {
  label: string
  value: string
  highlight?: boolean
}) {
  return (
    <div className="flex items-baseline gap-1.5">
      <span className="text-muted">{label}:</span>
      <span className={`tnum font-semibold ${highlight ? 'text-amber-dark' : 'text-ink'}`}>
        {value}
      </span>
    </div>
  )
}

function routeLabel(trip: TripResponse): string {
  const a = trip.locations.current_location.city ?? trip.input.current_location
  const b = trip.locations.dropoff_location.city ?? trip.input.dropoff_location
  return `${a} → ${b}`
}
