/**
 * Filter panel for the property map
 */
import { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  Switch,
  FormControlLabel,
  Divider,
  Chip,
  ToggleButtonGroup,
  ToggleButton,
} from '@mui/material';
import { FilterList as FilterIcon, Clear as ClearIcon } from '@mui/icons-material';
import type { PropertyFilters } from '../../../api/properties';

interface MapFilterPanelProps {
  filters: PropertyFilters;
  onApply: (filters: PropertyFilters) => void;
  totalResults: number;
  showChoropleth: boolean;
  onToggleChoropleth: (show: boolean) => void;
  choroplethAmbientes: number | null;
  onAmbientesChange: (ambientes: number | null) => void;
  choroplethGranularity: 'manzana' | 'barrio';
  onGranularityChange: (granularity: 'manzana' | 'barrio') => void;
}

export default function MapFilterPanel({
  filters: initialFilters,
  onApply,
  totalResults,
  showChoropleth,
  onToggleChoropleth,
  choroplethAmbientes,
  onAmbientesChange,
  choroplethGranularity,
  onGranularityChange,
}: MapFilterPanelProps) {
  const [filters, setFilters] = useState<PropertyFilters>(initialFilters);

  const handleClear = () => {
    const empty: PropertyFilters = {};
    setFilters(empty);
    onApply(empty);
  };

  const handleApply = () => {
    onApply(filters);
  };

  return (
    <Paper
      sx={{
        width: 280,
        p: 2,
        overflowY: 'auto',
        maxHeight: '100%',
        display: 'flex',
        flexDirection: 'column',
        gap: 1.5,
      }}
      elevation={2}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <FilterIcon fontSize="small" />
        <Typography variant="subtitle1" fontWeight="bold">
          Filtros
        </Typography>
        <Chip label={`${totalResults} resultados`} size="small" sx={{ ml: 'auto' }} />
      </Box>

      <Divider />

      <FormControl size="small" fullWidth>
        <InputLabel>Tipo de propiedad</InputLabel>
        <Select
          value={filters.property_type || ''}
          label="Tipo de propiedad"
          onChange={(e) => setFilters({ ...filters, property_type: e.target.value || undefined })}
        >
          <MenuItem value="">Todos</MenuItem>
          <MenuItem value="departamento">Departamento</MenuItem>
          <MenuItem value="casa">Casa</MenuItem>
          <MenuItem value="ph">PH</MenuItem>
          <MenuItem value="terreno">Terreno</MenuItem>
          <MenuItem value="local">Local</MenuItem>
          <MenuItem value="oficina">Oficina</MenuItem>
        </Select>
      </FormControl>

      <FormControl size="small" fullWidth>
        <InputLabel>Operación</InputLabel>
        <Select
          value={filters.operation_type || ''}
          label="Operación"
          onChange={(e) => setFilters({ ...filters, operation_type: e.target.value || undefined })}
        >
          <MenuItem value="">Todas</MenuItem>
          <MenuItem value="venta">Venta</MenuItem>
          <MenuItem value="alquiler">Alquiler</MenuItem>
          <MenuItem value="alquiler_temporal">Alquiler temporal</MenuItem>
        </Select>
      </FormControl>

      <FormControl size="small" fullWidth>
        <InputLabel>Estado</InputLabel>
        <Select
          value={filters.status || ''}
          label="Estado"
          onChange={(e) => setFilters({ ...filters, status: e.target.value || undefined })}
        >
          <MenuItem value="">Todos</MenuItem>
          <MenuItem value="ACTIVE">Activo</MenuItem>
          <MenuItem value="SOLD">Vendido</MenuItem>
          <MenuItem value="RENTED">Alquilado</MenuItem>
          <MenuItem value="RESERVED">Reservado</MenuItem>
          <MenuItem value="REMOVED">Removido</MenuItem>
        </Select>
      </FormControl>

      <FormControl size="small" fullWidth>
        <InputLabel>Moneda</InputLabel>
        <Select
          value={filters.currency || ''}
          label="Moneda"
          onChange={(e) => setFilters({ ...filters, currency: e.target.value || undefined })}
        >
          <MenuItem value="">Todas</MenuItem>
          <MenuItem value="USD">USD</MenuItem>
          <MenuItem value="ARS">ARS</MenuItem>
        </Select>
      </FormControl>

      <Box sx={{ display: 'flex', gap: 1 }}>
        <TextField
          size="small"
          label="Precio mín"
          type="number"
          value={filters.price_min ?? ''}
          onChange={(e) =>
            setFilters({ ...filters, price_min: e.target.value ? Number(e.target.value) : undefined })
          }
          fullWidth
        />
        <TextField
          size="small"
          label="Precio máx"
          type="number"
          value={filters.price_max ?? ''}
          onChange={(e) =>
            setFilters({ ...filters, price_max: e.target.value ? Number(e.target.value) : undefined })
          }
          fullWidth
        />
      </Box>

      <Box sx={{ display: 'flex', gap: 1 }}>
        <TextField
          size="small"
          label="Área mín (m²)"
          type="number"
          value={filters.area_min ?? ''}
          onChange={(e) =>
            setFilters({ ...filters, area_min: e.target.value ? Number(e.target.value) : undefined })
          }
          fullWidth
        />
        <TextField
          size="small"
          label="Área máx (m²)"
          type="number"
          value={filters.area_max ?? ''}
          onChange={(e) =>
            setFilters({ ...filters, area_max: e.target.value ? Number(e.target.value) : undefined })
          }
          fullWidth
        />
      </Box>

      <Box sx={{ display: 'flex', gap: 1 }}>
        <TextField
          size="small"
          label="Amb. mín"
          type="number"
          value={filters.bedrooms_min ?? ''}
          onChange={(e) =>
            setFilters({ ...filters, bedrooms_min: e.target.value ? Number(e.target.value) : undefined })
          }
          fullWidth
        />
        <TextField
          size="small"
          label="Baños mín"
          type="number"
          value={filters.bathrooms_min ?? ''}
          onChange={(e) =>
            setFilters({ ...filters, bathrooms_min: e.target.value ? Number(e.target.value) : undefined })
          }
          fullWidth
        />
      </Box>

      <TextField
        size="small"
        label="Barrio"
        value={filters.neighborhood || ''}
        onChange={(e) => setFilters({ ...filters, neighborhood: e.target.value || undefined })}
        fullWidth
      />

      <TextField
        size="small"
        label="Ciudad"
        value={filters.city || ''}
        onChange={(e) => setFilters({ ...filters, city: e.target.value || undefined })}
        fullWidth
      />

      <Divider />

      <FormControlLabel
        control={
          <Switch
            checked={showChoropleth}
            onChange={(e) => onToggleChoropleth(e.target.checked)}
            size="small"
          />
        }
        label="Mapa de precios"
      />

      {showChoropleth && (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          <Box>
            <Typography variant="caption" color="text.secondary" display="block" mb={0.5}>
              Granularidad
            </Typography>
            <ToggleButtonGroup
              value={choroplethGranularity}
              exclusive
              onChange={(_e, val: 'manzana' | 'barrio') => { if (val) onGranularityChange(val); }}
              size="small"
              fullWidth
            >
              <ToggleButton value="barrio">Barrio</ToggleButton>
              <ToggleButton value="manzana">Cuadra</ToggleButton>
            </ToggleButtonGroup>
          </Box>

          <Box>
            <Typography variant="caption" color="text.secondary" display="block" mb={0.5}>
              Ambientes
            </Typography>
            <ToggleButtonGroup
              value={choroplethAmbientes ?? 0}
              exclusive
              onChange={(_e, val: number) => onAmbientesChange(val === 0 ? null : val)}
              size="small"
              fullWidth
            >
              <ToggleButton value={0}>Todos</ToggleButton>
              <ToggleButton value={1}>1</ToggleButton>
              <ToggleButton value={2}>2</ToggleButton>
              <ToggleButton value={3}>3</ToggleButton>
              <ToggleButton value={4}>4+</ToggleButton>
            </ToggleButtonGroup>
          </Box>
        </Box>
      )}

      <Divider />

      <Box sx={{ display: 'flex', gap: 1 }}>
        <Button variant="contained" size="small" onClick={handleApply} fullWidth>
          Aplicar
        </Button>
        <Button variant="outlined" size="small" onClick={handleClear} startIcon={<ClearIcon />} fullWidth>
          Limpiar
        </Button>
      </Box>
    </Paper>
  );
}
