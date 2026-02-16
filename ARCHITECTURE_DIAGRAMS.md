# Диаграммы и примеры архитектуры VideoHost

## 1. ДИАГРАММА ВЗАИМОСВЯЗЕЙ МОДЕЛЕЙ

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ id, username, email, password_hash, is_author, created_at│  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │                    │                      │
         │ 1-to-1             │ 1-to-many           │ 1-to-many
         │ (cascade)          │ (cascade)           │ (cascade)
         ▼                    ▼                      ▼
    ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐
    │  CHANNEL    │    │SUBSCRIPTION  │    │      ROOM        │
    │ (1 per user)│    │(many per user)│    │(many per user)   │
    └─────────────┘    └──────────────┘    └──────────────────┘
         │                    │                      │
         │ 1-to-many          │ many-to-1           │ 1-to-many
         │ (cascade)          │                      │ (cascade)
         ▼                    ▼                      ▼
    ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐
    │   VIDEO     │    │  CHANNEL     │    │ ROOM_PARTICIPANT │
    │(many per    │    │(target)      │    │(many per room)   │
    │ channel)    │    └──────────────┘    └──────────────────┘
    └─────────────┘
         │
         │ 1-to-many
         │ (cascade)
         ▼
    ┌─────────────┐
    │    ROOM     │
    │(many per    │
    │  video)     │
    └─────────────┘
         │
         │ 1-to-many
         │ (cascade)
         ▼
    ┌──────────────────┐
    │  CHAT_MESSAGE    │
    │(many per room)   │
    └──────────────────┘
```

## 2. АРХИТЕКТУРА ПРИЛОЖЕНИЯ

```
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND (Browser)                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ HTML Templates (Jinja2)                                  │  │
│  │ - base.html, index.html, video_player.html, etc.        │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ CSS (modern.css, components.css, style.css)             │  │
│  │ - Glassmorphism, gradients, animations                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ JavaScript (app.js)                                      │  │
│  │ - API calls, WebSocket, UI interactions                 │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                    HTTP/WebSocket
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    FLASK APPLICATION                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Routes (routes.py)                                       │  │
│  │ - Web pages (HTML rendering)                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ API Blueprints (api/)                                    │  │
│  │ - auth.py, channels.py, videos.py, subscriptions.py,   │  │
│  │   rooms.py (REST endpoints)                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Services (services/)                                     │  │
│  │ - AuthService, ChannelService, VideoService,            │  │
│  │   SubscriptionService, RoomService (business logic)     │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ WebSocket Handlers (websocket/)                          │  │
│  │ - room_events.py (real-time events)                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Models (models.py)                                       │  │
│  │ - User, Channel, Video, Subscription, Room, etc.        │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │                    │                      │
         │ SQL               │ Redis              │ File I/O
         │                    │                      │
         ▼                    ▼                      ▼
    ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐
    │ PostgreSQL  │    │    Redis     │    │  File System     │
    │ (SQLite dev)│    │ (Sessions,   │    │ (Video files)    │
    │             │    │  Cache,      │    │                  │
    │             │    │  WebSocket)  │    │                  │
    └─────────────┘    └──────────────┘    └──────────────────┘
```

## 3. ПОТОК АУТЕНТИФИКАЦИИ

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. РЕГИСТРАЦИЯ                                                  │
├─────────────────────────────────────────────────────────────────┤
│ POST /api/auth/register                                         │
│ {username, email, password}                                     │
│         │                                                       │
│         ▼                                                       │
│ AuthService.register_user()                                     │
│ - Валидация данных                                              │
│ - Проверка уникальности username/email                          │
│ - Хеширование пароля (bcrypt)                                   │
│ - Создание User в БД                                            │
│         │                                                       │
│         ▼                                                       │
│ Response: {id, username, email, is_author, created_at} (201)   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 2. ЛОГИН                                                        │
├─────────────────────────────────────────────────────────────────┤
│ POST /api/auth/login                                            │
│ {username, password}                                            │
│         │                                                       │
│         ▼                                                       │
│ AuthService.authenticate()                                      │
│ - Поиск User по username                                        │
│ - Проверка пароля (bcrypt)                                      │
│         │                                                       │
│         ▼                                                       │
│ AuthService.create_session()                                    │
│ - Генерация токена (secrets.token_urlsafe)                      │
│ - Сохранение в Redis: session:{token} = user_id                │
│ - TTL: 86400 сек (24 часа)                                      │
│         │                                                       │
│         ▼                                                       │
│ Response: {token, user: {...}} (200)                            │
│ localStorage.setItem('token', token)                            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 3. ИСПОЛЬЗОВАНИЕ ТОКЕНА                                         │
├─────────────────────────────────────────────────────────────────┤
│ GET /api/auth/me                                                │
│ Headers: Authorization: Bearer {token}                          │
│         │                                                       │
│         ▼                                                       │
│ @require_auth decorator                                         │
│ - Парсинг Authorization header                                  │
│ - Извлечение токена                                             │
│ - AuthService.validate_session(token)                           │
│   - Поиск в Redis: session:{token}                              │
│   - Получение user_id                                           │
│   - Загрузка User из БД                                         │
│         │                                                       │
│         ▼                                                       │
│ request.current_user = user                                     │
│ Response: {id, username, email, is_author, created_at} (200)   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 4. ЛОГАУТ                                                       │
├─────────────────────────────────────────────────────────────────┤
│ POST /api/auth/logout                                           │
│ Headers: Authorization: Bearer {token}                          │
│         │                                                       │
│         ▼                                                       │
│ AuthService.terminate_session(token)                            │
│ - Удаление из Redis: session:{token}                            │
│         │                                                       │
│         ▼                                                       │
│ localStorage.removeItem('token')                                │
│ Response: {message: "Logged out successfully"} (200)            │
└─────────────────────────────────────────────────────────────────┘
```

