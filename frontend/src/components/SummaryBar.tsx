import { CalendarDays, Clock, Navigation, Briefcase } from 'lucide-react'
import type { TripResponse } from '../types'
import { fmtHours } from '../lib/format'

export function SummaryBar({ trip }: { trip: TripResponse }) {
  const { summary } = trip
  const items = [
    {
      label: 'Total distance',
      value: summary.total_distance_mi.toLocaleString(),
      unit: 'mi',
      Icon: Navigation,
      tone: 'text-brand-700',
    },
    {
      label: 'Driving time',
      value: fmtHours(summary.total_driving_hr),
      unit: '',
      Icon: Clock,
      tone: 'text-teal-600',
    },
    {
      label: 'On-duty (not driving)',
      value: fmtHours(summary.total_on_duty_hr),
      unit: '',
      Icon: Briefcase,
      tone: 'text-amber-dark',
    },
    {
      label: 'Log sheets',
      value: String(summary.total_days),
      unit: summary.total_days === 1 ? 'day' : 'days',
      Icon: CalendarDays,
      tone: 'text-rose-600',
    },
  ]

  return (
    <div className="grid grid-cols-2 gap-3">
      {items.map(({ label, value, unit, Icon, tone }) => (
        <div
          key={label}
          className="rounded-xl border border-line bg-surface p-3.5 shadow-sm"
        >
          <div className="flex items-center gap-1.5 text-muted">
            <Icon className={`size-3.5 ${tone}`} />
            <span className="text-xs font-medium">{label}</span>
          </div>
          <div className="mt-1.5 flex items-baseline gap-1">
            <span className="tnum text-2xl font-semibold text-ink">{value}</span>
            {unit && <span className="text-xs font-medium text-muted">{unit}</span>}
          </div>
        </div>
      ))}
    </div>
  )
}
