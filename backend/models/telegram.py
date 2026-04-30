from pydantic import BaseModel


class TelegramImportRequest(BaseModel):
    """Запрос на парсинг публичного поста t.me."""
    url: str
