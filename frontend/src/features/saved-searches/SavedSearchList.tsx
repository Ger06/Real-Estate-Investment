import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  CardActions,
  Chip,
  CircularProgress,
  Alert,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
} from '@mui/material';
import {
  Add as AddIcon,
  PlayArrow as PlayIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Visibility as ViewIcon,
  ToggleOn as ToggleOnIcon,
  ToggleOff as ToggleOffIcon,
} from '@mui/icons-material';
import {
  useSavedSearches,
  useCreateSearch,
  useUpdateSearch,
  useDeleteSearch,
  useExecuteSearch,
  useToggleSearch,
} from '../../hooks/useSavedSearches';
import type { SavedSearch, SavedSearchExecuteResponse } from '../../api/savedSearches';
import SavedSearchForm from './SavedSearchForm';

const PORTAL_COLORS: Record<string, 'success' | 'warning' | 'error' | 'default'> = {
  argenprop: 'success',
  zonaprop: 'warning',
  remax: 'error',
  mercadolibre: 'default',
};

const OPERATION_LABELS: Record<string, string> = {
  venta: 'Venta',
  alquiler: 'Alquiler',
  alquiler_temporal: 'Alq. Temporal',
};

const PROPERTY_TYPE_LABELS: Record<string, string> = {
  departamento: 'Departamento',
  casa: 'Casa',
  ph: 'PH',
  terreno: 'Terreno',
  local: 'Local',
  oficina: 'Oficina',
};

