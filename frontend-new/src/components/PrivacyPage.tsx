/**
 * Мини privacy policy для friends-беты: что храним, какие внешние сервисы
 * задействованы и как удалить аккаунт. Открывается по /privacy, без роутера —
 * App.tsx сверяет pathname, как и для /s/<slug>.
 */
export function PrivacyPage() {
  return (
    <div className="pp-screen">
      <div className="pp-card">
        <a className="pp-back" href="/">← Ленточка</a>
        <h1 className="pp-title">Конфиденциальность</h1>

        <h2 className="pp-h2">Что мы храним</h2>
        <p className="pp-p">
          Email и хэш пароля (или идентификатор Google/Telegram-аккаунта — если
          вход через них), имя, а также ваш список фильмов, сериалов и книг:
          отметки «посмотрено», личные оценки и заметки, источник рекомендации
          (например, ссылку на Reel или пост, из которого фильм был сохранён).
        </p>

        <h2 className="pp-h2">Зачем</h2>
        <p className="pp-p">
          Только чтобы приложение работало: показывать вашу библиотеку на любых
          устройствах и строить рекомендации по вашему списку. Мы не продаём и
          не передаём данные третьим лицам и не показываем рекламу.
        </p>

        <h2 className="pp-h2">Какие внешние сервисы задействованы</h2>
        <ul className="pp-ul">
          <li>OMDb и TMDB — данные о фильмах (постеры, рейтинги, описания);</li>
          <li>Google Books и Open Library — данные о книгах;</li>
          <li>Anthropic (Claude) и OpenAI — обработка текстов постов и описаний
            фильмов; ваши списки передаются туда только в момент построения
            рекомендации;</li>
          <li>Apify — разбор публичных Instagram Reels по присланной ссылке;</li>
          <li>Sentry — отчёты об ошибках (без содержимого ваших списков);</li>
          <li>Railway — хостинг приложения и базы данных.</li>
        </ul>

        <h2 className="pp-h2">Как удалить аккаунт</h2>
        <p className="pp-p">
          Напишите нам — удалим аккаунт и все данные:{' '}
          <a className="pp-link" href="mailto:nannenkova97@gmail.com">
            nannenkova97@gmail.com
          </a>.
        </p>
      </div>
      <style>{styles}</style>
    </div>
  );
}

const styles = `
.pp-screen {
  min-height: 100vh; display: flex; justify-content: center;
  padding: 32px 16px 64px; box-sizing: border-box;
}
.pp-card { max-width: 640px; width: 100%; }
.pp-back {
  font-family: var(--font-body); font-size: 13px;
  color: var(--color-gold); text-decoration: none;
}
.pp-title {
  margin: 16px 0 8px; font-family: var(--font-display); font-weight: 700;
  font-size: 30px; color: var(--color-cream);
}
.pp-h2 {
  margin: 22px 0 6px; font-family: var(--font-body); font-weight: 600;
  font-size: 12px; letter-spacing: 1.2px; text-transform: uppercase;
  color: var(--color-gold);
}
.pp-p, .pp-ul {
  margin: 0; font-family: var(--font-body); font-size: 14px; line-height: 1.6;
  color: var(--cream-60, rgba(233, 217, 167, 0.75));
}
.pp-ul { padding-left: 18px; }
.pp-link { color: var(--color-gold); }
`;
