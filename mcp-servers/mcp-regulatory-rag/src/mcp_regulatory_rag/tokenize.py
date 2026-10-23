"""Bilingual (zh-TW / en) tokenizer and BM25 sparse-vector encoder for Qdrant.

Qdrant's ``Modifier.IDF`` supplies the IDF term server-side; the client supplies the
saturated term-frequency part of BM25 for each (hashed) token.
"""

from __future__ import annotations

import re
import zlib
from collections import Counter

import jieba

_CJK_RUN = re.compile(r"[一-鿿]+")
_LATIN = re.compile(r"[a-z0-9][a-z0-9\-\.%]*")

EN_STOP = frozenset(
    """a an and are as at be been by for from has have in into is it its of on or that the this to was were
    will with within without which who whom whose when where while shall should may might must can could
    would also not no nor than then there these those such any all each other per via""".split()
)
ZH_STOP = frozenset(
    "的 之 與 及 或 並 以 在 為 是 於 其 等 和 將 應 由 對 中 上 下 及其 以及 或者 並且 但 而 則 即 本 該".split()
)

jieba.setLogLevel(60)  # silence model-loading chatter


def tokenize(text: str) -> list[str]:
    """Lower-case, jieba-segment CJK runs, regex-split Latin tokens, drop stopwords."""
    text = text.lower()
    tokens: list[str] = []
    pos = 0
    for m in _CJK_RUN.finditer(text):
        tokens.extend(_latin_tokens(text[pos : m.start()]))
        for tok in jieba.lcut(m.group(0)):
            tok = tok.strip()
            if len(tok) >= 2 and tok not in ZH_STOP:
                tokens.append(tok)
        pos = m.end()
    tokens.extend(_latin_tokens(text[pos:]))
    return tokens


def _latin_tokens(segment: str) -> list[str]:
    out: list[str] = []
    for m in _LATIN.finditer(segment):
        tok = m.group(0).strip(".-%")
        if len(tok) >= 2 and tok not in EN_STOP:
            out.append(tok)
    return out


def token_id(token: str) -> int:
    """Stable 32-bit id for a token (CRC32)."""
    return zlib.crc32(token.encode("utf-8")) & 0xFFFFFFFF


def bm25_sparse(
    text: str, *, k1: float = 1.2, b: float = 0.75, avg_len: float = 200.0
) -> tuple[list[int], list[float]]:
    """Return (indices, values) for a Qdrant sparse vector with BM25 tf-saturation."""
    toks = tokenize(text)
    if not toks:
        return [], []
    counts = Counter(toks)
    doc_len = len(toks)
    indices: list[int] = []
    values: list[float] = []
    seen: dict[int, int] = {}
    for tok, tf in counts.items():
        idx = token_id(tok)
        val = tf * (k1 + 1) / (tf + k1 * (1 - b + b * doc_len / avg_len))
        if idx in seen:  # hash collision: merge
            values[seen[idx]] += val
            continue
        seen[idx] = len(indices)
        indices.append(idx)
        values.append(val)
    return indices, values
