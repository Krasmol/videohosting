# Полный анализ архитектуры видеохостинг платформы VideoHost

## 1. ОБЗОР ПРОЕКТА

**Название:** VideoHost - Платформа для видео хостинга
**Язык:** Python (Flask) + JavaScript (Vanilla)
**Архитектура:** MVC (Model-View-Controller) с REST API
**Реал-тайм:** WebSocket (Socket.IO)
**БД:** SQLAlchemy ORM (SQLite/PostgreSQL)
**Кэширование:** Redis
**Фоновые задачи:** Celery

---

## 2. СТРУКТУРА ПРОЕКТА

```
VideoHost/
├── app/
│   ├── __init__.py              # Инициализация Flask приложения
│   ├── models.py                # SQLAlchemy модели БД
│   ├── routes.py                # Web маршруты (HTML страницы)
│   ├── api/                     # REST API endpoints
│   │   ├── __init__.py
│   │   ├── auth.py              # Аутентификация (регистрация, логин, логаут)
│   │   ├── channels.py          # Управление каналами
│   │   ├── videos.py            # Загрузка и управление видео
│   │   ├── subscriptions.py     # Подписки и спонсорство
│   │   └── rooms.py             # Комнаты совместного просмотра
│   ├── services/                # Бизнес-логика
│   │   ├── __init__.py
│   │   ├── auth_service.py      # Сервис аутентификации
│   │   ├── channel_service.py   # Сервис каналов
│   │   ├── video_service.py     # Сервис видео
│   │   ├── subscription_service.py  # Сервис подписок
│   │   └── room_service.py      # Сервис комнат
│   ├── websocket/               # WebSocket обработчики
│   │   ├── __init__.py
│   │   └── room_events.py       # События комнат (синхронизация видео, чат)
│   ├── static/                  # Статические файлы
│   │   ├── css/
│   │   │   ├── style.css        # Базовые стили (YouTube-подобный дизайн)
│   │   │   ├── modern.css       # Современный дизайн (glassmorphism)
│   │   │   └── components.css   # Компоненты UI
│   │   └── js/
│   │       └── app.js           # Главный JavaScript файл
│   └── templates/               # HTML шаблоны
│       ├── base.html            # Базовый шаблон
│       ├── index.html           # Главная страница
│       ├── video_player.html    # Плеер видео
│       ├── channel.html         # Страница канала
│       ├── rooms.html           # Список комнат
│       └── room.html            # Комната просмотра
├── config.py                    # Конфигурация приложения
├── run.py                       # Точка входа
├── requirements.txt             # Зависимости
├── .env.example                 # Пример переменных окружения
└── pytest.ini                   # Конфиг тестов
```

---

## 3. АРХИТЕКТУРА ПРИЛОЖЕНИЯ

### 3.1 Слой приложения (app/__init__.py)

**Функции:**
- Создание Flask приложения (factory pattern)
- Инициализация расширений (SQLAlchemy, SocketIO, Redis, Session, Limiter)
- Регистрация blueprints (маршруты)
- Регистрация обработчиков ошибок
- Настройка логирования
- Создание необходимых директорий

**Ключевые компоненты:**
```python
- db: SQLAlchemy для работы с БД
- socketio: Socket.IO для WebSocket
- login_manager: Flask-Login для управления сессиями
- session: Flask-Session для хранения сессий в Redis
- limiter: Flask-Limiter для rate limiting
- ma: Flask-Marshmallow для сериализации
- redis_client: Redis клиент для кэширования
```

---

## 4. МОДЕЛИ ДАННЫХ (app/models.py)

### 4.1 User (Пользователь)
```
- id: int (PK)
- username: str (unique, indexed)
- email: str (unique, indexed)
- password_hash: str
- is_author: bool (может ли создавать контент)
- created_at: datetime

Отношения:
- channel: 1-to-1 с Channel (каскадное удаление)
- subscriptions: 1-to-many с Subscription
- owned_rooms: 1-to-many с Room
```

