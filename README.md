# Техническое руководство по развертыванию Cypher Bot (Modernized)

Cypher Bot функционирует как изолированный микросервис со своей базой данных (для логов внутренней аналитики, статистики и администрирования). При этом ключевые финансовые транзакции, остатки товаров и балансы синхронизируются с внешним API основного сайта.

Благодаря использованию SQLAlchemy 2.0 ORM, код бота полностью СУБД-агностичен и совместим с **PostgreSQL**, **MySQL** и **SQLite** без необходимости изменения исходного кода.

---

## Архитектура микросервиса

```mermaid
graph TD
    Telegram[Telegram Client] <--> Bot[Aiogram 3 Bot Service]
    Bot <--> LocalDB[(Local DB: PostgreSQL / MySQL / SQLite)]
    Bot <--> Redis[(Redis: FSM & Tasks Queue)]
    Worker[Export Worker Service] <--> Redis
    Worker <--> LocalDB
    Bot <--> APIClient[External API Client]
    APIClient <--> MainSite[Marketplace Website API]
    WebhookServer[Webhook Server: aiohttp] <--> Bot
    Merchant[Merchant Gateway] -->|POST /api/v1/payments/webhook| WebhookServer
```

### Основные компоненты:
1. **Aiogram 3 Bot Service (bot/main.py)** — хэндлеры клиентов, админ-панель, прием входящих сообщений.
2. **Export Worker (bot/worker.py)** — асинхронный воркер, выполняющий фоновый экспорт отчетов о покупках за 3 месяца.
3. **Webhook Server (aiohttp)** — встроенный веб-сервер для моментального зачисления платежей от внешних шлюзов.
4. **Local DB** — база данных для хранения учетных записей пользователей, логов транзакций, покупок и динамических настроек текстов/кнопок (`system_settings`).
5. **External API Client (bot/api/client.py)** — клиент интеграции для связи с сайтом (2FA-коды, верификация привязки аккаунта, получение динамического каталога товаров).

---

## Конфигурационные переменные (.env)

Скопируйте `.env.example` в `.env` и укажите параметры:

```ini
# Telegram Bot настройки
BOT_TOKEN=your_bot_token_here
SUPPORT_USERNAME=sup_cypher
DEBUG=true

# Список Telegram ID администраторов (через запятую)
ADMIN_IDS=123456789,987654321

# DBMS-agnostic URL подключения (если задан, переопределяет отдельные DB_ параметры ниже)
# DATABASE_URL=postgresql+asyncpg://postgres:cypher_db_secure_pass@postgres:5432/cypher_db
# DATABASE_URL=mysql+aiomysql://root:cypher_db_secure_pass@mysql:3306/cypher_db

# Устаревшие параметры подключения (для совместимости)
DB_USER=postgres
DB_PASSWORD=cypher_db_secure_pass
DB_HOST=postgres
DB_PORT=5432
DB_NAME=cypher_db

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Внешнее API сайта маркетплейса (может быть как http://localhost:8000, так и .onion доменом)
EXTERNAL_API_URL=http://cyphermarket55x.onion
EXTERNAL_API_TOKEN=site_side_super_secret_token

# Локальный SOCKS5 прокси для маршрутизации Tor трафика (используется при указании .onion доменов)
TOR_PROXY=socks5://127.0.0.1:9050

# Локальный вебхук для приема уведомлений об оплате
WEBHOOK_PORT=8080
WEBHOOK_SECRET=local_payment_webhook_secret_signature
```

---

## Инструкция по переключению СУБД

По умолчанию в режиме `DEBUG=true` используется локальный файл базы данных SQLite (`sqlite+aiosqlite:///cypher_local.db`).

В продакшене вы можете использовать любую поддерживаемую реляционную базу данных. Для переключения СУБД достаточно раскомментировать или добавить переменную `DATABASE_URL` в `.env`:

### 1. Переключение на PostgreSQL:
```ini
DATABASE_URL=postgresql+asyncpg://[user]:[password]@[host]:[port]/[database_name]
```
*Драйвер: `asyncpg` (уже включен в requirements.txt).*

### 2. Переключение на MySQL:
```ini
DATABASE_URL=mysql+aiomysql://[user]:[password]@[host]:[port]/[database_name]
```
*Драйвер: `aiomysql`. Для работы в MySQL установите драйвер: `pip install aiomysql`.*

---

## Интеграция с сетью Tor (Tor Proxy)

Если ваш веб-сайт маркетплейса расположен в сети Tor (домен `.onion`), бот автоматически перенаправляет все исходящие API запросы через локальный SOCKS5 Tor прокси.

### Как это работает:
1. **Автоматическое обнаружение**: Бот проверяет значение `EXTERNAL_API_URL`. Если адрес хоста содержит `.onion`, бот активирует асинхронный SOCKS5 коннектор (`ProxyConnector` из библиотеки `aiohttp-socks`).
2. **Маршрутизация**: Все запросы к сайту (авторизация, проверка 2FA, получение каталога и оформление заказов) проксируются через Tor-адрес, указанный в `TOR_PROXY` (по умолчанию `socks5://127.0.0.1:9050`).
3. **Отказоустойчивость**: Для борьбы с высокой латентностью (latency) сети Tor тайм-аут запроса автоматически увеличивается с **10 секунд** до **30 секунд** при обращении к скрытым сервисам.

---

## Синхронизация заказов и баланса (API Checkout)

Для обеспечения безопасности и предотвращения расхождения балансов:
1. **Проведение покупки**: При нажатии кнопки покупки товара бот обращается напрямую к сайту через `POST /api/v1/marketplace/buy`.
2. **Списание**: Сайт списывает средства с баланса пользователя и возвращает данные товара (лицензионный ключ/информацию).
3. **Локальное зеркалирование**: В случае успешного ответа бот уменьшает баланс пользователя в локальной базе данных и заносит записи в таблицы `purchases` и `transactions`. Это позволяет администраторам строить верную статистику в админ-панели бота.

---

## Пошаговая инструкция по запуску через Docker-Compose

Проект настроен на сборку и запуск одной командой. В контейнерах разворачиваются база данных PostgreSQL, Redis, бот и фоновый воркер.

### Запуск инфраструктуры:
1. Перейдите в корень проекта.
2. Соберите образы и запустите сервисы в фоновом режиме:
   ```bash
   docker-compose up -d --build
   ```
3. Проверьте статус запущенных контейнеров:
   ```bash
   docker-compose ps
   ```
4. Для просмотра логов выполнения бота выполните:
   ```bash
   docker-compose logs -f bot
   ```

### Остановка сервисов:
```bash
docker-compose down
```

---

## Управление через CLI-скрипт (cli_admin.py)

В корне проекта реализована консольная утилита для выполнения административных операций напрямую из терминала сервера:

```bash
# Просмотр статистики за последние 7 дней
python cli_admin.py stats --days 7

# Принудительная привязка Telegram ID к логину на сайте
python cli_admin.py link 123456789 test_user

# Корректировка баланса (начисление $50.00)
python cli_admin.py adjust-balance 123456789 50.00

# Корректировка баланса (списание $10.00)
python cli_admin.py adjust-balance 123456789 -10.00

# Блокировка пользователя в боте
python cli_admin.py ban 123456789

# Разблокировка пользователя в боте
python cli_admin.py unban 123456789

# Включение режима технических работ
python cli_admin.py maintenance on

# Отключение режима технических работ
python cli_admin.py maintenance off

# Динамическое изменение приветственного сообщения /start для русского языка
python cli_admin.py setting welcome_ru "🌳 Добро пожаловать! Бот обновлен!"
```
