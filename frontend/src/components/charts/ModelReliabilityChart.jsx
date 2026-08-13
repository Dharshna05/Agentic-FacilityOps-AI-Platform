import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts'


const R2_STYLE = {

  high: {
    label: 'RELIABLE',
    color: '#2DD4BF'
  },

  medium: {
    label: 'MODERATE',
    color: '#f0a860'
  },

  low: {
    label: 'LOW CONFIDENCE',
    color: '#ef4444'
  },

}



function bucketR2(r2) {

  if (r2 >= 0.7)
    return 'high'

  if (r2 >= 0.4)
    return 'medium'

  return 'low'

}



function CustomTooltip({ active, payload, unit }) {

  if (!active || !payload?.length)
    return null


  const {
    actual,
    predicted
  } = payload[0].payload



  return (

    <div
    className="
    bg-slate-900/95
    border
    border-slate-700
    rounded-lg
    px-3
    py-2
    font-mono
    text-[11px]
    text-white
    shadow-xl
    "
    >

      <div>
        actual:
        {' '}
        {actual}
        {' '}
        {unit}
      </div>


      <div>
        predicted:
        {' '}
        {predicted}
        {' '}
        {unit}
      </div>


    </div>

  )

}




export default function ModelReliabilityChart({
  title,
  subtitle,
  data,
  unit = ''
}) {


  if (!data?.points?.length) {

    return (

      <div
      className="
      bg-paper-raised
      dark:bg-panel
      border
      border-slate-200
      dark:border-slate-800
      rounded-xl
      p-5
      text-sm
      text-slate-500
      "
      >

        No model prediction data available yet.

      </div>

    )

  }



  const {
    points,
    r2,
    model
  } = data



  const bucket = bucketR2(r2)

  const style = R2_STYLE[bucket]



  const values = points.flatMap(
    p => [
      p.actual,
      p.predicted
    ]
  )



  const min = Math.min(...values)

  const max = Math.max(...values)


  const pad =
    (max - min) * 0.08 || 1



  const domain = [

    Math.floor(min - pad),

    Math.ceil(max + pad)

  ]



  return (

    <div
    className="
    bg-paper-raised
    dark:bg-panel

    border
    border-slate-200
    dark:border-slate-800

    rounded-xl

    p-5

    relative
    overflow-hidden

    hover:border-teal-500/30

    hover:shadow-lg

    transition-all

    duration-300

    "
    >



      {/* Header */}

      <div
      className="
      flex
      items-center
      justify-between
      mb-2
      gap-3
      flex-wrap
      "
      >


        <div
        className="
        flex
        items-center
        gap-2
        "
        >

          <h3
          className="
          font-display
          text-sm
          font-medium
          text-ink
          dark:text-slate-200
          tracking-wide
          "
          >

          {title}

          </h3>



          <span
          className="
          text-[9px]
          font-mono
          tracking-widest

          px-2
          py-0.5

          rounded-full

          bg-teal-500/10

          border
          border-teal-500/30

          text-teal-400
          "
          >

          AI MODEL

          </span>


        </div>




        <span

        className="
        font-mono
        text-[10px]
        tracking-widest
        px-2
        py-1
        rounded
        "

        style={{
          color:style.color,
          backgroundColor:`${style.color}20`
        }}

        >

        {style.label}
        {' · '}
        R² {r2}

        </span>


      </div>





      <p
      className="
      text-[11px]
      text-slate-500
      mb-4
      "
      >

      {subtitle}

      {' · model: '}

      <span
      className="
      font-mono
      "
      >

      {model}

      </span>


      </p>





      <ResponsiveContainer
      width="100%"
      height={300}
      >

        <ScatterChart
        margin={{
          top:10,
          right:20,
          bottom:10,
          left:5
        }}
        >


          <CartesianGrid
          strokeDasharray="2 4"
          className="
          stroke-slate-200
          dark:stroke-slate-800
          "
          />



          <XAxis

          type="number"

          dataKey="actual"

          domain={domain}

          tick={{
            fontSize:10,
            fontFamily:'JetBrains Mono'
          }}

          className="
          fill-slate-400
          "

          label={{
            value:`actual (${unit})`,
            position:'insideBottom',
            offset:-5,
            fontSize:10,
            fill:'#94a3b8'
          }}

          />




          <YAxis

          type="number"

          dataKey="predicted"

          domain={domain}

          tick={{
            fontSize:10,
            fontFamily:'JetBrains Mono'
          }}

          className="
          fill-slate-400
          "

          label={{
            value:`predicted (${unit})`,
            angle:-90,
            position:'insideLeft',
            fontSize:10,
            fill:'#94a3b8'
          }}

          />




          <ZAxis
          range={[35,35]}
          />



          <Tooltip
          content={
            <CustomTooltip
            unit={unit}
            />
          }

          cursor={{
            strokeDasharray:'3 3'
          }}

          />





          <ReferenceLine

          segment={[
            {
              x:domain[0],
              y:domain[0]
            },
            {
              x:domain[1],
              y:domain[1]
            }
          ]}

          stroke="#94a3b8"

          strokeDasharray="5 5"

          strokeWidth={1.5}


          label={{
            value:'perfect prediction',
            position:'insideTopRight',
            fontSize:9,
            fill:'#94a3b8'
          }}

          />





          <Scatter

          data={points}

          fill={style.color}

          fillOpacity={0.65}

          />



        </ScatterChart>


      </ResponsiveContainer>





      {/* Explanation */}

      <div
      className="
      mt-3
      text-[11px]
      font-mono
      text-slate-500
      leading-relaxed
      "
      >

      ● Points close to diagonal =
      accurate prediction

      <br/>

      ● Scattered points =
      higher prediction error

      </div>



    </div>

  )

}