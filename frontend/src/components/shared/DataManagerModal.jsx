import { useEffect, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Trash2, Plus, X, Database, AlertTriangle } from 'lucide-react'
import { useToast } from '../../context/ToastContext'

function fmtTime(t) {
  if (!t) return '—'
  return new Date(t).toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

/**
 * Generic add / view / remove panel for one milestone's raw dataset.
 *
 * Props:
 *  - open: boolean — whether the panel is shown
 *  - onClose: () => void
 *  - title / subtitle: header text
 *  - fields: [{ key, label, type: 'text'|'number'|'checkbox'|'datetime-local', required?, step?, defaultValue? }]
 *    — drives the "add a record" form
 *  - columns: [{ key, label, format?: (value, row) => string }] — drives the table
 *  - fetchRecords: (limit) => Promise<{records: [...]}>
 *  - addRecord: (payload) => Promise
 *  - deleteRecord: (id) => Promise
 *  - clearAllRecords: optional (filterValue) => Promise — wipes the whole
 *    dataset (or just the locked entity's slice, if lockedField is set),
 *    with no replacement loaded. Omit to hide the "Clear all" control.
 *  - onChanged: () => void — called after a successful add/delete so the parent dashboard can refresh
 *  - lockedField: optional { key, value, label } — when set (e.g. clicked a specific
 *    access point / zone / asset), that field is pre-filled and shown read-only,
 *    and the record list is filtered to just that entity.
 */
export default function DataManagerModal({
  open, onClose, title, subtitle, fields, columns,
  fetchRecords, addRecord, deleteRecord, clearAllRecords, onChanged, lockedField,
}) {
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const { show } = useToast()
  const [submitting, setSubmitting] = useState(false)
  const [confirmingClear, setConfirmingClear] = useState(false)
  const [clearing, setClearing] = useState(false)
  const [form, setForm] = useState(() => {
    const init = {}
    fields.forEach(f => { init[f.key] = f.defaultValue ?? (f.type === 'checkbox' ? true : '') })
    if (lockedField) init[lockedField.key] = lockedField.value
    return init
  })

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    fetchRecords(20)
      .then(d => setRecords(d.records || []))
      .catch(err => setError(err.response?.data?.detail || err.message))
      .finally(() => setLoading(false))
  }, [fetchRecords])

  useEffect(() => {
    if (!open) return
    load()
    const init = {}
    fields.forEach(f => { init[f.key] = f.defaultValue ?? (f.type === 'checkbox' ? true : '') })
    if (lockedField) init[lockedField.key] = lockedField.value
    setForm(init)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, lockedField?.value])

  async function handleAdd(e) {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const payload = {}
      fields.forEach(f => {
        const v = form[f.key]
        if (v === '' || v == null) return
        payload[f.key] = f.type === 'number' ? Number(v) : v
      })
      await addRecord(payload)
      await load()
      onChanged?.()
      show(`${title || 'Record'} added.`, 'success')
    } catch (err) {
      const detail = err.response?.data?.detail || err.message
      setError(detail)
      show(detail, 'error')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDelete(id) {
    setError(null)
    try {
      await deleteRecord(id)
      setRecords(prev => prev.filter(r => r.id !== id))
      onChanged?.()
      show('Record deleted.', 'success')
    } catch (err) {
      const detail = err.response?.data?.detail || err.message
      setError(detail)
      show(detail, 'error')
    }
  }

  async function handleClearAll() {
    setClearing(true)
    setError(null)
    try {
      await clearAllRecords(lockedField?.value)
      const clearedCount = records.length
      setRecords([])
      setConfirmingClear(false)
      onChanged?.()
      show(`Cleared ${clearedCount} record${clearedCount === 1 ? '' : 's'}.`, 'success')
    } catch (err) {
      const detail = err.response?.data?.detail || err.message
      setError(detail)
      show(detail, 'error')
    } finally {
      setClearing(false)
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/30 dark:bg-black/50 z-40"
            onClick={onClose}
          />
          <motion.div
            key="panel"
            initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="fixed inset-y-0 right-0 w-full sm:w-[480px] bg-paper-raised dark:bg-panel z-50
                       border-l border-slate-200 dark:border-slate-800 shadow-2xl overflow-y-auto"
          >
            <div className="sticky top-0 bg-paper-raised dark:bg-panel border-b border-slate-200 dark:border-slate-800 px-5 py-4 flex items-start justify-between gap-3 z-10">
              <div className="flex items-center gap-2.5">
                <Database size={16} className="text-teal-500 shrink-0" />
                <div>
                  <h3 className="font-display text-base font-semibold text-ink dark:text-slate-100">{title}</h3>
                  {subtitle && <p className="font-mono text-[10px] text-slate-500 mt-0.5">{subtitle}</p>}
                </div>
              </div>
              <button onClick={onClose} className="shrink-0 w-7 h-7 rounded-lg flex items-center justify-center text-slate-400 hover:text-ink dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
                <X size={15} />
              </button>
            </div>

            <div className="p-5 flex flex-col gap-5">
              {error && (
                <div className="text-xs text-red-500 font-mono bg-red-500/5 border border-red-500/20 rounded-lg px-3 py-2">{error}</div>
              )}

              <form onSubmit={handleAdd} className="flex flex-col gap-3">
                <h4 className="font-display text-xs font-medium text-ink dark:text-slate-200 flex items-center gap-1.5">
                  <Plus size={13} className="text-teal-500" /> Add a record
                </h4>
                <div className="grid grid-cols-2 gap-2.5">
                  {fields.map(f => {
                    const locked = lockedField?.key === f.key
                    if (f.type === 'checkbox') {
                      return (
                        <label key={f.key} className="flex items-center gap-2 col-span-2 font-mono text-[11px] text-slate-600 dark:text-slate-300">
                          <input
                            type="checkbox"
                            checked={!!form[f.key]}
                            onChange={e => setForm(s => ({ ...s, [f.key]: e.target.checked }))}
                            className="rounded border-slate-300 dark:border-slate-700"
                          />
                          {f.label}
                        </label>
                      )
                    }
                    return (
                      <label key={f.key} className="flex flex-col gap-1 font-mono text-[10px] text-slate-500">
                        {f.label}{f.required && <span className="text-rose-400"> *</span>}
                        <input
                          type={f.type}
                          step={f.step}
                          required={f.required}
                          disabled={locked}
                          value={form[f.key] ?? ''}
                          onChange={e => setForm(s => ({ ...s, [f.key]: e.target.value }))}
                          className={`rounded-lg border px-2.5 py-1.5 text-xs font-body text-ink dark:text-slate-100 bg-white dark:bg-panel-raised border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-1 focus:ring-teal-400 ${locked ? 'opacity-60 cursor-not-allowed' : ''}`}
                        />
                      </label>
                    )
                  })}
                </div>
                <button
                  type="submit"
                  disabled={submitting}
                  className="self-start mt-1 px-3.5 py-1.5 rounded-full bg-teal-500 hover:bg-teal-600 text-white text-[11px] font-mono disabled:opacity-50 transition-colors"
                >
                  {submitting ? 'Adding…' : 'Add record'}
                </button>
              </form>

              <div className="border-t border-slate-200 dark:border-slate-800 pt-4">
                <div className="flex items-center justify-between mb-2.5 gap-2">
                  <h4 className="font-display text-xs font-medium text-ink dark:text-slate-200">
                    Recent records {lockedField && <span className="text-slate-400 font-mono text-[10px] font-normal">— {lockedField.label}</span>}
                  </h4>
                  {clearAllRecords && records.length > 0 && !confirmingClear && (
                    <button
                      onClick={() => setConfirmingClear(true)}
                      className="font-mono text-[10px] text-slate-400 hover:text-rose-500 transition-colors shrink-0"
                    >
                      Clear {lockedField ? 'this entity\'s' : 'all'} data
                    </button>
                  )}
                </div>

                {confirmingClear && (
                  <div className="flex items-start gap-2 text-xs text-rose-600 dark:text-rose-400 font-mono bg-rose-500/5 border border-rose-500/20 rounded-lg px-3 py-2.5 mb-3">
                    <AlertTriangle size={14} className="shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <p>{lockedField ? `Delete every record for ${lockedField.label}` : 'Delete every record in this dataset'} — no replacement is loaded. This can't be undone.</p>
                      <div className="flex items-center gap-2 mt-2">
                        <button onClick={handleClearAll} disabled={clearing} className="px-3 py-1 rounded-full bg-rose-500 hover:bg-rose-600 text-white text-[10px] disabled:opacity-50">
                          {clearing ? 'Clearing…' : 'Yes, clear it'}
                        </button>
                        <button onClick={() => setConfirmingClear(false)} className="px-3 py-1 rounded-full border border-slate-300 dark:border-slate-700 text-slate-500 text-[10px]">
                          Cancel
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {loading && <div className="font-mono text-xs text-slate-500 animate-pulse-line py-4 text-center">loading…</div>}

                {!loading && records.length === 0 && (
                  <div className="font-mono text-[11px] text-slate-400 py-4 text-center">No records yet.</div>
                )}

                {!loading && records.length > 0 && (
                  <div className="flex flex-col gap-1.5 max-h-[380px] overflow-y-auto pr-1">
                    {records.map(r => (
                      <div key={r.id} className="flex items-center justify-between gap-2 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2">
                        <div className="min-w-0 flex-1">
                          <div className="font-mono text-[9px] text-slate-400">{fmtTime(r.timestamp)}</div>
                          <div className="font-mono text-[11px] text-ink dark:text-slate-200 truncate">
                            {columns.map(c => `${c.label}: ${c.format ? c.format(r[c.key], r) : r[c.key] ?? '—'}`).join('  ·  ')}
                          </div>
                        </div>
                        <button
                          onClick={() => handleDelete(r.id)}
                          className="shrink-0 w-7 h-7 rounded-lg flex items-center justify-center text-slate-400 hover:text-rose-500 hover:bg-rose-500/10 transition-colors"
                          title="Delete this record"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
