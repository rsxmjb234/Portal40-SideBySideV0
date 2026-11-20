# Athena Query Rules

## How to run queries

Import and call `athena_query` from `athena_hello_world.py`:

```python
from athena_hello_world import athena_query

rows, bytes_scanned = athena_query("SELECT 1")
```

Returns `(rows, bytes_scanned)` where `rows` is a list of dicts and `bytes_scanned` is an int.

## SQL formatting

- One SQL statement at a time.
- No comment after the final `;`.

## Cost awareness

- Use `EXPLAIN <sql>` to check syntax — it's free (no data scanned).
- Report GB scanned after every query.
- Ask before running anything estimated over ~500 GB.

## Read-only by default

- Do not use `CREATE`, `ALTER`, or `DROP` unless explicitly asked.

## Hygiene

- Delete scratch/temp files when done.
- Never commit credentials or CSV exports.
