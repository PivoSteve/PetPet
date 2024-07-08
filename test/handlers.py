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
    waiting_for_training_choice = State()
    waiting_for_training_intensity = State()

TRAINING_TYPES = {
    "Бег": {"emoji": "🏃‍♂️", "primary": "stamina", "secondary": "agility"},
    "Плавание": {"emoji": "🏊‍♂️", "primary": "stamina", "secondary": "strength"},
    "Прыжки": {"emoji": "🦘", "primary": "agility", "secondary": "stamina"},
    "Силовые упражнения": {"emoji": "🏋️‍♂️", "primary": "strength", "secondary": "stamina"},
    "Растяжка": {"emoji": "🧘‍♂️", "primary": "flexibility", "secondary": "agility"},
    "Игры на сообразительность": {"emoji": "🧠", "primary": "intelligence", "secondary": "happiness"}
}

INTENSITY_LEVELS = {
    "Легкая": {"multiplier": 0.5, "energy_cost": 10},
    "Средняя": {"multiplier": 1.0, "energy_cost": 20},
    "Интенсивная": {"multiplier": 1.5, "energy_cost": 30}
}

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
            [KeyboardButton(text="😴 Уложить спать"), KeyboardButton(text="💪 Тренировать")]
        ],
        resize_keyboard=True
    )

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    pet = get_pet(message.from_user.id)
    if pet:
        await message.answer(f"С возвращением! Твой питомец {pet['name']} ждет тебя!", reply_markup=get_main_keyboard())
    else:
        await message.answer("Привет! Давай создадим твоего виртуального питомца. Как ты хочешь его назвать?")
        await state.set_state(PetStates.waiting_for_name)

@router.message(PetStates.waiting_for_name)
async def create_new_pet(message: Message, state: FSMContext):
    create_pet(message.from_user.id, message.text)
    pet = get_pet(message.from_user.id)
    await message.answer(
        f"Отлично! Твой новый питомец {message.text} создан. Вот его характеристики:\n"
        f"Характер: {pet['personality']}\n"
        f"Любимая еда: {pet['favorite_food']}\n"
        f"Любимое занятие: {pet['favorite_activity']}\n"
        f"Ухаживай за ним хорошо!",
        reply_markup=get_main_keyboard()
    )
    await state.clear()

@router.message(F.text == "🔍 Статус")
async def cmd_status(message: Message):
    pet = get_pet(message.from_user.id)
    if pet:
        status_emoji = {
            'hunger': '🍔 Голод',
            'cleanliness': '🚿 Чистота',
            'happiness': '😊 Счастье',
            'energy': '⚡ Энергия',
            'intelligence': '🧠 Интеллект',
            'strength': '💪 Сила'
        }
        status_text = f"Статус {pet['name']}:\n"
        for stat, emoji in status_emoji.items():
            value = pet[stat]
            bars = '█' * (value // 10) + '▒' * ((100 - value) // 10)
            status_text += f"{emoji}: {bars} {value}/100\n"
        await message.answer(status_text)
    else:
        await message.answer("У тебя еще нет питомца. Используй /start чтобы создать его.")

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
            await message.answer("Чем ты хочешь покормить питомца?", reply_markup=keyboard)
        else:
            await message.answer(f"{pet['name']} не голоден. Подожди немного перед следующим кормлением.")
    else:
        await message.answer("У тебя еще нет питомца. Используй /start чтобы создать его.")

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
        response += f"Это его любимая еда! Он очень доволен! "
    response += f"Уровень голода теперь {new_hunger}/100, энергии {new_energy}/100, а счастья {new_happiness}/100."
    
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
            await message.answer(f"Ты помыл {pet['name']}. Уровень чистоты теперь {new_cleanliness}/100, а счастья {new_happiness}/100.")
        else:
            await message.answer(f"{pet['name']} уже чистый. Подожди немного перед следующим купанием.")
    else:
        await message.answer("У тебя еще нет питомца. Используй /start чтобы создать его.")

@router.message(F.text == "🎮 Поиграть")
async def cmd_play(message: Message, state: FSMContext):
    pet = get_pet(message.from_user.id)
    if pet:
        last_played = parse_datetime(pet.get('last_played'))
        if datetime.now() - last_played > timedelta(minutes=10):
            games = ["🧩 Загадки", "🏃‍♂️ Прятки", "⚽ Мяч", "🧠 Головоломки"]
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=game, callback_data=f"play_{game.split()[1]}") for game in games[:2]],
                [InlineKeyboardButton(text=game, callback_data=f"play_{game.split()[1]}") for game in games[2:]]
            ])
            await message.answer("Во что ты хочешь поиграть с питомцем?", reply_markup=keyboard)
            await state.set_state(PetStates.waiting_for_game_choice)
        else:
            await message.answer(f"{pet['name']} устал. Подожди немного перед следующей игрой.")
    else:
        await message.answer("У тебя еще нет питомца. Используй /start чтобы создать его.")

