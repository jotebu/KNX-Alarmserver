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


def page_info(total, page):
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(max(page, 1), pages)
    return {'total': total, 'page': page, 'pages': pages, 'page_size': PAGE_SIZE,
            'first': (page - 1) * PAGE_SIZE + 1 if total else 0,
            'last': min(page * PAGE_SIZE, total)}


def alarms_page(rows, page=1, start=None, end=None, query='', open_only=False):
    import json
    filtered = [row for row in rows if (not start or row['last_seen'] and row['last_seen'] >= start)
                and (not end or row['last_seen'] and row['last_seen'] < end)
                and (not open_only or row['status'] != 'normal' or row['quality'] != 'ok')
                and query.casefold() in json.dumps(row, ensure_ascii=False).casefold()]
    order = {'active': 0, 'clear_pending': 1, 'active_ack': 2, 'unknown': 3, 'normal': 4}
    filtered.sort(key=lambda row: (order[row['status']], row['priority'], row['id']))
    info = page_info(len(filtered), page)
    offset = (info['page'] - 1) * PAGE_SIZE
    return {'rows': filtered[offset:offset + PAGE_SIZE], **info}