### 4.2 Channel (Канал)
```
- id: int (PK)
- author_id: int (FK -> User, indexed)
- name: str
- description: text
- created_at: datetime

Отношения:
- author: many-to-1 с User
- videos: 1-to-many с Video
- subscriptions: 1-to-many с Subscription

Методы:
- subscriber_count: количество подписчиков
```

### 4.3 Video (Видео)
```
- id: int (PK)
- channel_id: int (FK -> Channel, indexed)
- title: str
- description: text
- file_path: str (путь на диске)
- duration: int (в секундах)
- access_level: str ('public', 'subscriber', 'sponsor')
- has_ads: bool
- status: str ('processing', 'ready', 'failed')
- created_at: datetime

Отношения:
- channel: many-to-1 с Channel
- rooms: 1-to-many с Room
```

### 4.4 Subscription (Подписка)
```
- id: int (PK)
- user_id: int (FK -> User, indexed)
- channel_id: int (FK -> Channel, indexed)
- is_sponsor: bool (спонсор ли)
- created_at: datetime

Уникальное ограничение: (user_id, channel_id)
```

### 4.5 Room (Комната просмотра)
```
- id: int (PK)
- owner_id: int (FK -> User, indexed)
- video_id: int (FK -> Video, indexed)
- max_participants: int (макс участников, None = без ограничений)
- message_delay: int (задержка между сообщениями в сек)
- is_active: bool
- current_position: int (текущая позиция видео в сек)
- is_playing: bool
- created_at: datetime

Отношения:
- owner: many-to-1 с User
- video: many-to-1 с Video
- participants: 1-to-many с RoomParticipant
- invitations: 1-to-many с RoomInvitation
- messages: 1-to-many с ChatMessage
```

### 4.6 RoomParticipant (Участник комнаты)
```
- id: int (PK)
- room_id: int (FK -> Room, indexed)
- user_id: int (FK -> User, indexed)
- joined_at: datetime
- last_message_at: datetime (последнее сообщение)

Уникальное ограничение: (room_id, user_id)
```

### 4.7 RoomInvitation (Приглашение в комнату)
```
- id: int (PK)
- room_id: int (FK -> Room, indexed)
- sender_id: int (FK -> User)
- recipient_id: int (FK -> User)
- status: str ('pending', 'accepted', 'declined')
- created_at: datetime
```

### 4.8 ChatMessage (Сообщение чата)
```
- id: int (PK)
- room_id: int (FK -> Room, indexed)
- user_id: int (FK -> User)
- content: text
- timestamp: datetime
```

### 4.9 Advertisement (Реклама)
```
- id: int (PK)
- title: str
- video_url: str
- duration: int (в сек)
- target_category: str
```

### 4.10 Notification (Уведомление)
```
- id: int (PK)
- user_id: int (FK -> User, indexed)
- type: str ('video_upload', 'room_invitation', 'kicked')
- content: text
- is_read: bool
- created_at: datetime
```

---

## 5. REST API ENDPOINTS

### 5.1 Аутентификация (/api/auth)

| Метод | Endpoint | Описание | Требует auth |
|-------|----------|---------|--------------|
| POST | /register | Регистрация пользователя | Нет |
| POST | /login | Вход в систему | Нет |
| POST | /logout | Выход из системы | Да |
| GET | /me | Получить текущего пользователя | Да |

**Аутентификация:** Bearer token в заголовке Authorization

### 5.2 Каналы (/api/channels)

| Метод | Endpoint | Описание | Требует auth |
|-------|----------|---------|--------------|
| GET | / | Получить все каналы | Нет |
| POST | / | Создать канал | Да |
| GET | /{id} | Получить канал по ID | Нет |
| PUT | /{id} | Обновить канал | Да (владелец) |
| GET | /{id}/videos | Получить видео канала | Нет |

### 5.3 Видео (/api/videos)

