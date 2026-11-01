# Lviv Event Pipeline

Автоматизований pipeline для збору IT-подій у Львові та публікації їх у
Telegram.

```text
DOU calendar -> S3 (raw JSON) -> PostgreSQL -> dbt -> Telegram bot
```

## Компоненти

- **Airflow** — щодня запускає DAG `lviv_events_parser_dag`.
- **S3** — зберігає незмінний JSON-знімок джерела за датою.
- **PostgreSQL** — містить raw-дані, поточний стан подій і журнал Telegram-сповіщень.
- **dbt** — очищає, дедуплікує та будує `fct_events`, `active_events` і `past_events`.
- **Telegram bot** — показує актуальні події кнопкою `Всі події`.
- **Redis** — брокер Celery для Airflow.

## Структура

```text
.
├── dags/{parser,event_utils}.py           # DAG, інтеграції та чиста логіка
├── lviv_events/
│   ├── dbt_project.yml
│   └── models/
│       ├── staging/stg_raw_events.sql
│       └── marts/{fct_events,active_events,past_events}.sql
├── telegram_bot/
│   ├── bot.py
│   └── formatting.py                      # Чисте форматування Telegram
│   └── Dockerfile
├── tests/                                  # unit-тести парсера і форматування
├── docker-compose.yaml
├── requirements.txt
└── .env.example
```

## Налаштування

1. Скопіюйте приклад конфігурації:

   ```bash
   cp .env.example .env
   ```

2. Заповніть `.env` реальними значеннями. Файл `.env` не можна комітити.
3. Налаштуйте в Airflow connections:
   - `aws_default` — доступ до S3;
   - `lviv_events_postgres` — PostgreSQL з таблицями pipeline;
   - `telegram_bot` — HTTP host `https://api.telegram.org` і token у password.
4. Створіть Airflow Variable `TELEGRAM_CHAT_ID`.
5. Переконайтеся, що профіль dbt `lviv_events` доступний у
   `~/.dbt/profiles.yml` або змініть volume у Compose.

## Запуск

```bash
docker compose up -d
docker compose ps
```

Airflow UI: <http://localhost:8080>. Після першого запуску активуйте DAG
`lviv_events_parser_dag` або запустіть його вручну.

Для перевірки dbt локально:

```bash
cd lviv_events
dbt build --profiles-dir ~/.dbt
```

Для запуску unit-тестів:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

## Потік даних і дедуплікація

Кожен запуск зберігає snapshot у S3. PostgreSQL підтримує current-state за
`event_link` для повторних сповіщень, а raw-шар зберігає унікальні payload за
`payload_hash`. dbt бере останню версію події за її посиланням, тому зміни
події не створюють дублікати в `active_events`.

Помилка будь-якого кроку перериває DAG; Airflow повторює задачі двічі. Запис
Telegram-сповіщення відбувається тільки після успішної відповіді Telegram API.

## Безпека

- Не зберігайте токени, паролі або ключі AWS у репозиторії.
- Для production використовуйте Airflow Connections/Variables або secret backend.
- Обмежте мережевий доступ до PostgreSQL і використовуйте TLS.
- Не використовуйте демонстраційні паролі з Docker Compose у production.

## Відомі межі

Наразі джерело подій — DOU. Додавання наступних джерел має використовувати
той самий нормалізований контракт `title`, `date`, `link` і окремий `source`.
