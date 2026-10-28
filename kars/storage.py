"""Atomic snapshots with retries for short-lived Windows sharing violations."""
import json
import time
import uuid


def read_text_retry(path):
    for attempt in range(20):
        try:
            return path.read_text(encoding='utf-8')
        except PermissionError:
            if attempt==19:
                raise
            time.sleep(.01)


def read_json(path,fallback=None):
    try:
        return json.loads(read_text_retry(path))
    except (OSError,ValueError):
        return {} if fallback is None else fallback


def atomic_json(path,value):
    temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    temporary.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')
    try:
        for attempt in range(40):
            try:
                temporary.replace(path)
                return
            except PermissionError:
                if attempt==39:
                    raise
                time.sleep(min(.1,.01*(attempt+1)))
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except PermissionError:
            # A scanner may also hold the abandoned temporary file briefly.
            # Preserve the actual replacement error if one is already propagating.
            pass
