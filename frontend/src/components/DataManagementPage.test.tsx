import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import DataManagementPage from './DataManagementPage'

const mocks = vi.hoisted(() => ({
  environmentalRecords: vi.fn(),
  environmentalPreview: vi.fn(),
  validateEnvironmentalUpload: vi.fn(),
  importEnvironmentalUpload: vi.fn(),
  createEnvironmentalRecord: vi.fn(),
}))

vi.mock('../api', () => ({
  requests: mocks,
  errorMessage: (error: unknown) => error instanceof Error ? error.message : 'Backend unavailable',
  formatMetric: (value: unknown) => typeof value === 'number' ? String(value) : 'Unavailable',
}))

const wards = [{
  city: 'Delhi', zone: 'Ward_80', location: 'CHANDNI CHOWK', ward_no: 80,
}]

const preview = {
  filename: 'ward-observations.csv',
  checksum: 'a'.repeat(64),
  columns: ['Ward_No', 'timestamp_local', 'parameter', 'value', 'units', 'data_classification', 'station_name', 'sensor_id'],
  preview_rows: [{
    Ward_No: '80', timestamp_local: '2026-07-01', parameter: 'pm25', value: '59.1',
    units: 'µg/m³', data_classification: 'observed', station_name: 'Station A', sensor_id: 'sensor-80',
  }],
  total_rows_read: 1,
}

const recordPage = {
  records: [{
    record_id: 'ENV-123', ward_id: 80, observation_date: '2026-07-01', metric: 'pm25',
    value: 59.1, unit: 'µg/m³', data_classification: 'observed', source_name: 'Station A',
    source_reference: 'sensor-80', notes: null, created_at: '2026-07-02T00:00:00Z',
  }],
  total: 1,
  limit: 20,
  offset: 0,
}

describe('Environmental data management', () => {
  beforeEach(() => {
    Object.values(mocks).forEach((mock) => mock.mockReset())
    mocks.environmentalRecords.mockResolvedValue({ data: recordPage })
    mocks.environmentalPreview.mockResolvedValue({ data: preview })
    mocks.validateEnvironmentalUpload.mockResolvedValue({ data: {
      filename: preview.filename, checksum: preview.checksum, total_rows_read: 1,
      valid_rows: 1, invalid_rows: 0, duplicate_rows: 0, errors: [],
    } })
    mocks.importEnvironmentalUpload.mockResolvedValue({ data: {
      filename: preview.filename, checksum: preview.checksum, total_rows_read: 1,
      valid_rows: 1, invalid_rows: 0, duplicate_rows: 0, errors: [],
      import_id: 'import-test-id', imported_at: '2026-07-02T00:00:00Z',
      rows_inserted: 1, rows_skipped: 0, idempotent_retry: false,
    } })
    mocks.createEnvironmentalRecord.mockResolvedValue({ data: recordPage.records[0] })
  })

  it('previews, maps, validates and confirms an import before refreshing history', async () => {
    render(<DataManagementPage wards={wards} />)
    const file = new File(['ward,data'], 'ward-observations.csv', { type: 'text/csv' })
    fireEvent.change(screen.getByLabelText(/Select \.csv or \.xlsx file/i), { target: { files: [file] } })

    expect(await screen.findByText('ward-observations.csv')).toBeInTheDocument()
    expect(screen.getByLabelText('Map Ward ID')).toHaveValue('Ward_No')
    expect(screen.getByLabelText('Map Observation date')).toHaveValue('timestamp_local')
    expect(await screen.findByText('Station A')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /validate mapping/i }))
    expect(await screen.findByText('Validation report')).toBeInTheDocument()
    expect(mocks.validateEnvironmentalUpload).toHaveBeenCalledWith(file, expect.objectContaining({
      ward_id: 'Ward_No',
      observation_date: 'timestamp_local',
      metric: 'parameter',
      value: 'value',
      unit: 'units',
      data_classification: 'data_classification',
      source_name: 'station_name',
    }))

    fireEvent.click(screen.getByRole('button', { name: /confirm import/i }))
    expect(await screen.findByText('Import complete')).toBeInTheDocument()
    expect(mocks.importEnvironmentalUpload).toHaveBeenCalledWith(file, expect.any(Object), preview.checksum)
    await waitFor(() => expect(mocks.environmentalRecords).toHaveBeenCalledTimes(2))
  })

  it('requires explicit manual fields, submits a typed record, and shows classified history', async () => {
    render(<DataManagementPage wards={wards} />)
    expect(await screen.findByText('Station A')).toBeInTheDocument()
    expect(screen.getByText('observed')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /save observation/i }))
    expect(await screen.findByText('Select a ward.')).toBeInTheDocument()
    expect(mocks.createEnvironmentalRecord).not.toHaveBeenCalled()

    fireEvent.change(screen.getByLabelText('Ward'), { target: { value: '80' } })
    fireEvent.change(screen.getByLabelText('Observation date'), { target: { value: '2026-07-03' } })
    fireEvent.change(screen.getByLabelText('Metric'), { target: { value: 'pm25' } })
    fireEvent.change(screen.getByLabelText('Value'), { target: { value: '12.4' } })
    fireEvent.change(screen.getByLabelText('Source name'), { target: { value: 'Manual sensor record' } })
    fireEvent.change(screen.getByLabelText('Data classification'), { target: { value: 'observed' } })
    fireEvent.click(screen.getByRole('button', { name: /save observation/i }))

    expect(await screen.findByText(/Saved ENV-123 as observed/)).toBeInTheDocument()
    expect(mocks.createEnvironmentalRecord).toHaveBeenCalledWith(expect.objectContaining({
      ward_id: 80,
      observation_date: '2026-07-03',
      metric: 'pm25',
      value: 12.4,
      unit: 'µg/m³',
      data_classification: 'observed',
      source_name: 'Manual sensor record',
    }))
  })

  it('shows API errors without clearing entered manual data', async () => {
    mocks.createEnvironmentalRecord.mockRejectedValue(new Error('Record conflict'))
    render(<DataManagementPage wards={wards} />)
    fireEvent.change(await screen.findByLabelText('Ward'), { target: { value: '80' } })
    fireEvent.change(screen.getByLabelText('Observation date'), { target: { value: '2026-07-03' } })
    fireEvent.change(screen.getByLabelText('Value'), { target: { value: '15' } })
    fireEvent.change(screen.getByLabelText('Source name'), { target: { value: 'Sensor' } })
    fireEvent.click(screen.getByRole('button', { name: /save observation/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Record conflict')
    expect(screen.getByLabelText('Value')).toHaveValue(15)
  })
})