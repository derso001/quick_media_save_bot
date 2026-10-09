from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


class MediaCallback(CallbackData, prefix="media"):
    action: str
    media_id: str


def get_media_keyboard(media_id: str) -> InlineKeyboardMarkup:
    """Клавіатура з кнопкою завантаження аудіо."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎵 Завантажити аудіо (MP3)",
                    callback_data=MediaCallback(action="audio", media_id=media_id).pack(),
                )
            ]
        ]
    )
    return keyboard