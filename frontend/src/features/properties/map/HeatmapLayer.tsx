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
  metric: 'price' | 'price_per_sqm' | 'price_change';
  visible: boolean;
  priceChangeDays: number | null;
}

export default function HeatmapLayer({ properties, metric, visible, priceChangeDays }: HeatmapLayerProps) {
  const map = useMap();

  useEffect(() => {
    if (!visible || properties.length === 0) return;

    let points: [number, number, number][];

    if (metric === 'price_change') {
      const cutoff = priceChangeDays
        ? new Date(Date.now() - priceChangeDays * 86_400_000)
        : null;

      const filtered = properties.filter((p) => {
        if (!p.last_price_change) return false;
        if (!cutoff) return true;
        return new Date(p.last_price_change.changed_at) >= cutoff;
      });

      if (filtered.length === 0) return;

      const values = filtered.map((p) => Math.abs(p.last_price_change!.change_pct));
      const maxVal = Math.max(...values) || 1;
      const minVal = Math.min(...values);
      const range = maxVal - minVal || 1;

      points = filtered.map((p) => {
        const intensity = (Math.abs(p.last_price_change!.change_pct) - minVal) / range;
        return [p.latitude, p.longitude, intensity];
      });
    } else {
      const values = properties
        .map((p) => (metric === 'price_per_sqm' ? p.price_per_sqm : p.price))
        .filter((v): v is number => v != null && v > 0);

      if (values.length === 0) return;

      const maxVal = Math.max(...values);
      const minVal = Math.min(...values);
      const range = maxVal - minVal || 1;

      points = properties
        .filter((p) => {
          const val = metric === 'price_per_sqm' ? p.price_per_sqm : p.price;
          return val != null && val > 0;
        })
        .map((p) => {
          const val = (metric === 'price_per_sqm' ? p.price_per_sqm : p.price)!;
          const intensity = (val - minVal) / range;
          return [p.latitude, p.longitude, intensity];
        });
    }

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
  }, [map, properties, metric, visible, priceChangeDays]);

  return null;
}