function formatCurrency(amount: number, currency: string) {
  return `${currency} ${amount.toLocaleString('es-AR')}`;
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function SavedSearchList() {
  const navigate = useNavigate();
  const { data, isLoading, error: queryError } = useSavedSearches();
  const createMutation = useCreateSearch();
  const updateMutation = useUpdateSearch();
  const deleteMutation = useDeleteSearch();
  const executeMutation = useExecuteSearch();
  const toggleMutation = useToggleSearch();

  const [formOpen, setFormOpen] = useState(false);
  const [editSearch, setEditSearch] = useState<SavedSearch | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<SavedSearch | null>(null);
  const [executingId, setExecutingId] = useState<string | null>(null);
  const [executeResult, setExecuteResult] = useState<SavedSearchExecuteResponse | null>(null);
  const [actionError, setActionError] = useState('');

  const searches = data?.items || [];
  const error = queryError?.message || actionError;

  const handleCreate = () => {
    setEditSearch(null);
    setFormOpen(true);
  };

  const handleEdit = (search: SavedSearch) => {
    setEditSearch(search);
    setFormOpen(true);
  };

  const handleFormSubmit = async (formData: Record<string, unknown>) => {
    try {
      setActionError('');
      if (editSearch) {
        await updateMutation.mutateAsync({ id: editSearch.id, data: formData });
      } else {
        await createMutation.mutateAsync(formData as any);
      }
      setFormOpen(false);
      setEditSearch(null);
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Error al guardar la búsqueda');
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    try {
      setActionError('');
      await deleteMutation.mutateAsync(deleteConfirm.id);
      setDeleteConfirm(null);
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Error al eliminar la búsqueda');
      setDeleteConfirm(null);
    }
  };

  const handleExecute = async (search: SavedSearch) => {
    try {
      setActionError('');
      setExecuteResult(null);
      setExecutingId(search.id);
      const result = await executeMutation.mutateAsync({ id: search.id });
      setExecuteResult(result);
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Error al ejecutar la búsqueda');
    } finally {
      setExecutingId(null);
    }
  };

  const handleToggle = async (search: SavedSearch) => {
    try {
      setActionError('');
      await toggleMutation.mutateAsync(search.id);
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Error al cambiar el estado');
    }
  };

  const formLoading = createMutation.isPending || updateMutation.isPending;

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" fontWeight={600}>
          Búsquedas Guardadas
        </Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={handleCreate}>
          Nueva Búsqueda
        </Button>
      </Box>

      {/* Alerts */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setActionError('')}>
          {error}
        </Alert>
      )}

      {executeResult && (
        <Alert
          severity={executeResult.errors.length > 0 ? 'warning' : 'success'}
          sx={{ mb: 2 }}
          onClose={() => setExecuteResult(null)}
        >
          <Typography variant="subtitle2" gutterBottom>
            Resultados de "{executeResult.search_name}"
          </Typography>
          <Typography variant="body2">
            Encontradas: {executeResult.total_found} | Nuevas: {executeResult.new_properties} |
            Duplicadas: {executeResult.duplicates} | Scrapeadas: {executeResult.scraped} |
            Pendientes: {executeResult.pending}
          </Typography>
          {executeResult.errors.length > 0 && (
            <Typography variant="body2" color="error">
              Errores: {executeResult.errors.length}
            </Typography>
          )}
        </Alert>
      )}

      {/* Loading */}
      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : searches.length === 0 ? (
        /* Empty state */
        <Box sx={{ textAlign: 'center', py: 8 }}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No hay búsquedas guardadas
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Crea tu primera búsqueda para monitorear propiedades automáticamente.
          </Typography>
          <Button variant="contained" startIcon={<AddIcon />} onClick={handleCreate}>
            Crear Primera Búsqueda
          </Button>
        </Box>
      ) : (
        /* Search cards grid */
        <Grid container spacing={3}>
          {searches.map((search) => (
            <Grid item xs={12} sm={6} md={4} key={search.id}>
              <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <CardContent sx={{ flexGrow: 1 }}>
                  {/* Name + Active chip */}
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                    <Typography variant="h6" noWrap sx={{ maxWidth: '70%' }}>
                      {search.name}
                    </Typography>
                    <Chip
                      label={search.is_active ? 'Activa' : 'Inactiva'}
                      color={search.is_active ? 'success' : 'default'}
                      size="small"
                    />
                  </Box>

                  {/* Portals */}
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mb: 1.5 }}>
                    {search.portals.map((portal) => (
                      <Chip
                        key={portal}
                        label={portal}
                        size="small"
                        color={PORTAL_COLORS[portal] || 'default'}
                        variant="outlined"
                      />
                    ))}
                  </Box>

                  {/* Filters summary */}
                  <Box sx={{ mb: 1.5 }}>
                    <Typography variant="body2" color="text.secondary">
                      {OPERATION_LABELS[search.operation_type] || search.operation_type}
                      {search.property_type && ` - ${PROPERTY_TYPE_LABELS[search.property_type] || search.property_type}`}
                    </Typography>
                    {(search.min_price || search.max_price) && (
                      <Typography variant="body2" color="text.secondary">
                        Precio: {search.min_price ? formatCurrency(search.min_price, search.currency) : '—'}
                        {' - '}
                        {search.max_price ? formatCurrency(search.max_price, search.currency) : '—'}
                      </Typography>
                    )}
                    {(search.city || search.province) && (
                      <Typography variant="body2" color="text.secondary">
                        {[search.city, search.province].filter(Boolean).join(', ')}
                      </Typography>
                    )}
                    {search.neighborhoods && search.neighborhoods.length > 0 && (
                      <Typography variant="body2" color="text.secondary" noWrap>
                        Barrios: {search.neighborhoods.join(', ')}
                      </Typography>
                    )}
                    {(search.min_area || search.max_area) && (
                      <Typography variant="body2" color="text.secondary">
                        Superficie: {search.min_area || '—'} - {search.max_area || '—'} m²
                      </Typography>
                    )}
                    {(search.min_bedrooms !== undefined && search.min_bedrooms !== null) && (
                      <Typography variant="body2" color="text.secondary">
                        Dormitorios: {search.min_bedrooms}
                        {search.max_bedrooms !== undefined && search.max_bedrooms !== null ? ` - ${search.max_bedrooms}` : '+'}
                      </Typography>
                    )}
                  </Box>

                  {/* Stats */}
                  <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                    <Typography variant="caption" color="text.secondary">
                      Pendientes: <strong>{search.pending_count}</strong>
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Total: <strong>{search.total_properties_found}</strong>
                    </Typography>
                  </Box>
                  {search.last_executed_at && (
                    <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
                      Última ejecución: {formatDate(search.last_executed_at)}
                    </Typography>
                  )}
                </CardContent>

                <CardActions sx={{ justifyContent: 'space-between', px: 2, pb: 1.5 }}>
                  <Box>
                    <Tooltip title="Ejecutar búsqueda">
                      <span>
                        <IconButton
                          color="primary"
                          onClick={() => handleExecute(search)}
                          disabled={executingId === search.id}
                          size="small"
                        >
                          {executingId === search.id ? (
                            <CircularProgress size={20} />
                          ) : (
                            <PlayIcon />
                          )}
                        </IconButton>
                      </span>
                    </Tooltip>
                    <Tooltip title={search.is_active ? 'Desactivar' : 'Activar'}>
                      <IconButton
                        onClick={() => handleToggle(search)}
                        size="small"
                        color={search.is_active ? 'success' : 'default'}
                      >
                        {search.is_active ? <ToggleOnIcon /> : <ToggleOffIcon />}
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Editar">
                      <IconButton onClick={() => handleEdit(search)} size="small">
                        <EditIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Eliminar">
                      <IconButton
                        color="error"
                        onClick={() => setDeleteConfirm(search)}
                        size="small"
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Tooltip>
                  </Box>
                  <Button
                    size="small"
                    startIcon={<ViewIcon />}
                    onClick={() => navigate(`/saved-searches/${search.id}/pending`)}
                  >
                    Pendientes
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Form Dialog */}
      <SavedSearchForm
        open={formOpen}
        onClose={() => {
          setFormOpen(false);
          setEditSearch(null);
        }}
        onSubmit={handleFormSubmit}
        search={editSearch}
        loading={formLoading}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteConfirm} onClose={() => setDeleteConfirm(null)}>
        <DialogTitle>Eliminar Búsqueda</DialogTitle>
        <DialogContent>
          <DialogContentText>
            ¿Estás seguro de eliminar la búsqueda "{deleteConfirm?.name}"?
            Esto también eliminará todas las propiedades pendientes asociadas.
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
