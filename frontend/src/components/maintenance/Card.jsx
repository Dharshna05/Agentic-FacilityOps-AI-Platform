export default function Card({ title, badge, className = '', children }) {
  return (
    <div className={`surface-card p-5 ${className}`}>
      {(title || badge) && (
        <div className="flex items-center justify-between mb-4 gap-2">
          {title && <h3 className="font-display text-sm font-medium text-ink dark:text-slate-200">{title}</h3>}
          {badge && <span className="data-pill shrink-0">{badge}</span>}
        </div>
      )}
      {children}
    </div>
  )
}
