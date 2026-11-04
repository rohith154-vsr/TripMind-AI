import {
  MapPin, Cloud, Search, DollarSign, Calendar, Compass,
  CheckCircle, XCircle, Clock, Loader, AlertTriangle, Cpu, Globe, Database
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

function getSourceBadge(sourceType, isFallback) {
  if (isFallback || sourceType === 'fallback') {
    return {
      label: 'Estimated / Fallback',
      bg: 'bg-amber-50 text-amber-700 border-amber-200',
      icon: Database,
    }
  }
  if (sourceType === 'live_api') {
    return {
      label: 'Live External API',
      bg: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      icon: Globe,
    }
  }
  if (sourceType === 'hybrid') {
    return {
      label: 'Hybrid (API + LLM)',
      bg: 'bg-purple-50 text-purple-700 border-purple-200',
      icon: Cpu,
    }
  }
  return {
    label: 'AI Reasoning (LLM)',
    bg: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    icon: Cpu,
  }
}

export default function AgentCard({ agent }) {
  const status = STATUS_CONFIG[agent.status] || STATUS_CONFIG.waiting
  const AgentIcon = ICONS[agent.icon] || Compass
  const StatusIcon = status.Icon
  const sourceInfo = getSourceBadge(agent.source_type, agent.is_fallback)
  const SourceIcon = sourceInfo.icon

  return (
    <div className={`card p-5 border transition-all duration-300 ${status.border}`}>
      <div className="flex items-start gap-4">
        {/* Agent Icon */}
        <div className={`w-11 h-11 rounded-xl ${status.bg} flex items-center justify-center flex-shrink-0`}>
          <AgentIcon className={`w-5 h-5 ${status.color}`} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
            <h3 className="text-sm font-semibold text-gray-900 truncate">
              {agent.display_name}
            </h3>
            <div className="flex items-center gap-1.5">
              {agent.status === 'completed' && (
                <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-medium rounded-full border ${sourceInfo.bg}`}>
                  <SourceIcon className="w-3 h-3" />
                  {sourceInfo.label}
                </span>
              )}
              <span className={status.badge}>
                <StatusIcon
                  className={`w-3 h-3 ${agent.status === 'running' ? 'spinner' : ''}`}
                />
                {status.label}
              </span>
            </div>
          </div>

          {/* Responsibility */}
          {agent.responsibility && (
            <p className="text-xs font-medium text-gray-600 mb-1 leading-relaxed">
              Responsibility: <span className="text-gray-500 font-normal">{agent.responsibility}</span>
            </p>
          )}

          {/* Live Message */}
          <p className="text-xs text-gray-400 mb-3 leading-relaxed">
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

          {/* Transparency Metadata & Sources */}
          {agent.data_sources && agent.data_sources.length > 0 && agent.status === 'completed' && (
            <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
              <span className="text-[11px] text-gray-400 font-medium mr-1">Data sources:</span>
              {agent.data_sources.map((src, idx) => (
                <span key={idx} className="inline-flex items-center px-2 py-0.5 rounded text-[10px] bg-gray-100 text-gray-700">
                  {src}
                </span>
              ))}
            </div>
          )}

          {/* Errors, if any */}
          {agent.errors && agent.errors.length > 0 && (
            <div className="mt-2.5 p-2 bg-red-50 border border-red-100 rounded-lg text-xs text-red-700 flex items-start gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 text-red-500" />
              <div>
                <span className="font-semibold">Notice: </span>
                {agent.errors.join('; ')}
              </div>
            </div>
          )}

          {/* Timestamps & Execution Duration */}
          <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2 text-xs text-gray-400">
            <div className="flex gap-2">
              {agent.started_at && (
                <span>Started {new Date(agent.started_at.endsWith('Z') ? agent.started_at : agent.started_at + 'Z').toLocaleTimeString()}</span>
              )}
              {agent.completed_at && (
                <span>· Done {new Date(agent.completed_at.endsWith('Z') ? agent.completed_at : agent.completed_at + 'Z').toLocaleTimeString()}</span>
              )}
            </div>
            {agent.duration_seconds != null && (
              <span className="font-medium text-gray-600 bg-gray-50 px-2 py-0.5 rounded border border-gray-100">
                ⏱ {agent.duration_seconds}s
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
