import asyncio
import logging
import sys
from app.bot import bot, dp

# Налаштовуємо красиве логування в консоль
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def main():
    logger.info("Bot startup...")
    try:
        # Видаляємо вебхуки, щоб уникнути конфліктів при локальному тестуванні
        await bot.delete_webhook(drop_pending_updates=True)
        
        # Запускаємо асинхронний polling
        logger.info("Polling started...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Критична помилка під час роботи бота: {e}")
    finally:
        await bot.session.close()
        logger.info("🔌 Сесію бота закрито.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Бот зупинений.")
