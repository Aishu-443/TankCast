/**
 * TankCast Development Mock Data
 *
 * CAUTION: ALL DATA IN THIS FILE IS SYNTHETIC MOCK DATA FOR LOCAL DEVELOPMENT.
 * It is NOT real machine learning model output or verified sensor data.
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
} from '../api/types'

export const MOCK_HEALTH_INFO: ApiHealthResponse = {
  status: 'ok',
  version: '0.2.0-provisional',
  timestamp: '2026-10-14T10:00:00Z',
  modelLoaded: true,
  activeModelName: 'rf_daiad_residential_h24.joblib (MOCK)',
  environment: 'development-mock',
  provisionalNotice: 'Mock backend response. Real backend connection pending Phase 3.',
}

export const MOCK_MODEL_INFO: ModelInfo = {
  modelType: 'RandomForestRegressor (n_estimators=200, min_samples_leaf=3)',
  targetUnit: 'litres per meter per hour',
  frequency: 'hourly',
  horizonSteps: 24,
  isSynthetic: false,
  datasetSource: 'DAIAD Residential Water Dataset (Alicante smart meters)',
  featuresUsed: ['hour_of_day', 'day_of_week', 'is_weekend', 'lag_24h', 'rolling_mean_24h'],
  featurePolicy: 'Calendar features for forecast hour + target lags >= 24h old. No weather or occupancy features.',
}

export const MOCK_HOURLY_PREDICTIONS: HourlyDemandPrediction[] = [
  { timestamp: '2026-10-14T06:00:00', hour: 6, predictedLitersPerMeter: 12.5, totalScaledDemandLiters: 1250, lowerBoundLiters: 9.8, upperBoundLiters: 15.2 },
  { timestamp: '2026-10-14T07:00:00', hour: 7, predictedLitersPerMeter: 24.8, totalScaledDemandLiters: 2480, lowerBoundLiters: 19.5, upperBoundLiters: 30.1 },
  { timestamp: '2026-10-14T08:00:00', hour: 8, predictedLitersPerMeter: 31.2, totalScaledDemandLiters: 3120, lowerBoundLiters: 25.0, upperBoundLiters: 37.4 },
  { timestamp: '2026-10-14T09:00:00', hour: 9, predictedLitersPerMeter: 19.4, totalScaledDemandLiters: 1940, lowerBoundLiters: 15.1, upperBoundLiters: 23.7 },
  { timestamp: '2026-10-14T10:00:00', hour: 10, predictedLitersPerMeter: 14.1, totalScaledDemandLiters: 1410, lowerBoundLiters: 11.0, upperBoundLiters: 17.2 },
  { timestamp: '2026-10-14T11:00:00', hour: 11, predictedLitersPerMeter: 11.0, totalScaledDemandLiters: 1100, lowerBoundLiters: 8.5, upperBoundLiters: 13.5 },
  { timestamp: '2026-10-14T12:00:00', hour: 12, predictedLitersPerMeter: 16.3, totalScaledDemandLiters: 1630, lowerBoundLiters: 12.8, upperBoundLiters: 19.8 },
  { timestamp: '2026-10-14T13:00:00', hour: 13, predictedLitersPerMeter: 15.2, totalScaledDemandLiters: 1520, lowerBoundLiters: 11.9, upperBoundLiters: 18.5 },
  { timestamp: '2026-10-14T14:00:00', hour: 14, predictedLitersPerMeter: 13.0, totalScaledDemandLiters: 1300, lowerBoundLiters: 10.2, upperBoundLiters: 15.8 },
  { timestamp: '2026-10-14T15:00:00', hour: 15, predictedLitersPerMeter: 12.1, totalScaledDemandLiters: 1210, lowerBoundLiters: 9.5, upperBoundLiters: 14.7 },
  { timestamp: '2026-10-14T16:00:00', hour: 16, predictedLitersPerMeter: 14.5, totalScaledDemandLiters: 1450, lowerBoundLiters: 11.4, upperBoundLiters: 17.6 },
  { timestamp: '2026-10-14T17:00:00', hour: 17, predictedLitersPerMeter: 20.3, totalScaledDemandLiters: 2030, lowerBoundLiters: 16.0, upperBoundLiters: 24.6 },
  { timestamp: '2026-10-14T18:00:00', hour: 18, predictedLitersPerMeter: 28.6, totalScaledDemandLiters: 2860, lowerBoundLiters: 22.8, upperBoundLiters: 34.4 },
  { timestamp: '2026-10-14T19:00:00', hour: 19, predictedLitersPerMeter: 32.4, totalScaledDemandLiters: 3240, lowerBoundLiters: 26.0, upperBoundLiters: 38.8 },
  { timestamp: '2026-10-14T20:00:00', hour: 20, predictedLitersPerMeter: 29.1, totalScaledDemandLiters: 2910, lowerBoundLiters: 23.2, upperBoundLiters: 35.0 },
  { timestamp: '2026-10-14T21:00:00', hour: 21, predictedLitersPerMeter: 21.0, totalScaledDemandLiters: 2100, lowerBoundLiters: 16.5, upperBoundLiters: 25.5 },
  { timestamp: '2026-10-14T22:00:00', hour: 22, predictedLitersPerMeter: 13.8, totalScaledDemandLiters: 1380, lowerBoundLiters: 10.7, upperBoundLiters: 16.9 },
  { timestamp: '2026-10-14T23:00:00', hour: 23, predictedLitersPerMeter: 8.2, totalScaledDemandLiters: 820, lowerBoundLiters: 6.2, upperBoundLiters: 10.2 },
  { timestamp: '2026-10-15T00:00:00', hour: 0, predictedLitersPerMeter: 5.4, totalScaledDemandLiters: 540, lowerBoundLiters: 3.9, upperBoundLiters: 6.9 },
  { timestamp: '2026-10-15T01:00:00', hour: 1, predictedLitersPerMeter: 3.9, totalScaledDemandLiters: 390, lowerBoundLiters: 2.8, upperBoundLiters: 5.0 },
  { timestamp: '2026-10-15T02:00:00', hour: 2, predictedLitersPerMeter: 3.3, totalScaledDemandLiters: 330, lowerBoundLiters: 2.3, upperBoundLiters: 4.3 },
  { timestamp: '2026-10-15T03:00:00', hour: 3, predictedLitersPerMeter: 3.7, totalScaledDemandLiters: 370, lowerBoundLiters: 2.6, upperBoundLiters: 4.8 },
  { timestamp: '2026-10-15T04:00:00', hour: 4, predictedLitersPerMeter: 5.1, totalScaledDemandLiters: 510, lowerBoundLiters: 3.7, upperBoundLiters: 6.5 },
  { timestamp: '2026-10-15T05:00:00', hour: 5, predictedLitersPerMeter: 8.4, totalScaledDemandLiters: 840, lowerBoundLiters: 6.3, upperBoundLiters: 10.5 },
]

export const MOCK_FORECAST_RESPONSE: ForecastResponse = {
  generatedAt: '2026-10-14T05:00:00Z',
  horizonHours: 24,
  targetUnit: 'litres per meter per hour',
  scalingMultiplier: 100,
  predictions: MOCK_HOURLY_PREDICTIONS,
  isProvisional: true,
}

export const MOCK_HISTORICAL_DATA: HistoricalDataResponse = {
  timeRange: {
    start: '2026-10-13T18:00:00Z',
    end: '2026-10-14T06:00:00Z',
  },
  targetUnit: 'litres per meter per hour',
  points: [
    { timestamp: '2026-10-13T18:00:00', hour: 18, actualLitersPerMeter: 27.4, scaledBuildingLiters: 2740 },
    { timestamp: '2026-10-13T19:00:00', hour: 19, actualLitersPerMeter: 31.8, scaledBuildingLiters: 3180 },
    { timestamp: '2026-10-13T20:00:00', hour: 20, actualLitersPerMeter: 28.5, scaledBuildingLiters: 2850 },
    { timestamp: '2026-10-13T21:00:00', hour: 21, actualLitersPerMeter: 20.2, scaledBuildingLiters: 2020 },
    { timestamp: '2026-10-13T22:00:00', hour: 22, actualLitersPerMeter: 13.1, scaledBuildingLiters: 1310 },
    { timestamp: '2026-10-13T23:00:00', hour: 23, actualLitersPerMeter: 8.4, scaledBuildingLiters: 840 },
    { timestamp: '2026-10-14T00:00:00', hour: 0, actualLitersPerMeter: 5.1, scaledBuildingLiters: 510 },
    { timestamp: '2026-10-14T01:00:00', hour: 1, actualLitersPerMeter: 3.8, scaledBuildingLiters: 380 },
    { timestamp: '2026-10-14T02:00:00', hour: 2, actualLitersPerMeter: 3.2, scaledBuildingLiters: 320 },
    { timestamp: '2026-10-14T03:00:00', hour: 3, actualLitersPerMeter: 3.6, scaledBuildingLiters: 360 },
    { timestamp: '2026-10-14T04:00:00', hour: 4, actualLitersPerMeter: 4.9, scaledBuildingLiters: 490 },
    { timestamp: '2026-10-14T05:00:00', hour: 5, actualLitersPerMeter: 8.0, scaledBuildingLiters: 800 },
    { timestamp: '2026-10-14T06:00:00', hour: 6, actualLitersPerMeter: 12.1, scaledBuildingLiters: 1210 },
  ],
}

export const MOCK_SIMULATION_RESULT: SimulationResult = {
  status: 'depletes',
  hoursUntilEmpty: 8.5,
  criticalHour: 14,
  depletionInterval: 8,
  message: 'Tank depletes at hour 14 without intermediate replenishment.',
  deficitRisk: 'HIGH',
  hourlyLevels: [
    { hour: 6, levelLiters: 8000, inflowLiters: 0, demandLiters: 1250, percentage: 80.0 },
    { hour: 7, levelLiters: 5520, inflowLiters: 0, demandLiters: 2480, percentage: 55.2 },
    { hour: 8, levelLiters: 2400, inflowLiters: 0, demandLiters: 3120, percentage: 24.0 },
    { hour: 9, levelLiters: 460, inflowLiters: 0, demandLiters: 1940, percentage: 4.6 },
    { hour: 10, levelLiters: 0, inflowLiters: 0, demandLiters: 1410, percentage: 0.0 },
  ],
}

export const MOCK_RECOMMENDATIONS: Recommendation[] = [
  {
    id: 'rec-1',
    title: 'Pre-schedule Morning Inflow Refill',
    action: 'Trigger external tanker or borewell delivery before the 07:00 morning peak.',
    priority: 'urgent',
    suggestedAt: '06:00 AM',
    category: 'refill',
    explanation:
      'Forecast indicates residential demand surges from 12.5 to 31.2 L/meter/h between 07:00 and 08:00. Scheduling inflow before 07:00 prevents storage from dropping below the critical 15% buffer.',
    triggerReason: 'Projected demand surge coincides with low initial storage buffer',
    impactEstimate: 'Prevents reservoir exhaustion before 10:00 AM; preserves >25% reserve buffer.',
  },
  {
    id: 'rec-2',
    title: 'Shift Non-Essential Maintenance Usage',
    action: 'Postpone hostel courtyard cleaning and landscape watering until after 11:00 AM.',
    priority: 'medium',
    suggestedAt: '06:30 AM',
    category: 'conservation',
    explanation:
      'Coincident peak hours (07:00 - 09:00) coincide with heavy student showering. Deferring facility maintenance flattens building peak demand by an estimated ~15%.',
    triggerReason: 'Coincident peak demand hours (07:00 - 09:00)',
    impactEstimate: 'Conserves ~400–600 litres during critical peak window.',
  },
  {
    id: 'rec-3',
    title: 'Conduct Floor Tap Audit Before Evening Peak',
    action: 'Inspect communal washrooms for running taps or overflow leaks before 17:00.',
    priority: 'low',
    suggestedAt: '16:00 PM',
    category: 'alert',
    explanation:
      'A secondary demand peak occurs between 18:00 and 20:00. Eliminating fixture leaks beforehand prevents unmonitored baseline losses.',
    triggerReason: 'Forecasted evening rise to 32.4 L/meter/h at 19:00',
    impactEstimate: 'Prevents continuous passive loss of up to 100–150 L/hour.',
  },
]

export const MOCK_RECOMMENDATIONS_RESPONSE: RecommendationsResponse = {
  generatedAt: '2026-10-14T05:30:00Z',
  items: MOCK_RECOMMENDATIONS,
}

export const MOCK_MODEL_EVIDENCE: ModelEvidence = {
  modelName: 'tankcast_rf_hourly_water_demand.joblib',
  modelType: 'RandomForestRegressor (n_estimators=200, min_samples_leaf=3)',
  horizonHours: 24,
  datasetName: 'DAIAD Residential Smart Meters (Alicante, Spain)',
  samplePeriod: '2016-03-08 to 2017-02-28 (Hourly readings)',
  targetUnit: 'litres per meter per hour',
  mae: 11.79,
  rmse: 162.23,
  mape: null, // Omitted in verified evaluation to prevent division-by-zero on low hourly flows
  metrics: {
    mae: 11.79,
    rmse: 162.23,
    mape: null,
    baselineName: 'Persistence (Same hour yesterday / lag-24h)',
    baselineMae: 20.57,
    baselineRmse: 229.54,
    improvementOverBaselinePct: 42.7,
  },
  dataSplit: {
    trainRows: 6740,
    testRows: 1685,
    trainPeriod: '2016-03-08 to 2016-12-20 (First 80% chronological)',
    testPeriod: '2016-12-20 to 2017-02-28 (Held-out newest 20%)',
  },
  featurePolicy:
    'Calendar features for forecast hour + target lags and rolling stats >= 24h old. No weather or occupancy features are used.',
  isVerified: true,
  notes: [
    'Model predicts litres per residential meter per hour (mean over reporting meters).',
    'Evaluated strictly on an untouched 20% chronological holdout test period.',
    'Achieves a 42.7% MAE improvement over the 24-hour persistence baseline (11.79 vs 20.57 L/meter/h).',
  ],
  limitations: [
    'Trained on Spanish residential smart-meter data; usage patterns and climate differ from an Indian hostel.',
    'Scaling from per-meter predictions to an entire hostel building is a user-set assumption.',
    'Model does not include temperature, weather, or college calendar/occupancy features.',
    'Tank water levels are manual operator inputs, not automated telemetry sensors.',
  ],
}
