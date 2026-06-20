import { useQuery } from '@tanstack/react-query';
import { getAvailability, type WatchAvailability } from '../api';

/**
 * Lazily fetch where a title can be watched, keyed by (imdbId, region) so
 * React Query dedupes/caches across cards. Disabled until an imdbId is given
 * (e.g. detail modal closed). Server already caches 24h; we keep a 1h client
 * stale window so re-opening a film doesn't refetch.
 */
export function useAvailability(
  imdbId: string | null | undefined,
  region: string,
  enabled = true,
) {
  return useQuery<WatchAvailability>({
    queryKey: ['availability', imdbId, region],
    queryFn: () => getAvailability(imdbId!, region),
    enabled: !!imdbId && enabled,
    staleTime: 1000 * 60 * 60,
  });
}
