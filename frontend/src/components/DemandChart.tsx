import React, { useEffect, useState, useMemo, useCallback } from 'react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from 'recharts'
import { fetchDemandForecast, fetchHistoricalActuals, IS_MOCK } from '../api/client'
import type { HistoricalDataPoint, HourlyDemandPrediction } from '../api/types'

interface MergedChartPoint {
  rawTimestamp: string
  displayTime: string
  hour: number
  historical: number | null
  forecast: number | null
  lowerBound?: number | null
  upperBound?: number | null
  isCutoff?: boolean
  scaledHistorical?: number | null
  scaledForecast?: number | null
}

const formatDateTime = (isoString: string): string => {
  const d = new Date(isoString)
  if (isNaN(d.getTime())) return isoString
  const month = d.toLocaleString('en-US', { month: 'short' })
  const day = d.getDate()
  const hours = String(d.getHours()).padStart(2, '0')
  const mins = String(d.getMinutes()).padStart(2, '0')
  return `${month} ${day}, ${hours}:${mins}`
}

interface CustomTooltipProps {
  active?: boolean
  label?: string
  payload?: readonly unknown[]
  chartData: MergedChartPoint[]
  cutoffTimestamp: string | null
}

const CustomTooltip: React.FC<CustomTooltipProps> = ({
  active,
  label,
  chartData,
  cutoffTimestamp,
}) => {
  if (!active || !label) return null

  const point = chartData.find((p) => p.displayTime === label)
  if (!point) return null

  const isAtCutoff = point.isCutoff || point.rawTimestamp === cutoffTimestamp

  return (
    <div className="rounded-lg bg-slate-950 border border-slate-700 p-3 shadow-xl text-xs space-y-2 max-w-xs">
      <div className="font-semibold text-slate-200 border-b border-slate-800 pb-1 flex justify-between items-center gap-2">
        <span>{label}</span>
        {isAtCutoff && (
          <span className="text-[10px] bg-rose-950/80 text-rose-300 border border-rose-800/80 px-1.5 py-0.5 rounded font-mono">
            Cutoff Marker
          </span>
        )}
      </div>

      {point.historical !== null && point.historical !== undefined && (
        <div className="flex items-center justify-between gap-3 text-sky-400">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-sky-400 inline-block" />
            <span>Historical Actual:</span>
          </span>
          <span className="font-mono font-bold">{point.historical.toFixed(2)} L/meter/h</span>
        </div>
      )}

      {point.forecast !== null && point.forecast !== undefined && (
        <div className="flex flex-col gap-1 text-amber-400">
          <div className="flex items-center justify-between gap-3">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-1 border-b-2 border-dashed border-amber-400 inline-block" />
              <span>Forecast Prediction:</span>
            </span>
            <span className="font-mono font-bold">{point.forecast.toFixed(2)} L/meter/h</span>
          </div>
          {IS_MOCK && (
            <span className="text-[10px] text-amber-300/80 font-mono italic">
              * MOCK DATA, not model output
            </span>
          )}
        </div>
      )}

      {isAtCutoff && (
        <p className="text-[10px] text-rose-300/90 pt-1 border-t border-slate-800 italic">
          Transition: Left of cutoff is historical actuals; right is model forecast.
        </p>
      )}
    </div>
  )
}

