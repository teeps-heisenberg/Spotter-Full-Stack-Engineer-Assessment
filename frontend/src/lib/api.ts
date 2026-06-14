import type { TripFormValues, TripResponse } from '../types'

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8001').replace(
  /\/$/,
  '',
)

export class ApiError extends Error {
  field?: string
  constructor(message: string, field?: string) {
    super(message)
    this.name = 'ApiError'
    this.field = field
  }
}

export async function planTrip(values: TripFormValues): Promise<TripResponse> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}/api/trip/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(values),
    })
  } catch {
    throw new ApiError(
      'Could not reach the server. Is the backend running on ' + API_BASE + '?',
    )
  }

  let data: unknown = null
  try {
    data = await response.json()
  } catch {
    /* non-JSON error body */
  }

  if (!response.ok) {
    const body = data as { error?: string; field?: string; detail?: string } | null
    const message =
      body?.error ??
      body?.detail ??
      `Request failed (${response.status}). Please check your inputs and try again.`
    throw new ApiError(message, body?.field)
  }

  return data as TripResponse
}
