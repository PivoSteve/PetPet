from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from modules.libraries.database import get_pet, create_pet, update_pet
from datetime import datetime, timedelta
import random

router = Router()

class PetStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_game_choice = State()
    waiting_for_riddle_answer = State()
    waiting_for_math_answer = State()
    waiting_for_word_guess = State()

def parse_datetime(date_string):
    if not date_string:
        return datetime.min
    try:
        return datetime.fromisoformat(date_string)
    except (TypeError, ValueError):
        return datetime.min

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Статус"), KeyboardButton(text="🍽 Покормить")],
            [KeyboardButton(text="🚿 Помыть"), KeyboardButton(text="🎮 Поиграть")],
            [KeyboardButton(text="😴 Уложить спать")]
        ],
        resize_keyboard=True
    )

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    pet = get_pet(message.from_user.id)
    if pet:
        await message.answer(f"✔ С возвращением! Твой питомец {pet['name']} ждет тебя!", reply_markup=get_main_keyboard())
    else:
        await message.answer("✔ Привет! Давай создадим твоего виртуального питомца. Как ты хочешь его назвать?")
        await state.set_state(PetStates.waiting_for_name)

@router.message(PetStates.waiting_for_name)
async def create_new_pet(message: Message, state: FSMContext):
    create_pet(message.from_user.id, message.text)
    pet = get_pet(message.from_user.id)
    await cmd_status(message, f"✔ Отлично! Твой новый питомец {pet['name']} создан.\nУхаживай за ним хорошо! Вот его начальные характеристики:")
    await state.clear()

@router.message(F.text == "🔍 Статус")
async def cmd_status(message: Message, status_text: str):
    pet = get_pet(message.from_user.id)
    if pet:
        status_emoji = {
            'hunger': '🍔 Голод',
            'cleanliness': '🚿 Чистота',
            'happiness': '😊 Счастье',
            'energy': '⚡ Энергия',
            'intelligence': '🧠 Интеллект',
        }
        status_text += f"🙃 Характер: {pet['personality']}\n🥘 Любимая еда: {pet['favorite_food']}\n🏅 Любимое занятие: {pet['favorite_activity']}\n"
        for stat, emoji in status_emoji.items():
            value = pet[stat]
            bars = '█' * (value // 10) + '▒' * ((100 - value) // 10)
            status_text += f"{emoji}: {bars} {value}/100\n"
        await message.answer(status_text)
    else:
        await message.answer("❌ У тебя еще нет питомца. Используй /start чтобы создать его.")

@router.message(F.text == "🍽 Покормить")
async def cmd_feed(message: Message):
    pet = get_pet(message.from_user.id)
    if pet:
        last_fed = parse_datetime(pet.get('last_fed'))
        if datetime.now() - last_fed > timedelta(minutes=15):
            foods = ["🍎 Яблоко", "🥕 Морковь", "🍌 Банан", "🥜 Орехи", "🍓 Ягоды"]
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=food, callback_data=f"feed_{food.split()[1]}") for food in foods[:3]],
                [InlineKeyboardButton(text=food, callback_data=f"feed_{food.split()[1]}") for food in foods[3:]]
            ])
            await message.answer("✔ Чем ты хочешь покормить питомца?", reply_markup=keyboard)
        else:
            await message.answer(f"❌ {pet['name']} не голоден. Подожди немного перед следующим кормлением.")
    else:
        await message.answer("❌ У тебя еще нет питомца. Используй /start чтобы создать его.")

@router.callback_query(F.data.startswith("feed_"))
async def process_feed(callback_query: CallbackQuery):
    food = callback_query.data.split("_")[1]
    pet = get_pet(callback_query.from_user.id)
    new_hunger = max(0, pet['hunger'] - 30)
    new_energy = min(100, pet['energy'] + 20)
    happiness_boost = 15 if food == pet['favorite_food'] else 5
    new_happiness = min(100, pet['happiness'] + happiness_boost)
    update_pet(callback_query.from_user.id, hunger=new_hunger, energy=new_energy, happiness=new_happiness, last_fed=datetime.now().isoformat())
    
    response = f"Ты покормил {pet['name']} {food}. "
    if food == pet['favorite_food']:
        response += f"✔ Это его любимая еда! Он очень доволен! "
    response += f"✔ Уровень голода теперь {new_hunger}/100, энергии {new_energy}/100, а счастья {new_happiness}/100."
    
    await callback_query.message.edit_text(response)

