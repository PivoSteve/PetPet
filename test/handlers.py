from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from modules.libraries.database import get_pet, create_pet, update_pet
from modules.libraries.constant import const
from datetime import datetime, timedelta
import asyncio
import random, math

router = Router()

## MARK: Utils
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
            [KeyboardButton(text="😴 Уложить спать"), KeyboardButton(text="📚 Учить трюк")]
            ],
            resize_keyboard=True
        )

def check_evolution(pet: dict) -> str:
    if all(pet[stat] >= 80 for stat in const.STATS):
        new_form = random.choice(["Супер", "Мега", "Ультра", "Гипер"]) + pet['name']
        update_pet(pet['user_id'], name=new_form)
        return f"🎉 Поздравляем! Твой питомец эволюционировал в {new_form}!"
    return ""

def apply_personality_effect(pet, stat, value):
    personality = pet['personality']
    if personality == 'Игривый':
        if stat in ['happiness', 'energy']:
            value *= 1.2
        elif stat == 'intelligence':
            value *= 0.9
    elif personality == 'Ленивый':
        if stat == 'energy':
            value *= 0.8
        elif stat in ['cleanliness', 'intelligence']:
            value *= 1.1
    elif personality == 'Любопытный':
        if stat == 'intelligence':
            value *= 1.2
        elif stat == 'cleanliness':
            value *= 0.9
    elif personality == 'Дружелюбный':
        if stat == 'happiness':
            value *= 1.2
        elif stat == 'intelligence':
            value *= 0.9
    elif personality == 'Застенчивый':
        if stat == 'happiness':
            value *= 0.9
        elif stat == 'intelligence':
            value *= 1.1
    return round(value)
## MARK END: Utils

## MARK: Command handlers
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
async def cmd_status(message: Message, custom_message: str = None):
    pet = get_pet(message.from_user.id)
    if pet:
        if custom_message is not None: 
            status_text = f"{custom_message}\n\n"
        else:
            status_text = f"Статус {pet['name']}:\n\n"
        status_emoji = {
            'hunger': '🍔 Голод',
            'cleanliness': '🚿 Чистота',
            'happiness': '😊 Счастье',
            'energy': '⚡ Энергия',
            'intelligence': '🧠 Интеллект',
        }
        for stat, emoji in status_emoji.items():
            value = pet[stat]
            bars = '█' * (value // 10) + '▒' * ((100 - value) // 10)
            status_text += f"{emoji}: {bars} {value}/100\n"
        
        status_text += f"\n🙃 Характер: {pet['personality']}\n"
        status_text += f"🥘 Любимая еда: {pet['favorite_food']}\n"
        status_text += f"🏅 Любимое занятие: {pet['favorite_activity']}\n"
        
        evolution_message = check_evolution(pet)
        if evolution_message:
            status_text += f"\n{evolution_message}"
        
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
    
    hunger_reduction = apply_personality_effect(pet, 'hunger', random.randint(20, 40))
    energy_boost = apply_personality_effect(pet, 'energy', random.randint(10, 30))
    happiness_boost = apply_personality_effect(pet, 'happiness', random.randint(5, 15))
    
    if food == pet['favorite_food']:
        hunger_reduction = int(hunger_reduction * 1.5)
        happiness_boost = int(happiness_boost * 2)
    
    new_hunger = max(const.MIN_STAT, pet['hunger'] - hunger_reduction)
    new_energy = min(const.MAX_STAT, pet['energy'] + energy_boost)
    new_happiness = min(const.MAX_STAT, pet['happiness'] + happiness_boost)
    
    update_pet(callback_query.from_user.id, 
               hunger=new_hunger, 
               energy=new_energy, 
               happiness=new_happiness, 
               last_fed=datetime.now().isoformat())
    
    response = f"🍔 Ты покормил {pet['name']} {food}.\n"
    if food == pet['favorite_food']:
        response += f"✨ Это его любимая еда! Он в восторге!\n"
    response += f"❕ Уровень голода теперь {new_hunger}/100, энергии {new_energy}/100, а счастья {new_happiness}/100."
    
    if pet['personality'] == 'Ленивый':
        response += f"\n😴 {pet['name']} ленится и не тратит много энергии на еду."
    elif pet['personality'] == 'Игривый':
        response += f"\n🎉 {pet['name']} игриво набрасывается на еду!"
    
    await callback_query.message.edit_text(response)

@router.message(F.text == "🚿 Помыть")
async def cmd_clean(message: Message):
    pet = get_pet(message.from_user.id)
    if pet:
        last_cleaned = parse_datetime(pet.get('last_cleaned'))
        if datetime.now() - last_cleaned > timedelta(minutes=25):
            cleaning_options = ["🧼 Мыло", "🧴 Шампунь", "🧽 Губка"]
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=option, callback_data=f"clean_{option.split()[1]}") for option in cleaning_options]
            ])
            await message.answer(f"Выбери, чем ты хочешь помыть {pet['name']}:", reply_markup=keyboard)
        else:
            await message.answer(f"❌ {pet['name']} уже чистый. Подожди немного перед следующим купанием.")
    else:
        await message.answer("❌ У тебя еще нет питомца. Используй /start чтобы создать его.")

