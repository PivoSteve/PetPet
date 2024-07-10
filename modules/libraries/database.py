import sqlite3
from datetime import datetime
import random, json
from modules.libraries.constant import const
DATABASE_NAME = 'PetPet.db'

def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pets (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            hunger INTEGER DEFAULT 50,
            cleanliness INTEGER DEFAULT 50,
            happiness INTEGER DEFAULT 50,
            energy INTEGER DEFAULT 100,
            intelligence INTEGER DEFAULT 10,
            last_fed TEXT,
            last_cleaned TEXT,
            last_played TEXT,
            last_slept TEXT,
            personality TEXT,
            favorite_food TEXT,
            favorite_activity TEXT,
            tricks TEXT NULL
        )
    ''')
    conn.commit()
    conn.close()

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_pet(user_id: int):
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM pets WHERE user_id = ?', (user_id,))
    pet = cursor.fetchone()
    conn.close()
    return pet

def create_pet(user_id: int, name: str):
    personality = random.choice(['Игривый', 'Ленивый', 'Любопытный', 'Дружелюбный', 'Застенчивый'])
    favorite_food = random.choice(['Яблоко', 'Морковь', 'Банан', 'Орехи', 'Ягоды'])
    favorite_activity = random.choice(['Математика', 'Загадки', 'Угадайки'])
    
    initial_stats = {stat: random.randint(30, 60) for stat in const.NEWSTATS}
    
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO pets (user_id, name, personality, favorite_food, favorite_activity,
                          hunger, cleanliness, happiness, energy, intelligence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, name, personality, favorite_food, favorite_activity,
          initial_stats['hunger'], initial_stats['cleanliness'], initial_stats['happiness'],
          initial_stats['energy'], initial_stats['intelligence']))
    conn.commit()
    conn.close()

def update_pet(user_id: int, **kwargs):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    for key, value in kwargs.items():
        if isinstance(value, list):
            kwargs[key] = json.dumps(value)
    
    set_clause = ', '.join(f'{k} = ?' for k in kwargs)
    query = f'UPDATE pets SET {set_clause} WHERE user_id = ?'
    
    try:
        cursor.execute(query, tuple(kwargs.values()) + (user_id,))
        conn.commit()
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

def get_all_pets():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM pets')
    pets = cursor.fetchall()
    conn.close()
    return pets