export interface Ward {
  city: string
  zone: string
  location: string
  ward_no: number
  aqi?: number | null
  temperature?: number | null
  green_cover?: number | null
  traffic_density?: number | null
  health_risk?: number | null
  population?: number | null
  final_AQI?: number | null
  mean_LST_C?: number | null
}

export interface CitySummary {
  city: string
  zone_count?: number
  average_aqi?: number | null
  average_temperature_c?: number | null
  average_green_cover_pct?: number | null
  average_traffic_density?: number | null
  average_health_risk?: number | null
  [key: string]: unknown
}

export interface WardFeatureCollection {
  type: 'FeatureCollection'
  features: Array<{
    type: 'Feature'
    geometry: GeoJSON.Geometry
    properties: Record<string, string | number | null>
  }>
}

export interface Scenario {
  scenario_id: string
  scenario_version: number
  name: string
  description: string
  city: string
  zone?: string | null
  status: string
  estimated_cost?: {
    total_estimated_cost?: number | null
    currency?: string
  } | null
  expected_impacts?: {
    expected_aqi_change?: number | null
    expected_uhi_change?: number | null
    expected_green_cover_change?: number | null
    expected_carbon_reduction?: number | null
    expected_health_risk_change?: number | null
  } | null
}

export interface ScenarioSet {
  workflow_id?: string | null
  city: string
  zone?: string | null
  problem_statement?: string
  scenarios: Scenario[]
}

export interface MetricDelta {
  baseline_value?: number | null
  simulated_value?: number | null
  absolute_delta?: number | null
  percentage_delta?: number | null
  unit?: string
  availability?: string
  availability_reason?: string | null
}

export interface SimulationResult {
  simulation_id: string
  scenario_id: string
  status: string
  baseline_state: Record<string, unknown>
  simulated_state: Record<string, unknown>
  metrics: Record<string, MetricDelta>
  metadata?: { engine_version?: string; created_at?: string }
}

export interface OptimizationResult {
  optimization_id: string
  status: string
  objectives: Array<{ name: string; direction: string }>
  constraints: Array<Record<string, unknown>>
  pareto_solutions: Array<{
    scenario_id: string
    simulation_id: string
    objective_values: Record<string, number>
  }>
  dominated_strategies: Array<Record<string, unknown>>
  infeasible_strategies: Array<Record<string, unknown>>
  scores: Array<Record<string, unknown>>
}

export interface SystemStatus {
  overall_status: string
  checked_at: string
  components: Record<string, { status: string; latency_ms?: number; mode?: string; count?: number; ward_count?: number; backend?: string }>
}

export interface AuthConfig {
  required: boolean
  configured: boolean
}

export interface ApiError {
  detail?: string
}