@router.callback_query(PetStates.waiting_for_game_choice)
async def process_game_choice(callback_query: CallbackQuery, state: FSMContext):
    game = callback_query.data.split("_")[1]
    pet = get_pet(callback_query.from_user.id)
    
    if game == "Загадки":
        riddles = [
            ("У него огромный рот, Он зовется …", "бегемот"),
            ("Не птица, а с крыльями, Не пчела, а над цветком", "бабочка"),
            ("Хвост пушистый, мех золотистый, В лесу живет, В деревне кур крадет", "лиса")
        ]
        riddle, answer = random.choice(riddles)
        await state.update_data(correct_answer=answer)
        await callback_query.message.edit_text(f"Отгадай загадку:\n\n{riddle}")
        await state.set_state(PetStates.waiting_for_riddle_answer)
    else:
        happiness_boost = 25 if game == pet['favorite_activity'] else 15
        new_happiness = min(100, pet['happiness'] + happiness_boost)
        new_energy = max(0, pet['energy'] - 30)
        new_intelligence = min(100, pet['intelligence'] + 10)
        update_pet(callback_query.from_user.id, happiness=new_happiness, energy=new_energy, intelligence=new_intelligence, last_played=datetime.now().isoformat())
        
        response = f"Ты поиграл с {pet['name']} в {game}. "
        if game == pet['favorite_activity']:
            response += f"Это его любимое занятие! Он в восторге! "
        response += f"Уровень счастья теперь {new_happiness}/100, энергии {new_energy}/100, а интеллекта {new_intelligence}/100."
        
        await callback_query.message.edit_text(response)
        await state.clear()

@router.message(PetStates.waiting_for_riddle_answer)
async def process_riddle_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    correct_answer = data.get("correct_answer")
    pet = get_pet(message.from_user.id)
    
    if message.text.lower() == correct_answer:
        new_happiness = min(100, pet['happiness'] + 30)
        new_intelligence = min(100, pet['intelligence'] + 20)
        update_pet(message.from_user.id, happiness=new_happiness, intelligence=new_intelligence, last_played=datetime.now().isoformat())
        await message.answer(f"Правильно! {pet['name']} очень рад, что вы разгадали загадку вместе. Уровень счастья теперь {new_happiness}/100, а интеллекта {new_intelligence}/100.")
    else:
        new_happiness = min(100, pet['happiness'] + 10)
        new_intelligence = min(100, pet['intelligence'] + 5)
        update_pet(message.from_user.id, happiness=new_happiness, intelligence=new_intelligence, last_played=datetime.now().isoformat())
        await message.answer(f"К сожалению, это неправильный ответ. Правильный ответ: {correct_answer}. Но {pet['name']} все равно доволен, что вы играли вместе. Уровень счастья теперь {new_happiness}/100, а интеллекта {new_intelligence}/100.")
    
    await state.clear()

@router.message(F.text == "😴 Уложить спать")
async def pet_sleep(message: Message):
    pet = get_pet(message.from_user.id)
    if pet:
        last_slept = parse_datetime(pet.get('last_slept'))
        if datetime.now() - last_slept > timedelta(minutes=25):
            sleep_duration = random.randint(4, 8)
            new_energy = min(100, pet['energy'] + sleep_duration * 10)
            new_hunger = min(100, pet['hunger'] + sleep_duration * 5)
            new_happiness = max(0, pet['happiness'] - sleep_duration * 2)
            new_cleanliness = max(0, pet['cleanliness'] - sleep_duration * 3)
            
            update_pet(message.from_user.id, 
                       energy=new_energy, 
                       hunger=new_hunger, 
                       happiness=new_happiness, 
                       cleanliness=new_cleanliness, 
                       last_slept=datetime.now().isoformat())
            
            await message.answer(f"{pet['name']} поспал {sleep_duration} часов и хорошо отдохнул!\n"
                                 f"Энергия: {new_energy}/100\n"
                                 f"Голод: {new_hunger}/100\n"
                                 f"Счастье: {new_happiness}/100\n"
                                 f"Чистота: {new_cleanliness}/100")
        else:
            await message.answer(f"{pet['name']} еще не устал. Подожди немного перед следующим сном.")
    else:
        await message.answer("У тебя еще нет питомца. Используй /start чтобы создать его.")

