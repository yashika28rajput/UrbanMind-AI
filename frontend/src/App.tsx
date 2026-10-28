import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import {
  Activity, ArrowDownRight, BarChart3, BookOpen, Check, ChevronDown, Database,
  CircleHelp, Clock3, Cpu, FileSearch, FlaskConical, Gauge, Layers3, Leaf, LogOut,
  Map as MapIcon, MapPin, Menu, RefreshCw, ShieldCheck, Sparkles, Target, Thermometer, Wind,
} from 'lucide-react'
import {
  NavLink, Navigate, Route, Routes, useLocation, useNavigate,
} from 'react-router-dom'
import { errorMessage, formatMetric, requests } from './api'
import type { MapMetric } from './components/CityMap'
import DataManagementPage from './components/DataManagementPage'
import type {
  AnnualWardCarbonResponse, AuthConfig, CarbonActivityInput, CarbonCalculationRequest, CarbonCalculationResult,
  CarbonScenarioRequest, CarbonScenarioResult, CitySummary, OptimizationResult, Scenario, ScenarioSet,
  SimulationResult, SystemStatus, Ward, WardFeatureCollection,
} from './types'

type PageData = {
  summary: CitySummary | null
  wards: Ward[]
  geojson: WardFeatureCollection | null
  scenarios: Scenario[]
  status: SystemStatus | null
}

const emptyData: PageData = { summary: null, wards: [], geojson: null, scenarios: [], status: null }
const CityMap = lazy(async () => {
  const module = await import('./components/CityMap')
  return { default: module.CityMap }
})
const ParetoChart = lazy(() => import('./components/ParetoChart'))

const navigation = [
  { to: '/overview', label: 'Overview', icon: Gauge },
  { to: '/city-twin', label: 'City Twin', icon: MapIcon },
  { to: '/scenarios', label: 'Scenario Lab', icon: FlaskConical },
  { to: '/data-management', label: 'Data Management', icon: Database },
  { to: '/simulation', label: 'Simulation', icon: Activity },
  { to: '/optimization', label: 'Optimization', icon: BarChart3 },
  { to: '/decision-center', label: 'Decision Center', icon: Target },
  { to: '/explainability', label: 'Explainability', icon: Sparkles },
  { to: '/evidence', label: 'Evidence / RAG', icon: BookOpen },
  { to: '/system-status', label: 'System Status', icon: Cpu },
]

const pageNames: Record<string, string> = {
  '/overview': 'City overview',
  '/city-twin': 'City twin',
  '/scenarios': 'Scenario lab',
  '/data-management': 'Environmental data management',
  '/simulation': 'Simulation',
  '/optimization': 'Optimization',
  '/decision-center': 'Decision center',
  '/explainability': 'Explainability',
  '/evidence': 'Evidence & urban memory',
  '/system-status': 'System status',
}

function Panel({
  title, eyebrow, action, className = '', children,
}: {
  title: string
  eyebrow?: string
  action?: ReactNode
  className?: string
  children: ReactNode
}) {
  return (
    <section className={`panel ${className}`}>
      <div className="panel-heading">
        <div>{eyebrow && <span className="eyebrow">{eyebrow}</span>}<h2>{title}</h2></div>
        {action}
      </div>
      {children}
    </section>
  )
}

function InlineError({ message }: { message: string }) {
  return <div className="inline-error" role="alert"><CircleHelp size={16} /><span>{message}</span></div>
}

function EmptyState({ title, detail }: { title: string; detail: string }) {
  return <div className="empty-state"><span className="empty-icon"><CircleHelp size={19} /></span><strong>{title}</strong><p>{detail}</p></div>
}

function StatusPill({ status }: { status?: string }) {
  const normalized = (status ?? 'unknown').toLowerCase().replaceAll('_', '-')
  return <span className={`status-pill status-${normalized}`}><span />{(status ?? 'Unknown').replaceAll('_', ' ')}</span>
}

function MetricCard({
  label, value, unit, icon: Icon, accent = 'mint', note,
}: {
  label: string
  value: string
  unit?: string
  icon: typeof Wind
  accent?: string
  note?: string
}) {
  return (
    <article className={`metric-card accent-${accent}`}>
      <div className="metric-card-top"><span>{label}</span><span className="metric-icon"><Icon size={17} /></span></div>
      <div className="metric-value">{value}<small>{unit}</small></div>
      <div className="metric-note">{note ?? 'Current city twin'}</div>
    </article>
  )
}

function DataField({ label, value, unit = '', unavailableReason, digits = 1 }: { label: string; value: unknown; unit?: string; unavailableReason?: string | null; digits?: number }) {
  const isAvailable = typeof value === 'number' && Number.isFinite(value)
  return <div className="data-field"><span>{label}</span><strong>{isAvailable ? `${formatMetric(value, digits)}${unit}` : 'Unavailable'}</strong>{!isAvailable && <small className="data-field-reason">{unavailableReason ?? 'No valid numeric value was supplied for this metric.'}</small>}</div>
}

function HistoricalWardCarbon({ ward, result, error }: { ward: Ward | null; result: AnnualWardCarbonResponse | null; error: string }) {
  const estimate = ward && result?.wards.find((item) => item.ward_id === ward.ward_no)
  return (
    <section className="historical-carbon-panel" aria-label="Modelled 2021 Road-Traffic CO2">
      <div className="historical-carbon-heading"><div><span className="eyebrow">HISTORICAL ESTIMATE</span><h3>Modelled 2021 Road-Traffic CO2</h3></div></div>
      {error ? <p className="historical-carbon-status" role="status">Ward carbon data unavailable: {error}</p> : !result ? <p className="historical-carbon-status" role="status">Loading historical ward estimate…</p> : (
        <>
          <div className="historical-carbon-value">
            <strong>{estimate && typeof estimate.annual_co2_tonnes === 'number' ? formatMetric(estimate.annual_co2_tonnes, 2) : 'Unavailable'}</strong>
            <span>{result.metadata.unit}</span>
          </div>
          {estimate && <div className="historical-carbon-coverage">
            <span>{estimate.coverage_flag === 'PARTIAL_LT90%' ? 'Partial valid-area coverage' : estimate.coverage_flag === 'NO_COVERAGE' ? 'No valid-area coverage' : 'Adequate valid-area coverage'}</span>
            <strong>{typeof estimate.valid_area_coverage_pct === 'number' ? `${formatMetric(estimate.valid_area_coverage_pct, 2)}%` : 'Unavailable'}</strong>
          </div>}
          {!estimate && ward && <p className="historical-carbon-status">No annual row matched ward ID {ward.ward_no}; estimate unavailable.</p>}
          <p className="historical-carbon-status">{result.metadata.estimate_label}. This is modelled historical road-traffic CO2, not measured, current, or all-sector emissions.</p>
          <p className="historical-carbon-status">{result.metadata.methodology_summary}</p>
          <div className="historical-carbon-source"><a href={result.metadata.source_url} target="_blank" rel="noreferrer">{result.metadata.source_name}</a><span>Methodology: {result.metadata.methodology_file}</span></div>
        </>
      )}
    </section>
  )
}

function JsonResult({ value }: { value: unknown }) {
  if (!value) return null
  return <pre className="json-result">{JSON.stringify(value, null, 2)}</pre>
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function Login({ config, onLogin }: { config: AuthConfig; onLogin: (token: string) => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      const response = await requests.login(username, password)
      onLogin(response.data.access_token)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="login-screen">
      <div className="login-art">
        <div className="login-art-grid" />
        <div className="login-brand"><span className="brand-mark"><Layers3 size={19} /></span><span>UrbanMind<span className="brand-ai">AI</span></span></div>
        <div className="login-quote"><span className="eyebrow">URBAN DECISION INTELLIGENCE</span><h1>See the city.<br /><em>Shape what comes next.</em></h1><p>Evidence-aware planning across the urban systems that matter.</p></div>
        <div className="login-orbit"><div /><div /><div /><span>DELHI<br /><small>28.61° N · 77.21° E</small></span></div>
        <span className="login-footnote">CITY TWIN · ENVIRONMENT · DECISIONS</span>
      </div>
      <section className="login-form-wrap">
        <div className="login-form-card">
          <span className="eyebrow">SECURE ACCESS</span>
          <h2>Welcome back</h2>
          <p>Sign in to your UrbanMind decision workspace.</p>
          {!config.configured && (
            <div className="setup-notice">
              <ShieldCheck size={17} />
              <span>Authentication is required but not configured. Set the dashboard credentials in the backend environment before signing in.</span>
            </div>
          )}
          {error && <InlineError message={error} />}
          <form onSubmit={submit} className="form-stack">
            <label>Username<input autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} required /></label>
            <label>Password<input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
            <button className="button button-primary button-wide" disabled={busy || !config.configured}>{busy ? 'Signing in…' : 'Continue to dashboard'}<span>↗</span></button>
          </form>
          <div className="login-security"><ShieldCheck size={14} /> Secure session · Tokens expire after 8 hours</div>
        </div>
      </section>
    </main>
  )
}

