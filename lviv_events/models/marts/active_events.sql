select
    id,
    title,
    event_date,
    link,
    source
from {{ ref('fct_events') }}
where event_date >= current_date
order by event_date, id