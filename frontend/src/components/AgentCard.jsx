import {
  MapPin, Cloud, Search, DollarSign, Calendar, Compass,
  CheckCircle, XCircle, Clock, Loader
} from 'lucide-react'

const ICONS = {
  MapPin, Cloud, Search, DollarSign, Calendar, Compass,
}

const STATUS_CONFIG = {
  waiting: {
    color: 'text-gray-400',
    bg: 'bg-gray-50',
    border: 'border-gray-100',
    badge: 'badge-neutral',
    label: 'Waiting',
    Icon: Clock,
  },
  running: {
    color: 'text-brand-600',
    bg: 'bg-brand-50',
    border: 'border-brand-200',
    badge: 'badge-info',
    label: 'Running',
    Icon: Loader,
  },
  completed: {
    color: 'text-emerald-600',
    bg: 'bg-emerald-50',
    border: 'border-emerald-200',
    badge: 'badge-success',
    label: 'Completed',
    Icon: CheckCircle,
  },
  failed: {
    color: 'text-red-500',
    bg: 'bg-red-50',
    border: 'border-red-200',
    badge: 'badge-error',
    label: 'Failed',
    Icon: XCircle,
  },
}

export default function AgentCard({ agent }) {
  const status = STATUS_CONFIG[agent.status] || STATUS_CONFIG.waiting
  const AgentIcon = ICONS[agent.icon] || Compass
  const StatusIcon = status.Icon

  return (
    <div className={`card p-5 border transition-all duration-300 ${status.border}`}>
      <div className="flex items-start gap-4">
        {/* Agent Icon */}
        <div className={`w-10 h-10 rounded-xl ${status.bg} flex items-center justify-center flex-shrink-0`}>
          <AgentIcon className={`w-5 h-5 ${status.color}`} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2 mb-1">
            <h3 className="text-sm font-semibold text-gray-900 truncate">
              {agent.display_name}
            </h3>
            <span className={status.badge}>
              <StatusIcon
                className={`w-3 h-3 ${agent.status === 'running' ? 'spinner' : ''}`}
              />
              {status.label}
            </span>
          </div>

          <p className="text-xs text-gray-500 mb-3 leading-relaxed">
            {agent.message || agent.description}
          </p>

          {/* Progress bar */}
          <div className="h-1 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-700 ${
                agent.status === 'completed' ? 'w-full bg-emerald-500' :
                agent.status === 'failed' ? 'w-full bg-red-400' :
                agent.status === 'running' ? 'w-2/3 bg-brand-500 animate-pulse' :
                'w-0 bg-gray-300'
              }`}
            />
          </div>

          {/* Timestamps */}
          {(agent.started_at || agent.completed_at) && (
            <div className="mt-2 flex gap-3 text-xs text-gray-400">
              {agent.started_at && (
                <span>Started {new Date(agent.started_at + 'Z').toLocaleTimeString()}</span>
              )}
              {agent.completed_at && (
                <span>· Done {new Date(agent.completed_at + 'Z').toLocaleTimeString()}</span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
