import { useEffect, useMemo, useState } from 'react'
import type { FormEvent, ChangeEvent } from 'react'
import { AlertCircle, Check, ChevronLeft, ChevronRight, Database, FileSpreadsheet, Upload } from 'lucide-react'
import { errorMessage, formatMetric, requests } from '../api'
import type {
  EnvironmentalClassification,
  EnvironmentalColumnMapping,
  EnvironmentalMetric,
  EnvironmentalRecord,
  EnvironmentalRecordInput,
  EnvironmentalUploadPreview,
  EnvironmentalValidationReport,
  Ward,
} from '../types'

const PAGE_SIZE = 20
const classifications: EnvironmentalClassification[] = ['observed', 'official', 'derived', 'estimated', 'illustrative']
const metrics: Array<{ value: EnvironmentalMetric; label: string; units: string[]; defaultUnit: string }> = [
  { value: 'aqi', label: 'Air quality index (AQI)', units: ['AQI'], defaultUnit: 'AQI' },
  { value: 'pm25', label: 'PM2.5', units: ['µg/m³', 'mg/m³'], defaultUnit: 'µg/m³' },
  { value: 'pm10', label: 'PM10', units: ['µg/m³', 'mg/m³'], defaultUnit: 'µg/m³' },
  { value: 'no2', label: 'NO2', units: ['ppb', 'µg/m³', 'mg/m³'], defaultUnit: 'ppb' },
  { value: 'o3', label: 'Ozone (O3)', units: ['µg/m³', 'mg/m³', 'ppb'], defaultUnit: 'µg/m³' },
  { value: 'co', label: 'CO', units: ['ppb', 'µg/m³', 'mg/m³'], defaultUnit: 'ppb' },
  { value: 'so2', label: 'SO2', units: ['ppb', 'µg/m³', 'mg/m³'], defaultUnit: 'ppb' },
  { value: 'temperature', label: 'Air temperature', units: ['°C'], defaultUnit: '°C' },
  { value: 'land_surface_temperature', label: 'Land-surface temperature', units: ['°C'], defaultUnit: '°C' },
  { value: 'green_cover', label: 'Green cover', units: ['%'], defaultUnit: '%' },
  { value: 'population', label: 'Population', units: ['people'], defaultUnit: 'people' },
]

const mappingFields: Array<{ key: keyof EnvironmentalRecordInput; label: string; required: boolean; aliases: string[] }> = [
  { key: 'ward_id', label: 'Ward ID', required: true, aliases: ['ward', 'wardno', 'wardnumber', 'wardid', 'ward_no'] },
  { key: 'observation_date', label: 'Observation date', required: true, aliases: ['date', 'observationdate', 'timestamp', 'timestamp_local'] },
  { key: 'metric', label: 'Metric', required: true, aliases: ['metric', 'parameter', 'pollutant'] },
  { key: 'value', label: 'Value', required: true, aliases: ['value', 'measurement', 'reading'] },
  { key: 'unit', label: 'Unit', required: true, aliases: ['unit', 'units'] },
  { key: 'data_classification', label: 'Data classification', required: true, aliases: ['classification', 'dataclassification', 'data_classification'] },
  { key: 'source_name', label: 'Source name', required: true, aliases: ['source', 'sourcename', 'station', 'stationname', 'station_name'] },
  { key: 'source_reference', label: 'Source reference', required: false, aliases: ['reference', 'sourcereference', 'sensorid', 'sensor_id', 'url'] },
  { key: 'notes', label: 'Notes', required: false, aliases: ['notes', 'note', 'comment'] },
]

type EnvironmentalFormState = Omit<EnvironmentalRecordInput, 'ward_id' | 'value' | 'data_classification'> & {
  ward_id: number | null
  value: string
  data_classification: EnvironmentalClassification | ''
}

const emptyRecord: EnvironmentalFormState = {
  ward_id: null,
  observation_date: '',
  metric: 'aqi',
  value: '',
  unit: '',
  data_classification: '',
  source_name: '',
  source_reference: '',
  notes: '',
}

function normalizedColumn(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '')
}

function suggestedMapping(columns: string[]): EnvironmentalColumnMapping {
  const mapping: EnvironmentalColumnMapping = {}
  for (const field of mappingFields) {
    const aliases = new Set([normalizedColumn(field.key), ...field.aliases.map(normalizedColumn)])
    const match = columns.find((column) => aliases.has(normalizedColumn(column)))
    if (match) mapping[field.key] = match
  }
  return mapping
}

function mapServerFieldErrors(message: string): Record<string, string> {
  const result: Record<string, string> = {}
  for (const key of ['ward_id', 'observation_date', 'metric', 'value', 'unit', 'data_classification', 'source_name', 'source_reference', 'notes']) {
    const prefix = `${key}:`
    const detail = message.split('; ').find((part) => part.startsWith(prefix))
    if (detail) result[key] = detail.slice(prefix.length).trim()
  }
  return result
}

