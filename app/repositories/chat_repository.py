from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload, joinedload

from app.models.chat import Chat, ChatType
from app.models.chat_member import ChatMember
from app.models.user import User
from app.schemas.chat import ChatCreate, ChatUpdate, CreatePrivateChat, CreateGroupChat

class ChatRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_private_chat(self, creator_id: int, recipient_id: int) -> Optional[Chat]:
        """Создание приватного чата между двумя пользователями"""
        # Проверяем, не существует ли уже приватный чат между этими пользователями
        existing_chat = await self.get_private_chat_between_users(creator_id, recipient_id)
        if existing_chat:
            return existing_chat

        # Создаем новый приватный чат
        chat = Chat(
            chat_type=ChatType.PRIVATE,
            creator_id=creator_id
        )
        self.db.add(chat)
        await self.db.flush()  # Получаем ID чата

        # Добавляем участников
        creator_member = ChatMember(chat_id=chat.id, user_id=creator_id, is_admin=True)
        recipient_member = ChatMember(chat_id=chat.id, user_id=recipient_id, is_admin=False)
        
        self.db.add(creator_member)
        self.db.add(recipient_member)
        
        await self.db.commit()
        await self.db.refresh(chat)
        return chat

    async def create_group_chat(self, creator_id: int, name: str, member_ids: List[int]) -> Chat:
        """Создание группового чата"""
        chat = Chat(
            name=name,
            chat_type=ChatType.GROUP,
            creator_id=creator_id
        )
        self.db.add(chat)
        await self.db.flush()

        # Добавляем создателя как администратора
        creator_member = ChatMember(chat_id=chat.id, user_id=creator_id, is_admin=True)
        self.db.add(creator_member)

        # Добавляем остальных участников
        for member_id in member_ids:
            if member_id != creator_id:  # Избегаем дублирования создателя
                member = ChatMember(chat_id=chat.id, user_id=member_id, is_admin=False)
                self.db.add(member)

        await self.db.commit()
        await self.db.refresh(chat)
        return chat

    async def get_by_id(self, chat_id: int) -> Optional[Chat]:
        """Получение чата по ID"""
        result = await self.db.execute(
            select(Chat).options(
                selectinload(Chat.members).selectinload(ChatMember.user)
            ).where(Chat.id == chat_id)
        )
        return result.scalar_one_or_none()

    async def get_user_chats(self, user_id: int) -> List[Chat]:
        """Получение всех чатов пользователя"""
        result = await self.db.execute(
            select(Chat).join(ChatMember).options(
                selectinload(Chat.members).selectinload(ChatMember.user)
            ).where(ChatMember.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_private_chat_between_users(self, user_id1: int, user_id2: int) -> Optional[Chat]:
        """Поиск приватного чата между двумя пользователями"""
        # Подзапрос для поиска чатов пользователя 1
        user1_chats = select(ChatMember.chat_id).where(ChatMember.user_id == user_id1)
        
        # Подзапрос для поиска чатов пользователя 2  
        user2_chats = select(ChatMember.chat_id).where(ChatMember.user_id == user_id2)
        
        # Найти приватные чаты, где участвуют оба пользователя
        result = await self.db.execute(
            select(Chat).where(
                and_(
                    Chat.chat_type == ChatType.PRIVATE,
                    Chat.id.in_(user1_chats),
                    Chat.id.in_(user2_chats)
                )
            )
        )
        return result.scalar_one_or_none()

    async def add_member(self, chat_id: int, user_id: int, is_admin: bool = False) -> Optional[ChatMember]:
        """Добавление участника в чат"""
        # Проверяем, не является ли пользователь уже участником
        existing_member = await self.db.execute(
            select(ChatMember).where(
                and_(ChatMember.chat_id == chat_id, ChatMember.user_id == user_id)
            )
        )
        if existing_member.scalar_one_or_none():
            return None

        member = ChatMember(chat_id=chat_id, user_id=user_id, is_admin=is_admin)
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def remove_member(self, chat_id: int, user_id: int) -> bool:
        """Удаление участника из чата"""
        result = await self.db.execute(
            select(ChatMember).where(
                and_(ChatMember.chat_id == chat_id, ChatMember.user_id == user_id)
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            return False

        await self.db.delete(member)
        await self.db.commit()
        return True

    async def is_member(self, chat_id: int, user_id: int) -> bool:
        """Проверка, является ли пользователь участником чата"""
        result = await self.db.execute(
            select(ChatMember).where(
                and_(ChatMember.chat_id == chat_id, ChatMember.user_id == user_id)
            )
        )
        return result.scalar_one_or_none() is not None

    async def update(self, chat_id: int, chat_data: ChatUpdate) -> Optional[Chat]:
        """Обновление чата"""
        chat = await self.get_by_id(chat_id)
        if not chat:
            return None

        for field, value in chat_data.dict(exclude_unset=True).items():
            setattr(chat, field, value)

        await self.db.commit()
        await self.db.refresh(chat)
        return chat 