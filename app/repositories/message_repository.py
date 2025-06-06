from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from sqlalchemy.orm import selectinload, joinedload

from app.models.message import Message
from app.models.message_read_receipt import MessageReadReceipt
from app.models.user import User
from app.schemas.message import MessageCreate, MessageUpdate

class MessageRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, message_data: MessageCreate, sender_id: int) -> Optional[Message]:
        """Создание нового сообщения с проверкой на дублирование"""
        # Проверяем дублирование по client_message_id если он предоставлен
        if message_data.client_message_id:
            existing_message = await self.get_by_client_id(
                message_data.client_message_id, 
                sender_id, 
                message_data.chat_id
            )
            if existing_message:
                return existing_message

        message = Message(
            chat_id=message_data.chat_id,
            sender_id=sender_id,
            text=message_data.text,
            client_message_id=message_data.client_message_id
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def get_by_id(self, message_id: int) -> Optional[Message]:
        """Получение сообщения по ID"""
        result = await self.db.execute(
            select(Message).options(
                joinedload(Message.sender)
            ).where(Message.id == message_id)
        )
        return result.scalar_one_or_none()

    async def get_by_client_id(self, client_message_id: str, sender_id: int, chat_id: int) -> Optional[Message]:
        """Поиск сообщения по client_message_id для предотвращения дублирования"""
        result = await self.db.execute(
            select(Message).where(
                and_(
                    Message.client_message_id == client_message_id,
                    Message.sender_id == sender_id,
                    Message.chat_id == chat_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_chat_messages(
        self, 
        chat_id: int, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[Message]:
        """Получение сообщений чата с пагинацией (отсортированы по времени по возрастанию)"""
        result = await self.db.execute(
            select(Message).options(
                joinedload(Message.sender)
            ).where(Message.chat_id == chat_id)
            .order_by(Message.timestamp.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_unread_messages(self, chat_id: int, user_id: int) -> List[Message]:
        """Получение непрочитанных сообщений для пользователя в чате"""
        # Подзапрос для поиска прочитанных сообщений пользователем
        read_messages_subquery = select(MessageReadReceipt.message_id).where(
            MessageReadReceipt.user_id == user_id
        )
        
        result = await self.db.execute(
            select(Message).options(
                joinedload(Message.sender)
            ).where(
                and_(
                    Message.chat_id == chat_id,
                    Message.sender_id != user_id,  # Исключаем собственные сообщения
                    Message.id.not_in(read_messages_subquery)
                )
            ).order_by(Message.timestamp.asc())
        )
        return list(result.scalars().all())

    async def mark_message_read(self, message_id: int, user_id: int) -> bool:
        """Отметка сообщения как прочитанного"""
        # Проверяем, не отмечено ли уже сообщение как прочитанное
        existing_receipt = await self.db.execute(
            select(MessageReadReceipt).where(
                and_(
                    MessageReadReceipt.message_id == message_id,
                    MessageReadReceipt.user_id == user_id
                )
            )
        )
        
        if existing_receipt.scalar_one_or_none():
            return False  # Уже прочитано

        receipt = MessageReadReceipt(message_id=message_id, user_id=user_id)
        self.db.add(receipt)
        await self.db.commit()
        return True

    async def get_message_read_receipts(self, message_id: int) -> List[MessageReadReceipt]:
        """Получение списка пользователей, прочитавших сообщение"""
        result = await self.db.execute(
            select(MessageReadReceipt).options(
                joinedload(MessageReadReceipt.user)
            ).where(MessageReadReceipt.message_id == message_id)
        )
        return list(result.scalars().all())

    async def update(self, message_id: int, message_data: MessageUpdate) -> Optional[Message]:
        """Обновление сообщения"""
        message = await self.get_by_id(message_id)
        if not message:
            return None

        for field, value in message_data.dict(exclude_unset=True).items():
            setattr(message, field, value)

        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def delete(self, message_id: int) -> bool:
        """Удаление сообщения"""
        message = await self.get_by_id(message_id)
        if not message:
            return False

        await self.db.delete(message)
        await self.db.commit()
        return True

    async def get_chat_message_count(self, chat_id: int) -> int:
        """Получение количества сообщений в чате"""
        result = await self.db.execute(
            select(func.count(Message.id)).where(Message.chat_id == chat_id)
        )
        return result.scalar() or 0 