@router.callback_query(F.data.startswith("clean_"))
async def process_cleaning(callback_query: CallbackQuery):
    cleaning_item = callback_query.data.split("_")[1]
    pet = get_pet(callback_query.from_user.id)
    
    cleanliness_boost = apply_personality_effect(pet, 'cleanliness', random.randint(30, 50))
    happiness_change = apply_personality_effect(pet, 'happiness', random.randint(-10, 20))
    
    if cleaning_item == "Мыло":
        cleanliness_boost += 10
    elif cleaning_item == "Шампунь":
        happiness_change += 10
    elif cleaning_item == "Губка":
        cleanliness_boost += 5
        happiness_change += 5
    
    new_cleanliness = min(const.MAX_STAT, pet['cleanliness'] + cleanliness_boost)
    new_happiness = max(const.MIN_STAT, min(const.MAX_STAT, pet['happiness'] + happiness_change))
    
    update_pet(callback_query.from_user.id, 
               cleanliness=new_cleanliness, 
               happiness=new_happiness, 
               last_cleaned=datetime.now().isoformat())
    
    response = f"✨ Ты помыл {pet['name']} с помощью {cleaning_item}.\n"
    response += f"Уровень чистоты теперь {new_cleanliness}/100, а счастья {new_happiness}/100.\n"
    
    if pet['personality'] == 'Ленивый':
        response += f"\n😴 {pet['name']} лениво позволяет себя мыть."
    elif pet['personality'] == 'Игривый':
        response += f"\n🎉 {pet['name']} игриво плескается в воде!"
    
    await callback_query.message.edit_text(response)

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
            
            await message.answer(f"😴 {pet['name']} спит, дождись его пробуждения чтобы продолжить ухаживать за ним!")
            await asyncio.sleep(sleep_duration)
            await cmd_status(message, f"✔ {pet['name']} поспал {sleep_duration} часов и хорошо отдохнул!\nВот его нынешние характеристики:")
        else:
            await message.answer(f"❌ {pet['name']} еще не устал. Подожди немного перед следующим сном.")
    else:
        await message.answer("❌ У тебя еще нет питомца. Используй /start чтобы создать его.")


@router.message(F.text == "📚 Учить трюк")
async def cmd_learn_trick(message: Message):
    pet = get_pet(message.from_user.id)
    if pet:
        result = learn_new_trick(pet)
        await message.answer(result)
    else:
        await message.answer("❌ У тебя еще нет питомца. Используй /start чтобы создать его.")

