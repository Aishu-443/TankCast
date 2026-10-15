import React, { useEffect, useState, useCallback } from 'react'
import { fetchModelEvidence, IS_MOCK } from '../api/client'
import type { ModelEvidence } from '../api/types'

export const ModelEvidenceCard: React.FC = () => {
  const [evidence, setEvidence] = useState<ModelEvidence | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchModelEvidence()
      setEvidence(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load model evidence.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    let isCancelled = false

    async function initialFetch() {
      try {
        const data = await fetchModelEvidence()
        if (!isCancelled) {
          setEvidence(data)
          setLoading(false)
        }
      } catch (err) {
        if (!isCancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load model evidence.')
          setLoading(false)
        }
      }
    }

    initialFetch()

    return () => {
      isCancelled = true
    }
  }, [])

  return (
    <div className="space-y-4">
      {/* Evidence Subheader Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs pb-1 border-b border-slate-800/80">
        <span className="text-slate-400">
          Model Verification &amp; Evaluation Benchmarks
        </span>
        {IS_MOCK ? (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-amber-950/80 text-amber-300 border border-amber-800">
            MOCK / DEMO EVIDENCE
          </span>
        ) : evidence?.isVerified ? (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-emerald-950/80 text-emerald-300 border border-emerald-800">
            VERIFIED TRAINING LOG
          </span>
        ) : (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-slate-800 text-slate-300 border border-slate-700">
            UNCONFIRMED EVIDENCE
          </span>
        )}
      </div>

      {/* Loading state */}
      {loading && (
        <div className="h-44 flex flex-col items-center justify-center text-slate-400 space-y-2">
          <div className="w-5 h-5 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs">Loading model evidence metrics...</span>
        </div>
      )}

      {/* Error state */}
      {!loading && error && (
        <div className="h-44 flex flex-col items-center justify-center text-rose-400 space-y-2 p-4 text-center">
          <span className="text-sm font-semibold">Unable to load model evidence</span>
          <span className="text-xs text-slate-400">{error}</span>
          <button
            onClick={loadData}
            type="button"
            className="mt-2 px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded border border-slate-700 transition"
          >
            Retry
          </button>
        </div>
      )}

      {/* Main Evidence Content */}
      {!loading && !error && evidence && (
        <div className="space-y-4">
          {/* 1. Core Model Metadata */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div className="rounded-lg bg-slate-950 p-3 border border-slate-800">
              <span className="text-slate-400 block text-[11px]">Model Identifier</span>
              <span className="font-mono font-semibold text-slate-200 break-all">
                {evidence.modelName || 'Not available'}
              </span>
              <span className="text-[10px] text-slate-400 block mt-0.5">
                {evidence.modelType || 'RandomForestRegressor'}
              </span>
            </div>

            <div className="rounded-lg bg-slate-950 p-3 border border-slate-800">
              <span className="text-slate-400 block text-[11px]">Prediction Horizon &amp; Target</span>
              <span className="font-mono font-semibold text-slate-200">
                {evidence.horizonHours ? `${evidence.horizonHours}-Hour Ahead` : 'Not available'}
              </span>
              <span className="text-[10px] text-slate-400 block mt-0.5">
                Target: {evidence.targetUnit || 'litres per meter per hour'}
              </span>
            </div>
          </div>

          {/* 2. Evaluation Metrics (MAE, RMSE, Baseline) */}
          <div className="rounded-lg bg-slate-950 p-4 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                Holdout Evaluation Metrics (Chronological Test Split)
              </h3>
              <span className="text-[10px] font-mono text-slate-400">
                Untouched 20% holdout
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {/* MAE */}
              <div className="bg-slate-900/80 p-3 rounded border border-slate-800">
                <span className="text-[11px] text-slate-400 block">MAE (Mean Absolute Error)</span>
                {evidence.mae !== null && evidence.mae !== undefined ? (
                  <span className="text-lg font-mono font-bold text-sky-400">
                    {evidence.mae.toFixed(2)}{' '}
                    <span className="text-xs font-normal text-slate-400">L/meter/h</span>
                  </span>
                ) : (
                  <span className="text-xs text-slate-500 italic">Not available</span>
                )}
                <span className="text-[10px] text-slate-400 block mt-1">Average forecast miss</span>
              </div>

              {/* RMSE */}
              <div className="bg-slate-900/80 p-3 rounded border border-slate-800">
                <span className="text-[11px] text-slate-400 block">RMSE (Root Mean Squared Error)</span>
                {evidence.rmse !== null && evidence.rmse !== undefined ? (
                  <span className="text-lg font-mono font-bold text-purple-400">
                    {evidence.rmse.toFixed(2)}{' '}
                    <span className="text-xs font-normal text-slate-400">L/meter/h</span>
                  </span>
                ) : (
                  <span className="text-xs text-slate-500 italic">Not available</span>
                )}
                <span className="text-[10px] text-slate-400 block mt-1">Penalizes large spikes</span>
              </div>

              {/* MAPE */}
              <div className="bg-slate-900/80 p-3 rounded border border-slate-800 col-span-2 sm:col-span-1">
                <span className="text-[11px] text-slate-400 block">MAPE (Percentage Error)</span>
                {evidence.mape !== null && evidence.mape !== undefined ? (
                  <span className="text-lg font-mono font-bold text-slate-200">
                    {evidence.mape.toFixed(1)}%
                  </span>
                ) : (
                  <span className="text-xs text-slate-400 font-mono">
                    Not reported
                  </span>
                )}
                <span className="text-[10px] text-slate-400 block mt-1">
                  Omitted to avoid zero-flow division bias
                </span>
              </div>
            </div>

            {/* Baseline Comparison Card */}
            {evidence.metrics?.baselineMae ? (
              <div className="rounded bg-slate-900/60 p-3 border border-slate-800/80 space-y-1.5 text-xs">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                  <span className="font-semibold text-slate-300">
                    Benchmark: {evidence.metrics.baselineName || 'Persistence Baseline'}
                  </span>
                  {evidence.metrics.improvementOverBaselinePct && (
                    <span className="font-mono text-emerald-400 font-bold bg-emerald-950/70 border border-emerald-800 px-2 py-0.5 rounded text-[11px]">
                      +{evidence.metrics.improvementOverBaselinePct.toFixed(1)}% MAE Improvement
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Compared against 24-hour persistence baseline (same hour yesterday) evaluated on identical holdout intervals: Baseline MAE of{' '}
                  <strong className="text-slate-300 font-mono">{evidence.metrics.baselineMae.toFixed(2)} L/meter/h</strong> vs Random Forest MAE of{' '}
                  <strong className="text-sky-300 font-mono">{evidence.mae?.toFixed(2)} L/meter/h</strong>.
                </p>
              </div>
            ) : (
              <div className="text-[11px] text-slate-500 italic p-2 bg-slate-900/40 rounded">
                Baseline comparison metric not available for this run.
              </div>
            )}
          </div>

          {/* 3. Training & Evaluation Split Info */}
          {evidence.dataSplit && (
            <div className="rounded-lg bg-slate-950 p-3.5 border border-slate-800 text-xs space-y-1.5">
              <span className="font-semibold text-slate-300 block text-[11px] uppercase tracking-wider">
                Chronological Data Split
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] font-mono text-slate-400">
                <div>
                  <span className="text-slate-400">Train Period:</span>{' '}
                  <span className="text-slate-200">{evidence.dataSplit.trainPeriod}</span>{' '}
                  {evidence.dataSplit.trainRows && `(${evidence.dataSplit.trainRows.toLocaleString()} rows)`}
                </div>
                <div>
                  <span className="text-slate-400">Test Period:</span>{' '}
                  <span className="text-slate-200">{evidence.dataSplit.testPeriod}</span>{' '}
                  {evidence.dataSplit.testRows && `(${evidence.dataSplit.testRows.toLocaleString()} rows)`}
                </div>
              </div>
            </div>
          )}

          {/* 4. Limitations & Boundary Conditions */}
          <div className="rounded-lg bg-slate-950/90 border border-amber-900/40 p-4 space-y-2 text-xs">
            <span className="font-semibold text-amber-300 block flex items-center gap-1.5">
              <span>⚠️</span>
              <span>Dataset Scope &amp; Engineering Limitations</span>
            </span>
            <ul className="text-[11px] text-slate-400 space-y-1 list-disc list-inside leading-relaxed">
              {evidence.limitations && evidence.limitations.length > 0 ? (
                evidence.limitations.map((lim, idx) => (
                  <li key={idx}>
                    <span className="text-slate-300">{lim}</span>
                  </li>
                ))
              ) : (
                <>
                  <li>Trained on Spanish residential smart-meter data (DAIAD); climate and demographics differ from Indian hostels.</li>
                  <li>Per-meter estimates require user-set equivalent meter assumptions to scale to a building.</li>
                  <li>Does not incorporate weather, temperature, or college schedule/occupancy features.</li>
                  <li>Tank values in TankCast are manual simulation inputs, not automated live sensors.</li>
                </>
              )}
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}