## 4. ПОТОК ЗАГРУЗКИ ВИДЕО

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. ВЫБОР ВИДЕО И МЕТАДАННЫХ                                     │
├─────────────────────────────────────────────────────────────────┤
│ Пользователь заполняет форму:                                   │
│ - Файл видео                                                    │
│ - Название                                                      │
│ - Описание                                                      │
│ - Уровень доступа (public/subscriber/sponsor)                   │
│ - Наличие рекламы                                               │
│         │                                                       │
│         ▼                                                       │
│ JavaScript: handleVideoSelect()                                 │
│ - Создание <video> элемента                                     │
│ - Получение длительности видео                                  │
│ - Заполнение скрытого поля duration                             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 2. ОТПРАВКА НА СЕРВЕР                                           │
├─────────────────────────────────────────────────────────────────┤
│ POST /api/videos                                                │
│ Content-Type: multipart/form-data                               │
│ Headers: Authorization: Bearer {token}                          │
│ Body: {file, title, description, duration, access_level, ...}  │
│         │                                                       │
│         ▼                                                       │
│ JavaScript: uploadVideo()                                       │
│ - XMLHttpRequest для отслеживания прогресса                     │
│ - Обновление progress bar                                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 3. ОБРАБОТКА НА СЕРВЕРЕ                                         │
├─────────────────────────────────────────────────────────────────┤
│ VideoService.upload_video()                                     │
│ - Валидация метаданных                                          │
│ - Проверка расширения файла                                     │
│ - Генерация уникального имени файла (UUID)                      │
│ - Сохранение файла на диск                                      │
│ - Создание Video записи в БД                                    │
│   - channel_id (из канала пользователя)                         │
│   - title, description                                          │
│   - file_path (путь на диске)                                   │
│   - duration                                                    │
│   - access_level                                                │
│   - has_ads                                                     │
│   - status = 'ready' (для MVP, без обработки)                   │
│         │                                                       │
│         ▼                                                       │
│ Response: {id, channel_id, title, ...} (201)                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 4. ПОСЛЕ ЗАГРУЗКИ                                               │
├─────────────────────────────────────────────────────────────────┤
│ - Закрытие модального окна                                      │
│ - Показ уведомления об успехе                                   │
│ - Перезагрузка страницы (window.location.reload)                │
│ - Новое видео появляется в сетке                                │
└─────────────────────────────────────────────────────────────────┘
```

## 5. ПОТОК СОЗДАНИЯ И СИНХРОНИЗАЦИИ КОМНАТЫ

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. СОЗДАНИЕ КОМНАТЫ                                             │
├─────────────────────────────────────────────────────────────────┤
│ POST /api/rooms                                                 │
│ {video_id, max_participants}                                    │
│         │                                                       │
│         ▼                                                       │
│ RoomService.create_room()                                       │
│ - Проверка видео                                                │
│ - Определение max_participants:                                 │
│   - Если спонсор: None (без ограничений)                        │
│   - Иначе: 10 (по умолчанию)                                    │
│ - Создание Room в БД                                            │
│ - Автоматическое присоединение хоста                            │
│         │                                                       │
│         ▼                                                       │
│ Response: {id, owner_id, video_id, ...} (201)                   │
│ Редирект: /room/{room_id}                                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 2. ИНИЦИАЛИЗАЦИЯ WEBSOCKET                                      │
├─────────────────────────────────────────────────────────────────┤
│ JavaScript: initializeWebSocket()                               │
│ - Подключение к Socket.IO                                       │
│ - Отправка join_room события                                    │
│   {room_id, token}                                              │
│         │                                                       │
│         ▼                                                       │
│ WebSocket: handle_join_room()                                   │
│ - Аутентификация пользователя                                   │
│ - Проверка комнаты                                              │
│ - Проверка лимита участников                                    │
│ - Добавление RoomParticipant в БД                               │
│ - Присоединение к Socket.IO комнате                             │
│         │                                                       │
│         ▼                                                       │
│ Broadcast: user_joined                                          │
│ - Отправка всем в комнате                                       │
│ - Обновление списка участников                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 3. СИНХРОНИЗАЦИЯ ВИДЕО                                          │
├─────────────────────────────────────────────────────────────────┤
│ Хост нажимает Play/Pause/Seek                                   │
│         │                                                       │
│         ▼                                                       │
│ JavaScript: videoPlayer.addEventListener('play/pause/seeked')  │
│ - Отправка play/pause/seek события                              │
│   {room_id, position}                                           │
│         │                                                       │
│         ▼                                                       │
│ WebSocket: handle_play/pause/seek()                             │
│ - Проверка: только хост может управлять                         │
│ - Обновление Room в БД:                                         │
│   - current_position = position                                 │
│   - is_playing = true/false                                     │
│         │                                                       │
│         ▼                                                       │
│ Broadcast: play_event/pause_event/seek_event                    │
│ - Отправка всем в комнате (кроме хоста)                         │
│         │                                                       │
│         ▼                                                       │
│ JavaScript: socket.on('play_event/pause_event/seek_event')      │
│ - Синхронизация видеоплеера                                     │
│ - videoPlayer.currentTime = position                            │
│ - videoPlayer.play() / videoPlayer.pause()                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 4. ПЕРИОДИЧЕСКАЯ СИНХРОНИЗАЦИЯ                                  │
├─────────────────────────────────────────────────────────────────┤
│ Каждые 5 секунд (для не-хостов):                                │
│ - Отправка sync_request события                                 │
│         │                                                       │
│         ▼                                                       │
│ WebSocket: handle_sync_request()                                │
│ - Получение текущего состояния Room                             │
│ - Отправка state_sync события                                   │
│   {position, is_playing, timestamp}                             │
│         │                                                       │
│         ▼                                                       │
│ JavaScript: socket.on('state_sync')                             │
│ - Проверка разницы: |currentTime - position| > 3 сек           │
│ - Если разница > 3 сек: принудительная синхронизация           │
│ - videoPlayer.currentTime = position                            │
└─────────────────────────────────────────────────────────────────┘
```

