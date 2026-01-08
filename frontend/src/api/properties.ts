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
}

export interface PropertyImage {
  id: string;
  url?: string;
  file_path?: string;
  is_primary: boolean;
  order: number;
  created_at: string;
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
}

export const propertiesApi = {
  scrapeProperty: async (data: PropertyScrapeRequest): Promise<PropertyScrapeResponse> => {
    const response = await apiClient.post<PropertyScrapeResponse>('/properties/scrape', data);
    return response.data;
  },

  listProperties: async (skip: number = 0, limit: number = 50): Promise<PropertyListResponse> => {
    const response = await apiClient.get<PropertyListResponse>('/properties/', {
      params: { skip, limit },
    });
    return response.data;
  },

  getProperty: async (id: string): Promise<Property> => {
    const response = await apiClient.get<Property>(`/properties/${id}`);
    return response.data;
  },

  updateAllPrices: async (): Promise<UpdatePricesResponse> => {
    const response = await apiClient.post<UpdatePricesResponse>('/properties/update-prices');
    return response.data;
  },

  rescrapeAll: async (): Promise<RescrapeAllResponse> => {
    const response = await apiClient.post<RescrapeAllResponse>('/properties/rescrape-all');
    return response.data;
  },
};
