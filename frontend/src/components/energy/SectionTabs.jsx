import { useEffect, useRef, useState } from 'react'

const SECTIONS = [
  { id: 'overview', label: 'Overview' },
  { id: 'telemetry', label: 'Telemetry' },
  { id: 'assets', label: 'Assets' },
  { id: 'efficiency', label: 'Efficiency' },
]

export default function SectionTabs() {
  const [active, setActive] = useState('overview')
  const observerRef = useRef(null)

  useEffect(() => {
    const elements = SECTIONS
      .map((s) => document.getElementById(s.id))
      .filter(Boolean)

    observerRef.current = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)
        if (visible[0]) setActive(visible[0].target.id)
      },
      { rootMargin: '-35% 0px -55% 0px', threshold: [0, 0.25, 0.5, 0.75, 1] }
    )

    elements.forEach((el) => observerRef.current.observe(el))
    return () => observerRef.current?.disconnect()
  }, [])

  const scrollTo = (id) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <nav className="flex items-center gap-1 font-mono text-xs">
      {SECTIONS.map((s) => (
        <button
          key={s.id}
          onClick={() => scrollTo(s.id)}
          className={`px-3 py-1.5 rounded-full transition-colors ${
            active === s.id
              ? 'text-teal-700 dark:text-teal-300 bg-teal-500/10 dark:bg-teal-400/10'
              : 'text-slate-500 hover:text-ink dark:hover:text-slate-300'
          }`}
        >
          {s.label}
        </button>
      ))}
    </nav>
  )
}
