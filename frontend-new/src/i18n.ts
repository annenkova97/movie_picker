export type Lang = 'ru' | 'en';

type Pair = { ru: string; en: string };

export const T = {
  appName:     { ru: 'Ленточка',                      en: 'Lentochka' } as Pair,
  tagline:     { ru: 'кино, которое хочется смотреть', en: 'the films you want to watch' } as Pair,
  taglineSub:  { ru: 'сохраняй все рекомендации',
                 en: 'save every recommendation' } as Pair,
  addMovie:    { ru: '+ Добавить фильм',              en: '+ Add a film' } as Pair,
  mood:        { ru: 'Настроение',                    en: 'Mood' } as Pair,
  moodPh:      { ru: 'лёгкое, ламповое, под пиццу…',  en: 'light, cozy, pizza-night\u2026' } as Pair,
  pick:        { ru: 'Подобрать',                     en: 'Pick one' } as Pair,
  quickAdd:    { ru: 'Быстро сохранить',              en: 'Quick save' } as Pair,
  quickAddPh:  { ru: 'вставь ссылку из соцсети…',     en: 'paste a link from social…' } as Pair,
  save:        { ru: 'Сохранить',                     en: 'Save' } as Pair,
  find:        { ru: 'Найти',                         en: 'Find' } as Pair,

  statusOpenReels:  { ru: 'открываю Reels',            en: 'opening Reels' } as Pair,
  statusListen:     { ru: 'слушаю аудио',              en: 'listening to audio' } as Pair,
  statusCaptions:   { ru: 'читаю подписи',             en: 'reading captions' } as Pair,
  statusCollect:    { ru: 'собираю названия',          en: 'collecting titles' } as Pair,
  statusOpenPost:   { ru: 'открываю пост',             en: 'opening the post' } as Pair,
  statusReadPost:   { ru: 'читаю текст',               en: 'reading the text' } as Pair,
  statusFindTitle:  { ru: 'нахожу фильм',              en: 'pulling out the title' } as Pair,
  statusLookup:     { ru: 'ищу в базе',                en: 'looking it up' } as Pair,
  statusImdb:       { ru: 'сверяюсь с IMDb',           en: 'checking IMDb' } as Pair,
  toWatch:     { ru: 'Сохранённое',                   en: 'Saved' } as Pair,
  watched:     { ru: 'Смотрел',                       en: 'Watched' } as Pair,
  friendMode:  { ru: 'Показать другу',                en: 'Share with a friend' } as Pair,

  shelfToday:  { ru: 'Скорее всего сегодня',          en: 'Probably tonight' } as Pair,
  shelfRecent: { ru: 'Недавно добавленные',           en: 'Recently added' } as Pair,
  shelfWait:   { ru: 'Давно откладываешь',            en: 'Been waiting a while' } as Pair,
  shelfShort:  { ru: 'До 100 минут',                  en: 'Under 100 min' } as Pair,
  shelfDrama:  { ru: 'Драмы',                         en: 'Drama' } as Pair,
  shelfComedy: { ru: 'Комедии',                       en: 'Comedy' } as Pair,
  shelfAnim:   { ru: 'Анимация',                      en: 'Animation' } as Pair,
  shelfThr:    { ru: 'Триллеры',                      en: 'Thrillers' } as Pair,

  emptyTitle:  { ru: 'Какой фильм тебе недавно советовали?',
                 en: 'What did someone recently recommend?' } as Pair,
  emptySub:    { ru: 'Вставь ссылку или название — сохраним с постером и рейтингом.',
                 en: 'Paste a link or title — we\u2019ll save it with poster and rating.' } as Pair,

  min:         { ru: 'мин',                           en: 'min' } as Pair,
  myScore:     { ru: 'моё',                           en: 'mine' } as Pair,
  kp:          { ru: 'IMDb',                          en: 'IMDb' } as Pair,
  because:     { ru: 'Почему',                        en: 'Why' } as Pair,
  saved:       { ru: 'сохранено',                     en: 'saved' } as Pair,

  source_telegram:  { ru: 'Из Telegram',   en: 'From Telegram' } as Pair,
  source_instagram: { ru: 'Из Instagram',  en: 'From Instagram' } as Pair,
  source_friends:   { ru: 'От друзей',     en: 'From friends' } as Pair,
  source_personal:  { ru: 'Личное',        en: 'Personal' } as Pair,

  moodChips: {
    ru: ['поплакать', 'классика', 'с друзьями', 'романтичный вечер', 'что-то странное'],
    en: ['a good cry', 'classic', 'with friends', 'romantic night', 'something weird'],
  },

  moodGenreLabel:    { ru: 'Жанр',         en: 'Genre' } as Pair,
  moodDurationLabel: { ru: 'Длительность', en: 'Length' } as Pair,
  moodEraLabel:      { ru: 'Эпоха',        en: 'Era' } as Pair,
  moodAnyOption:     { ru: 'Любой',        en: 'Any' } as Pair,

  moodGenres: {
    ru: ['Комедия', 'Драма', 'Триллер', 'Фантастика', 'Документалка', 'Мелодрама', 'Ужасы', 'Анимация'],
    en: ['Comedy', 'Drama', 'Thriller', 'Sci-Fi', 'Documentary', 'Romance', 'Horror', 'Animation'],
  },
  moodDurations: {
    ru: ['До 90 мин', '90–120 мин', 'Больше 2 часов'],
    en: ['Under 90 min', '90–120 min', 'Over 2 hours'],
  },
  moodEras: {
    ru: ['2020-е', '2010-е', '2000-е', '90-е', 'Старое кино'],
    en: ['2020s', '2010s', '2000s', '90s', 'Classic'],
  },

  pickHeader:  { ru: 'Твой выбор на вечер',   en: 'Your pick for tonight' } as Pair,
  pickBecause: { ru: 'Почему именно этот',     en: 'Why this one' } as Pair,
  pickAgain:   { ru: 'Ещё вариант',            en: 'Try again' } as Pair,
  pickClose:   { ru: 'Закрыть',                en: 'Close' } as Pair,
  pickWatch:   { ru: 'Смотрим',                en: 'Watch it' } as Pair,

  quickParsed: { ru: 'Нашли',                  en: 'Found' } as Pair,
  quickKeep:   { ru: 'Сохранить',              en: 'Save' } as Pair,
  quickEdit:   { ru: 'Отмена',                 en: 'Cancel' } as Pair,

  markWatched: { ru: 'Отметить просмотренным', en: 'Mark as watched' } as Pair,
  unwatch:     { ru: 'Вернуть в очередь',       en: 'Back to queue' } as Pair,
  remove:      { ru: 'Удалить',                 en: 'Remove' } as Pair,

  loading:     { ru: 'Загружаем…',              en: 'Loading\u2026' } as Pair,
  noResults:   { ru: 'Ничего не нашли',         en: 'Nothing matches' } as Pair,
  errFetch:    { ru: 'Не получилось загрузить', en: 'Failed to load' } as Pair,
  errAdd:      { ru: 'Не удалось добавить',     en: 'Could not add' } as Pair,

  watchedSub:  { ru: 'моя полка, можно показать', en: 'my shelf, hand over the phone' } as Pair,

  awardsTab:     { ru: 'Стоит',                 en: 'Worth it' } as Pair,
  pickTonight:   { ru: '✨ Подобрать на вечер',   en: '✨ Pick for tonight' } as Pair,
  sourceHint:    { ru: 'из Instagram, Telegram или от друга — распознаем автоматически',
                   en: 'from Instagram, Telegram or a friend — we\u2019ll recognize it automatically' } as Pair,
  pickMoodTitle: { ru: 'Какое настроение?',       en: 'What\u2019s the mood?' } as Pair,
  awardsSub:     { ru: 'Оскар, Золотой глобус, Канны', en: 'Oscar, Golden Globe, Cannes' } as Pair,
  awardsEmpty:   { ru: 'Каталог пока пуст',      en: 'Catalog is empty for now' } as Pair,
  addToWatch:    { ru: '+ Сохранить',            en: '+ Save' } as Pair,
  addToWatched:  { ru: '✓ Уже смотрел',          en: '✓ Already watched' } as Pair,
  inMyLibrary:   { ru: 'уже на полке',           en: 'already on your shelf' } as Pair,

  detailPlot:    { ru: 'О чём',                   en: 'What it\u2019s about' } as Pair,
  detailCast:    { ru: 'В ролях',                 en: 'Cast' } as Pair,
  detailAwards:  { ru: 'Награды',                 en: 'Awards' } as Pair,
  detailImdb:    { ru: 'На IMDb',                 en: 'On IMDb' } as Pair,
  detailNoPlot:  { ru: 'Описание пока не загружено', en: 'No description yet' } as Pair,

  authLoading:   { ru: 'Проверяем вход…',         en: 'Checking sign-in\u2026' } as Pair,
  logout:        { ru: 'Выйти',                   en: 'Sign out' } as Pair,
};