## 6. ПОТОК ЧАТА В КОМНАТЕ

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. ОТПРАВКА СООБЩЕНИЯ                                           │
├─────────────────────────────────────────────────────────────────┤
│ Пользователь вводит текст и нажимает Enter                      │
│         │                                                       │
│         ▼                                                       │
│ JavaScript: sendMessage()                                       │
│ - Получение текста из input                                     │
│ - Отправка chat_message события                                 │
│   {room_id, message}                                            │
│         │                                                       │
│         ▼                                                       │
│ WebSocket: handle_chat_message()                                │
│ - Аутентификация пользователя                                   │
│ - Валидация сообщения (не пусто, макс 500 символов)            │
│ - Проверка rate limit (message_delay)                           │
│   - Если room.message_delay > 0:                                │
│     - Проверка времени последнего сообщения                     │
│     - Если меньше message_delay сек: отправка ошибки            │
│ - Сохранение ChatMessage в БД                                   │
│ - Обновление RoomParticipant.last_message_at                    │
│ - Обновление cooldown в памяти                                  │
│         │                                                       │
│         ▼                                                       │
│ Broadcast: chat_message_event                                   │
│ - Отправка всем в комнате                                       │
│   {message_id, user_id, username, message, timestamp}           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 2. ПОЛУЧЕНИЕ СООБЩЕНИЯ                                          │
├─────────────────────────────────────────────────────────────────┤
│ JavaScript: socket.on('chat_message_event')                     │
│ - Получение данных сообщения                                    │
│ - Создание HTML элемента сообщения                              │
│ - Добавление в чат контейнер                                    │
│ - Прокрутка чата вниз                                           │
│         │                                                       │
│         ▼                                                       │
│ Сообщение отображается в чате                                   │
│ [username] [time]                                               │
│ message text                                                    │
└─────────────────────────────────────────────────────────────────┘
```

## 7. СИСТЕМА ДОСТУПА К ВИДЕО

```
┌─────────────────────────────────────────────────────────────────┐
│ ПРОВЕРКА ДОСТУПА: VideoService.check_access(video, user)       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ if video.access_level == 'public':                              │
│     return True  ✓ Доступно всем                                │
│                                                                 │
│ if not user:                                                    │
│     return False  ✗ Требуется аутентификация                    │
│                                                                 │
│ if video.channel.author_id == user.id:                          │
│     return True  ✓ Владелец канала                              │
│                                                                 │
│ subscription = Subscription.query.filter_by(                    │
│     user_id=user.id,                                            │
│     channel_id=video.channel_id                                 │
│ ).first()                                                       │
│                                                                 │
│ if not subscription:                                            │
│     return False  ✗ Не подписан                                 │
│                                                                 │
│ if video.access_level == 'subscriber':                          │
│     return True  ✓ Подписчик                                    │
│                                                                 │
│ if video.access_level == 'sponsor':                             │
│     return subscription.is_sponsor  ✓/✗ Спонсор ли              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ ЛОГИКА РЕКЛАМЫ: VideoService.should_show_ads(video, user)      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ if not video.has_ads:                                           │
│     return False  ✗ Видео без рекламы                           │
│                                                                 │
│ if video.access_level in ['subscriber', 'sponsor']:             │
│     return False  ✗ Премиум контент без рекламы                 │
│                                                                 │
│ if not user:                                                    │
│     return True  ✓ Анонимный пользователь видит рекламу         │
│                                                                 │
│ if video.channel.author_id == user.id:                          │
│     return False  ✗ Владелец не видит рекламу                   │
│                                                                 │
│ subscription = Subscription.query.filter_by(                    │
│     user_id=user.id,                                            │
│     channel_id=video.channel_id                                 │
│ ).first()                                                       │
│                                                                 │
│ if subscription and subscription.is_sponsor:                    │
│     return False  ✗ Спонсоры не видят рекламу                   │
│                                                                 │
│ return True  ✓ Обычные пользователи видят рекламу               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 8. СТРУКТУРА ЗАПРОСА/ОТВЕТА API

