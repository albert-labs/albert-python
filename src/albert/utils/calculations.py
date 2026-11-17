"""Validation helpers for worksheet calculation expressions."""

from __future__ import annotations

import re

_AGGREGATION_CALL = re.compile(r"(sum|harmonicMean)\s*\(", re.IGNORECASE)
_WHERE_SPLIT = re.compile(r"^([\s\S]+?)\s+where\s+([\s\S]+)$", re.IGNORECASE)
_AND_CONDITION = re.compile(r"\bAND\b", re.IGNORECASE)
_OR_SPLIT = re.compile(r"\bOR\b", re.IGNORECASE)
_WHERE_WORD = re.compile(r"\bwhere\b", re.IGNORECASE)
_CONDITION = re.compile(
    r"^\s*(?:\[(?P<bracketed>[^\[\]]+)\]|(?P<bare>[A-Za-z_][A-Za-z0-9_]*))"
    r"\s*=\s*[\"'](?P<value>[^\"']+)[\"']\s*$"
)
# Markers of the ingredient expression language, including the built-in
# aliases. An aggregation whose content has none of these is a legacy
# cell-reference formula (e.g. "=SUM(COL5:COL9)") and is not examined.
_INGREDIENT_DSL = re.compile(
    r"wt%|wt_pct|parts_mass|ingredient_basis|function_tag|\[[^\[\]]+\]|\bwhere\b",
    re.IGNORECASE,
)
# Filter-key aliases the platform resolves to the same key before comparing.
_FILTER_KEY_ALIASES = {"Function": "function_tag"}
_QUOTED = re.compile(r'"[^"\n]*"|\'[^\'\n]*\'')
_TRAILING_OPERATOR = re.compile(r"[+\-*/^=(,]$")


def validate_calculation_expression(*, expression: str | None) -> None:
    """Validate a worksheet calculation expression before writing it to a cell.

    Applies the rules the platform calculation engine enforces on ingredient
    expressions, so a malformed formula is rejected with a clear message before
    anything is saved: lowercase aggregations (``sum``, ``harmonicMean``),
    balanced parentheses, ``WHERE`` filters only inside ``sum(...)`` and in
    ``key = "value"`` form (``OR`` between values of one key, never ``AND``),
    complete operands, and no trailing operators.

    Plain column-reference formulas such as ``"=COL1-COL2"`` or
    ``"=SUM(COL5:COL9)"`` are a different formula language and pass through
    unexamined.

    Parameters
    ----------
    expression : str | None
        The calculation expression to validate. ``None`` and empty strings
        mean "no formula" and are accepted.

    Raises
    ------
    ValueError
        If the expression uses an aggregation, a ``WHERE`` filter, or an
        operator in a way the platform refuses.
    """
    if expression is None:
        return
    text = expression.strip()
    if text.startswith("="):
        text = text[1:].strip()
    if not text:
        return

    _validate_scope(text=text, expression=expression)
    _validate_delimiters(text=text, expression=expression)


def _validate_scope(*, text: str, expression: str) -> None:
    """Validate one expression level: its aggregation calls and the text between them."""
    spans: list[tuple[int, int]] = []
    i = 0
    quote: str | None = None
    while i < len(text):
        char = text[i]
        if quote is not None:
            if char == quote:
                quote = None
            i += 1
            continue
        if char in "\"'":
            quote = char
            i += 1
            continue
        match = _AGGREGATION_CALL.match(text, i)
        if match is None:
            i += 1
            continue
        name = match.group(1)
        open_index = i + match.group(0).index("(")
        close_index = _closing_paren_index(text, open_index)
        if close_index < 0:
            raise ValueError(
                f"Unmatched parentheses in {name}(...) in the calculation expression "
                f'"{expression}".'
            )
        _validate_aggregation(
            name=name, content=text[open_index + 1 : close_index], expression=expression
        )
        spans.append((i, close_index))
        i = close_index + 1
    if _WHERE_WORD.search(_outside_spans(text, spans)):
        raise ValueError(
            "WHERE filters are supported only inside sum(...) in the calculation "
            f'expression "{expression}".'
        )
    stripped = text.rstrip()
    if _TRAILING_OPERATOR.search(stripped):
        raise ValueError(
            f'The calculation expression "{expression}" ends with the operator '
            f'"{stripped[-1]}", which does not parse. Complete or remove the trailing operator.'
        )


