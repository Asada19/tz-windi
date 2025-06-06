#!/usr/bin/env python3

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db, create_tables, AsyncSessionLocal
from app.repositories.user_repository import UserRepository
from app.repositories.chat_repository import ChatRepository
from app.repositories.message_repository import MessageRepository
from app.schemas.user import UserCreate
from app.schemas.message import MessageCreate

async def create_test_users():
    async with AsyncSessionLocal() as db:
        user_repo = UserRepository(db)
        
        users_data = [
            {
                "username": "alice",
                "email": "alice@example.com",
                "password": "password123"
            },
            {
                "username": "bob", 
                "email": "bob@example.com",
                "password": "password123"
            },
            {
                "username": "charlie",
                "email": "charlie@example.com", 
                "password": "password123"
            },
            {
                "username": "diana",
                "email": "diana@example.com",
                "password": "password123"
            },
            {
                "username": "eve",
                "email": "eve@example.com",
                "password": "password123"
            }
        ]
        
        created_users = []
        for user_data in users_data:
            existing_user = await user_repo.get_by_username(user_data["username"])
            if not existing_user:
                user_create = UserCreate(**user_data)
                user = await user_repo.create(user_create)
                created_users.append(user)
                print(f"Created user: {user.username} (ID: {user.id})")
            else:
                created_users.append(existing_user)
                print(f"User {user_data['username']} exists (ID: {existing_user.id})")
        
        return created_users

async def create_test_chats(users):
    async with AsyncSessionLocal() as db:
        chat_repo = ChatRepository(db)
        
        private_chat = await chat_repo.create_private_chat(users[0].id, users[1].id)
        print(f"Created private chat between {users[0].username} and {users[1].username} (ID: {private_chat.id})")
        
        group_chat = await chat_repo.create_group_chat(
            users[0].id,
            "Test Group",
            [users[1].id, users[2].id, users[3].id]
        )
        print(f"Created group chat '{group_chat.name}' (ID: {group_chat.id})")
        
        private_chat2 = await chat_repo.create_private_chat(users[2].id, users[3].id)
        print(f"Created private chat between {users[2].username} and {users[3].username} (ID: {private_chat2.id})")
        
        return [private_chat, group_chat, private_chat2]

async def create_test_messages(users, chats):
    async with AsyncSessionLocal() as db:
        message_repo = MessageRepository(db)
        
        messages_data = [
            {
                "chat_id": chats[0].id,
                "sender_id": users[0].id,
                "text": "Hey Bob! How's it going?",
            },
            {
                "chat_id": chats[0].id,
                "sender_id": users[1].id,
                "text": "Hi Alice! All good, thanks!",
            },
            {
                "chat_id": chats[0].id,
                "sender_id": users[0].id,
                "text": "Great! Ready to work on the project?",
            },
            {
                "chat_id": chats[1].id,
                "sender_id": users[0].id,
                "text": "Welcome to our test group!",
            },
            {
                "chat_id": chats[1].id,
                "sender_id": users[1].id,
                "text": "Thanks for the invitation!",
            },
            {
                "chat_id": chats[1].id,
                "sender_id": users[2].id,
                "text": "Hey everyone! Glad to be here",
            },
            {
                "chat_id": chats[1].id,
                "sender_id": users[3].id,
                "text": "Let's discuss the work plan",
            },
            {
                "chat_id": chats[1].id,
                "sender_id": users[0].id,
                "text": "Great idea! Let's start with defining tasks",
            },
            {
                "chat_id": chats[2].id,
                "sender_id": users[2].id,
                "text": "Diana, can we discuss project details?",
            },
            {
                "chat_id": chats[2].id,
                "sender_id": users[3].id,
                "text": "Sure! I have a few ideas",
            },
        ]
        
        created_messages = []
        for msg_data in messages_data:
            message_create = MessageCreate(
                chat_id=msg_data["chat_id"],
                text=msg_data["text"]
            )
            message = await message_repo.create(message_create, msg_data["sender_id"])
            created_messages.append(message)
            
            sender = next(u for u in users if u.id == msg_data["sender_id"])
            print(f"Created message from {sender.username} in chat {msg_data['chat_id']}: '{msg_data['text'][:30]}...'")
        
        return created_messages

async def main():
    print("Creating test data for WinDI Messenger...\n")
    
    try:
        print("1. Creating database tables...")
        await create_tables()
        print("Tables created\n")
        
        print("2. Creating test users...")
        users = await create_test_users()
        print(f"Created/found {len(users)} users\n")
        
        print("3. Creating test chats...")
        chats = await create_test_chats(users)
        print(f"Created {len(chats)} chats\n")
        
        print("4. Creating test messages...")
        messages = await create_test_messages(users, chats)
        print(f"Created {len(messages)} messages\n")
        
        print("Test data created successfully!")
        print("\nTest data summary:")
        print("Users:")
        for user in users:
            print(f"  - {user.username} (ID: {user.id}) - password: password123")
        
        print("\nChats:")
        for i, chat in enumerate(chats):
            chat_type = "Private" if chat.chat_type.value == "private" else "Group"
            name = chat.name if chat.name else f"Chat #{chat.id}"
            print(f"  - {chat_type} chat: {name} (ID: {chat.id})")
        
        print(f"\nMessages: {len(messages)}")
        
        print("\nUseful links:")
        print("  - API docs: http://localhost:8000/docs")
        print("  - ReDoc: http://localhost:8000/redoc")
        print("  - WebSocket test: ws://localhost:8000/api/v1/ws/test")
        
    except Exception as e:
        print(f"Error creating test data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 