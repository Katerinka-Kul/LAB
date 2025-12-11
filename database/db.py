from typing import Dict, List, Optional
import json
import os

DB_FILE = "database/users.json"

class Database:
    def __init__(self):
        self.users = self._load_users()
        
        # Предварительно создаем администратора
        if "Администратор" not in self.users:
            self.users["Администратор"] = {
                "username": "Администратор",
                "age": 21,
                "password": "12345678",
                "preferences": {
                    "food": ["пицца", "бургеры"],
                    "books": ["фантастика", "детектив"],
                    "movies": ["фантастика", "боевик"]
                }
            }
            self._save_users()
    
    def _load_users(self) -> Dict:
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_users(self):
        os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, ensure_ascii=False, indent=2)
    
    def get_user(self, username: str) -> Optional[Dict]:
        return self.users.get(username)
    
    def add_user(self, user_data: Dict) -> bool:
        if user_data["username"] in self.users:
            return False
        
        self.users[user_data["username"]] = user_data
        self._save_users()
        return True
    
    def delete_user(self, username: str) -> bool:
        if username in self.users:
            del self.users[username]
            self._save_users()
            return True
        return False
    
    def get_all_users(self) -> List[Dict]:
        return list(self.users.values())
    
    def clear_database(self) -> bool:
        # Сохраняем только администратора
        admin_data = self.users.get("Администратор")
        self.users = {}
        if admin_data:
            self.users["Администратор"] = admin_data
        self._save_users()
        return True

# Глобальный экземпляр базы данных
db = Database()