| Метод | Endpoint | Описание | Требует auth |
|-------|----------|---------|--------------|
| POST | / | Загрузить видео | Да |
| GET | /{id} | Получить видео | Нет |
| DELETE | /{id} | Удалить видео | Да (владелец) |
| GET | /{id}/stream | Получить URL потока | Нет (с проверкой доступа) |
| GET | /{id}/access | Проверить доступ | Нет |

### 5.4 Подписки (/api/subscriptions)

| Метод | Endpoint | Описание | Требует auth |
|-------|----------|---------|--------------|
| POST | /channels/{id}/subscribe | Подписаться | Да |
| DELETE | /channels/{id}/subscribe | Отписаться | Да |
| POST | /channels/{id}/sponsor | Стать спонсором | Да |
| DELETE | /channels/{id}/sponsor | Отменить спонсорство | Да |
| GET | /subscriptions/my | Мои подписки | Да |
| GET | /users/me/subscriptions | Мои подписки (полная инфо) | Да |

### 5.5 Комнаты (/api/rooms)

| Метод | Endpoint | Описание | Требует auth |
|-------|----------|---------|--------------|
| POST | / | Создать комнату | Да |
| GET | / | Получить активные комнаты | Нет |
| GET | /{id} | Получить комнату | Нет |
| POST | /{id}/join | Присоединиться | Да |
| POST | /{id}/leave | Покинуть | Да |
| POST | /{id}/kick/{user_id} | Выгнать пользователя | Да (хост) |
| POST | /{id}/invite | Пригласить | Да |

---

## 6. СЕРВИСЫ (app/services)

### 6.1 AuthService (auth_service.py)

**Методы:**
- `register_user(username, email, password)` - Регистрация
- `authenticate(username, password)` - Аутентификация
- `create_session(user)` - Создание сессии (токен)
- `validate_session(token)` - Проверка сессии
- `terminate_session(token)` - Завершение сессии
- `refresh_session(token)` - Обновление сессии

**Хранилище:** Redis (ключ: `session:{token}`, значение: `user_id`)

### 6.2 ChannelService (channel_service.py)

**Методы:**
- `create_channel(author, name, description)` - Создание канала
- `get_channel(channel_id)` - Получение канала
- `get_channel_by_author(author_id)` - Получение канала автора
- `update_channel(channel_id, **kwargs)` - Обновление
- `get_channel_videos(channel_id, status)` - Видео канала
- `delete_channel(channel_id)` - Удаление
- `to_dict(channel, include_videos)` - Сериализация

### 6.3 VideoService (video_service.py)

**Методы:**
- `upload_video(channel, file, metadata)` - Загрузка видео
- `get_video(video_id)` - Получение видео
- `delete_video(video_id)` - Удаление видео
- `check_access(video, user)` - Проверка доступа
- `should_show_ads(video, user)` - Показывать ли рекламу
- `get_access_info(video, user)` - Информация о доступе
- `get_stream_url(video)` - URL потока
- `get_videos_by_channel(channel_id, status)` - Видео канала
- `to_dict(video, include_stream_url)` - Сериализация

**Логика доступа:**
- `public`: Доступно всем
- `subscriber`: Только подписчикам
- `sponsor`: Только спонсорам

**Логика рекламы:**
- Нет рекламы если `has_ads=False`
- Нет рекламы для премиум контента (subscriber/sponsor)
- Нет рекламы для владельца канала
- Нет рекламы для спонсоров
- Реклама для публичных видео для неподписчиков

### 6.4 SubscriptionService (subscription_service.py)

**Методы:**
- `subscribe(user, channel, is_sponsor)` - Подписка
- `unsubscribe(user, channel)` - Отписка
- `upgrade_to_sponsor(user, channel)` - Стать спонсором
- `downgrade_from_sponsor(user, channel)` - Отменить спонсорство
- `is_subscribed(user, channel)` - Проверка подписки
- `is_sponsor(user, channel)` - Проверка спонсорства
- `get_user_subscriptions(user, sponsors_only)` - Подписки пользователя
- `get_channel_subscribers(channel, sponsors_only)` - Подписчики канала
- `to_dict(subscription, include_channel, include_user)` - Сериализация

