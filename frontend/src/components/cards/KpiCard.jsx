const ACCENT_STYLES = {

  teal: {
    bar: 'bg-teal-500/50',
    text: 'text-teal-600 dark:text-teal-400',
    glow: 'hover:shadow-teal-500/10'
  },

  blue: {
    bar: 'bg-blue-500/50',
    text: 'text-blue-600 dark:text-blue-400',
    glow: 'hover:shadow-blue-500/10'
  },

  violet: {
    bar: 'bg-violet-500/50',
    text: 'text-violet-600 dark:text-violet-400',
    glow: 'hover:shadow-violet-500/10'
  },

  emerald: {
    bar: 'bg-emerald-500/50',
    text: 'text-emerald-600 dark:text-emerald-400',
    glow: 'hover:shadow-emerald-500/10'
  },

  amber: {
    bar: 'bg-amber-500/50',
    text: 'text-amber-600 dark:text-signal',
    glow: 'hover:shadow-amber-500/10'
  },

  alert: {
    bar: 'bg-rose-500/60',
    text: 'text-rose-600 dark:text-rose-400',
    glow: 'hover:shadow-rose-500/10'
  },

  neutral: {
    bar: 'bg-navy/40',
    text: 'text-ink dark:text-slate-200',
    glow: 'hover:shadow-slate-500/10'
  }

}



export default function KpiCard({
  label,
  value,
  unit,
  trend,
  accent="teal"
}) {


  const style =
    ACCENT_STYLES[accent] ||
    ACCENT_STYLES.teal;



  const trendUp = trend > 0;



  return (

    <div
    className={`
    bg-paper-raised
    dark:bg-panel

    border
    border-slate-200
    dark:border-slate-800

    rounded-xl

    p-5

    flex
    flex-col

    gap-2

    relative

    overflow-hidden

    transition-all
    duration-300

    hover:-translate-y-1

    hover:shadow-xl

    ${style.glow}

    `}
    >


      {/* Accent line */}

      <div
      className={`
      absolute
      top-0
      left-0
      w-full
      h-[3px]

      ${style.bar}
      `}
      />



      {/* Label */}

      <span
      className="
      font-mono
      text-[10px]
      uppercase
      tracking-[0.2em]
      text-slate-500
      "
      >

      {label}

      </span>



      {/* Value */}

      <div
      className="
      flex
      items-baseline
      gap-1.5
      "
      >

        <span
        className={`
        font-display
        text-3xl
        font-semibold

        ${style.text}
        `}
        >

        {value}

        </span>


        {
        unit &&
        <span
        className="
        font-mono
        text-xs
        text-slate-400
        "
        >
          {unit}
        </span>
        }


      </div>




      {/* Trend */}

      {
      trend !== undefined && (

        <span
        className={`
        font-mono
        text-[10px]

        ${
        trendUp
        ?
        'text-amber-600 dark:text-signal'
        :
        'text-teal-600 dark:text-teal-400'
        }

        `}
        >

        {trendUp ? '▲' : '▼'}

        {" "}

        {Math.abs(trend)}% vs prev period

        </span>

      )
      }



    </div>

  )

}