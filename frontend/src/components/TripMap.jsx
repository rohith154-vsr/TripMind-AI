import { useEffect, useRef } from 'react'
import { MapContainer, TileLayer, Marker, Popup, CircleMarker } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Fix Leaflet's default icon path issue with Vite
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

const CATEGORY_COLORS = {
  food: '#f97316',        // orange
  attraction: '#6366f1',  // indigo
  historic: '#a16207',    // amber
  leisure: '#16a34a',     // green
  other: '#6b7280',       // gray
}

const isValidCoord = (lat, lon) => {
  if (lat == null || lon == null) return false
  const latN = parseFloat(lat)
  const lonN = parseFloat(lon)
  if (isNaN(latN) || isNaN(lonN)) return false
  if (latN < -90 || latN > 90 || lonN < -180 || lonN > 180) return false
  // Exclude Null Island (0,0)
  if (Math.abs(latN) < 0.001 && Math.abs(lonN) < 0.001) return false
  return true
}

export default function TripMap({ coordinates, pois = [], restaurants = [], attractions = [] }) {
  if (!coordinates || !isValidCoord(coordinates.lat, coordinates.lon)) {
    return (
      <div className="h-64 bg-gray-50 rounded-xl flex items-center justify-center border border-gray-100">
        <p className="text-gray-400 text-sm">Map unavailable — location coordinates not verified</p>
      </div>
    )
  }

  const center = [parseFloat(coordinates.lat), parseFloat(coordinates.lon)]

  // Strict filter: only display markers that have verified OSM provenance and authentic coordinates
  const rawMarkers = [
    ...pois.filter(p => p.is_verified_osm && isValidCoord(p.lat, p.lon)).map(p => ({ ...p, source: 'osm' })),
    ...restaurants.filter(r => r.is_verified_osm && isValidCoord(r.lat, r.lon)).map(r => ({ ...r, category: 'food', source: 'osm' })),
    ...attractions.filter(a => a.is_verified_osm && isValidCoord(a.lat, a.lon)).map(a => ({ ...a, category: 'attraction', source: 'osm' })),
  ]

  // Deduplicate markers by normalized name and coordinate pair
  const seen = new Set()
  const allMarkers = []
  for (const m of rawMarkers) {
    const key = `${(m.name || '').trim().toLowerCase()}_${m.lat?.toFixed(4)}_${m.lon?.toFixed(4)}`
    if (!seen.has(key)) {
      seen.add(key)
      allMarkers.push(m)
    }
  }

  return (
    <MapContainer
      center={center}
      zoom={13}
      className="w-full rounded-xl"
      style={{ height: '420px' }}
    >
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      />

      {/* Main destination marker */}
      <Marker position={center}>
        <Popup>
          <div className="font-medium">{coordinates.display_name || 'Destination'}</div>
        </Popup>
      </Marker>

      {/* POI markers */}
      {allMarkers.map((poi, i) => (
        <CircleMarker
          key={i}
          center={[poi.lat, poi.lon]}
          radius={7}
          pathOptions={{
            color: 'white',
            weight: 2,
            fillColor: CATEGORY_COLORS[poi.category] || CATEGORY_COLORS.other,
            fillOpacity: 0.9,
          }}
        >
          <Popup>
            <div>
              <div className="font-semibold text-sm">{poi.name}</div>
              {poi.type && <div className="text-xs text-gray-500 mt-0.5 capitalize">{poi.type}</div>}
              {poi.cuisine && <div className="text-xs text-gray-500">Cuisine: {poi.cuisine}</div>}
              {poi.opening_hours && <div className="text-xs text-gray-500">Hours: {poi.opening_hours}</div>}
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  )
}
