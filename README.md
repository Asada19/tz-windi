# WinDI Messenger

Чат с WebSocket, групповыми чатами и всем таким.

## Стек
FastAPI, PostgreSQL, Redis, WebSockets, Docker

## Что умеет
- Регистрация/логин с JWT
- Приватные и групповые чаты 
- Real-time сообщения через WebSocket
- История с пагинацией
- Статус "прочитано" 
- Typing indicators

## Запуск

```bash
docker-compose up -d
docker-compose exec app python create_test_data.py
```

http://localhost:8000 - апп  
http://localhost:8000/docs - доки

## API примеры

Регистрация:
```bash
curl -X POST localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "bob", "email": "bob@test.com", "password": "123456"}'
```

Логин:
```bash
curl -X POST localhost:8000/api/v1/auth/login-json \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "password123"}'
```

Список чатов:
```bash
curl localhost:8000/api/v1/chats/ -H "Authorization: Bearer TOKEN"
```

Создать приватный чат:
```bash
curl -X POST localhost:8000/api/v1/chats/private \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"recipient_id": 2}'
```

История сообщений:
```bash
curl "localhost:8000/api/v1/messages/history/1?limit=20&offset=0" \
  -H "Authorization: Bearer TOKEN"
```

Отправить сообщение:
```bash
curl -X POST localhost:8000/api/v1/messages/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": 1, "text": "привет", "client_message_id": "123"}'
```

## WebSocket

```javascript
const ws = new WebSocket(`ws://localhost:8000/api/v1/ws/chat?token=${token}`);

// Отправить сообщение
ws.send(JSON.stringify({
    action: "send_message",
    data: {
        chat_id: 1,
        text: "привет",
        client_message_id: "123"
    }
}));

// Показать что печатаю
ws.send(JSON.stringify({
    action: "typing",
    data: {
        chat_id: 1,
        is_typing: true
    }
}));
```

Входящие события:
```json
{"type": "new_message", "data": {...}}
{"type": "message_read", "data": {...}}
{"type": "typing_indicator", "data": {...}}
{"type": "user_status", "data": {...}}
```

## Тестовые данные

После `create_test_data.py` будет:
- 5 юзеров: alice, bob, charlie, diana, eve (пароль: password123)
- 3 чата с сообщениями

## Тест

```bash
python test_client.py  # простой тест WebSocket
curl localhost:8000/health  # проверка что живо
```

## .env

```env
DATABASE_URL=postgresql+asyncpg://windi:windi123@localhost:5432/windi_chat
REDIS_URL=redis://localhost:6379
SECRET_KEY=change-me-in-production
DEBUG=true
```

## Архитектура

Классическая слоеная: API → Repository → Model. Все асинхронно, JWT auth, дублирование сообщений предотвращается через `client_message_id`. 