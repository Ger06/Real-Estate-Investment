/**
 * Saved Searches & Pending Properties API
 */
import { apiClient } from './client';

// ── Saved Search Types ──────────────────────────────────────────────

export interface SavedSearch {
  id: string;
  user_id?: string;
  name: string;
  description?: string;
  portals: string[];
  property_type?: string;
  operation_type: string;
  city?: string;
  neighborhoods?: string[];
  province?: string;
  min_price?: number;
  max_price?: number;
  currency: string;
  min_area?: number;
  max_area?: number;
  min_bedrooms?: number;
  max_bedrooms?: number;
  min_bathrooms?: number;
  auto_scrape: boolean;
  is_active: boolean;
  last_executed_at?: string;
  total_executions: number;
  total_properties_found: number;
  pending_count: number;
  created_at: string;
  updated_at?: string;
}

export interface SavedSearchCreate {
  name: string;
  description?: string;
  portals: string[];
  property_type?: string;
  operation_type: string;
  city?: string;
  neighborhoods?: string[];
  province?: string;
  min_price?: number;
  max_price?: number;
  currency?: string;
  min_area?: number;
  max_area?: number;
  min_bedrooms?: number;
  max_bedrooms?: number;
  min_bathrooms?: number;
  auto_scrape?: boolean;
  is_active?: boolean;
}

export interface SavedSearchUpdate {
  name?: string;
  description?: string;
  portals?: string[];
  property_type?: string;
  operation_type?: string;
  city?: string;
  neighborhoods?: string[];
  province?: string;
  min_price?: number | null;
  max_price?: number | null;
  currency?: string;
  min_area?: number | null;
  max_area?: number | null;
  min_bedrooms?: number | null;
  max_bedrooms?: number | null;
  min_bathrooms?: number | null;
  auto_scrape?: boolean;
  is_active?: boolean;
}

export interface SavedSearchListResponse {
  total: number;
  skip: number;
  limit: number;
  items: SavedSearch[];
}

export interface SavedSearchExecuteResponse {
  success: boolean;
  search_id: string;
  search_name: string;
  total_found: number;
  new_properties: number;
  duplicates: number;
  scraped: number;
  pending: number;
  errors: Array<Record<string, unknown>>;
}

// ── Pending Property Types ──────────────────────────────────────────

export interface PendingProperty {
  id: string;
  saved_search_id: string;
  source_url: string;
  source: string;
  source_id?: string;
  title?: string;
  price?: number;
  currency?: string;
  thumbnail_url?: string;
  location_preview?: string;
  status: string;
  error_message?: string;
  property_id?: string;
  discovered_at: string;
  scraped_at?: string;
  updated_at?: string;
  saved_search_name?: string;
}

export interface PendingPropertyListResponse {
  total: number;
  skip: number;
  limit: number;
  items: PendingProperty[];
}

export interface PendingPropertyStats {
  total_pending: number;
  total_scraped: number;
  total_skipped: number;
  total_errors: number;
  by_search: Array<Record<string, unknown>>;
  by_portal: Array<Record<string, unknown>>;
}

export interface PendingPropertyScrapeResponse {
  success: boolean;
  scraped: number;
  errors: number;
  error_details: Array<Record<string, unknown>>;
}

export interface PendingPropertyActionResponse {
  success: boolean;
  message: string;
  pending_id: string;
  property_id?: string;
}

// ── API Client ──────────────────────────────────────────────────────

export const savedSearchesApi = {
  // Saved Searches
  list: async (skip: number = 0, limit: number = 50, active_only?: boolean): Promise<SavedSearchListResponse> => {
    const response = await apiClient.get<SavedSearchListResponse>('/saved-searches/', {
      params: { skip, limit, ...(active_only !== undefined && { active_only }) },
    });
    return response.data;
  },

  get: async (id: string): Promise<SavedSearch> => {
    const response = await apiClient.get<SavedSearch>(`/saved-searches/${id}`);
    return response.data;
  },

  create: async (data: SavedSearchCreate): Promise<SavedSearch> => {
    const response = await apiClient.post<SavedSearch>('/saved-searches/', data);
    return response.data;
  },

  update: async (id: string, data: SavedSearchUpdate): Promise<SavedSearch> => {
    const response = await apiClient.put<SavedSearch>(`/saved-searches/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/saved-searches/${id}`);
  },

  execute: async (id: string, max_properties?: number): Promise<SavedSearchExecuteResponse> => {
    const response = await apiClient.post<SavedSearchExecuteResponse>(
      `/saved-searches/${id}/execute`,
      null,
      { params: max_properties !== undefined ? { max_properties } : {} }
    );
    return response.data;
  },

  toggle: async (id: string): Promise<SavedSearch> => {
    const response = await apiClient.post<SavedSearch>(`/saved-searches/${id}/toggle`);
    return response.data;
  },

  // Pending Properties
  listPending: async (
    skip: number = 0,
    limit: number = 50,
    search_id?: string,
    status_filter?: string,
    portal?: string
  ): Promise<PendingPropertyListResponse> => {
    const response = await apiClient.get<PendingPropertyListResponse>('/pending-properties/', {
      params: {
        skip,
        limit,
        ...(search_id && { search_id }),
        ...(status_filter && { status_filter }),
        ...(portal && { portal }),
      },
    });
    return response.data;
  },

  getPendingStats: async (): Promise<PendingPropertyStats> => {
    const response = await apiClient.get<PendingPropertyStats>('/pending-properties/stats');
    return response.data;
  },

  scrapeBatch: async (search_id?: string, limit: number = 50): Promise<PendingPropertyScrapeResponse> => {
    const response = await apiClient.post<PendingPropertyScrapeResponse>('/pending-properties/scrape', {
      ...(search_id && { search_id }),
      limit,
    });
    return response.data;
  },

  scrapeSingle: async (id: string): Promise<PendingPropertyActionResponse> => {
    const response = await apiClient.post<PendingPropertyActionResponse>(`/pending-properties/${id}/scrape`);
    return response.data;
  },

  skipPending: async (id: string): Promise<PendingPropertyActionResponse> => {
    const response = await apiClient.post<PendingPropertyActionResponse>(`/pending-properties/${id}/skip`);
    return response.data;
  },

  deletePending: async (id: string): Promise<void> => {
    await apiClient.delete(`/pending-properties/${id}`);
  },

  clearErrors: async (search_id?: string): Promise<{ success: boolean; cleared: number }> => {
    const response = await apiClient.post<{ success: boolean; cleared: number }>(
      '/pending-properties/clear-errors',
      null,
      { params: search_id ? { search_id } : {} }
    );
    return response.data;
  },
};
