/**
 * Property Map - Main page component
 * Interactive map with markers, clustering, filters, and heatmap
 */
import { useState } from 'react';
import { Box, CircularProgress, Typography, Alert } from '@mui/material';
import { MapContainer, TileLayer } from 'react-leaflet';
import MarkerClusterGroup from 'react-leaflet-cluster';
import 'leaflet/dist/leaflet.css';

import type { PropertyFilters } from '../../../api/properties';
import { useMapProperties } from '../../../hooks/useMapProperties';
import MapFilterPanel from './MapFilterPanel';
import PropertyMarker from './PropertyMarker';
import HeatmapLayer from './HeatmapLayer';

// Buenos Aires center
const DEFAULT_CENTER: [number, number] = [-34.6037, -58.3816];
const DEFAULT_ZOOM = 12;

export default function PropertyMap() {
  const [filters, setFilters] = useState<PropertyFilters>({});
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [heatmapMetric, setHeatmapMetric] = useState<'price' | 'price_per_sqm'>('price');

  const { data, isLoading, error } = useMapProperties(filters);

  const properties = data?.items || [];

  return (
    <Box sx={{ display: 'flex', height: 'calc(100vh - 112px)', gap: 2 }}>
      <MapFilterPanel
        filters={filters}
        onApply={setFilters}
        totalResults={data?.total || 0}
        showHeatmap={showHeatmap}
        onToggleHeatmap={setShowHeatmap}
        heatmapMetric={heatmapMetric}
        onHeatmapMetricChange={setHeatmapMetric}
      />

      <Box sx={{ flex: 1, position: 'relative', borderRadius: 1, overflow: 'hidden' }}>
        {isLoading && (
          <Box
            sx={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              zIndex: 1000,
              bgcolor: 'rgba(255,255,255,0.8)',
              p: 3,
              borderRadius: 2,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 1,
            }}
          >
            <CircularProgress />
            <Typography>Cargando propiedades...</Typography>
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ position: 'absolute', top: 10, left: 10, zIndex: 1000 }}>
            Error cargando propiedades
          </Alert>
        )}

        <MapContainer
          center={DEFAULT_CENTER}
          zoom={DEFAULT_ZOOM}
          style={{ width: '100%', height: '100%' }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {!showHeatmap && (
            <MarkerClusterGroup key={JSON.stringify(filters)} chunkedLoading>
              {properties.map((prop) => (
                <PropertyMarker key={prop.id} property={prop} />
              ))}
            </MarkerClusterGroup>
          )}

          <HeatmapLayer
            properties={properties}
            metric={heatmapMetric}
            visible={showHeatmap}
          />
        </MapContainer>
      </Box>
    </Box>
  );
}