def learn_new_trick(pet):
    tricks = {
        "sit": "сидеть",
        "roll over": "перевернуться", 
        "fetch": "принести",
        "speak": "голос",
        "play dead": "притвориться мёртвым"
    }
    
    if pet['tricks'] is None:
        pet['tricks'] = []
    
    available_tricks = [t for t in tricks if tricks[t] not in pet['tricks']] 
    if not available_tricks:
        return f"🎓 {pet['name']} уже знает все доступные команды!"
    
    new_trick_key = random.choice(available_tricks)
    new_trick = tricks[new_trick_key]
    
    success_chance = (1 - math.sqrt(random.random()))
    intelligence_factor = pet['intelligence'] / 100
    
    if success_chance < intelligence_factor:
        pet['tricks'].append(new_trick) # FIXME: 
        
        intelligence_boost = apply_personality_effect(pet, 'intelligence', random.randint(5, 15))
        happiness_boost = apply_personality_effect(pet, 'happiness', random.randint(10, 20))
        
        new_intelligence = min(const.MAX_STAT, pet['intelligence'] + intelligence_boost)
        new_happiness = min(const.MAX_STAT, pet['happiness'] + happiness_boost)
        
        update_pet(pet['user_id'],
                   tricks=pet['tricks'],
                   intelligence=new_intelligence,
                   happiness=new_happiness)
        
        return f'🎉 {pet["name"]} успешно выучил новую команду: {new_trick}! Уровень интеллекта теперь {new_intelligence}/100, а счастья {new_happiness}/100.'
    else:
        energy_reduction = apply_personality_effect(pet, 'energy', random.randint(5, 10))
        new_energy = max(const.MIN_STAT, pet['energy'] - energy_reduction)
        
        update_pet(pet['user_id'], energy=new_energy)
        
        return f'😓 {pet["name"]} старался, но пока не смог выучить команду {new_trick}, ведь его интеллект {intelligence_factor:.2f} ниже ожидаемого {success_chance:.2f}. Уровень энергии теперь {new_energy}/100. Попробуй в следующий раз!'

@router.message(F.text == "🎮 Поиграть")
async def cmd_play(message: Message, state: FSMContext):
    pet = get_pet(message.from_user.id)
    if pet and can_play(pet):
        games = ["🧩 Загадки", "🔢 Математика", "🔤 Угадай слово"]
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=game, callback_data=f"play_{game.split()[1]}") for game in games[:3]],
            [InlineKeyboardButton(text=game, callback_data=f"play_{game.split()[1]}") for game in games[3:]]
        ])
        await message.answer("❔ Во что ты хочешь поиграть с питомцем?", reply_markup=keyboard)
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
        ("❔ У него огромный рот, Он зовется …", "бегемот"),
        ("❔ Не птица, а с крыльями, Не пчела, а над цветком", "бабочка"),
        ("❔ Что принадлежит вам, но другие используют это чаще?", "моё имя"),
        ("❔ Что можно видеть с закрытыми глазами?", "сон"),
        ("❔ Как человек может провести 8 дней без сна?", "спать ночью"),
        ("❔ Не живое, а на всех языках говорит.", "эхо"),
        ("❔ Что не вместится даже в самую большую кастрюлю?", "её крышка"),
        ("❔ Чем кончается лето и начинается осень?", "буква о"),
        ("❔ В году 12 месяцев. Семь из них имеют 31 день. Сколько месяцев в году имеют 28 дней?", "все"),
        ("❔ Кто ходит сидя?", "шахматист"),
        ("❔ Хвост пушистый, мех золотистый, В лесу живет, В деревне кур крадет", "лиса")    
    ]
    riddle, answer = random.choice(riddles)
    await state.update_data(correct_answer=answer)
    await callback_query.message.edit_text(f"❕ Отгадай загадку:\n\n{riddle}")
    await state.set_state(PetStates.waiting_for_riddle_answer)

async def start_math_game(callback_query: CallbackQuery, state: FSMContext):
    num1, num2 = random.randint(1, 10), random.randint(1, 10)
    operation = random.choice(['+', '-', '*'])
    question = f"{num1} {operation} {num2}"
    answer = eval(question)
    await state.update_data(correct_answer=answer)
    await callback_query.message.edit_text(f"❕ Реши пример:\n\n{question} = ?")
    await state.set_state(PetStates.waiting_for_math_answer)

