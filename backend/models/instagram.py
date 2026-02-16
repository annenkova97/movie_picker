from pydantic import BaseModel


class InstagramImportRequest(BaseModel):
    """Запрос на импорт фильма(ов) из Instagram Reel по ссылке."""
    url: str
    vision: bool = False
