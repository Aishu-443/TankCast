/**
 * TankCast Water Balance & Endurance Simulation
 *
 * Implements the domain logic from src/tank_calculator.py:
 * new_level = old_level - (demand - supply) * interval_hours
 *
 * INVARIANT:
 * Under the same demand assumptions, increasing supply delay cannot make
 * the estimated time until empty longer.
 */

import type {
  HourlyDemandPrediction,
  SimulationHourlyLevel,
  SimulationResult,
} from '../api/types'

export interface ClientSimulationInput {
  capacityLiters: number
  currentLevelLiters: number
  supplyDelayHours: number
  meterCount: number
  restoredSupplyRateLph?: number
  forecastPredictions: HourlyDemandPrediction[]
}

export function formatHoursAndMinutes(hours: number): string {
  const totalMinutes = Math.round(hours * 60)
  const h = Math.floor(totalMinutes / 60)
  const m = totalMinutes % 60
  if (h === 0) return `${m} min`
  if (m === 0) return `${h} h`
  return `${h} h ${m.toString().padStart(2, '0')} min`
}

export function calculateTankSimulation(input: ClientSimulationInput): SimulationResult {
  const {
    capacityLiters,
    currentLevelLiters,
    supplyDelayHours,
    meterCount,
    restoredSupplyRateLph = 1500,
    forecastPredictions,
  } = input

  // Handle zero/negative capacity
  if (capacityLiters <= 0) {
    return {
      status: 'empty_now',
      hoursUntilEmpty: 0,
      deficitRisk: 'CRITICAL',
      message: 'Tank capacity must be greater than zero litres.',
      hourlyLevels: [],
    }
  }

  // Current level clamped to [0, capacity]
  const validCurrentLevel = Math.max(0, Math.min(currentLevelLiters, capacityLiters))

  // Handle already empty tank
  if (validCurrentLevel === 0) {
    return {
      status: 'empty_now',
      hoursUntilEmpty: 0,
      deficitRisk: 'CRITICAL',
      message: 'The tank is currently empty (0 litres available).',
      hourlyLevels: [
        {
          hour: forecastPredictions[0]?.hour ?? 0,
          timestamp: forecastPredictions[0]?.timestamp,
          levelLiters: 0,
          inflowLiters: 0,
          demandLiters: 0,
          percentage: 0,
        },
      ],
    }
  }

  // Handle zero demand
  if (meterCount <= 0 || forecastPredictions.length === 0) {
    return {
      status: 'not_depleting',
      hoursUntilEmpty: null,
      deficitRisk: 'LOW',
      message: 'Building demand is zero; the tank will not run empty.',
      hourlyLevels: forecastPredictions.map((p) => ({
        hour: p.hour,
        timestamp: p.timestamp,
        levelLiters: validCurrentLevel,
        inflowLiters: 0,
        demandLiters: 0,
        percentage: Math.round((validCurrentLevel / capacityLiters) * 1000) / 10,
      })),
    }
  }

  let currentLevel = validCurrentLevel
  const hourlyLevels: SimulationHourlyLevel[] = []
  let hoursUntilEmpty: number | null = null
  let depletionInterval: number | null = null

  // Step through each hour of the forecast horizon
  for (let i = 0; i < forecastPredictions.length; i++) {
    const point = forecastPredictions[i]
    // Demand for building = predicted litres/meter/hour * equivalent residential meters
    const perMeterRate = Math.max(0, point.predictedLitersPerMeter || 0)
    const hourlyDemand = perMeterRate * meterCount

    // Supply is 0 during the delay, then resumes at restoredSupplyRateLph
    const hourlySupply = i < supplyDelayHours ? 0 : restoredSupplyRateLph
    const netLossRate = hourlyDemand - hourlySupply

    if (hoursUntilEmpty === null) {
      if (netLossRate > 0 && currentLevel - netLossRate <= 0) {
        // Tank depletes inside this 1-hour interval
        hoursUntilEmpty = i + currentLevel / netLossRate
        depletionInterval = i
        currentLevel = 0
      } else {
        currentLevel = Math.max(0, Math.min(capacityLiters, currentLevel - netLossRate))
      }
    } else {
      // Tank already depleted previously in the simulation
      if (hourlySupply > hourlyDemand) {
        // Net refill
        currentLevel = Math.min(capacityLiters, currentLevel + (hourlySupply - hourlyDemand))
      } else {
        currentLevel = 0
      }
    }

    hourlyLevels.push({
      hour: point.hour,
      timestamp: point.timestamp,
      levelLiters: Math.round(currentLevel),
      inflowLiters: Math.round(hourlySupply),
      demandLiters: Math.round(hourlyDemand),
      percentage: Math.round((currentLevel / capacityLiters) * 1000) / 10,
    })
  }

  // Determine risk assessment and explanation
  let deficitRisk: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' = 'LOW'
  let status: 'depletes' | 'empty_now' | 'not_depleting' | 'beyond_forecast' = 'beyond_forecast'
  let message = ''

  if (hoursUntilEmpty !== null) {
    status = 'depletes'
    if (hoursUntilEmpty < 3) {
      deficitRisk = 'CRITICAL'
    } else if (hoursUntilEmpty < 6) {
      deficitRisk = 'HIGH'
    } else if (hoursUntilEmpty < 12) {
      deficitRisk = 'MEDIUM'
    } else {
      deficitRisk = 'LOW'
    }
    const formatted = formatHoursAndMinutes(hoursUntilEmpty)
    const delayText =
      supplyDelayHours > 0
        ? `with a ${supplyDelayHours}-hour supply delay`
        : 'with uninterrupted supply'
    message = `At scaled building demand, tank runs empty in ${formatted} (${delayText}).`
  } else {
    const minLevelPct =
      hourlyLevels.length > 0 ? Math.min(...hourlyLevels.map((h) => h.percentage)) : 100

    if (minLevelPct < 15) {
      deficitRisk = 'HIGH'
      status = 'beyond_forecast'
      message = `Does not completely run dry within ${forecastPredictions.length}h, but storage drops to a critical ${minLevelPct.toFixed(1)}%.`
    } else if (minLevelPct < 30) {
      deficitRisk = 'MEDIUM'
      status = 'beyond_forecast'
      message = `Water storage remains sufficient, dropping to a minimum buffer of ${minLevelPct.toFixed(1)}%.`
    } else {
      deficitRisk = 'LOW'
      status = 'beyond_forecast'
      message = `Storage level remains healthy (>30%) throughout the ${forecastPredictions.length}-hour forecast window.`
    }
  }

  return {
    status,
    hoursUntilEmpty,
    depletionInterval,
    message,
    hourlyLevels,
    deficitRisk,
  }
}