@router.message(F.text == "💪 Тренировать")
async def train_pet(message: Message, state: FSMContext):
    pet = get_pet(message.from_user.id)
    if pet:
        last_trained = parse_datetime(pet.get('last_trained'))
        if datetime.now() - last_trained > timedelta(minutes=15):
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"{info['emoji']} {activity}", callback_data=f"train_{activity}") 
                 for activity, info in list(TRAINING_TYPES.items())[:3]],
                [InlineKeyboardButton(text=f"{info['emoji']} {activity}", callback_data=f"train_{activity}") 
                 for activity, info in list(TRAINING_TYPES.items())[3:]]
            ])
            await message.answer("Выбери тип тренировки для питомца:", reply_markup=keyboard)
            await state.set_state(PetStates.waiting_for_training_choice)
        else:
            cooldown = timedelta(minutes=15) - (datetime.now() - last_trained)
            await message.answer(f"{pet['name']} еще не восстановился после предыдущей тренировки. "
                                 f"Подожди еще {cooldown.seconds // 60} минут.")
    else:
        await message.answer("У тебя еще нет питомца. Используй /start чтобы создать его.")

@router.callback_query(PetStates.waiting_for_training_choice)
async def process_training_choice(callback_query: CallbackQuery, state: FSMContext):
    training_type = callback_query.data.split("_")[1]
    await state.update_data(training_type=training_type)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=level, callback_data=f"intensity_{level}") 
         for level in INTENSITY_LEVELS.keys()]
    ])
    await callback_query.message.edit_text(f"Выбрана тренировка: {TRAINING_TYPES[training_type]['emoji']} {training_type}\n"
                                           f"Теперь выбери интенсивность тренировки:", reply_markup=keyboard)
    await state.set_state(PetStates.waiting_for_training_intensity)

@router.callback_query(PetStates.waiting_for_training_intensity)
async def process_training_intensity(callback_query: CallbackQuery, state: FSMContext):
    intensity = callback_query.data.split("_")[1]
    data = await state.get_data()
    training_type = data['training_type']
    
    pet = get_pet(callback_query.from_user.id)
    
    primary_stat = TRAINING_TYPES[training_type]['primary']
    secondary_stat = TRAINING_TYPES[training_type]['secondary']
    
    multiplier = INTENSITY_LEVELS[intensity]['multiplier']
    energy_cost = INTENSITY_LEVELS[intensity]['energy_cost']
    
    if pet['energy'] < energy_cost:
        await callback_query.message.edit_text(f"{pet['name']} слишком устал для такой интенсивной тренировки. "
                                               f"Попробуй выбрать менее интенсивную тренировку или дай питомцу отдохнуть.")
        await state.clear()
        return
    
    primary_gain = int(random.randint(5, 15) * multiplier)
    secondary_gain = int(random.randint(2, 8) * multiplier)
    happiness_change = random.randint(-5, 10)
    
    new_primary_stat = min(100, pet[primary_stat] if primary_stat in pet.keys() else 50 + primary_gain)
    new_secondary_stat = min(100, pet[secondary_stat] if secondary_stat in pet.keys() else 50 + secondary_gain)
    new_energy = max(0, pet['energy'] - energy_cost)
    new_happiness = max(0, min(100, pet['happiness'] + happiness_change))
    
    update_pet(callback_query.from_user.id, 
               **{primary_stat: new_primary_stat, 
                  secondary_stat: new_secondary_stat, 
                  'energy': new_energy, 
                  'happiness': new_happiness, 
                  'last_trained': datetime.now().isoformat()})
    
    response = (f"{pet['name']} завершил {intensity.lower()} тренировку '{training_type}'!\n\n"
                f"{TRAINING_TYPES[training_type]['emoji']} {primary_stat.capitalize()}: {new_primary_stat}/100 (+{primary_gain})\n"
                f"{TRAINING_TYPES[training_type]['emoji']} {secondary_stat.capitalize()}: {new_secondary_stat}/100 (+{secondary_gain})\n"
                f"⚡ Энергия: {new_energy}/100 (-{energy_cost})\n"
                f"😊 Счастье: {new_happiness}/100 ({'+' if happiness_change > 0 else ''}{happiness_change})")
    
    # Проверка достижений
    achievements = check_achievements(pet, primary_stat, new_primary_stat)
    if achievements:
        response += "\n\n🏆 Достижения:\n" + "\n".join(achievements)
    
    await callback_query.message.edit_text(response)
    await state.clear()

def check_achievements(pet, trained_stat, new_stat_value):
    achievements = []
    old_stat_value = pet[trained_stat] if trained_stat in pet.keys() else 0
    if new_stat_value >= 50 and old_stat_value < 50:
        achievements.append(f"🥉 Бронзовый уровень в {trained_stat}!")
    if new_stat_value >= 75 and old_stat_value < 75:
        achievements.append(f"🥈 Серебряный уровень в {trained_stat}!")
    if new_stat_value == 100 and old_stat_value < 100:
        achievements.append(f"🥇 Золотой уровень в {trained_stat}!")
    return achievements