from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserResponse, UserUpdate
from app.auth import get_current_active_user
from app.models.user import User

router = APIRouter()

@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    limit: int = Query(50, ge=1, le=100, description="Ограничение количества записей"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Получение списка пользователей с пагинацией"""
    user_repo = UserRepository(db)
    users = await user_repo.get_multiple(skip=skip, limit=limit)
    return users

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Получение профиля текущего пользователя"""
    return current_user

@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Получение пользователя по ID"""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    return user

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Обновление профиля текущего пользователя"""
    user_repo = UserRepository(db)
    
    # Проверяем уникальность username и email если они изменяются
    if user_data.username and user_data.username != current_user.username:
        existing_user = await user_repo.get_by_username(user_data.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким именем уже существует"
            )
    
    if user_data.email and user_data.email != current_user.email:
        existing_user = await user_repo.get_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким email уже существует"
            )
    
    updated_user = await user_repo.update(current_user.id, user_data)
    return updated_user

@router.get("/search/{username}", response_model=List[UserResponse])
async def search_users_by_username(
    username: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Поиск пользователей по части имени пользователя"""
    user_repo = UserRepository(db)
    
    # Простой поиск по точному совпадению (можно расширить)
    user = await user_repo.get_by_username(username)
    if user:
        return [user]
    return [] 