async def start_word_guess_game(callback_query: CallbackQuery, state: FSMContext):
    words = ["кот", "собака", "попугай", "хомяк", "черепаха", "конь", "лиса", "лето"]
    word = random.choice(words)
    await state.update_data(correct_answer=word, attempts=5)
    masked_word = "".join(["🕳" if i != 0 else w for i, w in enumerate(word)])
    await callback_query.message.edit_text(f"❕ Угадай слово:\n\n{masked_word}\n\nУ тебя 5 попыток.")
    await state.set_state(PetStates.waiting_for_word_guess)

@router.message(PetStates.waiting_for_riddle_answer)
async def process_riddle_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    correct_answer = data.get("correct_answer")
    user_answer = str(message.text.lower())
    pet = get_pet(message.from_user.id)
    
    if user_answer == correct_answer:
        await process_correct_answer(message, state, "Загадки")
    else:
        await process_wrong_answer(message, state, f"Правильный ответ: {correct_answer}")

    await state.clear()

@router.message(PetStates.waiting_for_math_answer)
async def process_math_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    correct_answer = data.get("correct_answer")
    
    try:
        user_answer = int(message.text)
        if user_answer == correct_answer:
            await process_correct_answer(message, state, "Математика")
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
        await process_correct_answer(message, state, "Угадайки")
    else:
        attempts -= 1
        if attempts > 0:
            masked_word = "".join([w if w in message.text.lower() else "_" for w in correct_answer])
            await message.answer(f"❌ Неверно. Осталось попыток: {attempts}\n\n{masked_word}")
            await state.update_data(attempts=attempts)
        else:
            await process_wrong_answer(message, state, f"Правильное слово: {correct_answer}")

## MARK: Some more utils
def can_play(pet):
    last_played = parse_datetime(pet.get('last_played'))
    return datetime.now() - last_played > timedelta(minutes=10)

async def process_correct_answer(message: Message, state: FSMContext, game_type):
    pet = get_pet(message.from_user.id)
    happiness_boost = apply_personality_effect(pet, 'happiness', random.randint(20, 40))
    intelligence_boost = apply_personality_effect(pet, 'intelligence', random.randint(15, 30))
    energy_reduction = apply_personality_effect(pet, 'energy', random.randint(10, 20))
    
    if game_type == pet['favorite_activity']:
        happiness_boost = int(happiness_boost * 1.5)
        intelligence_boost = int(intelligence_boost * 1.5)
    
    new_happiness = min(const.MAX_STAT, pet['happiness'] + happiness_boost)
    new_intelligence = min(const.MAX_STAT, pet['intelligence'] + intelligence_boost)
    new_energy = max(const.MIN_STAT, pet['energy'] - energy_reduction)
    
    update_pet(message.from_user.id, 
               happiness=new_happiness, 
               intelligence=new_intelligence, 
               energy=new_energy,
               last_played=datetime.now().isoformat())
    
    response = f"✨ Отлично! {pet['name']} в восторге от вашей совместной игры в {game_type}. "
    if game_type == pet['favorite_activity']:
        response += "Это его любимое занятие!"
    response += f"\nУровень счастья теперь {new_happiness}/100, интеллекта {new_intelligence}/100, а энергии {new_energy}/100."
    
    if pet['personality'] == 'Любопытный':
        response += f"\n\n🧐 {pet['name']} с любопытством изучает новые знания!"
    elif pet['personality'] == 'Застенчивый':
        response += f"\n\n😊 {pet['name']} застенчиво радуется успеху."
    
    await message.answer(response)
    await state.clear()

async def process_wrong_answer(message: Message, state: FSMContext, correct_answer):
    pet = get_pet(message.from_user.id)
    new_happiness = min(100, pet['happiness'] + 10)
    new_intelligence = min(100, pet['intelligence'] - random.randint(2, 15))
    update_pet(message.from_user.id, happiness=new_happiness, intelligence=new_intelligence, last_played=datetime.now().isoformat())
    await message.answer(f"❌ К сожалению, это неправильный ответ. {correct_answer}.\n{pet['name']} все равно доволен, что вы играли вместе. Уровень счастья теперь {new_happiness}/100, а интеллекта {new_intelligence}/100.")
    await state.clear()

## MARK END: Some more utils