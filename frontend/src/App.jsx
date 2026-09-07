import { Suspense, lazy } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { ThemeProvider } from './context/ThemeContext'
import { AuthProvider } from './context/AuthContext'
import { ToastProvider } from './context/ToastContext'
import ProtectedRoute from './components/auth/ProtectedRoute'
import AppShell from './components/shell/AppShell'
import LoginPage from './pages/LoginPage'

// Route-level code splitting: each dashboard page pulls in its own charts
// (recharts), its own set of components, and — for Energy specifically —
// a heavier forecast-comparison chart. Before this, ALL SIX dashboards
// shipped in one 945KB bundle loaded on first visit even if the person
// only ever opens Energy; now each page's JS downloads only when its
// route is actually visited, which is what was behind vite's own
// "chunk larger than 500kB" build warning.
const EnergyDashboardPage = lazy(() => import('./pages/energy/EnergyDashboardPage'))
const MaintenanceDashboardPage = lazy(() => import('./pages/maintenance/MaintenanceDashboardPage'))
const OccupancyDashboardPage = lazy(() => import('./pages/occupancy/OccupancyDashboardPage'))
const SecurityDashboardPage = lazy(() => import('./pages/security/SecurityDashboardPage'))
const CostDashboardPage = lazy(() => import('./pages/cost/CostDashboardPage'))
const ExecutiveDashboardPage = lazy(() => import('./pages/executive/ExecutiveDashboardPage'))

function RouteLoadingFallback() {
  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <Loader2 size={20} className="animate-spin text-teal-400" />
    </div>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AuthProvider>
          <ToastProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/*"
              element={
                <ProtectedRoute>
                  <AppShell>
                    <Suspense fallback={<RouteLoadingFallback />}>
                      <Routes>
                        <Route path="/" element={<Navigate to="/executive" replace />} />
                        <Route path="/executive" element={<ExecutiveDashboardPage />} />
                        <Route path="/energy" element={<EnergyDashboardPage />} />
                        <Route path="/maintenance" element={<MaintenanceDashboardPage />} />
                        <Route path="/occupancy" element={<OccupancyDashboardPage />} />
                        <Route path="/security" element={<SecurityDashboardPage />} />
                        <Route path="/cost" element={<CostDashboardPage />} />
                      </Routes>
                    </Suspense>
                  </AppShell>
                </ProtectedRoute>
              }
            />
          </Routes>
          </ToastProvider>
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  )
}