export const DemandChart: React.FC = () => {
  const [historicalPoints, setHistoricalPoints] = useState<HistoricalDataPoint[]>([])
  const [forecastPoints, setForecastPoints] = useState<HourlyDemandPrediction[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [cutoffTimestamp, setCutoffTimestamp] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [histRes, forecastRes] = await Promise.all([
        fetchHistoricalActuals().catch((err) => {
          console.warn('Historical actuals fetch notice:', err)
          return { points: [] }
        }),
        fetchDemandForecast().catch((err) => {
          console.warn('Forecast fetch notice:', err)
          return { predictions: [] }
        }),
      ])

      setHistoricalPoints(histRes.points || [])
      setForecastPoints(forecastRes.predictions || [])

      if (forecastRes.predictions && forecastRes.predictions.length > 0) {
        setCutoffTimestamp(forecastRes.predictions[0].timestamp)
      } else if (histRes.points && histRes.points.length > 0) {
        setCutoffTimestamp(histRes.points[histRes.points.length - 1].timestamp)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load chart data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    let isCancelled = false

    async function initialFetch() {
      try {
        const [histRes, forecastRes] = await Promise.all([
          fetchHistoricalActuals().catch((err) => {
            console.warn('Historical actuals fetch notice:', err)
            return { points: [] }
          }),
          fetchDemandForecast().catch((err) => {
            console.warn('Forecast fetch notice:', err)
            return { predictions: [] }
          }),
        ])

        if (!isCancelled) {
          setHistoricalPoints(histRes.points || [])
          setForecastPoints(forecastRes.predictions || [])

          if (forecastRes.predictions && forecastRes.predictions.length > 0) {
            setCutoffTimestamp(forecastRes.predictions[0].timestamp)
          } else if (histRes.points && histRes.points.length > 0) {
            setCutoffTimestamp(histRes.points[histRes.points.length - 1].timestamp)
          }
          setLoading(false)
        }
      } catch (err) {
        if (!isCancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load chart data')
          setLoading(false)
        }
      }
    }

    initialFetch()

    return () => {
      isCancelled = true
    }
  }, [])

  // Merge historical and forecast points into a unified chronological array for Recharts
  const chartData = useMemo<MergedChartPoint[]>(() => {
    const pointMap = new Map<string, MergedChartPoint>()

    // Process historical points
    for (const h of historicalPoints) {
      pointMap.set(h.timestamp, {
        rawTimestamp: h.timestamp,
        displayTime: formatDateTime(h.timestamp),
        hour: h.hour,
        historical: h.actualLitersPerMeter,
        forecast: null,
        scaledHistorical: h.scaledBuildingLiters,
        scaledForecast: null,
      })
    }

    // Process forecast points
    for (const f of forecastPoints) {
      const existing = pointMap.get(f.timestamp)
      if (existing) {
        // At the cutoff boundary, both historical and forecast may exist
        existing.forecast = f.predictedLitersPerMeter
        existing.scaledForecast = f.totalScaledDemandLiters
        existing.lowerBound = f.lowerBoundLiters ?? null
        existing.upperBound = f.upperBoundLiters ?? null
        existing.isCutoff = true
      } else {
        pointMap.set(f.timestamp, {
          rawTimestamp: f.timestamp,
          displayTime: formatDateTime(f.timestamp),
          hour: f.hour,
          historical: null,
          forecast: f.predictedLitersPerMeter,
          scaledHistorical: null,
          scaledForecast: f.totalScaledDemandLiters,
          lowerBound: f.lowerBoundLiters ?? null,
          upperBound: f.upperBoundLiters ?? null,
        })
      }
    }

    // Sort chronologically
    return Array.from(pointMap.values()).sort(
      (a, b) => new Date(a.rawTimestamp).getTime() - new Date(b.rawTimestamp).getTime(),
    )
  }, [historicalPoints, forecastPoints])

  // Locate cutoff display label
  const cutoffLabel = useMemo(() => {
    if (!cutoffTimestamp) return null
    const found = chartData.find((p) => p.rawTimestamp === cutoffTimestamp)
    return found ? found.displayTime : null
  }, [chartData, cutoffTimestamp])

  return (
    <div className="space-y-4">
      {/* Chart Subheader / Legend Badges */}
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 text-sky-400">
            <span className="w-3 h-0.5 bg-sky-400 inline-block" />
            <span className="font-medium">Historical Actuals (Solid)</span>
          </span>
          <span className="flex items-center gap-1.5 text-amber-400">
            <span className="w-3 border-b-2 border-dashed border-amber-400 inline-block" />
            <span className="font-medium">Forecast Predictions (Dashed)</span>
          </span>
        </div>

        <div className="flex items-center gap-2">
          {IS_MOCK ? (
            <span className="px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-amber-950/70 text-amber-300 border border-amber-800">
              MOCK FORECAST DATA
            </span>
          ) : (
            <span className="px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-emerald-950/70 text-emerald-300 border border-emerald-800">
              MODEL PREDICTIONS
            </span>
          )}
        </div>
      </div>

      {/* Main Chart Area */}
      <div className="w-full h-80 min-h-[320px] bg-slate-950/40 rounded-lg p-2 border border-slate-800/80">
        {loading ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-400 space-y-2">
            <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-xs">Loading demand timeline data...</span>
          </div>
        ) : error ? (
          <div className="h-full flex flex-col items-center justify-center text-rose-400 space-y-2 p-4 text-center">
            <span className="text-sm font-semibold">Unable to load demand chart</span>
            <span className="text-xs text-slate-400">{error}</span>
            <button
              onClick={loadData}
              type="button"
              className="mt-2 px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded border border-slate-700 transition"
            >
              Retry
            </button>
          </div>
        ) : chartData.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 text-xs">
            No demand data available to display.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={{ top: 20, right: 30, left: 15, bottom: 25 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis
                dataKey="displayTime"
                stroke="#64748b"
                tick={{ fill: '#94a3b8', fontSize: 10 }}
                interval="preserveStartEnd"
                label={{
                  value: 'Timeline (Date & Hour)',
                  position: 'insideBottom',
                  offset: -15,
                  fill: '#94a3b8',
                  fontSize: 11,
                }}
              />
              <YAxis
                stroke="#64748b"
                tick={{ fill: '#94a3b8', fontSize: 10 }}
                label={{
                  value: 'Demand (litres per meter per hour)',
                  angle: -90,
                  position: 'insideLeft',
                  offset: 0,
                  fill: '#94a3b8',
                  fontSize: 11,
                  style: { textAnchor: 'middle' },
                }}
              />
              <Tooltip
                content={
                  <CustomTooltip
                    chartData={chartData}
                    cutoffTimestamp={cutoffTimestamp}
                  />
                }
              />
              <Legend
                verticalAlign="top"
                align="right"
                wrapperStyle={{ paddingBottom: '10px', fontSize: '11px' }}
              />

              {/* Vertical Cutoff Marker separating historical from forecast */}
              {cutoffLabel && (
                <ReferenceLine
                  x={cutoffLabel}
                  stroke="#f43f5e"
                  strokeWidth={2}
                  strokeDasharray="4 4"
                  label={{
                    value: 'Forecast Cutoff (Now)',
                    position: 'top',
                    fill: '#fda4af',
                    fontSize: 10,
                    fontWeight: 700,
                  }}
                />
              )}

              {/* Solid line for historical actuals */}
              <Line
                type="monotone"
                dataKey="historical"
                name="Historical Actuals (L/meter/h)"
                stroke="#38bdf8"
                strokeWidth={2.5}
                dot={{ r: 2.5, fill: '#38bdf8' }}
                activeDot={{ r: 5, fill: '#38bdf8' }}
                connectNulls={false}
              />

              {/* Dashed line for forecast predictions */}
              <Line
                type="monotone"
                dataKey="forecast"
                name={
                  IS_MOCK
                    ? 'Forecast (Mock Model - L/meter/h)'
                    : 'Forecast (Model - L/meter/h)'
                }
                stroke="#f59e0b"
                strokeWidth={2.5}
                strokeDasharray="6 6"
                dot={{ r: 2.5, fill: '#f59e0b' }}
                activeDot={{ r: 5, fill: '#f59e0b' }}
                connectNulls={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Axis & Units Clarification Footnote */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between text-[11px] text-slate-400 gap-1 pt-1">
        <span>
          <strong className="text-slate-300">Unit:</strong> Litres per residential smart meter per hour (L/meter/h).
        </span>
        <span className="italic text-slate-500">
          Cutoff marker delineates recorded past vs model forecast window.
        </span>
      </div>
    </div>
  )
}
