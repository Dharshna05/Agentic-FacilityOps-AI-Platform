import { useMemo, useState } from 'react'
import Card from './Card'

const STATUS_COLOR = {
  Critical: '#f43f5e',
  Warning: '#f59e0b',
  Excellent: '#10b981',
  Good: '#2dd4bf',
}

// Critical/Warning assets draw last (on top) so they're never hidden behind
// a cluster of healthy ones — the whole point of the radar is to make the
// assets that need attention easy to find at a glance.
const DRAW_PRIORITY = { Good: 0, Excellent: 1, Warning: 2, Critical: 3 }

const SIZE = 320
const CENTER = SIZE / 2
const RADIUS = 118

export default function FleetHealthRadar({ assets, selectedAssetId, onSelect }) {
  const [hovered, setHovered] = useState(null)

  const points = useMemo(() => {
    if (!assets?.length) return []
    const withPos = assets.map((asset, index) => {
      const angle = (index / assets.length) * Math.PI * 2
      // Lower health = closer to center, so the eye is drawn inward toward
      // the assets that need attention rather than outward toward the
      // (usually larger) healthy majority.
      const distance = (1 - asset.health_score / 100) * RADIUS
      return {
        asset,
        x: CENTER + Math.cos(angle) * distance,
        y: CENTER + Math.sin(angle) * distance,
      }
    })
    return withPos.sort((a, b) => (DRAW_PRIORITY[a.asset.status] ?? 0) - (DRAW_PRIORITY[b.asset.status] ?? 0))
  }, [assets])

  const statusCounts = useMemo(() => {
    const counts = { Excellent: 0, Good: 0, Warning: 0, Critical: 0 }
    assets?.forEach((a) => { counts[a.status] = (counts[a.status] || 0) + 1 })
    return counts
  }, [assets])

  return (
    <Card title="Fleet Health Radar" badge={`${assets?.length ?? 0} assets`}>
      <div className="flex justify-center relative">
        <svg width={SIZE} height={SIZE}>
          <defs>
            <radialGradient id="radarGlow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#2dd4bf" stopOpacity="0.08" />
              <stop offset="100%" stopColor="#2dd4bf" stopOpacity="0" />
            </radialGradient>
          </defs>

          <circle cx={CENTER} cy={CENTER} r={RADIUS} fill="url(#radarGlow)" />
          <circle cx={CENTER} cy={CENTER} r={RADIUS} fill="none" stroke="#334155" strokeOpacity="0.5" strokeDasharray="4 5" />
          <circle cx={CENTER} cy={CENTER} r={RADIUS / 2} fill="none" stroke="#334155" strokeOpacity="0.35" strokeDasharray="4 5" />
          <text x={CENTER} y={CENTER - RADIUS - 6} textAnchor="middle" className="fill-slate-400" style={{ fontSize: 9, fontFamily: 'JetBrains Mono' }}>
            low health
          </text>
          <circle cx={CENTER} cy={CENTER} r="4" fill="#94a3b8" />

          {points.map(({ asset, x, y }) => {
            const isSelected = selectedAssetId === asset.asset_id
            const isHovered = hovered?.asset_id === asset.asset_id
            return (
              <g key={asset.asset_id}>
                {isSelected && (
                  <circle cx={x} cy={y} r="12" fill="none" stroke={STATUS_COLOR[asset.status]} strokeWidth="1.5" opacity="0.6" />
                )}
                <circle
                  cx={x}
                  cy={y}
                  r={isHovered || isSelected ? 8 : 5.5}
                  fill={STATUS_COLOR[asset.status] || '#2dd4bf'}
                  stroke="white"
                  strokeOpacity={isSelected ? 0.9 : 0.25}
                  strokeWidth={isSelected ? 2 : 1.25}
                  style={{ filter: `drop-shadow(0 0 5px ${STATUS_COLOR[asset.status]}80)`, cursor: 'pointer', transition: 'r 0.15s ease' }}
                  onMouseEnter={() => setHovered(asset)}
                  onMouseLeave={() => setHovered(null)}
                  onClick={() => onSelect?.(asset.asset_id)}
                />
              </g>
            )
          })}
        </svg>

        {hovered && (
          <div className="absolute top-2 left-2 bg-slate-900 text-white rounded-lg p-3 text-xs shadow-xl pointer-events-none max-w-[180px]">
            <p className="font-semibold mb-1">{hovered.name}</p>
            <p className="text-slate-300">{hovered.asset_type}</p>
            <p className="text-slate-300">Health: {hovered.health_score}%</p>
            <p className="text-slate-300">RUL: {hovered.predicted_rul_cycles} cycles</p>
            <p className="text-teal-300 mt-1 text-[10px]">click to inspect →</p>
          </div>
        )}
      </div>

      <div className="flex flex-wrap justify-center gap-x-4 gap-y-1.5 mt-4 mb-1">
        {[
          { label: 'Excellent', color: STATUS_COLOR.Excellent },
          { label: 'Good', color: STATUS_COLOR.Good },
          { label: 'Warning', color: STATUS_COLOR.Warning },
          { label: 'Critical', color: STATUS_COLOR.Critical },
        ].map((item) => (
          <div key={item.label} className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full" style={{ background: item.color, boxShadow: `0 0 4px ${item.color}99` }} />
            <span className="text-[10px] font-mono text-slate-500">
              {item.label} <span className="text-slate-400">({statusCounts[item.label] || 0})</span>
            </span>
          </div>
        ))}
      </div>

      <div className="text-[10px] text-slate-500 font-mono text-center">
        points closer to center = lower health · click a point to inspect
      </div>
    </Card>
  )
}