def _validate_aggregation(*, name: str, content: str, expression: str) -> None:
    """Validate one aggregation call, recursing into nested calls."""
    canonical = _canonical_name(name)
    if name != canonical:
        # A differently cased aggregation does not compile. Legacy cell totals
        # such as "=SUM(COL5:COL9)" are another language and pass.
        if _INGREDIENT_DSL.search(content):
            raise ValueError(
                f'The aggregation "{name}" in the calculation expression "{expression}" '
                "does not compile: aggregations are spelled in lowercase "
                "(sum, harmonicMean)."
            )
        return
    if name == "sum":
        _validate_sum_content(content, expression)
    else:
        _validate_scope(text=content, expression=expression)


def _canonical_name(name: str) -> str:
    """Return the exact spelling of an aggregation name (``sum`` or ``harmonicMean``)."""
    return {"sum": "sum", "harmonicmean": "harmonicMean"}[name.lower()]


def _closing_paren_index(text: str, open_index: int) -> int:
    """Return the index of the ``)`` closing the ``(`` at ``open_index``, or -1.

    Parentheses inside quoted values do not count toward the depth.
    """
    depth = 0
    quote: str | None = None
    for i in range(open_index, len(text)):
        char = text[i]
        if quote is not None:
            if char == quote:
                quote = None
            continue
        if char in "\"'":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
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
        inner = where_match.group(1)
        _validate_where_condition(where_match.group(2).strip(), expression)
    else:
        inner = content
        if _WHERE_WORD.search(_QUOTED.sub("", content)):
            raise ValueError(
                f'Unsupported WHERE filter in the calculation expression "{expression}". '
                'Use the form sum(expression WHERE key = "value"), for example '
                'sum(wt% WHERE Function = "Core").'
            )
    _validate_scope(text=inner, expression=expression)


def _validate_where_condition(condition: str, expression: str) -> None:
    """Validate the right-hand side of one ``WHERE`` filter.

    Mirrors the platform's condition parser, including its limitations: an OR
    word or an apostrophe inside a quoted value is refused there too.
    """
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
        part_key = _FILTER_KEY_ALIASES.get(part_key, part_key)
        if key is None:
            key = part_key
        elif part_key != key:
            raise ValueError(
                f'The WHERE filter "{condition}" mixes keys ("{key}" and "{part_key}") '
                f'in the calculation expression "{expression}". All OR branches of one '
                "WHERE filter must use the same key, for example "
                'Function = "Core" OR Function = "Shell". Filter keys are case-sensitive.'
            )


def _outside_spans(text: str, spans: list[tuple[int, int]]) -> str:
    """Return ``text`` with the aggregation spans blanked and quoted values removed."""
    masked = list(text)
    for start, end in spans:
        for j in range(start, end + 1):
            masked[j] = " "
    return _QUOTED.sub("", "".join(masked))


def _validate_delimiters(*, text: str, expression: str) -> None:
    """Reject unbalanced parentheses at the whole-expression level.

    Ingredient expressions also refuse a parenthesis inside a quoted value:
    the platform's own scan does not skip quotes, so it refuses them too.
    """
    check_quoted_parens = bool(_INGREDIENT_DSL.search(text) or _AGGREGATION_CALL.search(text))
    depth = 0
    quote: str | None = None
    for char in text:
        if quote is not None:
            if char == quote:
                quote = None
            elif check_quoted_parens and char in "()":
                raise ValueError(
                    f"A parenthesis inside a quoted value of the calculation expression "
                    f'"{expression}" does not parse.'
                )
            continue
        if char in "\"'":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                raise ValueError(
                    f'Unmatched parentheses in the calculation expression "{expression}".'
                )
    if depth != 0:
        raise ValueError(f'Unmatched parentheses in the calculation expression "{expression}".')
