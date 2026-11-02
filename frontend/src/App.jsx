import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import LandingPage from './pages/LandingPage'
import TripPlannerPage from './pages/TripPlannerPage'
import AgentDashboardPage from './pages/AgentDashboardPage'
import ResultsDashboardPage from './pages/ResultsDashboardPage'
import SavedTripsPage from './pages/SavedTripsPage'

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <main>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/plan" element={<TripPlannerPage />} />
            <Route path="/agents/:tripId" element={<AgentDashboardPage />} />
            <Route path="/results/:tripId" element={<ResultsDashboardPage />} />
            <Route path="/saved" element={<SavedTripsPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
