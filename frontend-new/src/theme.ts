export type ThemeName = 'light' | 'dark';

export interface Theme {
  name: ThemeName;
  bg: string;
  bgAlt: string;
  surface: string;
  ink: string;
  ink2: string;
  ink3: string;
  plum: string;
  plumInk: string;
  butter: string;
  butterDeep: string;
  cream: string;
  line: string;
  lineStrong: string;
  chipBg: string;
  posterInk: string;
  posterPaper: string;
  shadow: string;
  shadowLg: string;
  plumSurface: string;
  plumLine: string;
}

export const THEMES: Record<ThemeName, Theme> = {
  light: {
    name: 'light',
    bg: '#faf5ea',
    bgAlt: '#f3ebd9',
    surface: '#ffffff',
    ink: '#2a1830',
    ink2: '#5a4556',
    ink3: '#8f7a88',
    plum: '#3d2442',
    plumInk: '#f5e6b8',
    butter: '#e4b15c',
    butterDeep: '#c78f3c',
    cream: '#f5e6b8',
    line: 'rgba(61,36,66,0.12)',
    lineStrong: 'rgba(61,36,66,0.22)',
    chipBg: 'rgba(61,36,66,0.06)',
    posterInk: '#2a1830',
    posterPaper: '#f5e6b8',
    shadow: '0 1px 2px rgba(61,36,66,0.08), 0 12px 28px -12px rgba(61,36,66,0.18)',
    shadowLg: '0 1px 2px rgba(61,36,66,0.10), 0 30px 60px -20px rgba(61,36,66,0.35)',
    plumSurface: '#3d2442',
    plumLine: 'rgba(245,230,184,0.18)',
  },
  dark: {
    name: 'dark',
    bg: '#1d1218',
    bgAlt: '#251620',
    surface: '#2a1a23',
    ink: '#f5e6b8',
    ink2: '#d7c5a7',
    ink3: '#9a8b78',
    plum: '#f5e6b8',
    plumInk: '#2a1830',
    butter: '#e4b15c',
    butterDeep: '#c78f3c',
    cream: '#f5e6b8',
    line: 'rgba(245,230,184,0.10)',
    lineStrong: 'rgba(245,230,184,0.22)',
    chipBg: 'rgba(245,230,184,0.08)',
    posterInk: '#2a1830',
    posterPaper: '#f5e6b8',
    shadow: '0 1px 2px rgba(0,0,0,0.35), 0 12px 28px -10px rgba(0,0,0,0.55)',
    shadowLg: '0 1px 2px rgba(0,0,0,0.45), 0 40px 60px -20px rgba(0,0,0,0.7)',
    plumSurface: '#2a1a23',
    plumLine: 'rgba(245,230,184,0.12)',
  },
};
