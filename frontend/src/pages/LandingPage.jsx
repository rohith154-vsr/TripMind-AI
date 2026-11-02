import { Link } from 'react-router-dom'
import {
  Compass, ArrowRight, MapPin, Cloud, Search,
  DollarSign, Calendar, Zap, Star, Shield, Globe
} from 'lucide-react'

const AGENTS = [
  {
    icon: MapPin,
    name: 'Destination Research',
    color: 'bg-indigo-50 text-indigo-600',
    desc: 'Identifies top attractions, activities, and places tailored to your travel style.',
  },
  {
    icon: Calendar,
    name: 'Itinerary Planning',
    color: 'bg-violet-50 text-violet-600',
    desc: 'Builds a day-by-day schedule clustering nearby locations to minimize travel time.',
  },
  {
    icon: DollarSign,
    name: 'Budget Management',
    color: 'bg-emerald-50 text-emerald-600',
    desc: 'Breaks down accommodation, food, transport and activities against your budget.',
  },
  {
    icon: Cloud,
    name: 'Weather Intelligence',
    color: 'bg-sky-50 text-sky-600',
    desc: 'Fetches real forecasts via Open-Meteo and adjusts activities for the conditions.',
  },
  {
    icon: Search,
    name: 'Local Discovery',
    color: 'bg-orange-50 text-orange-600',
    desc: "Finds restaurants and hidden gems using OpenStreetMap's live POI database.",
  },
  {
    icon: Compass,
    name: 'Travel Coordinator',
    color: 'bg-rose-50 text-rose-600',
    desc: 'Orchestrates all agents, resolves conflicts, and synthesizes a final plan.',
  },
]

const FEATURES = [
  { icon: Zap, title: 'Real-time Agent Execution', desc: 'Watch six AI agents work in parallel with live status updates.' },
  { icon: Globe, title: 'Live Data Integrations', desc: 'Weather from Open-Meteo, POIs from OpenStreetMap, rates from Frankfurter.' },
  { icon: Star, title: 'Personalized Itineraries', desc: 'Day-by-day plans crafted around your style, interests and budget.' },
  { icon: Shield, title: 'Transparent AI', desc: 'Agents clearly mark uncertain data — no hallucinated facts.' },
]

const HOW_IT_WORKS = [
  { step: '01', title: 'Enter Your Trip Details', desc: 'Fill in origin, destination, dates, budget and preferences.' },
  { step: '02', title: 'Agents Get to Work', desc: 'Six specialized AI agents run concurrently to research every aspect.' },
  { step: '03', title: 'Get Your Plan', desc: 'Receive a comprehensive itinerary, budget breakdown, and interactive map.' },
]

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      {/* Hero */}
      <section className="relative overflow-hidden bg-white pt-16 pb-24">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_#f0f4ff_0%,_transparent_60%)] pointer-events-none" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-brand-50 border border-brand-100 rounded-full text-xs font-medium text-brand-700 mb-6">
            <Zap className="w-3.5 h-3.5" />
            Multi-Agent AI Travel Planning
          </div>
          <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold text-gray-900 text-balance mb-6 leading-tight">
            Your Next Adventure,
            <br />
            <span className="text-brand-600">Planned by AI.</span>
          </h1>
          <p className="text-lg text-gray-500 max-w-2xl mx-auto mb-10 text-balance">
            TripMind AI deploys six specialized agents that research destinations, check real weather, 
            find local gems, manage your budget, and build a day-by-day itinerary — all in one click.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link to="/plan" className="btn-primary flex items-center justify-center gap-2 text-base">
              Plan My Trip <ArrowRight className="w-4 h-4" />
            </Link>
            <Link to="/saved" className="btn-secondary flex items-center justify-center gap-2 text-base">
              View Saved Trips
            </Link>
          </div>

          {/* Trust badge */}
          <div className="mt-12 flex flex-wrap justify-center gap-6 text-xs text-gray-400">
            {['Open-Meteo Weather API', 'OpenStreetMap POIs', 'Frankfurter Currency API', 'Powered by Gemini AI'].map(item => (
              <span key={item} className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full" />
                {item}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-14">
            <h2 className="section-title">How It Works</h2>
            <p className="section-subtitle mt-2">From form to full itinerary in minutes</p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {HOW_IT_WORKS.map(({ step, title, desc }) => (
              <div key={step} className="relative">
                <div className="text-6xl font-black text-gray-100 mb-3 select-none">{step}</div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Agents */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-14">
            <h2 className="section-title">Meet Your AI Travel Team</h2>
            <p className="section-subtitle mt-2">Six specialized agents, one cohesive plan</p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {AGENTS.map(({ icon: Icon, name, color, desc }) => (
              <div key={name} className="card-hover p-6">
                <div className={`w-10 h-10 rounded-xl ${color} flex items-center justify-center mb-4`}>
                  <Icon className="w-5 h-5" />
                </div>
                <h3 className="text-sm font-semibold text-gray-900 mb-2">{name} Agent</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-14">
            <h2 className="section-title">Why TripMind AI?</h2>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {FEATURES.map(({ icon: Icon, title, desc }) => (
              <div key={title} className="text-center">
                <div className="w-12 h-12 bg-brand-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <Icon className="w-6 h-6 text-brand-600" />
                </div>
                <h3 className="text-sm font-semibold text-gray-900 mb-2">{title}</h3>
                <p className="text-xs text-gray-500 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 bg-brand-600">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
            Ready to plan your dream trip?
          </h2>
          <p className="text-brand-200 mb-8">
            Let six AI agents do the research while you focus on getting excited.
          </p>
          <Link
            to="/plan"
            className="inline-flex items-center gap-2 bg-white text-brand-700 px-8 py-3.5 rounded-xl font-semibold hover:bg-brand-50 transition-all duration-200 shadow-sm"
          >
            Start Planning <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-100 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-sm text-gray-400">
          TripMind AI — Portfolio Project · Built with React, FastAPI, and Gemini AI
        </div>
      </footer>
    </div>
  )
}
