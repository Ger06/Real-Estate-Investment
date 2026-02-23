import { useQuery } from '@tanstack/react-query';
import { propertiesApi, type PropertyFilters, type PropertyListResponse } from '../api/properties';

export const useProperties = (
  skip: number = 0,
  limit: number = 25,
  filters: PropertyFilters = {}
) => {
  return useQuery<PropertyListResponse>({
    queryKey: ['properties', skip, limit, filters],
    queryFn: () => propertiesApi.listProperties(skip, limit, filters),
    staleTime: 2 * 60 * 1000,
    gcTime: 5 * 60 * 1000,
  });
};
