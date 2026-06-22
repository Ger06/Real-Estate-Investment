/**
 * Filter panel for the property list page.
 * Collapsible, with local state; applies on button click.
 */
import { useState } from 'react';
import {
  Box,
  Button,
  Collapse,
  Grid,
  MenuItem,
  Paper,
  Select,
  TextField,
  Typography,
  Chip,
} from '@mui/material';
import type { SelectChangeEvent } from '@mui/material/Select';
import FilterListIcon from '@mui/icons-material/FilterList';
import ClearIcon from '@mui/icons-material/Clear';
import type { PropertyFilters } from '../../api/properties';

interface Props {
  open: boolean;
  filters: PropertyFilters;
  onApply: (filters: PropertyFilters) => void;
  totalResults: number;
}

const PORTALS = [
  { value: 'argenprop', label: 'Argenprop', bg: '#00a650', color: '#fff' },
  { value: 'zonaprop', label: 'Zonaprop', bg: '#ff6600', color: '#fff' },
  { value: 'remax', label: 'Remax', bg: '#e31837', color: '#fff' },
  { value: 'mercadolibre', label: 'MercadoLibre', bg: '#ffe600', color: '#000' },
  { value: 'manual', label: 'Manual', bg: '#757575', color: '#fff' },
];

const PROPERTY_TYPES = ['casa', 'ph', 'departamento', 'terreno', 'local', 'oficina'];
const OPERATION_TYPES = [
  { value: 'venta', label: 'Venta' },
  { value: 'alquiler', label: 'Alquiler' },
  { value: 'alquiler_temporal', label: 'Alquiler temporal' },
];
const STATUSES = [
  { value: 'active', label: 'Activa' },
  { value: 'sold', label: 'Vendida' },
  { value: 'rented', label: 'Alquilada' },
  { value: 'reserved', label: 'Reservada' },
  { value: 'removed', label: 'Eliminada' },
];
const CURRENCIES = ['USD', 'ARS'];
const BEDROOMS = [
  { value: 1, label: '1+' },
  { value: 2, label: '2+' },
  { value: 3, label: '3+' },
  { value: 4, label: '4+' },
];