### 6.5 RoomService (room_service.py)

**Методы:**
- `create_room(host_id, video_id, max_participants)` - Создание комнаты
- `get_room(room_id)` - Получение комнаты
- `get_active_rooms()` - Активные комнаты
- `join_room(room_id, user_id)` - Присоединение
- `leave_room(room_id, user_id)` - Выход
- `kick_user(room_id, host_id, user_id)` - Выгнание
- `invite_user(room_id, inviter_id, invitee_id)` - Приглашение
- `to_dict(room, include_participants)` - Сериализация

---

## 7. WEBSOCKET СОБЫТИЯ (app/websocket/room_events.py)

### 7.1 События подключения

| Событие | Данные | Описание |
|---------|--------|---------|
| connect | - | Клиент подключился |
| disconnect | - | Клиент отключился |
| join_room | {room_id, token} | Присоединиться к комнате |
| leave_room_event | {room_id} | Покинуть комнату |

### 7.2 События видео

| Событие | Данные | Описание |
|---------|--------|---------|
| play | {room_id, position} | Воспроизведение (только хост) |
| pause | {room_id, position} | Пауза (только хост) |
| seek | {room_id, position} | Перемотка (только хост) |
| sync_request | {room_id} | Запрос синхронизации |

### 7.3 События чата

| Событие | Данные | Описание |
|---------|--------|---------|
| chat_message | {room_id, message} | Отправить сообщение |

### 7.4 Broadcast события

| Событие | Данные | Описание |
|---------|--------|---------|
| room_state | {room_id, video_id, current_position, is_playing, owner_id, participants} | Состояние комнаты |
| user_joined | {user_id, username, timestamp} | Пользователь присоединился |
| user_left | {user_id, username, timestamp} | Пользователь ушел |
| play_event | {position, timestamp} | Воспроизведение |
| pause_event | {position, timestamp} | Пауза |
| seek_event | {position, timestamp} | Перемотка |
| state_sync | {position, is_playing, timestamp} | Синхронизация состояния |
| chat_message_event | {message_id, user_id, username, message, timestamp} | Сообщение чата |

---

## 8. ФРОНТЕНД АРХИТЕКТУРА

### 8.1 HTML Шаблоны

**base.html** - Базовый шаблон
- Навигация с поиском
- Модальные окна (логин, регистрация, загрузка)
- Меню пользователя
- Подключение CSS и JS

**index.html** - Главная страница
- Сетка видео
- Загрузка видео с каналов
- Скелетон загрузки
- Пустое состояние

**video_player.html** - Плеер видео
- HTML5 видеоплеер
- Информация о видео
- Информация о канале
- Кнопки подписки
- Кнопка создания комнаты

**channel.html** - Страница канала
- Информация о канале
- Сетка видео канала
- Кнопки подписки/редактирования

**rooms.html** - Список комнат
- Сетка активных комнат
- Кнопка создания комнаты
- Модальное окно создания

**room.html** - Комната просмотра
- Видеоплеер
- Список участников
- Чат в реальном времени
- Кнопки управления (пригласить, поделиться, выгнать)

### 8.2 CSS Файлы

**style.css** - Базовые стили (YouTube-подобный дизайн)
- Навигация
- Кнопки
- Видеокарточки
- Модальные окна
- Формы

**modern.css** - Современный дизайн (glassmorphism)
- Градиенты
- Blur эффекты
- Анимации
- Адаптивный дизайн
- Скелетон загрузки

**components.css** - Компоненты UI
- Badges
- Buttons (расширенные)
- Cards
- Alerts
- Tooltips
- Avatars
- Chips
- Progress indicators
- Utility классы

### 8.3 JavaScript (app.js)