function Overview({
  data, ward, annualCarbon, annualCarbonError, onSelectWard, onNavigate,
}: {
  data: PageData
  ward: Ward | null
  annualCarbon: AnnualWardCarbonResponse | null
  annualCarbonError: string
  onSelectWard: (number: number) => void
  onNavigate: (path: string) => void
}) {
  const [layer, setLayer] = useState<MapMetric>('aqi')
  const populationValues = data.wards
    .map((item) => item.population)
    .filter((value): value is number => typeof value === 'number' && Number.isFinite(value))
  const population = populationValues.length ? populationValues.reduce((total, value) => total + value, 0) : null
  const summary = data.summary

  return (
    <div className="page-grid overview-grid">
      <div className="metric-grid">
        <MetricCard label="Air quality index" value={formatMetric(summary?.average_aqi, 0)} icon={Wind} accent="coral" note={summary?.average_aqi == null ? 'No valid ward AQI observations are available' : 'Mean across mapped wards'} />
        <MetricCard label="Surface temperature" value={formatMetric(summary?.average_temperature_c)} unit="°C" icon={Thermometer} accent="amber" note={summary?.average_temperature_c == null ? 'No valid ward temperature observations are available' : 'Mean land surface temperature'} />
        <MetricCard label="Green cover" value={formatMetric(summary?.average_green_cover_pct)} unit="%" icon={Leaf} accent="mint" note="Digital Twin estimate" />
        <MetricCard label="Health risk" value={formatMetric(summary?.average_health_risk, 2)} icon={Activity} accent="violet" note="Normalized composite exposure score (0–1)" />
        <MetricCard
          label="Carbon reduction"
          value="Unavailable"
          icon={ArrowDownRight}
          accent="blue"
          note={data.summary?.carbon_reduction_availability_reason ?? 'No validated city-wide tCO2e estimate'}
        />
        <MetricCard label="Population represented" value={population === null ? 'Unavailable' : formatMetric(population, 0)} icon={MapIcon} accent="slate" note={population === null ? 'No valid ward population values are available' : `${data.wards.length} wards in the Digital Twin`} />
      </div>

      <div className="overview-main-grid">
        <Suspense fallback={<div className="map-shell map-loading">Loading ward map…</div>}><CityMap data={data.geojson} activeLayer={layer} onLayerChange={setLayer} selectedWard={ward?.ward_no ?? null} onWardSelect={onSelectWard} /></Suspense>
        <Panel title="Selected ward" eyebrow="DIGITAL TWIN / WARD DETAIL" className="ward-panel">
          {ward ? (
            <>
              <div className="ward-title"><div><span className="ward-code">WARD {ward.ward_no.toString().padStart(3, '0')}</span><h3>{ward.location || `Ward ${ward.ward_no}`}</h3></div>              <span className="ward-pin"><MapIcon size={16} /></span></div>
              <div className="ward-data-grid">
                <DataField label="AQI" value={ward.aqi} />
                <DataField label="Surface temperature" value={ward.temperature} unit="°C" />
                <DataField label="Green cover" value={ward.green_cover} unit="%" />
                <DataField label="Traffic index" value={ward.traffic_density} />
                <DataField label="Population" value={ward.population} />
                <DataField label="Composite health-risk score" value={ward.health_risk} unit=" (0–1)" />
              </div>
              <HistoricalWardCarbon ward={ward} result={annualCarbon} error={annualCarbonError} />
              <button className="text-link" onClick={() => onNavigate('/city-twin')}>Open ward in City Twin <span>↗</span></button>
            </>
          ) : <EmptyState title="Ward data unavailable" detail="Connect to the backend Digital Twin to view ward-level data." />}
        </Panel>
      </div>

      <div className="overview-bottom-grid">
        <Panel title="Scenario comparison" eyebrow="INTERVENTIONS" action={<button className="text-link" onClick={() => onNavigate('/scenarios')}>Scenario lab <span>↗</span></button>} className="scenario-preview">
          {data.scenarios.length ? (
            <div className="table-scroll"><table><thead><tr><th>Scenario</th><th>Status</th><th>AQI impact</th><th>Green cover</th><th>Carbon</th></tr></thead><tbody>
              {data.scenarios.slice(0, 4).map((scenario) => <tr key={scenario.scenario_id}><td><strong>{scenario.name}</strong><small>{scenario.scenario_id}</small></td><td><StatusPill status={scenario.status} /></td><td>{formatMetric(scenario.expected_impacts?.expected_aqi_change)}{scenario.expected_impacts?.expected_aqi_change == null && <small>No provenance-backed AQI impact estimate is available.</small>}</td><td>{formatMetric(scenario.expected_impacts?.expected_green_cover_change)}%</td><td>{formatMetric(scenario.expected_impacts?.expected_carbon_reduction)}{scenario.expected_impacts?.expected_carbon_reduction == null && <small>{scenario.carbon_reduction_availability_reason ?? 'No provenance-backed carbon reduction estimate is available.'}</small>}</td></tr>)}
            </tbody></table></div>
          ) : <EmptyState title="No scenarios yet" detail="Generate intervention scenarios to compare evidence-backed outcomes." />}
        </Panel>
        <Panel title="Decision intelligence" eyebrow="NEXT ACTION" className="recommendation-panel">
          <div className="recommendation-icon"><Target size={20} /></div>
          <h3>Move from indicators to action</h3>
          <p>Run a decision analysis using the current ward, problem statement, objectives and constraints.</p>
          <button className="button button-primary" onClick={() => onNavigate('/decision-center')}>Open Decision Center <span>↗</span></button>
          <div className="recommendation-foot"><span>ANALYSIS PIPELINE</span><span>SCENARIOS → SIMULATION → TRADE-OFFS</span></div>
        </Panel>
      </div>
      <div className="overview-footer-note"><span className="data-dot" /> City indicators use Digital Twin backend data. Carbon values remain unavailable until a scenario has been simulated.</div>
    </div>
  )
}

function WardPage({ data, ward, annualCarbon, annualCarbonError, onSelectWard }: { data: PageData; ward: Ward | null; annualCarbon: AnnualWardCarbonResponse | null; annualCarbonError: string; onSelectWard: (number: number) => void }) {
  const [layer, setLayer] = useState<MapMetric>('temperature')
  return (
    <div className="page-grid twin-layout">
      <div className="twin-intro"><div><span className="eyebrow">PHASE 05 · URBAN DIGITAL TWIN</span><h2>A living model of the city.</h2><p>Explore ward-level environmental and population indicators derived from the current Digital Twin state.</p></div><div className="twin-total"><strong>{data.wards.length || '—'}</strong><span>wards represented</span></div></div>
      <div className="twin-map-layout">
        <Suspense fallback={<div className="map-shell map-loading">Loading ward map…</div>}><CityMap data={data.geojson} activeLayer={layer} onLayerChange={setLayer} selectedWard={ward?.ward_no ?? null} onWardSelect={onSelectWard} /></Suspense>
        <Panel title={ward?.location ?? 'Select a ward'} eyebrow={ward ? `WARD ${ward.ward_no}` : 'WARD DETAIL'} className="twin-detail">
          {ward ? <>
            <div className="ward-data-grid twin-data-grid">
              <DataField label="Air quality index" value={ward.aqi} />
              <DataField label="Surface temperature" value={ward.temperature} unit="°C" />
              <DataField label="Green cover" value={ward.green_cover} unit="%" />
              <DataField label="Traffic index" value={ward.traffic_density} />
              <DataField label="Population" value={ward.population} />
              <DataField label="Composite health-risk score" value={ward.health_risk} unit=" (0–1)" />
            </div>
            <HistoricalWardCarbon ward={ward} result={annualCarbon} error={annualCarbonError} />
            <div className="detail-note"><Activity size={15} /> Values are provided by the Digital Twin API for this ward.</div>
          </> : <EmptyState title="Choose a map feature" detail="Select a ward polygon to inspect its urban state." />}
        </Panel>
      </div>
      <Panel title="City-level baseline" eyebrow="CURRENT DIGITAL TWIN STATE">
        <div className="baseline-strip">
          <DataField label="Mean AQI" value={data.summary?.average_aqi} />
          <DataField label="Mean temperature" value={data.summary?.average_temperature_c} unit="°C" />
          <DataField label="Mean green cover" value={data.summary?.average_green_cover_pct} unit="%" />
          <DataField label="Mean traffic index" value={data.summary?.average_traffic_density} />
          <DataField label="Mean health risk" value={data.summary?.average_health_risk} />
        </div>
      </Panel>
    </div>
  )
}

