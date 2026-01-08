/**
 * Main Application Component
 */
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { theme } from './styles/theme';

// Pages (to be created)
import Login from './features/auth/Login';
import Register from './features/auth/Register';
import Dashboard from './features/dashboard/Dashboard';
import PropertyList from './features/properties/PropertyList';
import PropertyDetail from './features/properties/PropertyDetail';
import PropertyAnalysis from './features/properties/PropertyAnalysis';
import PropertyScrape from './features/properties/PropertyScrape';
import Layout from './components/layout/Layout';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

// Commented out for now - authentication disabled
// function ProtectedRoute({ children }: { children: React.ReactNode }) {
//   const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
//   return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
// }

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Router>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            {/* Public routes - authentication disabled for now */}
            <Route path="/" element={<Layout />}>
              <Route index element={<Dashboard />} />
              <Route path="properties" element={<PropertyList />} />
              <Route path="properties/analysis" element={<PropertyAnalysis />} />
              <Route path="properties/:id" element={<PropertyDetail />} />
              <Route path="properties/scrape" element={<PropertyScrape />} />
            </Route>
          </Routes>
        </Router>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
