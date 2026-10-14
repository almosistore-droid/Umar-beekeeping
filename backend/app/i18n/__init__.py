"""Server texts in the user's language (Русский / Тоҷикӣ).

Russian is the source. `tg.json` maps every Russian text or f-string template found in the code
(see extract.py: «Улей №{0} уже есть на пасеке «{1}»») to Tajik; `tg_data.json` maps reference data stored
in the database (disease catalog). A whole string is translated when it equals a text or matches a template;
values captured by a template are translated too (they may be labels themselves), and «label: message»
pairs are translated part by part. Anything unknown — user data — is returned unchanged.

The language of the current request comes from the X-Lang header (set by the middleware in main.py);
code outside a request (bot jobs) passes the language explicitly.
"""
import json
import re
from contextvars import ContextVar
from functools import lru_cache
from pathlib import Path
from typing import Any

LANGS = ("ru", "tg")
DEFAULT = "ru"
_HERE = Path(__file__).resolve().parent
current_lang: ContextVar[str] = ContextVar("current_lang", default=DEFAULT)
_CYR = re.compile(r"[А-Яа-яЁё]")
_PH = re.compile(r"\{(\d+)\}")
# «5 дней», «2 года 3 месяца», «≈ 1 год 5 месяцев»: numbers with unit words joined in code
_NUMBER_WORDS = re.compile(r"^(≈ )?\d+(?:[.,]\d+)? [^\d\s]+(?: \d+(?:[.,]\d+)? [^\d\s]+)*$")
_SENTENCES = re.compile(r"(?<=[.!?…])(\s+)")


def normalize(lang: str | None) -> str:
    lang = (lang or "").strip().lower()[:2]
    return lang if lang in LANGS else DEFAULT


class _Catalog:
    def __init__(self, mapping: dict[str, str]):
        self.exact: dict[str, str] = {}
        self.patterns: list[tuple[str, re.Pattern, str]] = []  # (longest literal, regex, target)
        for src, dst in mapping.items():
            if not _PH.search(src):
                self.exact[src] = dst
                continue
            parts = _PH.split(src)  # literal, index, literal, index, …
            literals = parts[0::2]
            if not any(_CYR.search(lit) for lit in literals):
                continue  # «{0}: {1}» would match anything
            regex = "".join(re.escape(lit) if i % 2 == 0 else f"(?P<p{lit}>.+?)" for i, lit in enumerate(parts))
            self.patterns.append((max(literals, key=len), re.compile(f"^{regex}$", re.S), dst))
        # more literal text first = more specific
        self.patterns.sort(key=lambda p: -len(p[1].pattern))

    def translate(self, text: str, depth: int = 0) -> str:
        if depth > 3 or not text or not _CYR.search(text):
            return text
        hit = self.exact.get(text)
        if hit is not None:
            return hit
        # labels capitalised in code: «Очень слабая» from «очень слабая»
        if text[0].isupper():
            low = self.exact.get(text[0].lower() + text[1:])
            if low is not None:
                return low[:1].upper() + low[1:]
        for literal, regex, target in self.patterns:
            if literal not in text:
                continue
            m = regex.match(text)
            if m:
                values = {k[1:]: self.translate(v, depth + 1) for k, v in m.groupdict().items()}
                return _PH.sub(lambda g: values.get(g.group(1), g.group(0)), target)
        # «5 дней», «2 года» — a number and a word joined in code
        if _NUMBER_WORDS.match(text):
            tokens = [self.exact.get(tok, tok) if _CYR.search(tok) else tok for tok in text.split(" ")]
            new = " ".join(tokens)
            if new != text:
                return new
        # two sentences glued in code: «… без матки. Отметьте улей …» (the second one may be stored with a leading space)
        pieces = _SENTENCES.split(text)
        if len(pieces) > 1:
            out, changed = [], False
            for i, piece in enumerate(pieces):
                if i % 2:  # separator
                    out.append(piece)
                    continue
                new = self.translate(piece, depth + 1)
                if new == piece and (" " + piece) in self.exact:
                    new = self.exact[" " + piece].lstrip()
                changed |= new != piece
                out.append(new)
            if changed:
                return "".join(out)
        # «Проверьте введённые данные: Вес: должно быть больше 0» → translate around the first «: »
        if ": " in text:
            head, tail = text.split(": ", 1)
            new_head, new_tail = self.translate(head, depth + 1), self.translate(tail, depth + 1)
            if (new_head, new_tail) != (head, tail):
                return f"{new_head}: {new_tail}"
        return text


@lru_cache
def _catalog(lang: str) -> _Catalog | None:
    if lang == DEFAULT:
        return None
    mapping: dict[str, str] = {}
    for name in (f"{lang}_data.json", f"{lang}.json"):
        path = _HERE / name
        if path.exists():
            mapping.update(json.loads(path.read_text(encoding="utf-8")))
    return _Catalog(mapping)


def translate(text: str, lang: str | None = None) -> str:
    catalog = _catalog(normalize(lang or current_lang.get()))
    return catalog.translate(text) if catalog else text


def L(text: str) -> str:  # noqa: N802 — short on purpose: L("Улей №{0}") reads like the text itself
    """Translate a ready Russian text into the language of the current request."""
    return translate(text)


def translate_json(value: Any, lang: str) -> Any:
    """Translate every string value in a JSON document (dict keys are left alone)."""
    catalog = _catalog(normalize(lang))
    if catalog is None:
        return value

    def walk(v: Any) -> Any:
        if isinstance(v, str):
            return catalog.translate(v)
        if isinstance(v, list):
            return [walk(x) for x in v]
        if isinstance(v, dict):
            return {k: walk(x) for k, x in v.items()}
        return v

    return walk(value)
