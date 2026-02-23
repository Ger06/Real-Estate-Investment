/**
 * Properties API
 */
import { apiClient } from './client';

export interface PropertyScrapeRequest {
  url: string;
  save_to_db: boolean;
}

export interface PropertyScrapeResponse {
  success: boolean;
  message: string;
  data?: any;
  property_id?: string;
}

export interface Property {
  id: string;
  source: string;
  source_url?: string;
  source_id?: string;
  property_type: string;
  operation_type: string;
  title: string;
  description?: string;
  price: number;
  currency: string;
  price_per_sqm?: number;
  estimated_value?: number;
  address?: string;
  street?: string;
  street_number?: string;
  neighborhood?: string;
  city: string;
  province: string;
  postal_code?: string;
  covered_area?: number;
  semi_covered_area?: number;
  uncovered_area?: number;
  total_area?: number;
  floor_level?: number;
  bedrooms?: number;
  bathrooms?: number;
  parking_spaces?: number;
  amenities?: any;
  property_condition?: string;
  real_estate_agency?: string;
  contact_info?: any;
  observations?: string;
  status: string;
  scraped_at?: string;
  created_at: string;
  updated_at?: string;
  images: PropertyImage[];
  price_history: PriceHistoryEntry[];
}

export interface PropertyImage {
  id: string;
  url?: string;
  file_path?: string;
  is_primary: boolean;
  order: number;
  created_at: string;
}

export interface PriceHistoryEntry {
  id: string;
  price: number;
  previous_price?: number;
  currency: string;
  change_percentage?: number;
  recorded_at: string;
}

export interface LastPriceChange {
  previous_price: number;
  change_pct: number;
  changed_at: string;
}

export interface PropertyListResponse {
  total: number;
  skip: number;
  limit: number;
  items: Property[];
}

export interface UpdatePricesResponse {
  success: boolean;
  message: string;
  total_properties: number;
  updated_count: number;
  error_count: number;
  price_changes?: Array<{
    property_id: string;
    title: string;
    old_price: number;
    new_price: number;
    change_percentage: number;
  }>;
}

export interface RescrapeAllResponse {
  success: boolean;
  message: string;
  total_properties: number;
  updated_count: number;
  error_count: number;
  errors?: string[];
}

export interface PropertyFilters {
  source?: string;
  property_type?: string;
  operation_type?: string;
  status?: string;
  currency?: string;
  price_min?: number;
  price_max?: number;
  area_min?: number;
  area_max?: number;
  bedrooms_min?: number;
  bathrooms_min?: number;
  neighborhood?: string;
  city?: string;
  has_location?: boolean;
}

export interface PropertyMapItem {
  id: string;
  title: string;
  property_type: string;
  operation_type: string;
  price: number;
  currency: string;
  price_per_sqm?: number;
  total_area?: number;
  bedrooms?: number;
  bathrooms?: number;
  neighborhood?: string;
  city: string;
  address?: string;
  status: string;
  latitude: number;
  longitude: number;
  primary_image_url?: string;
  observations?: string;
  source_url?: string;
  scraped_at?: string;
  last_price_change?: LastPriceChange;
}

export interface PropertyMapResponse {
  total: number;
  items: PropertyMapItem[];
}

export interface RescrapePropertyResponse {
  success: boolean;
  old_price: number;
  new_price: number;
  price_changed: boolean;
  old_status: string;
  new_status: string;
  status_changed: boolean;
  error?: string;
}

export interface GeocodeResponse {
  success: boolean;
  message: string;
  total: number;
  geocoded: number;
  failed: number;
  failed_details?: Array<{
    id: string;
    title: string;
    address?: string;
    neighborhood?: string;
    error?: string;
  }>;
}

export interface PropertyUpdateData {
  price?: number;
  currency?: string;
  status?: string;
  observations?: string;
  latitude?: number;
  longitude?: number;
}

