# T7 — Import/export (`evtrack/io_formats.py`)
Functions (all operate on `list[Task]`; ids preserved on export, ignored on import → returned Tasks have `id=None`):
## CSV
- `to_csv(tasks) -> str`: header `id,title,status,priority,tags,due`; tags joined with `;`; due ISO or empty;
  standard `csv` module quoting (QUOTE_MINIMAL), line terminator `\n`.
- `from_csv(text) -> list[Task]`: inverse. Header must match exactly (else `ValueError`). Empty tags field → `[]`.
  Rows with invalid data (bad status/priority/date, empty title) → `ValueError` mentioning the 1-based data row number (`row 3`).
## iCalendar (RFC 5545 subset, VTODO)
- `to_ics(tasks) -> str`: lines joined by `\r\n`, ending with `\r\n`:
  `BEGIN:VCALENDAR`, `VERSION:2.0`, `PRODID:-//evtrack//EN`, then per task:
  `BEGIN:VTODO`, `UID:evtrack-<id>@local` (id None → `UID:evtrack-new-<index>@local`, index 0-based in list),
  `SUMMARY:<escaped title>`, `STATUS:NEEDS-ACTION` (open) or `STATUS:COMPLETED` (done),
  `PRIORITY:<1|5|9>` (priority 1→1, 2→5, 3→9), `CATEGORIES:<comma-joined escaped tags>` (omit line if no tags),
  `DUE;VALUE=DATE:YYYYMMDD` (omit if no due), `END:VTODO`; finally `END:VCALENDAR`.
  Text escaping: `\` → `\\`, `;` → `\;`, `,` → `\,`, newline → `\n`.
  Line folding: any content line longer than 75 octets (UTF-8) is split into chunks of at most 75 octets for the first
  line and 74 octets for following lines, each continuation line starting with a single space; never split inside a
  UTF-8 multibyte character.
- `from_ics(text) -> list[Task]`: inverse of the above (accepts `\r\n` or `\n`; unfolds lines starting with a space
  or tab; unescapes; PRIORITY 1–4→1, 5 or 0 or missing→2, 6–9→3; STATUS COMPLETED→done else open; unknown
  properties ignored). A VTODO without SUMMARY → `ValueError`.
