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
  annualWardCarbon: vi.fn(),
  generateScenarios: vi.fn(),
  calculateCarbonScenario: vi.fn(),
  calculateCarbon: vi.fn(),
  simulateScenario: vi.fn(),
  getSimulation: vi.fn(),
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
  formatMetric: (value: unknown, digits = 1) => typeof value === 'number' ? value.toLocaleString('en-IN', { maximumFractionDigits: digits }) : 'Unavailable',
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
    mocks.summary.mockResolvedValue({ data: { summary: {
      average_aqi: 124,
      average_temperature_c: 34.2,
      average_green_cover_pct: 18.5,
      average_health_risk: 0.21,
      carbon_reduction_availability_reason: 'Carbon reduction is unavailable: the calibrated emissions inventory and factors are missing.',
    } } })
    mocks.wards.mockResolvedValue({ data: { wards: [ward] } })
    mocks.wardGeojson.mockResolvedValue({ data: null })
    mocks.scenarios.mockResolvedValue({ data: { scenarios: [] } })
    mocks.systemStatus.mockResolvedValue({ data: status })
    mocks.annualWardCarbon.mockResolvedValue({ data: {
      metadata: {
        estimate_label: 'MODELLED 2021 ROAD-TRAFFIC CO2',
        year: 2021,
        unit: 'tonnes CO2/year',
        source_name: 'CHETNA-Road Delhi road-traffic emissions dataset',
        source_url: 'https://doi.org/10.6084/m9.figshare.28330067.v2',
        methodology_file: 'CHETNA_Road_Delhi_CO2_methodology.md',
        methodology_summary: 'Fractional cell-polygon area allocation; NaN cells were not imputed.',
      },
      wards: [{ ward_id: 7, ward_name: 'Test Ward', annual_co2_tonnes: 123.456, valid_area_coverage_pct: 75, coverage_flag: 'PARTIAL_LT90%', contributing_grid_cells: 11 }],
    } })
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
          carbon_reduction_availability_reason: 'Carbon reduction unavailable: required emissions data is missing.',
        }],
      },
    })
    mocks.simulateScenario.mockResolvedValue({ data: {} })
    mocks.getSimulation.mockResolvedValue({ data: {} })
    mocks.calculateCarbonScenario.mockImplementation(async (payload: {
      scenario_name: string
      annual_vehicle_km: number
      input_classification: string
    }) => ({
      data: {
        scenario_id: 'SCN-CARBON-DEMO',
        scenario_name: payload.scenario_name,
        result_classification: payload.input_classification === 'Illustrative' ? 'SIMULATED' : payload.input_classification.toUpperCase(),
        display_label: payload.input_classification === 'Illustrative' ? 'SIMULATED SCENARIO — NOT MEASURED' : `${payload.input_classification.toUpperCase()} SCENARIO`,
        unit: 'tCO2/year',
        baseline_emissions_tco2_per_year: payload.annual_vehicle_km * 0.000938,
        project_emissions_tco2_per_year: payload.annual_vehicle_km * 0.00078,
        avoided_emissions_tco2_per_year: payload.annual_vehicle_km * 0.000158,
        percentage_change: -16.84,
        baseline_diesel_litres_per_year: payload.annual_vehicle_km * 0.35,
        project_electricity_kwh_per_year: payload.annual_vehicle_km * 1.2,
        annual_vehicle_km: payload.annual_vehicle_km,
        periods: {
          baseline_start: '2023-01-01',
          baseline_end: '2023-12-31',
          project_start: '2024-01-01',
          project_end: '2024-12-31',
        },
        assumptions: {
          service_boundary: 'Equal annual vehicle-kilometres in both cases.',
          period_basis: 'Annualized periods.',
          calculation: 'Activity × intensity × factor ÷ 1,000.',
          activity_source: 'Illustrative demonstration assumptions',
          activity_reference: 'Illustrative demonstration assumptions',
          input_classification: payload.input_classification,
          diesel_factor: {
            value_kg_co2_per_litre: 2.68,
            source: 'Illustrative',
            version: 'Demo',
            reference: 'Demo assumptions',
            status: payload.input_classification === 'Illustrative' ? 'Illustrative' : 'Unverified',
          },
          electricity_factor: {
            value_kg_co2_per_kwh: 0.65,
            source: 'Illustrative',
            version: 'Demo',
            reference: 'Demo assumptions',
            status: payload.input_classification === 'Illustrative' ? 'Illustrative' : 'Unverified',
          },
        },
      },
    }))
    mocks.calculateCarbon.mockResolvedValue({
      data: {
        status: 'calculated',
        method: 'activity_quantity_x_emission_factor',
        evidence_type: 'user_supplied_inputs',
        unit: 'kgCO2e/year',
        baseline_emissions_kgco2e_per_year: 150,
        projected_emissions_kgco2e_per_year: 80,
        reduction_kgco2e_per_year: 70,
        reduction_percent: 46.67,
        reduction_percent_note: null,
        direction: 'reduction',
        baseline_line_items: [{ name: 'grid electricity', quantity: 300, quantity_unit: 'kWh', period: 'year', emission_factor_kgco2e_per_unit: 0.5, factor_source: 'Synthetic test factor source', annual_quantity: 300, annual_emissions_kgco2e: 150 }],
        projected_line_items: [{ name: 'grid electricity', quantity: 160, quantity_unit: 'kWh', period: 'year', emission_factor_kgco2e_per_unit: 0.5, factor_source: 'Synthetic test factor source', annual_quantity: 160, annual_emissions_kgco2e: 80 }],
        warnings: ['Synthetic test result; not a measurement.'],
      },
    })
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

  it('explains why city-wide carbon reduction is unavailable', async () => {
    renderDashboard()
    expect(await screen.findByText(/calibrated emissions inventory and factors are missing/)).toBeInTheDocument()
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
    fireEvent.change(screen.getByLabelText(/Implementation duration \(years\)/), { target: { value: '2.5' } })
    fireEvent.click(screen.getByRole('button', { name: /generate candidate scenarios/i }))
    expect(await screen.findByText('Backend generated strategy')).toBeInTheDocument()
    expect(screen.getByText('Carbon reduction unavailable: required emissions data is missing.')).toBeInTheDocument()
    expect(screen.getAllByText(/no provenance-backed impact estimate or complete validated prediction input was supplied/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/no provenance-backed cost estimate is available/i)).toBeInTheDocument()
    expect(mocks.generateScenarios).toHaveBeenCalledWith(expect.objectContaining({
      city: 'Delhi',
      problem_statement: 'Reduce heat exposure',
      implementation_period_years: 2.5,
    }))
  })

  it('renders supplied zero AQI, temperature, and cost estimates as valid values', async () => {
    mocks.generateScenarios.mockResolvedValue({
      data: {
        city: 'Delhi',
        scenarios: [{
          scenario_id: 'SCN-ZERO-METRICS',
          scenario_version: 1,
          name: 'Verified zero impact',
          description: 'Zero estimates supplied with provenance.',
          city: 'Delhi',
          status: 'VALIDATED',
          estimated_cost: {
            total_estimated_cost: 0,
            currency: 'INR',
            provenance: [{ source_type: 'validated_model', source_id: 'cost-model' }],
          },
          expected_impacts: {
            expected_aqi_change: 0,
            expected_uhi_change: 0,
            units: { aqi: 'AQI points', temperature: '°C' },
            provenance: [{ source_type: 'validated_model', source_id: 'impact-model' }],
          },
        }],
      },
    })
    renderDashboard()
    fireEvent.click(await screen.findByRole('navigation').then((navigation) => within(navigation).findByRole('link', { name: /scenario lab/i })))
    fireEvent.change(await screen.findByLabelText('Problem statement'), { target: { value: 'Reduce heat exposure' } })
    fireEvent.change(screen.getByLabelText(/Implementation duration \(years\)/), { target: { value: '2' } })
    fireEvent.click(screen.getByRole('button', { name: /generate candidate scenarios/i }))

    const card = (await screen.findByText('Verified zero impact')).closest<HTMLElement>('.scenario-card')
    if (!card) throw new Error('Zero estimate scenario card was not rendered.')
    expect(within(card).getByText('0 INR')).toBeInTheDocument()
    expect(within(card).getByText('0 AQI points')).toBeInTheDocument()
    expect(within(card).getByText('0 °C')).toBeInTheDocument()
    for (const label of ['Estimated cost', 'AQI change', 'UHI change']) {
      const metric = within(card).getByText(label).closest<HTMLElement>('.data-field')
      if (!metric) throw new Error(`${label} metric was not rendered.`)
      expect(within(metric).queryByText('Unavailable')).not.toBeInTheDocument()
    }
  })

  it('shows the modelled historical ward estimate and coverage separately from Carbon Reduction', async () => {
    renderDashboard()
    expect(await screen.findByText('Modelled 2021 Road-Traffic CO2')).toBeInTheDocument()
    expect(screen.getByText('123.46')).toBeInTheDocument()
    expect(screen.getByText('75%')).toBeInTheDocument()
    expect(screen.getByText('Partial valid-area coverage')).toBeInTheDocument()
    expect(screen.getByText(/modelled historical road-traffic CO2, not measured, current, or all-sector emissions/i)).toBeInTheDocument()
    expect(screen.getByText('Carbon reduction')).toBeInTheDocument()
    expect(screen.getByText(/Carbon reduction is unavailable: the calibrated emissions inventory and factors are missing/i)).toBeInTheDocument()
    expect(mocks.annualWardCarbon).toHaveBeenCalledOnce()
  })

  it('keeps historical carbon endpoint failures local to its panel', async () => {
    mocks.annualWardCarbon.mockRejectedValue(new Error('Annual carbon endpoint unavailable'))
    renderDashboard()
    expect(await screen.findByText(/Ward carbon data unavailable: Annual carbon endpoint unavailable/i)).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getByText('Air quality index')).toBeInTheDocument()
  })

  it('passes a planner schedule through simulation and explicitly optimizes execution time', async () => {
    const scheduleSource = 'user_input: Planner-supplied implementation schedule'
    mocks.generateScenarios.mockResolvedValue({
      data: {
        city: 'Delhi',
        scenarios: [{
          scenario_id: 'SCN-EXECUTION-TIME',
          scenario_version: 1,
          name: 'Scheduled urban forest',
          description: 'Planner-supplied schedule.',
          city: 'Delhi',
          status: 'REQUIRES_REVIEW',
          provenance: {
            implementation_schedule: {
              duration_years: 2.5,
              source_type: 'user_input',
              source: 'Planner-supplied implementation schedule',
            },
          },
        }],
      },
    })
    mocks.simulateScenario.mockResolvedValue({
      data: {
        simulation_id: 'SIM-EXECUTION-TIME',
        scenario_id: 'SCN-EXECUTION-TIME',
        status: 'completed',
        baseline_state: { city: 'Delhi' },
        simulated_state: { city: 'Delhi', execution_time: 2.5 },
        metrics: {
          execution_time: {
            baseline_value: null,
            simulated_value: 2.5,
            absolute_delta: null,
            percentage_delta: null,
            unit: 'years',
            source_model: scheduleSource,
            availability: 'available',
          },
          aqi: {
            baseline_value: 35,
            simulated_value: null,
            absolute_delta: null,
            percentage_delta: null,
            unit: 'AQI',
            source_model: 'unavailable: no validated intervention effect',
            availability: 'unavailable',
            availability_reason: 'No validated intervention effect is available.',
          },
        },
      },
    })
    mocks.optimize.mockResolvedValue({
      data: {
        optimization_id: 'OPT-EXECUTION-TIME',
        status: 'completed',
        objectives: [{ name: 'execution_time', direction: 'minimize' }],
        constraints: [],
        pareto_solutions: [{
          scenario_id: 'SCN-EXECUTION-TIME',
          simulation_id: 'SIM-EXECUTION-TIME',
          objective_values: { execution_time: 2.5 },
          objective_sources: { execution_time: scheduleSource },
          pareto_rank: 1,
        }],
        dominated_strategies: [],
        infeasible_strategies: [],
        unevaluable_strategies: [],
        scores: [],
      },
    })

    renderDashboard()
    fireEvent.click(await screen.findByRole('navigation').then((navigation) => within(navigation).findByRole('link', { name: /scenario lab/i })))
    fireEvent.change(await screen.findByLabelText('Problem statement'), { target: { value: 'Low green cover' } })
    fireEvent.change(screen.getByLabelText(/Implementation duration \(years\)/), { target: { value: '2.5' } })
    fireEvent.click(screen.getByRole('button', { name: /generate candidate scenarios/i }))
    expect(await screen.findByText('Scheduled urban forest')).toBeInTheDocument()

    fireEvent.click(await screen.findByRole('navigation').then((navigation) => within(navigation).findByRole('link', { name: /^simulation$/i })))
    fireEvent.change(await screen.findByLabelText('Candidate scenario'), { target: { value: 'SCN-EXECUTION-TIME' } })
    fireEvent.click(screen.getByRole('button', { name: /run simulation/i }))
    expect(await screen.findByText(scheduleSource)).toBeInTheDocument()
    expect(mocks.simulateScenario).toHaveBeenCalledWith(expect.objectContaining({
      scenario: expect.objectContaining({ scenario_id: 'SCN-EXECUTION-TIME' }),
    }))

    fireEvent.click(await screen.findByRole('navigation').then((navigation) => within(navigation).findByRole('link', { name: /^optimization$/i })))
    fireEvent.click(await screen.findByLabelText(/Execution time \(years\)/))
    fireEvent.click(screen.getByRole('button', { name: /run optimization/i }))
    expect(await screen.findByText('2.5 years')).toBeInTheDocument()
    expect(mocks.optimize).toHaveBeenCalledWith(expect.objectContaining({
      objectives: [{ name: 'execution_time', direction: 'minimize' }],
    }))
    expect(screen.getAllByText(scheduleSource).length).toBeGreaterThan(0)
  })

  it('renders numeric baseline-equal metrics and unavailable reasons from a saved simulation', async () => {
    mocks.getSimulation.mockResolvedValue({
      data: {
        simulation_id: 'SIM-158AF5F07F51',
        scenario_id: 'SCN-82A1B073421C',
        status: 'completed',
        baseline_state: { city: 'Delhi', zone: 'Ward_80' },
        simulated_state: { city: 'Delhi', zone: 'Ward_80' },
        metrics: {
          aqi: { baseline_value: 24.91, simulated_value: 24.91, absolute_delta: 0, unit: 'AQI', source_model: 'Phase 5 Digital Twin (CHANDNI CHOWK, Ward_80)', availability: 'available' },
          temperature: { baseline_value: 34.81, simulated_value: 34.81, absolute_delta: 0, unit: '°C', source_model: 'Phase 5 Digital Twin (CHANDNI CHOWK, Ward_80)', availability: 'available' },
          green_cover: { baseline_value: 2.23, simulated_value: 2.23, absolute_delta: 0, unit: '%', source_model: 'Phase 5 Digital Twin (CHANDNI CHOWK, Ward_80)', availability: 'available' },
          health_risk: { baseline_value: 0.1664, simulated_value: 0.1664, absolute_delta: 0, unit: 'score', source_model: 'Phase 5 Digital Twin (CHANDNI CHOWK, Ward_80)', availability: 'available' },
          health_benefit: { baseline_value: -0.1664, simulated_value: -0.1664, absolute_delta: 0, unit: 'inverse health-risk score', source_model: 'derived from health-risk score', availability: 'available' },
          carbon_impact: { baseline_value: null, simulated_value: null, absolute_delta: null, unit: 'tCO2e/year', source_model: 'unavailable', availability: 'unavailable', availability_reason: 'Carbon impact is unavailable because the carbon artifact is a placeholder.' },
          carbon_emissions: { baseline_value: null, simulated_value: null, absolute_delta: null, unit: 'tCO2e/year', source_model: 'unavailable', availability: 'unavailable', availability_reason: 'No scenario-specific absolute emissions inventory was supplied.' },
          cost: { baseline_value: null, simulated_value: null, absolute_delta: null, unit: 'INR', source_model: 'unavailable', availability: 'unavailable', availability_reason: 'No provenance-backed scenario cost estimate is available.' },
          population_exposure: { baseline_value: null, simulated_value: null, absolute_delta: null, unit: 'people', source_model: 'unavailable', availability: 'unavailable', availability_reason: 'No validated scenario exposure estimate is available.' },
          execution_time: { baseline_value: null, simulated_value: null, absolute_delta: null, unit: 'years', source_model: 'unavailable', availability: 'unavailable', availability_reason: 'No implementation or deployment duration was supplied.' },
          sustainability: { baseline_value: null, simulated_value: null, absolute_delta: null, unit: 'score', source_model: 'unavailable', availability: 'unavailable', availability_reason: 'No validated sustainability estimate is available.' },
        },
      },
    })

    renderDashboard()
    fireEvent.click(await screen.findByRole('navigation').then((navigation) => within(navigation).findByRole('link', { name: /^simulation$/i })))
    fireEvent.change(await screen.findByLabelText('Load a persisted simulation'), { target: { value: 'SIM-158AF5F07F51' } })
    fireEvent.click(screen.getByRole('button', { name: /load result/i }))

    expect(await screen.findByText('SIM-158AF5F07F51')).toBeInTheDocument()
    expect(screen.getAllByText('24.9 AQI')).toHaveLength(2)
    expect(screen.getAllByText('34.8 °C')).toHaveLength(2)
    expect(screen.getAllByText('2.2 %')).toHaveLength(2)
    expect(screen.getAllByText('0.2 score')).toHaveLength(2)
    expect(screen.getAllByText('-0.2 inverse health-risk score')).toHaveLength(2)
    expect(screen.getByText('No provenance-backed scenario cost estimate is available.')).toBeInTheDocument()
    expect(screen.getByText('No implementation or deployment duration was supplied.')).toBeInTheDocument()
    expect(mocks.getSimulation).toHaveBeenCalledWith('SIM-158AF5F07F51')
  })

  it('does not offer saved carbon calculation records as Digital Twin simulation candidates', async () => {
    mocks.scenarios.mockResolvedValue({ data: { scenarios: [{
      scenario_id: 'SCN-CARBON-DEMO',
      scenario_version: 1,
      name: 'Illustrative bus electrification comparison',
      description: 'A standalone transport carbon calculation.',
      city: 'Delhi',
      status: 'SIMULATED',
      provenance: { carbon_scenario_result: { scenario_name: 'Illustrative bus electrification comparison' } },
    }, {
      scenario_id: 'SCN-DT-DEMO',
      scenario_version: 1,
      name: 'Urban Forest Expansion',
      description: 'A Digital Twin intervention candidate.',
      city: 'Delhi',
      zone: 'Ward_80',
      status: 'VALIDATED',
    }] } })

    renderDashboard('/simulation')

    const selector = await screen.findByLabelText('Candidate scenario')
    expect(within(selector).queryByRole('option', { name: /Illustrative bus electrification comparison/ })).not.toBeInTheDocument()
    expect(within(selector).getByRole('option', { name: /Urban Forest Expansion · SCN-DT-DEMO/ })).toBeInTheDocument()
  })

  it('rejects a missing or zero planner duration before scenario generation', async () => {
    renderDashboard()
    fireEvent.click(await screen.findByRole('navigation').then((navigation) => within(navigation).findByRole('link', { name: /scenario lab/i })))
    fireEvent.change(await screen.findByLabelText('Problem statement'), { target: { value: 'Low green cover' } })
    fireEvent.change(screen.getByLabelText(/Implementation duration \(years\)/), { target: { value: '0' } })
    fireEvent.click(screen.getByRole('button', { name: /generate candidate scenarios/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('positive finite implementation duration')
    expect(mocks.generateScenarios).not.toHaveBeenCalled()
  })

  it('opens Scenario Lab with editable illustrative defaults and calculates a simulated result through the backend', async () => {
    renderDashboard()
    fireEvent.click(await screen.findByRole('navigation').then((navigation) => within(navigation).findByRole('link', { name: /scenario lab/i })))
    expect(await screen.findByText('Illustrative demonstration assumptions')).toBeInTheDocument()
    expect(screen.getByDisplayValue('1000000')).toBeInTheDocument()
    expect(screen.getByDisplayValue('0.35')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /calculate scenario/i }))
    expect(await screen.findByText('SIMULATED SCENARIO — NOT MEASURED')).toBeInTheDocument()
    expect(screen.getByText('Saved scenario: SCN-CARBON-DEMO')).toBeInTheDocument()
    expect(screen.getByText('938 tCO2/year')).toBeInTheDocument()
    expect(screen.getByText('780 tCO2/year')).toBeInTheDocument()
    expect(screen.getByText('158 tCO2/year')).toBeInTheDocument()
    expect(mocks.calculateCarbonScenario).toHaveBeenCalledWith(expect.objectContaining({
      annual_vehicle_km: 1_000_000,
      diesel_litres_per_vehicle_km: 0.35,
      electric_kwh_per_vehicle_km: 1.2,
      input_classification: 'Illustrative',
      diesel_factor: expect.objectContaining({ status: 'Illustrative' }),
      electricity_factor: expect.objectContaining({ status: 'Illustrative' }),
    }))
  })

  it('uses edited activity for a fresh backend result and reset restores demo defaults', async () => {
    renderDashboard()
    fireEvent.click(await screen.findByRole('navigation').then((navigation) => within(navigation).findByRole('link', { name: /scenario lab/i })))
    const vehicleKm = await screen.findByLabelText(/Total annual vehicle-kilometres/)
    fireEvent.change(vehicleKm, { target: { value: '2000000' } })
    fireEvent.click(screen.getByRole('button', { name: /calculate scenario/i }))
    expect(await screen.findByText('1,876 tCO2/year')).toBeInTheDocument()
    expect(mocks.calculateCarbonScenario).toHaveBeenLastCalledWith(expect.objectContaining({ annual_vehicle_km: 2_000_000 }))
    fireEvent.click(screen.getByRole('button', { name: /reset to demo defaults/i }))
    expect(screen.getByLabelText(/Total annual vehicle-kilometres/)).toHaveValue(1_000_000)
    expect(screen.queryByTestId('carbon-scenario-result')).not.toBeInTheDocument()
  })

  it('rejects invalid numeric input before making a carbon calculation request', async () => {
    renderDashboard()
    fireEvent.click(await screen.findByRole('navigation').then((navigation) => within(navigation).findByRole('link', { name: /scenario lab/i })))
    fireEvent.change(await screen.findByLabelText(/Total annual vehicle-kilometres/), { target: { value: '0' } })
    fireEvent.click(screen.getByRole('button', { name: /calculate scenario/i }))
    expect(mocks.calculateCarbonScenario).not.toHaveBeenCalled()
  })

  it('shows factor limitations and backend validation when illustrative inputs are relabelled estimated', async () => {
    mocks.calculateCarbonScenario.mockRejectedValue(new Error('Replace illustrative emission factors before classifying this scenario as Estimated or Measured.'))
    renderDashboard()
    fireEvent.click(await screen.findByRole('navigation').then((navigation) => within(navigation).findByRole('link', { name: /scenario lab/i })))
    expect(screen.getByText(/neither emission factor is an official or verified factor/i)).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Input data classification'), { target: { value: 'Estimated' } })
    fireEvent.click(screen.getByRole('button', { name: /calculate scenario/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Replace illustrative emission factors')
    expect(mocks.calculateCarbonScenario).toHaveBeenCalledWith(expect.objectContaining({
      input_classification: 'Estimated',
      diesel_factor: expect.objectContaining({ status: 'Illustrative' }),
    }))
    expect(screen.queryByTestId('carbon-scenario-result')).not.toBeInTheDocument()
  })

  it('submits sourced baseline and projected activities to the activity carbon API', async () => {
    renderDashboard()
    fireEvent.click(await screen.findByRole('navigation').then((navigation) => within(navigation).findByRole('link', { name: /scenario lab/i })))
    const baseline = await screen.findByRole('region', { name: 'baseline activities' })
    const projected = screen.getByRole('region', { name: 'projected activities' })
    for (const [section, quantity] of [[baseline, '300'], [projected, '160']] as const) {
      fireEvent.change(within(section).getByLabelText('Activity name'), { target: { value: 'grid electricity' } })
      fireEvent.change(within(section).getByLabelText('Quantity'), { target: { value: quantity } })
      fireEvent.change(within(section).getByLabelText('Quantity unit'), { target: { value: 'kWh' } })
      fireEvent.change(within(section).getByLabelText(/kg CO₂e/), { target: { value: '0.5' } })
      fireEvent.change(within(section).getByLabelText('Emission factor source / reference'), { target: { value: 'Synthetic test factor source' } })
    }
    fireEvent.click(screen.getByRole('button', { name: /calculate co/i }))
    expect(await screen.findByTestId('activity-carbon-result')).toBeInTheDocument()
    expect(screen.getByText('150 kgCO2e/year')).toBeInTheDocument()
    expect(screen.getByText('80 kgCO2e/year')).toBeInTheDocument()
    expect(screen.getByText('70 kgCO2e/year')).toBeInTheDocument()
    expect(mocks.calculateCarbon).toHaveBeenCalledWith({
      baseline: [{ name: 'grid electricity', quantity: 300, quantity_unit: 'kWh', period: 'year', emission_factor_kgco2e_per_unit: 0.5, factor_source: 'Synthetic test factor source' }],
      projected: [{ name: 'grid electricity', quantity: 160, quantity_unit: 'kWh', period: 'year', emission_factor_kgco2e_per_unit: 0.5, factor_source: 'Synthetic test factor source' }],
    })
  })

  it('requires explicit zero quantities or factors instead of treating empty fields as zero', async () => {
    renderDashboard()
    fireEvent.click(await screen.findByRole('navigation').then((navigation) => within(navigation).findByRole('link', { name: /scenario lab/i })))
    const baseline = await screen.findByRole('region', { name: 'baseline activities' })
    fireEvent.change(within(baseline).getByLabelText('Activity name'), { target: { value: 'fuel' } })
    fireEvent.change(within(baseline).getByLabelText('Quantity unit'), { target: { value: 'litre' } })
    fireEvent.change(within(baseline).getByLabelText('Emission factor source / reference'), { target: { value: 'Synthetic test factor source' } })
    fireEvent.submit(screen.getByTestId('activity-carbon-form'))
    expect(await screen.findByRole('alert')).toHaveTextContent('enter 0 explicitly')
    expect(mocks.calculateCarbon).not.toHaveBeenCalled()
  })

  it('displays a provenance-backed carbon estimate with its annual CO2e unit', async () => {
    mocks.generateScenarios.mockResolvedValue({
      data: {
        city: 'Delhi',
        scenarios: [{
          scenario_id: 'SCN-CARBON',
          scenario_version: 1,
          name: 'Evidence-backed strategy',
          description: 'Scenario estimate supplied with declared provenance.',
          city: 'Delhi',
          status: 'VALIDATED',
          expected_impacts: {
            expected_carbon_reduction: 2.75,
            provenance: [{ source_type: 'evidence', source_id: 'test-evidence' }],
          },
        }, {
          scenario_id: 'SCN-CARBON-ZERO',
          scenario_version: 1,
          name: 'Evidence-backed zero reduction',
          description: 'Zero is a supplied value, not an unavailable metric.',
          city: 'Delhi',
          status: 'VALIDATED',
          expected_impacts: {
            expected_carbon_reduction: 0,
            provenance: [{ source_type: 'evidence', source_id: 'test-zero-evidence' }],
          },
        }],
      },
    })
    renderDashboard()
    fireEvent.click(await screen.findByRole('navigation').then((navigation) => within(navigation).findByRole('link', { name: /scenario lab/i })))
    fireEvent.change(await screen.findByLabelText('Problem statement'), { target: { value: 'Reduce carbon emissions' } })
    fireEvent.change(screen.getByLabelText(/Implementation duration \(years\)/), { target: { value: '2.5' } })
    fireEvent.click(screen.getByRole('button', { name: /generate candidate scenarios/i }))
    expect(await screen.findByText('Evidence-backed strategy')).toBeInTheDocument()
    const evidencedScenario = screen.getByText('Evidence-backed strategy').closest<HTMLElement>('.scenario-card')
    if (!evidencedScenario) throw new Error('Evidence-backed scenario was not rendered.')
    const carbonMetric = within(evidencedScenario).getByText('Carbon reduction').closest<HTMLElement>('.data-field')
    if (!carbonMetric) throw new Error('Carbon reduction metric field was not rendered.')
    expect(within(carbonMetric).getByText('2.75 tCO₂e/year')).toBeInTheDocument()
    expect(within(carbonMetric).queryByText('Unavailable')).not.toBeInTheDocument()
    const zeroScenario = screen.getByText('Evidence-backed zero reduction').closest<HTMLElement>('.scenario-card')
    if (!zeroScenario) throw new Error('Zero carbon reduction scenario was not rendered.')
    const zeroCarbonMetric = within(zeroScenario).getByText('Carbon reduction').closest<HTMLElement>('.data-field')
    if (!zeroCarbonMetric) throw new Error('Zero carbon reduction metric field was not rendered.')
    expect(within(zeroCarbonMetric).getByText('0 tCO₂e/year')).toBeInTheDocument()
  })

  it('keeps a non-finite carbon value unavailable and shows its explanation', async () => {
    mocks.generateScenarios.mockResolvedValue({
      data: {
        city: 'Delhi',
        scenarios: [{
          scenario_id: 'SCN-NAN-CARBON',
          scenario_version: 1,
          name: 'Invalid carbon response',
          description: 'A non-finite value must not be rendered as a metric.',
          city: 'Delhi',
          status: 'VALIDATED',
          carbon_reduction_availability_reason: 'Carbon reduction is unavailable: the estimate is not finite.',
          expected_impacts: { expected_carbon_reduction: Number.NaN },
        }],
      },
    })
    renderDashboard()
    fireEvent.click(await screen.findByRole('navigation').then((navigation) => within(navigation).findByRole('link', { name: /scenario lab/i })))
    fireEvent.change(await screen.findByLabelText('Problem statement'), { target: { value: 'Reduce carbon emissions' } })
    fireEvent.change(screen.getByLabelText(/Implementation duration \(years\)/), { target: { value: '2.5' } })
    fireEvent.click(screen.getByRole('button', { name: /generate candidate scenarios/i }))
    expect(await screen.findByText('Invalid carbon response')).toBeInTheDocument()
    const carbonMetric = screen.getByText('Carbon reduction').closest<HTMLElement>('.data-field')
    if (!carbonMetric) throw new Error('Carbon reduction metric field was not rendered.')
    expect(within(carbonMetric).getByText('Carbon reduction is unavailable: the estimate is not finite.')).toBeInTheDocument()
    expect(within(carbonMetric).getByText('Unavailable')).toBeInTheDocument()
    expect(screen.queryByText(/NaN|%/)).not.toBeInTheDocument()
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
