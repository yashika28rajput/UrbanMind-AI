import axios from 'axios'
import type {
  AuthConfig,
  AnnualWardCarbonResponse,
  CarbonScenarioRequest,
  CarbonScenarioResult,
  CarbonCalculationRequest,
  CarbonCalculationResult,
  CitySummary,
  EnvironmentalColumnMapping,
  EnvironmentalImportResult,
  EnvironmentalRecord,
  EnvironmentalRecordInput,
  EnvironmentalRecordPage,
  EnvironmentalUploadPreview,
  EnvironmentalValidationReport,
  OptimizationResult,
  Scenario,
  ScenarioSet,
  SimulationResult,
  SystemStatus,
  Ward,
  WardFeatureCollection,
} from './types'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 30_000,
})

api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('urbanmind_access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export const requests = {
  authConfig: () => api.get<AuthConfig>('/auth/config'),
  login: (username: string, password: string) =>
    api.post<{ access_token: string; expires_in: number }>('/auth/login', { username, password }),
  me: () => api.get<{ username: string }>('/auth/me'),
  summary: () => api.get<{ summary: CitySummary }>('/digital-twin/summary'),
  wards: () => api.get<{ wards: Ward[] }>('/digital-twin/wards'),
  wardGeojson: () => api.get<WardFeatureCollection>('/digital-twin/wards/geojson'),
  scenarios: () => api.get<{ scenarios: Scenario[] }>('/scenarios'),
  systemStatus: () => api.get<SystemStatus>('/system/status'),
  annualWardCarbon: () => api.get<AnnualWardCarbonResponse>('/carbon/wards/annual'),
  generateScenarios: (payload: Record<string, unknown>) =>
    api.post<ScenarioSet>('/scenarios/generate', payload),
  calculateCarbonScenario: (payload: CarbonScenarioRequest) =>
    api.post<CarbonScenarioResult>('/carbon/scenarios/calculate', payload),
  calculateCarbon: (payload: CarbonCalculationRequest) =>
    api.post<CarbonCalculationResult>('/carbon/calculate', payload),
  environmentalPreview: (file: File) => {
    const body = new FormData()
    body.append('file', file)
    return api.post<EnvironmentalUploadPreview>('/environmental-data/uploads/preview', body)
  },
  validateEnvironmentalUpload: (file: File, mapping: EnvironmentalColumnMapping) => {
    const body = new FormData()
    body.append('file', file)
    body.append('mapping_json', JSON.stringify(mapping))
    return api.post<EnvironmentalValidationReport>('/environmental-data/uploads/validate', body)
  },
  importEnvironmentalUpload: (file: File, mapping: EnvironmentalColumnMapping, checksum: string) => {
    const body = new FormData()
    body.append('file', file)
    body.append('mapping_json', JSON.stringify(mapping))
    body.append('checksum', checksum)
    return api.post<EnvironmentalImportResult>('/environmental-data/imports/confirm', body)
  },
  createEnvironmentalRecord: (payload: EnvironmentalRecordInput) =>
    api.post<EnvironmentalRecord>('/environmental-data/records', payload),
  environmentalRecords: (params: { limit: number; offset: number; ward_id?: number }) =>
    api.get<EnvironmentalRecordPage>('/environmental-data/records', { params }),
  simulateScenario: (payload: Record<string, unknown>) =>
    api.post<SimulationResult>('/simulation/run', payload),
  getSimulation: (simulationId: string) =>
    api.get<SimulationResult>(`/simulation/${encodeURIComponent(simulationId)}`),
  optimize: (payload: Record<string, unknown>) =>
    api.post<OptimizationResult>('/optimization/run', payload),
  getOptimization: (optimizationId: string) =>
    api.get<OptimizationResult>(`/optimization/${encodeURIComponent(optimizationId)}`),
  getPareto: (optimizationId: string) =>
    api.get<Pick<OptimizationResult, 'optimization_id' | 'objectives' | 'pareto_solutions'>>(
      `/optimization/${encodeURIComponent(optimizationId)}/pareto`,
    ),
  decision: (payload: Record<string, unknown>) =>
    api.post<Record<string, unknown>>('/decision/analyze', payload),
  ragQuery: (payload: Record<string, unknown>) =>
    api.post<Record<string, unknown>>('/rag/query', payload),
  explainPrediction: (payload: Record<string, unknown>) =>
    api.post<Record<string, unknown>>('/explanation/prediction', payload),
  explainRecommendation: (payload: Record<string, unknown>) =>
    api.post<Record<string, unknown>>('/explanation/recommendation', payload),
  counterfactual: (payload: Record<string, unknown>) =>
    api.post<Record<string, unknown>>('/explanation/counterfactual', payload),
}

export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      const validationMessages = detail.flatMap((item) => {
        if (typeof item !== 'object' || item === null) return []
        const validationError = item as { loc?: unknown; msg?: unknown }
        if (typeof validationError.msg !== 'string') return []
        const location = Array.isArray(validationError.loc)
          ? validationError.loc.filter((part): part is string | number => typeof part === 'string' || typeof part === 'number').slice(1).join('.')
          : ''
        return [location ? `${location}: ${validationError.msg}` : validationError.msg]
      })
      if (validationMessages.length) return validationMessages.join('; ')
    }
    if (error.code === 'ECONNABORTED') return 'The request timed out. Please try again.'
    if (!error.response) return 'Unable to connect to the UrbanMind AI backend.'
    return `The backend returned an error (${error.response.status}).`
  }
  return error instanceof Error ? error.message : 'An unexpected error occurred.'
}

export function formatMetric(value: unknown, digits = 1): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) return 'Unavailable'
  return value.toLocaleString('en-IN', { maximumFractionDigits: digits })
}

export function formatCurrency(value: unknown, currency = 'INR'): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) return 'Unavailable'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(value)
}

export type { Scenario, ScenarioSet, SimulationResult, OptimizationResult, SystemStatus, Ward, CitySummary }
