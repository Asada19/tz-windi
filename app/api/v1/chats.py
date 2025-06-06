from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.chat_repository import ChatRepository
from app.repositories.user_repository import UserRepository
from app.schemas.chat import (
    ChatResponse, 
    ChatWithMembersResponse, 
    CreatePrivateChat, 
    CreateGroupChat,
    ChatUpdate
)
from app.auth import get_current_active_user
from app.models.user import User

router = APIRouter()

@router.get("/", response_model=List[ChatWithMembersResponse])
async def get_user_chats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Получение всех чатов текущего пользователя"""
    chat_repo = ChatRepository(db)
    chats = await chat_repo.get_user_chats(current_user.id)
    
    # Преобразуем в response формат
    result = []
    for chat in chats:
        chat_data = {
            **chat.__dict__,
            "members": [
                {
                    "id": member.id,
                    "user_id": member.user_id,
                    "username": member.user.username,
                    "is_admin": member.is_admin,
                    "joined_at": member.joined_at
                }
                for member in chat.members
            ]
        }
        result.append(chat_data)
    
    return result

@router.post("/private", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_private_chat(
    chat_data: CreatePrivateChat,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Создание приватного чата"""
    # Проверяем, что получатель существует
    user_repo = UserRepository(db)
    recipient = await user_repo.get_by_id(chat_data.recipient_id)
    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Получатель не найден"
        )
    
    # Проверяем, что пользователь не создает чат с самим собой
    if chat_data.recipient_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя создать чат с самим собой"
        )
    
    chat_repo = ChatRepository(db)
    chat = await chat_repo.create_private_chat(current_user.id, chat_data.recipient_id)
    
    return chat

@router.post("/group", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_group_chat(
    chat_data: CreateGroupChat,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Создание группового чата"""
    # Проверяем, что все участники существуют
    user_repo = UserRepository(db)
    for member_id in chat_data.member_ids:
        member = await user_repo.get_by_id(member_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Пользователь с ID {member_id} не найден"
            )
    
    chat_repo = ChatRepository(db)
    chat = await chat_repo.create_group_chat(
        current_user.id, 
        chat_data.name, 
        chat_data.member_ids
    )
    
    return chat

@router.get("/{chat_id}", response_model=ChatWithMembersResponse)
async def get_chat(
    chat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Получение информации о чате"""
    chat_repo = ChatRepository(db)
    
    # Проверяем, является ли пользователь участником чата
    if not await chat_repo.is_member(chat_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому чату"
        )
    
    chat = await chat_repo.get_by_id(chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Чат не найден"
        )
    
    # Преобразуем в response формат
    chat_data = {
        **chat.__dict__,
        "members": [
            {
                "id": member.id,
                "user_id": member.user_id,
                "username": member.user.username,
                "is_admin": member.is_admin,
                "joined_at": member.joined_at
            }
            for member in chat.members
        ]
    }
    
    return chat_data

@router.put("/{chat_id}", response_model=ChatResponse)
async def update_chat(
    chat_id: int,
    chat_data: ChatUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Обновление информации о чате (только для администраторов)"""
    chat_repo = ChatRepository(db)
    
    # Проверяем права доступа (только создатель или админ)
    chat = await chat_repo.get_by_id(chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Чат не найден"
        )
    
    # Проверяем, является ли пользователь администратором чата
    is_admin = False
    for member in chat.members:
        if member.user_id == current_user.id and member.is_admin:
            is_admin = True
            break
    
    if not is_admin and chat.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для изменения этого чата"
        )
    
    updated_chat = await chat_repo.update(chat_id, chat_data)
    return updated_chat

@router.post("/{chat_id}/members/{user_id}")
async def add_member_to_chat(
    chat_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Добавление участника в групповой чат"""
    chat_repo = ChatRepository(db)
    user_repo = UserRepository(db)
    
    # Проверяем существование чата и пользователя
    chat = await chat_repo.get_by_id(chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Чат не найден"
        )
    
    user_to_add = await user_repo.get_by_id(user_id)
    if not user_to_add:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    # Проверяем права (только админы могут добавлять участников)
    is_admin = False
    for member in chat.members:
        if member.user_id == current_user.id and member.is_admin:
            is_admin = True
            break
    
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администраторы могут добавлять участников"
        )
    
    # Добавляем участника
    member = await chat_repo.add_member(chat_id, user_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь уже является участником чата"
        )
    
    return {"message": "Участник успешно добавлен"}

@router.delete("/{chat_id}/members/{user_id}")
async def remove_member_from_chat(
    chat_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Удаление участника из группового чата"""
    chat_repo = ChatRepository(db)
    
    # Проверяем существование чата
    chat = await chat_repo.get_by_id(chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Чат не найден"
        )
    
    # Проверяем права (админы могут удалять любых, обычные пользователи только себя)
    is_admin = False
    for member in chat.members:
        if member.user_id == current_user.id and member.is_admin:
            is_admin = True
            break
    
    if not is_admin and user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для удаления этого участника"
        )
    
    # Удаляем участника
    success = await chat_repo.remove_member(chat_id, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Участник не найден в этом чате"
        )
    
    return {"message": "Участник успешно удален"} 