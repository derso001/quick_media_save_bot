import asyncio
import logging
from aiogram import Bot, Dispatcher
from core.config import settings
from handlers import user_handlers
from database.db import init_db  # Імпорт ініціалізації БД

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    
    # Створюємо таблиці, якщо їх ще немає
    await init_db()
    logging.info("База даних успішно ініціалізована.")

    bot = Bot(token=settings.bot_token.get_secret_value())
    dp = Dispatcher()

    dp.include_router(user_handlers.router)

    logging.info("QuickSave Bot запускається...")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот зупинений.")