export default function DataManagementPage({ wards }: { wards: Ward[] }) {
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<EnvironmentalUploadPreview | null>(null)
  const [mapping, setMapping] = useState<EnvironmentalColumnMapping>({})
  const [validation, setValidation] = useState<EnvironmentalValidationReport | null>(null)
  const [importResult, setImportResult] = useState<Awaited<ReturnType<typeof requests.importEnvironmentalUpload>>['data'] | null>(null)
  const [uploadBusy, setUploadBusy] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [record, setRecord] = useState<EnvironmentalFormState>(emptyRecord)
  const [recordBusy, setRecordBusy] = useState(false)
  const [recordError, setRecordError] = useState('')
  const [recordFieldErrors, setRecordFieldErrors] = useState<Record<string, string>>({})
  const [recordSuccess, setRecordSuccess] = useState('')
  const [records, setRecords] = useState<EnvironmentalRecord[]>([])
  const [totalRecords, setTotalRecords] = useState(0)
  const [offset, setOffset] = useState(0)
  const [historyBusy, setHistoryBusy] = useState(true)
  const [historyError, setHistoryError] = useState('')
  const selectedMetric = useMemo(() => metrics.find((item) => item.value === record.metric) ?? metrics[0], [record.metric])

  useEffect(() => {
    let active = true
    setHistoryBusy(true)
    requests.environmentalRecords({ limit: PAGE_SIZE, offset }).then(({ data }) => {
      if (!active) return
      setRecords(data.records)
      setTotalRecords(data.total)
      setHistoryError('')
    }).catch((error: unknown) => {
      if (active) setHistoryError(errorMessage(error))
    }).finally(() => {
      if (active) setHistoryBusy(false)
    })
    return () => { active = false }
  }, [offset])

  const refreshRecords = async () => {
    setHistoryBusy(true)
    try {
      const { data } = await requests.environmentalRecords({ limit: PAGE_SIZE, offset })
      setRecords(data.records)
      setTotalRecords(data.total)
      setHistoryError('')
    } catch (error) {
      setHistoryError(errorMessage(error))
    } finally {
      setHistoryBusy(false)
    }
  }

  const selectFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0] ?? null
    setFile(selectedFile)
    setPreview(null)
    setValidation(null)
    setImportResult(null)
    setUploadError('')
    if (!selectedFile) return
    setUploadBusy(true)
    try {
      const { data } = await requests.environmentalPreview(selectedFile)
      setPreview(data)
      setMapping(suggestedMapping(data.columns))
    } catch (error) {
      setUploadError(errorMessage(error))
    } finally {
      setUploadBusy(false)
    }
  }

  const setColumn = (field: keyof EnvironmentalRecordInput, value: string) => {
    setMapping((current) => ({ ...current, [field]: value || undefined }))
    setValidation(null)
    setImportResult(null)
  }

  const validateUpload = async () => {
    if (!file) return
    setUploadBusy(true)
    setUploadError('')
    setValidation(null)
    setImportResult(null)
    try {
      setValidation((await requests.validateEnvironmentalUpload(file, mapping)).data)
    } catch (error) {
      setUploadError(errorMessage(error))
    } finally {
      setUploadBusy(false)
    }
  }

  const confirmImport = async () => {
    if (!file || !preview || !validation || validation.valid_rows <= validation.duplicate_rows) return
    setUploadBusy(true)
    setUploadError('')
    try {
      const result = (await requests.importEnvironmentalUpload(file, mapping, preview.checksum)).data
      setImportResult(result)
      setValidation(result)
      await refreshRecords()
    } catch (error) {
      setUploadError(errorMessage(error))
    } finally {
      setUploadBusy(false)
    }
  }

  const submitRecord = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setRecordError('')
    setRecordFieldErrors({})
    setRecordSuccess('')
    const localErrors: Record<string, string> = {}
    if (!record.ward_id) localErrors.ward_id = 'Select a ward.'
    if (!record.observation_date) localErrors.observation_date = 'Select an observation date.'
    if (!record.value.trim() || !Number.isFinite(Number(record.value))) localErrors.value = 'Enter a finite numeric value.'
    if (!record.source_name.trim()) localErrors.source_name = 'Enter the data source.'
    if (!record.data_classification) localErrors.data_classification = 'Select a classification.'
    if (Object.keys(localErrors).length) {
      setRecordFieldErrors(localErrors)
      return
    }
    setRecordBusy(true)
    try {
      const payload: EnvironmentalRecordInput = {
        ...record,
        ward_id: record.ward_id as number,
        value: Number(record.value),
        data_classification: record.data_classification as EnvironmentalClassification,
        source_reference: record.source_reference?.trim() || null,
        notes: record.notes?.trim() || null,
      }
      const { data } = await requests.createEnvironmentalRecord(payload)
      setRecord({ ...emptyRecord })
      setRecordSuccess(`Saved ${data.record_id} as ${data.data_classification}.`)
      await refreshRecords()
    } catch (error) {
      const message = errorMessage(error)
      setRecordError(message)
      setRecordFieldErrors(mapServerFieldErrors(message))
    } finally {
      setRecordBusy(false)
    }
  }

  const updateRecord = <K extends keyof EnvironmentalFormState>(key: K, value: EnvironmentalFormState[K]) => {
    setRecord((current) => ({ ...current, [key]: value }))
    setRecordFieldErrors((current) => ({ ...current, [key]: '' }))
  }

  const requiredMappingsComplete = mappingFields.filter((field) => field.required).every((field) => mapping[field.key])
  const readyRows = Math.max(0, (validation?.valid_rows ?? 0) - (validation?.duplicate_rows ?? 0))

  return (
    <div className="page-grid data-management-page">
      <div className="page-intro"><span className="eyebrow">ENVIRONMENTAL DATA · OBSERVATIONS</span><h2>Manage sourced environmental records.</h2><p>Imports are validated before confirmation. Saved records remain separate from current Digital Twin datasets and model inputs.</p></div>
      <div className="data-management-grid">
        <section className="panel data-management-panel">
          <div className="panel-heading"><div><span className="eyebrow">CSV / XLSX</span><h2>Upload a dataset</h2></div><FileSpreadsheet size={18} /></div>
          <label className="upload-file-input"><span>Select .csv or .xlsx file</span><input type="file" accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange={selectFile} /></label>
          <p className="data-helper">Maximum 5 MiB and 5,000 rows. Legacy .xls is unsupported. Spreadsheet formulas are rejected, never evaluated.</p>
          {uploadBusy && <p className="data-status" role="status">Processing upload…</p>}
          {uploadError && <div className="data-error" role="alert"><AlertCircle size={15} />{uploadError}</div>}
          {preview && <>
            <div className="data-summary-line"><strong>{preview.filename}</strong><span>{preview.total_rows_read.toLocaleString()} rows · SHA-256 {preview.checksum.slice(0, 12)}…</span></div>
            <div className="column-mapping-grid">
              {mappingFields.map((field) => <label key={field.key}>{field.label}{field.required && <span className="required-mark">Required</span>}<select aria-label={`Map ${field.label}`} value={mapping[field.key] ?? ''} onChange={(event) => setColumn(field.key, event.target.value)}><option value="">{field.required ? 'Select source column' : 'Not mapped'}</option>{preview.columns.map((column) => <option key={column} value={column}>{column}</option>)}</select></label>)}
            </div>
            <div className="table-scroll data-preview-table"><table><thead><tr>{preview.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{preview.preview_rows.map((row, index) => <tr key={index}>{preview.columns.map((column) => <td key={column}>{row[column] ?? '—'}</td>)}</tr>)}</tbody></table></div>
            <div className="data-action-row"><button className="button button-secondary" onClick={() => void validateUpload()} disabled={uploadBusy || !requiredMappingsComplete}><Check size={14} />Validate mapping</button>{validation && readyRows > 0 && <button className="button button-primary" onClick={() => void confirmImport()} disabled={uploadBusy}><Upload size={14} />Confirm import ({readyRows} rows)</button>}</div>
          </>}
          {validation && <div className="validation-report" aria-live="polite"><strong>Validation report</strong><div className="validation-counts"><span>{validation.total_rows_read} read</span><span>{validation.valid_rows} valid</span><span>{validation.invalid_rows} invalid</span><span>{validation.duplicate_rows} duplicate</span></div>{validation.errors.length > 0 && <ul>{validation.errors.slice(0, 12).map((issue, index) => <li key={`${issue.row_number}-${issue.field}-${index}`}>Row {issue.row_number} · {issue.field}: {issue.reason}</li>)}</ul>}{validation.errors.length > 12 && <p>{validation.errors.length - 12} more validation issues.</p>}</div>}
          {importResult && <div className="data-success" role="status"><strong>Import {importResult.idempotent_retry ? 'already completed' : 'complete'}</strong><span>{importResult.rows_inserted} inserted · {importResult.rows_skipped} skipped · ID {importResult.import_id.slice(0, 12)}</span></div>}
        </section>

        <section className="panel data-management-panel">
          <div className="panel-heading"><div><span className="eyebrow">MANUAL ENTRY</span><h2>Save one observation</h2></div><Database size={18} /></div>
          <form className="environmental-record-form" onSubmit={submitRecord} noValidate>
            <label>Ward<select value={record.ward_id ?? ''} onChange={(event) => updateRecord('ward_id', event.target.value ? Number(event.target.value) : null)} required><option value="">Select ward</option>{wards.map((ward) => <option key={ward.ward_no} value={ward.ward_no}>{String(ward.ward_no).padStart(3, '0')} · {ward.location}</option>)}</select>{recordFieldErrors.ward_id && <small className="field-error">{recordFieldErrors.ward_id}</small>}</label>
            <label>Observation date<input type="date" value={record.observation_date} onChange={(event) => updateRecord('observation_date', event.target.value)} required />{recordFieldErrors.observation_date && <small className="field-error">{recordFieldErrors.observation_date}</small>}</label>
            <label>Metric<select value={record.metric} onChange={(event) => { const metric = event.target.value as EnvironmentalMetric; updateRecord('metric', metric); updateRecord('unit', metrics.find((item) => item.value === metric)?.defaultUnit ?? '') }}>{metrics.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
            <label>Value<input type="number" step={record.metric === 'population' ? 1 : 'any'} value={record.value} onChange={(event) => updateRecord('value', event.target.value)} required />{recordFieldErrors.value && <small className="field-error">{recordFieldErrors.value}</small>}</label>
            <label>Unit<select value={record.unit} onChange={(event) => updateRecord('unit', event.target.value)}>{selectedMetric.units.map((unit) => <option key={unit} value={unit}>{unit}</option>)}</select>{recordFieldErrors.unit && <small className="field-error">{recordFieldErrors.unit}</small>}</label>
            <label>Data classification<select value={record.data_classification} onChange={(event) => updateRecord('data_classification', event.target.value as EnvironmentalClassification)} required><option value="">Select classification</option>{classifications.map((classification) => <option key={classification} value={classification}>{classification}</option>)}</select>{recordFieldErrors.data_classification && <small className="field-error">{recordFieldErrors.data_classification}</small>}</label>
            <label>Source name<input value={record.source_name} onChange={(event) => updateRecord('source_name', event.target.value)} maxLength={300} required />{recordFieldErrors.source_name && <small className="field-error">{recordFieldErrors.source_name}</small>}</label>
            <label>Source reference<input value={record.source_reference ?? ''} onChange={(event) => updateRecord('source_reference', event.target.value)} maxLength={1000} /></label>
            <label className="environmental-notes-field">Notes <span className="label-hint">Optional</span><textarea rows={2} value={record.notes ?? ''} onChange={(event) => updateRecord('notes', event.target.value)} maxLength={2000} /></label>
            {recordError && <div className="data-error" role="alert"><AlertCircle size={15} />{recordError}</div>}
            {recordSuccess && <div className="data-success" role="status"><Check size={15} />{recordSuccess}</div>}
            <button className="button button-primary" type="submit" disabled={recordBusy}>{recordBusy ? 'Saving…' : 'Save observation'}</button>
          </form>
        </section>
      </div>

      <section className="panel data-management-panel">
        <div className="panel-heading"><div><span className="eyebrow">READ-ONLY HISTORY</span><h2>Recent environmental records</h2></div><span>{totalRecords.toLocaleString()} total</span></div>
        {historyError && <div className="data-error" role="alert"><AlertCircle size={15} />{historyError}</div>}
        {historyBusy ? <p className="data-status" role="status">Loading saved records…</p> : records.length ? <>
          <div className="table-scroll"><table><thead><tr><th>Ward</th><th>Date</th><th>Metric</th><th>Value</th><th>Classification</th><th>Source</th><th>Reference</th></tr></thead><tbody>{records.map((item) => <tr key={item.record_id}><td>{item.ward_id}</td><td>{item.observation_date}</td><td>{metrics.find((metric) => metric.value === item.metric)?.label ?? item.metric}</td><td>{formatMetric(item.value)} {item.unit}</td><td><span className={`classification-label classification-${item.data_classification}`}>{item.data_classification}</span></td><td>{item.source_name}</td><td>{item.source_reference || '—'}</td></tr>)}</tbody></table></div>
          <div className="data-pagination"><span>{offset + 1}–{Math.min(offset + records.length, totalRecords)} of {totalRecords}</span><div><button className="icon-button" aria-label="Previous records" onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} disabled={offset === 0}><ChevronLeft size={16} /></button><button className="icon-button" aria-label="Next records" onClick={() => setOffset(offset + PAGE_SIZE)} disabled={offset + PAGE_SIZE >= totalRecords}><ChevronRight size={16} /></button></div></div>
        </> : <div className="data-empty"><Database size={18} /><span>No saved observations yet.</span></div>}
      </section>
      <div className="data-integration-note"><AlertCircle size={16} /><span>Imported and manual records are stored as classified observations. They do not replace Digital Twin inputs, train models, or alter simulation outputs; matching date, unit, geographic and model-input contracts are required before downstream use.</span></div>
    </div>
  )
}