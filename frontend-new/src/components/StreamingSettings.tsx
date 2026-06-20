import { useState } from 'react';
import { useSettings } from '../settings';
import { useAuth } from '../auth';
import { patchSettings } from '../api';

interface ProviderOption {
  id: number;
  name: string;
}

const REGIONS: { code: string; label: string }[] = [
  { code: 'RU', label: 'Россия' },
  { code: 'US', label: 'США' },
  { code: 'GB', label: 'Великобритания' },
  { code: 'DE', label: 'Германия' },
  { code: 'FR', label: 'Франция' },
];

// Curated providers with their TMDb ids. Matching uses these ids against the
// JustWatch data, so the global majors (Netflix=8 etc.) are reliable; a few
// regional ids may need tuning — a wrong id just means "no match", never a crash.
const PROVIDERS: ProviderOption[] = [
  { id: 8, name: 'Netflix' },
  { id: 119, name: 'Amazon Prime' },
  { id: 350, name: 'Apple TV+' },
  { id: 337, name: 'Disney+' },
  { id: 1899, name: 'Max' },
  { id: 531, name: 'Paramount+' },
  { id: 116, name: 'Кинопоиск' },
  { id: 115, name: 'Okko' },
  { id: 126, name: 'ivi' },
];

/**
 * "Сервисы и регион" sheet. The parent renders it only while open, so the
 * draft state initialises fresh from the stored settings each time. On save we
 * persist locally (useSettings → localStorage) and, when signed in, mirror to
 * the server best-effort so settings follow the user and the bot can read them.
 */
export function StreamingSettings({ onClose }: { onClose: () => void }) {
  const { region, setRegion, services, setServices } = useSettings();
  const auth = useAuth();
  const [draftRegion, setDraftRegion] = useState(region);
  const [draftServices, setDraftServices] = useState<number[]>(services);

  const toggle = (id: number) =>
    setDraftServices((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  const save = () => {
    setRegion(draftRegion);
    setServices(draftServices);
    if (auth.user) {
      patchSettings({ region: draftRegion, streaming_services: draftServices }).catch(() => {});
    }
    onClose();
  };

  return (
    <div className="ss-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="ss-card" onClick={(e) => e.stopPropagation()}>
        <div className="ss-head">
          <h2 className="ss-title">Сервисы и регион</h2>
          <button className="ss-close" onClick={onClose} aria-label="Закрыть">×</button>
        </div>
        <p className="ss-hint">
          Покажем, где из твоего списка можно посмотреть фильм прямо сейчас — и
          сможем подбирать только доступное на твоих сервисах.
        </p>

        <div className="ss-section">
          <div className="ss-eyebrow">Регион</div>
          <select
            className="ss-select"
            value={draftRegion}
            onChange={(e) => setDraftRegion(e.target.value)}
          >
            {REGIONS.map((r) => (
              <option key={r.code} value={r.code}>{r.label}</option>
            ))}
          </select>
        </div>

        <div className="ss-section">
          <div className="ss-eyebrow">Мои сервисы</div>
          <div className="ss-providers">
            {PROVIDERS.map((p) => {
              const active = draftServices.includes(p.id);
              return (
                <button
                  key={p.id}
                  type="button"
                  className={`ss-chip${active ? ' is-active' : ''}`}
                  onClick={() => toggle(p.id)}
                  aria-pressed={active}
                >
                  {active ? '✓ ' : ''}{p.name}
                </button>
              );
            })}
          </div>
        </div>

        <button className="ss-save" type="button" onClick={save}>Готово</button>
        <style>{styles}</style>
      </div>
    </div>
  );
}

const styles = `
.ss-overlay {
  position: fixed; inset: 0; z-index: 130;
  background: rgba(20, 10, 18, 0.6);
  backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
  display: flex; align-items: center; justify-content: center;
  padding: 20px; overflow-y: auto;
}
.ss-card {
  background: var(--color-wine);
  border: 1px solid var(--wine-light-border);
  border-radius: 20px; padding: 24px;
  max-width: 420px; width: 100%;
  box-shadow: 0 30px 70px rgba(0, 0, 0, 0.5);
  display: flex; flex-direction: column; gap: 16px;
  animation: ss-rise 0.2s ease both;
}
@keyframes ss-rise { from { transform: translateY(12px); opacity: 0; } to { transform: none; opacity: 1; } }
.ss-head { display: flex; justify-content: space-between; align-items: center; }
.ss-title {
  margin: 0; font-family: var(--font-display); font-weight: 700;
  font-size: 22px; color: var(--color-cream);
}
.ss-close {
  border: none; background: transparent; color: var(--cream-60);
  font-size: 26px; line-height: 1; cursor: pointer; padding: 0 4px;
}
.ss-hint {
  margin: 0; font-family: var(--font-body); font-size: 13px;
  line-height: 1.5; color: var(--cream-70);
}
.ss-section { display: flex; flex-direction: column; gap: 10px; }
.ss-eyebrow {
  font-family: var(--font-body); font-weight: 600; font-size: 11px;
  letter-spacing: 1.4px; text-transform: uppercase; color: var(--color-gold);
}
.ss-select {
  height: 44px; border-radius: 12px; padding: 0 12px;
  background: var(--color-wine-deep); color: var(--color-cream);
  border: 1px solid var(--wine-light-border);
  font-family: var(--font-body); font-size: 14px;
}
.ss-providers { display: flex; flex-wrap: wrap; gap: 8px; }
.ss-chip {
  height: 36px; padding: 0 14px; border-radius: 18px;
  border: 1px solid var(--wine-light-border);
  background: var(--color-wine-deep); color: var(--cream-85);
  font-family: var(--font-body); font-size: 14px; cursor: pointer;
  transition: background 0.12s ease, border-color 0.12s ease, color 0.12s ease;
}
.ss-chip:hover { border-color: var(--gold-border); }
.ss-chip.is-active {
  background: var(--color-gold); color: var(--color-wine-deep);
  border-color: var(--color-gold); font-weight: 600;
}
.ss-save {
  height: 52px; border-radius: var(--radius-pill); border: 0;
  background: var(--color-gold); color: var(--color-wine-deep);
  font-family: var(--font-body); font-weight: 600; font-size: 16px;
  cursor: pointer; transition: background 0.15s ease; margin-top: 4px;
}
.ss-save:hover { background: var(--color-gold-dark); }
`;