@router.message(F.text == "🚿 Помыть")
async def cmd_clean(message: Message):
    pet = get_pet(message.from_user.id)
    if pet:
        last_cleaned = parse_datetime(pet.get('last_cleaned'))
        if datetime.now() - last_cleaned > timedelta(minutes=25):
            new_cleanliness = min(100, pet['cleanliness'] + 40)
            new_happiness = min(100, pet['happiness'] + 10)
            update_pet(message.from_user.id, cleanliness=new_cleanliness, happiness=new_happiness, last_cleaned=datetime.now().isoformat())
            await message.answer(f"✔ Ты помыл {pet['name']}. Уровень чистоты теперь {new_cleanliness}/100, а счастья {new_happiness}/100.")
        else:
            await message.answer(f"❌ {pet['name']} уже чистый. Подожди немного перед следующим купанием.")
    else:
        await message.answer("❌ У тебя еще нет питомца. Используй /start чтобы создать его.")

@router.message(F.text == "🎮 Поиграть")
async def cmd_play(message: Message, state: FSMContext):
    pet = get_pet(message.from_user.id)
    if pet and can_play(pet):
        games = ["🧩 Загадки", "🔢 Математика", "🔤 Угадай слово"]
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=game, callback_data=f"play_{game.split()[1]}") for game in games[:3]],
            [InlineKeyboardButton(text=game, callback_data=f"play_{game.split()[1]}") for game in games[3:]]
        ])
        await message.answer("✔ Во что ты хочешь поиграть с питомцем?", reply_markup=keyboard)
        await state.set_state(PetStates.waiting_for_game_choice)
    else:
        await message.answer(f"❌ {pet['name']} устал. Подожди немного перед следующей игрой.")

@router.callback_query(PetStates.waiting_for_game_choice)
async def process_game_choice(callback_query: CallbackQuery, state: FSMContext):
    game = callback_query.data.split("_")[1]
    pet = get_pet(callback_query.from_user.id)
    
    if game == "Загадки":
        await start_riddle_game(callback_query, state)
    elif game == "Математика":
        await start_math_game(callback_query, state)
    elif game == "Угадай":
        await start_word_guess_game(callback_query, state)
        
async def start_riddle_game(callback_query: CallbackQuery, state: FSMContext):
    riddles = [
        ("✔ У него огромный рот, Он зовется …", "бегемот"),
        ("✔ Не птица, а с крыльями, Не пчела, а над цветком", "бабочка"),
        ("✔ Что принадлежит вам, но другие используют это чаще?", "моё имя"),
        ("✔ Что можно видеть с закрытыми глазами?", "сон"),
        ("✔ Как человек может провести 8 дней без сна?", "спать ночью"),
        ("✔ Не живое, а на всех языках говорит.", "эхо"),
        ("✔ Что не вместится даже в самую большую кастрюлю?", "её крышка"),
        ("✔ Чем кончается лето и начинается осень?", "буква о"),
        ("✔ В году 12 месяцев. Семь из них имеют 31 день. Сколько месяцев в году имеют 28 дней?", "все"),
        ("✔ Кто ходит сидя?", "шахматисты"),
        ("✔ Хвост пушистый, мех золотистый, В лесу живет, В деревне кур крадет", "лиса")    
    ]
    riddle, answer = random.choice(riddles)
    await state.update_data(correct_answer=answer)
    await callback_query.message.edit_text(f"✔ Отгадай загадку:\n\n{riddle}")
    await state.set_state(PetStates.waiting_for_riddle_answer)

async def start_math_game(callback_query: CallbackQuery, state: FSMContext):
    num1, num2 = random.randint(1, 10), random.randint(1, 10)
    operation = random.choice(['+', '-', '*'])
    question = f"{num1} {operation} {num2}"
    answer = eval(question)
    await state.update_data(correct_answer=answer)
    await callback_query.message.edit_text(f"✔ Реши пример:\n\n{question} = ?")
    await state.set_state(PetStates.waiting_for_math_answer)

