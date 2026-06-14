// Shapes returned by the Django backend POST /api/trip/.

export type DutyStatus = 'off_duty' | 'sleeper' | 'driving' | 'on_duty'

export type StopKind =
  | 'start'
  | 'pickup'
  | 'dropoff'
  | 'fuel'
  | 'break'
  | 'rest'
  | 'restart'

export interface Stop {
  kind: StopKind
  status: DutyStatus
  time: string // ISO datetime
  lat: number | null
  lon: number | null
  label: string | null
  remark: string
}

export interface LogSegment {
  status: DutyStatus
  start: string
  end: string
  duration_hr: number
  kind: string
  remark: string
  label: string | null
  lat: number | null
  lon: number | null
}

export interface LogRemark {
  time: string
  label: string | null
  note: string
}

export interface LogDay {
  date: string // YYYY-MM-DD
  segments: LogSegment[]
  totals: Record<DutyStatus, number>
  total_miles: number
  remarks: LogRemark[]
}

export interface GeocodedLocation {
  lat: number
  lon: number
  formatted: string
  city: string | null
  state_code: string | null
}

export interface TripResponse {
  input: {
    current_location: string
    pickup_location: string
    dropoff_location: string
    current_cycle_used: number
  }
  locations: {
    current_location: GeocodedLocation
    pickup_location: GeocodedLocation
    dropoff_location: GeocodedLocation
  }
  route: {
    geometry: [number, number][] // [lon, lat]
    distance_mi: number
    time_hr: number
    legs: { distance_mi: number; time_hr: number }[]
  }
  stops: Stop[]
  days: LogDay[]
  summary: {
    start: string
    end: string
    total_days: number
    total_distance_mi: number
    total_driving_hr: number
    total_on_duty_hr: number
  }
}

export interface TripFormValues {
  current_location: string
  pickup_location: string
  dropoff_location: string
  current_cycle_used: number
}
