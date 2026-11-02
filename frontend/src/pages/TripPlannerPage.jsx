import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  MapPin, Calendar, Users, DollarSign, Plane,
  Sparkles, ChevronDown, AlertCircle, Loader
} from 'lucide-react'
import { tripApi } from '../services/api'

const TRAVEL_STYLES = ['Adventure', 'Relaxation', 'Luxury', 'Budget', 'Cultural']
const INTERESTS = ['Nature', 'Food', 'Shopping', 'Historical Places', 'Photography', 'Nightlife']
const CURRENCIES = ['USD', 'EUR', 'GBP', 'INR', 'JPY', 'AUD', 'CAD', 'SGD', 'AED', 'THB']

export default function TripPlannerPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [form, setForm] = useState({
    origin: '',
    destination: '',
    departure_date: '',
    return_date: '',
    num_travelers: 1,
    budget: '',
    currency: 'USD',
    travel_style: 'Adventure',
    interests: [],
  })

  const today = new Date().toISOString().split('T')[0]

  const updateField = (field, value) => {
    setForm(prev => ({ ...prev, [field]: value }))
    setError('')
  }

  const toggleInterest = (interest) => {
    setForm(prev => ({
      ...prev,
      interests: prev.interests.includes(interest)
        ? prev.interests.filter(i => i !== interest)
        : [...prev.interests, interest],
    }))
  }

  const validate = () => {
    if (!form.origin.trim()) return 'Please enter your starting location.'
    if (!form.destination.trim()) return 'Please enter your destination.'
    if (!form.departure_date) return 'Please select a departure date.'
    if (!form.return_date) return 'Please select a return date.'
    if (form.return_date <= form.departure_date) return 'Return date must be after departure date.'
    if (!form.budget || Number(form.budget) <= 0) return 'Please enter a valid budget.'
    return null
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const validationError = validate()
    if (validationError) {
      setError(validationError)
      return
    }

    setLoading(true)
    setError('')

    try {
      const payload = {
        ...form,
        num_travelers: Number(form.num_travelers),
        budget: Number(form.budget),
      }
      const data = await tripApi.generate(payload)
      navigate(`/agents/${data.trip_id}`)
    } catch (err) {
      setError(err.message || 'Failed to start trip generation. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="max-w-3xl mx-auto px-4 sm:px-6">
        {/* Header */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-brand-50 border border-brand-100 rounded-full text-xs font-medium text-brand-700 mb-4">
            <Sparkles className="w-3.5 h-3.5" />
            AI-Powered Planning
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Plan Your Trip</h1>
          <p className="text-gray-500 text-sm">Fill in your details and six AI agents will build your personalized itinerary.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Locations */}
          <div className="card p-6">
            <h2 className="text-base font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Plane className="w-4 h-4 text-brand-600" /> Locations
            </h2>
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="label">Starting Location *</label>
                <div className="relative">
                  <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    className="input-field pl-9"
                    placeholder="e.g. New York, USA"
                    value={form.origin}
                    onChange={e => updateField('origin', e.target.value)}
                    required
                  />
                </div>
              </div>
              <div>
                <label className="label">Destination *</label>
                <div className="relative">
                  <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-brand-500" />
                  <input
                    type="text"
                    className="input-field pl-9"
                    placeholder="e.g. Tokyo, Japan"
                    value={form.destination}
                    onChange={e => updateField('destination', e.target.value)}
                    required
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Dates */}
          <div className="card p-6">
            <h2 className="text-base font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Calendar className="w-4 h-4 text-brand-600" /> Travel Dates
            </h2>
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="label">Departure Date *</label>
                <input
                  type="date"
                  className="input-field"
                  min={today}
                  value={form.departure_date}
                  onChange={e => updateField('departure_date', e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="label">Return Date *</label>
                <input
                  type="date"
                  className="input-field"
                  min={form.departure_date || today}
                  value={form.return_date}
                  onChange={e => updateField('return_date', e.target.value)}
                  required
                />
              </div>
            </div>
          </div>

          {/* Travelers & Budget */}
          <div className="card p-6">
            <h2 className="text-base font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <DollarSign className="w-4 h-4 text-brand-600" /> Travelers & Budget
            </h2>
            <div className="grid sm:grid-cols-3 gap-4">
              <div>
                <label className="label">Travelers *</label>
                <div className="relative">
                  <Users className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="number"
                    className="input-field pl-9"
                    min="1"
                    max="50"
                    value={form.num_travelers}
                    onChange={e => updateField('num_travelers', e.target.value)}
                  />
                </div>
              </div>
              <div>
                <label className="label">Total Budget *</label>
                <input
                  type="number"
                  className="input-field"
                  placeholder="e.g. 3000"
                  min="1"
                  value={form.budget}
                  onChange={e => updateField('budget', e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="label">Currency</label>
                <div className="relative">
                  <select
                    className="input-field appearance-none pr-8"
                    value={form.currency}
                    onChange={e => updateField('currency', e.target.value)}
                  >
                    {CURRENCIES.map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                  <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                </div>
              </div>
            </div>
          </div>

          {/* Travel Style */}
          <div className="card p-6">
            <h2 className="text-base font-semibold text-gray-900 mb-4">Travel Style</h2>
            <div className="flex flex-wrap gap-2">
              {TRAVEL_STYLES.map(style => (
                <button
                  key={style}
                  type="button"
                  onClick={() => updateField('travel_style', style)}
                  className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 border ${
                    form.travel_style === style
                      ? 'bg-brand-600 text-white border-brand-600 shadow-sm'
                      : 'bg-white text-gray-600 border-gray-200 hover:border-brand-300 hover:text-brand-600'
                  }`}
                >
                  {style}
                </button>
              ))}
            </div>
          </div>

          {/* Interests */}
          <div className="card p-6">
            <h2 className="text-base font-semibold text-gray-900 mb-1">Interests</h2>
            <p className="text-xs text-gray-400 mb-4">Select all that apply</p>
            <div className="flex flex-wrap gap-2">
              {INTERESTS.map(interest => (
                <button
                  key={interest}
                  type="button"
                  onClick={() => toggleInterest(interest)}
                  className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 border ${
                    form.interests.includes(interest)
                      ? 'bg-brand-50 text-brand-700 border-brand-300'
                      : 'bg-white text-gray-600 border-gray-200 hover:border-gray-300'
                  }`}
                >
                  {interest}
                </button>
              ))}
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-100 rounded-xl text-sm text-red-700">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              {error}
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full flex items-center justify-center gap-2 text-base py-4"
          >
            {loading ? (
              <>
                <Loader className="w-5 h-5 spinner" />
                Starting agents…
              </>
            ) : (
              <>
                <Sparkles className="w-5 h-5" />
                Generate My Trip
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
