import asyncio
import logging
from aiogram import Bot, Dispatcher
from core.config import settings
from handlers import user_handlers

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    
    bot = Bot(token=settings.bot_token.get_secret_value())
    dp = Dispatcher()

    # Реєстрація хендлерів
    dp.include_router(user_handlers.router)

    logging.info("QuickSave Bot запускається...")
    
    # Скидаємо старі апдейти, які накопичились поки бот лежав
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот зупинений.")