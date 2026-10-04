import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

const mocks = vi.hoisted(() => ({
  authConfig: vi.fn(),
  login: vi.fn(),
  me: vi.fn(),
  summary: vi.fn(),
  wards: vi.fn(),
  wardGeojson: vi.fn(),
  scenarios: vi.fn(),
  systemStatus: vi.fn(),
  generateScenarios: vi.fn(),
  simulateScenario: vi.fn(),
  optimize: vi.fn(),
  decision: vi.fn(),
  ragQuery: vi.fn(),
  explainPrediction: vi.fn(),
  explainRecommendation: vi.fn(),
  counterfactual: vi.fn(),
}))

vi.mock('./api', () => ({
  requests: mocks,
  errorMessage: (error: unknown) => error instanceof Error ? error.message : 'Backend unavailable',
  formatMetric: (value: unknown) => typeof value === 'number' ? value.toLocaleString() : 'Unavailable',
  formatCurrency: (value: unknown) => typeof value === 'number' ? String(value) : 'Unavailable',
}))

vi.mock('./components/CityMap', () => ({
  CityMap: () => <div data-testid="city-map">Ward map</div>,
}))

const ward = {
  city: 'Delhi',
  zone: 'Ward_7',
  location: 'Test Ward',
  ward_no: 7,
  aqi: 124,
  temperature: 34.2,
  green_cover: 18.5,
  traffic_density: 0.42,
  health_risk: 0.21,
  population: 42000,
}

const status = {
  overall_status: 'DEGRADED',
  checked_at: '2026-10-04T06:00:00Z',
  components: {
    fastapi: { status: 'HEALTHY' },
    database: { status: 'HEALTHY', latency_ms: 2.4, backend: 'sqlite' },
    qdrant: { status: 'NOT_CONFIGURED', mode: 'fallback' },
    rag: { status: 'DEGRADED', mode: 'fallback' },
    ml_models: { status: 'HEALTHY', count: 5 },
    digital_twin: { status: 'HEALTHY', ward_count: 272 },
  },
}

function renderDashboard(path = '/overview') {
  return render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>)
}

describe('UrbanMind dashboard', () => {
  beforeEach(() => {
    sessionStorage.clear()
    Object.values(mocks).forEach((mock) => mock.mockReset())
    mocks.authConfig.mockResolvedValue({ data: { required: false, configured: false } })
    mocks.login.mockResolvedValue({ data: { access_token: 'signed-test-token' } })
    mocks.me.mockRejectedValue(new Error('No session'))
    mocks.summary.mockResolvedValue({ data: { summary: { average_aqi: 124, average_temperature_c: 34.2, average_green_cover_pct: 18.5, average_health_risk: 0.21 } } })
    mocks.wards.mockResolvedValue({ data: { wards: [ward] } })
    mocks.wardGeojson.mockResolvedValue({ data: null })
    mocks.scenarios.mockResolvedValue({ data: { scenarios: [] } })
    mocks.systemStatus.mockResolvedValue({ data: status })
    mocks.generateScenarios.mockResolvedValue({
      data: {
        city: 'Delhi',
        scenarios: [{
          scenario_id: 'SCN-TEST',
          scenario_version: 1,
          name: 'Backend generated strategy',
          description: 'Returned by the scenario API.',
          city: 'Delhi',
          status: 'VALIDATED',
        }],
      },
    })
    mocks.simulateScenario.mockResolvedValue({ data: {} })
    mocks.optimize.mockResolvedValue({ data: {} })
    mocks.decision.mockResolvedValue({
      data: {
        recommendation: 'Prioritize urban forestry',
        detected_problems: ['Elevated heat exposure'],
        evidence: [],
        limitations: [],
      },
    })
    mocks.ragQuery.mockResolvedValue({ data: {} })
    mocks.explainPrediction.mockResolvedValue({ data: {} })
    mocks.explainRecommendation.mockResolvedValue({ data: {} })
    mocks.counterfactual.mockResolvedValue({ data: {} })
  })

  it('shows a loading state while the dashboard APIs are pending', async () => {
    mocks.summary.mockReturnValue(new Promise(() => undefined))
    renderDashboard()
    expect(await screen.findByText('Loading urban intelligence…')).toBeInTheDocument()
  })

  it('surfaces backend failures without substituting demo indicators', async () => {
    mocks.summary.mockRejectedValue(new Error('Backend is offline'))
    renderDashboard()
    expect(await screen.findByText('Backend is offline')).toBeInTheDocument()
    expect(screen.getAllByText('Unavailable').length).toBeGreaterThan(0)
  })

  it('supports configured login and opens the dashboard after sign-in', async () => {
    mocks.authConfig.mockResolvedValue({ data: { required: true, configured: true } })
    renderDashboard()
    fireEvent.change(await screen.findByLabelText('Username'), { target: { value: 'planner' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret' } })
    fireEvent.click(screen.getByRole('button', { name: /continue to dashboard/i }))
    expect(await screen.findByRole('heading', { name: 'City overview', level: 1 })).toBeInTheDocument()
    expect(sessionStorage.getItem('urbanmind_access_token')).toBe('signed-test-token')
  })

  it('generates and displays backend scenarios from Scenario Lab', async () => {
    renderDashboard()
    fireEvent.click(await screen.findByRole('navigation').then((navigation) => within(navigation).findByRole('link', { name: /scenario lab/i })))
    fireEvent.change(await screen.findByLabelText('Problem statement'), { target: { value: 'Reduce heat exposure' } })
    fireEvent.click(screen.getByRole('button', { name: /generate candidate scenarios/i }))
    expect(await screen.findByText('Backend generated strategy')).toBeInTheDocument()
    expect(mocks.generateScenarios).toHaveBeenCalledWith(expect.objectContaining({
      city: 'Delhi',
      problem_statement: 'Reduce heat exposure',
    }))
  })

  it('submits the decision brief to the existing analysis API', async () => {
    renderDashboard()
    fireEvent.click(await screen.findByRole('navigation').then((navigation) => within(navigation).findByRole('link', { name: /decision center/i })))
    fireEvent.change(await screen.findByLabelText('Problem'), { target: { value: 'High heat exposure in the ward' } })
    fireEvent.click(screen.getByRole('button', { name: /analyze decision/i }))
    expect(await screen.findByText(/Prioritize urban forestry/)).toBeInTheDocument()
    expect(mocks.decision).toHaveBeenCalledWith(expect.objectContaining({
      query: 'High heat exposure in the ward',
      city: 'Delhi',
      zone: 'Ward_7',
    }))
  })

  it('shows live service status, including unconfigured Qdrant', async () => {
    renderDashboard()
    fireEvent.click(await screen.findByRole('navigation').then((navigation) => within(navigation).findByRole('link', { name: /system status/i })))
    expect(await screen.findByText('Evidence retrieval')).toBeInTheDocument()
    expect(screen.getByText('NOT CONFIGURED')).toBeInTheDocument()
    expect(screen.getByText(/fallback retrieval/i)).toBeInTheDocument()
  })
})
