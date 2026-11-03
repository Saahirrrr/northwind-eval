import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiBaseUrl, apiClient, normalizeApiBaseUrl } from './client';

const { mockedGet } = vi.hoisted(() => ({
  mockedGet: vi.fn(),
}));

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: mockedGet,
    })),
  },
}));

describe('API client URLs', () => {
  beforeEach(() => {
    mockedGet.mockReset();
    mockedGet.mockResolvedValue({ data: {} });
  });

  it('normalizes backend origins and avoids duplicate API prefixes', () => {
    expect(normalizeApiBaseUrl('https://backend.example.com')).toBe(
      'https://backend.example.com/api',
    );
    expect(normalizeApiBaseUrl('https://backend.example.com/api/')).toBe(
      'https://backend.example.com/api',
    );
    expect(normalizeApiBaseUrl('/api')).toBe('/api');
    expect(apiBaseUrl).toBe('/api');
  });

  it('uses the API-prefixed paths for analysis endpoints', async () => {
    await apiClient.getOverview();
    await apiClient.getAccuracy();
    await apiClient.getSeries();
    await apiClient.getVintages();
    await apiClient.getProvenance();

    expect(mockedGet).toHaveBeenNthCalledWith(1, '/analysis/overview');
    expect(mockedGet).toHaveBeenNthCalledWith(2, '/analysis/accuracy');
    expect(mockedGet).toHaveBeenNthCalledWith(3, '/analysis/series', {
      params: { date_from: undefined, date_to: undefined },
    });
    expect(mockedGet).toHaveBeenNthCalledWith(4, '/analysis/vintages', {
      params: { date: undefined, page: 1, page_size: 48 },
    });
    expect(mockedGet).toHaveBeenNthCalledWith(5, '/analysis/provenance', {
      params: {
        date: undefined,
        settlement_period: undefined,
        delivery_interval: undefined,
        page: 1,
        page_size: 50,
      },
    });
  });
});
