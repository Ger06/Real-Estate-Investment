import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  savedSearchesApi,
  type SavedSearchListResponse,
  type SavedSearch,
  type SavedSearchCreate,
  type SavedSearchUpdate,
  type SavedSearchExecuteResponse,
  type PendingPropertyListResponse,
  type PendingPropertyStats,
  type PendingPropertyScrapeResponse,
  type PendingPropertyActionResponse,
} from '../api/savedSearches';

// ── Queries ─────────────────────────────────────────────────────────

export const useSavedSearches = (skip: number = 0, limit: number = 50) => {
  return useQuery<SavedSearchListResponse>({
    queryKey: ['savedSearches', skip, limit],
    queryFn: () => savedSearchesApi.list(skip, limit),
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
};

export const useSavedSearch = (id: string) => {
  return useQuery<SavedSearch>({
    queryKey: ['savedSearch', id],
    queryFn: () => savedSearchesApi.get(id),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
};

export const usePendingProperties = (
  skip: number = 0,
  limit: number = 50,
  search_id?: string,
  status_filter?: string,
  portal?: string
) => {
  return useQuery<PendingPropertyListResponse>({
    queryKey: ['pendingProperties', skip, limit, search_id, status_filter, portal],
    queryFn: () => savedSearchesApi.listPending(skip, limit, search_id, status_filter, portal),
    staleTime: 2 * 60 * 1000,
    gcTime: 5 * 60 * 1000,
  });
};

export const usePendingStats = () => {
  return useQuery<PendingPropertyStats>({
    queryKey: ['pendingStats'],
    queryFn: () => savedSearchesApi.getPendingStats(),
    staleTime: 2 * 60 * 1000,
    gcTime: 5 * 60 * 1000,
  });
};

// ── Mutations ───────────────────────────────────────────────────────

export const useCreateSearch = () => {
  const queryClient = useQueryClient();
  return useMutation<SavedSearch, Error, SavedSearchCreate>({
    mutationFn: (data) => savedSearchesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['savedSearches'] });
    },
  });
};

export const useUpdateSearch = () => {
  const queryClient = useQueryClient();
  return useMutation<SavedSearch, Error, { id: string; data: SavedSearchUpdate }>({
    mutationFn: ({ id, data }) => savedSearchesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['savedSearches'] });
      queryClient.invalidateQueries({ queryKey: ['savedSearch'] });
    },
  });
};

export const useDeleteSearch = () => {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (id) => savedSearchesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['savedSearches'] });
    },
  });
};

export const useExecuteSearch = () => {
  const queryClient = useQueryClient();
  return useMutation<SavedSearchExecuteResponse, Error, { id: string; max_properties?: number }>({
    mutationFn: ({ id, max_properties }) => savedSearchesApi.execute(id, max_properties),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['savedSearches'] });
      queryClient.invalidateQueries({ queryKey: ['pendingProperties'] });
      queryClient.invalidateQueries({ queryKey: ['pendingStats'] });
    },
  });
};

export const useToggleSearch = () => {
  const queryClient = useQueryClient();
  return useMutation<SavedSearch, Error, string>({
    mutationFn: (id) => savedSearchesApi.toggle(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['savedSearches'] });
      queryClient.invalidateQueries({ queryKey: ['savedSearch'] });
    },
  });
};

export const useScrapeBatch = () => {
  const queryClient = useQueryClient();
  return useMutation<PendingPropertyScrapeResponse, Error, { search_id?: string; limit?: number }>({
    mutationFn: ({ search_id, limit }) => savedSearchesApi.scrapeBatch(search_id, limit),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pendingProperties'] });
      queryClient.invalidateQueries({ queryKey: ['pendingStats'] });
      queryClient.invalidateQueries({ queryKey: ['savedSearches'] });
      queryClient.invalidateQueries({ queryKey: ['properties'] });
    },
  });
};

export const useScrapeSingle = () => {
  const queryClient = useQueryClient();
  return useMutation<PendingPropertyActionResponse, Error, string>({
    mutationFn: (id) => savedSearchesApi.scrapeSingle(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pendingProperties'] });
      queryClient.invalidateQueries({ queryKey: ['pendingStats'] });
      queryClient.invalidateQueries({ queryKey: ['savedSearches'] });
      queryClient.invalidateQueries({ queryKey: ['properties'] });
    },
  });
};

export const useSkipPending = () => {
  const queryClient = useQueryClient();
  return useMutation<PendingPropertyActionResponse, Error, string>({
    mutationFn: (id) => savedSearchesApi.skipPending(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pendingProperties'] });
      queryClient.invalidateQueries({ queryKey: ['pendingStats'] });
      queryClient.invalidateQueries({ queryKey: ['savedSearches'] });
    },
  });
};

export const useDeletePending = () => {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (id) => savedSearchesApi.deletePending(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pendingProperties'] });
      queryClient.invalidateQueries({ queryKey: ['pendingStats'] });
      queryClient.invalidateQueries({ queryKey: ['savedSearches'] });
    },
  });
};

export const useClearErrors = () => {
  const queryClient = useQueryClient();
  return useMutation<{ success: boolean; cleared: number }, Error, string | undefined>({
    mutationFn: (search_id) => savedSearchesApi.clearErrors(search_id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pendingProperties'] });
      queryClient.invalidateQueries({ queryKey: ['pendingStats'] });
    },
  });
};
