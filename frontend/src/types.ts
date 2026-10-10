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
  carbon_reduction_availability_reason?: string | null
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
  provenance?: {
    implementation_schedule?: {
      duration_years: number
      source_type: string
      source: string
    }
  }
  estimated_cost?: {
    total_estimated_cost?: number | null
    currency?: string
  } | null
  carbon_reduction_availability_reason?: string | null
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

export interface CarbonFactorInput {
  source: string
  version: string
  reference: string
  status: 'Illustrative' | 'Unverified' | 'Verified'
}

export interface CarbonScenarioRequest {
  scenario_name: string
  annual_vehicle_km: number
  diesel_litres_per_vehicle_km: number
  electric_kwh_per_vehicle_km: number
  diesel_emission_factor_kg_co2_per_litre: number
  electricity_emission_factor_kg_co2_per_kwh: number
  baseline_period_start: string
  baseline_period_end: string
  project_period_start: string
  project_period_end: string
  activity_source: string
  activity_reference: string
  input_classification: 'Illustrative' | 'Estimated' | 'Measured'
  diesel_factor: CarbonFactorInput
  electricity_factor: CarbonFactorInput
}

export interface CarbonScenarioResult {
  scenario_id?: string | null
  scenario_name: string
  result_classification: 'SIMULATED' | 'ESTIMATED' | 'MEASURED'
  display_label: string
  unit: 'tCO2/year'
  baseline_emissions_tco2_per_year: number
  project_emissions_tco2_per_year: number
  avoided_emissions_tco2_per_year: number
  percentage_change: number | null
  baseline_diesel_litres_per_year: number
  project_electricity_kwh_per_year: number
  annual_vehicle_km: number
  periods: {
    baseline_start: string
    baseline_end: string
    project_start: string
    project_end: string
  }
  assumptions: {
    service_boundary: string
    period_basis: string
    calculation: string
    activity_source: string
    activity_reference: string
    input_classification: string
    diesel_factor: {
      value_kg_co2_per_litre: number
      source: string
      version: string
      reference: string
      status: 'Illustrative' | 'Unverified' | 'Verified'
    }
    electricity_factor: {
      value_kg_co2_per_kwh: number
      source: string
      version: string
      reference: string
      status: 'Illustrative' | 'Unverified' | 'Verified'
    }
  }
}

export interface MetricDelta {
  baseline_value?: number | null
  simulated_value?: number | null
  absolute_delta?: number | null
  percentage_delta?: number | null
  unit?: string
  source_model?: string
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
    objective_sources?: Record<string, string>
  }>
  dominated_strategies: Array<Record<string, unknown>>
  infeasible_strategies: Array<Record<string, unknown>>
  unevaluable_strategies: Array<Record<string, unknown>>
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

export type EnvironmentalMetric =
  | 'aqi' | 'pm25' | 'pm10' | 'no2' | 'o3' | 'co' | 'so2'
  | 'temperature' | 'land_surface_temperature' | 'green_cover' | 'population'
export type EnvironmentalClassification = 'observed' | 'official' | 'derived' | 'estimated' | 'illustrative'

export interface EnvironmentalRecordInput {
  ward_id: number
  observation_date: string
  metric: EnvironmentalMetric
  value: number
  unit: string
  data_classification: EnvironmentalClassification
  source_name: string
  source_reference?: string | null
  notes?: string | null
}

export interface EnvironmentalRecord extends EnvironmentalRecordInput {
  record_id: string
  created_at: string
}

export interface EnvironmentalRecordPage {
  records: EnvironmentalRecord[]
  total: number
  limit: number
  offset: number
}

export type EnvironmentalColumnMapping = Partial<Record<keyof EnvironmentalRecordInput, string>>

export interface EnvironmentalUploadPreview {
  filename: string
  checksum: string
  columns: string[]
  preview_rows: Array<Record<string, string | null>>
  total_rows_read: number
}

export interface EnvironmentalValidationIssue {
  row_number: number
  field: string
  reason: string
  kind: 'invalid' | 'duplicate'
}

export interface EnvironmentalValidationReport {
  filename: string
  checksum: string
  total_rows_read: number
  valid_rows: number
  invalid_rows: number
  duplicate_rows: number
  errors: EnvironmentalValidationIssue[]
}

export interface EnvironmentalImportResult extends EnvironmentalValidationReport {
  import_id: string
  imported_at: string
  rows_inserted: number
  rows_skipped: number
  idempotent_retry: boolean
}
