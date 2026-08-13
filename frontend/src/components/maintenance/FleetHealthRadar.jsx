import { useState } from "react";

export default function FleetHealthRadar({ assets }) {

  const [hovered, setHovered] = useState(null);


  const size = 360;
  const center = size / 2;
  const radius = 130;


  const getColor = (status) => {

    if(status === "Critical")
      return "#f43f5e"; // rose-500

    if(status === "Warning")
      return "#f59e0b"; // amber-500

    if(status === "Excellent")
      return "#10b981"; // emerald-500

    return "#2dd4bf"; // teal-400 (Good)

  };


  const getPosition = (asset,index)=>{

    const angle =
      (index / assets.length) *
      Math.PI *
      2;


    // lower health = closer to center
    const distance =
      (asset.health_score / 100) *
      radius;


    return {

      x:
      center +
      Math.cos(angle) *
      distance,


      y:
      center +
      Math.sin(angle) *
      distance

    };

  };


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
    "
    >

      <h3
      className="
      font-display
      text-sm
      font-medium
      text-ink
      dark:text-slate-200
      mb-3
      "
      >
        Fleet Health Radar
      </h3>



      <div className="flex justify-center">


      <svg
      width={size}
      height={size}
      >

        <defs>
          <radialGradient id="radarGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#2dd4bf" stopOpacity="0.10" />
            <stop offset="100%" stopColor="#2dd4bf" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* Ambient glow */}
        <circle cx={center} cy={center} r={radius} fill="url(#radarGlow)" />

        {/* Outer circles */}

        <circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke="#334155"
        strokeDasharray="5 5"
        />


        <circle
        cx={center}
        cy={center}
        r={radius/2}
        fill="none"
        stroke="#334155"
        />


        {/* Center */}

        <circle
        cx={center}
        cy={center}
        r="5"
        fill="#94a3b8"
        />



        {
        assets?.map((asset,index)=>{


          const pos=getPosition(asset,index);


          return (

          <g key={asset.asset_id}>


            <circle

            cx={pos.x}
            cy={pos.y}

            r={hovered?.asset_id === asset.asset_id ? "9" : "7"}

            fill={
              getColor(asset.status)
            }

            stroke="white"
            strokeOpacity="0.25"
            strokeWidth="1.5"

            style={{
              filter: `drop-shadow(0 0 6px ${getColor(asset.status)}99)`
            }}

            className="
            cursor-pointer
            transition-all
            duration-200
            "

            onMouseEnter={()=>
              setHovered(asset)
            }

            onMouseLeave={()=>
              setHovered(null)
            }

            />

          </g>

          )

        })
        }



        {/* Tooltip */}

        {
        hovered && (

        <foreignObject
        x="10"
        y="10"
        width="170"
        height="120"
        >

        <div
        className="
        bg-slate-900
        text-white
        rounded-lg
        p-3
        text-xs
        shadow-xl
        "
        >

        <p className="font-bold">
        {hovered.name}
        </p>


        <p>
        Type:
        {hovered.asset_type}
        </p>


        <p>
        Health:
        {hovered.health_score}%
        </p>


        <p>
        RUL:
        {hovered.predicted_rul_cycles}
        cycles
        </p>


        </div>

        </foreignObject>

        )
        }


      </svg>


      </div>


      <div className="flex flex-wrap justify-center gap-x-4 gap-y-1.5 mt-4 mb-1">
        {[
          { label: "Excellent", color: "#10b981" },
          { label: "Good", color: "#2dd4bf" },
          { label: "Warning", color: "#f59e0b" },
          { label: "Critical", color: "#f43f5e" },
        ].map((item) => (
          <div key={item.label} className="flex items-center gap-1.5">
            <span
              className="w-2 h-2 rounded-full"
              style={{ background: item.color, boxShadow: `0 0 4px ${item.color}99` }}
            />
            <span className="text-[10px] font-mono text-slate-500">{item.label}</span>
          </div>
        ))}
      </div>

      <div
      className="
      text-xs
      text-slate-500
      font-mono
      text-center
      "
      >

      Points closer to center indicate lower health

      </div>


    </div>

  );

}