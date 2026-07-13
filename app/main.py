import asyncio
import logging
import sys
import os
from aiohttp import web
from aiogram import types

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

WEBHOOK_PATH = "/webhook"

async def on_startup(app):
    """Викликається при старті сервера."""
    logger.info("Bot startup...")
    # Render автоматично задає RENDER_EXTERNAL_URL (напр. https://my-bot.onrender.com)
    webhook_url = os.getenv("RENDER_EXTERNAL_URL", "")
    if webhook_url:
        full_url = f"{webhook_url}{WEBHOOK_PATH}"
        logger.info(f"Встановлюю Webhook: {full_url}")
        await bot.set_webhook(full_url, drop_pending_updates=True)
    else:
        logger.warning("RENDER_EXTERNAL_URL не знайдено! Працюємо локально?")

async def on_shutdown(app):
    """Викликається при вимкненні сервера."""
    logger.info("Shutting down...")
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.session.close()

async def delayed_processing(update: types.Update):
    """Затримка гарантує, що aiohttp встигне віддати Telegram 200 OK до початку важких розрахунків."""
    await asyncio.sleep(1)
    try:
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.error(f"Помилка фонової обробки: {e}")

async def handle_webhook(request):
    """Обробник вебхуків від Telegram."""
    try:
        update_data = await request.json()
        update = types.Update.model_validate(update_data, context={"bot": bot})
        
        # МАГІЯ: Відправляємо задачу у фон і не чекаємо її завершення!
        asyncio.create_task(delayed_processing(update))
    except Exception as e:
        logger.error(f"Помилка валідації вебхука: {e}")
        
    # Миттєво віддаємо 200 OK, щоб Telegram не обірвав з'єднання
    return web.Response(text="OK")

async def healthcheck(request):
    """Ендпоінт для перевірки 'здоров'я' сервісу (щоб Render бачив, що ми живі)."""
    return web.Response(text="Bot is running and healthy!")

def main():
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle_webhook)
    app.router.add_get("/", healthcheck)  # Головна сторінка
    
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    # Render передає порт через змінну середовища PORT
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Запускаємо aiohttp сервер на порту {port}")
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
