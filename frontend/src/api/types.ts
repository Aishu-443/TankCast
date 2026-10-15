/**
 * TankCast Frontend API Contracts (Provisional)
 * 
 * NOTE: These types represent the proposed data contracts for the TankCast frontend.
 * They align with the ML model (RandomForest on DAIAD meter data) and the tank water-balance
 * calculation logic, but remain PROVISIONAL until the backend API teammate confirms the final routes.
 */

// ---------------------------------------------------------------------------
// 1. System Health & Model Information
// ---------------------------------------------------------------------------

export type HealthStatus = 'ok' | 'degraded' | 'error'

export interface ApiHealthResponse {
  status: HealthStatus
  version: string
  timestamp: string
  modelLoaded: boolean
  activeModelName?: string
  environment?: string
  provisionalNotice?: string
}

export interface ModelInfo {
  modelType: string
  targetUnit: string
  frequency: 'hourly' | 'daily'
  horizonSteps: number
  isSynthetic: boolean
  datasetSource: string
  featuresUsed: string[]
  featurePolicy: string
}

// ---------------------------------------------------------------------------
// 2. Forecast Predictions
// ---------------------------------------------------------------------------

export interface HourlyDemandPrediction {
  timestamp: string
  hour: number // 0-23
  predictedLitersPerMeter: number
  totalScaledDemandLiters: number
  lowerBoundLiters?: number
  upperBoundLiters?: number
}

export interface ForecastResponse {
  generatedAt: string
  horizonHours: number
  targetUnit: string
  scalingMultiplier: number
  predictions: HourlyDemandPrediction[]
  isProvisional: boolean
}

// ---------------------------------------------------------------------------
// 3. Historical Actual Values
// ---------------------------------------------------------------------------

export interface HistoricalDataPoint {
  timestamp: string
  hour: number
  actualLitersPerMeter: number
  scaledBuildingLiters: number
  isImputed?: boolean
}

export interface HistoricalDataResponse {
  timeRange: {
    start: string
    end: string
  }
  targetUnit: string
  points: HistoricalDataPoint[]
}

// ---------------------------------------------------------------------------
// 4. Tank Simulation & Water Balance
// ---------------------------------------------------------------------------

export type EnduranceStatus = 'depletes' | 'empty_now' | 'not_depleting' | 'beyond_forecast'
export type DeficitRiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

export interface TankSimulationParams {
  tankCapacityLiters: number
  currentLevelLiters: number
  reserveLiters?: number
  meterCount: number
  scalingFactor: number
  supplyDelayHours?: number
  restoredSupplyRateLph?: number
  refillScheduleHours?: number[]
  refillVolumeLiters?: number
  constantSupplyRateLph?: number
}

export interface SimulationHourlyLevel {
  hour: number
  timestamp?: string
  levelLiters: number
  inflowLiters: number
  demandLiters: number
  percentage: number
}

export interface SimulationResult {
  status?: EnduranceStatus
  hoursUntilEmpty: number | null
  criticalHour?: number
  depletionInterval?: number | null
  message?: string
  hourlyLevels: SimulationHourlyLevel[]
  deficitRisk: DeficitRiskLevel
}

// ---------------------------------------------------------------------------
// 5. Operational Recommendations
// ---------------------------------------------------------------------------

export type RecommendationPriority = 'low' | 'medium' | 'high' | 'urgent'
export type RecommendationCategory = 'refill' | 'conservation' | 'maintenance' | 'alert'

export interface Recommendation {
  id: string
  title: string
  action: string
  priority: RecommendationPriority
  suggestedAt: string
  category?: RecommendationCategory
  impactEstimate?: string
  explanation?: string
  triggerReason?: string
}

export interface RecommendationsResponse {
  generatedAt: string
  items: Recommendation[]
}

// ---------------------------------------------------------------------------
// 6. Model Evidence & Evaluation Metrics
// ---------------------------------------------------------------------------

export interface ModelMetrics {
  mae?: number | null
  rmse?: number | null
  mape?: number | null
  baselineName?: string | null
  baselineMae?: number | null
  baselineRmse?: number | null
  improvementOverBaselinePct?: number | null
}

export interface DataSplitInfo {
  trainRows?: number | null
  testRows?: number | null
  trainPeriod?: string | null
  testPeriod?: string | null
}

export interface ModelEvidence {
  modelName?: string | null
  modelType?: string | null
  horizonHours?: number | null
  datasetName: string
  samplePeriod: string
  targetUnit?: string | null
  mae?: number | null
  rmse?: number | null
  mape?: number | null
  metrics?: ModelMetrics | null
  dataSplit?: DataSplitInfo | null
  featurePolicy?: string | null
  isVerified?: boolean
  notes: string[]
  limitations: string[]
}
