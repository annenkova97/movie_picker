from telegram import (
    ForceReply,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    WebAppInfo,
)
from telegram.ext import ApplicationHandlerStop, ContextTypes

from backend import database as db
from backend.config import MINI_APP_URL
from backend.services import book_search
from backend.services.omdb import omdb_service
from backend.services.llm import llm_service
from backend.services.title_search import search_title
from handlers.formatting import imdb_suffix
from handlers.source_context import get_source, remember_source


def _saved_confirmation_keyboard() -> InlineKeyboardMarkup | None:
    """Карточка после сохранения: только «Открыть в Lentochka».

    Раньше тут были «Не тот фильм?» и «Удалить» — их убрали: после явного
    сохранения они только путали (пользователь уже выбрал фильм). Если
    MINI_APP_URL не задан — возвращаем None (клавиатура убирается совсем).
    """
    if not MINI_APP_URL:
        return None
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "📖 Открыть в Lentochka",
            web_app=WebAppInfo(url=MINI_APP_URL),
        ),
    ]])


def _loading_keyboard() -> InlineKeyboardMarkup:
    """Мгновенный лоадер вместо «застывшей» кнопки «+ Сохранить»."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⏳ Сохраняю…", callback_data="noop"),
    ]])


def _save_button_keyboard(imdb_id: str) -> InlineKeyboardMarkup:
    """Кнопка «+ Сохранить» — чтобы восстановить карточку при ошибке OMDB."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("+ Сохранить", callback_data=f"add:{imdb_id}"),
    ]])


def wrong_undo_keyboard(movie_id: int) -> InlineKeyboardMarkup:
    """Кнопки под только что сохранённым из ссылки фильмом.

    Фильм уже в списке (сохраняем сразу, без подтверждения), поэтому кнопки —
    только «откатить»: «Не тот» убирает и предлагает похожие варианты,
    «Не добавлять» просто убирает.
    """
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Не тот", callback_data=f"wrong:{movie_id}"),
        InlineKeyboardButton("Не добавлять", callback_data=f"undo:{movie_id}"),
    ]])


def _chat_id(query) -> int | None:
    """chat_id сообщения с карточкой — ключ реестра источников."""
    chat = getattr(getattr(query, "message", None), "chat", None)
    return getattr(chat, "id", None)