function ScenariosPage({
  wards, selectedWard, scenarios, onScenariosChanged,
}: {
  wards: Ward[]
  selectedWard: Ward | null
  scenarios: Scenario[]
  onScenariosChanged: (result: ScenarioSet) => void
}) {
  const [problem, setProblem] = useState('')
  const [objective, setObjective] = useState('')
  const [requestedInterventions, setRequestedInterventions] = useState('')
  const [implementationPeriodYears, setImplementationPeriodYears] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [generated, setGenerated] = useState<ScenarioSet | null>(null)
  const allScenarios = useMemo(() => {
    const map = new Map<string, Scenario>()
    ;[...scenarios, ...(generated?.scenarios ?? [])].forEach((item) => map.set(item.scenario_id, item))
    return [...map.values()]
  }, [scenarios, generated])

  const generate = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    const duration = Number(implementationPeriodYears)
    if (!implementationPeriodYears.trim() || !Number.isFinite(duration) || duration <= 0) {
      setError('Enter a positive finite implementation duration in years from the planner schedule.')
      return
    }
    setBusy(true)
    try {
      const result = (await requests.generateScenarios({
        city: 'Delhi',
        zone: selectedWard?.zone,
        problem_statement: problem.trim(),
        problems: [problem.trim()],
        objectives: objective.split(',').map((item) => item.trim()).filter(Boolean),
        requested_interventions: requestedInterventions.split(',').map((item) => item.trim()).filter(Boolean),
        implementation_period_years: duration,
        include_baseline: true,
        include_combinations: true,
        max_scenarios: 8,
      })).data
      setGenerated(result)
      onScenariosChanged(result)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page-grid">
      <div className="page-intro"><span className="eyebrow">PHASE 10 · INTERVENTION GENERATION</span><h2>Explore possible futures.</h2><p>Generate candidate strategies from the existing intervention catalog, then inspect their evidence, assumptions and status.</p></div>
      <div className="scenario-workspace">
        <Panel title="Define an urban challenge" eyebrow="SCENARIO REQUEST" className="scenario-form-panel">
          <form className="form-stack" onSubmit={generate}>
            <label>Problem statement<textarea rows={3} placeholder="Describe the urban condition you want to address…" value={problem} onChange={(event) => setProblem(event.target.value)} required /></label>
            <label>Primary objectives <span className="label-hint">Separate multiple objectives with commas</span><input value={objective} onChange={(event) => setObjective(event.target.value)} placeholder="Reduce air pollution, improve green cover" /></label>
            <label>Requested interventions <span className="label-hint">Optional · comma separated</span><input value={requestedInterventions} onChange={(event) => setRequestedInterventions(event.target.value)} placeholder="Name an intervention or leave blank" /></label>
            <label>Implementation duration (years) <span className="label-hint">Planner-supplied schedule · no default is assumed</span><input type="number" min="0" step="any" value={implementationPeriodYears} onChange={(event) => setImplementationPeriodYears(event.target.value)} placeholder="Enter duration from the approved plan" required /></label>
            <div className="request-context"><MapPin size={15} />Delhi · {selectedWard ? selectedWard.zone : 'City-wide'} · Baseline included</div>
            {error && <InlineError message={error} />}
            <button className="button button-primary button-wide" disabled={busy}>{busy ? <><RefreshCw size={15} className="spin" /> Generating scenarios…</> : <>Generate candidate scenarios <span>↗</span></>}</button>
          </form>
        </Panel>
        <Panel title="Generation context" eyebrow="BACKEND WORKFLOW">
          <div className="workflow-steps">
            <div className="workflow-step"><span>01</span><div><strong>Catalog matching</strong><p>Available interventions matched to the stated problem.</p></div></div>
            <div className="workflow-step"><span>02</span><div><strong>Constraint validation</strong><p>Backend validates available resources and policy constraints.</p></div></div>
            <div className="workflow-step"><span>03</span><div><strong>Evidence & estimates</strong><p>Impact and cost estimates retain their provenance.</p></div></div>
          </div>
          {selectedWard && <div className="context-summary"><span>Selected ward</span><strong>{selectedWard.location} · #{selectedWard.ward_no}</strong></div>}
          <div className="context-summary"><span>Digital Twin coverage</span><strong>{wards.length ? `${wards.length} ward states available` : 'Unavailable'}</strong></div>
        </Panel>
      </div>
      <CarbonScenarioForm />
      <ActivityCarbonCalculator />
      <Panel title="Candidate scenarios" eyebrow={`${allScenarios.length} AVAILABLE`} className="scenario-results">
        {allScenarios.length ? <div className="scenario-card-grid">{allScenarios.map((item) => <ScenarioCard key={item.scenario_id} scenario={item} />)}</div> : <EmptyState title="No generated scenarios" detail="Submit a problem statement to create backend-generated candidate interventions." />}
      </Panel>
    </div>
  )
}

function ScenarioCard({ scenario }: { scenario: Scenario }) {
  const impacts = scenario.expected_impacts
  const missingImpactReason = 'No provenance-backed impact estimate or complete validated prediction input was supplied.'
  return (
    <article className="scenario-card">
      <div className="scenario-card-top"><span className="scenario-mark"><Leaf size={17} /></span><StatusPill status={scenario.status} /></div>
      <h3>{scenario.name}</h3>
      <p>{scenario.description || 'No description provided by the scenario service.'}</p>
      <div className="scenario-card-metrics">
        <DataField
          label="Estimated cost"
          value={scenario.estimated_cost?.total_estimated_cost}
          unit={scenario.estimated_cost?.currency ? ` ${scenario.estimated_cost.currency}` : ''}
          unavailableReason={scenario.estimated_cost ? 'The scenario cost estimate has no total amount.' : 'No provenance-backed cost estimate is available; this intervention has no configured cost model.'}
          digits={0}
        />
        <DataField label="AQI change" value={impacts?.expected_aqi_change} unit={` ${impacts?.units?.aqi ?? 'AQI points'}`} unavailableReason={missingImpactReason} />
        <DataField label="UHI change" value={impacts?.expected_uhi_change} unit={` ${impacts?.units?.temperature ?? '°C'}`} unavailableReason={missingImpactReason} />
        <DataField label="Green cover" value={impacts?.expected_green_cover_change} unit={` ${impacts?.units?.green_cover ?? '%'}`} unavailableReason={missingImpactReason} />
        <DataField
          label="Carbon reduction"
          value={impacts?.expected_carbon_reduction}
          unit={` ${impacts?.units?.carbon_impact ?? 'tCO₂e/year'}`}
          unavailableReason={scenario.carbon_reduction_availability_reason ?? 'No provenance-backed carbon reduction estimate is available.'}
          digits={2}
        />
        <DataField label="Composite health-risk score change" value={impacts?.expected_health_risk_change} unit=" (0–1)" unavailableReason={missingImpactReason} />
      </div>
      <div className="scenario-card-foot"><span>{scenario.scenario_id}</span><span>Ward: {scenario.zone || 'City-wide'}</span></div>
    </article>
  )
}

type CarbonScenarioFormValues = {
  scenario_name: string
  annual_vehicle_km: string
  diesel_litres_per_vehicle_km: string
  electric_kwh_per_vehicle_km: string
  diesel_emission_factor_kg_co2_per_litre: string
  electricity_emission_factor_kg_co2_per_kwh: string
  baseline_period_start: string
  baseline_period_end: string
  project_period_start: string
  project_period_end: string
  activity_source: string
  activity_reference: string
  input_classification: 'Illustrative' | 'Estimated' | 'Measured'
  diesel_factor_source: string
  diesel_factor_version: string
  diesel_factor_reference: string
  diesel_factor_status: 'Illustrative' | 'Unverified' | 'Verified'
  electricity_factor_source: string
  electricity_factor_version: string
  electricity_factor_reference: string
  electricity_factor_status: 'Illustrative' | 'Unverified' | 'Verified'
}

type CarbonTextField =
  | 'scenario_name' | 'activity_source' | 'activity_reference'
  | 'diesel_factor_source' | 'diesel_factor_version' | 'diesel_factor_reference'
  | 'electricity_factor_source' | 'electricity_factor_version' | 'electricity_factor_reference'
type CarbonNumberField =
  | 'annual_vehicle_km' | 'diesel_litres_per_vehicle_km' | 'electric_kwh_per_vehicle_km'
  | 'diesel_emission_factor_kg_co2_per_litre' | 'electricity_emission_factor_kg_co2_per_kwh'
type CarbonDateField =
  | 'baseline_period_start' | 'baseline_period_end' | 'project_period_start' | 'project_period_end'

const carbonDemoDefaults: CarbonScenarioFormValues = {
  scenario_name: 'Illustrative bus electrification comparison',
  annual_vehicle_km: '1000000',
  diesel_litres_per_vehicle_km: '0.35',
  electric_kwh_per_vehicle_km: '1.2',
  diesel_emission_factor_kg_co2_per_litre: '2.68',
  electricity_emission_factor_kg_co2_per_kwh: '0.65',
  baseline_period_start: '2023-01-01',
  baseline_period_end: '2023-12-31',
  project_period_start: '2024-01-01',
  project_period_end: '2024-12-31',
  activity_source: 'Illustrative demonstration assumptions',
  activity_reference: 'User-editable demo defaults; not observed Delhi records',
  input_classification: 'Illustrative',
  diesel_factor_source: 'Illustrative demonstration assumption — not an official factor',
  diesel_factor_version: 'Demo assumption v1',
  diesel_factor_reference: 'Illustrative only; replace with a verified source before real-world use',
  diesel_factor_status: 'Illustrative',
  electricity_factor_source: 'Illustrative demonstration assumption — not an official factor',
  electricity_factor_version: 'Demo assumption v1',
  electricity_factor_reference: 'Illustrative only; replace with a verified source before real-world use',
  electricity_factor_status: 'Illustrative',
}

function CarbonScenarioForm() {
  const [values, setValues] = useState(carbonDemoDefaults)
  const [result, setResult] = useState<CarbonScenarioResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const update = <K extends keyof CarbonScenarioFormValues>(key: K, value: CarbonScenarioFormValues[K]) => {
    setValues((current) => ({ ...current, [key]: value }))
    setResult(null)
    setError('')
  }

  const calculate = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    const annualVehicleKm = Number(values.annual_vehicle_km)
    const dieselLitresPerKm = Number(values.diesel_litres_per_vehicle_km)
    const electricKwhPerKm = Number(values.electric_kwh_per_vehicle_km)
    const dieselFactor = Number(values.diesel_emission_factor_kg_co2_per_litre)
    const electricityFactor = Number(values.electricity_emission_factor_kg_co2_per_kwh)
    if ([annualVehicleKm, dieselLitresPerKm, electricKwhPerKm, dieselFactor, electricityFactor]
      .some((value) => !Number.isFinite(value) || value <= 0)) {
      setError('Enter finite values greater than zero for annual distance, energy intensities, and emission factors.')
      return
    }
    setBusy(true)
    try {
      const payload: CarbonScenarioRequest = {
        scenario_name: values.scenario_name.trim(),
        annual_vehicle_km: annualVehicleKm,
        diesel_litres_per_vehicle_km: dieselLitresPerKm,
        electric_kwh_per_vehicle_km: electricKwhPerKm,
        diesel_emission_factor_kg_co2_per_litre: dieselFactor,
        electricity_emission_factor_kg_co2_per_kwh: electricityFactor,
        baseline_period_start: values.baseline_period_start,
        baseline_period_end: values.baseline_period_end,
        project_period_start: values.project_period_start,
        project_period_end: values.project_period_end,
        activity_source: values.activity_source.trim(),
        activity_reference: values.activity_reference.trim(),
        input_classification: values.input_classification,
        diesel_factor: {
          source: values.diesel_factor_source.trim(),
          version: values.diesel_factor_version.trim(),
          reference: values.diesel_factor_reference.trim(),
          status: values.diesel_factor_status,
        },
        electricity_factor: {
          source: values.electricity_factor_source.trim(),
          version: values.electricity_factor_version.trim(),
          reference: values.electricity_factor_reference.trim(),
          status: values.electricity_factor_status,
        },
      }
      const response = await requests.calculateCarbonScenario(payload)
      setResult(response.data)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const reset = () => {
    setValues({ ...carbonDemoDefaults })
    setResult(null)
    setError('')
  }

  const textField = (
    label: string,
    key: CarbonTextField,
    hint?: string,
  ) => (
    <label>{label}{hint && <span className="label-hint">{hint}</span>}
      <input required value={values[key]} onChange={(event) => update(key, event.target.value)} />
    </label>
  )
  const numberField = (label: string, key: CarbonNumberField, unit: string) => (
    <label>{label} <span className="label-hint">{unit}</span>
      <input
        type="number"
        min="0.0000001"
        step="any"
        required
        value={values[key]}
        onChange={(event) => update(key, event.target.value)}
      />
    </label>
  )
  const dateField = (label: string, key: CarbonDateField) => (
    <label>{label}
      <input type="date" required value={values[key]} onChange={(event) => update(key, event.target.value)} />
    </label>
  )
  const selectField = (
    label: string,
    key: 'input_classification' | 'diesel_factor_status' | 'electricity_factor_status',
  ) => (
    <label>{label}
      <select value={values[key]} onChange={(event) => {
        const value = event.target.value
        if (key === 'input_classification') {
          update(key, value === 'Estimated' || value === 'Measured' ? value : 'Illustrative')
        } else {
          update(key, value === 'Verified' || value === 'Unverified' ? value : 'Illustrative')
        }
      }}>
        {(key === 'input_classification'
          ? ['Illustrative', 'Estimated', 'Measured']
          : ['Illustrative', 'Unverified', 'Verified']).map((option) => <option key={option}>{option}</option>)}
      </select>
    </label>
  )

  return (
    <Panel title="Carbon Reduction Scenario" eyebrow="TRANSPORT PILOT · BACKEND CALCULATION" className="carbon-scenario-panel">
      <div className="carbon-demo-notice">
        <strong>Illustrative demonstration assumptions</strong>
        <span>The defaults are not measured Delhi transport data and neither emission factor is an official or verified factor.</span>
      </div>
      <form className="carbon-scenario-form" onSubmit={calculate}>
        <div className="carbon-input-group">
          <h3>Scenario and activity</h3>
          <div className="carbon-input-grid">
            {textField('Scenario name', 'scenario_name')}
            {numberField('Total annual vehicle-kilometres', 'annual_vehicle_km', 'vehicle-km/year · shared baseline/project service')}
            {numberField('Diesel consumption intensity', 'diesel_litres_per_vehicle_km', 'litres/vehicle-km')}
            {numberField('Electric bus energy intensity', 'electric_kwh_per_vehicle_km', 'kWh/vehicle-km')}
            <label>Input data classification
              <select value={values.input_classification} onChange={(event) => {
                const value = event.target.value
                update('input_classification', value === 'Estimated' || value === 'Measured' ? value : 'Illustrative')
              }}>
                <option>Illustrative</option><option>Estimated</option><option>Measured</option>
              </select>
            </label>
            {textField('Activity data source', 'activity_source')}
            {textField('Activity data reference / provenance', 'activity_reference')}
          </div>
          <p className="carbon-form-note">Annual vehicle-kilometres are entered once and applied to both cases to avoid double-counting distance. Operating days are not needed because activity is already annualized.</p>
        </div>
        <div className="carbon-input-group">
          <h3>Reporting periods</h3>
          <div className="carbon-input-grid carbon-period-grid">
            {dateField('Baseline period start', 'baseline_period_start')}
            {dateField('Baseline period end', 'baseline_period_end')}
            {dateField('Project period start', 'project_period_start')}
            {dateField('Project period end', 'project_period_end')}
          </div>
        </div>
        <div className="carbon-input-group">
          <h3>Emission factors and provenance</h3>
          <div className="carbon-factor-grid">
            <section>
              <h4>Diesel combustion</h4>
              <div className="carbon-input-grid">
                {numberField('Diesel emission factor', 'diesel_emission_factor_kg_co2_per_litre', 'kg CO₂/litre')}
                {textField('Source', 'diesel_factor_source')}
                {textField('Version / year', 'diesel_factor_version')}
                {textField('Provenance / reference', 'diesel_factor_reference')}
                {selectField('Factor status', 'diesel_factor_status')}
              </div>
            </section>
            <section>
              <h4>Charging electricity</h4>
              <div className="carbon-input-grid">
                {numberField('Electricity emission factor', 'electricity_emission_factor_kg_co2_per_kwh', 'kg CO₂/kWh')}
                {textField('Source', 'electricity_factor_source')}
                {textField('Version / year', 'electricity_factor_version')}
                {textField('Provenance / reference', 'electricity_factor_reference')}
                {selectField('Factor status', 'electricity_factor_status')}
              </div>
            </section>
          </div>
          <p className="carbon-form-note">Estimated/measured classifications reject demo-only activity provenance or illustrative factors. Measured mode additionally requires both factors to be marked verified.</p>
        </div>
        {error && <InlineError message={error} />}
        <div className="carbon-form-actions">
          <button className="button button-primary" disabled={busy}>{busy ? 'Calculating…' : 'Calculate Scenario'}</button>
          <button className="button button-secondary" type="button" onClick={reset}>Reset to demo defaults</button>
        </div>
      </form>
      {result && <section className="carbon-result" aria-live="polite" data-testid="carbon-scenario-result">
        <div className="carbon-result-heading">
          <div><span className="eyebrow">BACKEND-CALCULATED RESULT</span><h3>{result.scenario_name}</h3>{result.scenario_id && <span className="label-hint">Saved scenario: {result.scenario_id}</span>}</div>
          <span className={`carbon-result-badge ${result.result_classification.toLowerCase()}`}>{result.display_label}</span>
        </div>
        <div className="carbon-result-grid">
          <DataField label="Baseline diesel emissions" value={result.baseline_emissions_tco2_per_year} unit={` ${result.unit}`} digits={2} />
          <DataField label="Project electricity emissions" value={result.project_emissions_tco2_per_year} unit={` ${result.unit}`} digits={2} />
          <DataField label="Avoided emissions (baseline − project)" value={result.avoided_emissions_tco2_per_year} unit={` ${result.unit}`} digits={2} />
          <DataField label="Project emissions change" value={result.percentage_change} unit={result.percentage_change === null ? '' : '%'} digits={2} />
        </div>
        <p className="carbon-form-note">Baseline activity: {formatMetric(result.baseline_diesel_litres_per_year, 2)} litres diesel/year · Project activity: {formatMetric(result.project_electricity_kwh_per_year, 2)} kWh/year · Service: {formatMetric(result.annual_vehicle_km, 0)} vehicle-km/year</p>
        <div className="carbon-provenance">
          <span>Diesel factor: {result.assumptions.diesel_factor.value_kg_co2_per_litre} kg CO₂/litre · {result.assumptions.diesel_factor.source} ({result.assumptions.diesel_factor.version}) · {result.assumptions.diesel_factor.status} · {result.assumptions.diesel_factor.reference}</span>
          <span>Electricity factor: {result.assumptions.electricity_factor.value_kg_co2_per_kwh} kg CO₂/kWh · {result.assumptions.electricity_factor.source} ({result.assumptions.electricity_factor.version}) · {result.assumptions.electricity_factor.status} · {result.assumptions.electricity_factor.reference}</span>
          <span>Activity provenance: {result.assumptions.activity_source} · {result.assumptions.activity_reference}</span>
        </div>
        <details className="carbon-method">
          <summary>Calculation method and period assumptions</summary>
          <p>{result.assumptions.calculation}</p>
          <p>{result.assumptions.service_boundary}</p>
          <p>Baseline: {result.periods.baseline_start} to {result.periods.baseline_end}. Project: {result.periods.project_start} to {result.periods.project_end}.</p>
        </details>
      </section>}
    </Panel>
  )
}

type CarbonActivityValues = {
  name: string
  quantity: string
  quantity_unit: string
  period: 'day' | 'month' | 'year'
  emission_factor_kgco2e_per_unit: string
  factor_source: string
}

const emptyCarbonActivity = (): CarbonActivityValues => ({
  name: '', quantity: '', quantity_unit: '', period: 'year',
  emission_factor_kgco2e_per_unit: '', factor_source: '',
})

function ActivityCarbonCalculator() {
  const [baseline, setBaseline] = useState<CarbonActivityValues[]>([emptyCarbonActivity()])
  const [projected, setProjected] = useState<CarbonActivityValues[]>([emptyCarbonActivity()])
  const [result, setResult] = useState<CarbonCalculationResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const updateActivity = (
    side: 'baseline' | 'projected', index: number, key: keyof CarbonActivityValues, value: string,
  ) => {
    const setter = side === 'baseline' ? setBaseline : setProjected
    setter((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, [key]: value } : row))
    setResult(null)
    setError('')
  }

  const parseActivities = (rows: CarbonActivityValues[], side: string): CarbonActivityInput[] => rows.map((row, index) => {
    const quantity = Number(row.quantity)
    const factor = Number(row.emission_factor_kgco2e_per_unit)
    if (!row.name.trim() || !row.quantity_unit.trim() || !row.factor_source.trim()) {
      throw new Error(`${side} activity ${index + 1} needs a name, unit, and emission-factor source.`)
    }
    if (!row.quantity.trim() || !row.emission_factor_kgco2e_per_unit.trim()) {
      throw new Error(`${side} activity ${index + 1} needs both a quantity and an emission factor; enter 0 explicitly when appropriate.`)
    }
    if (!Number.isFinite(quantity) || quantity < 0 || !Number.isFinite(factor) || factor < 0) {
      throw new Error(`${side} activity ${index + 1} needs finite, non-negative quantity and factor values.`)
    }
    if (row.factor_source.trim().length < 3) {
      throw new Error(`${side} activity ${index + 1} needs a source reference of at least 3 characters.`)
    }
    return {
      name: row.name.trim(),
      quantity,
      quantity_unit: row.quantity_unit.trim(),
      period: row.period,
      emission_factor_kgco2e_per_unit: factor,
      factor_source: row.factor_source.trim(),
    }
  })

  const calculate = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    let payload: CarbonCalculationRequest
    try {
      payload = {
        baseline: parseActivities(baseline, 'Baseline'),
        projected: parseActivities(projected, 'Projected'),
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Enter complete activity and factor provenance.')
      return
    }
    setBusy(true)
    try {
      setResult((await requests.calculateCarbon(payload)).data)
    } catch (cause) {
      setError(errorMessage(cause))
    } finally {
      setBusy(false)
    }
  }

  const renderActivities = (side: 'baseline' | 'projected', rows: CarbonActivityValues[]) => (
    <section className="activity-carbon-side" aria-label={`${side} activities`}>
      <div className="activity-carbon-heading"><h3>{side === 'baseline' ? 'Baseline activities' : 'Projected activities'}</h3>
        <button className="button button-secondary" type="button" onClick={() => {
          (side === 'baseline' ? setBaseline : setProjected)((current) => [...current, emptyCarbonActivity()])
          setResult(null)
        }}>Add activity</button>
      </div>
      {rows.map((row, index) => <fieldset className="activity-carbon-row" key={`${side}-${index}`}>
        <legend>Activity {index + 1}</legend>
        <label>Activity name<input required value={row.name} onChange={(event) => updateActivity(side, index, 'name', event.target.value)} placeholder="e.g. grid electricity" /></label>
        <label>Quantity<input required type="number" min="0" step="any" value={row.quantity} onChange={(event) => updateActivity(side, index, 'quantity', event.target.value)} /></label>
        <label>Quantity unit<input required value={row.quantity_unit} onChange={(event) => updateActivity(side, index, 'quantity_unit', event.target.value)} placeholder="e.g. kWh" /></label>
        <label>Reporting period<select value={row.period} onChange={(event) => updateActivity(side, index, 'period', event.target.value as CarbonActivityValues['period'])}>
          <option value="day">Per day</option><option value="month">Per month</option><option value="year">Per year</option>
        </select></label>
        <label>Emission factor <span className="label-hint">kg CO₂e / {row.quantity_unit || 'unit'}</span>
          <input required type="number" min="0" step="any" value={row.emission_factor_kgco2e_per_unit} onChange={(event) => updateActivity(side, index, 'emission_factor_kgco2e_per_unit', event.target.value)} /></label>
        <label>Emission factor source / reference<input required minLength={3} value={row.factor_source} onChange={(event) => updateActivity(side, index, 'factor_source', event.target.value)} placeholder="Publisher, table, year, or URL" /></label>
        {rows.length > 1 && <button className="button button-secondary" type="button" onClick={() => {
          (side === 'baseline' ? setBaseline : setProjected)((current) => current.filter((_, rowIndex) => rowIndex !== index))
          setResult(null)
        }}>Remove activity</button>}
      </fieldset>)}
    </section>
  )

  return (
    <Panel title="Activity-based Carbon Calculation" eyebrow="SOURCE-REQUIRED · CO₂e" className="carbon-scenario-panel">
      <div className="carbon-demo-notice"><strong>User-supplied assumptions</strong>
        <span>No activity, period, or emission factor is prefilled. Add sourced quantities and factors for both cases; results are calculations from those inputs, not measured outcomes or Delhi estimates.</span></div>
      <form className="activity-carbon-form" data-testid="activity-carbon-form" onSubmit={calculate}>
        {renderActivities('baseline', baseline)}
        {renderActivities('projected', projected)}
        <p className="carbon-form-note">Daily and monthly quantities are annualized by the backend. Match activity names and units across cases when comparing the same activity. Each emission factor needs a source or reference.</p>
        {error && <InlineError message={error} />}
        <button className="button button-primary" disabled={busy}>{busy ? 'Calculating…' : 'Calculate CO₂e'}</button>
      </form>
      {result && <section className="carbon-result" aria-live="polite" data-testid="activity-carbon-result">
        <div className="carbon-result-heading"><div><span className="eyebrow">CALCULATED FROM USER-SUPPLIED INPUTS</span><h3>Annual emissions comparison</h3></div>
          <span className="carbon-result-badge simulated">{result.direction.replace('_', ' ').toUpperCase()}</span></div>
        <div className="carbon-result-grid">
          <DataField label="Baseline emissions" value={result.baseline_emissions_kgco2e_per_year} unit={` ${result.unit}`} digits={2} />
          <DataField label="Projected emissions" value={result.projected_emissions_kgco2e_per_year} unit={` ${result.unit}`} digits={2} />
          <DataField label="Reduction (baseline − projected)" value={result.reduction_kgco2e_per_year} unit={` ${result.unit}`} digits={2} />
          <DataField label="Reduction percentage" value={result.reduction_percent} unit={result.reduction_percent === null ? '' : '%'} digits={2} unavailableReason={result.reduction_percent_note ?? undefined} />
        </div>
        <div className="carbon-provenance">
          <span>Baseline factors: {result.baseline_line_items.map((item) => `${item.name} — ${item.factor_source}`).join(' · ')}</span>
          <span>Projected factors: {result.projected_line_items.map((item) => `${item.name} — ${item.factor_source}`).join(' · ')}</span>
          {result.warnings.map((warning) => <span key={warning}>{warning}</span>)}
        </div>
        <details className="carbon-method">
          <summary>Annualized activity and factor details</summary>
          {([['Baseline', result.baseline_line_items], ['Projected', result.projected_line_items]] as const).map(([label, items]) => <section key={label}>
            <h4>{label}</h4>
            {items.map((item, index) => <p key={`${item.name}-${index}`}>
              {item.name}: {formatMetric(item.annual_quantity, 3)} {item.quantity_unit}/year × {formatMetric(item.emission_factor_kgco2e_per_unit, 5)} kgCO₂e/{item.quantity_unit} = {formatMetric(item.annual_emissions_kgco2e, 3)} kgCO₂e/year. Source: {item.factor_source}
            </p>)}
          </section>)}
          {result.reduction_percent_note && <p>{result.reduction_percent_note}</p>}
        </details>
      </section>}
    </Panel>
  )
}

function SimulationPage({
  scenarios, ward, simulations, onSimulation,
}: {
  scenarios: Scenario[]
  ward: Ward | null
  simulations: SimulationResult[]
  onSimulation: (result: SimulationResult) => void
}) {
  const [scenarioId, setScenarioId] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [savedSimulationId, setSavedSimulationId] = useState('')
  const scenario = scenarios.find((item) => item.scenario_id === scenarioId)
  const candidateScenarios = scenarios.filter((item) => !item.provenance?.carbon_scenario_result)
  const run = async () => {
    if (!scenario) return
    setError('')
    setBusy(true)
    try {
      const result = (await requests.simulateScenario({
        scenario,
        urban_state: {
          workflow_id: `dashboard-${scenario.scenario_id}`,
          request: { query: `Simulate ${scenario.name}`, city: scenario.city, zone: scenario.zone ?? '' },
        },
        simulation_input: { baseline_metrics: {} },
      })).data
      onSimulation(result)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }
  const loadSaved = async (event: FormEvent) => {
    event.preventDefault()
    if (!savedSimulationId.trim()) return
    setBusy(true)
    setError('')
    try {
      onSimulation((await requests.getSimulation(savedSimulationId.trim())).data)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }
  const latest = simulations[0]
  const metricLabels: Record<string, string> = {
    aqi: 'Air quality index', temperature: 'Surface temperature', green_cover: 'Green cover',
    health_risk: 'Composite health-risk score', carbon_emissions: 'Carbon emissions', carbon_impact: 'Carbon impact',
    execution_time: 'Implementation duration',
    population_exposure: 'Population exposure', health_benefit: 'Inverse composite health-risk score', cost: 'Cost',
  }

  return (
    <div className="page-grid">
      <div className="page-intro"><span className="eyebrow">PHASE 11 · DIGITAL TWIN SIMULATION</span><h2>Model the intervention.</h2><p>Compare backend-calculated baseline and simulated states. Metrics not supplied by the simulation engine are shown as unavailable.</p></div>
      <Panel title="Run a simulation" eyebrow="SCENARIO STATE" className="simulation-controls">
        <div className="simulation-run-row">
          <label className="select-label">Candidate scenario<select value={scenarioId} onChange={(event) => setScenarioId(event.target.value)}><option value="">Select a generated scenario</option>{candidateScenarios.map((item) => <option key={item.scenario_id} value={item.scenario_id}>{item.name} · {item.scenario_id}</option>)}</select></label>
          <div className="simulation-baseline"><span>Baseline state</span><strong>{ward?.location ?? 'City-level Digital Twin'}</strong><small>Resolved by the simulation service</small></div>
          <button className="button button-primary" onClick={run} disabled={!scenario || busy}>{busy ? 'Running…' : 'Run simulation'} <span>↗</span></button>
        </div>
        {error && <InlineError message={error} />}
      </Panel>
      <form className="saved-result-form" onSubmit={loadSaved}>
        <label>Load a persisted simulation<input value={savedSimulationId} onChange={(event) => setSavedSimulationId(event.target.value)} placeholder="SIM-…" /></label>
        <button className="button button-secondary" disabled={busy || !savedSimulationId.trim()}>Load result</button>
      </form>
      {latest ? (
        <>
          <div className="result-meta"><div><span className="eyebrow">SIMULATION RESULT</span><strong>{latest.simulation_id}</strong></div><StatusPill status={latest.status} /><span>Scenario {latest.scenario_id}</span></div>
          <Panel title="Baseline vs simulated state" eyebrow="MODEL OUTPUT" className="simulation-table-panel">
            <div className="table-scroll"><table className="comparison-table"><thead><tr><th>Metric</th><th>Baseline</th><th>Simulated</th><th>Change</th></tr></thead><tbody>
              {Object.entries(latest.metrics).map(([key, metric]) => {
                const unit = metric.unit && metric.unit !== 'dimensionless' ? ` ${metric.unit}` : ''
                const baseline = typeof metric.baseline_value === 'number' ? `${formatMetric(metric.baseline_value)}${unit}` : 'Unavailable'
                const simulated = typeof metric.simulated_value === 'number' ? `${formatMetric(metric.simulated_value)}${unit}` : 'Unavailable'
                const delta = typeof metric.absolute_delta === 'number' ? `${metric.absolute_delta > 0 ? '+' : ''}${formatMetric(metric.absolute_delta)}${unit}` : 'Unavailable'
                const missingReason = metric.availability_reason ?? (
                  metric.simulated_value == null
                    ? 'No validated simulated value is available for the required inputs.'
                    : metric.baseline_value == null && metric.absolute_delta == null
                      ? key === 'cost'
                        ? 'A baseline cost was not supplied; only the scenario cost estimate is available.'
                        : key === 'carbon_impact' || key === 'carbon_emissions'
                          ? 'A baseline emissions inventory was not supplied; the change cannot be calculated.'
                          : 'A Digital Twin baseline value was not supplied; the change cannot be calculated.'
                      : null
                )
                return <tr key={key}><td><strong>{metricLabels[key] ?? key.replaceAll('_', ' ')}</strong>{missingReason && <small>{missingReason}</small>}{key === 'execution_time' && metric.availability === 'available' && metric.source_model && <small>{metric.source_model}</small>}</td><td>{baseline}</td><td>{simulated}</td><td className={metric.absolute_delta != null && metric.absolute_delta < 0 ? 'positive-delta' : ''}>{delta}</td></tr>
              })}
            </tbody></table></div>
          </Panel>
        </>
      ) : <EmptyState title="No simulation result" detail="Choose a backend-generated scenario and run the Digital Twin simulation." />}
      {simulations.length > 1 && <div className="saved-results"><span>Saved in this session</span>{simulations.length} simulations available to Optimization</div>}
    </div>
  )
}

function OptimizationPage({
  simulations, result, onResult,
}: {
  simulations: SimulationResult[]
  result: OptimizationResult | null
  onResult: (result: OptimizationResult) => void
}) {
  const [selected, setSelected] = useState<string[]>(simulations.map((item) => item.simulation_id))
  const [executionTimeSelected, setExecutionTimeSelected] = useState(false)
  const [savedOptimizationId, setSavedOptimizationId] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => setSelected(simulations.map((item) => item.simulation_id)), [simulations])
  const selectedSims = simulations.filter((item) => selected.includes(item.simulation_id))
  const run = async () => {
    if (!selectedSims.length || !executionTimeSelected) return
    setBusy(true)
    setError('')
    try {
      onResult((await requests.optimize({
        simulations: selectedSims,
        objectives: [{ name: 'execution_time', direction: 'minimize' }],
      })).data)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }
  const loadSaved = async (event: FormEvent) => {
    event.preventDefault()
    const id = savedOptimizationId.trim()
    if (!id) return
    setBusy(true)
    setError('')
    try {
      const [stored, pareto] = await Promise.all([requests.getOptimization(id), requests.getPareto(id)])
      onResult({ ...stored.data, pareto_solutions: pareto.data.pareto_solutions })
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }
  const points = result?.pareto_solutions.flatMap((solution) => {
    const values = solution.objective_values
    const cost = values.cost
    const aqi = values.aqi
    return typeof cost === 'number' && typeof aqi === 'number'
      ? [{ cost, aqi, scenario_id: solution.scenario_id }]
      : []
  }) ?? []

  return (
    <div className="page-grid">
      <div className="page-intro"><span className="eyebrow">PHASE 12 · MULTI-OBJECTIVE OPTIMIZATION</span><h2>Make trade-offs visible.</h2><p>Compare feasible strategies across the simulation outputs. No frontend composite score is used.</p></div>
      <Panel title="Optimization inputs" eyebrow="SIMULATIONS & OBJECTIVES">
        {simulations.length ? <>
          <div className="simulation-select-list">{simulations.map((item) => <label key={item.simulation_id} className="simulation-select-item"><input type="checkbox" checked={selected.includes(item.simulation_id)} onChange={(event) => setSelected((current) => event.target.checked ? [...current, item.simulation_id] : current.filter((id) => id !== item.simulation_id))} /><span><strong>{item.scenario_id}</strong><small>{item.simulation_id} · {item.status}</small></span><Check size={16} /></label>)}</div>
          <label className="simulation-select-item"><input type="checkbox" checked={executionTimeSelected} onChange={(event) => setExecutionTimeSelected(event.target.checked)} /><span><strong>Execution time (years)</strong><small>Minimize using the planner-supplied schedule</small></span><Check size={16} /></label>
          <div className="objective-note"><Target size={16} />Only explicitly selected, supported objectives are sent. Environmental objectives remain unavailable without evidence-backed simulation values.</div>
          <button className="button button-primary" onClick={run} disabled={busy || selectedSims.length === 0 || !executionTimeSelected}>{busy ? 'Optimizing…' : 'Run optimization'} <span>↗</span></button>
        </> : <EmptyState title="Simulation inputs required" detail="Run one or more scenario simulations before optimizing candidate strategies." />}
        {error && <InlineError message={error} />}
      </Panel>
      <form className="saved-result-form" onSubmit={loadSaved}>
        <label>Load a persisted optimization<input value={savedOptimizationId} onChange={(event) => setSavedOptimizationId(event.target.value)} placeholder="OPT-…" /></label>
        <button className="button button-secondary" disabled={busy || !savedOptimizationId.trim()}>Load result & Pareto frontier</button>
      </form>
      {result && <>
        <div className="optimization-summary">
          <div><span className="eyebrow">OPTIMIZATION</span><strong>{result.optimization_id}</strong><StatusPill status={result.status} /></div>
          <div className="optimization-count"><strong>{result.pareto_solutions.length}</strong><span>Pareto-optimal</span></div>
          <div className="optimization-count"><strong>{result.dominated_strategies.length}</strong><span>Dominated</span></div>
          <div className="optimization-count"><strong>{result.infeasible_strategies.length}</strong><span>Infeasible</span></div>
          <div className="optimization-count"><strong>{result.unevaluable_strategies.length}</strong><span>Unevaluable</span></div>
        </div>
        <div className="optimization-grid">
          <Panel title="Pareto frontier" eyebrow="COST ↔ AIR QUALITY" className="pareto-panel">
            {points.length > 1 ? <Suspense fallback={<div className="pareto-plot">Loading Pareto frontier…</div>}><ParetoChart points={points} /></Suspense> : <EmptyState title="Pareto plot unavailable" detail="The backend did not return numeric cost and AQI objective values for enough strategies." />}
          </Panel>
          <Panel title="Optimization objectives" eyebrow="CONFIGURED TRADE-OFFS" className="objective-panel">
            <div className="objective-list">{result.objectives.map((item) => <div key={item.name}><span>{item.name.replaceAll('_', ' ')}</span><strong>{item.direction}</strong></div>)}</div>
          </Panel>
        </div>
        <Panel title="Strategy classification" eyebrow="BACKEND OPTIMIZATION RESULT">
          <div className="strategy-columns">
            <StrategyList title="Pareto-optimal" items={result.pareto_solutions} />
            <StrategyList title="Dominated" items={result.dominated_strategies} />
            <StrategyList title="Infeasible" items={result.infeasible_strategies} />
            <StrategyList title="Unevaluable" items={result.unevaluable_strategies} />
          </div>
        </Panel>
      </>}
    </div>
  )
}

function StrategyList({ title, items }: { title: string; items: Array<Record<string, unknown>> }) {
  return <div className="strategy-column"><strong>{title} <span>{items.length}</span></strong>{items.length ? items.slice(0, 8).map((item, index) => {
    const values = item.objective_values as Record<string, unknown> | undefined
    const sources = item.objective_sources as Record<string, unknown> | undefined
    const executionTime = values?.execution_time
    const executionSource = sources?.execution_time
    return <div className="strategy-row" key={String(item.scenario_id ?? index)}><span>{String(item.scenario_id ?? 'Strategy')}{typeof executionTime === 'number' && <small>{formatMetric(executionTime)} years</small>}{typeof executionSource === 'string' && <small>{executionSource}</small>}</span><small>{typeof item.pareto_rank === 'number' ? `Rank ${item.pareto_rank}` : ''}</small></div>
  }) : <p>None returned.</p>}</div>
}

function DecisionPage({ selectedWard }: { selectedWard: Ward | null }) {
  const [problem, setProblem] = useState('')
  const [objective, setObjective] = useState('')
  const [constraints, setConstraints] = useState('')
  const [interventions, setInterventions] = useState('')
  const [result, setResult] = useState<Record<string, unknown> | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const analyze = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      setResult((await requests.decision({
        query: problem.trim(),
        city: 'Delhi',
        zone: selectedWard?.zone ?? 'City-wide',
        objective: objective.trim() || undefined,
        constraints: constraints.split('\n').map((item) => item.trim()).filter(Boolean),
        requested_interventions: interventions.split(',').map((item) => item.trim()).filter(Boolean),
      })).data)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }
  const sections: Array<[string, string]> = [
    ['Current urban state', 'current_state'], ['Problem diagnosis', 'detected_problems'],
    ['Relevant evidence', 'evidence'], ['Candidate scenarios', 'scenarios'],
    ['Simulation results', 'simulation_results'], ['Optimization results', 'pareto_strategies'],
    ['Recommended strategy', 'recommendation'], ['Explanation', 'explanation'],
    ['Limitations', 'limitations'],
  ]
  return (
    <div className="page-grid">
      <div className="page-intro"><span className="eyebrow">MULTI-AGENT DECISION WORKFLOW</span><h2>From urban problem to informed choice.</h2><p>Send the planning context to the existing decision-analysis API and review its findings, evidence, recommendation and limitations.</p></div>
      <div className="decision-layout">
        <Panel title="Decision brief" eyebrow="ANALYSIS INPUT">
          <form className="form-stack" onSubmit={analyze}>
            <label>Problem<textarea rows={4} placeholder="What urban condition needs attention?" value={problem} onChange={(event) => setProblem(event.target.value)} required /></label>
            <label>Objective<input value={objective} onChange={(event) => setObjective(event.target.value)} placeholder="What outcome should be prioritized?" /></label>
            <label>Constraints <span className="label-hint">One constraint per line</span><textarea rows={3} value={constraints} onChange={(event) => setConstraints(event.target.value)} placeholder="Available budget, policy requirements…" /></label>
            <label>Requested interventions <span className="label-hint">Optional, comma separated</span><input value={interventions} onChange={(event) => setInterventions(event.target.value)} placeholder="Use a named intervention or leave blank" /></label>
            <div className="request-context"><MapPin size={15} />Delhi · {selectedWard?.zone ?? 'City-wide'}</div>
            {error && <InlineError message={error} />}
            <button className="button button-primary button-wide" disabled={busy}>{busy ? 'Analyzing…' : 'Analyze decision'} <span>↗</span></button>
          </form>
        </Panel>
        <Panel title="Decision analysis" eyebrow={result ? 'BACKEND WORKFLOW RESULT' : 'OUTPUT'} className="decision-result-panel">
          {result ? <div className="decision-sections">{sections.map(([label, key]) => {
            const value = result[key]
            if (value === undefined || value === null || (Array.isArray(value) && value.length === 0)) return null
            return <details key={key} open={key === 'recommendation' || key === 'detected_problems'} className="decision-section"><summary>{label}<ChevronDown size={15} /></summary>{typeof value === 'string' ? <p className="decision-text">{value}</p> : <JsonResult value={value} />}</details>
          })}</div> : <EmptyState title="No analysis submitted" detail="Complete the decision brief to run the existing urban decision workflow." />}
        </Panel>
      </div>
      {result && <div className="evidence-disclaimer"><FileSearch size={16} />Decision output may contain model synthesis. Verify any referenced evidence and review the returned limitations before acting.</div>}
    </div>
  )
}

function ExplainabilityPage({
  simulations, optimization,
}: {
  simulations: SimulationResult[]
  optimization: OptimizationResult | null
}) {
  const [model, setModel] = useState('aqi')
  const [features, setFeatures] = useState('')
  const [featureName, setFeatureName] = useState('')
  const [counterValue, setCounterValue] = useState('')
  const [predictionResult, setPredictionResult] = useState<unknown>(null)
  const [counterResult, setCounterResult] = useState<unknown>(null)
  const [recommendationResult, setRecommendationResult] = useState<unknown>(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const run = async (kind: 'prediction' | 'counterfactual' | 'recommendation') => {
    setBusy(kind)
    setError('')
    try {
      if (kind === 'prediction' || kind === 'counterfactual') {
        const parsed = JSON.parse(features) as Record<string, number>
        if (!parsed || Array.isArray(parsed) || Object.values(parsed).some((item) => typeof item !== 'number' || !Number.isFinite(item))) throw new Error('Feature input must be a JSON object of finite numeric values.')
        if (kind === 'prediction') {
          setPredictionResult((await requests.explainPrediction({ model_name: model, features: parsed })).data)
        } else {
          if (!featureName.trim() || !Number.isFinite(Number(counterValue))) throw new Error('Enter a feature name and a numeric counterfactual value.')
          setCounterResult((await requests.counterfactual({ model_name: model, features: parsed, feature_name: featureName.trim(), counterfactual_value: Number(counterValue) })).data)
        }
      } else {
        if (!optimization || !simulations.length) throw new Error('Run simulations and an optimization first.')
        setRecommendationResult((await requests.explainRecommendation({ simulations, optimization_result: optimization })).data)
      }
    } catch (err) {
      setError(err instanceof SyntaxError ? 'Features must be valid JSON containing numeric values.' : errorMessage(err))
    } finally {
      setBusy('')
    }
  }
  const contributions = isRecord(predictionResult) && Array.isArray(predictionResult.feature_contributions)
    ? predictionResult.feature_contributions.filter(isRecord)
    : []
  const counterfactual = isRecord(counterResult) ? counterResult : null
  return (
    <div className="page-grid">
      <div className="page-intro"><span className="eyebrow">PHASE 13 · EXPLAINABILITY</span><h2>Understand why the model responds.</h2><p>Request explanations and counterfactuals from the backend. Provide the exact model features; no feature values or outcomes are invented in the dashboard.</p></div>
      <Panel title="Prediction explanation" eyebrow="FEATURE ATTRIBUTION">
        <div className="explain-input-grid">
          <label>Prediction model<select value={model} onChange={(event) => setModel(event.target.value)}>{['aqi', 'urban_heat', 'green_cover', 'carbon', 'carbon_reduction', 'health_risk'].map((item) => <option key={item} value={item}>{item.replaceAll('_', ' ')}</option>)}</select></label>
          <label className="explain-features">Feature values <span className="label-hint">JSON object of numeric backend model inputs</span><textarea rows={4} value={features} onChange={(event) => setFeatures(event.target.value)} placeholder={'{"feature_name": 1.2}'} /></label>
        </div>
        <div className="button-row"><button className="button button-primary" onClick={() => run('prediction')} disabled={!features || Boolean(busy)}>{busy === 'prediction' ? 'Explaining…' : 'Explain prediction'}</button></div>
        {predictionResult !== null && <JsonResult value={predictionResult} />}
      </Panel>
      {predictionResult !== null && <Panel title="Feature importance" eyebrow="TOP CONTRIBUTING FACTORS">
        {contributions.length ? <div className="contribution-list">{contributions.map((item, index) => {
          const value = typeof item.shap_value === 'number' ? item.shap_value : null
          const maximum = Math.max(0.0001, ...contributions.map((entry) => typeof entry.shap_value === 'number' ? Math.abs(entry.shap_value) : 0))
          const width = value === null ? 0 : Math.max(2, Math.abs(value) / maximum * 100)
          return <div className="contribution-row" key={`${String(item.feature ?? 'feature')}-${index}`}><div className="contribution-copy"><strong>{String(item.feature ?? 'Unknown feature').replaceAll('_', ' ')}</strong><span>{String(item.influence ?? 'unknown').replaceAll('_', ' ')}</span><small>Feature value {formatMetric(item.feature_value)} · SHAP {formatMetric(value, 3)}</small></div><div className="contribution-track"><span className={value !== null && value < 0 ? 'contribution-negative' : ''} style={{ width: `${width}%` }} /></div></div>
        })}</div> : <EmptyState title="Feature contributions unavailable" detail="The prediction explanation did not return feature-level attributions." />}
      </Panel>}
      <div className="explain-grid">
        <Panel title="Counterfactual analysis" eyebrow="WHAT-IF QUESTION">
          <p className="panel-copy">Change one model input and inspect the backend-calculated counterfactual prediction.</p>
          <div className="counter-input-row"><label>Feature name<input value={featureName} onChange={(event) => setFeatureName(event.target.value)} placeholder="Feature to change" /></label><label>New value<input type="number" step="any" value={counterValue} onChange={(event) => setCounterValue(event.target.value)} placeholder="Numeric value" /></label></div>
          <button className="button button-secondary" onClick={() => run('counterfactual')} disabled={!features || Boolean(busy)}>{busy === 'counterfactual' ? 'Calculating…' : 'Run counterfactual'} <span>↗</span></button>
          {counterfactual && <><div className="counterfactual-values"><DataField label="Baseline prediction" value={counterfactual.baseline_prediction} /><DataField label="Counterfactual prediction" value={counterfactual.counterfactual_prediction} /><DataField label="Change" value={counterfactual.absolute_delta} /></div><JsonResult value={counterfactual} /></>}
        </Panel>
        <Panel title="Recommendation explanation" eyebrow="TRADE-OFFS & REASONS">
          <p className="panel-copy">Explain the preferred strategy from the available simulation and optimization result.</p>
          {!optimization && <div className="request-context"><CircleHelp size={15} />Run Optimization first to enable this explanation.</div>}
          <button className="button button-secondary" onClick={() => run('recommendation')} disabled={!optimization || simulations.length === 0 || Boolean(busy)}>{busy === 'recommendation' ? 'Explaining…' : 'Explain recommendation'} <span>↗</span></button>
          {recommendationResult !== null && <JsonResult value={recommendationResult} />}
        </Panel>
      </div>
      {error && <InlineError message={error} />}
    </div>
  )
}

function EvidencePage({ selectedWard }: { selectedWard: Ward | null }) {
  const [query, setQuery] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<Record<string, unknown> | null>(null)
  const ask = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      setResult((await requests.ragQuery({ query: query.trim(), city: 'Delhi', zone: selectedWard?.zone, top_k: 5 })).data)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }
  const sources = Array.isArray(result?.sources) ? result.sources as Array<Record<string, unknown>> : []
  return (
    <div className="page-grid">
      <div className="page-intro"><span className="eyebrow">PHASE 07 · URBAN MEMORY & RAG</span><h2>Bring evidence into the room.</h2><p>Search indexed urban knowledge. Retrieved sources are kept distinct from AI-generated synthesis and are not treated as a decision.</p></div>
      <Panel title="Ask the evidence layer" eyebrow="RETRIEVAL QUERY" className="evidence-query-panel">
        <form className="evidence-query-form" onSubmit={ask}><label className="sr-only" htmlFor="evidence-query">Question</label><input id="evidence-query" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Ask about air quality, urban heat, interventions or policy…" required /><button className="button button-primary" disabled={busy}>{busy ? 'Searching…' : 'Search evidence'} <span>↗</span></button></form>
        <div className="request-context"><MapPin size={15} />Delhi · {selectedWard?.zone ?? 'City-wide context'}</div>
        {error && <InlineError message={error} />}
      </Panel>
      {result && <>
        <div className={`retrieval-mode-banner ${result.retrieval_mode === 'qdrant' ? 'mode-persistent' : 'mode-fallback'}`}>
          <div><span className="mode-icon">{result.retrieval_mode === 'qdrant' ? <Check size={15} /> : <CircleHelp size={15} />}</span><span><strong>{result.retrieval_mode === 'qdrant' ? 'Persistent retrieval' : 'Degraded fallback retrieval'}</strong><small>{result.retrieval_mode === 'qdrant' ? 'Connected to Qdrant vector storage.' : 'Qdrant is not active; results use the in-process fallback and may not persist across restarts.'}</small></span></div>
          <span>RETRIEVAL MODE</span>
        </div>
        <Panel title="Generated synthesis" eyebrow={result.grounded ? 'RESPONSE GROUNDED IN RETRIEVED SOURCES' : 'NO SUPPORTING SOURCES'}>
          <p className="rag-answer">{String(result.answer ?? 'No answer was returned.')}</p>
          <div className="synthesis-label"><Sparkles size={14} />AI-generated synthesis · review source documents before use</div>
        </Panel>
        <Panel title="Retrieved source material" eyebrow={`${sources.length} SOURCES`}>
          {sources.length ? <div className="source-list">{sources.map((source, index) => <article className="source-card" key={`${String(source.document_id)}-${index}`}><span className="source-number">{String(index + 1).padStart(2, '0')}</span><div className="source-main"><strong>{String(source.title ?? 'Untitled source')}</strong><span>{String(source.source ?? 'Source unavailable')}</span><div className="source-meta"><span>Document {String(source.document_id ?? 'Unavailable')}</span><span>Page {String(source.page ?? 'Unavailable')}</span><span>Similarity {formatMetric(source.score, 3)}</span></div></div>{typeof source.url === 'string' && source.url.startsWith('https://') && <a className="text-link" href={source.url} target="_blank" rel="noreferrer">Open source ↗</a>}</article>)}</div> : <EmptyState title="No source references returned" detail="The retrieval service returned no cited documents for this query." />}
        </Panel>
        {result.graph_context !== undefined && <Panel title="Knowledge graph context" eyebrow="RELATED URBAN ENTITIES"><JsonResult value={result.graph_context} /></Panel>}
      </>}
      <div className="evidence-disclaimer"><BookOpen size={16} />RAG is an evidence-retrieval layer, not the decision engine. Similarity scores are retrieval metadata, not confidence.</div>
    </div>
  )
}

function SystemPage({ status, error, onRefresh, refreshing }: { status: SystemStatus | null; error: string; onRefresh: () => void; refreshing: boolean }) {
  const labels: Record<string, string> = {
    fastapi: 'FastAPI', database: 'Database', qdrant: 'Qdrant', rag: 'Evidence retrieval',
    ml_models: 'ML model metadata', digital_twin: 'Digital Twin',
  }
  return (
    <div className="page-grid">
      <div className="page-intro page-intro-row"><div><span className="eyebrow">LIVE SERVICE CHECKS</span><h2>Know what is available.</h2><p>Statuses are checked by the backend when requested; unconfigured services are never shown as healthy.</p></div><button className="button button-secondary" onClick={onRefresh} disabled={refreshing}><RefreshCw size={15} className={refreshing ? 'spin' : ''} />Refresh status</button></div>
      {error && <InlineError message={error} />}
      {status ? <>
        <div className="system-overall"><div><span className="eyebrow">OVERALL SYSTEM STATUS</span><StatusPill status={status.overall_status} /></div><span className="last-checked"><Clock3 size={14} />Last checked {new Date(status.checked_at).toLocaleString()}</span></div>
        <div className="service-grid">{Object.entries(status.components).map(([key, component]) => <article key={key} className="service-card"><div className="service-card-top"><span className="service-icon"><Cpu size={17} /></span><StatusPill status={component.status} /></div><h3>{labels[key] ?? key.replaceAll('_', ' ')}</h3><div className="service-details">{component.backend && <span>Backend <strong>{component.backend}</strong></span>}{component.mode && <span>Mode <strong>{component.mode}</strong></span>}{typeof component.latency_ms === 'number' && <span>Response <strong>{formatMetric(component.latency_ms, 2)} ms</strong></span>}{typeof component.count === 'number' && <span>Assets <strong>{component.count}</strong></span>}{typeof component.ward_count === 'number' && <span>Wards <strong>{component.ward_count}</strong></span>}</div></article>)}</div>
        {(status.components.rag?.mode === 'fallback' || status.components.qdrant?.status === 'NOT_CONFIGURED') && <div className="setup-notice"><CircleHelp size={17} /><span>RAG is using fallback retrieval because persistent Qdrant is not configured or is unavailable. Configure QDRANT_URL to enable persistent vector storage.</span></div>}
      </> : <EmptyState title="System status unavailable" detail="The backend status endpoint could not provide live service checks." />}
    </div>
  )
}

function App() {
  const navigate = useNavigate()
  const location = useLocation()
  const [authConfig, setAuthConfig] = useState<AuthConfig | null>(null)
  const [authReady, setAuthReady] = useState(false)
  const [authenticated, setAuthenticated] = useState(false)
  const [data, setData] = useState<PageData>(emptyData)
  const [annualCarbon, setAnnualCarbon] = useState<AnnualWardCarbonResponse | null>(null)
  const [annualCarbonError, setAnnualCarbonError] = useState('')
  const carbonRequestId = useRef(0)
  const [selectedWardNumber, setSelectedWardNumber] = useState<number | null>(null)
  const [simulations, setSimulations] = useState<SimulationResult[]>([])
  const [optimization, setOptimization] = useState<OptimizationResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [dataError, setDataError] = useState('')
  const [systemError, setSystemError] = useState('')
  const [navOpen, setNavOpen] = useState(false)

  useEffect(() => {
    let active = true
    requests.authConfig().then(async ({ data: config }) => {
      if (!active) return
      setAuthConfig(config)
      const token = sessionStorage.getItem('urbanmind_access_token')
      if (token) {
        try {
          await requests.me()
          if (active) setAuthenticated(true)
        } catch {
          sessionStorage.removeItem('urbanmind_access_token')
        }
      }
      if (active) {
        if (!config.required) setAuthenticated(true)
        setAuthReady(true)
      }
    }).catch(() => {
      if (active) {
        setAuthConfig({ required: false, configured: false })
        setAuthenticated(true)
        setAuthReady(true)
      }
    })
    return () => { active = false }
  }, [])

  const loadAnnualCarbon = useCallback(async () => {
    const requestId = ++carbonRequestId.current
    setAnnualCarbonError('')
    try {
      const response = await requests.annualWardCarbon()
      if (requestId === carbonRequestId.current) setAnnualCarbon(response.data)
    } catch (error) {
      if (requestId === carbonRequestId.current) {
        setAnnualCarbon(null)
        setAnnualCarbonError(errorMessage(error))
      }
    }
  }, [])

  const loadDashboard = useCallback(async (quiet = false) => {
    void loadAnnualCarbon()
    if (!quiet) setLoading(true)
    setRefreshing(quiet)
    setDataError('')
    const [summary, wards, geojson, scenarios, status] = await Promise.allSettled([
      requests.summary(), requests.wards(), requests.wardGeojson(), requests.scenarios(), requests.systemStatus(),
    ])
    setData((current) => {
      const next: PageData = {
        summary: summary.status === 'fulfilled' ? summary.value.data.summary : current.summary,
        wards: wards.status === 'fulfilled' ? wards.value.data.wards : current.wards,
        geojson: geojson.status === 'fulfilled' ? geojson.value.data : current.geojson,
        scenarios: scenarios.status === 'fulfilled' ? scenarios.value.data.scenarios : current.scenarios,
        status: status.status === 'fulfilled' ? status.value.data : current.status,
      }
      return next
    })
    const failures = [summary, wards, geojson, scenarios, status].filter((item) => item.status === 'rejected')
    if (failures.length) {
      const firstError = failures[0]
      if (firstError.status === 'rejected') setDataError(errorMessage(firstError.reason))
      if (status.status === 'rejected') setSystemError(errorMessage(status.reason))
    } else {
      setSystemError('')
    }
    setLoading(false)
    setRefreshing(false)
  }, [loadAnnualCarbon])

  useEffect(() => {
    if (selectedWardNumber === null && data.wards.length) setSelectedWardNumber(data.wards[0].ward_no)
  }, [data.wards, selectedWardNumber])

  useEffect(() => {
    if (authReady && authenticated) void loadDashboard()
  }, [authReady, authenticated, loadDashboard])

  const ward = data.wards.find((item) => item.ward_no === selectedWardNumber) ?? null
  const handleLogin = (token: string) => {
    sessionStorage.setItem('urbanmind_access_token', token)
    setAuthenticated(true)
  }
  const logout = () => {
    sessionStorage.removeItem('urbanmind_access_token')
    setAuthenticated(false)
    setAuthReady(true)
    navigate('/overview')
  }
  const addSimulation = (simulation: SimulationResult) => {
    setSimulations((current) => [simulation, ...current.filter((item) => item.simulation_id !== simulation.simulation_id)])
  }
  const addScenarios = (result: ScenarioSet) => {
    setData((current) => {
      const byId = new Map(current.scenarios.map((scenario) => [scenario.scenario_id, scenario]))
      result.scenarios.forEach((scenario) => byId.set(scenario.scenario_id, scenario))
      return { ...current, scenarios: [...byId.values()] }
    })
  }
  const refreshSystem = async () => {
    setRefreshing(true)
    setSystemError('')
    try {
      const response = await requests.systemStatus()
      setData((current) => ({ ...current, status: response.data }))
    } catch (error) {
      setSystemError(errorMessage(error))
    } finally {
      setRefreshing(false)
    }
  }

  if (!authReady) return <div className="app-loading"><span className="loading-mark"><Layers3 size={22} /></span><span>Connecting to UrbanMind AI</span></div>
  if (authConfig?.required && !authenticated) return <Login config={authConfig} onLogin={handleLogin} />

  const path = location.pathname === '/' ? '/overview' : location.pathname
  const pageTitle = pageNames[path] ?? 'City overview'
  return (
    <div className={`app-shell ${navOpen ? 'nav-open' : ''}`}>
      <aside className="sidebar">
        <div className="sidebar-brand"><span className="brand-mark"><Layers3 size={19} /></span><span>UrbanMind<span className="brand-ai">AI</span><small>DECISION INTELLIGENCE</small></span></div>
        <div className="nav-section-label">WORKSPACE</div>
        <nav className="main-nav">{navigation.map(({ to, label, icon: Icon }) => <NavLink to={to} key={to} onClick={() => setNavOpen(false)} className={({ isActive }) => `nav-link ${isActive ? 'is-active' : ''}`}><Icon size={17} /><span>{label}</span>{to === '/overview' && <span className="nav-live-dot" />}</NavLink>)}</nav>
        <div className="sidebar-bottom">
          <div className="sidebar-system"><span className={`system-dot ${data.status?.overall_status?.toLowerCase() ?? 'unknown'}`} /><div><strong>System {data.status?.overall_status?.toLowerCase() ?? 'checking'}</strong><small>Delhi urban intelligence</small></div></div>
          {authConfig?.required && <button className="logout-button" onClick={logout}><LogOut size={16} />Sign out</button>}
          <div className="sidebar-version"><span>URBANMIND AI</span><span>PHASE 15 · DASHBOARD</span></div>
        </div>
      </aside>
      {navOpen && <button className="nav-scrim" onClick={() => setNavOpen(false)} aria-label="Close navigation" />}
      <div className="main-shell">
        <header className="topbar">
          <button className="icon-button mobile-menu" aria-label="Open menu" onClick={() => setNavOpen(true)}><Menu size={19} /></button>
          <div className="topbar-location"><span className="location-mark"><MapPin size={14} /></span><div><strong>Delhi, India</strong><small>{pageTitle}</small></div><ChevronDown size={14} /></div>
          <div className="topbar-right">
            <label className="ward-select"><span>WARD</span><select aria-label="Select a ward" value={selectedWardNumber ?? ''} onChange={(event) => setSelectedWardNumber(Number(event.target.value))}><option value="" disabled>Select ward</option>{data.wards.map((item) => <option key={item.ward_no} value={item.ward_no}>{String(item.ward_no).padStart(3, '0')} · {item.location}</option>)}</select></label>
            <div className="topbar-status"><span className={`system-dot ${data.status?.overall_status?.toLowerCase() ?? 'unknown'}`} />{data.status?.overall_status ?? 'Checking'}</div>
            <div className="topbar-updated"><small>LAST CHECK</small><strong>{data.status?.checked_at ? new Date(data.status.checked_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}</strong></div>
            <button className="icon-button topbar-refresh" aria-label="Refresh dashboard" onClick={() => void loadDashboard(true)} disabled={refreshing}><RefreshCw size={16} className={refreshing ? 'spin' : ''} /></button>
          </div>
        </header>
        <main className="main-content">
          <div className="content-heading"><div><span className="eyebrow">URBAN DECISION OPERATING SYSTEM <span className="heading-slash">/</span> DELHI</span><h1>{pageTitle}</h1></div><div className="heading-date"><span className="data-dot" />Live backend data</div></div>
          {dataError && <div className="global-error"><CircleHelp size={16} /><span>{dataError}</span><button onClick={() => void loadDashboard(true)}>Retry</button></div>}
          {loading ? <div className="loading-page"><span className="loading-spinner" />Loading urban intelligence…</div> : (
            <Routes>
              <Route path="/" element={<Navigate to="/overview" replace />} />
              <Route path="/overview" element={<Overview data={data} ward={ward} annualCarbon={annualCarbon} annualCarbonError={annualCarbonError} onSelectWard={setSelectedWardNumber} onNavigate={navigate} />} />
              <Route path="/city-twin" element={<WardPage data={data} ward={ward} annualCarbon={annualCarbon} annualCarbonError={annualCarbonError} onSelectWard={setSelectedWardNumber} />} />
              <Route path="/scenarios" element={<ScenariosPage wards={data.wards} selectedWard={ward} scenarios={data.scenarios} onScenariosChanged={addScenarios} />} />
              <Route path="/data-management" element={<DataManagementPage wards={data.wards} />} />
              <Route path="/simulation" element={<SimulationPage scenarios={data.scenarios} ward={ward} simulations={simulations} onSimulation={addSimulation} />} />
              <Route path="/optimization" element={<OptimizationPage simulations={simulations} result={optimization} onResult={setOptimization} />} />
              <Route path="/decision-center" element={<DecisionPage selectedWard={ward} />} />
              <Route path="/explainability" element={<ExplainabilityPage simulations={simulations} optimization={optimization} />} />
              <Route path="/evidence" element={<EvidencePage selectedWard={ward} />} />
              <Route path="/system-status" element={<SystemPage status={data.status} error={systemError} onRefresh={refreshSystem} refreshing={refreshing} />} />
              <Route path="*" element={<Navigate to="/overview" replace />} />
            </Routes>
          )}
          <footer className="main-footer"><span>UrbanMind AI · Decision Intelligence</span><span>Data from connected backend services · unavailable metrics are not estimated</span></footer>
        </main>
      </div>
    </div>
  )
}

export default App
