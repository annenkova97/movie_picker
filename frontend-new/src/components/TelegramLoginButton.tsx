import { useEffect, useRef } from 'react';

export interface TelegramWidgetUser {
  id: number;
  first_name?: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
  auth_date: number;
  hash: string;
}

interface Props {
  botUsername: string;
  onAuth: (user: TelegramWidgetUser) => void;
  size?: 'large' | 'medium' | 'small';
  radius?: number;
  /** Запросить право бота писать юзеру (опционально). */
  requestWriteAccess?: boolean;
}

// Глобальный счётчик, чтобы у нескольких кнопок были разные callback-имена
// и они не затирали друг друга на window.
let callbackCounter = 0;

/**
 * Telegram Login Widget — официальная кнопка «Login with Telegram».
 *
 * Скрипт от telegram.org читает свои собственные data-* атрибуты и
 * рендерит iframe-кнопку внутрь нашего контейнера. По клику открывает
 * Telegram OAuth-попап; на успех вызывает функцию по имени из data-onauth.
 *
 * Требует, чтобы домен сайта был зарегистрирован у бота через BotFather
 * `/setdomain`. Локально (localhost) Telegram кнопку покажет, но клик
 * вернёт ошибку — это норма, на проде заработает.
 */
export function TelegramLoginButton({
  botUsername,
  onAuth,
  size = 'large',
  radius = 12,
  requestWriteAccess = false,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const callbackName = `__tgLoginCb_${++callbackCounter}`;
    (window as unknown as Record<string, unknown>)[callbackName] = (user: TelegramWidgetUser) => {
      onAuth(user);
    };

    const script = document.createElement('script');
    script.src = 'https://telegram.org/js/telegram-widget.js?22';
    script.async = true;
    script.setAttribute('data-telegram-login', botUsername);
    script.setAttribute('data-size', size);
    script.setAttribute('data-radius', String(radius));
    script.setAttribute('data-onauth', `${callbackName}(user)`);
    if (requestWriteAccess) {
      script.setAttribute('data-request-access', 'write');
    }

    const container = containerRef.current;
    container.appendChild(script);

    return () => {
      delete (window as unknown as Record<string, unknown>)[callbackName];
      // Контейнер чистим — script + сгенерированный iframe.
      while (container.firstChild) container.removeChild(container.firstChild);
    };
  }, [botUsername, onAuth, size, radius, requestWriteAccess]);

  return <div ref={containerRef} style={{ display: 'flex', justifyContent: 'center' }} />;
}
