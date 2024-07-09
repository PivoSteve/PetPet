
import asyncio
import logging
import os
import sys
import random
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.callback_answer import CallbackAnswerMiddleware
from modules.handlers.handlers import router
from modules.libraries.database import init_db, get_all_pets, update_pet
from datetime import datetime, timedelta
from modules.libraries.constant import const
if os.name == 'nt':  ## MARK: CHANGE TOKEN 
    TOKEN_FILE_PATH = 'C:/2501/petpet/data/TOKEN'
else:
    TOKEN_FILE_PATH = '/home/syra/2501/tg_bots/petpet/TOKEN'
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

async def notify_user(user_id: int, event: str, bot: Bot):
    try:
        await bot.send_message(user_id, f"🎉 Событие у твоего питомца!\n\n{event}")
    except TelegramAPIError:
        logging.error(f"Failed to send notification to user {user_id}")

async def periodic_update(bot: Bot):
    while True:
        pets = get_all_pets()
        for pet in pets:
            updates = {}
            for stat in const.STATS:
                if stat in ['hunger', 'energy']:
                    updates[stat] = min(const.MAX_STAT, pet[stat] + const.STAT_DECAY_RATE)
                    print(updates[stat])
                else:
                    updates[stat] = max(const.MIN_STAT, pet[stat] - const.STAT_DECAY_RATE)
                    print(updates[stat])
            if random.random() < 0.3:  # дефолт: 30% шанс
                event, effect = random_event()
                updates.update(effect)
                await notify_user(pet['user_id'], event, bot)
            update_pet(pet['user_id'], **updates)
        await asyncio.sleep(3600) # дефолт: 3600

def random_event():
    events = [
        ("Твой питомец нашел вкусняшку.\nОн насытился и стал немного счастливее!", {'hunger': -10, 'happiness': 10}),
        ("Твой питомец поиграл с соседским питомцем.\nОн немного устал, но стал счастливее!", {'energy': -10, 'happiness': 15}),
        ("Твой питомец научился новому трюку.\nОн стал умнее, но устал!", {'intelligence': 10, 'energy': -5}),
        ("Твой питомец испугался громкого звука.\nЕму стало грустно!", {'happiness': -10, 'energy': 5}),
        ("Твой питомец поспал на солнышке.\nОн испачкался, но выспался!", {'energy': 15, 'cleanliness': -5}),
        ("Твой питомец нашел интересную книгу.\nНе поняв ни слова он стал немного умнее и счатливее!", {'intelligence': 15, 'happiness': 5}),
        ("Твой питомец устроил беспорядок.\nОн испачкался, но стал немного счастливее!", {'cleanliness': -15, 'happiness': 5}),
        ("Твой питомец помог соседу и получил награду.\nОн устал, но стал счастливее!", {'happiness': 20, 'energy': -10}),
        ("Твой питомец участвовал в местном конкурсе талантов и выиграл.\nОн стал умнее и счастливее, хоть и устал!", {'intelligence': 10, 'happiness': 15, 'energy': -15}),
        ("Твой питомец участвовал в местном конкурсе талантов и проиграл.\nЕму стало грустно, так еще и он устал!", {'happiness': -20, 'energy': -15}),
        ("Твой питомец обнаружил секретный проход в доме.\nЕму стало счастливее!", {'happiness': 25, 'intelligence': 5})
    ]
    return random.choice(events)

async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router)
    
    dp.callback_query.middleware(CallbackAnswerMiddleware())
    
    init_db() 

    asyncio.create_task(periodic_update(bot))

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