import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../auth';
import { getLibrary } from '../library';
import { track } from '../analytics';
import type { ApiMovie } from '../types';
import type { MoviePatch } from '../api';

const GUEST_SIGNUP_SHOWN_KEY = 'lentochka.guestSignupShown';

/**
 * Single entry-point that the UI uses to read and mutate the user's library.
 * Internally picks BackendLibrary or LocalLibrary based on auth state, so
 * components don't have to branch on `auth.user` themselves.
 *
 * The query key includes a stable per-identity tag so that signing in / out
 * swaps to a fresh cache slot rather than mixing guest data with server data.
 */
export function useLibrary() {
  const auth = useAuth();
  const qc = useQueryClient();
  const isGuest = !auth.user;
  const lib = getLibrary(isGuest);

  // Distinct cache slots for guest vs each user id.
  const queryKey = ['library', isGuest ? 'guest' : auth.user?.id];

  const list = useQuery({
    queryKey,
    queryFn: () => lib.list(),
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ['library'] });
  // Track an add, then refresh the library. Used by every "movie enters the
  // library" path so the kill-metric's save-rate signal is complete.
  const onAdded = (source: string) => () => {
    track('movie_added', { source });
    invalidate();
  };

  const save = useMutation({
    mutationFn: ({ imdbId, watched }: { imdbId: string; watched: boolean }) =>
      lib.saveByImdbId(imdbId, watched),
    onSuccess: onAdded('save'),
  });

  const saveAward = useMutation({
    mutationFn: ({ movie, watched }: { movie: ApiMovie; watched: boolean }) =>
      lib.saveAward(movie, watched),
    onSuccess: onAdded('award'),
  });

  const addByQuery = useMutation({
    mutationFn: (query: string) => lib.addByQuery(query),
    onSuccess: onAdded('query'),
  });

  const patch = useMutation({
    mutationFn: ({ id, fields }: { id: number; fields: MoviePatch }) =>
      lib.patch(id, fields),
    onSuccess: invalidate,
  });

  const remove = useMutation({
    mutationFn: (id: number) => lib.remove(id),
    onSuccess: invalidate,
  });

  const importInstagram = useMutation({
    mutationFn: (url: string) => lib.importFromInstagram(url),
    onSuccess: onAdded('instagram'),
  });

  const importTelegram = useMutation({
    mutationFn: (url: string) => lib.importFromTelegram(url),
    onSuccess: onAdded('telegram'),
  });

  const absorbShared = useMutation({
    mutationFn: (movies: ApiMovie[]) => lib.absorbShared(movies),
    onSuccess: invalidate,
  });

  return {
    isGuest,
    list,
    save,
    saveAward,
    addByQuery,
    patch,
    remove,
    importInstagram,
    importTelegram,
    absorbShared,
  };
}

/**
 * Decides whether to render the "create an account" bottom sheet.
 * Opens once a guest has at least one saved movie and hasn't dismissed it
 * before. Dismissal is sticky across sessions via localStorage.
 */
export function useGuestSignupPrompt(libraryCount: number, isGuest: boolean) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!isGuest) {
      setOpen(false);
      return;
    }
    if (libraryCount < 1) return;
    try {
      if (localStorage.getItem(GUEST_SIGNUP_SHOWN_KEY)) return;
    } catch {}
    setOpen(true);
  }, [isGuest, libraryCount]);

  const dismiss = () => {
    try {
      localStorage.setItem(GUEST_SIGNUP_SHOWN_KEY, '1');
    } catch {}
    setOpen(false);
  };

  return { open, dismiss };
}
