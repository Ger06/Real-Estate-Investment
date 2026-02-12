/**
 * React Query hook for map properties
 */
import { useQuery } from '@tanstack/react-query';
import { propertiesApi } from '../api/properties';
import type { PropertyFilters } from '../api/properties';

export function useMapProperties(filters: PropertyFilters) {
  return useQuery({
    queryKey: ['properties-map', filters],
    queryFn: () => propertiesApi.listPropertiesForMap(filters),
    staleTime: 30_000,
  });
}
