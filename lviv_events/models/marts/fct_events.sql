with staged as (

    select
        id,
        source,
        s3_key,
        payload_hash,
        replace(replace(title, chr(160), ' '), '&amp;', '&') as title,
        event_date_text,
        link,

        trim(
            split_part(
                replace(event_date_text, chr(10), ' '),
                ' ',
                1
            )
        )::int as event_day,

        case
            when lower(event_date_text) like '%січня%' then 1
            when lower(event_date_text) like '%лютого%' then 2
            when lower(event_date_text) like '%березня%' then 3
            when lower(event_date_text) like '%квітня%' then 4
            when lower(event_date_text) like '%травня%' then 5
            when lower(event_date_text) like '%червня%' then 6
            when lower(event_date_text) like '%липня%' then 7
            when lower(event_date_text) like '%серпня%' then 8
            when lower(event_date_text) like '%вересня%' then 9
            when lower(event_date_text) like '%жовтня%' then 10
            when lower(event_date_text) like '%листопада%' then 11
            when lower(event_date_text) like '%грудня%' then 12
        end as event_month

    from {{ ref('stg_raw_events') }}

)

select
    id,
    source,
    title,
    make_date(
        extract(year from current_date)::int,
        event_month,
        event_day
    ) as event_date,
    link,
    s3_key,
    payload_hash
from staged