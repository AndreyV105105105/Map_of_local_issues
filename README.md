# Map of Local Issues - Документация

## Содержание
- [Настройка окружения](#настройка-окружения)
- [Запуск проекта](#запуск-проекта)
- [Создание суперпользователя](#создание-суперпользователя)
- [Полезные команды](#полезные-команды)
- [Решение проблем](#решение-проблем)

## Настройка окружения

### Создание файла .env

Для работы проекта необходимо создать файл `.env` в корневой директории на основе предоставленного шаблона.

#### Шаг 1: Создайте файл .env
Создайте новый файл с именем `.env` в корне проекта.

#### Шаг 2: Заполните переменные окружения
Скопируйте следующую структуру в ваш `.env` файл и замените значения на свои:

```env
DB_NAME=map_of_local_issues_db
DB_USER=your_username_here
DB_PASSWORD=your_secure_password_here
DB_HOST=db
DB_PORT=5432

SECRET_KEY=your_generated_secret_key_here
```

#### Объяснение переменных:

- **DB_NAME** - название базы данных (можно оставить по умолчанию)
- **DB_USER** - имя пользователя PostgreSQL
- **DB_PASSWORD** - пароль для подключения к БД
- **DB_HOST** - хост базы данных (оставьте `db` для работы с Docker)
- **DB_PORT** - порт PostgreSQL (оставьте 5432)
- **SECRET_KEY** - секретный ключ Django для безопасности приложения

### Генерация SECRET_KEY для Django

#### Способ 1: Через Django (рекомендуется)

Если у вас установлен Django, выполните в командной строке:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

#### Способ 2: Через Python

Альтернативный способ с использованием стандартной библиотеки Python:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

#### Способ 3: Через OpenSSL

Если у вас установлен OpenSSL:

```bash
openssl rand -base64 64
```

Скопируйте сгенерированный ключ и вставьте его в переменную `SECRET_KEY` в файле `.env`.

#### Пример заполненного .env файла

```env
DB_NAME=map_of_local_issues_db
DB_USER=my_username
DB_PASSWORD=MySecurePassword123!
DB_HOST=db
DB_PORT=5432

SECRET_KEY=django-insecure-8^_k$&a@l+8m=7)9q#r2%t5y7u9o0i1p3*6@v8b$e^h&k=m*n_p
```

#### Важные примечания

- ⚠️ **НИКОГДА не коммитьте** реальный `.env` файл в Git
- ⚠️ Убедитесь, что `.env` добавлен в `.gitignore`
- ✅ Используйте сложные пароли длиной от 12 символов
- ✅ База данных будет создана автоматически при запуске Docker Compose
- ✅ Для разных окружений (development/production) используйте разные `.env` файлы

## Запуск проекта

### Предварительные требования

Перед запуском убедитесь, что у вас установлены:
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) для Windows
- Git (опционально)

### Инструкция по запуску

#### Шаг 1: Откройте терминал
- Нажмите `Win + R`, введите `cmd` и нажмите Enter
- Или используйте PowerShell
- Или используйте терминал в вашей IDE (VS Code, PyCharm и т.д.)

#### Шаг 2: Перейдите в директорию проекта
```bash
cd путь\к\вашему\проекту
```

#### Шаг 3: Запустите Docker Compose
```bash
docker-compose up --build
```

Флаг `--build` пересобирает образы при наличии изменений.

#### Шаг 4: Дождитесь запуска контейнеров
В консоли вы увидите процесс запуска:
- Скачивание образов PostgreSQL с PostGIS
- Сборка Django приложения
- Запуск контейнеров
- Сообщение от Django: `Starting development server at http://0.0.0.0:8000/`

#### Шаг 5: Откройте браузер
Перейдите по адресу: **[http://localhost:8000/](http://localhost:8000/)**

## Создание суперпользователя

Для доступа к административной панели Django необходимо создать суперпользователя:

### Способ 1: Когда контейнеры уже запущены
Откройте **новое окно терминала** и выполните:
```bash
docker-compose exec web python manage.py createsuperuser
```

### Способ 2: Если контейнеры не запущены
```bash
docker-compose run --rm web python manage.py createsuperuser
```

### Процесс создания:
1. Введите имя пользователя (username)
2. Введите email (опционально)
3. Введите пароль (символы не будут отображаться для безопасности)
4. Подтвердите пароль

После создания перейдите в админ-панель: **[http://localhost:8000/admin/](http://localhost:8000/admin/)**

## Полезные команды

### Запуск в фоновом режиме:
```bash
docker-compose up -d
```

### Просмотр логов:
```bash
docker-compose logs
```

### Остановка контейнеров:
```bash
docker-compose down
```

### Остановка с удалением volumes (очистка БД):
```bash
docker-compose down -v
```

### Выполнение команд в контейнере Django:
```bash
# Применение миграций
docker-compose exec web python manage.py migrate

# Создание миграций
docker-compose exec web python manage.py makemigrations

# Сбор статических файлов
docker-compose exec web python manage.py collectstatic

# Запуск тестов
docker-compose exec web python manage.py test
```

## Решение проблем

### Проблема с правами доступа на Windows:
Если возникают ошибки с volumes, попробуйте:
1. В Docker Desktop зайдите в Settings → Shared Drives
2. Убедитесь, что ваш диск расшарен
3. Перезапустите Docker

### Проблема с портами:
Если порты заняты, измените их в `docker-compose.yml`:
```yaml
ports:
  - "5433:5432"  # Вместо 5432 для БД
  - "8001:8000"  # Вместо 8000 для Django
```

### Очистка системы Docker:
Если возникают проблемы с кэшем:
```bash
docker system prune
```

### Проблема с созданием суперпользователя:
Если возникает ошибка подключения к БД при создании суперпользователя:
1. Убедитесь, что контейнер `db` запущен (`docker-compose ps`)
2. Проверьте, что в `.env` файле указаны правильные данные для подключения
3. Попробуйте перезапустить контейнеры: `docker-compose restart`

## Структура контейнеров

- **db**: PostgreSQL с PostGIS на порту 5432
- **web**: Django приложение на порту 8000

База данных автоматически создается при первом запуске с указанными в `.env` параметрами.

## Проверка работоспособности

После запуска проверьте:
1. Главная страница: [http://localhost:8000/](http://localhost:8000/)
2. Админ-панель: [http://localhost:8000/admin/](http://localhost:8000/admin/)
3. Статус контейнеров: `docker-compose ps`

---

Для дополнительной помощи обращайтесь к документации Docker и Django.