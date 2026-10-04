import axios from 'axios'
import type {
  AuthConfig,
  CitySummary,
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
  generateScenarios: (payload: Record<string, unknown>) =>
    api.post<ScenarioSet>('/scenarios/generate', payload),
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