export const propertiesApi = {
  scrapeProperty: async (data: PropertyScrapeRequest): Promise<PropertyScrapeResponse> => {
    const response = await apiClient.post<PropertyScrapeResponse>('/properties/scrape', data);
    return response.data;
  },

  listProperties: async (
    skip: number = 0,
    limit: number = 25,
    filters: PropertyFilters = {}
  ): Promise<PropertyListResponse> => {
    const params: Record<string, string | number | boolean> = { skip, limit };
    if (filters.source) params.source = filters.source;
    if (filters.property_type) params.property_type = filters.property_type;
    if (filters.operation_type) params.operation_type = filters.operation_type;
    if (filters.status) params.status = filters.status;
    if (filters.currency) params.currency = filters.currency;
    if (filters.price_min != null) params.price_min = filters.price_min;
    if (filters.price_max != null) params.price_max = filters.price_max;
    if (filters.area_min != null) params.area_min = filters.area_min;
    if (filters.area_max != null) params.area_max = filters.area_max;
    if (filters.bedrooms_min != null) params.bedrooms_min = filters.bedrooms_min;
    if (filters.bathrooms_min != null) params.bathrooms_min = filters.bathrooms_min;
    if (filters.neighborhood) params.neighborhood = filters.neighborhood;
    if (filters.city) params.city = filters.city;
    const response = await apiClient.get<PropertyListResponse>('/properties/', { params });
    return response.data;
  },

  getProperty: async (id: string): Promise<Property> => {
    const response = await apiClient.get<Property>(`/properties/${id}`);
    return response.data;
  },

  updateAllPrices: async (portal?: string): Promise<UpdatePricesResponse> => {
    const params = portal ? { portal } : {};
    const response = await apiClient.post<UpdatePricesResponse>('/properties/update-prices', {}, { params });
    return response.data;
  },

  rescrapeAll: async (portal?: string): Promise<RescrapeAllResponse> => {
    const params = portal ? { portal } : {};
    const response = await apiClient.post<RescrapeAllResponse>('/properties/rescrape-all', {}, { params });
    return response.data;
  },

  listPropertiesForMap: async (filters: PropertyFilters = {}): Promise<PropertyMapResponse> => {
    const params: Record<string, string | number | boolean> = {};
    if (filters.property_type) params.property_type = filters.property_type;
    if (filters.operation_type) params.operation_type = filters.operation_type;
    if (filters.status) params.status = filters.status;
    if (filters.currency) params.currency = filters.currency;
    if (filters.price_min != null) params.price_min = filters.price_min;
    if (filters.price_max != null) params.price_max = filters.price_max;
    if (filters.area_min != null) params.area_min = filters.area_min;
    if (filters.area_max != null) params.area_max = filters.area_max;
    if (filters.bedrooms_min != null) params.bedrooms_min = filters.bedrooms_min;
    if (filters.bathrooms_min != null) params.bathrooms_min = filters.bathrooms_min;
    if (filters.neighborhood) params.neighborhood = filters.neighborhood;
    if (filters.city) params.city = filters.city;
    const response = await apiClient.get<PropertyMapResponse>('/properties/map', { params });
    return response.data;
  },

  updateProperty: async (id: string, data: PropertyUpdateData): Promise<Property> => {
    const response = await apiClient.put<Property>(`/properties/${id}`, data);
    return response.data;
  },

  geocodeAll: async (): Promise<GeocodeResponse> => {
    const response = await apiClient.post('/properties/geocode-all');
    return response.data;
  },

  geocodeBySearch: async (searchId: string): Promise<GeocodeResponse> => {
    const response = await apiClient.post('/properties/geocode-all', null, {
      params: { search_id: searchId },
    });
    return response.data;
  },

  rescrapeProperty: async (id: string): Promise<RescrapePropertyResponse> => {
    const response = await apiClient.post<RescrapePropertyResponse>(`/properties/${id}/rescrape`);
    return response.data;
  },
};
