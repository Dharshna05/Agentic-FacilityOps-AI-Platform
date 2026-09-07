import { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { UploadCloud, X, CheckCircle2, AlertCircle, FileSpreadsheet } from 'lucide-react'

/**
 * Drop/browse a CSV or Excel file, upload it to the milestone's
 * /ingest/upload endpoint, and trigger a full dashboard refresh once the
 * backend confirms it re-scored everything from the new file. Every field
 * shown after upload (row count, affected entities) comes straight back
 * from the server — nothing here is a guess or a canned message.
 */
export default function DatasetUploadPanel({ open, onClose, title, subtitle, uploadFn, onUploaded, accentClass = 'teal' }) {
  const [file, setFile] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [status, setStatus] = useState('idle') // idle | uploading | done | error
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  const accent = {
    teal: { text: 'text-teal-600 dark:text-teal-400', border: 'border-teal-400/40', bg: 'bg-teal-500/5', btn: 'bg-teal-500 hover:bg-teal-600' },
    blue: { text: 'text-blue-600 dark:text-blue-400', border: 'border-blue-400/40', bg: 'bg-blue-500/5', btn: 'bg-blue-500 hover:bg-blue-600' },
    violet: { text: 'text-violet-600 dark:text-violet-400', border: 'border-violet-400/40', bg: 'bg-violet-500/5', btn: 'bg-violet-500 hover:bg-violet-600' },
    rose: { text: 'text-rose-600 dark:text-rose-400', border: 'border-rose-400/40', bg: 'bg-rose-500/5', btn: 'bg-rose-500 hover:bg-rose-600' },
  }[accentClass]

  function reset() {
    setFile(null); setStatus('idle'); setResult(null); setError(null)
  }

  function handleClose() {
    reset()
    onClose()
  }

  function pickFile(f) {
    if (!f) return
    const ok = /\.(csv|xlsx|xls)$/i.test(f.name)
    if (!ok) {
      setError('Only .csv, .xlsx, or .xls files are supported.')
      return
    }
    setFile(f)
    setError(null)
    setStatus('idle')
  }

  async function handleUpload() {
    if (!file) return
    setStatus('uploading')
    setError(null)
    try {
      const data = await uploadFn(file)
      setResult(data)
      setStatus('done')
      onUploaded?.()
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
      setStatus('error')
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/30 dark:bg-black/50 z-40"
            onClick={handleClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 10 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.96, y: 10 }}
            transition={{ type: 'spring', stiffness: 320, damping: 28 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div className="w-full max-w-lg bg-paper-raised dark:bg-panel border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-800 flex items-start justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <UploadCloud size={16} className={accent.text} />
                  <div>
                    <h3 className="font-display text-base font-semibold text-ink dark:text-slate-100">{title}</h3>
                    {subtitle && <p className="font-mono text-[10px] text-slate-500 mt-0.5">{subtitle}</p>}
                  </div>
                </div>
                <button onClick={handleClose} className="shrink-0 w-7 h-7 rounded-lg flex items-center justify-center text-slate-400 hover:text-ink dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
                  <X size={15} />
                </button>
              </div>

              <div className="p-5 flex flex-col gap-4">
                <div
                  onDragOver={e => { e.preventDefault(); setDragOver(true) }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={e => { e.preventDefault(); setDragOver(false); pickFile(e.dataTransfer.files?.[0]) }}
                  onClick={() => inputRef.current?.click()}
                  className={`rounded-xl border-2 border-dashed p-6 flex flex-col items-center gap-2 text-center cursor-pointer transition-colors
                             ${dragOver ? `${accent.border} ${accent.bg}` : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'}`}
                >
                  <input ref={inputRef} type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={e => pickFile(e.target.files?.[0])} />
                  {file ? (
                    <>
                      <FileSpreadsheet size={22} className={accent.text} />
                      <p className="font-mono text-xs text-ink dark:text-slate-200">{file.name}</p>
                      <p className="font-mono text-[10px] text-slate-400">{(file.size / 1024).toFixed(1)} KB — click or drop to replace</p>
                    </>
                  ) : (
                    <>
                      <UploadCloud size={22} className="text-slate-400" />
                      <p className="font-mono text-xs text-slate-500">Drop a .csv / .xlsx file here, or click to browse</p>
                      <p className="font-mono text-[10px] text-slate-400">Column names are auto-detected — no reformatting needed</p>
                    </>
                  )}
                </div>

                {error && (
                  <div className="flex items-start gap-2 text-xs text-red-500 font-mono bg-red-500/5 border border-red-500/20 rounded-lg px-3 py-2.5">
                    <AlertCircle size={14} className="shrink-0 mt-0.5" />
                    <span>{error}</span>
                  </div>
                )}

                {status === 'done' && result && (
                  <div className="flex items-start gap-2 text-xs text-emerald-600 dark:text-emerald-400 font-mono bg-emerald-500/5 border border-emerald-500/20 rounded-lg px-3 py-2.5">
                    <CheckCircle2 size={14} className="shrink-0 mt-0.5" />
                    <span>
                      Ingested {result.rows_ingested} row{result.rows_ingested === 1 ? '' : 's'}
                      {(result.assets_affected || result.zones_affected || result.access_points_affected) &&
                        ` across ${(result.assets_affected || result.zones_affected || result.access_points_affected).length} entit${(result.assets_affected || result.zones_affected || result.access_points_affected).length === 1 ? 'y' : 'ies'}`}
                      . Dashboard refreshed with your data.
                    </span>
                  </div>
                )}

                {status === 'done' && result?.note && (
                  <div className="flex items-start gap-2 text-xs text-amber-700 dark:text-amber-400 font-mono bg-amber-500/5 border border-amber-500/20 rounded-lg px-3 py-2.5">
                    <AlertCircle size={14} className="shrink-0 mt-0.5" />
                    <span>{result.note}</span>
                  </div>
                )}

                <button
                  onClick={handleUpload}
                  disabled={!file || status === 'uploading'}
                  className={`self-end px-4 py-2 rounded-full text-white text-xs font-mono disabled:opacity-40 disabled:cursor-not-allowed transition-colors ${accent.btn}`}
                >
                  {status === 'uploading' ? 'Uploading…' : 'Upload & recompute'}
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
