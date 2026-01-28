import { useState } from 'react';
import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  CardMedia,
  CardActions,
  Chip,
  CircularProgress,
  Alert,
  Tabs,
  Tab,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Breadcrumbs,
  Link,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
} from '@mui/material';
import {
  Download as ScrapeIcon,
  SkipNext as SkipIcon,
  Delete as DeleteIcon,
  Visibility as ViewIcon,
  CleaningServices as ClearIcon,
  NavigateNext as BreadcrumbSep,
} from '@mui/icons-material';
import {
  useSavedSearch,
  usePendingProperties,
  useScrapeBatch,
  useScrapeSingle,
  useSkipPending,
  useDeletePending,
  useClearErrors,
} from '../../hooks/useSavedSearches';

const STATUS_TABS = [
  { value: '', label: 'Todos' },
  { value: 'PENDING', label: 'Pendientes' },
  { value: 'SCRAPED', label: 'Scrapeadas' },
  { value: 'SKIPPED', label: 'Omitidas' },
  { value: 'ERROR', label: 'Errores' },
];

const PORTAL_OPTIONS = [
  { value: '', label: 'Todos los portales' },
  { value: 'argenprop', label: 'Argenprop' },
  { value: 'zonaprop', label: 'Zonaprop' },
  { value: 'remax', label: 'Remax' },
  { value: 'mercadolibre', label: 'MercadoLibre' },
];

const PORTAL_COLORS: Record<string, 'success' | 'warning' | 'error' | 'default'> = {
  argenprop: 'success',
  zonaprop: 'warning',
  remax: 'error',
  mercadolibre: 'default',
};

const STATUS_COLORS: Record<string, 'default' | 'info' | 'success' | 'warning' | 'error'> = {
  PENDING: 'info',
  SCRAPED: 'success',
  SKIPPED: 'warning',
  ERROR: 'error',
  DUPLICATE: 'default',
};

const STATUS_LABELS: Record<string, string> = {
  PENDING: 'Pendiente',
  SCRAPED: 'Scrapeada',
  SKIPPED: 'Omitida',
  ERROR: 'Error',
  DUPLICATE: 'Duplicada',
};

