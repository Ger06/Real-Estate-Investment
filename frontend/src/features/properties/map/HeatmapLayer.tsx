/**
 * Heatmap layer for the property map using leaflet.heat
 */
import { useEffect } from 'react';
import { useMap } from 'react-leaflet';
import * as L from 'leaflet';
import 'leaflet.heat';
import type { PropertyMapItem } from '../../../api/properties';

interface HeatmapLayerProps {
  properties: PropertyMapItem[];
  metric: 'price' | 'price_per_sqm';
  visible: boolean;
}

export default function HeatmapLayer({ properties, metric, visible }: HeatmapLayerProps) {
  const map = useMap();

  useEffect(() => {
    if (!visible || properties.length === 0) return;

    const values = properties
      .map((p) => (metric === 'price_per_sqm' ? p.price_per_sqm : p.price))
      .filter((v): v is number => v != null && v > 0);

    if (values.length === 0) return;

    const maxVal = Math.max(...values);
    const minVal = Math.min(...values);
    const range = maxVal - minVal || 1;

    const points: [number, number, number][] = properties
      .filter((p) => {
        const val = metric === 'price_per_sqm' ? p.price_per_sqm : p.price;
        return val != null && val > 0;
      })
      .map((p) => {
        const val = (metric === 'price_per_sqm' ? p.price_per_sqm : p.price)!;
        const intensity = (val - minVal) / range;
        return [p.latitude, p.longitude, intensity];
      });

    const heat = L.heatLayer(points, {
      radius: 25,
      blur: 15,
      maxZoom: 17,
      max: 1.0,
      gradient: {
        0.0: '#3288bd',
        0.25: '#66c2a5',
        0.5: '#fee08b',
        0.75: '#f46d43',
        1.0: '#d53e4f',
      },
    });

    heat.addTo(map);

    return () => {
      map.removeLayer(heat);
    };
  }, [map, properties, metric, visible]);

  return null;
}
