import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../auth';
import { getBookLibrary } from '../bookLibrary';

/**
 * Single entry-point the UI uses to read and mutate the user's book library.
 * Mirrors useLibrary(): picks the backend or local store based on auth state.
 */
export function useBooks() {
  const auth = useAuth();
  const qc = useQueryClient();
  const isGuest = !auth.user;
  const lib = getBookLibrary(isGuest);

  const queryKey = ['books', isGuest ? 'guest' : auth.user?.id];
  const list = useQuery({ queryKey, queryFn: () => lib.list() });
  const invalidate = () => qc.invalidateQueries({ queryKey: ['books'] });

  const save = useMutation({
    mutationFn: ({ workKey, isRead }: { workKey: string; isRead: boolean }) =>
      lib.saveByWorkKey(workKey, isRead),
    onSuccess: invalidate,
  });

  const addByQuery = useMutation({
    mutationFn: (query: string) => lib.addByQuery(query),
    onSuccess: invalidate,
  });

  const patch = useMutation({
    mutationFn: ({ id, fields }: { id: number; fields: { is_read?: boolean } }) =>
      lib.patch(id, fields),
    onSuccess: invalidate,
  });

  const remove = useMutation({
    mutationFn: (id: number) => lib.remove(id),
    onSuccess: invalidate,
  });

  return { isGuest, list, save, addByQuery, patch, remove };
}
