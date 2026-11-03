import { act } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AccuracyPage } from './AccuracyPage';
import { apiClient } from '../api/client';
import { accuracyResponse, seriesResponse } from '../test/testData';

vi.mock('../api/client', () => ({
  apiClient: {
    getAccuracy: vi.fn(),
    getSeries: vi.fn(),
  },
}));

const mockedClient = vi.mocked(apiClient);

describe('AccuracyPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedClient.getAccuracy.mockResolvedValue(accuracyResponse);
    mockedClient.getSeries.mockResolvedValue(seriesResponse);
  });

  it('renders metrics and chart data from the API', async () => {
    render(<AccuracyPage />);

    expect(screen.getByText('Loading…')).toBeInTheDocument();
    expect(await screen.findByText('Forecast Accuracy Dashboard')).toBeInTheDocument();
    expect(screen.getByText('2,145.2')).toBeInTheDocument();
    expect(screen.getByText('2,615.8')).toBeInTheDocument();
    expect(screen.getByText('1,851.9')).toBeInTheDocument();
    expect(screen.getByText('66.7')).toBeInTheDocument();
    expect(screen.getAllByText(/Positive means overforecast/).length).toBeGreaterThan(0);

    const charts = screen.getAllByTestId('mock-chart');
    expect(charts.some((chart) => chart.getAttribute('data-chart-data')?.includes('"actual_mw":5000'))).toBe(true);
    expect(charts.some((chart) => chart.getAttribute('data-chart-data')?.includes('"forecast_mw":4900'))).toBe(true);
    expect(charts.some((chart) => chart.getAttribute('data-chart-data')?.includes('"absoluteError":100'))).toBe(true);
  });

  it('shows API errors and supports retry', async () => {
    mockedClient.getAccuracy.mockRejectedValueOnce(new Error('API unavailable'));
    render(<AccuracyPage />);

    expect(await screen.findByText('API unavailable')).toBeInTheDocument();
    mockedClient.getAccuracy.mockResolvedValue(accuracyResponse);
    await act(async () => {
      await screen.getByRole('button', { name: 'Retry' }).click();
    });
    await waitFor(() => expect(screen.getByText('Forecast Accuracy Dashboard')).toBeInTheDocument());
  });

  it('shows the empty matched-interval state without charts', async () => {
    mockedClient.getAccuracy.mockResolvedValue({
      ...accuracyResponse,
      metrics: { ...accuracyResponse.metrics, sample_size: 0 },
    });
    render(<AccuracyPage />);

    expect(await screen.findByText('No matched intervals')).toBeInTheDocument();
    expect(screen.queryByTestId('mock-chart')).not.toBeInTheDocument();
  });
});
