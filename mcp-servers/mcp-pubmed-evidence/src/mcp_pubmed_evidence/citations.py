"""Reference formatting (Vancouver / ICMJE and APA 7) for :class:`PubMedArticle`."""

from __future__ import annotations

import re

from .models import PubMedArticle


def _vancouver_authors(authors: list[str], limit: int = 6) -> str:
    if not authors:
        return ""
    shown = authors[:limit]
    text = ", ".join(shown)
    if len(authors) > limit:
        text += ", et al"
    return text


def _apa_author(name: str) -> str:
    """'Smith JA' → 'Smith, J. A.'"""
    parts = name.strip().split()
    if len(parts) < 2:
        return name.strip()
    last, initials = " ".join(parts[:-1]), parts[-1]
    if not re.fullmatch(r"[A-Z]{1,4}", initials):
        return name.strip()
    return f"{last}, " + " ".join(f"{c}." for c in initials)


def _apa_authors(authors: list[str]) -> str:
    if not authors:
        return ""
    formatted = [_apa_author(a) for a in authors]
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) <= 20:
        return ", ".join(formatted[:-1]) + ", & " + formatted[-1]
    return ", ".join(formatted[:19]) + ", … " + formatted[-1]


def _title_with_period(title: str) -> str:
    t = title.strip()
    if not t:
        return ""
    return t if t.endswith((".", "?", "!")) else t + "."


def format_vancouver(article: PubMedArticle) -> str:
    """ICMJE / Vancouver style, e.g.

    ``Smith J, Lee K, et al. Title. J Abbrev. 2021;12(3):123-30. doi:10.1000/xyz. PMID: 1234.``
    """
    pieces: list[str] = []
    authors = _vancouver_authors(article.authors)
    if authors:
        pieces.append(authors + ".")
    if article.title:
        pieces.append(_title_with_period(article.title))
    journal = article.journal_abbreviation or article.journal
    if journal:
        pieces.append(journal.rstrip(".") + ".")
    cite = ""
    if article.year:
        cite += str(article.year)
    if article.volume:
        cite += f";{article.volume}"
        if article.issue:
            cite += f"({article.issue})"
    if article.pages:
        cite += f":{article.pages}"
    if cite:
        pieces.append(cite + ".")
    if article.doi:
        pieces.append(f"doi:{article.doi}.")
    pieces.append(f"PMID: {article.pmid}.")
    return " ".join(pieces)


def format_apa(article: PubMedArticle) -> str:
    """APA 7 style, e.g.

    ``Smith, J., & Lee, K. (2021). Title. Journal Name, 12(3), 123–130. https://doi.org/...``
    """
    pieces: list[str] = []
    authors = _apa_authors(article.authors)
    if authors:
        pieces.append(authors)
    pieces.append(f"({article.year})." if article.year else "(n.d.).")
    if article.title:
        pieces.append(_title_with_period(article.title))
    journal = article.journal or article.journal_abbreviation
    src = journal.rstrip(".")
    if article.volume:
        src += f", {article.volume}"
        if article.issue:
            src += f"({article.issue})"
    if article.pages:
        src += f", {article.pages.replace('-', '–')}"
    if src:
        pieces.append(src + ".")
    if article.doi:
        pieces.append(f"https://doi.org/{article.doi}")
    else:
        pieces.append(article.url)
    return " ".join(p for p in pieces if p)


def format_citation(article: PubMedArticle, style: str = "vancouver") -> str:
    if style == "apa":
        return format_apa(article)
    if style == "vancouver":
        return format_vancouver(article)
    raise ValueError(f"unknown citation style {style!r}")