export default function PendingProperties() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [statusFilter, setStatusFilter] = useState('');
  const [portalFilter, setPortalFilter] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [actionError, setActionError] = useState('');

  const { data: search, isLoading: searchLoading } = useSavedSearch(id || '');
  const { data: pendingData, isLoading: pendingLoading } = usePendingProperties(
    0,
    100,
    id,
    statusFilter || undefined,
    portalFilter || undefined
  );

  const scrapeBatchMutation = useScrapeBatch();
  const scrapeSingleMutation = useScrapeSingle();
  const skipMutation = useSkipPending();
  const deleteMutation = useDeletePending();
  const clearErrorsMutation = useClearErrors();

  const pending = pendingData?.items || [];
  const total = pendingData?.total || 0;

  // Count stats from current data
  const allItems = pendingData?.items || [];
  const stats = {
    pending: allItems.filter((p) => p.status === 'PENDING').length,
    scraped: allItems.filter((p) => p.status === 'SCRAPED').length,
    skipped: allItems.filter((p) => p.status === 'SKIPPED').length,
    errors: allItems.filter((p) => p.status === 'ERROR').length,
  };

  const handleScrapeBatch = async () => {
    try {
      setActionError('');
      await scrapeBatchMutation.mutateAsync({ search_id: id, limit: 10 });
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Error al scrapear lote');
    }
  };

  const handleScrapeSingle = async (pendingId: string) => {
    try {
      setActionError('');
      await scrapeSingleMutation.mutateAsync(pendingId);
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Error al scrapear propiedad');
    }
  };

  const handleSkip = async (pendingId: string) => {
    try {
      setActionError('');
      await skipMutation.mutateAsync(pendingId);
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Error al omitir propiedad');
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    try {
      setActionError('');
      await deleteMutation.mutateAsync(deleteConfirm);
      setDeleteConfirm(null);
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Error al eliminar');
      setDeleteConfirm(null);
    }
  };

  const handleClearErrors = async () => {
    try {
      setActionError('');
      await clearErrorsMutation.mutateAsync(id);
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Error al limpiar errores');
    }
  };

  const isLoading = searchLoading || pendingLoading;

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      {/* Breadcrumb */}
      <Breadcrumbs separator={<BreadcrumbSep fontSize="small" />} sx={{ mb: 2 }}>
        <Link component={RouterLink} to="/saved-searches" underline="hover" color="inherit">
          Búsquedas Guardadas
        </Link>
        <Typography color="text.primary">{search?.name || 'Búsqueda'}</Typography>
      </Breadcrumbs>

      {/* Header */}
      <Typography variant="h4" fontWeight={600} gutterBottom>
        Propiedades Pendientes
      </Typography>

      {/* Alerts */}
      {actionError && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setActionError('')}>
          {actionError}
        </Alert>
      )}

      {/* Stats cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {[
          { label: 'Pendientes', value: stats.pending, color: '#1976d2' },
          { label: 'Scrapeadas', value: stats.scraped, color: '#2e7d32' },
          { label: 'Omitidas', value: stats.skipped, color: '#ed6c02' },
          { label: 'Errores', value: stats.errors, color: '#d32f2f' },
        ].map((stat) => (
          <Grid item xs={6} sm={3} key={stat.label}>
            <Card>
              <CardContent sx={{ textAlign: 'center', py: 1.5 }}>
                <Typography variant="h4" fontWeight={700} sx={{ color: stat.color }}>
                  {stat.value}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {stat.label}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Actions */}
      <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
        <Button
          variant="contained"
          startIcon={scrapeBatchMutation.isPending ? <CircularProgress size={18} color="inherit" /> : <ScrapeIcon />}
          onClick={handleScrapeBatch}
          disabled={scrapeBatchMutation.isPending || stats.pending === 0}
        >
          Scrapear Lote
        </Button>
        <Button
          variant="outlined"
          startIcon={<ClearIcon />}
          onClick={handleClearErrors}
          disabled={clearErrorsMutation.isPending || stats.errors === 0}
        >
          Limpiar Errores
        </Button>
      </Box>

      {/* Filters */}
      <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mb: 2, flexWrap: 'wrap' }}>
        <Tabs
          value={statusFilter}
          onChange={(_, val) => setStatusFilter(val)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{ flexGrow: 1 }}
        >
          {STATUS_TABS.map((tab) => (
            <Tab key={tab.value} value={tab.value} label={tab.label} />
          ))}
        </Tabs>
        <FormControl size="small" sx={{ minWidth: 180 }}>
          <InputLabel>Portal</InputLabel>
          <Select
            value={portalFilter}
            onChange={(e) => setPortalFilter(e.target.value)}
            label="Portal"
          >
            {PORTAL_OPTIONS.map((opt) => (
              <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {/* Total count */}
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {total} resultado{total !== 1 ? 's' : ''}
      </Typography>

      {/* Properties grid */}
      {pending.length === 0 ? (
        <Box sx={{ textAlign: 'center', py: 6 }}>
          <Typography variant="body1" color="text.secondary">
            No hay propiedades {statusFilter ? `con estado "${STATUS_LABELS[statusFilter] || statusFilter}"` : 'pendientes'}.
          </Typography>
        </Box>
      ) : (
        <Grid container spacing={2}>
          {pending.map((item) => (
            <Grid item xs={12} sm={6} md={4} key={item.id}>
              <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                {item.thumbnail_url && (
                  <CardMedia
                    component="img"
                    height="160"
                    image={item.thumbnail_url}
                    alt={item.title || 'Propiedad'}
                    sx={{ objectFit: 'cover' }}
                  />
                )}
                <CardContent sx={{ flexGrow: 1 }}>
                  {/* Title */}
                  <Typography variant="subtitle1" fontWeight={600} noWrap gutterBottom>
                    {item.title || 'Sin título'}
                  </Typography>

                  {/* Price */}
                  {item.price && (
                    <Typography variant="body1" fontWeight={500} gutterBottom>
                      {item.currency || 'USD'} {item.price.toLocaleString('es-AR')}
                    </Typography>
                  )}

                  {/* Location */}
                  {item.location_preview && (
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      {item.location_preview}
                    </Typography>
                  )}

                  {/* Chips */}
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 1 }}>
                    <Chip
                      label={item.source}
                      size="small"
                      color={PORTAL_COLORS[item.source] || 'default'}
                      variant="outlined"
                    />
                    <Chip
                      label={STATUS_LABELS[item.status] || item.status}
                      size="small"
                      color={STATUS_COLORS[item.status] || 'default'}
                    />
                  </Box>

                  {/* Error message */}
                  {item.status === 'ERROR' && item.error_message && (
                    <Alert severity="error" sx={{ mt: 1, py: 0 }}>
                      <Typography variant="caption">{item.error_message}</Typography>
                    </Alert>
                  )}
                </CardContent>

                <CardActions sx={{ px: 2, pb: 1.5 }}>
                  {(item.status === 'PENDING' || item.status === 'ERROR') && (
                    <>
                      <Tooltip title="Scrapear">
                        <span>
                          <IconButton
                            color="primary"
                            onClick={() => handleScrapeSingle(item.id)}
                            disabled={scrapeSingleMutation.isPending}
                            size="small"
                          >
                            <ScrapeIcon />
                          </IconButton>
                        </span>
                      </Tooltip>
                      <Tooltip title="Omitir">
                        <IconButton
                          onClick={() => handleSkip(item.id)}
                          disabled={skipMutation.isPending}
                          size="small"
                        >
                          <SkipIcon />
                        </IconButton>
                      </Tooltip>
                    </>
                  )}
                  {item.status === 'SCRAPED' && item.property_id && (
                    <Button
                      size="small"
                      startIcon={<ViewIcon />}
                      onClick={() => navigate(`/properties/${item.property_id}`)}
                    >
                      Ver Propiedad
                    </Button>
                  )}
                  <Box sx={{ flexGrow: 1 }} />
                  <Tooltip title="Eliminar">
                    <IconButton
                      color="error"
                      onClick={() => setDeleteConfirm(item.id)}
                      size="small"
                    >
                      <DeleteIcon />
                    </IconButton>
                  </Tooltip>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteConfirm} onClose={() => setDeleteConfirm(null)}>
        <DialogTitle>Eliminar Propiedad Pendiente</DialogTitle>
        <DialogContent>
          <DialogContentText>
            ¿Estás seguro de eliminar esta propiedad pendiente? Esta acción no se puede deshacer.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirm(null)}>Cancelar</Button>
          <Button onClick={handleDelete} color="error" variant="contained">
            Eliminar
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