**Функции аутентификации:**
- `checkAuth()` - Проверка аутентификации
- `login(event)` - Вход
- `register(event)` - Регистрация
- `logout()` - Выход

**Функции видео:**
- `uploadVideo(event)` - Загрузка видео
- `handleVideoSelect(input)` - Получение длительности видео

**Функции каналов:**
- `showMyChannel()` - Переход на мой канал
- `createUserChannel(name)` - Создание канала
- `showSubscriptions()` - Показать подписки

**Функции комнат:**
- `createRoomForVideo()` - Создание комнаты для видео
- `joinRoom(roomId)` - Присоединение к комнате
- `leaveRoom()` - Выход из комнаты

**Функции UI:**
- `showModal(modalId)` - Показать модальное окно
- `closeModal(modalId)` - Закрыть модальное окно
- `toggleUserDropdown()` - Переключить меню пользователя
- `showNotification(message, type)` - Показать уведомление

**Функции утилиты:**
- `escapeHtml(text)` - Экранирование HTML
- `formatDuration(seconds)` - Форматирование длительности

---

## 9. КОНФИГУРАЦИЯ (config.py)

### 9.1 Переменные окружения

```
FLASK_APP=run.py
FLASK_ENV=development|production|testing
SECRET_KEY=...
DATABASE_URL=sqlite:///video_platform.db или postgresql://...
REDIS_URL=redis://localhost:6379/0
UPLOAD_FOLDER=uploads/videos
THUMBNAIL_FOLDER=uploads/thumbnails
MAX_CONTENT_LENGTH=524288000 (500MB)
VIDEO_PROCESSING_ENABLED=True|False
SOCKETIO_MESSAGE_QUEUE=redis://localhost:6379/1
SOCKETIO_ASYNC_MODE=threading|eventlet|gevent
CELERY_BROKER_URL=redis://localhost:6379/2
CELERY_RESULT_BACKEND=redis://localhost:6379/3
DEFAULT_MAX_PARTICIPANTS=10
SPONSOR_MAX_PARTICIPANTS=-1 (unlimited)
RATELIMIT_STORAGE_URL=redis://localhost:6379/4
RATELIMIT_DEFAULT=100 per hour
CORS_ORIGINS=*
LOG_LEVEL=INFO|DEBUG
LOG_FILE=logs/app.log
```

### 9.2 Классы конфигурации

- **Config** - Базовая конфигурация
- **DevelopmentConfig** - Разработка (DEBUG=True)
- **ProductionConfig** - Продакшн (DEBUG=False, проверки)
- **TestingConfig** - Тестирование (in-memory БД, отключены лимиты)

---

## 10. ПОТОК ДАННЫХ

### 10.1 Загрузка видео

```
1. Пользователь выбирает видео в модальном окне
2. JavaScript получает длительность видео
3. POST /api/videos с multipart/form-data
4. VideoService.upload_video():
   - Валидация метаданных
   - Сохранение файла на диск
   - Создание записи в БД
5. Возврат информации о видео (201 Created)
6. Перезагрузка страницы
```

### 10.2 Просмотр видео

```
1. Пользователь кликает на видеокарточку
2. GET /video/{id} -> video_player.html
3. JavaScript загружает информацию о видео
4. GET /api/videos/{id} -> информация о видео
5. GET /api/videos/{id}/stream -> URL потока (с проверкой доступа)
6. HTML5 плеер загружает видео
7. Пользователь может подписаться/создать комнату
```

### 10.3 Создание комнаты

```
1. Пользователь кликает "Создать комнату"
2. POST /api/rooms с {video_id, max_participants}
3. RoomService.create_room():
   - Проверка видео
   - Определение max_participants (зависит от подписки)
   - Создание комнаты
   - Автоматическое присоединение хоста
4. Редирект на /room/{id}
5. JavaScript инициализирует WebSocket
6. Отправка join_room события
7. Получение room_state события
8. Синхронизация видео
```

