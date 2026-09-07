export default function SectionHeader({ title, subtitle, badge }) {
  return (
    <div className="flex items-end justify-between flex-wrap gap-2 mb-1">
      <div>
        <h2 className="font-display text-xl font-semibold text-ink dark:text-slate-100 tracking-tight">
          {title}
        </h2>
        {subtitle && (
          <p className="font-body text-xs text-slate-500 mt-1 max-w-3xl">{subtitle}</p>
        )}
      </div>
      {badge && (
        <span className="data-pill">
          {badge}
        </span>
      )}
    </div>
  )
}
