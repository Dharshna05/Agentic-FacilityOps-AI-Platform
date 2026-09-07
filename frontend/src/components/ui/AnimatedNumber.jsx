import { useEffect, useRef, useState } from 'react'

/**
 * Counts up/down from the previous value to the new one whenever `value`
 * changes — makes a KPI refresh (dashboard poll, manual add/delete, a
 * newly-run forecast) actually visible as a live number moving, instead of
 * silently swapping static text. Falls back to rendering the raw value
 * untouched for anything that isn't a plain finite number (e.g. "₹1.2 Cr",
 * "—", or a formatted string already containing its own unit) — animating
 * text like that would either do nothing or look broken.
 */
export default function AnimatedNumber({ value, duration = 700 }) {
  const isNumeric = typeof value === 'number' && Number.isFinite(value)
  const decimals = isNumeric && !Number.isInteger(value) ? Math.min(2, (String(value).split('.')[1] || '').length) : 0

  const [display, setDisplay] = useState(isNumeric ? value : 0)
  const fromRef = useRef(isNumeric ? value : 0)
  const rafRef = useRef(null)

  useEffect(() => {
    if (!isNumeric) return
    const from = fromRef.current
    const to = value
    if (from === to) return

    const start = performance.now()
    const tick = (now) => {
      const t = Math.min((now - start) / duration, 1)
      // Ease-out cubic — fast start, gentle settle, reads as "counting"
      // rather than a linear ticker.
      const eased = 1 - Math.pow(1 - t, 3)
      setDisplay(from + (to - from) * eased)
      if (t < 1) {
        rafRef.current = requestAnimationFrame(tick)
      } else {
        fromRef.current = to
      }
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(rafRef.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value])

  if (!isNumeric) return <>{value}</>

  return <>{display.toLocaleString('en-IN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}</>
}
