import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  BookMarked, MapPin, Calendar, DollarSign,
  Trash2, ExternalLink, Loader, AlertTriangle,
  Plus, Clock
} from 'lucide-react'
import { tripApi } from '../services/api'

const STATUS_BADGE = {
  completed: 'badge-success',
  running: 'badge-info',
  pending: 'badge-neutral',
  failed: 'badge-error',
}

export default function SavedTripsPage() {
  const [trips, setTrips] = useState([])
  const [loading, setLoading] = useState(true)
  const [deletingId, setDeletingId] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    loadTrips()
  }, [])

  const loadTrips = async () => {
    try {
      const data = await tripApi.list()
      setTrips(data)
    } catch (err) {
      setError('Failed to load trips. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  const deleteTrip = async (tripId) => {
    if (!confirm('Delete this trip? This cannot be undone.')) return
    setDeletingId(tripId)
    try {
      await tripApi.delete(tripId)
      setTrips(prev => prev.filter(t => t.id !== tripId))
    } catch (err) {
      setError('Failed to delete trip.')
    } finally {
      setDeletingId(null)
    }
  }

  const getDuration = (dep, ret) => {
    if (!dep || !ret) return '—'
    const d1 = new Date(dep), d2 = new Date(ret)
    const days = Math.round((d2 - d1) / (1000 * 60 * 60 * 24))
    return `${days} day${days !== 1 ? 's' : ''}`
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="max-w-5xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <BookMarked className="w-6 h-6 text-brand-600" />
              Saved Trips
            </h1>
            <p className="text-gray-500 text-sm mt-1">
              {trips.length} trip{trips.length !== 1 ? 's' : ''} generated
            </p>
          </div>
          <Link to="/plan" className="btn-primary flex items-center gap-2 text-sm">
            <Plus className="w-4 h-4" /> New Trip
          </Link>
        </div>

        {error && (
          <div className="mb-6 flex items-start gap-3 p-4 bg-amber-50 border border-amber-100 rounded-xl text-sm text-amber-800">
            <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
            {error}
          </div>
        )}

        {loading ? (
          <div className="text-center py-16">
            <Loader className="w-7 h-7 text-brand-500 spinner mx-auto mb-3" />
            <p className="text-gray-400 text-sm">Loading trips…</p>
          </div>
        ) : trips.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <MapPin className="w-8 h-8 text-gray-300" />
            </div>
            <h2 className="text-lg font-semibold text-gray-700 mb-2">No trips yet</h2>
            <p className="text-gray-400 text-sm mb-6">Plan your first trip and it will appear here.</p>
            <Link to="/plan" className="btn-primary">Plan a Trip</Link>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {trips.map(trip => (
              <div key={trip.id} className="card-hover p-5">
                {/* Status */}
                <div className="flex items-center justify-between mb-3">
                  <span className={STATUS_BADGE[trip.status] + ' badge'}>
                    {trip.status}
                  </span>
                  <button
                    onClick={() => deleteTrip(trip.id)}
                    disabled={deletingId === trip.id}
                    className="p-1.5 text-gray-300 hover:text-red-400 hover:bg-red-50 rounded-lg transition-colors"
                    title="Delete trip"
                  >
                    {deletingId === trip.id
                      ? <Loader className="w-3.5 h-3.5 spinner" />
                      : <Trash2 className="w-3.5 h-3.5" />
                    }
                  </button>
                </div>

                {/* Title */}
                <h3 className="text-base font-semibold text-gray-900 mb-1 line-clamp-1">{trip.title}</h3>

                {/* Details */}
                <div className="space-y-1.5 text-xs text-gray-500 mb-4">
                  <div className="flex items-center gap-1.5">
                    <MapPin className="w-3 h-3 flex-shrink-0" />
                    {trip.origin} → {trip.destination}
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Calendar className="w-3 h-3 flex-shrink-0" />
                    {trip.departure_date} · {getDuration(trip.departure_date, trip.return_date)}
                  </div>
                  <div className="flex items-center gap-1.5">
                    <DollarSign className="w-3 h-3 flex-shrink-0" />
                    {trip.budget?.toLocaleString()} {trip.currency}
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Clock className="w-3 h-3 flex-shrink-0" />
                    {trip.created_at
                      ? new Date(trip.created_at).toLocaleDateString()
                      : '—'}
                  </div>
                </div>

                {/* Style & Interests */}
                {trip.travel_style && (
                  <div className="flex flex-wrap gap-1.5 mb-4">
                    <span className="badge badge-info">{trip.travel_style}</span>
                    {(trip.interests || []).slice(0, 2).map(i => (
                      <span key={i} className="badge badge-neutral">{i}</span>
                    ))}
                    {(trip.interests?.length || 0) > 2 && (
                      <span className="badge badge-neutral">+{trip.interests.length - 2}</span>
                    )}
                  </div>
                )}

                {/* Action */}
                {trip.status === 'completed' ? (
                  <Link
                    to={`/results/${trip.id}`}
                    className="btn-primary w-full text-center text-sm py-2.5 flex items-center justify-center gap-1.5"
                  >
                    View Plan <ExternalLink className="w-3.5 h-3.5" />
                  </Link>
                ) : trip.status === 'running' || trip.status === 'pending' ? (
                  <Link
                    to={`/agents/${trip.id}`}
                    className="btn-secondary w-full text-center text-sm py-2.5 flex items-center justify-center gap-1.5"
                  >
                    <Loader className="w-3.5 h-3.5 spinner" /> View Progress
                  </Link>
                ) : (
                  <Link
                    to={`/results/${trip.id}`}
                    className="btn-secondary w-full text-center text-sm py-2.5 flex items-center justify-center gap-1.5"
                  >
                    View Partial Plan <ExternalLink className="w-3.5 h-3.5" />
                  </Link>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
