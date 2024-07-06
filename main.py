
import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.callback_answer import CallbackAnswerMiddleware
from modules.handlers.handlers import router
from modules.libraries.database import init_db, get_all_pets, update_pet
from datetime import datetime, timedelta
TOKEN_FILE_PATH = '/home/syra/2501/tg_bots/petpet/TOKEN' ## MARK: CHANGE TOKEN PATH
LOGGING_PATH = './logs'

def read_token_from_file(file_path):
    try:
        with open(file_path, 'r') as file:
            token = file.read().strip()
            return token
    except Exception as e:
        raise ValueError(f"Error reading token from file: {e}")

TOKEN = read_token_from_file(TOKEN_FILE_PATH)
if not TOKEN:
    raise ValueError("No BOT_TOKEN found in the token file. Please check your token.")

async def periodic_update():
    while True:
        pets = get_all_pets()
        for pet in pets:
            new_hunger = min(100, pet['hunger'] + 5)
            new_cleanliness = max(0, pet['cleanliness'] - 5)
            new_happiness = max(0, pet['happiness'] - 3)
            new_energy = min(100, pet['energy'] + 10)
            update_pet(pet['user_id'], hunger=new_hunger, cleanliness=new_cleanliness, happiness=new_happiness, energy=new_energy)
        await asyncio.sleep(3600)  # Обновление каждый час

async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router)
    
    dp.callback_query.middleware(CallbackAnswerMiddleware())
    
    init_db() 

    asyncio.create_task(periodic_update())

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if not os.path.exists(LOGGING_PATH):
    os.makedirs(LOGGING_PATH)
log_filename = f'pp_{datetime.now().strftime("%d-%m-%Y_%H-%M-%S")}.log'

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s]:%(levelname)s:%(funcName)s:%(message)s',
        datefmt='%Y-%m-%d|%H:%M:%S',
        handlers=[
            logging.FileHandler(f"{LOGGING_PATH}/{log_filename}", mode='a', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    asyncio.run(main())