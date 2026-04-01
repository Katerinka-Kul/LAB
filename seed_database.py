#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для автоматического заполнения базы данных Soulmate тестовыми данными.
Запуск: python seed_database.py
"""

import random
import string
from datetime import datetime, timedelta
from sqlmodel import Session, select
import sys
import os

# Добавляем корневую папку в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.connection import engine
from models.users import User
from models.events import Event

# ==================== КОНСТАНТЫ ДЛЯ ГЕНЕРАЦИИ ====================

# Категории интересов (расширенный список)
CATEGORIES = {
    "food": [
        "пицца", "суши", "бургеры", "паста", "стейк", "салат", "суп"
    ],
    "books": [
        "фантастика", "детектив", "роман", "биография", "фэнтези", 
        "наука", "поэзия"
    ],
    "movies": [
        "комедия", "драма", "боевик", "фантастика", "ужасы", 
        "мультфильмы", "документальные"
    ]
}

# Имена и фамилии для генерации
FIRST_NAMES = [
    "Александр", "Дмитрий", "Максим", "Сергей", "Андрей", "Алексей", 
    "Иван", "Кирилл", "Михаил", "Николай", "Павел", "Роман", "Артем",
    "Владимир", "Елена", "Анна", "Ольга", "Наталья", "Екатерина", 
    "Татьяна", "Ирина", "Юлия", "Ксения", "Марина", "Светлана"
]

LAST_NAMES = [
    "Иванов", "Петров", "Сидоров", "Кузнецов", "Смирнов", "Попов", 
    "Васильев", "Федоров", "Морозов", "Волков", "Алексеев", "Лебедев",
    "Семенов", "Козлов", "Михайлов", "Новиков", "Зайцев", "Соловьев"
]



# ==================== ФУНКЦИИ ГЕНЕРАЦИИ ====================

def generate_username(first_name, last_name):
    """Генерация уникального имени пользователя"""
    # Транслитерация имени и фамилии (упрощенная)
    translit = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
        'ы': 'y', 'э': 'e', 'ю': 'yu', 'я': 'ya'
    }
    
    def translit_word(word):
        result = ''
        for char in word.lower():
            result += translit.get(char, char)
        return result
    
    first = translit_word(first_name)
    last = translit_word(last_name)
    number = random.randint(1, 9999)
    return f"{first}_{last}{number}"

def generate_password():
    """Генерация пароля"""
    chars = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(random.choice(chars) for _ in range(random.randint(8, 12)))

def generate_age():
    """Генерация возраста"""
    return random.randint(18, 75)

def generate_preferences():
    """Генерация случайных предпочтений"""
    prefs = {}
    for category, items in CATEGORIES.items():
        # Выбираем от 2 до 5 случайных интересов
        num_prefs = random.randint(2, min(5, len(items)))
        prefs[category] = random.sample(items, num_prefs)
    return prefs



# ==================== ФУНКЦИИ СОЗДАНИЯ ЗАПИСЕЙ ====================

def create_users(session: Session, count: int = 500):
    """Создание тестовых пользователей"""
    users = []
    existing_usernames = set()
    
    # Получаем уже существующие имена пользователей
    existing = session.exec(select(User.username)).all()
    existing_usernames.update(existing)
    
    print(f"Создание {count} пользователей...")
    
    for i in range(count):
        # Генерируем уникальное имя пользователя
        while True:
            first_name = random.choice(FIRST_NAMES)
            last_name = random.choice(LAST_NAMES)
            username = generate_username(first_name, last_name)
            if username not in existing_usernames:
                existing_usernames.add(username)
                break
        
        age = generate_age()
        password = generate_password()
        preferences = generate_preferences()
        
        # Администраторы: 2% от общего числа
        is_admin = random.random() < 0.02
        
        user = User(
            username=username,
            age=age,
            password=password,
            is_admin=is_admin,
            preferences=preferences
        )
        session.add(user)
        users.append(user)
        
        # Прогресс-бар
        if (i + 1) % 50 == 0 or (i + 1) == count:
            print(f"  Прогресс: {i + 1}/{count} пользователей")
            session.commit()  # Промежуточный коммит
    
    print(f"✓ Создано {len(users)} пользователей")
    return users



# ==================== ОСНОВНАЯ ФУНКЦИЯ ====================

def main():
    """Основная функция заполнения БД"""
    print("\n" + "=" * 60)
    print("ЗАПОЛНЕНИЕ БАЗЫ ДАННЫХ SOULMATE ТЕСТОВЫМИ ДАННЫМИ")
    print("=" * 60)
    
    # Параметры заполнения
    NUM_USERS = 1000
    NUM_EVENTS = 300
    
    print(f"\nПараметры генерации:")
    print(f"  Пользователей: {NUM_USERS}")
    print(f"  Событий: {NUM_EVENTS}")
    
    # Подтверждение
    response = input("\nНачать заполнение? (y/n): ")
    if response.lower() != 'y':
        print("Операция отменена")
        return
    
    start_time = datetime.now()
    
    with Session(engine) as session:
        # Проверяем существующие данные
        existing_users = session.exec(select(User)).all()
        existing_events = session.exec(select(Event)).all()
        
        if existing_users:
            print(f"\nВ базе уже есть {len(existing_users)} пользователей")
            if len(existing_users) > 10:
                response = input("Очистить базу перед заполнением? (y/n): ")
                if response.lower() == 'y':
                    # Удаляем всех пользователей кроме администратора
                    for user in existing_users:
                        if user.username != "Administrator":
                            session.delete(user)
                    session.commit()
                    print("База очищена")
        
        # Создаем пользователей
        print("\n" + "-" * 40)
        users = create_users(session, count=NUM_USERS)
        
        
        # Итоги
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("\n" + "=" * 60)
        print("ЗАПОЛНЕНИЕ ЗАВЕРШЕНО УСПЕШНО!")
        print("=" * 60)
        print(f"\nИТОГИ:")
        print(f"  Пользователей: {len(users)}")
        print(f"  Время выполнения: {duration:.2f} сек")
        print(f"  Файл БД: soulmate.db")
        print("\n" + "=" * 60)

if __name__ == "__main__":
    main()