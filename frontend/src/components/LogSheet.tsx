import type { DutyStatus, LogDay } from '../types'
import { fmtDayLong } from '../lib/format'

// --- Grid geometry (SVG user units) ---
const PAD = 12
const LABEL_W = 116
const HOUR_W = 33
const GRID_W = HOUR_W * 24 // 792
const TOTAL_W = 70
const ROW_H = 30
const GRID_H = ROW_H * 4 // 120
const HOUR_LABEL_H = 20
const REMARKS_H = 140

const gridLeft = PAD + LABEL_W
const gridTop = PAD + HOUR_LABEL_H
const gridRight = gridLeft + GRID_W
const gridBottom = gridTop + GRID_H
const W = gridLeft + GRID_W + TOTAL_W + PAD
const H = gridBottom + REMARKS_H + PAD

const ROWS: { key: DutyStatus; label: string }[] = [
  { key: 'off_duty', label: '1. Off Duty' },
  { key: 'sleeper', label: '2. Sleeper Berth' },
  { key: 'driving', label: '3. Driving' },
  { key: 'on_duty', label: '4. On Duty (not driving)' },
]
const ROW_INDEX: Record<DutyStatus, number> = {
  off_duty: 0,
  sleeper: 1,
  driving: 2,
  on_duty: 3,
}

const LINE = '#0f172a'

const clamp = (t: number) => Math.max(0, Math.min(24, t))
const x = (t: number) => gridLeft + (t / 24) * GRID_W
const rowY = (i: number) => gridTop + i * ROW_H + ROW_H / 2

function fmtTot(h: number): string {
  const r = Math.round(h * 100) / 100
  return Number.isInteger(r) ? String(r) : String(r)
}

const SHORT_NOTE: Record<string, string> = {
  'Trip start': 'Start',
  'Pickup (load)': 'Pickup',
  'Drop-off (unload)': 'Drop-off',
  'Fuel stop': 'Fuel',
  '30-minute break': 'Break',
  '10-hour rest': 'Rest',
  '34-hour restart (cycle reset)': 'Restart',
}

interface Props {
  day: LogDay
  index: number
  total: number
}

