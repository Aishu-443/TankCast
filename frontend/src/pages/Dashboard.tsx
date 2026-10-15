import React from 'react'
import { IS_MOCK } from '../api/client'
import { MockBanner } from '../components/MockBanner'
import { DemandChart } from '../components/DemandChart'
import { TankSimulator } from '../components/TankSimulator'
import { Recommendations } from '../components/Recommendations'
import { ModelEvidenceCard } from '../components/ModelEvidenceCard'

export const Dashboard: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans">
      <MockBanner isMock={IS_MOCK} />

      <header className="border-b border-slate-800 bg-slate-950 px-5 py-5">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              <span className="text-cyan-400">TankCast</span>
              <span className="text-slate-400 font-medium"> | Water Planner</span>
            </h1>
            <p className="text-sm text-slate-400 mt-2">
              Check your water reserves, estimate shortage risk, and plan replenishment.
            </p>
          </div>
          <div className="text-xs px-3 py-2 rounded-lg border border-slate-700 bg-slate-900 w-fit">
            API status: <span className={IS_MOCK ? 'text-amber-400 font-semibold' : 'text-emerald-400 font-semibold'}>
              {IS_MOCK ? 'Demo data' : 'Backend connected'}
            </span>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto w-full p-4 sm:p-6 space-y-6">
        <section className="rounded-xl border border-cyan-900/60 bg-gradient-to-r from-slate-900 to-cyan-950/30 p-5 sm:p-6">
          <p className="text-xs font-semibold uppercase tracking-widest text-cyan-400">
            Your water, planned better
          </p>
          <h2 className="text-xl sm:text-2xl font-bold text-white mt-2">
            How long will your water last?
          </h2>
          <p className="text-sm text-slate-300 mt-2 max-w-3xl leading-relaxed">
            Enter your tank level and expected supply delay in the simulator below.
            TankCast estimates how the water level may change using its demand forecast.
          </p>
          <p className="text-xs text-slate-400 mt-3">
            Prototype notice: forecasts use historical Spanish residential smart-meter data,
            not live sensors. Building size and tank inputs are assumptions supplied by the user.
            Results have not been validated for an Indian hostel.
          </p>
        </section>

        <section id="tank-planner" className="rounded-xl border border-cyan-900/50 bg-slate-900/70 p-4 sm:p-6">
          <div className="mb-5">
            <p className="text-xs uppercase tracking-widest text-cyan-400 font-semibold">
              Step 1
            </p>
            <h2 className="text-xl font-bold text-white mt-1">
              Tank shortage planner
            </h2>
            <p className="text-sm text-slate-400 mt-1">
              Adjust the values below to see the projected reserve and shortage risk.
              Results recalculate as you change the inputs.
            </p>
          </div>
          <TankSimulator />
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 sm:p-6">
          <div className="mb-4">
            <p className="text-xs uppercase tracking-widest text-sky-400 font-semibold">
              Step 2
            </p>
            <h2 className="text-xl font-bold text-white">Water demand forecast</h2>
            <p className="text-sm text-slate-400 mt-1">
              Review historical demand and the model's forecasted demand.
            </p>
          </div>
          <DemandChart />
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 sm:p-6">
          <div className="mb-4">
            <p className="text-xs uppercase tracking-widest text-emerald-400 font-semibold">
              Step 3
            </p>
            <h2 className="text-xl font-bold text-white">Suggested actions</h2>
            <p className="text-sm text-slate-400 mt-1">
              Review the prototype's recommendations for managing water reserves.
            </p>
          </div>
          <Recommendations />
        </section>

        <details className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 sm:p-6">
          <summary className="cursor-pointer text-lg font-semibold text-slate-200">
            Model evidence and limitations
          </summary>
          <p className="text-sm text-slate-400 mt-2 mb-4">
            Technical details, evaluation metrics, data coverage, and model limitations.
          </p>
          <ModelEvidenceCard />
        </details>
      </main>

      <footer className="border-t border-slate-800 mt-8 py-5 px-4 text-center text-xs text-slate-500">
        TankCast Prototype · Water Demand Forecasting · Historical-data-based planning
      </footer>
    </div>
  )
}

export default Dashboard
