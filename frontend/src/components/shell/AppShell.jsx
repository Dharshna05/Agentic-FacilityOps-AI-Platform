import { NavLink } from 'react-router-dom'
import { useTheme } from '../../context/ThemeContext'
import ThemeToggle from '../ui/ThemeToggle'

const NAV_ITEMS = [
  {
    to: '/energy', label: 'Energy', code: 'EN',
    activeClass: 'bg-blue-500/10 dark:bg-blue-400/10 text-blue-700 dark:text-blue-300',
    barClass: 'bg-blue-500 dark:bg-blue-400',
    icon: (
      <path d="M13 2L4 14h6l-1 8 9-12h-6l1-8z" strokeLinecap="round" strokeLinejoin="round" />
    ),
  },
  {
    to: '/maintenance', label: 'Maintenance', code: 'MT',
    activeClass: 'bg-teal-500/10 dark:bg-teal-400/10 text-teal-700 dark:text-teal-300',
    barClass: 'bg-teal-500 dark:bg-teal-400',
    icon: (
      <path d="M14.7 6.3a4 4 0 0 1-5.4 5.4L4 17l3 3 5.3-5.3a4 4 0 0 1 5.4-5.4l-2.6 2.6-2-2 2.6-2.6z" strokeLinecap="round" strokeLinejoin="round" />
    ),
  },
]

export default function AppShell({ children }) {
  const { theme } = useTheme()

  return (
    <div className="min-h-screen flex bg-paper dark:bg-graphite transition-colors duration-200">
      <aside className="w-[76px] md:w-[220px] shrink-0 border-r border-slate-200 dark:border-slate-800/80
                         bg-paper-raised dark:bg-panel flex flex-col">
        <div className="h-[76px] flex items-center justify-center md:justify-start md:px-5 gap-2.5 border-b border-slate-200 dark:border-slate-800/80">
          <div className="w-7 h-7 rounded-md bg-gradient-to-br from-teal-400 via-blue-500 to-violet-600 flex items-center justify-center shrink-0">
            <span className="text-white font-display text-xs font-bold">F</span>
          </div>
          <div className="hidden md:block leading-tight">
            <div className="font-display text-sm font-semibold text-ink dark:text-slate-100">FacilityOps</div>
            <div className="font-mono text-[9px] tracking-[0.15em] text-slate-400 dark:text-slate-600">AGENTIC AI PLATFORM</div>
          </div>
        </div>

        <nav className="flex-1 py-4 flex flex-col gap-1 px-3">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `group flex items-center gap-3 rounded-lg px-3 py-2.5 transition-colors relative
                 ${isActive
                   ? item.activeClass
                   : 'text-slate-500 dark:text-slate-500 hover:bg-slate-100 dark:hover:bg-panel-raised hover:text-ink dark:hover:text-slate-300'}`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && <span className={`absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-full ${item.barClass}`} />}
                  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="shrink-0">
                    {item.icon}
                  </svg>
                  <span className="hidden md:inline font-body text-sm">{item.label}</span>
                  <span className="hidden md:inline ml-auto font-mono text-[9px] text-slate-300 dark:text-slate-700">{item.code}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="p-3 border-t border-slate-200 dark:border-slate-800/80 flex items-center justify-center md:justify-between gap-2">
          <div className="hidden md:flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-teal-500 dark:bg-teal-400" />
            <span className="font-mono text-[9px] tracking-widest text-slate-400 dark:text-slate-600">SYSTEM LIVE</span>
          </div>
          <ThemeToggle />
        </div>
      </aside>

      <main className="flex-1 min-w-0">{children}</main>
    </div>
  )
}
