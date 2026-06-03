import { describe, expect, it } from 'vitest';
import { T } from './i18n';

describe('i18n', () => {
  it('every entry has both ru and en (or matching ListPair)', () => {
    const offenders: string[] = [];
    for (const [key, val] of Object.entries(T)) {
      if (val === null || typeof val !== 'object') {
        offenders.push(`${key}: not an object`);
        continue;
      }
      const v = val as Record<string, unknown>;
      if (!('ru' in v) || !('en' in v)) {
        offenders.push(`${key}: missing ru/en`);
        continue;
      }
      const ru = v.ru;
      const en = v.en;
      if (typeof ru !== typeof en) {
        offenders.push(`${key}: ru/en types differ (${typeof ru} vs ${typeof en})`);
        continue;
      }
      if (Array.isArray(ru) !== Array.isArray(en)) {
        offenders.push(`${key}: ru/en array-ness differs`);
      } else if (Array.isArray(ru) && Array.isArray(en) && ru.length !== en.length) {
        offenders.push(`${key}: array length differs (${ru.length} vs ${en.length})`);
      } else if (typeof ru === 'string' && (ru.trim() === '' || (en as string).trim() === '')) {
        offenders.push(`${key}: empty string in one of locales`);
      }
    }
    expect(offenders).toEqual([]);
  });

  it('share-flow keys exist in both locales', () => {
    // Smoke for share copy added in this iteration.
    const requiredKeys = [
      'shareButton', 'shareTitle', 'shareNameLabel', 'shareNamePh',
      'shareCreate', 'shareCancel', 'shareCopied', 'shareCopy',
      'sharedHeader', 'sharedSaveAll', 'sharedSavedAll', 'sharedNotFound',
    ] as const;
    for (const k of requiredKeys) {
      expect(T[k]?.ru, `T.${k}.ru`).toBeTruthy();
      expect(T[k]?.en, `T.${k}.en`).toBeTruthy();
    }
  });

  it('wine-deep home + settings keys exist in both locales', () => {
    const requiredKeys = [
      'greetingBack', 'friend', 'wlTitle',
      'wlFilterAll', 'wlFilterMovies', 'wlFilterSeries', 'wlFilterBooks',
      'wlRecent', 'wlSortByDate', 'wlRecsEyebrow', 'wlRecsTitle', 'wlSeeAll',
      'wlBooksEyebrow', 'wlBooksTitle', 'wlBooksOpenList',
      'tonightEyebrow', 'tonightTitle', 'tonightSubtitle',
      'settingsAria', 'searchAria', 'emptyHeroTitle', 'emptyHeroSub',
      'recSrcInstagram', 'recSrcTelegram', 'recSrcFriends', 'recSrcPersonal',
      'settingsTitle', 'settingsLanguage', 'settingsTheme',
      'settingsThemeLight', 'settingsThemeDark', 'settingsAccount',
      'settingsShareList', 'settingsGuest', 'settingsClose',
    ] as const;
    for (const k of requiredKeys) {
      expect(T[k]?.ru, `T.${k}.ru`).toBeTruthy();
      expect(T[k]?.en, `T.${k}.en`).toBeTruthy();
    }
  });

  it('books keys exist in both locales', () => {
    const requiredKeys = [
      'booksTitle', 'booksSubtitle', 'booksWantToRead', 'booksRead',
      'booksEmptyTitle', 'booksEmptySub', 'booksFindCta',
      'bookSearchTitle', 'bookSearchSub', 'bookSearchPh',
      'bookAddWant', 'bookAddRead', 'bookMarkRead', 'bookBackToList',
      'bookSubjects', 'bookAuthorless', 'pickBookCta', 'pickBookPh', 'pickBookGo',
      'back', 'searchTitle', 'searchSubtitle',
    ] as const;
    for (const k of requiredKeys) {
      expect(T[k]?.ru, `T.${k}.ru`).toBeTruthy();
      expect(T[k]?.en, `T.${k}.en`).toBeTruthy();
    }
  });

  it('greetingBack carries the %s name placeholder in both locales', () => {
    expect(T.greetingBack.ru).toContain('%s');
    expect(T.greetingBack.en).toContain('%s');
  });
});
