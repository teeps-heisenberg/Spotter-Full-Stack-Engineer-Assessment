// Small display formatters. Backend datetimes are home-terminal local time
// (naive ISO), so we render them as-is via the Date object.

export function fmtHours(hours: number): string {
  const h = Math.floor(hours + 1e-6)
  const m = Math.round((hours - h) * 60)
  if (h === 0 && m === 0) return '0m'
  if (h === 0) return `${m}m`
  if (m === 0) return `${h}h`
  return `${h}h ${m}m`
}

export function fmtClock(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  })
}

export function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export function fmtDayLong(dateOnly: string): string {
  // dateOnly = "YYYY-MM-DD"; append midday to avoid timezone date-shift.
  return new Date(`${dateOnly}T12:00:00`).toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}
