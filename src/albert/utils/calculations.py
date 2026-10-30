"""Validation helpers for worksheet calculation expressions."""

from __future__ import annotations

import re

_SUM_CALL = re.compile(r"^sum\s*\(")
_WHERE_SPLIT = re.compile(r"^([\s\S]+?)\s+where\s+([\s\S]+)$", re.IGNORECASE)
_AND_CONDITION = re.compile(r"\bAND\b", re.IGNORECASE)
_OR_SPLIT = re.compile(r"\bOR\b", re.IGNORECASE)
_WHERE_WORD = re.compile(r"\bwhere\b", re.IGNORECASE)
_CONDITION = re.compile(
    r"^\s*(?:\[(?P<bracketed>[^\[\]]+)\]|(?P<bare>[A-Za-z_][A-Za-z0-9_]*))"
    r"\s*=\s*[\"'](?P<value>[^\"']+)[\"']\s*$"
)


def validate_calculation_expression(*, expression: str | None) -> None:
    """Validate a worksheet calculation expression before writing it to a cell.

    Applies the rules the platform calculation engine enforces on ingredient
    expressions, so a malformed formula is rejected with a clear message before
    anything is saved: balanced parentheses on ``sum(...)`` calls and
    well-formed ``WHERE`` filters (``OR`` between values of one key, never
    ``AND``; quoted values; a single key per filter).

    Plain column-reference formulas such as ``"=COL1-COL2"`` and expressions
    without a ``sum(...)`` call pass through unexamined.

    Parameters
    ----------
    expression : str | None
        The calculation expression to validate. ``None`` and empty strings
        mean "no formula" and are accepted.

    Raises
    ------
    ValueError
        If the expression uses ``sum(...)`` or a ``WHERE`` filter in a way the
        platform refuses.
    """
    if expression is None:
        return
    text = expression.strip()
    if text.startswith("="):
        text = text[1:].strip()
    if not text:
        return

    i = 0
    while i < len(text):
        rest = text[i:]
        match = _SUM_CALL.match(rest)
        if match and not rest.startswith(("sumAll(", "sumWhere(")):
            open_index = i + match.group(0).index("(")
            close_index = _closing_paren_index(text, open_index)
            if close_index < 0:
                raise ValueError(
                    f'Unmatched parentheses in sum(...) in the calculation expression "{expression}".'
                )
            _validate_sum_content(text[open_index + 1 : close_index], expression)
            i = close_index + 1
        else:
            i += 1


def _closing_paren_index(text: str, open_index: int) -> int:
    """Return the index of the ``)`` closing the ``(`` at ``open_index``, or -1."""
    depth = 0
    for i in range(open_index, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return i
    return -1


def _validate_sum_content(content: str, expression: str) -> None:
    """Validate the parenthesized content of one ``sum(...)`` call."""
    if re.match(r"^\s*where\b", content, re.IGNORECASE):
        raise ValueError(
            f"Missing expression before the WHERE filter in the calculation "
            f'expression "{expression}". Use the form sum(expression WHERE '
            'key = "value"), for example sum(wt% WHERE Function = "Core").'
        )
    where_match = _WHERE_SPLIT.match(content)
    if where_match:
        _validate_where_condition(where_match.group(2).strip(), expression)
    elif _WHERE_WORD.search(content):
        raise ValueError(
            f'Unsupported WHERE filter in the calculation expression "{expression}". '
            'Use the form sum(expression WHERE key = "value"), for example '
            'sum(wt% WHERE Function = "Core").'
        )


def _validate_where_condition(condition: str, expression: str) -> None:
    """Validate the right-hand side of one ``WHERE`` filter."""
    if _AND_CONDITION.search(condition):
        raise ValueError(
            f'AND conditions in WHERE filters are not supported ("{condition}" in '
            f'"{expression}"): an ingredient carries one value per filter key, so AND '
            "would match no ingredients. Use OR to include several values, for example "
            'sum(wt% WHERE Function = "Core" OR Function = "Shell").'
        )

    key = None
    for part in _OR_SPLIT.split(condition):
        condition_match = _CONDITION.match(part)
        if condition_match is None:
            raise ValueError(
                f'Unsupported WHERE condition "{part.strip()}" in the calculation '
                f'expression "{expression}". Use the form key = "value", for example '
                'Function = "Core". A property attribute in brackets, such as '
                '[Resin Type] = "Epoxy", is also accepted.'
            )
        part_key = condition_match.group("bracketed") or condition_match.group("bare")
        if key is None:
            key = part_key
        elif part_key != key:
            raise ValueError(
                f'The WHERE filter "{condition}" mixes keys ("{key}" and "{part_key}") '
                f'in the calculation expression "{expression}". All OR branches of one '
                "WHERE filter must use the same key, for example "
                'Function = "Core" OR Function = "Shell".'
            )
