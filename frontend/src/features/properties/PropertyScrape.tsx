/**
 * Property Scraping Page
 */
import { useState } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  Alert,
  CircularProgress,
  Card,
  CardContent,
  CardMedia,
  Grid,
  Chip,
  FormControlLabel,
  Checkbox,
} from '@mui/material';
import { Search as SearchIcon } from '@mui/icons-material';
import { propertiesApi, type PropertyScrapeResponse } from '../../api/properties';

export default function PropertyScrape() {
  const [url, setUrl] = useState('');
  const [saveToDb, setSaveToDb] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PropertyScrapeResponse | null>(null);
  const [error, setError] = useState('');

  const handleScrape = async () => {
    if (!url.trim()) {
      setError('Por favor ingresa una URL válida');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await propertiesApi.scrapeProperty({
        url: url.trim(),
        save_to_db: saveToDb,
      });

      setResult(response);

      if (!response.success) {
        setError(response.message);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al scrapear la propiedad');
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number, currency: string) => {
    return `${currency} ${amount.toLocaleString('es-AR')}`;
  };

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3 }}>
        Scrapear Propiedad
      </Typography>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
          Ingresa la URL de una propiedad de Argenprop para extraer automáticamente sus datos.
        </Typography>

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField
            fullWidth
            label="URL de la Propiedad"
            placeholder="https://www.argenprop.com.ar/..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={loading}
            helperText="Portales soportados: Argenprop"
          />

          <FormControlLabel
            control={
              <Checkbox
                checked={saveToDb}
                onChange={(e) => setSaveToDb(e.target.checked)}
                disabled={loading}
              />
            }
            label="Guardar en la base de datos"
          />

          <Button
            variant="contained"
            startIcon={loading ? <CircularProgress size={20} /> : <SearchIcon />}
            onClick={handleScrape}
            disabled={loading || !url.trim()}
            size="large"
          >
            {loading ? 'Scrapeando...' : 'Scrapear Propiedad'}
          </Button>
        </Box>
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {result?.success && result.data && (
        <Paper sx={{ p: 3 }}>
          <Alert severity="success" sx={{ mb: 3 }}>
            {result.message}
            {result.property_id && ` (ID: ${result.property_id})`}
          </Alert>

          <Typography variant="h5" sx={{ mb: 2 }}>
            Datos Extraídos
          </Typography>

          <Grid container spacing={3}>
            {/* Images Gallery */}
            {result.data.images && result.data.images.length > 0 && (
              <Grid item xs={12}>
                <Typography variant="h6" sx={{ mb: 1 }}>
                  Imágenes ({result.data.images.length})
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, overflowX: 'auto', pb: 1 }}>
                  {result.data.images.slice(0, 5).map((imgUrl: string, idx: number) => (
                    <CardMedia
                      key={idx}
                      component="img"
                      sx={{ width: 200, height: 150, objectFit: 'cover', borderRadius: 1 }}
                      image={imgUrl}
                      alt={`Property image ${idx + 1}`}
                    />
                  ))}
                  {result.data.images.length > 5 && (
                    <Box
                      sx={{
                        width: 200,
                        height: 150,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        bgcolor: 'grey.200',
                        borderRadius: 1,
                      }}
                    >
                      <Typography variant="h6" color="text.secondary">
                        +{result.data.images.length - 5} más
                      </Typography>
                    </Box>
                  )}
                </Box>
              </Grid>
            )}

            {/* Title and Description */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h5" gutterBottom>
                    {result.data.title}
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                    <Chip label={result.data.property_type} color="primary" size="small" />
                    <Chip label={result.data.operation_type} color="secondary" size="small" />
                  </Box>
                  {result.data.description && (
                    <Typography variant="body2" color="text.secondary">
                      {result.data.description.substring(0, 300)}
                      {result.data.description.length > 300 && '...'}
                    </Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>

            {/* Price and Location */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Precio
                  </Typography>
                  <Typography variant="h4" color="primary">
                    {formatCurrency(result.data.price, result.data.currency)}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Ubicación
                  </Typography>
                  {result.data.address && (
                    <Typography variant="body1">{result.data.address}</Typography>
                  )}
                  <Typography variant="body2" color="text.secondary">
                    {result.data.location?.neighborhood && `${result.data.location.neighborhood}, `}
                    {result.data.location?.city || 'Buenos Aires'},{' '}
                    {result.data.location?.province || 'Buenos Aires'}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            {/* Features */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Características
                  </Typography>
                  <Grid container spacing={2}>
                    {result.data.features?.bedrooms && (
                      <Grid item xs={6} sm={3}>
                        <Typography variant="body2" color="text.secondary">
                          Dormitorios
                        </Typography>
                        <Typography variant="h6">{result.data.features.bedrooms}</Typography>
                      </Grid>
                    )}
                    {result.data.features?.bathrooms && (
                      <Grid item xs={6} sm={3}>
                        <Typography variant="body2" color="text.secondary">
                          Baños
                        </Typography>
                        <Typography variant="h6">{result.data.features.bathrooms}</Typography>
                      </Grid>
                    )}
                    {result.data.features?.parking_spaces && (
                      <Grid item xs={6} sm={3}>
                        <Typography variant="body2" color="text.secondary">
                          Cocheras
                        </Typography>
                        <Typography variant="h6">{result.data.features.parking_spaces}</Typography>
                      </Grid>
                    )}
                    {result.data.features?.total_area && (
                      <Grid item xs={6} sm={3}>
                        <Typography variant="body2" color="text.secondary">
                          Superficie Total
                        </Typography>
                        <Typography variant="h6">{result.data.features.total_area} m²</Typography>
                      </Grid>
                    )}
                    {result.data.features?.covered_area && (
                      <Grid item xs={6} sm={3}>
                        <Typography variant="body2" color="text.secondary">
                          Superficie Cubierta
                        </Typography>
                        <Typography variant="h6">{result.data.features.covered_area} m²</Typography>
                      </Grid>
                    )}
                  </Grid>

                  {/* Amenities */}
                  {result.data.features?.amenities && result.data.features.amenities.length > 0 && (
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="body2" color="text.secondary" gutterBottom>
                        Amenities
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                        {result.data.features.amenities.map((amenity: string, idx: number) => (
                          <Chip key={idx} label={amenity} size="small" variant="outlined" />
                        ))}
                      </Box>
                    </Box>
                  )}
                </CardContent>
              </Card>
            </Grid>

            {/* Contact Information */}
            {result.data.contact && (
              <Grid item xs={12}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Información de Contacto
                    </Typography>
                    {result.data.contact.real_estate_agency && (
                      <Typography variant="body1">
                        <strong>Inmobiliaria:</strong> {result.data.contact.real_estate_agency}
                      </Typography>
                    )}
                    {result.data.contact.phone && (
                      <Typography variant="body2" color="text.secondary">
                        <strong>Teléfono:</strong> {result.data.contact.phone}
                      </Typography>
                    )}
                    {result.data.contact.email && (
                      <Typography variant="body2" color="text.secondary">
                        <strong>Email:</strong> {result.data.contact.email}
                      </Typography>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            )}

            {/* Source Information */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Información de Origen
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    <strong>Portal:</strong> {result.data.source}
                  </Typography>
                  {result.data.source_id && (
                    <Typography variant="body2" color="text.secondary">
                      <strong>ID:</strong> {result.data.source_id}
                    </Typography>
                  )}
                  <Typography variant="body2" color="text.secondary">
                    <strong>URL:</strong>{' '}
                    <a href={result.data.source_url} target="_blank" rel="noopener noreferrer">
                      {result.data.source_url}
                    </a>
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Paper>
      )}
    </Box>
  );
}
