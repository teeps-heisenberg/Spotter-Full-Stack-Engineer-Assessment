import type { Stop } from '../types'
import { STOP_META } from '../lib/stops'
import { fmtDateTime } from '../lib/format'

export function StopsList({ stops }: { stops: Stop[] }) {
  return (
    <div className="rounded-xl border border-line bg-surface shadow-sm">
      <div className="border-b border-line px-4 py-3">
        <h2 className="text-sm font-semibold text-ink">Stops &amp; rests</h2>
        <p className="text-xs text-muted">{stops.length} events along the route</p>
      </div>
      <ol className="relative max-h-[340px] overflow-y-auto px-4 py-3">
        {stops.map((stop, i) => {
          const meta = STOP_META[stop.kind]
          const { Icon } = meta
          const isLast = i === stops.length - 1
          return (
            <li key={`${stop.kind}-${stop.time}-${i}`} className="relative flex gap-3 pb-4">
              {!isLast && (
                <span
                  aria-hidden
                  className="absolute left-[13px] top-7 h-[calc(100%-1rem)] w-px bg-line"
                />
              )}
              <span
                className="z-10 flex size-7 shrink-0 items-center justify-center rounded-full text-white shadow-sm"
                style={{ background: meta.color }}
              >
                <Icon className="size-3.5" />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-sm font-semibold text-ink">{meta.label}</span>
                  <span className="tnum shrink-0 text-xs text-muted">{fmtDateTime(stop.time)}</span>
                </div>
                {stop.label && <p className="truncate text-xs text-ink-soft">{stop.label}</p>}
              </div>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
