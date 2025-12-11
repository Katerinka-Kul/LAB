from fastapi import APIRouter, HTTPException, status
from models.users import User, UserSignIn
from database.db import db

user_router = APIRouter(tags=["User"])

@user_router.post("/api/register")
async def register(user_data: User):
    if db.get_user(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким логином уже существует"
        )
    
    # Ограничиваем количество предпочтений до 5
    for category in ["food", "books", "movies"]:
        preferences = getattr(user_data.preferences, category)
        if len(preferences) > 5:
            setattr(user_data.preferences, category, preferences[:5])
    
    if db.add_user(user_data.dict()):
        return {"message": "Пользователь успешно зарегистрирован"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при регистрации пользователя"
        )

@user_router.post("/api/login")
async def login(user: UserSignIn):
    db_user = db.get_user(user.username)
    
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    if db_user["password"] != user.password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Неверный пароль"
        )
    
    return {
        "message": "Вход выполнен успешно",
        "username": user.username,
        "is_admin": user.username == "Администратор"
    }

@user_router.get("/api/users")
async def get_all_users():
    return db.get_all_users()

@user_router.get("/api/users/{username}")
async def get_user_profile(username: str):
    user = db.get_user(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    return user

@user_router.delete("/api/users/{username}")
async def delete_user(username: str):
    if username == "Администратор":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нельзя удалить администратора"
        )
    
    if db.delete_user(username):
        return {"message": f"Пользователь {username} удален"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )

@user_router.post("/api/clear-db")
async def clear_database():
    if db.clear_database():
        return {"message": "База данных очищена"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при очистке базы данных"
        )
