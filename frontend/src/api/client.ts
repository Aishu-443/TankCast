/**
 * TankCast API Client
 *
 * Configurable via environment variables:
 * - VITE_API_BASE_URL: Backend URL (defaults to http://localhost:8000)
 * - VITE_USE_MOCK: Set to 'true' to use development mock data without hitting a real backend.
 *
 * IMPORTANT:
 * All backend API routes referenced below are PROVISIONAL proposals.
 * The backend contract has NOT yet been confirmed by the backend teammate.
 */

import type {
  ApiHealthResponse,
  ForecastResponse,
  HistoricalDataResponse,
  HourlyDemandPrediction,
  ModelEvidence,
  ModelInfo,
  Recommendation,
  RecommendationsResponse,
  SimulationResult,
  TankSimulationParams,
} from './types'
import {
  MOCK_FORECAST_RESPONSE,
  MOCK_HEALTH_INFO,
  MOCK_HISTORICAL_DATA,
  MOCK_HOURLY_PREDICTIONS,
  MOCK_MODEL_EVIDENCE,
  MOCK_MODEL_INFO,
  MOCK_RECOMMENDATIONS,
  MOCK_RECOMMENDATIONS_RESPONSE,
  MOCK_SIMULATION_RESULT,
} from '../mocks/mockData'

// Base configuration
export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) || 'http://localhost:8000'

export const IS_MOCK: boolean =
  import.meta.env.VITE_USE_MOCK === 'true' || import.meta.env.VITE_USE_MOCK === undefined

/**
 * Provisional endpoints dictionary.
 * These endpoints are subject to confirmation by the backend teammate.
 */
export const PROVISIONAL_ENDPOINTS = {
  HEALTH: '/api/health',
  MODEL_INFO: '/api/model/info',
  FORECAST: '/api/forecast',
  HISTORICAL: '/api/historical',
  SIMULATE: '/api/simulate',
  RECOMMENDATIONS: '/api/recommendations',
  MODEL_EVIDENCE: '/api/model/evidence',
} as const

// Helper to log provisional notice when real HTTP calls are attempted
function logProvisionalCall(route: string): void {
  if (import.meta.env.DEV) {
    console.info(`[TankCast API (Provisional)] Requesting ${API_BASE_URL}${route} - route pending backend confirmation.`)
  }
}

/**
 * Check backend health status (Provisional route: GET /api/health)
 */
export async function checkHealth(): Promise<ApiHealthResponse> {
  if (IS_MOCK) {
    return MOCK_HEALTH_INFO
  }

  logProvisionalCall(PROVISIONAL_ENDPOINTS.HEALTH)
  const res = await fetch(`${API_BASE_URL}${PROVISIONAL_ENDPOINTS.HEALTH}`)
  if (!res.ok) {
    throw new Error(`[Provisional API] Failed to fetch health status: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

/**
 * Fetch ML Model configuration & metadata (Provisional route: GET /api/model/info)
 */
export async function fetchModelInfo(): Promise<ModelInfo> {
  if (IS_MOCK) {
    return MOCK_MODEL_INFO
  }

  logProvisionalCall(PROVISIONAL_ENDPOINTS.MODEL_INFO)
  const res = await fetch(`${API_BASE_URL}${PROVISIONAL_ENDPOINTS.MODEL_INFO}`)
  if (!res.ok) {
    throw new Error(`[Provisional API] Failed to fetch model info: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

/**
 * Fetch 24-hour demand forecast response (Provisional route: GET /api/forecast)
 */
export async function fetchDemandForecast(params?: {
  scalingFactor?: number
  meterCount?: number
}): Promise<ForecastResponse> {
  if (IS_MOCK) {
    return MOCK_FORECAST_RESPONSE
  }

  logProvisionalCall(PROVISIONAL_ENDPOINTS.FORECAST)
  const query = new URLSearchParams()
  if (params?.scalingFactor) query.set('scaling_factor', String(params.scalingFactor))
  if (params?.meterCount) query.set('meter_count', String(params.meterCount))

  const url = `${API_BASE_URL}${PROVISIONAL_ENDPOINTS.FORECAST}${query.toString() ? `?${query}` : ''}`
  const res = await fetch(url)
  if (!res.ok) {
    throw new Error(`[Provisional API] Failed to fetch forecast: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

/**
 * Backwards-compatible helper returning hourly predictions array
 */
export async function fetchDemandPredictions(): Promise<HourlyDemandPrediction[]> {
  if (IS_MOCK) {
    return MOCK_HOURLY_PREDICTIONS
  }

  const forecast = await fetchDemandForecast()
  return forecast.predictions
}

/**
 * Fetch historical actual values for comparison (Provisional route: GET /api/historical)
 */
export async function fetchHistoricalActuals(): Promise<HistoricalDataResponse> {
  if (IS_MOCK) {
    return MOCK_HISTORICAL_DATA
  }

  logProvisionalCall(PROVISIONAL_ENDPOINTS.HISTORICAL)
  const res = await fetch(`${API_BASE_URL}${PROVISIONAL_ENDPOINTS.HISTORICAL}`)
  if (!res.ok) {
    throw new Error(`[Provisional API] Failed to fetch historical data: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

/**
 * Run tank endurance & water balance simulation (Provisional route: POST /api/simulate)
 */
export async function runTankSimulation(
  params: TankSimulationParams,
): Promise<SimulationResult> {
  if (IS_MOCK) {
    return MOCK_SIMULATION_RESULT
  }

  logProvisionalCall(PROVISIONAL_ENDPOINTS.SIMULATE)
  const res = await fetch(`${API_BASE_URL}${PROVISIONAL_ENDPOINTS.SIMULATE}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  if (!res.ok) {
    throw new Error(`[Provisional API] Failed to run tank simulation: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

/**
 * Fetch shortage operational recommendations container (Provisional route: GET /api/recommendations)
 */
export async function fetchRecommendationsResponse(): Promise<RecommendationsResponse> {
  if (IS_MOCK) {
    return MOCK_RECOMMENDATIONS_RESPONSE
  }

  logProvisionalCall(PROVISIONAL_ENDPOINTS.RECOMMENDATIONS)
  const res = await fetch(`${API_BASE_URL}${PROVISIONAL_ENDPOINTS.RECOMMENDATIONS}`)
  if (!res.ok) {
    throw new Error(`[Provisional API] Failed to fetch recommendations: ${res.status} ${res.statusText}`)
  }
  const data: RecommendationsResponse | Recommendation[] = await res.json()
  return Array.isArray(data) ? { generatedAt: new Date().toISOString(), items: data } : data
}

/**
 * Fetch shortage operational recommendations array (Provisional route: GET /api/recommendations)
 */
export async function fetchRecommendations(): Promise<Recommendation[]> {
  if (IS_MOCK) {
    return MOCK_RECOMMENDATIONS
  }

  const response = await fetchRecommendationsResponse()
  return response.items
}

/**
 * Fetch model performance evidence and baseline comparisons (Provisional route: GET /api/model/evidence)
 */
export async function fetchModelEvidence(): Promise<ModelEvidence> {
  if (IS_MOCK) {
    return MOCK_MODEL_EVIDENCE
  }

  logProvisionalCall(PROVISIONAL_ENDPOINTS.MODEL_EVIDENCE)
  const res = await fetch(`${API_BASE_URL}${PROVISIONAL_ENDPOINTS.MODEL_EVIDENCE}`)
  if (!res.ok) {
    throw new Error(`[Provisional API] Failed to fetch model evidence: ${res.status} ${res.statusText}`)
  }
  return res.json()
}
