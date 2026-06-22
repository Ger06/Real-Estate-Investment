/**
 * Choropleth layer - colors CABA city blocks by avg price/m² (USD)
 */
import { useEffect, useRef } from 'react';
import { useMap } from 'react-leaflet';
import type { Layer, PathOptions } from 'leaflet';
import L from 'leaflet';
import type { ChoroplethResponse, ChoroplethFeatureProperties } from '../../../api/properties';

const COLOR_MAP: Record<number, string> = {
  1: '#1a9641',
  2: '#74c476',
  3: '#d9ef8b',
  4: '#fee08b',
  5: '#fdae61',
  6: '#f46d43',
  7: '#d73027',
  8: '#a50026',
};

interface Props {
  data: ChoroplethResponse;
}

export default function ChoroplethLayer({ data }: Props) {
  const map = useMap();
  const layerRef = useRef<L.GeoJSON | null>(null);

  useEffect(() => {
    if (layerRef.current) {
      map.removeLayer(layerRef.current);
      layerRef.current = null;
    }

    if (!data || !data.features.length) return;

    const geoJsonLayer = L.geoJSON(data as any, {
      style(feature): PathOptions {
        const props = feature?.properties as ChoroplethFeatureProperties;
        const color = COLOR_MAP[props?.color_level] ?? '#cccccc';
        return {
          fillColor: color,
          fillOpacity: 0.65,
          color: '#555',
          weight: 0.5,
        };
      },
      onEachFeature(feature, layer: Layer) {
        const props = feature.properties as ChoroplethFeatureProperties;
        const barrio = props.barrio ?? 'Sin barrio';
        const avg = props.avg_price_per_sqm
          ? `USD ${props.avg_price_per_sqm.toLocaleString('es-AR')}/m²`
          : 'Sin datos';
        const count = props.property_count;
        (layer as L.Path).bindTooltip(
          `<strong>${barrio}</strong><br/>${avg}<br/>${count} propiedad${count !== 1 ? 'es' : ''}`,
          { sticky: true }
        );
      },
    });

    geoJsonLayer.addTo(map);
    layerRef.current = geoJsonLayer;

    return () => {
      if (layerRef.current) {
        map.removeLayer(layerRef.current);
        layerRef.current = null;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, map]);

  return null;
}