async def _get_or_create_user(tg_user) -> dict:
    """Находит или создаёт юзера в БД по telegram_id из callback'а.

    Telegram не отдаёт email, поэтому выдаём синтетический ``tg<id>@telegram.local``.
    Тот же подход используется в /auth/telegram-webapp на фронте — поэтому
    юзер, добавивший фильмы в боте, видит их же при открытии Mini App.
    """
    telegram_id = int(tg_user.id)
    row = await db.get_user_by_telegram_id(telegram_id)
    if row:
        return row

    name_parts = [tg_user.first_name or "", tg_user.last_name or ""]
    full_name = " ".join(p for p in name_parts if p).strip() or (tg_user.username or "")
    return await db.create_user(
        # Synthetic email — example.com зарезервирован RFC 2606.
        email=f"tg{telegram_id}@tg.example.com",
        telegram_id=telegram_id,
        name=full_name or None,
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка всех callback-кнопок"""
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    if ":" not in data:
        return  # неактивные плейсхолдеры, напр. лоадер «⏳ Сохраняю…» (noop)
    action, value = data.split(":", 1)

    user_row = await _get_or_create_user(query.from_user)
    user_id = user_row["id"]

    if action == "add":
        await _handle_add(query, value, user_id=user_id, context=context)
    elif action == "wrong":
        await _handle_wrong(query, int(value), user_id=user_id)
    elif action == "undo":
        await _handle_undo(query, int(value), user_id=user_id)
    elif action == "watch":
        await _handle_watch(query, int(value), user_id=user_id, watched=True)
    elif action == "unwatch":
        await _handle_watch(query, int(value), user_id=user_id, watched=False)
    elif action == "delete":
        await _handle_delete(query, int(value), user_id=user_id)
    elif action == "addbook":
        await _handle_add_book(query, value, user_id=user_id)
    elif action == "readbook":
        await _handle_read(query, int(value), user_id=user_id, read=True)
    elif action == "unreadbook":
        await _handle_read(query, int(value), user_id=user_id, read=False)
    elif action == "rate":
        await _handle_rate(query, value, user_id=user_id, context=context)


async def _handle_add(query, imdb_id: str, *, user_id: int, context):
    """Сохраняет фильм в библиотеку — быстро, без ожидания LLM.

    Раньше карточка «висела» 1–3 сек: после OMDB бот ждал, пока Claude
    сгенерит описание, и только потом сохранял и отвечал. Но описание в
    подтверждении не показывается — оно нужно только Mini-App. Поэтому теперь:
    мгновенный лоадер → OMDB → запись в БД → подтверждение с рейтингом, а
    описание и «крючок» догоняются в фоне (см. ``_enrich_saved_movie``).
    """
    existing = await db.get_user_movie_by_imdb_id(imdb_id, user_id)
    if existing:
        await query.edit_message_reply_markup(
            reply_markup=_saved_confirmation_keyboard(),
        )
        await query.message.reply_text(
            f"«{existing.title}» уже в твоём списке."
        )
        return

    # Мгновенная реакция на тап — лоадер вместо «застывшей» кнопки.
    await query.edit_message_reply_markup(reply_markup=_loading_keyboard())

    movie_base = await omdb_service.get_movie_by_id(imdb_id)
    if not movie_base:
        # Возвращаем кнопку, чтобы можно было повторить.
        await query.edit_message_reply_markup(
            reply_markup=_save_button_keyboard(imdb_id),
        )
        await query.message.reply_text(
            "Не получилось загрузить фильм. Попробуй ещё раз."
        )
        return

    # Если карточка родилась из ссылки (Reel, пост в канале) — хендлер ссылки
    # зарегистрировал её источник, сохраняем его вместе с фильмом.
    chat_id = _chat_id(query)
    src = get_source(chat_id, imdb_id) if chat_id is not None else None

    # Сохраняем сразу, без описания — догенерим его в фоне. ``source`` всегда
    # personal (это тип записи), канал рекомендации — в rec_source.
    movie = await db.add_movie(
        movie_base,
        user_id=user_id,
        source="personal",
        rec_source=src.rec_source if src else None,
        source_url=src.source_url if src else None,
    )

    # Для карточек из ссылок даём откат («Не тот» / «Не добавлять»); после
    # явного выбора из поиска эти кнопки только путали бы.
    await query.edit_message_reply_markup(
        reply_markup=wrong_undo_keyboard(movie.id) if src
        else _saved_confirmation_keyboard(),
    )

    rating = imdb_suffix(movie.imdb_rating, ", IMDb ")
    await query.message.reply_text(
        f"*{movie.title}* — сохранила{rating}.",
        parse_mode="Markdown",
    )

    # Фоном: краткое описание (для Mini-App) + интригующий «крючок», который
    # придёт отдельным сообщением через ~1 сек, чтобы ещё раз заинтересовать.
    if movie_base.plot:
        context.application.create_task(
            _enrich_saved_movie(
                query.message, movie.id, movie_base.plot, movie.title
            )
        )


async def auto_add_movie(
    message,
    context,
    tg_user,
    movie_base,
    *,
    rec_source: str | None,
    source_url: str | None,
):
    """Сохраняет фильм из поста/ссылки сразу, без кнопки «Добавить».

    Возвращает ``(movie, already_existed)``; ``movie is None`` не бывает.
    Описание и «крючок» догоняются в фоне, как и при обычном сохранении.
    """
    user_row = await _get_or_create_user(tg_user)
    user_id = user_row["id"]

    existing = await db.get_user_movie_by_imdb_id(movie_base.imdb_id, user_id)
    if existing:
        return existing, True

    movie = await db.add_movie(
        movie_base,
        user_id=user_id,
        source="personal",
        rec_source=rec_source,
        source_url=source_url,
    )

    if movie_base.plot:
        context.application.create_task(
            _enrich_saved_movie(message, movie.id, movie_base.plot, movie.title)
        )
    return movie, False


async def _handle_wrong(query, movie_id: int, *, user_id: int):
    """«Не тот» под авто-сохранённым фильмом: убрать и показать похожие."""
    movie = await db.get_user_movie_by_id(movie_id, user_id=user_id)
    if not movie:
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("Этого фильма уже нет в списке.")
        return

    await db.delete_movie(movie_id, user_id=user_id)
    # Кнопка «+ Сохранить» возвращается — вдруг это всё-таки был он.
    await query.edit_message_reply_markup(
        reply_markup=_save_button_keyboard(movie.imdb_id),
    )

    results = await search_title(movie.title)
    results = [r for r in results if r.imdb_id != movie.imdb_id][:4]
    if not results:
        await query.message.reply_text(
            f"Убрала «{movie.title}». Похожих вариантов не нашла — "
            "напиши название текстом, поищу ещё."
        )
        return

    # Альтернативы — из той же ссылки, переносим на них источник.
    chat_id = _chat_id(query)
    src = get_source(chat_id, movie.imdb_id) if chat_id is not None else None
    if chat_id is not None and src:
        for r in results:
            remember_source(chat_id, r.imdb_id, src.rec_source, src.source_url)

    await query.message.reply_text(
        f"Убрала «{movie.title}». Вот похожие варианты — выбери нужный:"
    )
    # Локальный импорт: search.py не зависит от callbacks, цикла нет, но
    # держим его здесь, чтобы модульная зависимость была односторонней.
    from handlers.search import send_search_results
    await send_search_results(query.message, results)


async def _handle_undo(query, movie_id: int, *, user_id: int):
    """«Не добавлять» под авто-сохранённым фильмом: просто убрать из списка."""
    movie = await db.get_user_movie_by_id(movie_id, user_id=user_id)
    if not movie:
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("Этого фильма уже нет в списке.")
        return

    await db.delete_movie(movie_id, user_id=user_id)
    await query.edit_message_reply_markup(
        reply_markup=_save_button_keyboard(movie.imdb_id),
    )
    await query.message.reply_text(
        f"Окей, «{movie.title}» не сохраняю. Передумаешь — кнопка на месте."
    )


async def _enrich_saved_movie(message, movie_id: int, plot: str, title: str) -> None:
    """Фоновая догенерация после сохранения: описание в БД + «крючок» в чат.

    Запускается через ``application.create_task`` уже после ответа пользователю,
    поэтому ничего не блокирует. Любые сбои (LLM/БД/сеть) глотаем — это не
    критичный путь, фильм уже сохранён.
    """
    try:
        description, hook = await llm_service.describe_and_tease(plot, title)
    except Exception:
        return

    if description:
        try:
            await db.set_description(movie_id, description)
        except Exception:
            pass

    if hook:
        # Без parse_mode — текст от LLM может содержать «*»/«_» и ломать Markdown.
        try:
            await message.reply_text(f"🎬 {hook}")
        except Exception:
            pass


async def _handle_watch(query, movie_id: int, *, user_id: int, watched: bool):
    """Отметить фильм просмотренным/непросмотренным."""
    movie = await db.update_movie(movie_id, user_id=user_id, is_watched=watched)
    if not movie:
        await query.message.reply_text("Фильм не нашла.")
        return

    status = "посмотрен ✅" if watched else "вернула в список 🎬"
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(
        f"*{movie.title}* — {status}", parse_mode="Markdown"
    )
    if watched:
        await query.message.reply_text(
            "Как тебе? Поставь оценку:",
            reply_markup=_rating_keyboard("movie", movie.id),
        )


# ── books ──────────────────────────────────────────────────────────────────


async def _handle_add_book(query, work_key: str, *, user_id: int):
    """Сохраняет книгу в библиотеку и переключает карточку в подтверждение."""
    existing = await db.get_user_book_by_work_key(work_key, user_id)
    if existing:
        await query.edit_message_reply_markup(
            reply_markup=_book_saved_keyboard(existing.id, existing.is_read),
        )
        await query.message.reply_text(f"«{existing.title}» уже в твоих книгах.")
        return

    book_base = await book_search.get_book_by_key(work_key)
    if not book_base:
        await query.message.reply_text("Не получилось загрузить книгу.")
        return

    chat_id = _chat_id(query)
    src = get_source(chat_id, work_key) if chat_id is not None else None
    book = await db.add_book(
        book_base,
        user_id=user_id,
        source="personal",
        rec_source=src.rec_source if src else None,
    )
    await query.edit_message_reply_markup(
        reply_markup=_book_saved_keyboard(book.id, book.is_read),
    )
    await query.message.reply_text(
        f"*{book.title}* — сохранила в книги.", parse_mode="Markdown",
    )


async def _handle_read(query, book_id: int, *, user_id: int, read: bool):
    """Отметить книгу прочитанной/непрочитанной."""
    book = await db.update_book(book_id, user_id=user_id, is_read=read)
    if not book:
        await query.message.reply_text("Книгу не нашла.")
        return

    status = "прочитана ✅" if read else "вернула к чтению 📚"
    await query.edit_message_reply_markup(
        reply_markup=_book_saved_keyboard(book.id, book.is_read),
    )
    await query.message.reply_text(f"*{book.title}* — {status}", parse_mode="Markdown")
    if read:
        await query.message.reply_text(
            "Как тебе? Поставь оценку:",
            reply_markup=_rating_keyboard("book", book.id),
        )


def _book_saved_keyboard(book_id: int, is_read: bool) -> InlineKeyboardMarkup:
    """Ряд действий под сохранённой книгой."""
    read_btn = (
        InlineKeyboardButton("↺ Не прочитана", callback_data=f"unreadbook:{book_id}")
        if is_read
        else InlineKeyboardButton("✓ Прочитана", callback_data=f"readbook:{book_id}")
    )
    return InlineKeyboardMarkup([[read_btn]])


# ── rating (diary on bot) ───────────────────────────────────────────────────


def _rating_keyboard(kind: str, item_id: int) -> InlineKeyboardMarkup:
    """Ряд из пяти звёзд. callback ``rate:<kind>:<id>:<n>``."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⭐" * n, callback_data=f"rate:{kind}:{item_id}:{n}")
        for n in range(1, 6)
    ]])


