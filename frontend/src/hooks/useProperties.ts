import { useQuery } from '@tanstack/react-query';
import { propertiesApi, type PropertyListResponse } from '../api/properties';

/**
 * Hook para obtener lista de propiedades con React Query
 * Comparte caché automáticamente entre componentes que usan la misma queryKey
 *
 * @param skip - Número de registros a saltar (paginación)
 * @param limit - Número de registros a traer
 * @returns Query con datos, loading state, error y función refetch
 */
export const useProperties = (skip: number = 0, limit: number = 50) => {
  return useQuery<PropertyListResponse>({
    queryKey: ['properties', skip, limit],
    queryFn: () => propertiesApi.listProperties(skip, limit),
    staleTime: 5 * 60 * 1000, // 5 minutos - datos considerados frescos
    gcTime: 10 * 60 * 1000,   // 10 minutos - tiempo en caché antes de garbage collection
  });
};
