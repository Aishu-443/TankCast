import React, { useState, useEffect, useMemo } from 'react'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts'
import { fetchDemandForecast, IS_MOCK } from '../api/client'
import { MOCK_HOURLY_PREDICTIONS } from '../mocks/mockData'
import type { HourlyDemandPrediction, SimulationResult } from '../api/types'
import {
  calculateTankSimulation,
  formatHoursAndMinutes,
} from '../utils/tankSimulation'

export const TankSimulator: React.FC = () => {
  // 1. Simulation Inputs
  const [tankCapacity, setTankCapacity] = useState<number>(10000)
  const [currentLevel, setCurrentLevel] = useState<number>(6000)
  const [supplyDelayHours, setSupplyDelayHours] = useState<number>(4)
  const [meterCount, setMeterCount] = useState<number>(100)
  const [restoredSupplyRate, setRestoredSupplyRate] = useState<number>(1500)

  const [checkedInputs, setCheckedInputs] = useState({
    tankCapacity: 10000,
    currentLevel: 6000,
    supplyDelayHours: 4,
    meterCount: 100,
    restoredSupplyRate: 1500,
  })

  // 2. Forecast Data for Simulation
  const [predictions, setPredictions] = useState<HourlyDemandPrediction[]>([])
  const [loadingForecast, setLoadingForecast] = useState<boolean>(true)

  useEffect(() => {
    let isCancelled = false

    async function loadForecast() {
      try {
        const res = await fetchDemandForecast().catch(() => ({ predictions: [] }))
        if (!isCancelled) {
          if (res.predictions && res.predictions.length > 0) {
            setPredictions(res.predictions)
          } else {
            // Fallback to local mock predictions
            setPredictions(MOCK_HOURLY_PREDICTIONS)
          }
          setLoadingForecast(false)
        }
      } catch {
        if (!isCancelled) {
          setPredictions(MOCK_HOURLY_PREDICTIONS)
          setLoadingForecast(false)
        }
      }
    }

    loadForecast()

    return () => {
      isCancelled = true
    }
  }, [])

  // Validate the last submitted scenario.
  const isCapacityValid = checkedInputs.tankCapacity > 0
  const isCurrentLevelValid =
    checkedInputs.currentLevel >= 0 &&
    checkedInputs.currentLevel <= checkedInputs.tankCapacity
  const isMeterCountValid = checkedInputs.meterCount >= 0

  const validationError = useMemo(() => {
    if (checkedInputs.tankCapacity <= 0) return 'Tank capacity must be greater than 0 litres.'
    if (checkedInputs.currentLevel < 0) return 'Available water level cannot be negative.'
    if (checkedInputs.currentLevel > checkedInputs.tankCapacity) {
      return `Available water (${checkedInputs.currentLevel.toLocaleString()} L) cannot exceed tank capacity (${checkedInputs.tankCapacity.toLocaleString()} L).`
    }
    if (checkedInputs.meterCount < 0) return 'Equivalent meter count cannot be negative.'
    return null
  }, [checkedInputs])

  const hasPendingChanges =
    tankCapacity !== checkedInputs.tankCapacity ||
    currentLevel !== checkedInputs.currentLevel ||
    supplyDelayHours !== checkedInputs.supplyDelayHours ||
    meterCount !== checkedInputs.meterCount ||
    restoredSupplyRate !== checkedInputs.restoredSupplyRate

  // Run Simulation in real-time
  const simulation: SimulationResult = useMemo(() => {
    if (!isCapacityValid || !isCurrentLevelValid || !isMeterCountValid) {
      return {
        status: 'empty_now',
        hoursUntilEmpty: 0,
        deficitRisk: 'CRITICAL',
        message: validationError || 'Invalid inputs.',
        hourlyLevels: [],
      }
    }

    return calculateTankSimulation({
      capacityLiters: checkedInputs.tankCapacity,
      currentLevelLiters: checkedInputs.currentLevel,
      supplyDelayHours: checkedInputs.supplyDelayHours,
      meterCount: checkedInputs.meterCount,
      restoredSupplyRateLph: checkedInputs.restoredSupplyRate,
      forecastPredictions: predictions.length > 0 ? predictions : MOCK_HOURLY_PREDICTIONS,
    })
  }, [
    checkedInputs,
    predictions,
    isCapacityValid,
    isCurrentLevelValid,
    isMeterCountValid,
    validationError,
  ])

  // Quick preset handlers for tank percentage
  const setLevelByPercent = (pct: number) => {
    if (tankCapacity > 0) {
      setCurrentLevel(Math.round((tankCapacity * pct) / 100))
    }
  }

  // Risk Badge Styling
  const getRiskBadge = (risk: SimulationResult['deficitRisk']) => {
    switch (risk) {
      case 'CRITICAL':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-red-950/80 text-red-300 border border-red-700 animate-pulse">
            <span className="w-2 h-2 rounded-full bg-red-500" />
            CRITICAL DEFICIT RISK
          </span>
        )
      case 'HIGH':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-amber-950/80 text-amber-300 border border-amber-700">
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            HIGH SHORTAGE RISK
          </span>
        )
      case 'MEDIUM':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-yellow-950/80 text-yellow-300 border border-yellow-700">
            <span className="w-2 h-2 rounded-full bg-yellow-500" />
            MODERATE BUFFER
          </span>
        )
      case 'LOW':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-emerald-950/80 text-emerald-300 border border-emerald-700">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            STORAGE SECURE
          </span>
        )
    }
  }

  // Format chart data
  const chartData = useMemo(() => {
    return simulation.hourlyLevels.map((item, idx) => ({
      step: idx === 0 ? 'Now' : `+${idx}h`,
      hour: item.hour,
      levelLiters: item.levelLiters,
      percentage: item.percentage,
      inflowLiters: item.inflowLiters,
      demandLiters: item.demandLiters,
    }))
  }, [simulation.hourlyLevels])

  const criticalThresholdLitres = Math.round(checkedInputs.tankCapacity * 0.15)
  const warningThresholdLitres = Math.round(checkedInputs.tankCapacity * 0.3)

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-cyan-800/60 bg-slate-900 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Ready to check your water reserves?</p>
          <p className="text-xs text-slate-400 mt-1">
            {hasPendingChanges
              ? 'You changed inputs. Run the check to update the results.'
              : 'Results reflect the last checked scenario.'}
          </p>
        </div>
        <button
          type="button"
          disabled={loadingForecast}
          onClick={() => setCheckedInputs({
            tankCapacity,
            currentLevel,
            supplyDelayHours,
            meterCount,
            restoredSupplyRate,
          })}
          className="shrink-0 rounded-lg bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 disabled:cursor-wait px-5 py-3 text-sm font-bold text-slate-950 transition"
        >
          {loadingForecast ? 'Loading forecast?' : 'Run Shortage Check'}
        </button>
      </div>

      {hasPendingChanges && (
        <p role="status" className="text-xs text-amber-300">
          Scenario changed ? results below still reflect your previous check.
        </p>
      )}

      {/* 1. Key Simulation Outputs Banner */}
      <div className="rounded-xl bg-slate-950 border border-slate-800 p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
          <div>
            <span className="text-xs font-medium text-slate-400 block uppercase tracking-wider">
              Endurance Projection
            </span>
            <div className="text-3xl font-extrabold text-white mt-1 flex items-baseline gap-2">
              {simulation.hoursUntilEmpty !== null ? (
                <>
                  <span className={simulation.hoursUntilEmpty < 6 ? 'text-rose-400' : 'text-amber-300'}>
                    {formatHoursAndMinutes(simulation.hoursUntilEmpty)}
                  </span>
                  <span className="text-sm font-normal text-slate-400">until empty</span>
                </>
              ) : (
                <>
                  <span className="text-emerald-400">&gt; 24 Hours</span>
                  <span className="text-sm font-normal text-slate-400">exceeds forecast window</span>
                </>
              )}
            </div>
          </div>
          <div>{getRiskBadge(simulation.deficitRisk)}</div>
        </div>

        <p className="text-xs text-slate-300 leading-relaxed">
          {validationError ? (
            <span className="text-rose-400 font-semibold">{validationError}</span>
          ) : (
            simulation.message
          )}
        </p>

        {/* Quick status metrics row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1 text-xs">
          <div className="rounded-lg bg-slate-900/80 p-2.5 border border-slate-800">
            <span className="text-slate-400 block">Available Water</span>
            <span className="font-mono font-bold text-slate-100 text-sm">
              {checkedInputs.currentLevel.toLocaleString()} L
            </span>
            <span className="text-[10px] text-slate-400 block">
              ({checkedInputs.tankCapacity > 0 ? Math.round((checkedInputs.currentLevel / checkedInputs.tankCapacity) * 100) : 0}% of capacity)
            </span>
          </div>
          <div className="rounded-lg bg-slate-900/80 p-2.5 border border-slate-800">
            <span className="text-slate-400 block">Supply Delay</span>
            <span className="font-mono font-bold text-amber-400 text-sm">
              {checkedInputs.supplyDelayHours} Hours
            </span>
            <span className="text-[10px] text-slate-400 block">inflow withheld</span>
          </div>
          <div className="rounded-lg bg-slate-900/80 p-2.5 border border-slate-800">
            <span className="text-slate-400 block">Building Assumption</span>
            <span className="font-mono font-bold text-sky-400 text-sm">
              {checkedInputs.meterCount} Equiv. Meters
            </span>
            <span className="text-[10px] text-slate-400 block">scaling multiplier</span>
          </div>
          <div className="rounded-lg bg-slate-900/80 p-2.5 border border-slate-800">
            <span className="text-slate-400 block">Restored Inflow Rate</span>
            <span className="font-mono font-bold text-emerald-400 text-sm">
              {checkedInputs.restoredSupplyRate.toLocaleString()} L/h
            </span>
            <span className="text-[10px] text-slate-400 block">after delay</span>
          </div>
        </div>
      </div>

      {/* 2. Projected Water Level Trajectory Chart */}
      <div className="rounded-xl bg-slate-950/60 border border-slate-800 p-4 space-y-2">
        <div className="flex items-center justify-between text-xs pb-1">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-200">
              Projected Level Over Time
            </span>
            <span className="text-[10px] font-mono bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded">
              Litres vs Hours
            </span>
          </div>
          <div className="flex items-center gap-3 text-[11px] text-slate-400">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded bg-cyan-500 inline-block" />
              <span>Projected Level</span>
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 border-b border-rose-500 border-dashed inline-block" />
              <span>Critical (15%)</span>
            </span>
          </div>
        </div>

        <div className="w-full h-56 min-h-[220px]">
          {loadingForecast ? (
            <div className="h-full flex items-center justify-center text-xs text-slate-400">
              Loading simulation trajectory...
            </div>
          ) : chartData.length === 0 ? (
            <div className="h-full flex items-center justify-center text-xs text-slate-500">
              Adjust inputs to display projected storage curve.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
                <defs>
                  <linearGradient id="tankLevelGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.6} />
                    <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis
                  dataKey="step"
                  stroke="#64748b"
                  tick={{ fill: '#94a3b8', fontSize: 10 }}
                  interval="preserveStartEnd"
                />
                <YAxis
                  stroke="#64748b"
                  domain={[0, checkedInputs.tankCapacity > 0 ? checkedInputs.tankCapacity : 'auto']}
                  tick={{ fill: '#94a3b8', fontSize: 10 }}
                  tickFormatter={(val) => `${val >= 1000 ? `${(val / 1000).toFixed(0)}k` : val}L`}
                />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (!active || !payload || payload.length === 0) return null
                    const p = payload[0].payload as {
                      step: string
                      levelLiters: number
                      percentage: number
                      inflowLiters: number
                      demandLiters: number
                    }
                    return (
                      <div className="rounded-lg bg-slate-950 border border-slate-700 p-2.5 shadow-xl text-xs space-y-1">
                        <div className="font-semibold text-slate-200 border-b border-slate-800 pb-1">
                          Timeline: {label}
                        </div>
                        <div className="flex justify-between gap-4 text-cyan-400 font-mono">
                          <span>Level:</span>
                          <span className="font-bold">
                            {p.levelLiters.toLocaleString()} L ({p.percentage}%)
                          </span>
                        </div>
                        <div className="flex justify-between gap-4 text-amber-400 font-mono">
                          <span>Hourly Demand:</span>
                          <span>{p.demandLiters.toLocaleString()} L/h</span>
                        </div>
                        <div className="flex justify-between gap-4 text-emerald-400 font-mono">
                          <span>Hourly Inflow:</span>
                          <span>{p.inflowLiters.toLocaleString()} L/h</span>
                        </div>
                      </div>
                    )
                  }}
                />
                {/* 15% Critical Level Marker */}
                {criticalThresholdLitres > 0 && (
                  <ReferenceLine
                    y={criticalThresholdLitres}
                    stroke="#ef4444"
                    strokeDasharray="3 3"
                    label={{
                      value: '15% Critical',
                      fill: '#f87171',
                      fontSize: 9,
                      position: 'insideBottomRight',
                    }}
                  />
                )}
                {/* 30% Warning Level Marker */}
                {warningThresholdLitres > 0 && (
                  <ReferenceLine
                    y={warningThresholdLitres}
                    stroke="#f59e0b"
                    strokeDasharray="3 3"
                    label={{
                      value: '30% Warning',
                      fill: '#fbbf24',
                      fontSize: 9,
                      position: 'insideTopRight',
                    }}
                  />
                )}
                <Area
                  type="monotone"
                  dataKey="levelLiters"
                  stroke="#06b6d4"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#tankLevelGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* 3. Interactive Inputs Grid */}
      <div className="rounded-xl bg-slate-950 border border-slate-800 p-5 space-y-5">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Simulation Controls & Parameters
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* Input 1: Tank Capacity */}
          <div className="space-y-1.5">
            <label
              htmlFor="tank-capacity"
              className="text-xs font-medium text-slate-300 flex justify-between"
            >
              <span>Tank Total Capacity</span>
              <span className="text-slate-500 font-mono">Litres</span>
            </label>
            <input
              id="tank-capacity"
              type="number"
              min="1"
              step="500"
              value={tankCapacity}
              onChange={(e) => setTankCapacity(Math.max(1, Number(e.target.value)))}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 font-mono focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Input 2: Current Water Level */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-center text-xs">
              <label htmlFor="current-level" className="font-medium text-slate-300">
                Available Water in Tank
              </label>
              <div className="flex gap-1">
                {[25, 50, 75, 100].map((pct) => (
                  <button
                    key={pct}
                    type="button"
                    onClick={() => setLevelByPercent(pct)}
                    className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
                  >
                    {pct}%
                  </button>
                ))}
              </div>
            </div>
            <input
              id="current-level"
              type="number"
              min="0"
              max={tankCapacity}
              step="500"
              value={currentLevel}
              onChange={(e) => setCurrentLevel(Math.max(0, Number(e.target.value)))}
              className={`w-full bg-slate-900 border rounded-lg px-3 py-2 text-sm font-mono text-slate-100 focus:outline-none focus:ring-1 ${
                currentLevel > tankCapacity
                  ? 'border-rose-500 focus:ring-rose-500'
                  : 'border-slate-700 focus:ring-blue-500'
              }`}
            />
            {currentLevel > tankCapacity && (
              <span className="text-[11px] text-rose-400 block">
                Water cannot exceed capacity ({tankCapacity.toLocaleString()} L).
              </span>
            )}
          </div>

          {/* Input 3: Supply Delay Slider */}
          <div className="space-y-2 md:col-span-2 bg-slate-900/60 p-3.5 rounded-lg border border-slate-800/80">
            <div className="flex justify-between items-center">
              <div>
                <label
                  htmlFor="supply-delay-slider"
                  className="text-xs font-semibold text-slate-200 block"
                >
                  Supply Interruption / Delivery Delay
                </label>
                <span className="text-[11px] text-slate-400">
                  Simulates delayed tanker replenishment or municipal supply window shift
                </span>
              </div>
              <span className="font-mono font-bold text-sm text-amber-400 bg-amber-950/60 border border-amber-800/80 px-2.5 py-1 rounded">
                {supplyDelayHours === 0 ? '0h (Immediate Inflow)' : `${supplyDelayHours} Hours Delay`}
              </span>
            </div>
            <input
              id="supply-delay-slider"
              type="range"
              min="0"
              max="24"
              step="1"
              value={supplyDelayHours}
              onChange={(e) => setSupplyDelayHours(Number(e.target.value))}
              className="w-full accent-amber-500 cursor-pointer h-2 bg-slate-800 rounded-lg"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>0h (No delay)</span>
              <span>6h</span>
              <span>12h</span>
              <span>18h</span>
              <span>24h (Full-day outage)</span>
            </div>
          </div>

          {/* Input 4: Demand Scaling Assumption (Equivalent Meters) */}
          <div className="space-y-1.5">
            <label
              htmlFor="meter-count"
              className="text-xs font-medium text-slate-300 flex justify-between"
            >
              <span>Equivalent Residential Meters</span>
              <span className="text-slate-500 font-mono">Building Multiplier</span>
            </label>
            <input
              id="meter-count"
              type="number"
              min="1"
              step="10"
              value={meterCount}
              onChange={(e) => setMeterCount(Math.max(0, Number(e.target.value)))}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 font-mono focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <span className="text-[11px] text-slate-500 block">
              1 unit = 1 residential smart-meter rate. Scaling to whole hostel block.
            </span>
          </div>

          {/* Input 5: Restored Supply Inflow Rate */}
          <div className="space-y-1.5">
            <label
              htmlFor="restored-supply"
              className="text-xs font-medium text-slate-300 flex justify-between"
            >
              <span>Restored Replenishment Rate</span>
              <span className="text-slate-500 font-mono">Litres / Hour</span>
            </label>
            <input
              id="restored-supply"
              type="number"
              min="0"
              step="250"
              value={restoredSupplyRate}
              onChange={(e) => setRestoredSupplyRate(Math.max(0, Number(e.target.value)))}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 font-mono focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <span className="text-[11px] text-slate-500 block">
              Inflow delivered per hour once delay concludes.
            </span>
          </div>
        </div>
      </div>

      {/* 4. Explicit Assumptions & Scope Callout (Requirement 7) */}
      <div className="rounded-xl bg-slate-950/80 border border-amber-900/40 p-4 space-y-2">
        <div className="flex items-center gap-2 text-amber-400 text-xs font-semibold">
          <span>⚠️</span>
          <span>Explicit Simulation Assumptions & Prototype Boundaries</span>
        </div>
        <ul className="text-[11px] text-slate-400 space-y-1 list-disc list-inside leading-relaxed">
          <li>
            <strong className="text-slate-300">Smart-Meter Foundation:</strong> Demand estimates are trained on Spanish residential smart-meter data (DAIAD).
          </li>
          <li>
            <strong className="text-slate-300">Building Scaling:</strong> Scaling to a commercial or hostel building uses a user-defined meter-equivalent multiplier assumption, not live occupancy sensors.
          </li>
          <li>
            <strong className="text-slate-300">Manual Input Baseline:</strong> Tank level values and delivery schedules are user inputs for planning, not automated IoT telemetry.
          </li>
          {IS_MOCK && (
            <li className="text-amber-300/90 font-mono">
              <strong>Mock Mode:</strong> Operating with development mock data fixture parameters.
            </li>
          )}
        </ul>
      </div>
    </div>
  )
}
