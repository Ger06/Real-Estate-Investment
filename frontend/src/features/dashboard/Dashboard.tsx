/**
 * Dashboard Page
 */
import { Box, Grid, Card, CardContent, Typography, Paper, CircularProgress } from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  Home as HomeIcon,
  AttachMoney as MoneyIcon,
} from '@mui/icons-material';
import { useProperties } from '../../hooks/useProperties';

export default function Dashboard() {
  // Usar el mismo hook que PropertyList - comparte caché automáticamente
  const { data, isLoading } = useProperties(0, 50);
  const totalProperties = data?.total || 0;

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>

      <Grid container spacing={3}>
        {/* Stats Cards */}
        <Grid item xs={12} sm={6} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <HomeIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Propiedades</Typography>
              </Box>
              <Typography variant="h3">
                {isLoading ? <CircularProgress size={32} /> : totalProperties}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Total registradas
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <TrendingUpIcon color="success" sx={{ mr: 1 }} />
                <Typography variant="h6">Análisis</Typography>
              </Box>
              <Typography variant="h3">0</Typography>
              <Typography variant="body2" color="text.secondary">
                Análisis realizados
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <MoneyIcon color="warning" sx={{ mr: 1 }} />
                <Typography variant="h6">Inversiones</Typography>
              </Box>
              <Typography variant="h3">$0</Typography>
              <Typography variant="body2" color="text.secondary">
                Total invertido
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Activity */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Actividad Reciente
            </Typography>
            <Typography variant="body2" color="text.secondary">
              No hay actividad reciente para mostrar
            </Typography>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