async def _handle_rate(query, value: str, *, user_id: int, context):
    """Сохраняет личную оценку и предлагает добавить заметку (ForceReply)."""
    try:
        kind, id_str, n_str = value.split(":")
        item_id, rating = int(id_str), int(n_str)
    except ValueError:
        return

    if kind == "movie":
        await db.update_movie(item_id, user_id=user_id, user_rating=rating)
    else:
        await db.update_book(item_id, user_id=user_id, user_rating=rating)

    await query.edit_message_text(f"Оценка {'⭐' * rating} сохранена.")
    # Запоминаем, к чему относится следующая текстовая заметка-ответ.
    context.user_data["await_note"] = (kind, item_id)
    await query.message.reply_text(
        "Хочешь оставить заметку на память? Ответь на это сообщение "
        "(или просто пропусти).",
        reply_markup=ForceReply(selective=True),
    )


async def note_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ловит ответ-заметку после оценки. Регистрируется в группе -1.

    Если ждём заметку (``await_note`` в user_data) — сохраняем и стопаем
    дальнейшую обработку; иначе молча пропускаем, чтобы обычный текст ушёл
    в text_handler.
    """
    pending = context.user_data.get("await_note")
    if not pending:
        return
    kind, item_id = pending
    context.user_data.pop("await_note", None)

    note = (update.message.text or "").strip()
    user_row = await _get_or_create_user(update.effective_user)
    uid = user_row["id"]
    if kind == "movie":
        await db.update_movie(item_id, user_id=uid, user_note=note)
    else:
        await db.update_book(item_id, user_id=uid, user_note=note)

    await update.message.reply_text("Записала ✍️")
    raise ApplicationHandlerStop


async def _handle_delete(query, movie_id: int, *, user_id: int):
    """Удаление фильма из библиотеки юзера."""
    movie = await db.get_movie_by_id(movie_id, user_id=user_id)
    title = movie.title if movie else "Фильм"

    success = await db.delete_movie(movie_id, user_id=user_id)
    if not success:
        await query.message.reply_text("Фильм не нашла.")
        return

    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(f"«{title}» — удалила из списка.")
