import axios from 'axios';
import type {
  OverviewResponse,
  SeriesResponse,
  AccuracyResponse,
  VintagesResponse,
  MetadataResponse,
  ProvenanceResponse,
} from './types';

export const normalizeApiBaseUrl = (baseUrl: string): string => {
  const normalized = baseUrl.replace(/\/+$/, '');
  return normalized.endsWith('/api') ? normalized : `${normalized}/api`;
};

export const apiBaseUrl = normalizeApiBaseUrl(import.meta.env.VITE_API_BASE_URL || '/api');

const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 30000,
});

export const apiClient = {
  getHealth: async () => {
    const res = await api.get('/health');
    return res.data;
  },

  getMetadata: async (): Promise<MetadataResponse> => {
    const res = await api.get<MetadataResponse>('/metadata');
    return res.data;
  },

  getOverview: async (): Promise<OverviewResponse> => {
    const res = await api.get<OverviewResponse>('/analysis/overview');
    return res.data;
  },

  getSeries: async (dateFrom?: string, dateTo?: string): Promise<SeriesResponse> => {
    const res = await api.get<SeriesResponse>('/analysis/series', {
      params: {
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      },
    });
    return res.data;
  },

  getAccuracy: async (): Promise<AccuracyResponse> => {
    const res = await api.get<AccuracyResponse>('/analysis/accuracy');
    return res.data;
  },

  getVintages: async (date?: string, page = 1, pageSize = 48): Promise<VintagesResponse> => {
    const res = await api.get<VintagesResponse>('/analysis/vintages', {
      params: {
        date: date || undefined,
        page,
        page_size: pageSize,
      },
    });
    return res.data;
  },

  getProvenance: async (
    date?: string,
    settlementPeriod?: number,
    deliveryInterval?: string,
    page = 1,
    pageSize = 50,
  ): Promise<ProvenanceResponse> => {
    const res = await api.get<ProvenanceResponse>('/analysis/provenance', {
      params: {
        date: date || undefined,
        settlement_period: settlementPeriod || undefined,
        delivery_interval: deliveryInterval || undefined,
        page,
        page_size: pageSize,
      },
    });
    return res.data;
  },
};
