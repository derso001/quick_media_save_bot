from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    user_name = message.from_user.first_name if message.from_user else "друже"
    await message.answer(
        f"Привіт, {user_name}! 👋\n\n"
        "Я **QuickSave Bot** — допомагаю зберігати медіа без водяних знаків у найкращій якості.\n\n"
        "⚡️ **Зараз підтримується:** TikTok\n"
        "🔜 **У розробці:** Instagram Reels, YouTube Shorts\n\n"
        "Просто надішли мені посилання на відео з TikTok!"
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 **Як користуватися ботом:**\n\n"
        "1. Скопіюй посилання на відео в TikTok.\n"
        "2. Надішли його повідомленням у цей чат.\n"
        "3. Бот автоматично надішле тобі готове відео без водяних знаків."
    )