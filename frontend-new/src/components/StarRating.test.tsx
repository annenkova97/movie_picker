import { describe, it, expect } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { StarRating } from './StarRating';

describe('StarRating', () => {
  // Match the class attribute form (trailing quote) so the embedded <style>
  // block — which also mentions `.sr-star--on` — doesn't inflate the count.
  const filledCount = (html: string) => (html.match(/sr-star--on"/g) || []).length;

  it('fills exactly `value` stars in read-only mode', () => {
    const html = renderToStaticMarkup(<StarRating value={3} readOnly />);
    expect(filledCount(html)).toBe(3);
  });

  it('treats null as zero filled stars', () => {
    const html = renderToStaticMarkup(<StarRating value={null} readOnly />);
    expect(filledCount(html)).toBe(0);
  });

  it('renders 5 interactive radio buttons when onChange is provided', () => {
    const html = renderToStaticMarkup(<StarRating value={2} onChange={() => {}} />);
    expect((html.match(/role="radio"/g) || []).length).toBe(5);
    // the active star is marked checked
    expect(html).toContain('aria-checked="true"');
  });
});
