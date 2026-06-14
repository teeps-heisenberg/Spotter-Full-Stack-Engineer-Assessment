import {
  ArrowDownToLine,
  Coffee,
  Fuel,
  Moon,
  PackageCheck,
  Play,
  RotateCcw,
  type LucideIcon,
} from 'lucide-react'
import type { StopKind } from '../types'

interface StopMeta {
  label: string
  color: string
  Icon: LucideIcon
  glyph: string // inline SVG markup for Leaflet divIcon
}

const PLAY = '<path d="M9 7.5l8 4.5-8 4.5z" fill="white"/>'
const ARROW_DOWN =
  '<path d="M12 4v9m0 0l-3.5-3.5M12 13l3.5-3.5M6 18h12" fill="none" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'
const CHECK =
  '<path d="M6 12.5l4 4 8-9" fill="none" stroke="white" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>'
const DROPLET = '<path d="M12 4s-5 5.5-5 9a5 5 0 0010 0c0-3.5-5-9-5-9z" fill="white"/>'
const PAUSE =
  '<rect x="8" y="7" width="2.6" height="10" rx="1" fill="white"/><rect x="13.4" y="7" width="2.6" height="10" rx="1" fill="white"/>'
const MOON = '<path d="M17 13.5A6 6 0 1110.5 7 4.7 4.7 0 0017 13.5z" fill="white"/>'
const REFRESH =
  '<path d="M7 12a5 5 0 105-5" fill="none" stroke="white" stroke-width="2.2" stroke-linecap="round"/><path d="M12 4l1.2 3.2-3.2 1" fill="none" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'

export const STOP_META: Record<StopKind, StopMeta> = {
  start: { label: 'Trip start', color: '#1e40af', Icon: Play, glyph: PLAY },
  pickup: { label: 'Pickup', color: '#0d9488', Icon: ArrowDownToLine, glyph: ARROW_DOWN },
  dropoff: { label: 'Drop-off', color: '#be123c', Icon: PackageCheck, glyph: CHECK },
  fuel: { label: 'Fuel stop', color: '#f59e0b', Icon: Fuel, glyph: DROPLET },
  break: { label: '30-min break', color: '#7c3aed', Icon: Coffee, glyph: PAUSE },
  rest: { label: '10-hour rest', color: '#475569', Icon: Moon, glyph: MOON },
  restart: { label: '34-hour restart', color: '#0f766e', Icon: RotateCcw, glyph: REFRESH },
}

export function markerHtml(kind: StopKind): string {
  const { color, glyph } = STOP_META[kind]
  return `
    <div style="width:26px;height:26px;border-radius:50%;background:${color};
      border:2px solid #fff;box-shadow:0 2px 6px rgba(15,23,42,.4);
      display:flex;align-items:center;justify-content:center;">
      <svg viewBox="0 0 24 24" width="16" height="16">${glyph}</svg>
    </div>`
}
