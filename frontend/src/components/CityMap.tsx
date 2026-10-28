import { useMemo, useState } from 'react'
import { GeoJSON, MapContainer, TileLayer } from 'react-leaflet'
import type { Feature, FeatureCollection } from 'geojson'
import type { Layer, PathOptions } from 'leaflet'
import { Layers3, MapPin, Maximize2 } from 'lucide-react'
import type { WardFeatureCollection } from '../types'

export type MapMetric = 'aqi' | 'temperature' | 'green_cover' | 'health_risk' | 'population'

const layers: Array<{ key: MapMetric; label: string; field: string; unit: string; name: string }> = [
  { key: 'aqi', label: 'AQI', field: 'final_AQI', unit: 'AQI', name: 'Air quality' },
  { key: 'temperature', label: 'UHI', field: 'mean_LST_C', unit: '°C', name: 'Surface temperature' },
  { key: 'green_cover', label: 'Green', field: 'green_cover', unit: '%', name: 'Green cover' },
  { key: 'health_risk', label: 'Health', field: 'health_risk', unit: 'score (0–1)', name: 'Composite health-risk score' },
  { key: 'population', label: 'Exposure', field: 'population', unit: 'people', name: 'Population exposure' },
]

interface CityMapProps {
  data: WardFeatureCollection | null
  activeLayer: MapMetric
  onLayerChange: (layer: MapMetric) => void
  selectedWard: number | null
  onWardSelect: (wardNumber: number) => void
  compact?: boolean
}

function colorFor(value: number | null, min: number, max: number): string {
  if (value === null || !Number.isFinite(value)) return '#66716e'
  const stops = ['#81c995', '#d3d466', '#efaf5d', '#eb785f', '#cb5961']
  const ratio = max === min ? 0.5 : Math.max(0, Math.min(1, (value - min) / (max - min)))
  return stops[Math.min(stops.length - 1, Math.floor(ratio * stops.length))]
}

function numericValue(feature: Feature, field: string): number | null {
  const value = feature.properties?.[field]
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

export function CityMap({
  data,
  activeLayer,
  onLayerChange,
  selectedWard,
  onWardSelect,
  compact = false,
}: CityMapProps) {
  const [expanded, setExpanded] = useState(false)
  const layer = layers.find((item) => item.key === activeLayer) ?? layers[0]
  const values = useMemo(() => {
    if (!data) return []
    return data.features
      .map((feature) => numericValue(feature as Feature, layer.field))
      .filter((value): value is number => value !== null)
  }, [data, layer.field])
  const min = values.length ? Math.min(...values) : 0
  const max = values.length ? Math.max(...values) : 0

  const renderFeature = (feature: Feature, leafletLayer: Layer) => {
    const properties = feature.properties ?? {}
    const wardNumber = Number(properties.ward_no ?? properties.Ward_No)
    const wardName = String(properties.location ?? properties.Ward_Name ?? `Ward ${wardNumber}`)
    const value = numericValue(feature, layer.field)
    const selected = Number.isFinite(wardNumber) && selectedWard === wardNumber
    if ('setStyle' in leafletLayer && typeof leafletLayer.setStyle === 'function') {
      const style: PathOptions = {
        color: selected ? '#f2f5d0' : '#182321',
        weight: selected ? 2.4 : 0.65,
        fillColor: colorFor(value, min, max),
        fillOpacity: selected ? 0.94 : 0.72,
      }
      leafletLayer.setStyle(style)
    }
    if ('bindTooltip' in leafletLayer && typeof leafletLayer.bindTooltip === 'function') {
      leafletLayer.bindTooltip(
        `<strong>${wardName}</strong><br>${layer.name}: ${value === null ? 'Unavailable' : value.toLocaleString('en-IN') + (layer.unit === 'people' ? '' : ` ${layer.unit}`)}`,
        { sticky: true, className: 'ward-tooltip' },
      )
    }
    if ('on' in leafletLayer && typeof leafletLayer.on === 'function' && Number.isFinite(wardNumber)) {
      leafletLayer.on('click', () => onWardSelect(wardNumber))
    }
  }

  const geoJson = data as unknown as FeatureCollection

  return (
    <section className={`map-shell ${compact ? 'map-shell-compact' : ''} ${expanded ? 'map-shell-expanded' : ''}`}>
      <div className="map-toolbar">
        <div className="map-toolbar-heading">
          <span className="map-icon"><MapPin size={15} /></span>
          <span><strong>Delhi ward atlas</strong><small>Municipal ward boundaries · live layer data</small></span>
        </div>
        <button className="icon-button map-expand" onClick={() => setExpanded((value) => !value)} aria-label="Toggle map size">
          <Maximize2 size={16} />
        </button>
      </div>
      <div className="map-layer-switcher" role="tablist" aria-label="Map data layer">
        <span className="layer-label"><Layers3 size={14} /> Layer</span>
        {layers.map((item) => (
          <button
            key={item.key}
            role="tab"
            aria-selected={activeLayer === item.key}
            className={`layer-tab ${activeLayer === item.key ? 'is-active' : ''}`}
            onClick={() => onLayerChange(item.key)}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div className="map-frame">
        {data ? (
          <MapContainer center={[28.6139, 77.209]} zoom={9} minZoom={8} maxZoom={13} scrollWheelZoom className="city-leaflet">
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <GeoJSON
              key={`${activeLayer}-${selectedWard ?? 'none'}`}
              data={geoJson}
              onEachFeature={renderFeature}
            />
          </MapContainer>
        ) : (
          <div className="map-unavailable">
            <MapPin size={22} />
            <strong>Ward map unavailable</strong>
            <span>Boundary geometry could not be loaded from the backend.</span>
          </div>
        )}
        {values.length > 0 && (
          <div className="map-legend">
            <div><span>{layer.name}</span><strong>{layer.unit}</strong></div>
            <div className="legend-gradient" />
            <div className="legend-range"><span>{min.toLocaleString('en-IN', { maximumFractionDigits: 1 })}</span><span>{max.toLocaleString('en-IN', { maximumFractionDigits: 1 })}</span></div>
          </div>
        )}
        <div className="map-source-badge"><span /> {data?.features.length ?? 0} wards · backend boundaries</div>
      </div>
    </section>
  )
}
