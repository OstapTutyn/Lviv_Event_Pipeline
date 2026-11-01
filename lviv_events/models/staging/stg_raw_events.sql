with ranked_events as (

    select
        id,
        source,
        event_date,
        s3_key,
        payload_hash,
        payload->>'title' as title,
        payload->>'date' as event_date_text,
        payload->>'link' as link,
        row_number() over (
            partition by payload->>'link'
            order by id desc
        ) as row_num
    from {{ target.schema }}.raw_events

)

select
    id,
    source,
    event_date,
    s3_key,
    payload_hash,
    title,
    event_date_text,
    link
from ranked_events
where row_num = 1