```
┌─────────────────────────────────────────────────────────────────┐
│ УСПЕШНЫЙ ОТВЕТ (200/201)                                        │
├─────────────────────────────────────────────────────────────────┤
│ {                                                               │
│   "id": 1,                                                      │
│   "username": "john_doe",                                       │
│   "email": "john@example.com",                                  │
│   "is_author": true,                                            │
│   "created_at": "2024-01-15T10:30:00"                           │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ ОШИБКА (4xx/5xx)                                                │
├─────────────────────────────────────────────────────────────────┤
│ {                                                               │
│   "error": {                                                    │
│     "code": "UNAUTHORIZED",                                     │
│     "message": "Invalid username or password"                   │
│   }                                                             │
│ }                                                               │
│                                                                 │
│ Коды ошибок:                                                    │
│ - BAD_REQUEST (400)                                             │
│ - UNAUTHORIZED (401)                                            │
│ - FORBIDDEN (403)                                               │
│ - NOT_FOUND (404)                                               │
│ - CONFLICT (409)                                                │
│ - UNPROCESSABLE_ENTITY (422)                                    │
│ - RATE_LIMIT_EXCEEDED (429)                                     │
│ - INTERNAL_SERVER_ERROR (500)                                   │
│ - SERVICE_UNAVAILABLE (503)                                     │
└─────────────────────────────────────────────────────────────────┘
```

## 9. ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ API

### Регистрация
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "secure_password"
  }'
```

### Логин
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "secure_password"
  }'
```

### Загрузка видео
```bash
curl -X POST http://localhost:5000/api/videos \
  -H "Authorization: Bearer {token}" \
  -F "file=@video.mp4" \
  -F "title=My Video" \
  -F "description=Video description" \
  -F "duration=120" \
  -F "access_level=public" \
  -F "has_ads=true"
```

### Создание комнаты
```bash
curl -X POST http://localhost:5000/api/rooms \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": 1,
    "max_participants": 10
  }'
```

### Подписка на канал
```bash
curl -X POST http://localhost:5000/api/subscriptions \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": 1,
    "is_sponsor": false
  }'
```

