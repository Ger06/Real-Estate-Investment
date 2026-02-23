/**
 * Property marker with popup and inline editing.
 *
 * Critical architecture: PopupContent is a SEPARATE component so that editing
 * state changes (typing, toggling edit mode) only re-render the inner content,
 * NOT the Marker/Popup wrappers. This prevents react-leaflet from calling
 * Leaflet's popup.update(), which would collapse spiderfied clusters and
 * cause flicker/focus loss on every keystroke.
 */
import React, { useState, useCallback } from 'react';
import { Marker, Popup } from 'react-leaflet';
import L, { Icon } from 'leaflet';
import {
  Box,
  Typography,
  TextField,
  Select,
  MenuItem,
  Button,
  Chip,
  FormControl,
} from '@mui/material';
import { Edit as EditIcon, Save as SaveIcon, Close as CloseIcon, OpenInNew as OpenInNewIcon, Refresh as RefreshIcon } from '@mui/icons-material';
import type { PropertyMapItem, PropertyUpdateData } from '../../../api/properties';
import { propertiesApi } from '../../../api/properties';
import { useQueryClient } from '@tanstack/react-query';

// Fix Leaflet default icon paths for bundlers (known Vite/Webpack issue)
delete (Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl;
Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const statusColors: Record<string, string> = {
  ACTIVE: '#4caf50',
  SOLD: '#f44336',
  RENTED: '#ff9800',
  RESERVED: '#2196f3',
  REMOVED: '#9e9e9e',
};

const statusLabels: Record<string, string> = {
  ACTIVE: 'Activo',
  SOLD: 'Vendido',
  RENTED: 'Alquilado',
  RESERVED: 'Reservado',
  REMOVED: 'Removido',
};

const typeLabels: Record<string, string> = {
  departamento: 'Depto',
  casa: 'Casa',
  ph: 'PH',
  terreno: 'Terreno',
  local: 'Local',
  oficina: 'Oficina',
};

function formatPrice(price: number, currency: string): string {
  return `${currency} ${price.toLocaleString('es-AR', { maximumFractionDigits: 0 })}`;
}

/**
 * Inner popup content — owns all editing state.
 * Re-renders here do NOT propagate to Marker/Popup.
 */
function PopupContent({ property }: { property: PropertyMapItem }) {
  const [editing, setEditing] = useState(false);
  const [editPrice, setEditPrice] = useState(String(property.price));
  const [editStatus, setEditStatus] = useState(property.status);
  const [editObservations, setEditObservations] = useState(property.observations || '');
  const [editCoords, setEditCoords] = useState(
    `${property.latitude}, ${property.longitude}`
  );
  const [saving, setSaving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const queryClient = useQueryClient();

  // Callback ref: fires once when the DOM element mounts.
  // Sets up Leaflet event blocking so clicks/scrolls don't reach the map.
  const containerRef = useCallback((el: HTMLDivElement | null) => {
    if (el) {
      L.DomEvent.disableClickPropagation(el);
      L.DomEvent.disableScrollPropagation(el);
    }
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const data: PropertyUpdateData = {};
      const newPrice = Number(editPrice);
      if (!isNaN(newPrice) && newPrice !== property.price) data.price = newPrice;
      if (editStatus !== property.status) data.status = editStatus;
      if (editObservations !== (property.observations || '')) data.observations = editObservations;
      const coordParts = editCoords.split(',').map(s => s.trim());
      if (coordParts.length === 2) {
        const newLat = Number(coordParts[0]);
        const newLng = Number(coordParts[1]);
        if (!isNaN(newLat) && !isNaN(newLng) &&
            (newLat !== property.latitude || newLng !== property.longitude)) {
          data.latitude = newLat;
          data.longitude = newLng;
        }
      }

      if (Object.keys(data).length > 0) {
        await propertiesApi.updateProperty(property.id, data);
        // Optimistic cache update: patch only the changed property
        // instead of invalidating, which would refetch and destroy popups/spiderfy
        queryClient.setQueriesData<{ items: PropertyMapItem[]; total: number }>(
          { queryKey: ['properties-map'] },
          (old) => {
            if (!old) return old;
            return {
              ...old,
              items: old.items.map((p) =>
                p.id === property.id ? { ...p, ...data } : p
              ),
            };
          }
        );
      }
      setEditing(false);
    } catch (err) {
      console.error('Error updating property:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleRescrape = async () => {
    setRefreshing(true);
    try {
      const result = await propertiesApi.rescrapeProperty(property.id);
      if (result.success) {
        const newStatus = result.new_status.toUpperCase();
        queryClient.setQueriesData<{ items: PropertyMapItem[]; total: number }>(
          { queryKey: ['properties-map'] },
          (old) => {
            if (!old) return old;
            return {
              ...old,
              items: old.items.map((p) =>
                p.id === property.id
                  ? {
                      ...p,
                      price: result.new_price,
                      status: newStatus,
                      scraped_at: new Date().toISOString(),
                    }
                  : p
              ),
            };
          }
        );
      }
    } catch (err) {
      console.error('Error rescraping property:', err);
    } finally {
      setRefreshing(false);
    }
  };

  const handleCancel = () => {
    setEditPrice(String(property.price));
    setEditStatus(property.status);
    setEditObservations(property.observations || '');
    setEditCoords(`${property.latitude}, ${property.longitude}`);
    setEditing(false);
  };

  return (
    <div
      ref={containerRef}
      onMouseDown={(e) => e.stopPropagation()}
      onClick={(e) => e.stopPropagation()}
      onDoubleClick={(e) => e.stopPropagation()}
    >
      <Box sx={{ p: 0.5 }}>
        {property.primary_image_url && (
          <Box
            component="img"
            src={property.primary_image_url}
            alt={property.title}
            sx={{
              width: '100%',
              height: 120,
              objectFit: 'cover',
              borderRadius: 1,
              mb: 1,
            }}
          />
        )}

        <Typography variant="subtitle2" sx={{ fontWeight: 'bold', lineHeight: 1.3, mb: 0.5 }}>
          {property.title}
        </Typography>

        <Box sx={{ display: 'flex', gap: 0.5, mb: 0.5, flexWrap: 'wrap' }}>
          <Chip
            label={typeLabels[property.property_type] || property.property_type}
            size="small"
            variant="outlined"
          />
          <Chip
            label={statusLabels[property.status] || property.status}
            size="small"
            sx={{
              backgroundColor: statusColors[property.status] || '#9e9e9e',
              color: 'white',
            }}
          />
        </Box>

        {!editing ? (
          <>
            <Typography variant="h6" color="primary" sx={{ fontWeight: 'bold', mb: 0.5 }}>
              {formatPrice(property.price, property.currency)}
            </Typography>

            {property.address && (
              <Typography variant="body2" color="text.secondary" sx={{ mb: 0.3 }}>
                {property.address}
              </Typography>
            )}

            <Box sx={{ display: 'flex', gap: 1.5, mb: 0.5 }}>
              {property.total_area && (
                <Typography variant="body2">{property.total_area} m²</Typography>
              )}
              {property.bedrooms != null && (
                <Typography variant="body2">{property.bedrooms} amb</Typography>
              )}
              {property.bathrooms != null && (
                <Typography variant="body2">{property.bathrooms} baños</Typography>
              )}
            </Box>

            {property.price_per_sqm && (
              <Typography variant="body2" color="text.secondary">
                {formatPrice(property.price_per_sqm, property.currency)}/m²
              </Typography>
            )}

            {property.last_price_change && (
              <Typography variant="body2" sx={{ mt: 0.5 }}>
                Últ. precio:{' '}
                {new Date(property.last_price_change.changed_at).toLocaleDateString('es-AR')}{' '}
                <Box
                  component="span"
                  sx={{
                    color: property.last_price_change.change_pct < 0 ? 'error.main' : 'success.main',
                    fontWeight: 'bold',
                  }}
                >
                  {property.last_price_change.change_pct > 0 ? '+' : ''}
                  {property.last_price_change.change_pct.toFixed(1)}%
                </Box>
              </Typography>
            )}

            {property.scraped_at && (
              <Typography variant="body2" color="text.secondary">
                Verificado: {new Date(property.scraped_at).toLocaleDateString('es-AR')}
              </Typography>
            )}

            {property.observations && (
              <Typography variant="body2" sx={{ mt: 0.5, fontStyle: 'italic', color: 'text.secondary' }}>
                {property.observations}
              </Typography>
            )}

            <Box sx={{ display: 'flex', gap: 1, mt: 1, flexWrap: 'wrap' }}>
              {property.source_url && (
                <Button
                  size="small"
                  startIcon={<OpenInNewIcon />}
                  href={property.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Publicación
                </Button>
              )}
              <Button
                size="small"
                startIcon={<RefreshIcon />}
                onClick={handleRescrape}
                disabled={refreshing || !property.source_url}
              >
                {refreshing ? 'Actualizando...' : 'Actualizar'}
              </Button>
              <Button
                size="small"
                startIcon={<EditIcon />}
                onClick={() => setEditing(true)}
              >
                Editar
              </Button>
            </Box>
          </>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mt: 1 }}>
            <TextField
              size="small"
              label="Precio"
              type="number"
              value={editPrice}
              onChange={(e) => setEditPrice(e.target.value)}
              fullWidth
            />

            <FormControl size="small" fullWidth>
              <Select
                value={editStatus}
                onChange={(e) => setEditStatus(e.target.value)}
                MenuProps={{ disablePortal: true }}
              >
                <MenuItem value="ACTIVE">Activo</MenuItem>
                <MenuItem value="SOLD">Vendido</MenuItem>
                <MenuItem value="RENTED">Alquilado</MenuItem>
                <MenuItem value="RESERVED">Reservado</MenuItem>
                <MenuItem value="REMOVED">Removido</MenuItem>
              </Select>
            </FormControl>

            <TextField
              size="small"
              label="Observaciones"
              value={editObservations}
              onChange={(e) => setEditObservations(e.target.value)}
              multiline
              rows={2}
              fullWidth
            />

            <TextField
              size="small"
              label="Coordenadas (lat, lng)"
              placeholder="-34.5600, -58.4803"
              value={editCoords}
              onChange={(e) => setEditCoords(e.target.value)}
              fullWidth
            />

            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button
                size="small"
                variant="contained"
                startIcon={<SaveIcon />}
                onClick={handleSave}
                disabled={saving}
                fullWidth
              >
                {saving ? 'Guardando...' : 'Guardar'}
              </Button>
              <Button
                size="small"
                variant="outlined"
                startIcon={<CloseIcon />}
                onClick={handleCancel}
                disabled={saving}
                fullWidth
              >
                Cancelar
              </Button>
            </Box>
          </Box>
        )}
      </Box>
    </div>
  );
}

/**
 * Outer marker — only re-renders when the property object reference changes.
 * Editing state lives in PopupContent, so typing/toggling edit mode
 * never triggers Marker/Popup re-renders.
 */
interface PropertyMarkerProps {
  property: PropertyMapItem;
}

export default React.memo(function PropertyMarker({ property }: PropertyMarkerProps) {
  return (
    <Marker position={[property.latitude, property.longitude]}>
      <Popup closeOnClick={false} autoClose={false} minWidth={280}>
        <PopupContent property={property} />
      </Popup>
    </Marker>
  );
});
