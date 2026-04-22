export type Lang = 'ru' | 'en';

type Pair = { ru: string; en: string };

export const T = {
  appName:     { ru: 'Ленточка',                      en: 'Lentochka' } as Pair,
  tagline:     { ru: 'кино, которое ты хочешь посмотреть', en: 'the films you want to watch' } as Pair,
  addMovie:    { ru: '+ Добавить фильм',              en: '+ Add a film' } as Pair,
  mood:        { ru: 'Настроение',                    en: 'Mood' } as Pair,
  moodPh:      { ru: 'лёгкое, ламповое, под пиццу…',  en: 'light, cozy, pizza-night\u2026' } as Pair,
  pick:        { ru: 'Подобрать',                     en: 'Pick one' } as Pair,
  quickAdd:    { ru: 'Быстро сохранить',              en: 'Quick save' } as Pair,
  quickAddPh:  { ru: 'вставь ссылку или название…',   en: 'paste a link or title\u2026' } as Pair,
  save:        { ru: 'Сохранить',                     en: 'Save' } as Pair,
  toWatch:     { ru: 'Хочу посмотреть',               en: 'To watch' } as Pair,
  watched:     { ru: 'Уже смотрел',                   en: 'Watched' } as Pair,
  friendMode:  { ru: 'Показать другу',                en: 'Share with a friend' } as Pair,

  shelfToday:  { ru: 'Скорее всего сегодня',          en: 'Probably tonight' } as Pair,
  shelfRecent: { ru: 'Недавно добавленные',           en: 'Recently added' } as Pair,
  shelfWait:   { ru: 'Давно откладываешь',            en: 'Been waiting a while' } as Pair,
  shelfShort:  { ru: 'До 100 минут',                  en: 'Under 100 min' } as Pair,
  shelfDrama:  { ru: 'Драмы',                         en: 'Drama' } as Pair,
  shelfComedy: { ru: 'Комедии',                       en: 'Comedy' } as Pair,
  shelfAnim:   { ru: 'Анимация',                      en: 'Animation' } as Pair,
  shelfThr:    { ru: 'Триллеры',                      en: 'Thrillers' } as Pair,

  emptyTitle:  { ru: 'Пока пусто — и это нормально',
                 en: 'Empty for now — that\u2019s fine' } as Pair,
  emptySub:    { ru: 'Увидел рекомендацию в ленте? Вставь ссылку или название — и фильм окажется здесь.',
                 en: 'Saw a recommendation in your feed? Paste a link or title — a film lands here.' } as Pair,

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
    ru: ['поплакать', 'классика', 'с друзьями', 'романтичный вечер', 'коротко, до 100 мин', 'что-то странное'],
    en: ['a good cry', 'classic', 'with friends', 'romantic night', 'under 100 min', 'something weird'],
  },

  pickHeader:  { ru: 'Твой выбор на вечер',   en: 'Your pick for tonight' } as Pair,
  pickBecause: { ru: 'Почему именно этот',     en: 'Why this one' } as Pair,
  pickAgain:   { ru: 'Ещё вариант',            en: 'Try again' } as Pair,
  pickClose:   { ru: 'Закрыть',                en: 'Close' } as Pair,
  pickWatch:   { ru: 'Смотрим',                en: 'Watch it' } as Pair,

  quickParsed: { ru: 'Нашли',                  en: 'Found' } as Pair,
  quickKeep:   { ru: 'В «Хочу посмотреть»',    en: 'To "To watch"' } as Pair,
  quickEdit:   { ru: 'Отмена',                 en: 'Cancel' } as Pair,

  markWatched: { ru: 'Отметить просмотренным', en: 'Mark as watched' } as Pair,
  unwatch:     { ru: 'Вернуть в очередь',       en: 'Back to queue' } as Pair,
  remove:      { ru: 'Удалить',                 en: 'Remove' } as Pair,

  loading:     { ru: 'Загружаем…',              en: 'Loading\u2026' } as Pair,
  noResults:   { ru: 'Ничего не нашли',         en: 'Nothing matches' } as Pair,
  errFetch:    { ru: 'Не получилось загрузить', en: 'Failed to load' } as Pair,
  errAdd:      { ru: 'Не удалось добавить',     en: 'Could not add' } as Pair,

  watchedSub:  { ru: 'моя полка, можно показать', en: 'my shelf, hand over the phone' } as Pair,

  awardsTab:     { ru: 'Награды',               en: 'Awards' } as Pair,
  awardsSub:     { ru: 'Оскар, Золотой глобус, Канны', en: 'Oscar, Golden Globe, Cannes' } as Pair,
  awardsEmpty:   { ru: 'Каталог пока пуст',      en: 'Catalog is empty for now' } as Pair,
  addToWatch:    { ru: '+ в «Хочу»',             en: '+ to "To watch"' } as Pair,
  addToWatched:  { ru: '✓ Уже смотрел',          en: '✓ Already watched' } as Pair,
  inMyLibrary:   { ru: 'уже на полке',           en: 'already on your shelf' } as Pair,

  detailPlot:    { ru: 'О чём',                   en: 'What it\u2019s about' } as Pair,
  detailCast:    { ru: 'В ролях',                 en: 'Cast' } as Pair,
  detailAwards:  { ru: 'Награды',                 en: 'Awards' } as Pair,
  detailImdb:    { ru: 'На IMDb',                 en: 'On IMDb' } as Pair,
  detailNoPlot:  { ru: 'Описание пока не загружено', en: 'No description yet' } as Pair,
};
