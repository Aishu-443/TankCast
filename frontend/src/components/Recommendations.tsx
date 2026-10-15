import React, { useEffect, useState, useCallback } from 'react'
import { fetchRecommendations, IS_MOCK } from '../api/client'
import type { Recommendation, RecommendationPriority, RecommendationCategory } from '../api/types'

export const Recommendations: React.FC = () => {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchRecommendations()
      setRecommendations(data || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load recommendations.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    let isCancelled = false

    async function initialFetch() {
      try {
        const data = await fetchRecommendations()
        if (!isCancelled) {
          setRecommendations(data || [])
          setLoading(false)
        }
      } catch (err) {
        if (!isCancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load recommendations.')
          setLoading(false)
        }
      }
    }

    initialFetch()

    return () => {
      isCancelled = true
    }
  }, [])

  const getPriorityBadge = (priority: RecommendationPriority) => {
    switch (priority) {
      case 'urgent':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-red-950/80 text-red-300 border border-red-700">
            Urgent Action
          </span>
        )
      case 'high':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-orange-950/80 text-orange-300 border border-orange-700">
            High Priority
          </span>
        )
      case 'medium':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-yellow-950/80 text-yellow-300 border border-yellow-700">
            Medium Priority
          </span>
        )
      case 'low':
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-slate-800 text-slate-300 border border-slate-700">
            Low Priority
          </span>
        )
    }
  }

  const getCategoryBadge = (category?: RecommendationCategory) => {
    switch (category) {
      case 'refill':
        return (
          <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/60 border border-cyan-800/80 px-2 py-0.5 rounded">
            Inflow / Supply
          </span>
        )
      case 'conservation':
        return (
          <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 border border-emerald-800/80 px-2 py-0.5 rounded">
            Demand Shifting
          </span>
        )
      case 'alert':
        return (
          <span className="text-[10px] font-mono text-amber-400 bg-amber-950/60 border border-amber-800/80 px-2 py-0.5 rounded">
            Audit & Alert
          </span>
        )
      case 'maintenance':
      default:
        return (
          <span className="text-[10px] font-mono text-slate-400 bg-slate-900 border border-slate-700 px-2 py-0.5 rounded">
            Maintenance
          </span>
        )
    }
  }

  return (
    <div className="space-y-4">
      {/* Header Context Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs pb-1 border-b border-slate-800/80">
        <span className="text-slate-400">
          Shortage Mitigation &amp; Operational Advisories
        </span>
        {IS_MOCK ? (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-amber-950/80 text-amber-300 border border-amber-800">
            MOCK RECOMMENDATIONS (Demo)
          </span>
        ) : (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-emerald-950/80 text-emerald-300 border border-emerald-800">
            OPERATIONAL ADVISORIES
          </span>
        )}
      </div>

      {/* Loading state */}
      {loading && (
        <div className="h-44 flex flex-col items-center justify-center text-slate-400 space-y-2">
          <div className="w-5 h-5 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs">Evaluating operational advisories...</span>
        </div>
      )}

      {/* Error state */}
      {!loading && error && (
        <div className="h-44 flex flex-col items-center justify-center text-rose-400 space-y-2 p-4 text-center">
          <span className="text-sm font-semibold">Unable to load recommendations</span>
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

      {/* Empty state */}
      {!loading && !error && recommendations.length === 0 && (
        <div className="h-44 flex flex-col items-center justify-center text-slate-500 text-xs text-center p-4">
          <span className="text-lg mb-1">✅</span>
          <span className="font-semibold text-slate-400">No active shortage advisories</span>
          <span className="text-[11px] text-slate-500 mt-1">
            Current water balance and projected demand indicate safe reservoir buffer.
          </span>
        </div>
      )}

      {/* Recommendations Cards List */}
      {!loading && !error && recommendations.length > 0 && (
        <div className="space-y-3">
          {recommendations.map((rec) => (
            <article
              key={rec.id}
              className="rounded-lg bg-slate-950 border border-slate-800/90 p-4 space-y-2.5 transition hover:border-slate-700"
            >
              {/* Card Title & Badges */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold text-sm text-slate-100">
                    {rec.title}
                  </h3>
                </div>
                <div className="flex items-center gap-2">
                  {getCategoryBadge(rec.category)}
                  {getPriorityBadge(rec.priority)}
                </div>
              </div>

              {/* Action Directive */}
              <div className="text-xs text-slate-200 bg-slate-900/70 p-2.5 rounded border border-slate-800/80">
                <span className="font-bold text-sky-400 block mb-0.5">Recommended Action:</span>
                <p className="leading-relaxed">{rec.action}</p>
              </div>

              {/* Why this recommendation is suggested (Available context) */}
              {(rec.explanation || rec.triggerReason) && (
                <div className="text-[11px] text-slate-300 space-y-1">
                  <span className="font-semibold text-amber-300/90 block">
                    Trigger &amp; Rationale:
                  </span>
                  <p className="leading-relaxed text-slate-400">
                    {rec.explanation || rec.triggerReason}
                  </p>
                </div>
              )}

              {/* Meta / Impact / Suggested Time */}
              <div className="flex flex-wrap items-center justify-between text-[11px] text-slate-400 pt-1 border-t border-slate-900">
                <span>
                  Suggested Timing: <strong className="text-slate-300 font-mono">{rec.suggestedAt}</strong>
                </span>
                {rec.impactEstimate && (
                  <span className="text-emerald-400/90 font-medium">
                    Est. Impact: {rec.impactEstimate}
                  </span>
                )}
              </div>
            </article>
          ))}
        </div>
      )}

      {/* Scope and Transparency Footnote */}
      <div className="rounded bg-slate-950/60 p-2.5 border border-slate-800/60 text-[11px] text-slate-500 leading-relaxed space-y-0.5">
        <p>
          <strong className="text-slate-400">Advisory Logic:</strong> Recommendations are derived from operational rule-based thresholds and demand timing patterns, not direct ML model predictions.
        </p>
        {IS_MOCK && (
          <p className="text-amber-400/80 font-mono text-[10px]">
            * Mock Mode: Recommendations above are sample fixtures for UI validation.
          </p>
        )}
      </div>
    </div>
  )
}
