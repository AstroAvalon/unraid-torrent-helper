# ==============================
# app/pathmap.py
# ==============================
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, List, Optional, Any


def _norm(p: str) -> str:
    """Normalize slashes and trim trailing slash except for root '/'. """
    if not p:
        return "/"
    p = p.replace("\\", "/")
    if p != "/" and p.endswith("/"):
        p = p[:-1]
    return p or "/"


@dataclass(frozen=True)
class MapRule:
    container: str
    host: str

    def __post_init__(self):
        object.__setattr__(self, "container", _norm(self.container))
        object.__setattr__(self, "host", _norm(self.host))


class PathMapper:
    """
    Bi-directional path translator between container paths and host paths.
    Chooses the *longest-prefix* rule (most specific) and preserves the remainder.
    Accepts rules as:
      - dicts: {"container": "...", "host": "..."}
      - MapRule instances
      - objects with .container and .host attributes (e.g., your PathMapping)
    """

    def __init__(self, rules: Iterable[Any]):
        parsed: List[MapRule] = []
        for r in rules:
            if isinstance(r, MapRule):
                parsed.append(r)
            elif isinstance(r, dict):
                parsed.append(MapRule(container=r["container"], host=r["host"]))
            else:
                # generic object with attributes
                try:
                    parsed.append(MapRule(container=getattr(r, "container"), host=getattr(r, "host")))
                except Exception as e:
                    raise TypeError(f"Unsupported rule type {type(r)!r}: {e}")

        # sort by descending container/host length so more specific wins
        self._by_container = sorted(parsed, key=lambda r: len(r.container), reverse=True)
        self._by_host = sorted(parsed, key=lambda r: len(r.host), reverse=True)

    # ---------- helpers ----------
    @staticmethod
    def _under(path: str, root: str) -> bool:
        p = _norm(path)
        r = _norm(root)
        return p == r or p.startswith(r + "/")

    @staticmethod
    def _join(root: str, rest: str) -> str:
        root = _norm(root)
        if not rest or rest == "/":
            return root
        if rest.startswith("/"):
            rest = rest[1:]
        return root + "/" + rest

    @staticmethod
    def _rest(path: str, root: str) -> str:
        p = _norm(path)
        r = _norm(root)
        if p == r:
            return ""
        assert p.startswith(r + "/"), (p, r)
        return p[len(r) + 1 :]

    # ---------- public API ----------
    def container_to_host(self, container_path: str) -> Optional[str]:
        p = _norm(container_path)
        for rule in self._by_container:
            if self._under(p, rule.container):
                rest = self._rest(p, rule.container) if p != rule.container else ""
                return self._join(rule.host, rest)
        return None

    def host_to_container(self, host_path: str) -> Optional[str]:
        p = _norm(host_path)
        for rule in self._by_host:
            if self._under(p, rule.host):
                rest = self._rest(p, rule.host) if p != rule.host else ""
                return self._join(rule.container, rest)
        return None