/**
 * Property Detail Page
 */
import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Paper,
  Grid,
  Chip,
  CircularProgress,
  Alert,
  Divider,
  IconButton,
  Card,
  CardMedia,
  Stack,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Home as HomeIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  OpenInNew as OpenInNewIcon,
  NavigateNext as NavigateNextIcon,
  NavigateBefore as NavigateBeforeIcon,
} from '@mui/icons-material';
import { propertiesApi, type Property } from '../../api/properties';

export default function PropertyDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [property, setProperty] = useState<Property | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [currentImageIndex, setCurrentImageIndex] = useState(0);

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
    loadProperty();
  }, [id]);

  const loadProperty = async () => {
    if (!id) return;

    try {
      setLoading(true);
      setError('');
      const data = await propertiesApi.getProperty(id);
      setProperty(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al cargar propiedad');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number, currency: string) => {
    return `${currency} ${amount.toLocaleString('es-AR')}`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-AR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const handlePrevImage = () => {
    if (!property?.images) return;
    setCurrentImageIndex((prev) =>
      prev === 0 ? property.images.length - 1 : prev - 1
    );
  };

  const handleNextImage = () => {
    if (!property?.images) return;
    setCurrentImageIndex((prev) =>
      prev === property.images.length - 1 ? 0 : prev + 1
    );
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !property) {
    return (
      <Box>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/properties')} sx={{ mb: 3 }}>
          Volver a Propiedades
        </Button>
        <Alert severity="error">
          {error || 'Propiedad no encontrada'}
        </Alert>
      </Box>
    );
  }

  const hasImages = property.images && property.images.length > 0;
  const currentImage = hasImages ? property.images[currentImageIndex] : null;

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3, alignItems: 'center' }}>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/properties')}>
          Volver a Propiedades
        </Button>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button variant="outlined" startIcon={<EditIcon />}>
            Editar
          </Button>
          <Button variant="outlined" color="error" startIcon={<DeleteIcon />}>
            Eliminar
          </Button>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* Left Column - Images */}
        <Grid item xs={12} md={7}>
          <Paper sx={{ p: 0, overflow: 'hidden' }}>
            {hasImages ? (
              <>
                {/* Main Image */}
                <Box sx={{ position: 'relative', bgcolor: 'grey.900' }}>
                  <CardMedia
                    component="img"
                    image={currentImage?.url}
                    alt={property.title}
                    sx={{
                      width: '100%',
                      height: 500,
                      objectFit: 'contain',
                    }}
                  />

                  {/* Navigation Arrows */}
                  {property.images.length > 1 && (
                    <>
                      <IconButton
                        onClick={handlePrevImage}
                        sx={{
                          position: 'absolute',
                          left: 8,
                          top: '50%',
                          transform: 'translateY(-50%)',
                          bgcolor: 'rgba(0, 0, 0, 0.5)',
                          color: 'white',
                          '&:hover': { bgcolor: 'rgba(0, 0, 0, 0.7)' },
                        }}
                      >
                        <NavigateBeforeIcon />
                      </IconButton>
                      <IconButton
                        onClick={handleNextImage}
                        sx={{
                          position: 'absolute',
                          right: 8,
                          top: '50%',
                          transform: 'translateY(-50%)',
                          bgcolor: 'rgba(0, 0, 0, 0.5)',
                          color: 'white',
                          '&:hover': { bgcolor: 'rgba(0, 0, 0, 0.7)' },
                        }}
                      >
                        <NavigateNextIcon />
                      </IconButton>
                    </>
                  )}

                  {/* Image Counter */}
                  <Box
                    sx={{
                      position: 'absolute',
                      bottom: 16,
                      right: 16,
                      bgcolor: 'rgba(0, 0, 0, 0.7)',
                      color: 'white',
                      px: 2,
                      py: 0.5,
                      borderRadius: 1,
                    }}
                  >
                    {currentImageIndex + 1} / {property.images.length}
                  </Box>
                </Box>

                {/* Thumbnail Strip */}
                {property.images.length > 1 && (
                  <Box sx={{ display: 'flex', gap: 1, p: 2, overflowX: 'auto' }}>
                    {property.images.map((img, idx) => (
                      <Card
                        key={img.url}
                        onClick={() => setCurrentImageIndex(idx)}
                        sx={{
                          minWidth: 100,
                          cursor: 'pointer',
                          border: idx === currentImageIndex ? 2 : 0,
                          borderColor: 'primary.main',
                          opacity: idx === currentImageIndex ? 1 : 0.6,
                          '&:hover': { opacity: 1 },
                        }}
                      >
                        <CardMedia
                          component="img"
                          image={img.url}
                          alt={`Thumbnail ${idx + 1}`}
                          sx={{ height: 80, objectFit: 'cover' }}
                        />
                      </Card>
                    ))}
                  </Box>
                )}
              </>
            ) : (
              <Box
                sx={{
                  height: 500,
                  bgcolor: 'grey.200',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <HomeIcon sx={{ fontSize: 120, color: 'grey.400' }} />
              </Box>
            )}
          </Paper>

          {/* Description */}
          {property.description && (
            <Paper sx={{ p: 3, mt: 3 }}>
              <Typography variant="h6" gutterBottom>
                Descripción
              </Typography>
              <Typography variant="body1" sx={{ whiteSpace: 'pre-line' }}>
                {property.description}
              </Typography>
            </Paper>
          )}
        </Grid>

        {/* Right Column - Details */}
        <Grid item xs={12} md={5}>
          <Paper sx={{ p: 3 }}>
            {/* Title and Source */}
            <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: 'wrap' }}>
              <Chip
                label={property.source}
                size="small"
                sx={{
                  bgcolor: getPortalColor(property.source),
                  color: getPortalTextColor(property.source),
                  fontWeight: 600,
                  textTransform: 'uppercase',
                }}
              />
              <Chip label={property.property_type} size="small" color="primary" />
              <Chip label={property.operation_type} size="small" color="secondary" />
            </Stack>

            <Typography variant="h4" gutterBottom>
              {property.title}
            </Typography>

            {/* Price */}
            <Typography variant="h3" color="primary" gutterBottom>
              {formatCurrency(property.price, property.currency)}
            </Typography>

            {property.price_per_sqm && (
              <Typography variant="h6" color="text.secondary" gutterBottom>
                {formatCurrency(property.price_per_sqm, property.currency)}/m²
              </Typography>
            )}

            <Divider sx={{ my: 3 }} />

            {/* Location */}
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                📍 Ubicación
              </Typography>
              {property.address && (
                <Typography variant="body1" gutterBottom>
                  {property.address}
                </Typography>
              )}
              <Typography variant="body1" color="text.secondary">
                {property.neighborhood && `${property.neighborhood}, `}
                {property.city}
                {property.province && property.province !== property.city && `, ${property.province}`}
              </Typography>
            </Box>

            <Divider sx={{ my: 3 }} />

            {/* Features */}
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                Características
              </Typography>
              <Grid container spacing={2}>
                {property.bedrooms && (
                  <Grid item xs={6}>
                    <Typography variant="body1">
                      🛏️ Dormitorios: <strong>{property.bedrooms}</strong>
                    </Typography>
                  </Grid>
                )}
                {property.bathrooms && (
                  <Grid item xs={6}>
                    <Typography variant="body1">
                      🚿 Baños: <strong>{property.bathrooms}</strong>
                    </Typography>
                  </Grid>
                )}
                {property.parking_spaces && (
                  <Grid item xs={6}>
                    <Typography variant="body1">
                      🚗 Cocheras: <strong>{property.parking_spaces}</strong>
                    </Typography>
                  </Grid>
                )}
                {property.total_area && (
                  <Grid item xs={6}>
                    <Typography variant="body1">
                      📐 Superficie Total: <strong>{property.total_area}m²</strong>
                    </Typography>
                  </Grid>
                )}
                {property.covered_area && (
                  <Grid item xs={6}>
                    <Typography variant="body1">
                      🏠 Sup. Cubierta: <strong>{property.covered_area}m²</strong>
                    </Typography>
                  </Grid>
                )}
              </Grid>
            </Box>

            {/* Amenities */}
            {property.amenities?.list && property.amenities.list.length > 0 && (
              <>
                <Divider sx={{ my: 3 }} />
                <Box sx={{ mb: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    Amenities
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    {property.amenities.list.map((amenity: string, idx: number) => (
                      <Chip key={idx} label={amenity} size="small" variant="outlined" />
                    ))}
                  </Box>
                </Box>
              </>
            )}

            {/* Contact Info */}
            {property.real_estate_agency && (
              <>
                <Divider sx={{ my: 3 }} />
                <Box sx={{ mb: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    Contacto
                  </Typography>
                  <Typography variant="body1">
                    <strong>Inmobiliaria:</strong> {property.real_estate_agency}
                  </Typography>
                  {property.contact_info?.phone && (
                    <Typography variant="body1">
                      <strong>Teléfono:</strong> {property.contact_info.phone}
                    </Typography>
                  )}
                  {property.contact_info?.email && (
                    <Typography variant="body1">
                      <strong>Email:</strong> {property.contact_info.email}
                    </Typography>
                  )}
                </Box>
              </>
            )}

            <Divider sx={{ my: 3 }} />

            {/* Source Link */}
            {property.source_url && (
              <Button
                variant="outlined"
                fullWidth
                startIcon={<OpenInNewIcon />}
                href={property.source_url}
                target="_blank"
                rel="noopener noreferrer"
                sx={{ mb: 2 }}
              >
                Ver Anuncio Original en {property.source}
              </Button>
            )}

            {/* Metadata */}
            <Typography variant="caption" color="text.secondary" display="block">
              ID: {property.id}
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block">
              Agregada: {formatDate(property.created_at)}
            </Typography>
            {property.scraped_at && (
              <Typography variant="caption" color="text.secondary" display="block">
                Última actualización: {formatDate(property.scraped_at)}
              </Typography>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
