import userEvent from '@testing-library/user-event';
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { VintagesPage } from './VintagesPage';
import { apiClient } from '../api/client';
import { vintagesResponse } from '../test/testData';

vi.mock('../api/client', () => ({
  apiClient: { getVintages: vi.fn() },
}));

const mockedClient = vi.mocked(apiClient);

describe('VintagesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedClient.getVintages.mockResolvedValue(vintagesResponse);
  });

  it('renders selected and post-cutoff statuses and cutoff explanation', async () => {
    render(<VintagesPage />);

    expect(await screen.findByText('Forecast Vintage Inspector')).toBeInTheDocument();
    expect(screen.getByText('Selected')).toBeInTheDocument();
    expect(screen.getByText('After cutoff')).toBeInTheDocument();
    expect(screen.getAllByText(/latest eligible vintage/).length).toBeGreaterThan(0);
    expect(screen.getByText(/D-1 at 09:00 UTC/)).toBeInTheDocument();
  });

  it('filters by date and paginates delivery intervals', async () => {
    const user = userEvent.setup();
    mockedClient.getVintages
      .mockResolvedValueOnce(vintagesResponse)
      .mockResolvedValueOnce({ ...vintagesResponse, page: 2 });
    render(<VintagesPage />);

    const dateInput = await screen.findByLabelText('Delivery date (UTC)');
    await user.clear(dateInput);
    await user.type(dateInput, '2026-01-16');
    expect(mockedClient.getVintages).toHaveBeenCalledWith('2026-01-16', 1, 48);

    await user.click(screen.getByRole('button', { name: /next/i }));
    await waitFor(() => expect(mockedClient.getVintages).toHaveBeenCalledWith('2026-01-16', 2, 48));
  });

  it('shows an empty state for a date with no records', async () => {
    mockedClient.getVintages.mockResolvedValue({ ...vintagesResponse, records: [], total_records: 0 });
    render(<VintagesPage />);

    expect(await screen.findByText(/No delivery intervals were returned/)).toBeInTheDocument();
  });
});
