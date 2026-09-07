import { useState, useEffect, useCallback } from 'react'
import { NavLink } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Building2, Wrench, UsersRound, ShieldCheck, PoundSterling, LayoutDashboard, Search, Command, Sparkles, LogOut } from 'lucide-react'
import ThemeToggle from '../ui/ThemeToggle'
import CommandPalette from './CommandPalette'
import NotificationBell from './NotificationBell'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'

const NAV_ITEMS = [
  { to: '/executive', label: 'Overview', code: '00', Icon: LayoutDashboard, icon: 'bg-[#ece5ff] text-[#6d28d9]', dot: 'bg-[#8b5cf6]' },
  { to: '/energy', label: 'Energy flow', code: '01', Icon: Building2, icon: 'bg-[#dcedff] text-[#2374d9]', dot: 'bg-[#3b82f6]' },
  { to: '/maintenance', label: 'Asset care', code: '02', Icon: Wrench, icon: 'bg-[#dff7ef] text-[#0d9488]', dot: 'bg-[#14b8a6]' },
  { to: '/occupancy', label: 'Space pulse', code: '03', Icon: UsersRound, icon: 'bg-[#ede5ff] text-[#7c3aed]', dot: 'bg-[#8b5cf6]' },
  { to: '/security', label: 'Safety watch', code: '04', Icon: ShieldCheck, icon: 'bg-[#ffe4e9] text-[#e11d48]', dot: 'bg-[#f43f5e]' },
  { to: '/cost', label: 'Cost watch', code: '05', Icon: PoundSterling, icon: 'bg-[#ffe9c0] text-[#92400e]', dot: 'bg-[#f0a860]' },
]

export default function AppShell({ children }) {
  const [commandOpen, setCommandOpen] = useState(false)
  const { username, logout } = useAuth()
  const { show } = useToast()

  const handleLogout = () => {
    show('Logged out.', 'info')
    logout()
  }

  useEffect(() => {
    const onKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setCommandOpen(true)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  const initials = (username || 'OP').slice(0, 2).toUpperCase()

  return (
    <div className="min-h-screen bg-[#f7f6f2] dark:bg-graphite md:flex">
      <aside className="sticky top-0 z-30 flex h-screen w-[84px] shrink-0 flex-col border-r border-black/10 bg-[#0d0f13] px-3 py-5 md:w-[250px] md:px-4">
        <div className="mb-9 flex items-center justify-center gap-3 md:justify-start md:px-2">
          <motion.div initial={{ rotate: -12, scale: 0.75, opacity: 0 }} animate={{ rotate: 0, scale: 1, opacity: 1 }} transition={{ type: 'spring', stiffness: 260, damping: 18 }} className="relative grid h-10 w-10 place-items-center overflow-hidden rounded-[1.15rem] bg-[#15161a] text-white shadow-lg shadow-black/40">
            <span className="absolute -right-1 -top-1 h-4 w-4 rounded-full bg-[#c7f36a]" />
            <Building2 size={20} strokeWidth={2.2} />
          </motion.div>
          <div className="hidden min-w-0 md:block"><p className="font-display text-[15px] font-bold tracking-tight text-white">Facility<span className="text-teal-400">OS</span></p><p className="font-mono text-[8px] tracking-[0.18em] text-slate-500">INFOSYS · AI OPS</p></div>
        </div>

        <div className="mb-3 hidden px-3 font-mono text-[9px] tracking-[0.18em] text-slate-500 md:block">WORKSPACES</div>
        <nav className="flex flex-col gap-2">
          {NAV_ITEMS.map((item) => {
            const Icon = item.Icon
            return <NavLink key={item.to} to={item.to} end={item.to === '/occupancy'} className={({ isActive }) => `group relative flex items-center gap-3 rounded-2xl px-2 py-2.5 transition-colors ${isActive ? 'text-white' : 'text-slate-500 hover:bg-white/[0.05] hover:text-slate-200'}`}>
              {({ isActive }) => <>
                {isActive && <motion.span layoutId="nav-pill" transition={{ type: 'spring', stiffness: 360, damping: 28 }} className="absolute inset-0 rounded-2xl bg-white/[0.09]" />}
                <span className={`relative z-10 grid h-9 w-9 place-items-center rounded-xl ${item.icon}`}><Icon size={17} strokeWidth={2.1} /></span>
                <span className="relative z-10 hidden flex-1 font-body text-sm font-medium md:block">{item.label}</span>
                {isActive ? <motion.span layoutId="nav-dot" className={`relative z-10 hidden h-1.5 w-1.5 rounded-full md:block ${item.dot}`} /> : <span className="relative z-10 hidden font-mono text-[9px] text-slate-600 md:block">{item.code}</span>}
              </>}
            </NavLink>
          })}
        </nav>

        <div className="mt-auto">
          <div className="hidden rounded-[1.25rem] bg-white/[0.05] p-3 md:block"><div className="flex items-center gap-2"><span className="relative flex h-2 w-2"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-teal-400 opacity-70" /><span className="relative inline-flex h-2 w-2 rounded-full bg-teal-400" /></span><span className="font-mono text-[9px] tracking-wider text-slate-400">ALL SYSTEMS LINKED</span></div><p className="mt-2 font-body text-[11px] leading-relaxed text-slate-500">Four agents are ready to investigate your building.</p></div>
          <div className="mt-4 flex items-center justify-center gap-2 md:justify-between md:px-2"><div className="hidden items-center gap-2 md:flex"><span className="grid h-7 w-7 place-items-center rounded-full bg-[#ffe2c6] font-display text-[10px] font-bold text-[#9a561c]">{initials}</span><span className="font-mono text-[9px] text-slate-500 uppercase">{username || 'operator'}</span></div><div className="flex items-center gap-1"><button onClick={handleLogout} title="Log out" className="grid h-7 w-7 place-items-center rounded-full text-slate-500 hover:bg-white/[0.08] hover:text-rose-400 transition"><LogOut size={13} /></button><ThemeToggle /></div></div>
        </div>
      </aside>

      <main className="min-w-0 flex-1"><div className="flex h-16 items-center justify-end gap-2 border-b border-slate-200/70 bg-white/70 px-5 backdrop-blur-md dark:border-white/[0.06] dark:bg-panel/70 sm:px-7 lg:px-9"><button onClick={() => setCommandOpen(true)} className="hidden items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-2 font-mono text-[10px] text-slate-400 shadow-sm transition hover:border-slate-300 md:flex dark:border-white/[0.08] dark:bg-white/[0.04]"><Search size={13} />SEARCH <Command size={11} /></button><button className="grid h-9 w-9 place-items-center rounded-full border border-slate-200 bg-white text-slate-500 transition hover:-translate-y-0.5 hover:shadow-sm md:hidden dark:border-white/[0.08] dark:bg-white/[0.04]" onClick={() => setCommandOpen(true)}><Search size={15} /></button><NotificationBell /><span className="grid h-9 w-9 place-items-center rounded-full bg-[#15161a] text-[#c7f36a]"><Sparkles size={15} /></span></div>{children}</main>
      <CommandPalette open={commandOpen} onClose={() => setCommandOpen(false)} />
    </div>
  )
}