async def start_word_guess_game(callback_query: CallbackQuery, state: FSMContext):
    words = ["кот", "собака", "попугай", "хомяк", "черепаха"]
    word = random.choice(words)
    await state.update_data(correct_answer=word, attempts=3)
    masked_word = "".join(["_" if i != 0 else w for i, w in enumerate(word)])
    await callback_query.message.edit_text(f"✔ Угадай слово:\n\n{masked_word}\n\nУ тебя 3 попытки.")
    await state.set_state(PetStates.waiting_for_word_guess)

@router.message(PetStates.waiting_for_math_answer)
async def process_math_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    correct_answer = data.get("correct_answer")
    
    try:
        user_answer = int(message.text)
        if user_answer == correct_answer:
            await process_correct_answer(message, state, "математическую задачу")
        else:
            await process_wrong_answer(message, state, f"Правильный ответ: {correct_answer}")
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число.")

@router.message(PetStates.waiting_for_word_guess)
async def process_word_guess(message: Message, state: FSMContext):
    data = await state.get_data()
    correct_answer = data.get("correct_answer")
    attempts = data.get("attempts", 3)
    
    if message.text.lower() == correct_answer:
        await process_correct_answer(message, state, "слово")
    else:
        attempts -= 1
        if attempts > 0:
            masked_word = "".join([w if w in message.text.lower() else "_" for w in correct_answer])
            await message.answer(f"❌ Неверно. Осталось попыток: {attempts}\n\n{masked_word}")
            await state.update_data(attempts=attempts)
        else:
            await process_wrong_answer(message, state, f"Правильное слово: {correct_answer}")

def can_play(pet):
    last_played = parse_datetime(pet.get('last_played'))
    return datetime.now() - last_played > timedelta(minutes=10)

async def process_correct_answer(message: Message, state: FSMContext, game_type):
    pet = get_pet(message.from_user.id)
    new_happiness = min(100, pet['happiness'] + 30)
    new_intelligence = min(100, pet['intelligence'] + 20)
    update_pet(message.from_user.id, happiness=new_happiness, intelligence=new_intelligence, last_played=datetime.now().isoformat())
    await message.answer(f"✔ Правильно! {pet['name']} очень рад, что вы разгадали {game_type} вместе. Уровень счастья теперь {new_happiness}/100, а интеллекта {new_intelligence}/100.")
    await state.clear()

async def process_wrong_answer(message: Message, state: FSMContext, correct_answer):
    pet = get_pet(message.from_user.id)
    new_happiness = min(100, pet['happiness'] + 10)
    new_intelligence = min(100, pet['intelligence'] - 10)
    update_pet(message.from_user.id, happiness=new_happiness, intelligence=new_intelligence, last_played=datetime.now().isoformat())
    await message.answer(f"❌ К сожалению, это неправильный ответ. {correct_answer}. Но {pet['name']} все равно доволен, что вы играли вместе. Уровень счастья теперь {new_happiness}/100, а интеллекта {new_intelligence}/100.")
    await state.clear()

@router.message(F.text == "😴 Уложить спать")
async def pet_sleep(message: Message):
    pet = get_pet(message.from_user.id)
    if pet:
        last_slept = parse_datetime(pet.get('last_slept'))
        if datetime.now() - last_slept > timedelta(minutes=25) or pet.get('energy') < 40:
            sleep_duration = random.randint(2, 7)
            new_energy = min(100, pet['energy'] + sleep_duration * 10)
            new_hunger = min(100, pet['hunger'] + sleep_duration * 5)
            new_happiness = max(0, pet['happiness'] - sleep_duration * 2)
            new_cleanliness = max(0, pet['cleanliness'] - sleep_duration * 3)
            time_asleep = datetime.now() - timedelta(hours=sleep_duration)
            time_asleep_str = time_asleep.isoformat()
            
            update_pet(message.from_user.id, 
                       energy=new_energy, 
                       hunger=new_hunger, 
                       happiness=new_happiness, 
                       cleanliness=new_cleanliness, 
                       last_slept=datetime.now().isoformat(),
                       last_fed=time_asleep_str,
                       last_cleaned=time_asleep_str,
                       last_played=time_asleep_str)
            
            await asyncio.sleep(sleep_duration)
            await message.answer(f"{pet['name']} поспал {sleep_duration} часов и хорошо отдохнул!\n")
        else:
            await message.answer(f"❌ {pet['name']} еще не устал. Подожди немного перед следующим сном.")
    else:
        await message.answer("❌ У тебя еще нет питомца. Используй /start чтобы создать его.")