### 10.4 Синхронизация видео в комнате

```
1. Хост нажимает play/pause/seek
2. JavaScript отправляет play/pause/seek событие
3. WebSocket обновляет состояние комнаты в БД
4. Broadcast play_event/pause_event/seek_event всем участникам
5. Клиенты получают события и синхронизируют видео
6. Каждые 5 сек клиенты отправляют sync_request
7. Сервер отправляет state_sync с текущим состоянием
```

### 10.5 Чат в комнате

```
1. Пользователь вводит сообщение и нажимает Enter
2. JavaScript отправляет chat_message событие
3. WebSocket обработчик:
   - Проверка rate limit (message_delay)
   - Сохранение сообщения в БД
   - Обновление last_message_at участника
4. Broadcast chat_message_event всем в комнате
5. Клиенты получают событие и добавляют сообщение в чат
```

---

## 11. БЕЗОПАСНОСТЬ

### 11.1 Аутентификация

- Bearer token в Redis
- Срок действия: 24 часа
- Хеширование паролей: bcrypt

### 11.2 Авторизация

- Проверка владельца при обновлении/удалении
- Проверка доступа к видео (public/subscriber/sponsor)
- Проверка прав хоста при управлении комнатой

### 11.3 Rate Limiting

- Flask-Limiter с Redis
- По умолчанию: 100 запросов в час
- Задержка между сообщениями в чате (message_delay)

### 11.4 CORS

- Настраивается через CORS_ORIGINS
- По умолчанию: * (все источники)

---

## 12. ПРОИЗВОДИТЕЛЬНОСТЬ

### 12.1 Кэширование

- Redis для сессий
- Redis для rate limiting
- Redis для WebSocket message queue

### 12.2 Оптимизация БД

- Индексы на часто используемых полях
- Уникальные ограничения для предотвращения дубликатов
- Каскадное удаление для целостности данных

### 12.3 Асинхронность

- Socket.IO для реал-тайм коммуникации
- Celery для фоновых задач (видео обработка)
- Threading/eventlet/gevent для асинхронного режима

---

## 13. РАСШИРЯЕМОСТЬ

### 13.1 Новые функции

- Система уведомлений (Notification модель)
- Система рекламы (Advertisement модель)
- Обработка видео (Celery задачи)
- Рекомендации видео
- Поиск видео
- Комментарии к видео

### 13.2 Интеграции

- Платежные системы (для спонсорства)
- Email уведомления
- SMS уведомления
- Социальные сети (OAuth)
- CDN для видео

---

## 14. РАЗВЕРТЫВАНИЕ

### 14.1 Разработка

```bash
python run.py
```

### 14.2 Продакшн

```bash
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 run:app
```

### 14.3 Зависимости

- Python 3.8+
- PostgreSQL (рекомендуется для продакшна)
- Redis
- FFmpeg (для обработки видео)

---

## 15. КЛЮЧЕВЫЕ ОСОБЕННОСТИ

✅ **Реал-тайм синхронизация видео** - WebSocket для синхронизации воспроизведения
✅ **Система подписок** - Обычные подписчики и спонсоры
✅ **Контроль доступа** - Public/Subscriber/Sponsor уровни
✅ **Система рекламы** - Показ рекламы в зависимости от типа пользователя
✅ **Чат в комнатах** - Реал-тайм общение участников
✅ **Rate limiting** - Защита от спама
✅ **Модульная архитектура** - Легко расширяемая структура
✅ **REST API** - Полнофункциональный API
✅ **Современный UI** - Glassmorphism дизайн

---

## 16. СТАТИСТИКА КОДА

- **Python файлы:** 11 (models, routes, 5 API, 5 services, websocket)
- **HTML шаблоны:** 6
- **CSS файлы:** 3
- **JavaScript файлы:** 1 (основной)
- **Строк кода:** ~3000+
- **Моделей БД:** 10
- **API endpoints:** 25+
- **WebSocket событий:** 15+

