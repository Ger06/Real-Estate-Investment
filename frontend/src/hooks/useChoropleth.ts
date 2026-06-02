import { useQuery } from '@tanstack/react-query';
import { propertiesApi } from '../api/properties';
import type { ChoroplethFilters } from '../api/properties';

export function useChoropleth(filters: ChoroplethFilters, enabled: boolean) {
  return useQuery({
    queryKey: ['choropleth', filters],
    queryFn: () => propertiesApi.getChoropleth(filters),
    staleTime: 5 * 60_000,
    enabled,
  });
}
