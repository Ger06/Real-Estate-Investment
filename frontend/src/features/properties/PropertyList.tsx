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
  Snackbar,
  Pagination,
  Select,
} from '@mui/material';
import type { SelectChangeEvent } from '@mui/material/Select';
import {
  Search as SearchIcon,
  Home as HomeIcon,
  Refresh as RefreshIcon,
  TableChart as TableChartIcon,
  PriceChange as PriceChangeIcon,
  Cached as CachedIcon,
  ArrowDropDown as ArrowDropDownIcon,
  ChevronRight as ChevronRightIcon,
  FilterList as FilterListIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { propertiesApi, type Property, type PropertyFilters } from '../../api/properties';
import { useProperties } from '../../hooks/useProperties';
import UpdatePriceDialog from './UpdatePriceDialog';
import PropertyFilterPanel from './PropertyFilterPanel';

const PAGE_SIZE = 25;

export default function PropertyList() {
  const navigate = useNavigate();

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(PAGE_SIZE);
  const [activeFilters, setActiveFilters] = useState<PropertyFilters>({});
  const [filtersOpen, setFiltersOpen] = useState(false);

  const {
    data,
    isLoading,
    error: queryError,
    refetch
  } = useProperties((page - 1) * pageSize, pageSize, activeFilters);

  const [actionError, setActionError] = useState('');

  const properties = data?.items || [];
  const total = data?.total || 0;
  const error = queryError?.message || actionError || '';

  const [updatePriceProperty, setUpdatePriceProperty] = useState<Property | null>(null);

  const [updateMenuAnchor, setUpdateMenuAnchor] = useState<null | HTMLElement>(null);
  const [pricesSubMenuAnchor, setPricesSubMenuAnchor] = useState<null | HTMLElement>(null);
  const [rescrapeSubMenuAnchor, setRescrapeSubMenuAnchor] = useState<null | HTMLElement>(null);
  const [updating, setUpdating] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  const activeFilterCount = Object.values(activeFilters).filter(
    (v) => v != null && v !== ''
  ).length;

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

  const closeAllMenus = () => {
    setUpdateMenuAnchor(null);
    setPricesSubMenuAnchor(null);
    setRescrapeSubMenuAnchor(null);
  };

  const handleRefreshView = async () => {
    handleUpdateMenuClose();
    await refetch();
  };

  const handleUpdatePrices = async (portal?: string) => {
    closeAllMenus();
    try {
      setUpdating(true);
      setActionError('');

      const response = await propertiesApi.updateAllPrices(portal);

      if (response.success) {
        let msg = response.message;
        if (response.price_changes && response.price_changes.length > 0) {
          const sample = response.price_changes
            .slice(0, 3)
            .map((c) => `${c.title.slice(0, 40)}: ${c.old_price} → ${c.new_price}`)
            .join(' | ');
          msg += ` — ${sample}`;
        }
        setSuccessMessage(msg);
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

  const handleRescrapeAll = async (portal?: string) => {
    closeAllMenus();

    const portalLabel = portal ? ` de ${portal}` : '';
    const confirmed = window.confirm(
      `¿Estás seguro de que querés re-scrapear las propiedades${portalLabel}? Esto puede tomar varios minutos.`
    );

    if (!confirmed) return;

    try {
      setUpdating(true);
      setActionError('');

      const response = await propertiesApi.rescrapeAll(portal);

      if (response.success) {
        let msg = `Re-scraping: ${response.total_properties} encontradas, ${response.updated_count} actualizadas, ${response.error_count} errores`;
        if (response.errors && response.errors.length > 0) {
          msg += ` | ${response.errors.slice(0, 3).join(', ')}`;
        }
        setSuccessMessage(msg);
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

  const handleApplyFilters = (filters: PropertyFilters) => {
    setActiveFilters(filters);
    setPage(1);
  };

  const handlePageSizeChange = (e: SelectChangeEvent) => {
    setPageSize(Number(e.target.value));
    setPage(1);
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
        <Box>
          <Typography variant="h4">Propiedades</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            {total} {total === 1 ? 'propiedad registrada' : 'propiedades registradas'}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
          <Button
            variant="outlined"
            startIcon={<FilterListIcon />}
            onClick={() => setFiltersOpen((v) => !v)}
            color={activeFilterCount > 0 ? 'primary' : 'inherit'}
          >
            Filtros{activeFilterCount > 0 ? ` (${activeFilterCount})` : ''}
          </Button>
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
            <MenuItem onClick={(e) => setPricesSubMenuAnchor(e.currentTarget)}>
              <ListItemIcon>
                <PriceChangeIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText
                primary="Actualizar precios"
                secondary="Verificar cambios de precio en cada portal"
              />
              <ChevronRightIcon fontSize="small" sx={{ ml: 1 }} />
            </MenuItem>
            <MenuItem onClick={(e) => setRescrapeSubMenuAnchor(e.currentTarget)}>
              <ListItemIcon>
                <CachedIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText
                primary="Re-scrapear todo"
                secondary="Actualizar toda la información de cada propiedad"
              />
              <ChevronRightIcon fontSize="small" sx={{ ml: 1 }} />
            </MenuItem>
          </Menu>

          {/* Submenú: Actualizar precios por portal */}
          <Menu
            anchorEl={pricesSubMenuAnchor}
            open={Boolean(pricesSubMenuAnchor)}
            onClose={() => setPricesSubMenuAnchor(null)}
            anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
            transformOrigin={{ vertical: 'top', horizontal: 'left' }}
          >
            <MenuItem onClick={() => handleUpdatePrices()}>Todos los portales</MenuItem>
            <Divider />
            <MenuItem onClick={() => handleUpdatePrices('argenprop')}>Argenprop</MenuItem>
            <MenuItem onClick={() => handleUpdatePrices('zonaprop')}>Zonaprop</MenuItem>
            <MenuItem onClick={() => handleUpdatePrices('remax')}>Remax</MenuItem>
            <MenuItem onClick={() => handleUpdatePrices('mercadolibre')}>MercadoLibre</MenuItem>
          </Menu>

          {/* Submenú: Re-scrapear por portal */}
          <Menu
            anchorEl={rescrapeSubMenuAnchor}
            open={Boolean(rescrapeSubMenuAnchor)}
            onClose={() => setRescrapeSubMenuAnchor(null)}
            anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
            transformOrigin={{ vertical: 'top', horizontal: 'left' }}
          >
            <MenuItem onClick={() => handleRescrapeAll()}>Todos los portales</MenuItem>
            <Divider />
            <MenuItem onClick={() => handleRescrapeAll('argenprop')}>Argenprop</MenuItem>
            <MenuItem onClick={() => handleRescrapeAll('zonaprop')}>Zonaprop</MenuItem>
            <MenuItem onClick={() => handleRescrapeAll('remax')}>Remax</MenuItem>
            <MenuItem onClick={() => handleRescrapeAll('mercadolibre')}>MercadoLibre</MenuItem>
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
        </Box>
      </Box>

      {/* Filter panel */}
      <PropertyFilterPanel
        open={filtersOpen}
        filters={activeFilters}
        onApply={handleApplyFilters}
        totalResults={total}
      />

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
                  <Button
                    size="small"
                    variant="outlined"
                    startIcon={<PriceChangeIcon />}
                    onClick={(e) => { e.stopPropagation(); setUpdatePriceProperty(property); }}
                    sx={{ mb: 1 }}
                  >
                    Actualizar precio
                  </Button>

                  {property.price_history?.length > 0 && (() => {
                    const last = [...property.price_history]
                      .sort((a, b) => new Date(b.recorded_at).getTime() - new Date(a.recorded_at).getTime())[0];
                    if (!last.previous_price || !last.change_percentage) return null;
                    const isDown = last.change_percentage < 0;
                    return (
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
                        <Chip
                          label={`${isDown ? '' : '+'}${last.change_percentage.toFixed(1)}%`}
                          size="small"
                          sx={{
                            bgcolor: isDown ? 'success.light' : 'error.light',
                            color: isDown ? 'success.dark' : 'error.dark',
                            fontWeight: 600,
                          }}
                        />
                        <Box>
                          <Typography variant="caption" color="text.secondary">
                            antes {last.currency} {last.previous_price.toLocaleString('es-AR')}
                          </Typography>
                          <Typography variant="caption" color="text.secondary" display="block">
                            Últ. cambio: {formatDate(last.recorded_at)}
                          </Typography>
                        </Box>
                      </Box>
                    );
                  })()}

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

      {/* Pagination */}
      {total > 0 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', mt: 3, gap: 2 }}>
          <Pagination
            count={Math.ceil(total / pageSize)}
            page={page}
            onChange={(_, p) => setPage(p)}
            color="primary"
          />
          <Select
            size="small"
            value={String(pageSize)}
            onChange={handlePageSizeChange}
          >
            <MenuItem value="25">25 por página</MenuItem>
            <MenuItem value="50">50 por página</MenuItem>
            <MenuItem value="100">100 por página</MenuItem>
          </Select>
        </Box>
      )}

      {updatePriceProperty && (
        <UpdatePriceDialog
          open={Boolean(updatePriceProperty)}
          onClose={() => setUpdatePriceProperty(null)}
          property={updatePriceProperty}
          onSuccess={() => { setUpdatePriceProperty(null); refetch(); }}
        />
      )}

      <Snackbar
        open={Boolean(successMessage)}
        autoHideDuration={7000}
        onClose={() => setSuccessMessage('')}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={() => setSuccessMessage('')} severity="success" sx={{ width: '100%' }}>
          {successMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
}
