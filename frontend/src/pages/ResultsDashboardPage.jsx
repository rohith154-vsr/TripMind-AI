import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  MapPin, Cloud, DollarSign, Calendar, Search, Compass,
  Sun, CloudRain, ThumbsUp, ThumbsDown, Star, UtensilsCrossed,
  ChevronDown, ChevronUp, RefreshCw, BookMarked, ArrowLeft,
  Loader, AlertTriangle, Info, Thermometer, Wind
} from 'lucide-react'
import { tripApi } from '../services/api'
import TripMap from '../components/TripMap'
import { WeatherChart, BudgetChart } from '../components/Charts'

function Section({ id, title, icon: Icon, iconColor = 'text-brand-600', children }) {
  return (
    <section id={id} className="card p-6 md:p-8">
      <div className="flex items-center gap-3 mb-6">
        <div className={`w-9 h-9 rounded-xl bg-gray-50 flex items-center justify-center`}>
          <Icon className={`w-5 h-5 ${iconColor}`} />
        </div>
        <h2 className="text-xl font-bold text-gray-900">{title}</h2>
      </div>
      {children}
    </section>
  )
}

function WeatherBadge({ code }) {
  const good = code <= 3
  return (
    <span className={`badge ${good ? 'badge-success' : code <= 65 ? 'badge-warning' : 'badge-error'}`}>
      {good ? <Sun className="w-3 h-3" /> : <CloudRain className="w-3 h-3" />}
      {code <= 3 ? 'Clear' : code <= 45 ? 'Cloudy' : code <= 65 ? 'Rain' : 'Storm'}
    </span>
  )
}

function formatCurrency(amount, currency = 'USD') {
  if (amount == null || isNaN(Number(amount))) return '—'
  const curr = (currency || 'USD').toUpperCase()
  const symbols = {
    USD: '$',
    EUR: '€',
    GBP: '£',
    INR: '₹',
    JPY: '¥',
    CAD: 'CA$',
    AUD: 'AU$',
  }
  const sym = symbols[curr] || `${curr} `
  return `${sym}${Number(amount).toLocaleString(undefined, { maximumFractionDigits: 0 })}`
}

