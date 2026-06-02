/**
 * Property Map - Main page component
 * Interactive map with markers, clustering, filters, and choropleth
 */
import { useState } from 'react';
import { Box, CircularProgress, Typography, Alert } from '@mui/material';
import { MapContainer, TileLayer } from 'react-leaflet';
import MarkerClusterGroup from 'react-leaflet-cluster';
import 'leaflet/dist/leaflet.css';

import type { PropertyFilters, ChoroplethFilters } from '../../../api/properties';
import { useMapProperties } from '../../../hooks/useMapProperties';
import { useChoropleth } from '../../../hooks/useChoropleth';
import MapFilterPanel from './MapFilterPanel';
import PropertyMarker from './PropertyMarker';
import ChoroplethLayer from './ChoroplethLayer';
import ChoroplethLegend from './ChoroplethLegend';

// Buenos Aires center
const DEFAULT_CENTER: [number, number] = [-34.6037, -58.3816];
const DEFAULT_ZOOM = 12;

export default function PropertyMap() {
  const [filters, setFilters] = useState<PropertyFilters>({});
  const [showChoropleth, setShowChoropleth] = useState(false);
  const [choroplethAmbientes, setChoroplethAmbientes] = useState<number | null>(null);

  const { data, isLoading, error } = useMapProperties(filters);

  const choroplethFilters: ChoroplethFilters = {
    property_type: filters.property_type,
    ambientes: choroplethAmbientes ?? undefined,
  };

  const { data: choroplethData } = useChoropleth(choroplethFilters, showChoropleth);

  const properties = data?.items || [];

  return (
    <Box sx={{ display: 'flex', height: 'calc(100vh - 112px)', gap: 2 }}>
      <MapFilterPanel
        filters={filters}
        onApply={setFilters}
        totalResults={data?.total || 0}
        showChoropleth={showChoropleth}
        onToggleChoropleth={setShowChoropleth}
        choroplethAmbientes={choroplethAmbientes}
        onAmbientesChange={setChoroplethAmbientes}
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

          {showChoropleth && choroplethData && (
            <ChoroplethLayer data={choroplethData} />
          )}

          <MarkerClusterGroup key={JSON.stringify(filters)} chunkedLoading>
            {properties.map((prop) => (
              <PropertyMarker key={prop.id} property={prop} />
            ))}
          </MarkerClusterGroup>
        </MapContainer>

        {showChoropleth && choroplethData && (
          <ChoroplethLegend colorScale={choroplethData.color_scale} />
        )}
      </Box>
    </Box>
  );
}
