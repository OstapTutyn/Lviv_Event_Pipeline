import json
from datetime import datetime, timezone

import requests
from airflow import DAG
from airflow.hooks.base import BaseHook
from airflow.models import Variable
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.postgres.hooks.postgres import PostgresHook

from event_utils import event_payload, parse_events, payload_hash

DOU_URL = "https://dou.ua/calendar/city/%D0%9B%D1%8C%D0%B2%D1%96%D0%B2/"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
)
S3_BUCKET = "ostap-lviv-events-data-lake"
S3_CONNECTION_ID = "aws_default"
POSTGRES_CONNECTION_ID = "lviv_events_postgres"
SOURCE_NAME = "dou"


def fetch_events():
    response = requests.get(
        DOU_URL,
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    response.raise_for_status()
    events = parse_events(response.text)

    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    s3_key = f"raw_data/{current_date}/events.json"
    S3Hook(aws_conn_id=S3_CONNECTION_ID).load_string(
        string_data=json.dumps(events, ensure_ascii=False, indent=2),
        key=s3_key,
        bucket_name=S3_BUCKET,
        replace=True,
    )
    print(f"Зібрано {len(events)} подій. S3 key: {s3_key}")


def load_events_to_postgres():
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    s3_key = f"raw_data/{current_date}/events.json"
    json_data = S3Hook(aws_conn_id=S3_CONNECTION_ID).read_key(
        key=s3_key,
        bucket_name=S3_BUCKET,
    )
    events = json.loads(json_data)

    connection = PostgresHook(postgres_conn_id=POSTGRES_CONNECTION_ID).get_conn()
    cursor = connection.cursor()

    new_events = []
    changed_count = 0
    unchanged_count = 0

    try:
        for event in events:
            event_link = event["link"]
            payload = event_payload(event)
            current_hash = payload_hash(event)

            cursor.execute(
                "SELECT payload_hash FROM event_current WHERE event_link = %s",
                (event_link,),
            )
            existing = cursor.fetchone()

            if existing is None:
                cursor.execute(
                    """
                    INSERT INTO event_current (
                        event_link,
                        title,
                        event_date_text,
                        payload,
                        payload_hash
                    )
                    VALUES (%s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        event_link,
                        event["title"],
                        event.get("date"),
                        payload,
                        current_hash,
                    ),
                )
                new_events.append(event)

            elif existing[0] != current_hash:
                cursor.execute(
                    """
                    UPDATE event_current
                    SET
                        title = %s,
                        event_date_text = %s,
                        payload = %s::jsonb,
                        payload_hash = %s,
                        last_seen_at = NOW(),
                        updated_at = NOW(),
                        is_active = TRUE
                    WHERE event_link = %s
                    """,
                    (
                        event["title"],
                        event.get("date"),
                        payload,
                        current_hash,
                        event_link,
                    ),
                )
                changed_count += 1

            else:
                cursor.execute(
                    """
                    UPDATE event_current
                    SET
                        last_seen_at = NOW(),
                        is_active = TRUE
                    WHERE event_link = %s
                    """,
                    (event_link,),
                )
                unchanged_count += 1

            cursor.execute(
                """
                INSERT INTO raw_events (source, s3_key, payload, payload_hash)
                VALUES (%s, %s, %s::jsonb, %s)
                ON CONFLICT (payload_hash) DO NOTHING
                """,
                (SOURCE_NAME, s3_key, payload, current_hash),
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()

    print(f"Нових подій: {len(new_events)}")
    print(f"Змінених подій: {changed_count}")
    print(f"Без змін: {unchanged_count}")

    return new_events

def notify_new_events():
    postgres_hook = PostgresHook(postgres_conn_id=POSTGRES_CONNECTION_ID)
    telegram_connection = BaseHook.get_connection("telegram_bot")
    chat_id = Variable.get("TELEGRAM_CHAT_ID")

    connection = postgres_hook.get_conn()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT event_link, title, event_date_text, payload_hash
        FROM event_current e
        WHERE NOT EXISTS (
            SELECT 1
            FROM telegram_notifications n
            WHERE n.event_link = e.event_link
              AND n.event_hash = e.payload_hash
              AND n.notification_type = 'new_event'
        )
        ORDER BY event_date_text, event_link;
    """)

    events = cursor.fetchall()

    try:
        for event_link, title, event_date_text, payload_hash in events:
            response = requests.post(
                f"{telegram_connection.host}/bot{telegram_connection.password}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": (
                        "🆕 Нова подія у Львові\n\n"
                        f"📌 {title}\n"
                        f"📅 {event_date_text}\n"
                        f"🔗 {event_link}"
                    ),
                },
                timeout=10,
            )
            response.raise_for_status()

            cursor.execute("""
                INSERT INTO telegram_notifications (
                    event_link,
                    event_hash,
                    notification_type
                )
                VALUES (%s, %s, 'new_event')
                ON CONFLICT DO NOTHING
            """, (event_link, payload_hash))

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()

    print(f"Надіслано повідомлень: {len(events)}")


default_args = {
    'owner': 'ostap',
    'start_date': datetime(2023, 11, 1),
    'retries': 2,
}

with DAG(
        'lviv_events_parser_dag',
        default_args=default_args,
        schedule='0 9 * * *',
        catchup=False,
        max_active_runs=1,
) as dag:
    parse_task = PythonOperator(
        task_id="parse_dou_events",
        python_callable=fetch_events
    )

    load_task = PythonOperator(
        task_id="load_events_to_postgres",
        python_callable=load_events_to_postgres
    )

    dbt_task = BashOperator(
        task_id="dbt_build",
        bash_command=(
            "/home/airflow/.local/bin/dbt build "
            "--project-dir /opt/airflow/lviv_events "
            "--profiles-dir /home/airflow/.dbt"
        ),
    )

    notify_task = PythonOperator(
        task_id="notify_new_events",
        python_callable=notify_new_events,
    )

    parse_task >> load_task >> dbt_task >> notify_task
