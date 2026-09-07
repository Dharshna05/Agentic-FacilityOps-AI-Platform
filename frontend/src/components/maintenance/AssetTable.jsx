import { useEffect, useMemo, useState } from 'react'
import Card from './Card'

const STATUSES = ['Critical', 'Warning', 'Good', 'Excellent']

const STATUS_STYLE = {
  Critical: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
  Warning: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
  Excellent: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
  Good: 'bg-teal-500/10 text-teal-400 border-teal-500/30',
}

const HEALTH_BAR = (score) =>
  score < 50 ? 'bg-rose-500' : score < 80 ? 'bg-amber-400' : score < 92 ? 'bg-teal-400' : 'bg-emerald-400'

const PAGE_SIZE = 8

function SortArrow({ active, direction }) {
  if (!active) return null
  return <span className="ml-1 text-teal-500">{direction === 'asc' ? '↑' : '↓'}</span>
}

export default function AssetTable({ assets, onSelect, selectedAssetId }) {
  const [sortConfig, setSortConfig] = useState({ key: 'health_score', direction: 'asc' })
  const [search, setSearch] = useState('')
  const [statusFilters, setStatusFilters] = useState([])
  const [page, setPage] = useState(1)

  const handleSort = (key) => {
    setSortConfig((prev) => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }))
  }

  const toggleStatusFilter = (status) => {
    setStatusFilters((prev) => (prev.includes(status) ? prev.filter((s) => s !== status) : [...prev, status]))
  }

  const filtered = useMemo(() => {
    let list = assets || []
    if (statusFilters.length) list = list.filter((a) => statusFilters.includes(a.status))
    if (search.trim()) {
      const q = search.trim().toLowerCase()
      list = list.filter(
        (a) => a.name.toLowerCase().includes(q) || a.asset_id.toLowerCase().includes(q) || a.asset_type.toLowerCase().includes(q)
      )
    }
    return list
  }, [assets, statusFilters, search])

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      const valueA = a[sortConfig.key]
      const valueB = b[sortConfig.key]
      if (valueA < valueB) return sortConfig.direction === 'asc' ? -1 : 1
      if (valueA > valueB) return sortConfig.direction === 'asc' ? 1 : -1
      return 0
    })
  }, [filtered, sortConfig])

  useEffect(() => { setPage(1) }, [search, statusFilters, assets])

  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE))
  const pageSafe = Math.min(page, totalPages)
  const pageItems = sorted.slice((pageSafe - 1) * PAGE_SIZE, pageSafe * PAGE_SIZE)

  const columns = [
    { key: 'asset_id', label: 'Asset' },
    { key: 'asset_type', label: 'Type' },
    { key: 'health_score', label: 'Health' },
    { key: 'status', label: 'Status' },
    { key: 'predicted_rul_cycles', label: 'RUL Days' },
  ]

  return (
    <Card title="Fleet Assets" badge={`${sorted.length} of ${assets?.length ?? 0}`}>
      <div className="flex flex-col sm:flex-row gap-2.5 mb-4">
        <div className="relative flex-1">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
               className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" strokeLinecap="round">
            <circle cx="11" cy="11" r="7" /><path d="M21 21l-4.3-4.3" />
          </svg>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="search by name, id, or type…"
            className="w-full pl-8 pr-3 py-1.5 text-xs font-mono rounded-lg border border-slate-200 dark:border-slate-800
                       bg-transparent text-ink dark:text-slate-200 placeholder:text-slate-400
                       focus:outline-none focus:border-teal-500/50 dark:focus:border-teal-400/40 transition-colors"
          />
        </div>
        <div className="flex gap-1.5 flex-wrap">
          {STATUSES.map((status) => {
            const active = statusFilters.includes(status)
            return (
              <button
                key={status}
                onClick={() => toggleStatusFilter(status)}
                className={`px-2.5 py-1.5 rounded-lg border text-[10px] font-mono transition-colors
                  ${active ? STATUS_STYLE[status] : 'border-slate-200 dark:border-slate-800 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'}`}
              >
                {status}
              </button>
            )
          })}
        </div>
      </div>

      {!pageItems.length && (
        <div className="text-xs text-slate-500 font-mono py-10 text-center">no assets match this filter</div>
      )}

      {pageItems.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wider text-slate-500 border-b border-slate-200 dark:border-slate-800">
                {columns.map((col) => (
                  <th key={col.key} className="py-2.5 cursor-pointer select-none hover:text-teal-500 transition-colors" onClick={() => handleSort(col.key)}>
                    {col.label}
                    <SortArrow active={sortConfig.key === col.key} direction={sortConfig.direction} />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {pageItems.map((asset) => (
                <tr
                  key={asset.asset_id}
                  onClick={() => onSelect(asset.asset_id)}
                  className={`border-b border-slate-200 dark:border-slate-800 cursor-pointer transition-colors
                    hover:bg-slate-100 dark:hover:bg-slate-800/50
                    ${selectedAssetId === asset.asset_id ? 'bg-teal-500/10 dark:bg-teal-400/10' : ''}`}
                >
                  <td className="py-3 font-medium">
                    {asset.name}
                    <div className="text-xs text-slate-500 font-mono">{asset.asset_id}</div>
                  </td>
                  <td className="text-slate-600 dark:text-slate-400">{asset.asset_type}</td>
                  <td className="w-40">
                    <div className="flex items-center gap-2.5">
                      <div className="flex-1 h-2 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
                        <div className={`h-full rounded-full ${HEALTH_BAR(asset.health_score)}`} style={{ width: `${asset.health_score}%` }} />
                      </div>
                      <span className="text-xs tabular-nums">{asset.health_score}%</span>
                    </div>
                  </td>
                  <td>
                    <span className={`px-2.5 py-1 rounded-full border text-xs ${STATUS_STYLE[asset.status] || ''}`}>
                      {asset.status}
                    </span>
                  </td>
                  <td className="font-mono text-xs tabular-nums">{asset.predicted_rul_cycles}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-200 dark:border-slate-800">
          <span className="font-mono text-[10px] text-slate-500">page {pageSafe} of {totalPages}</span>
          <div className="flex gap-1.5">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={pageSafe === 1}
              className="px-2.5 py-1 rounded-lg border border-slate-200 dark:border-slate-800 text-[11px] font-mono text-slate-500
                         hover:text-teal-500 hover:border-teal-500/40 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              ← prev
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={pageSafe === totalPages}
              className="px-2.5 py-1 rounded-lg border border-slate-200 dark:border-slate-800 text-[11px] font-mono text-slate-500
                         hover:text-teal-500 hover:border-teal-500/40 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              next →
            </button>
          </div>
        </div>
      )}
    </Card>
  )
}