function DayCard({ day, idx, currency = 'USD' }) {
  const [expanded, setExpanded] = useState(idx === 0)

  const allActivities = [
    ...(day.morning?.activities || []),
    ...(day.afternoon?.activities || []),
    ...(day.evening?.activities || []),
  ]

  return (
    <div className="border border-gray-100 rounded-xl overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-brand-50 rounded-lg flex items-center justify-center text-brand-700 text-xs font-bold">
            {day.day_number}
          </div>
          <div className="text-left">
            <div className="text-sm font-semibold text-gray-900">{day.theme || `Day ${day.day_number}`}</div>
            <div className="text-xs text-gray-400">{day.date} · {allActivities.length} activities</div>
          </div>
        </div>
        {expanded ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-gray-50 pt-4">
          {day.weather_note && (
            <div className="flex items-start gap-2 p-3 bg-sky-50 rounded-lg text-xs text-sky-700">
              <Cloud className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
              {day.weather_note}
            </div>
          )}

          {['morning', 'afternoon', 'evening'].map(period => {
            const periodData = day[period]
            if (!periodData?.activities?.length) return null
            return (
              <div key={period}>
                <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 capitalize">
                  {period} · {periodData.time}
                </div>
                <div className="space-y-2">
                  {periodData.activities.map((act, i) => (
                    <div key={i} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                      <div className="text-xs text-gray-400 w-12 flex-shrink-0 mt-0.5">{act.time}</div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-gray-900">{act.name}</div>
                        <div className="text-xs text-gray-500 mt-0.5 leading-relaxed">{act.description}</div>
                        <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                          {act.duration_hours && <span>⏱ {act.duration_hours}h</span>}
                          {act.cost_per_person > 0 && <span>💰 ~{formatCurrency(act.cost_per_person, currency)}/person</span>}
                          {act.location && <span>📍 {act.location}</span>}
                        </div>
                        {act.tips && (
                          <div className="mt-2 text-xs text-amber-700 bg-amber-50 px-2 py-1 rounded">
                            💡 {act.tips}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}

          {day.meals && (
            <div className="grid grid-cols-3 gap-2 mt-3">
              {Object.entries(day.meals).map(([meal, place]) => (
                <div key={meal} className="text-center p-2 bg-orange-50 rounded-lg">
                  <div className="text-xs text-orange-500 font-medium capitalize">{meal}</div>
                  <div className="text-xs text-gray-600 mt-0.5 truncate">{place}</div>
                </div>
              ))}
            </div>
          )}

          {day.daily_budget_estimate > 0 && (
            <div className="text-xs text-gray-500 text-right">
              Est. daily spend: <span className="font-semibold text-gray-700">{formatCurrency(day.daily_budget_estimate, currency)}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function ResultsDashboardPage() {
  const { tripId } = useParams()
  const navigate = useNavigate()
  const [trip, setTrip] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    loadTrip()
  }, [tripId])

  const loadTrip = async () => {
    try {
      const data = await tripApi.get(tripId)
      if (data.status === 'running' || data.status === 'pending') {
        navigate(`/agents/${tripId}`)
        return
      }
      setTrip(data)
    } catch (err) {
      setError('Failed to load trip results.')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader className="w-8 h-8 text-brand-600 spinner mx-auto mb-3" />
          <p className="text-gray-500 text-sm">Loading your travel plan…</p>
        </div>
      </div>
    )
  }

  if (error || !trip) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="w-8 h-8 text-amber-500 mx-auto mb-3" />
          <p className="text-gray-700 font-medium mb-2">{error || 'Trip not found'}</p>
          <Link to="/plan" className="btn-primary text-sm">Plan a New Trip</Link>
        </div>
      </div>
    )
  }

  const result = trip.result || {}
  const coordinator = result.coordinator || {}
  const destination = result.destination_research || {}
  const weather = result.weather_intelligence || {}
  const local = result.local_discovery || {}
  const budget = result.budget_management || {}
  const itinerary = result.itinerary_planning || {}

  const mapCoords = destination.coordinates || weather.coordinates || local.coordinates
  const rawPois = local.raw_osm_pois || []
  const restaurants = local.featured_restaurants || []
  const attractions = local.top_attractions || []

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 space-y-6">

        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <button
              onClick={() => navigate('/saved')}
              className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900 mb-3 transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Back to Saved Trips
            </button>
            <h1 className="text-2xl md:text-3xl font-bold text-gray-900">
              {coordinator.trip_title || trip.title}
            </h1>
            <div className="flex flex-wrap gap-3 mt-2 text-sm text-gray-500">
              <span className="flex items-center gap-1"><MapPin className="w-3.5 h-3.5" />{trip.destination}</span>
              <span className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5" />{trip.departure_date} → {trip.return_date}</span>
              <span className="flex items-center gap-1"><DollarSign className="w-3.5 h-3.5" />{formatCurrency(trip.budget, trip.currency)}</span>
            </div>
          </div>
          <div className="flex gap-2 flex-shrink-0">
            <Link to="/plan" className="btn-secondary text-sm flex items-center gap-1.5 py-2">
              <RefreshCw className="w-3.5 h-3.5" /> New Trip
            </Link>
          </div>
        </div>

        {/* Trip Overview */}
        {coordinator.executive_summary && (
          <Section id="overview" title="Trip Overview" icon={Compass}>
            <p className="text-gray-600 leading-relaxed mb-6">{coordinator.executive_summary}</p>
            {coordinator.trip_highlights?.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-3">Trip Highlights</h3>
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {coordinator.trip_highlights.map((h, i) => (
                    <div key={i} className="flex items-start gap-2 p-3 bg-brand-50 rounded-lg text-sm text-brand-800">
                      <Star className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 text-brand-500" />
                      {h}
                    </div>
                  ))}
                </div>
              </div>
            )}
            {coordinator.key_recommendations?.length > 0 && (
              <div className="mt-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-3">Key Recommendations</h3>
                <div className="space-y-2">
                  {coordinator.key_recommendations.slice(0, 5).map((rec, i) => (
                    <div key={i} className="flex items-start gap-2 text-sm">
                      <span className={`badge mt-0.5 ${rec.priority === 'must' ? 'badge-error' : rec.priority === 'should' ? 'badge-info' : 'badge-neutral'}`}>
                        {rec.priority}
                      </span>
                      <span className="text-gray-600">{rec.recommendation}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Section>
        )}

        {/* Destination Research */}
        {destination.destination_overview && !destination.error && (
          <Section id="destination" title="Destination Research" icon={MapPin} iconColor="text-indigo-600">
            <div className="grid sm:grid-cols-2 gap-4 mb-6">
              {[
                ['Language', destination.destination_overview.language],
                ['Currency', destination.destination_overview.currency],
                ['Best Time', destination.destination_overview.best_time_to_visit],
                ['Getting Around', destination.destination_overview.getting_around],
              ].filter(([, v]) => v).map(([label, value]) => (
                <div key={label} className="p-3 bg-gray-50 rounded-lg">
                  <div className="text-xs text-gray-400 mb-1">{label}</div>
                  <div className="text-sm text-gray-800 font-medium">{value}</div>
                </div>
              ))}
            </div>

            {destination.top_attractions?.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-3">Top Attractions</h3>
                <div className="grid sm:grid-cols-2 gap-3">
                  {destination.top_attractions.slice(0, 6).map((attr, i) => (
                    <div key={i} className="p-4 border border-gray-100 rounded-xl hover:border-brand-200 transition-colors">
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <div className="text-sm font-semibold text-gray-900">{attr.name}</div>
                        <span className="badge badge-neutral capitalize">{attr.type}</span>
                      </div>
                      <p className="text-xs text-gray-500 leading-relaxed mb-2">{attr.description}</p>
                      <div className="flex gap-3 text-xs text-gray-400">
                        {attr.estimated_duration_hours && <span>⏱ {attr.estimated_duration_hours}h</span>}
                        {attr.admission_fee_usd != null && (
                          <span>{attr.admission_fee_usd === 0 ? '🆓 Free' : `💰 ${formatCurrency(attr.admission_fee_usd, trip.currency || budget.budget_summary?.currency || 'USD')}`}</span>
                        )}
                        {attr.best_time && <span>🕐 {attr.best_time}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {destination.cultural_tips?.length > 0 && (
              <div className="mt-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Cultural Tips</h3>
                <div className="grid sm:grid-cols-2 gap-2">
                  {destination.cultural_tips.map((tip, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs text-gray-600 p-2 bg-amber-50 rounded-lg">
                      <Info className="w-3.5 h-3.5 text-amber-500 mt-0.5 flex-shrink-0" />
                      {tip}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Section>
        )}

        {/* Itinerary */}
        {itinerary.days?.length > 0 && !itinerary.error && (
          <Section id="itinerary" title="Day-by-Day Itinerary" icon={Calendar} iconColor="text-violet-600">
            {itinerary.itinerary_overview && (
              <div className="mb-5 p-4 bg-violet-50 rounded-xl">
                <div className="text-sm font-semibold text-violet-800 mb-1">{itinerary.itinerary_overview.theme}</div>
                <div className="flex flex-wrap gap-2 mt-2">
                  {(itinerary.itinerary_overview.highlights || []).map((h, i) => (
                    <span key={i} className="badge bg-violet-100 text-violet-700">{h}</span>
                  ))}
                </div>
              </div>
            )}
            <div className="space-y-3">
              {itinerary.days.map((day, idx) => (
                <DayCard key={idx} day={day} idx={idx} currency={trip.currency || budget.budget_summary?.currency || 'USD'} />
              ))}
            </div>
          </Section>
        )}

        {/* Budget */}
        {budget.budget_summary && !budget.error && (
          <Section id="budget" title="Budget Breakdown" icon={DollarSign} iconColor="text-emerald-600">
            <div className="grid sm:grid-cols-3 gap-4 mb-6">
              <div className="p-4 bg-emerald-50 rounded-xl text-center">
                <div className="text-2xl font-bold text-emerald-700">
                  {budget.budget_summary.currency} {budget.budget_summary.total_budget?.toLocaleString()}
                </div>
                <div className="text-xs text-emerald-600 mt-1">Total Budget</div>
              </div>
              <div className="p-4 bg-gray-50 rounded-xl text-center">
                <div className="text-2xl font-bold text-gray-800">
                  {budget.budget_summary.currency} {budget.total_estimated_cost?.toLocaleString() || '—'}
                </div>
                <div className="text-xs text-gray-500 mt-1">Estimated Cost</div>
              </div>
              <div className={`p-4 rounded-xl text-center ${
                budget.budget_vs_estimate?.status === 'under_budget' ? 'bg-green-50' : 'bg-amber-50'
              }`}>
                <div className={`text-2xl font-bold ${
                  budget.budget_vs_estimate?.status === 'under_budget' ? 'text-green-700' : 'text-amber-700'
                }`}>
                  {budget.budget_vs_estimate?.status === 'under_budget' ? '✓ ' : '⚠ '}
                  {budget.budget_vs_estimate?.status?.replace('_', ' ') || '—'}
                </div>
                <div className="text-xs text-gray-500 mt-1">Budget Status</div>
              </div>
            </div>

            {/* Currency conversion banner */}
            {budget.currency_conversion && (
              <div className="mb-6 p-3.5 bg-gray-50 border border-gray-200 rounded-xl flex flex-wrap items-center justify-between gap-2 text-xs">
                <div>
                  <span className="text-gray-500">Currency Conversion: </span>
                  <span className="font-semibold text-gray-800">
                    1 USD = {budget.currency_conversion.exchange_rate} {budget.currency_conversion.target_currency}
                  </span>
                  <span className="text-gray-500 ml-2">({budget.currency_conversion.rate_source})</span>
                </div>
                <span className={`badge ${budget.currency_conversion.is_live_rate ? 'badge-success' : 'badge-warning'}`}>
                  {budget.currency_conversion.is_live_rate ? '✓ Live Frankfurter Rate' : '⚠ Estimated Rate'}
                </span>
              </div>
            )}

            <BudgetChart breakdown={budget.expense_breakdown || {}} />

            {budget.cost_saving_tips?.length > 0 && (
              <div className="mt-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-3">Cost-Saving Tips</h3>
                <div className="grid sm:grid-cols-2 gap-2">
                  {budget.cost_saving_tips.slice(0, 4).map((tip, i) => (
                    <div key={i} className="p-3 border border-emerald-100 bg-emerald-50 rounded-xl text-xs text-emerald-800">
                      <span className="font-medium">{tip.category}: </span>
                      {tip.tip}
                      {tip.potential_savings && (
                        <span className="ml-1 text-emerald-600 font-medium">({tip.potential_savings})</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Section>
        )}

        {/* Weather */}
        {weather.daily_forecast?.length > 0 && !weather.error && (
          <Section id="weather" title="Weather Forecast" icon={Cloud} iconColor="text-sky-600">
            <div className="mb-4 p-4 bg-sky-50 rounded-xl text-sm text-sky-800">
              {weather.weather_summary}
            </div>

            <WeatherChart dailyForecast={weather.daily_forecast} />

            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-gray-400 border-b border-gray-100">
                    <th className="text-left py-2 font-medium">Date</th>
                    <th className="text-left py-2 font-medium">Condition</th>
                    <th className="text-center py-2 font-medium">Max °C</th>
                    <th className="text-center py-2 font-medium">Min °C</th>
                    <th className="text-center py-2 font-medium">Rain mm</th>
                    <th className="text-center py-2 font-medium">Outdoor?</th>
                  </tr>
                </thead>
                <tbody>
                  {weather.daily_forecast.slice(0, 7).map((d, i) => (
                    <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                      <td className="py-2 text-gray-600">{d.date}</td>
                      <td className="py-2 text-gray-700">{d.condition}</td>
                      <td className="py-2 text-center text-orange-600 font-medium">{d.temp_max_c?.toFixed(1)}</td>
                      <td className="py-2 text-center text-blue-600 font-medium">{d.temp_min_c?.toFixed(1)}</td>
                      <td className="py-2 text-center text-gray-500">{d.precipitation_mm?.toFixed(1)}</td>
                      <td className="py-2 text-center">
                        {d.is_good_outdoor
                          ? <ThumbsUp className="w-3.5 h-3.5 text-emerald-500 mx-auto" />
                          : <ThumbsDown className="w-3.5 h-3.5 text-gray-300 mx-auto" />
                        }
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {weather.packing_recommendations?.length > 0 && (
              <div className="mt-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Packing Recommendations</h3>
                <div className="flex flex-wrap gap-2">
                  {weather.packing_recommendations.map((item, i) => (
                    <span key={i} className="badge badge-neutral">{item}</span>
                  ))}
                </div>
              </div>
            )}
          </Section>
        )}

        {/* Local Discovery */}
        {!local.error && (local.featured_restaurants?.length > 0 || local.general_dining_suggestions?.length > 0 || local.neighborhood_guides?.length > 0 || local.api_status_message) && (
          <Section id="local" title="Restaurants & Local Gems" icon={UtensilsCrossed} iconColor="text-orange-600">
            {/* Status & Provenance Message */}
            {local.api_status_message && (
              <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 flex items-start gap-3">
                <Info className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
                <div>
                  <div className="font-semibold text-amber-800 mb-0.5">Zero Fabricated Establishments Notice</div>
                  <div className="leading-relaxed">{local.api_status_message}</div>
                </div>
              </div>
            )}

            {/* Verified OpenStreetMap Restaurants */}
            {local.featured_restaurants?.length > 0 && (
              <div className="mb-6">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-gray-700">Verified Local Restaurants</h3>
                  <span className="badge badge-success text-[11px]">✓ OpenStreetMap Verified</span>
                </div>
                <div className="grid sm:grid-cols-2 gap-3">
                  {local.featured_restaurants.slice(0, 6).map((r, i) => (
                    <div key={i} className="p-4 border border-gray-100 rounded-xl hover:border-brand-200 transition-colors">
                      <div className="flex items-start justify-between gap-2 mb-1.5">
                        <div className="text-sm font-semibold text-gray-900">{r.name}</div>
                        <span className="badge badge-neutral">{r.price_range || '$$'}</span>
                      </div>
                      <div className="text-xs text-brand-600 font-medium mb-1">{r.cuisine || 'Local Cuisine'}</div>
                      <p className="text-xs text-gray-500 leading-relaxed">{r.description || r.recommendation_reason}</p>
                      {r.opening_hours && (
                        <div className="text-xs text-gray-400 mt-1.5">🕐 {r.opening_hours}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* General Regional Dining Suggestions */}
            {local.general_dining_suggestions?.length > 0 && (
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-3">Regional Culinary & Dining Guide</h3>
                <div className="space-y-2">
                  {local.general_dining_suggestions.map((sug, i) => (
                    <div key={i} className="p-3 bg-orange-50 border border-orange-100 rounded-xl text-xs text-orange-900 flex items-start gap-2.5">
                      <UtensilsCrossed className="w-3.5 h-3.5 text-orange-600 mt-0.5 flex-shrink-0" />
                      <span className="leading-relaxed">{sug}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Verified Attractions */}
            {local.top_attractions?.length > 0 && (
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-3">Local Points of Interest</h3>
                <div className="grid sm:grid-cols-2 gap-3">
                  {local.top_attractions.slice(0, 4).map((a, i) => (
                    <div key={i} className="p-4 border border-gray-100 rounded-xl">
                      <div className="flex items-start justify-between gap-2 mb-1.5">
                        <div className="text-sm font-semibold text-gray-900">{a.name}</div>
                        <span className="badge badge-neutral capitalize">{a.type}</span>
                      </div>
                      <p className="text-xs text-gray-500 leading-relaxed">{a.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Neighborhood Guides */}
            {local.neighborhood_guides?.length > 0 && (
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-3">Neighborhood Guides</h3>
                <div className="grid sm:grid-cols-2 gap-3">
                  {local.neighborhood_guides.slice(0, 4).map((n, i) => (
                    <div key={i} className="p-4 bg-gray-50 rounded-xl border border-gray-100">
                      <div className="text-sm font-semibold text-gray-900 mb-1">{n.name}</div>
                      <p className="text-xs text-gray-600 mb-2">{n.vibe}</p>
                      {n.top_spots?.length > 0 && (
                        <div className="flex flex-wrap gap-1.5">
                          {n.top_spots.map((spot, sIdx) => (
                            <span key={sIdx} className="badge bg-white text-gray-700 text-[10px] border border-gray-200">
                              {spot}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {local.hidden_gems?.length > 0 && (
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-3">Hidden Gems</h3>
                <div className="grid sm:grid-cols-2 gap-3">
                  {local.hidden_gems.slice(0, 4).map((gem, i) => (
                    <div key={i} className="p-3 bg-orange-50 border border-orange-100 rounded-xl">
                      <div className="text-sm font-semibold text-orange-900 mb-1">{gem.name}</div>
                      <p className="text-xs text-orange-700">{gem.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {local.local_tips?.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Local Tips</h3>
                <div className="space-y-1.5">
                  {local.local_tips.map((tip, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs text-gray-600">
                      <span className="text-brand-500 mt-0.5">•</span>
                      {tip}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Section>
        )}

        {/* Interactive Map */}
        <Section id="map" title="Interactive Map" icon={MapPin} iconColor="text-red-500">
          <p className="text-xs text-gray-400 mb-4">
            Data from OpenStreetMap · Orange = Food · Indigo = Attractions · Green = Leisure
          </p>
          <TripMap
            coordinates={mapCoords}
            pois={rawPois}
            restaurants={restaurants}
            attractions={attractions}
          />
        </Section>

        {/* Travel Recommendations */}
        {coordinator.travel_readiness_checklist?.length > 0 && (
          <Section id="recommendations" title="Travel Recommendations" icon={Compass}>
            <div className="grid sm:grid-cols-2 gap-3">
              {coordinator.travel_readiness_checklist.map((item, i) => (
                <div key={i} className="flex items-start gap-3 p-3 border border-gray-100 rounded-xl">
                  <span className={`badge mt-0.5 ${
                    item.priority === 'essential' ? 'badge-error' :
                    item.priority === 'recommended' ? 'badge-info' : 'badge-neutral'
                  }`}>
                    {item.priority}
                  </span>
                  <div>
                    <div className="text-sm font-medium text-gray-800">{item.item}</div>
                    <div className="text-xs text-gray-400 capitalize">{item.category}</div>
                  </div>
                </div>
              ))}
            </div>

            {coordinator.final_tips?.length > 0 && (
              <div className="mt-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-3">Final Tips</h3>
                <div className="space-y-2">
                  {coordinator.final_tips.map((tip, i) => (
                    <div key={i} className="flex items-start gap-2 text-sm text-gray-600 p-3 bg-gray-50 rounded-lg">
                      <span className="text-brand-500">💡</span>
                      {tip}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Section>
        )}

        {/* Data quality notice */}
        {coordinator.data_quality && (
          <div className="card p-4 flex items-start gap-3">
            <Info className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
            <div className="text-xs text-gray-500">
              <span className="font-medium">{coordinator.data_quality.agents_failed === 0 ? 6 : (coordinator.data_quality.agents_successful || 6)} of 6 agents</span> completed successfully.
              Confidence level: <span className="font-medium">{coordinator.data_quality.confidence_level}</span>.
              {coordinator.data_quality.missing_data?.length > 0 && (
                <span> Missing: {coordinator.data_quality.missing_data.join(', ')}.</span>
              )}
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