export function LogSheet({ day, index, total }: Props) {
  const dayStart = new Date(`${day.date}T00:00:00`).getTime()
  const hod = (iso: string) => clamp((new Date(iso).getTime() - dayStart) / 3600000)

  const segs = day.segments.map((s) => ({
    i: ROW_INDEX[s.status],
    t0: hod(s.start),
    t1: hod(s.end),
  }))

  const grandTotal =
    day.totals.off_duty + day.totals.sleeper + day.totals.driving + day.totals.on_duty

  // Minor (15-min) + hour gridlines.
  const quarterLines = []
  for (let q = 0; q <= 96; q++) {
    const gx = gridLeft + (q / 96) * GRID_W
    const isHour = q % 4 === 0
    const isMajor = q === 0 || q === 48 || q === 96
    quarterLines.push(
      <line
        key={`q${q}`}
        x1={gx}
        y1={gridTop}
        x2={gx}
        y2={gridBottom}
        stroke={isMajor ? '#94a3b8' : isHour ? '#cbd5e1' : '#eef2f7'}
        strokeWidth={isMajor ? 1.1 : isHour ? 0.8 : 0.5}
      />,
    )
  }

  const hourLabels = []
  for (let h = 0; h <= 24; h++) {
    const label = h === 0 || h === 24 ? 'MID' : h === 12 ? 'NOON' : String(h % 12)
    hourLabels.push(
      <text
        key={`h${h}`}
        x={x(h)}
        y={gridTop - 6}
        textAnchor="middle"
        fontSize={h % 12 === 0 ? 7 : 8}
        fill="#475569"
        fontWeight={h % 12 === 0 ? 700 : 400}
      >
        {label}
      </text>,
    )
  }

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      width="100%"
      role="img"
      aria-label={`Daily log grid for ${day.date}`}
      style={{ display: 'block', minWidth: 720 }}
    >
      {/* Hour labels */}
      {hourLabels}

      {/* Grid background + minor/hour lines */}
      <rect
        x={gridLeft}
        y={gridTop}
        width={GRID_W}
        height={GRID_H}
        fill="#ffffff"
        stroke="#475569"
        strokeWidth={1}
      />
      {quarterLines}

      {/* Row separators + labels + totals header */}
      {ROWS.map((row, i) => (
        <g key={row.key}>
          {i > 0 && (
            <line
              x1={gridLeft}
              y1={gridTop + i * ROW_H}
              x2={gridRight}
              y2={gridTop + i * ROW_H}
              stroke="#94a3b8"
              strokeWidth={0.8}
            />
          )}
          <text
            x={gridLeft - 8}
            y={rowY(i)}
            textAnchor="end"
            dominantBaseline="middle"
            fontSize={9}
            fontWeight={600}
            fill="#334155"
          >
            {row.label}
          </text>
          {/* per-row total */}
          <text
            x={gridRight + TOTAL_W / 2}
            y={rowY(i)}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize={11}
            fontWeight={600}
            fill="#0f172a"
            style={{ fontFamily: 'Fira Code, monospace' }}
          >
            {fmtTot(day.totals[row.key])}
          </text>
        </g>
      ))}

      {/* Totals column frame + header */}
      <rect
        x={gridRight}
        y={gridTop}
        width={TOTAL_W}
        height={GRID_H}
        fill="none"
        stroke="#475569"
        strokeWidth={1}
      />
      <text
        x={gridRight + TOTAL_W / 2}
        y={gridTop - 6}
        textAnchor="middle"
        fontSize={7}
        fontWeight={700}
        fill="#475569"
      >
        TOTAL HRS
      </text>
      <text
        x={gridRight + TOTAL_W / 2}
        y={gridBottom + 12}
        textAnchor="middle"
        fontSize={10}
        fontWeight={700}
        fill="#0f172a"
        style={{ fontFamily: 'Fira Code, monospace' }}
      >
        = {fmtTot(grandTotal)}
      </text>

      {/* Duty-status step line */}
      <g fill="none" stroke={LINE} strokeWidth={2.4} strokeLinejoin="round" strokeLinecap="round">
        {segs.map((s, k) => (
          <line key={`hz${k}`} x1={x(s.t0)} y1={rowY(s.i)} x2={x(s.t1)} y2={rowY(s.i)} />
        ))}
        {segs.slice(0, -1).map((s, k) => (
          <line
            key={`vt${k}`}
            x1={x(s.t1)}
            y1={rowY(s.i)}
            x2={x(s.t1)}
            y2={rowY(segs[k + 1].i)}
          />
        ))}
      </g>
      {/* Transition dots */}
      {segs.slice(0, -1).map((s, k) => (
        <circle key={`dot${k}`} cx={x(s.t1)} cy={rowY(segs[k + 1].i)} r={2.3} fill={LINE} />
      ))}

      {/* Remarks */}
      <text x={PAD} y={gridBottom + 16} fontSize={8} fontWeight={700} fill="#475569">
        REMARKS
      </text>
      {day.remarks.map((r, k) => {
        const rx = x(hod(r.time))
        const short = SHORT_NOTE[r.note] ?? r.note
        return (
          <g key={`rm${k}`}>
            <line
              x1={rx}
              y1={gridBottom}
              x2={rx}
              y2={gridBottom + 14}
              stroke="#64748b"
              strokeWidth={0.8}
            />
            <g transform={`translate(${rx}, ${gridBottom + 17}) rotate(-58)`}>
              <text x={4} y={0} fontSize={8.5} fontWeight={600} fill="#0f172a">
                {r.label ?? '—'}
              </text>
              <text x={4} y={10} fontSize={7.5} fill="#64748b">
                {short}
              </text>
            </g>
          </g>
        )
      })}

      {/* Day index caption (bottom-right) */}
      <text x={W - PAD} y={H - 2} textAnchor="end" fontSize={7} fill="#94a3b8">
        Day {index + 1} of {total} · {fmtDayLong(day.date)}
      </text>
    </svg>
  )
}