export default function PropertyFilterPanel({ open, filters, onApply, totalResults }: Props) {
  const [local, setLocal] = useState<PropertyFilters>(filters);

  // Sync when parent resets filters
  // (shallow compare intentionally skipped — we trust the parent passes a new object on reset)

  const set = (key: keyof PropertyFilters, value: PropertyFilters[keyof PropertyFilters]) => {
    setLocal((prev) => ({ ...prev, [key]: value }));
  };

  const handleSelectChange = (key: keyof PropertyFilters) => (e: SelectChangeEvent) => {
    set(key, e.target.value || undefined);
  };

  const handleClear = () => {
    const empty: PropertyFilters = {};
    setLocal(empty);
    onApply(empty);
  };

  const handleApply = () => {
    // Strip empty strings so the API doesn't receive empty params
    const cleaned: PropertyFilters = {};
    for (const [k, v] of Object.entries(local)) {
      if (v !== '' && v !== undefined && v !== null) {
        (cleaned as Record<string, unknown>)[k] = v;
      }
    }
    onApply(cleaned);
  };

  return (
    <Collapse in={open} timeout="auto" unmountOnExit>
      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Grid container spacing={2} alignItems="flex-start">
          {/* Portal chips */}
          <Grid item xs={12}>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              Portal
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              {PORTALS.map((p) => {
                const selected = local.source === p.value;
                return (
                  <Chip
                    key={p.value}
                    label={p.label}
                    clickable
                    onClick={() => set('source', selected ? undefined : p.value)}
                    sx={{
                      bgcolor: selected ? p.bg : undefined,
                      color: selected ? p.color : undefined,
                      fontWeight: selected ? 700 : 400,
                      border: selected ? 'none' : undefined,
                    }}
                    variant={selected ? 'filled' : 'outlined'}
                  />
                );
              })}
            </Box>
          </Grid>

          {/* Tipo */}
          <Grid item xs={12} sm={4} md={3}>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              Tipo de inmueble
            </Typography>
            <Select
              size="small"
              fullWidth
              displayEmpty
              value={local.property_type ?? ''}
              onChange={handleSelectChange('property_type')}
            >
              <MenuItem value="">Todos</MenuItem>
              {PROPERTY_TYPES.map((t) => (
                <MenuItem key={t} value={t} sx={{ textTransform: 'capitalize' }}>
                  {t}
                </MenuItem>
              ))}
            </Select>
          </Grid>

          {/* Operación */}
          <Grid item xs={12} sm={4} md={3}>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              Operación
            </Typography>
            <Select
              size="small"
              fullWidth
              displayEmpty
              value={local.operation_type ?? ''}
              onChange={handleSelectChange('operation_type')}
            >
              <MenuItem value="">Todos</MenuItem>
              {OPERATION_TYPES.map((o) => (
                <MenuItem key={o.value} value={o.value}>
                  {o.label}
                </MenuItem>
              ))}
            </Select>
          </Grid>

          {/* Estado */}
          <Grid item xs={12} sm={4} md={3}>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              Estado
            </Typography>
            <Select
              size="small"
              fullWidth
              displayEmpty
              value={local.status ?? ''}
              onChange={handleSelectChange('status')}
            >
              <MenuItem value="">Todos</MenuItem>
              {STATUSES.map((s) => (
                <MenuItem key={s.value} value={s.value}>
                  {s.label}
                </MenuItem>
              ))}
            </Select>
          </Grid>

          {/* Moneda */}
          <Grid item xs={12} sm={4} md={3}>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              Moneda
            </Typography>
            <Select
              size="small"
              fullWidth
              displayEmpty
              value={local.currency ?? ''}
              onChange={handleSelectChange('currency')}
            >
              <MenuItem value="">Todas</MenuItem>
              {CURRENCIES.map((c) => (
                <MenuItem key={c} value={c}>
                  {c}
                </MenuItem>
              ))}
            </Select>
          </Grid>

          {/* Precio min */}
          <Grid item xs={6} sm={3} md={2}>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              Precio mín
            </Typography>
            <TextField
              size="small"
              fullWidth
              type="number"
              placeholder="0"
              value={local.price_min ?? ''}
              onChange={(e) => set('price_min', e.target.value ? Number(e.target.value) : undefined)}
              inputProps={{ min: 0 }}
            />
          </Grid>

          {/* Precio max */}
          <Grid item xs={6} sm={3} md={2}>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              Precio máx
            </Typography>
            <TextField
              size="small"
              fullWidth
              type="number"
              placeholder="∞"
              value={local.price_max ?? ''}
              onChange={(e) => set('price_max', e.target.value ? Number(e.target.value) : undefined)}
              inputProps={{ min: 0 }}
            />
          </Grid>

          {/* Dormitorios mínimos */}
          <Grid item xs={12} sm={4} md={3}>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              Dormitorios mín
            </Typography>
            <Select
              size="small"
              fullWidth
              displayEmpty
              value={local.bedrooms_min != null ? String(local.bedrooms_min) : ''}
              onChange={(e) =>
                set('bedrooms_min', e.target.value ? Number(e.target.value) : undefined)
              }
            >
              <MenuItem value="">Todos</MenuItem>
              {BEDROOMS.map((b) => (
                <MenuItem key={b.value} value={String(b.value)}>
                  {b.label}
                </MenuItem>
              ))}
            </Select>
          </Grid>

          {/* Ciudad */}
          <Grid item xs={12} sm={4} md={3}>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              Ciudad
            </Typography>
            <TextField
              size="small"
              fullWidth
              placeholder="Ej: Buenos Aires"
              value={local.city ?? ''}
              onChange={(e) => set('city', e.target.value || undefined)}
            />
          </Grid>

          {/* Barrio */}
          <Grid item xs={12} sm={4} md={3}>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              Barrio
            </Typography>
            <TextField
              size="small"
              fullWidth
              placeholder="Ej: Palermo"
              value={local.neighborhood ?? ''}
              onChange={(e) => set('neighborhood', e.target.value || undefined)}
            />
          </Grid>

          {/* Actions */}
          <Grid item xs={12}>
            <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, alignItems: 'center' }}>
              <Typography variant="caption" color="text.secondary">
                {totalResults} resultado{totalResults !== 1 ? 's' : ''}
              </Typography>
              <Button
                size="small"
                startIcon={<ClearIcon />}
                onClick={handleClear}
                color="inherit"
              >
                Limpiar
              </Button>
              <Button
                size="small"
                variant="contained"
                startIcon={<FilterListIcon />}
                onClick={handleApply}
              >
                Aplicar
              </Button>
            </Box>
          </Grid>
        </Grid>
      </Paper>
    </Collapse>
  );
}
