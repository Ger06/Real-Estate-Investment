/**
 * Property List Page
 */
import { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Button,
  Paper,
  Grid,
  Card,
  CardContent,
  CardMedia,
  Chip,
  CircularProgress,
  Alert,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Divider,
} from '@mui/material';
import {
  Add as AddIcon,
  Search as SearchIcon,
  Home as HomeIcon,
  Refresh as RefreshIcon,
  TableChart as TableChartIcon,
  Sync as SyncIcon,
  PriceChange as PriceChangeIcon,
  Cached as CachedIcon,
  ArrowDropDown as ArrowDropDownIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { propertiesApi, type Property } from '../../api/properties';
import { useProperties } from '../../hooks/useProperties';

export default function PropertyList() {
  const navigate = useNavigate();

  // React Query hook - reemplaza useState + useEffect + loadProperties
  const {
    data,
    isLoading,
    error: queryError,
    refetch
  } = useProperties(0, 50);

  const [actionError, setActionError] = useState('');

  const properties = data?.items || [];
  const total = data?.total || 0;
  const error = queryError?.message || actionError || '';

  const [updateMenuAnchor, setUpdateMenuAnchor] = useState<null | HTMLElement>(null);
  const [updating, setUpdating] = useState(false);

  // Portal colors
  const getPortalColor = (source: string) => {
    const colors: Record<string, string> = {
      argenprop: '#00a650',
      zonaprop: '#ff6600',
      remax: '#e31837',
      mercadolibre: '#ffe600',
    };
    return colors[source?.toLowerCase()] || '#757575';
  };

  const getPortalTextColor = (source: string) => {
    return source?.toLowerCase() === 'mercadolibre' ? '#000' : '#fff';
  };

  useEffect(() => {
    console.log(properties);
  }, [properties]);

  const formatCurrency = (amount: number, currency: string) => {
    return `${currency} ${amount.toLocaleString('es-AR')}`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-AR');
  };

  // Menu handlers
  const handleUpdateMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setUpdateMenuAnchor(event.currentTarget);
  };

  const handleUpdateMenuClose = () => {
    setUpdateMenuAnchor(null);
  };

  // Opción 1: Refrescar vista (simplemente recarga desde BD)
  const handleRefreshView = async () => {
    handleUpdateMenuClose();
    await refetch();
  };

  // Opción 2: Actualizar precios desde portales
  const handleUpdatePrices = async () => {
    handleUpdateMenuClose();
    try {
      setUpdating(true);
      setActionError('');

      const response = await propertiesApi.updateAllPrices();

      if (response.success) {
        // Mostrar detalles de los cambios de precio
        if (response.price_changes && response.price_changes.length > 0) {
          const changes = response.price_changes
            .map(
              (change) =>
                `${change.title}: ${change.old_price} → ${change.new_price} (${change.change_percentage > 0 ? '+' : ''}${change.change_percentage}%)`
            )
            .join('\n');

          alert(
            `${response.message}\n\nCambios de precio:\n${changes}`
          );
        } else {
          alert(response.message);
        }

        await refetch();
      } else {
        setActionError(response.message);
      }
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Error al actualizar precios');
    } finally {
      setUpdating(false);
    }
  };

  // Opción 3: Re-scrapear todas las propiedades
  const handleRescrapeAll = async () => {
    handleUpdateMenuClose();

    const confirmed = window.confirm(
      `¿Estás seguro de que querés re-scrapear todas las ${total} propiedades? Esto puede tomar varios minutos.`
    );

    if (!confirmed) return;

    try {
      setUpdating(true);
      setActionError('');

      const response = await propertiesApi.rescrapeAll();

      if (response.success) {
        alert(response.message);
        await refetch();
      } else {
        setActionError(response.message);
      }
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Error al re-scrapear propiedades');
    } finally {
      setUpdating(false);
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Box>
          <Typography variant="h4">Propiedades</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            {total} {total === 1 ? 'propiedad registrada' : 'propiedades registradas'}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            endIcon={<ArrowDropDownIcon />}
            onClick={handleUpdateMenuOpen}
            disabled={isLoading || updating}
          >
            {updating ? 'Actualizando...' : 'Actualizar'}
          </Button>
          <Menu
            anchorEl={updateMenuAnchor}
            open={Boolean(updateMenuAnchor)}
            onClose={handleUpdateMenuClose}
          >
            <MenuItem onClick={handleRefreshView}>
              <ListItemIcon>
                <RefreshIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText
                primary="Refrescar vista"
                secondary="Recargar propiedades desde la base de datos"
              />
            </MenuItem>
            <Divider />
            <MenuItem onClick={handleUpdatePrices}>
              <ListItemIcon>
                <PriceChangeIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText
                primary="Actualizar precios desde portales"
                secondary="Verificar cambios de precio en cada portal"
              />
            </MenuItem>
            <MenuItem onClick={handleRescrapeAll}>
              <ListItemIcon>
                <CachedIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText
                primary="Re-scrapear todas"
                secondary="Actualizar toda la información de cada propiedad"
              />
            </MenuItem>
          </Menu>
          <Button
            variant="outlined"
            startIcon={<TableChartIcon />}
            onClick={() => navigate('/properties/analysis')}
          >
            Análisis y Exportar
          </Button>
          <Button
            variant="outlined"
            startIcon={<SearchIcon />}
            onClick={() => navigate('/properties/scrape')}
          >
            Scrapear Propiedad
          </Button>
          {/*<Button variant="contained" startIcon={<AddIcon />}>
            Nueva Propiedad
          </Button>*/}
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {updating && (
        <Alert severity="info" sx={{ mb: 3 }} icon={<CircularProgress size={20} />}>
          Actualizando propiedades... Esto puede tomar varios minutos.
        </Alert>
      )}

      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : properties.length === 0 ? (
        <Paper sx={{ p: 3 }}>
          <Typography variant="body1" color="text.secondary">
            No hay propiedades registradas aún.
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Comienza agregando propiedades manualmente o mediante web scraping.
          </Typography>
        </Paper>
      ) : (
        <Grid container spacing={3}>
          {properties.map((property) => (
            <Grid item xs={12} sm={6} md={4} key={property.id}>
              <Card
                sx={{
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  cursor: 'pointer',
                  transition: 'transform 0.2s, box-shadow 0.2s',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: 4,
                  },
                }}
                onClick={() => navigate(`/properties/${property.id}`)}
              >
                {property.images && property.images.length > 0 ? (
                  <CardMedia
                    component="img"
                    height="200"
                    image={property.images.find((img) => img.is_primary)?.url || property.images[0]?.url}
                    alt={property.title}
                    sx={{ objectFit: 'cover' }}
                  />
                ) : (
                  <Box
                    sx={{
                      height: 200,
                      bgcolor: 'grey.200',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <HomeIcon sx={{ fontSize: 64, color: 'grey.400' }} />
                  </Box>
                )}
                <CardContent sx={{ flexGrow: 1 }}>
                  <Box sx={{ display: 'flex', gap: 1, mb: 1, flexWrap: 'wrap' }}>
                    <Chip label={property.property_type} size="small" color="primary" />
                    <Chip label={property.operation_type} size="small" color="secondary" />
                    <Chip label={property.status} size="small" color="success" />
                    <Chip
                      label={property.source}
                      size="small"
                      sx={{
                        bgcolor: getPortalColor(property.source),
                        color: getPortalTextColor(property.source),
                        fontWeight: 600,
                        textTransform: 'uppercase',
                        fontSize: '0.7rem',
                      }}
                    />
                  </Box>

                  <Typography variant="h6" gutterBottom noWrap>
                    {property.title}
                  </Typography>

                  <Typography variant="h5" color="primary" gutterBottom>
                    {formatCurrency(property.price, property.currency)}
                  </Typography>

                  {property.price_per_sqm && (
                    <Typography variant="body2" color="text.secondary">
                      {formatCurrency(property.price_per_sqm, property.currency)}/m²
                    </Typography>
                  )}

                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    📍 {property.neighborhood}, {property.city}
                  </Typography>

                  <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
                    {property.bedrooms && (
                      <Typography variant="body2" color="text.secondary">
                        🛏️ {property.bedrooms}
                      </Typography>
                    )}
                    {property.bathrooms && (
                      <Typography variant="body2" color="text.secondary">
                        🚿 {property.bathrooms}
                      </Typography>
                    )}
                    {property.total_area && (
                      <Typography variant="body2" color="text.secondary">
                        📐 {property.total_area}m²
                      </Typography>
                    )}
                  </Box>

                  <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
                    Agregada: {formatDate(property.created_at)}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  );
}
