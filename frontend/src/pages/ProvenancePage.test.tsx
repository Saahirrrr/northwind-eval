import userEvent from '@testing-library/user-event';
import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ProvenancePage } from './ProvenancePage';
import { apiClient } from '../api/client';
import { provenanceResponse } from '../test/testData';

vi.mock('../api/client', () => ({
  apiClient: { getProvenance: vi.fn() },
}));

const mockedClient = vi.mocked(apiClient);

describe('ProvenancePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedClient.getProvenance.mockResolvedValue(provenanceResponse);
  });

  it('expands raw records and displays duplicate and selection indicators', async () => {
    const user = userEvent.setup();
    const { container } = render(<ProvenancePage />);

    expect(await screen.findByText('Data Provenance')).toBeInTheDocument();
    expect(screen.getByText('FUELHH')).toBeInTheDocument();
    expect(screen.getByText('WINDFOR')).toBeInTheDocument();
    expect(screen.getByText('Duplicate indicator')).toBeInTheDocument();
    expect(screen.getByText('Selected vintage')).toBeInTheDocument();
    await user.click(screen.getAllByRole('button', { name: /raw record/i })[1]);
    expect(container.querySelector('pre')).toHaveTextContent('"generation": 4900');
    expect(screen.getByText('startTime normalized to UTC.')).toBeInTheDocument();
  });

  it('shows empty and partial-data states from the API', async () => {
    mockedClient.getProvenance.mockResolvedValueOnce({
      ...provenanceResponse,
      records: [provenanceResponse.records[0]],
      total_records: 1,
    });
    const { unmount } = render(<ProvenancePage />);
    expect(await screen.findByText('FUELHH')).toBeInTheDocument();
    expect(screen.queryByText('WINDFOR')).not.toBeInTheDocument();

    mockedClient.getProvenance.mockResolvedValue({
      ...provenanceResponse,
      records: [],
      total_records: 0,
    });
    unmount();
    render(<ProvenancePage />);
    expect(await screen.findByText(/No provenance records match/)).toBeInTheDocument();
  });
});
