import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Compass, CheckCircle, XCircle, ArrowRight, RefreshCw, AlertTriangle } from 'lucide-react'
import AgentCard from '../components/AgentCard'
import { agentApi, tripApi } from '../services/api'

const AGENT_ORDER = [
  'destination_research',
  'weather_intelligence',
  'local_discovery',
  'budget_management',
  'itinerary_planning',
  'travel_coordinator',
]

export default function AgentDashboardPage() {
  const { tripId } = useParams()
  const navigate = useNavigate()
  const [agents, setAgents] = useState([])
  const [tripStatus, setTripStatus] = useState('pending')
  const [error, setError] = useState('')
  const eventSourceRef = useRef(null)
  const pollingRef = useRef(null)

  useEffect(() => {
    if (!tripId) return

    // Use SSE for live updates with polling fallback
    startPolling()

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current)
      if (eventSourceRef.current) eventSourceRef.current.close()
    }
  }, [tripId])

  const startPolling = () => {
    // Poll every 2 seconds for agent statuses
    const poll = async () => {
      try {
        const data = await agentApi.getStatus(tripId)
        setAgents(data.agents || [])
        setTripStatus(data.trip_status)

        if (data.trip_status === 'completed') {
          clearInterval(pollingRef.current)
          // Keep completed agent transparency dashboard visible until user clicks 'View My Travel Plan'
        }
        if (data.trip_status === 'failed') {
          clearInterval(pollingRef.current)
        }
      } catch (err) {
        setError('Failed to connect to backend. Is the server running?')
        clearInterval(pollingRef.current)
      }
    }

    poll() // Immediate first call
    pollingRef.current = setInterval(poll, 2000)
  }

  const completedCount = agents.filter(a => a.status === 'completed').length
  const failedCount = agents.filter(a => a.status === 'failed').length
  const totalCount = agents.length || 6

  // Sort agents in fixed order
  const sortedAgents = [...agents].sort((a, b) => {
    return AGENT_ORDER.indexOf(a.agent_name) - AGENT_ORDER.indexOf(b.agent_name)
  })

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="max-w-4xl mx-auto px-4 sm:px-6">
        {/* Header */}
        <div className="text-center mb-10">
          <div className="w-14 h-14 bg-brand-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Compass className={`w-7 h-7 text-brand-600 ${tripStatus === 'running' || tripStatus === 'pending' ? 'spinner' : ''}`} />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            {tripStatus === 'completed'
              ? '✓ Your travel plan is ready!'
              : tripStatus === 'failed'
              ? 'Some agents encountered issues'
              : 'AI Agents at Work…'}
          </h1>
          <p className="text-gray-500 text-sm">
            {tripStatus === 'completed'
              ? "Review each agent's execution, data sources, and provenance below, then explore your comprehensive itinerary."
              : tripStatus === 'failed'
              ? 'Your plan was partially generated.'
              : 'Sit tight while your specialized travel team prepares your plan.'}
          </p>
        </div>

        {/* Progress bar */}
        <div className="mb-8">
          <div className="flex justify-between text-xs text-gray-500 mb-2">
            <span>{completedCount} of {totalCount} agents completed</span>
            {failedCount > 0 && (
              <span className="text-red-500">{failedCount} failed</span>
            )}
          </div>
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-700 ${
                tripStatus === 'failed' && completedCount === 0 ? 'bg-red-400' : 'bg-brand-500'
              }`}
              style={{ width: `${(completedCount / totalCount) * 100}%` }}
            />
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 flex items-start gap-3 p-4 bg-amber-50 border border-amber-100 rounded-xl text-sm text-amber-800">
            <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
            <div>
              <div className="font-medium mb-1">Connection Error</div>
              {error}
            </div>
          </div>
        )}

        {/* Agent Cards */}
        <div className="grid sm:grid-cols-2 gap-4 mb-8">
          {sortedAgents.length === 0
            ? AGENT_ORDER.map(name => (
                <div key={name} className="card p-5 animate-pulse">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gray-100 rounded-xl" />
                    <div className="flex-1">
                      <div className="h-3 bg-gray-100 rounded w-2/3 mb-2" />
                      <div className="h-2.5 bg-gray-100 rounded w-1/2" />
                    </div>
                  </div>
                </div>
              ))
            : sortedAgents.map(agent => (
                <AgentCard key={agent.agent_name} agent={agent} />
              ))
          }
        </div>

        {/* Actions */}
        {tripStatus === 'completed' && (
          <div className="text-center">
            <button
              onClick={() => navigate(`/results/${tripId}`)}
              className="btn-primary flex items-center gap-2 mx-auto"
            >
              View My Travel Plan <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {tripStatus === 'failed' && (
          <div className="text-center space-y-3">
            <p className="text-sm text-gray-500">Some data may be missing, but a partial plan might still be available.</p>
            <div className="flex justify-center gap-3">
              <button
                onClick={() => navigate(`/results/${tripId}`)}
                className="btn-primary flex items-center gap-2"
              >
                View Partial Plan <ArrowRight className="w-4 h-4" />
              </button>
              <button
                onClick={() => navigate('/plan')}
                className="btn-secondary flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" /> Try Again
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
