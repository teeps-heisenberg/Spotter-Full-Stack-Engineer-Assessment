import { useState, type FormEvent } from 'react'
import { CircleAlert, Flag, Loader2, MapPin, PackageCheck, Timer } from 'lucide-react'
import type { TripFormValues } from '../types'

interface Props {
  onSubmit: (values: TripFormValues) => void
  loading: boolean
  error: { message: string; field?: string } | null
}

const EXAMPLE: TripFormValues = {
  current_location: 'Chicago, IL',
  pickup_location: 'Des Moines, IA',
  dropoff_location: 'Denver, CO',
  current_cycle_used: 14,
}

export function TripForm({ onSubmit, loading, error }: Props) {
  const [current, setCurrent] = useState('')
  const [pickup, setPickup] = useState('')
  const [dropoff, setDropoff] = useState('')
  const [cycle, setCycle] = useState('0')
  const [touched, setTouched] = useState(false)

  const cycleNum = Number(cycle)
  const cycleValid = cycle !== '' && !Number.isNaN(cycleNum) && cycleNum >= 0 && cycleNum <= 70
  const valid = current.trim() && pickup.trim() && dropoff.trim() && cycleValid

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setTouched(true)
    if (!valid || loading) return
    onSubmit({
      current_location: current.trim(),
      pickup_location: pickup.trim(),
      dropoff_location: dropoff.trim(),
      current_cycle_used: cycleNum,
    })
  }

  function fillExample() {
    setCurrent(EXAMPLE.current_location)
    setPickup(EXAMPLE.pickup_location)
    setDropoff(EXAMPLE.dropoff_location)
    setCycle(String(EXAMPLE.current_cycle_used))
  }

  const fieldError = (name: string) => error?.field === name

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
      <Field
        id="current_location"
        label="Current location"
        icon={<MapPin className="size-4" />}
        value={current}
        onChange={setCurrent}
        placeholder="City, ST"
        invalid={(touched && !current.trim()) || fieldError('current_location')}
        accent="text-brand-700"
      />
      <Field
        id="pickup_location"
        label="Pickup location"
        icon={<PackageCheck className="size-4" />}
        value={pickup}
        onChange={setPickup}
        placeholder="City, ST"
        invalid={(touched && !pickup.trim()) || fieldError('pickup_location')}
        accent="text-teal-600"
      />
      <Field
        id="dropoff_location"
        label="Drop-off location"
        icon={<Flag className="size-4" />}
        value={dropoff}
        onChange={setDropoff}
        placeholder="City, ST"
        invalid={(touched && !dropoff.trim()) || fieldError('dropoff_location')}
        accent="text-rose-600"
      />

      <div className="flex flex-col gap-1.5">
        <label
          htmlFor="current_cycle_used"
          className="flex items-center gap-2 text-sm font-medium text-ink-soft"
        >
          <Timer className="size-4 text-amber-dark" />
          Current cycle used
          <span className="font-normal text-muted">(hours, of 70)</span>
        </label>
        <input
          id="current_cycle_used"
          type="number"
          min={0}
          max={70}
          step={0.5}
          value={cycle}
          onChange={(e) => setCycle(e.target.value)}
          aria-invalid={touched && !cycleValid}
          className={`tnum w-full rounded-lg border bg-white px-3 py-2.5 text-ink outline-none transition-colors focus:border-brand-500 focus:ring-2 focus:ring-brand-500/30 ${
            touched && !cycleValid ? 'border-rose-400' : 'border-line'
          }`}
        />
        {touched && !cycleValid && (
          <p className="text-xs text-rose-600">Enter a number between 0 and 70.</p>
        )}
      </div>

      {error && !error.field && (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2.5 text-sm text-rose-700"
        >
          <CircleAlert className="mt-0.5 size-4 shrink-0" />
          <span>{error.message}</span>
        </div>
      )}
      {error?.field && (
        <p className="text-sm text-rose-600">{error.message}</p>
      )}

      <button
        type="submit"
        disabled={loading}
        className="mt-1 flex cursor-pointer items-center justify-center gap-2 rounded-lg bg-brand-800 px-4 py-2.5 font-semibold text-white shadow-sm transition-colors hover:bg-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500/40 disabled:cursor-not-allowed disabled:opacity-70"
      >
        {loading ? (
          <>
            <Loader2 className="size-4 animate-spin" /> Planning route…
          </>
        ) : (
          'Plan trip & generate logs'
        )}
      </button>

      <button
        type="button"
        onClick={fillExample}
        disabled={loading}
        className="cursor-pointer text-center text-xs font-medium text-brand-700 hover:text-brand-900 disabled:opacity-60"
      >
        Fill in an example trip
      </button>
    </form>
  )
}

interface FieldProps {
  id: string
  label: string
  icon: React.ReactNode
  value: string
  onChange: (v: string) => void
  placeholder: string
  invalid: boolean
  accent: string
}

function Field({ id, label, icon, value, onChange, placeholder, invalid, accent }: FieldProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="flex items-center gap-2 text-sm font-medium text-ink-soft">
        <span className={accent}>{icon}</span>
        {label}
      </label>
      <input
        id={id}
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-invalid={invalid}
        autoComplete="off"
        className={`w-full rounded-lg border bg-white px-3 py-2.5 text-ink outline-none transition-colors placeholder:text-muted/70 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/30 ${
          invalid ? 'border-rose-400' : 'border-line'
        }`}
      />
    </div>
  )
}
