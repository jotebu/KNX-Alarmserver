"""Shared bounded pages and UTC time bounds for dashboard lists."""
from datetime import datetime, timezone

PAGE_SIZE = 200


def bounds(start, end):
    def canonical(value):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError('Datumsgrenzen benoetigen eine Zeitzone')
        return value.astimezone(timezone.utc).isoformat(timespec='microseconds')
    start, end = canonical(start), canonical(end)
    if start and end and start >= end:
        raise ValueError('Von muss vor Bis liegen')
    return start, end


def page_info(total, page, page_size=PAGE_SIZE):
    pages = max(1, (total + page_size - 1) // page_size)
    page = min(max(page, 1), pages)
    return {'total': total, 'page': page, 'pages': pages, 'page_size': page_size,
            'first': (page - 1) * page_size + 1 if total else 0,
            'last': min(page * page_size, total)}


def alarms_page(rows, page=1, start=None, end=None, query='', open_only=False, unlimited=False, incidents_only=False, status_filter=''):
    import json
    filtered = [row for row in rows if (not start or row['changed_at'] and row['changed_at'] >= start)
                and (not end or row['changed_at'] and row['changed_at'] < end)
                and (not open_only or row['status'] != 'normal' or row['quality'] != 'ok')
                and (not incidents_only or row['status'] in {'active', 'active_ack', 'clear_pending'})
                and (not status_filter or row['status'] == status_filter)
                and query.casefold() in json.dumps(row, ensure_ascii=False).casefold()]
    def changed(row):
        value = row.get('changed_at')
        if not value:
            return float('-inf')
        return datetime.fromisoformat(value).timestamp()
    filtered.sort(key=lambda row: (row['priority'], -changed(row), row['id']))
    if unlimited:
        return {'rows': filtered, 'total': len(filtered), 'shown': len(filtered), 'limit': None}
    info = page_info(len(filtered), page)
    offset = (info['page'] - 1) * PAGE_SIZE
    return {'rows': filtered[offset:offset + PAGE_SIZE], **info}
