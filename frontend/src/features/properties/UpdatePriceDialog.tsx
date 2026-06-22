/**
 * Dialog for manually updating property price or triggering a re-scrape
 */
import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Box,
  Typography,
  Alert,
  CircularProgress,
} from '@mui/material';
import { PriceChange as PriceChangeIcon, Refresh as RefreshIcon } from '@mui/icons-material';
import { propertiesApi, type Property } from '../../api/properties';

interface Props {
  open: boolean;
  onClose: () => void;
  property: Property;
  onSuccess: () => void;
}

export default function UpdatePriceDialog({ open, onClose, property, onSuccess }: Props) {
  const [price, setPrice] = useState<string>(String(property.price));
  const [currency, setCurrency] = useState<string>(property.currency);
  const [saving, setSaving] = useState(false);
  const [rescraping, setRescraping] = useState(false);
  const [error, setError] = useState('');
  const [rescrapeResult, setRescrapeResult] = useState('');

  const handleSave = async () => {
    const parsedPrice = parseFloat(price);
    if (isNaN(parsedPrice) || parsedPrice <= 0) {
      setError('Ingresá un precio válido');
      return;
    }
    try {
      setSaving(true);
      setError('');
      setRescrapeResult('');
      await propertiesApi.updateProperty(property.id, { price: parsedPrice, currency });
      onSuccess();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al guardar el precio');
    } finally {
      setSaving(false);
    }
  };

  const handleRescrape = async () => {
    try {
      setRescraping(true);
      setError('');
      setRescrapeResult('');
      const result = await propertiesApi.rescrapeProperty(property.id);
      if (result.price_changed) {
        setRescrapeResult(
          `Precio actualizado: ${result.old_price.toLocaleString('es-AR')} → ${result.new_price.toLocaleString('es-AR')} ${property.currency}`
        );
      } else if (result.error) {
        setError(result.error);
        return;
      } else {
        setRescrapeResult('Sin cambios: el precio sigue siendo el mismo en el portal.');
      }
      onSuccess();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al actualizar desde el portal');
    } finally {
      setRescraping(false);
    }
  };

  const isLoading = saving || rescraping;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Actualizar precio</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Precio actual:{' '}
          <strong>
            {property.currency} {property.price.toLocaleString('es-AR')}
          </strong>
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {rescrapeResult && (
          <Alert severity="success" sx={{ mb: 2 }}>
            {rescrapeResult}
          </Alert>
        )}

        <Box sx={{ display: 'flex', gap: 1 }}>
          <TextField
            label="Nuevo precio"
            type="number"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            fullWidth
            inputProps={{ min: 0, step: 1000 }}
            disabled={isLoading}
          />
          <FormControl sx={{ minWidth: 90 }} disabled={isLoading}>
            <InputLabel>Moneda</InputLabel>
            <Select
              value={currency}
              label="Moneda"
              onChange={(e) => setCurrency(e.target.value)}
            >
              <MenuItem value="USD">USD</MenuItem>
              <MenuItem value="ARS">ARS</MenuItem>
            </Select>
          </FormControl>
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2, flexWrap: 'wrap', gap: 1 }}>
        {property.source_url && (
          <Button
            variant="outlined"
            startIcon={rescraping ? <CircularProgress size={16} /> : <RefreshIcon />}
            onClick={handleRescrape}
            disabled={isLoading}
            sx={{ mr: 'auto' }}
          >
            Actualizar desde portal
          </Button>
        )}
        <Button onClick={onClose} disabled={isLoading}>
          Cancelar
        </Button>
        <Button
          variant="contained"
          startIcon={saving ? <CircularProgress size={16} /> : <PriceChangeIcon />}
          onClick={handleSave}
          disabled={isLoading}
        >
          Guardar
        </Button>
      </DialogActions>
    </Dialog>
  );
}
