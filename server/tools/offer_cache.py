"""
Short-lived store of the raw provider offers behind each entity id, so a
"Book" click can ask RouteStack for a checkout link without the client ever
holding provider tokens. Offers expire with the provider's search session.
"""
import threading
import time
from collections import OrderedDict
from typing import Any, Dict, Optional

TTL_S = 45 * 60
MAX_ITEMS = 5000

_lock = threading.Lock()
_items: "OrderedDict[str, tuple]" = OrderedDict()


def put(entity_id: str, kind: str, payload: Dict[str, Any]) -> None:
    with _lock:
        _items[entity_id] = (time.time(), kind, payload)
        _items.move_to_end(entity_id)
        while len(_items) > MAX_ITEMS:
            _items.popitem(last=False)


def get(entity_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        item = _items.get(entity_id)
        if not item:
            return None
        ts, kind, payload = item
        if time.time() - ts > TTL_S:
            _items.pop(entity_id, None)
            return None
        return {"kind": kind, **payload}
