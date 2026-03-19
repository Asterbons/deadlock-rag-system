"""
KV3 Parser — High-performance Valve KeyValues3 (.vdata) → Python dict converter.

Character-level scanner + recursive descent parser designed for 120k+ line files.

Handles:
  - <!-- kv3 ... --> header stripping
  - Nested { } → dicts, [ ] → lists (arbitrary depth)
  - resource_name:, panorama:, soundevent:, subclass: prefix stripping
  - Numeric normalisation: "6.700000" → 6.7, "4" → 4, scientific notation
  - Boolean normalisation: true/false → True/False
  - Trailing commas in arrays  [1, 2, 3, ]
  - Assignments with both = and :
  - Multi-line blocks where { or [ is on the next line
  - Pipe-separated enum flags in quoted strings
  - Empty inline blocks  key = {}  or  key = []
  - // line comments and /* */ block comments
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.setrecursionlimit(5000)

__all__ = ["parse_kv3", "parse_kv3_file"]

# Known Valve prefixes to strip from values
_VALVE_PREFIXES = frozenset(("resource_name", "panorama", "soundevent", "subclass"))


# ── value normalisation ─────────────────────────────────────────────────────

def _normalise(raw: str):
    """Convert a raw string token to its best Python type."""
    v = raw.strip()
    if not v:
        return ""

    # Remove surrounding quotes
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        v = v[1:-1]

    # Booleans
    if v == "true":
        return True
    if v == "false":
        return False

    # Numeric (int / float / scientific)
    try:
        f = float(v)
        i = int(f)
        return i if f == i else round(f, 10)
    except (ValueError, OverflowError):
        pass

    return v


# ── character-level scanner ─────────────────────────────────────────────────

class _Scanner:
    """Fast single-pass scanner over KV3 text.

    All hot-path string comparisons use str.startswith(prefix, pos)
    to avoid O(N) slice allocations.
    """

    __slots__ = ("_src", "_len", "_pos")

    def __init__(self, src: str) -> None:
        self._src = src
        self._len = len(src)
        self._pos = 0

    # -- low-level helpers ---------------------------------------------------

    @property
    def pos(self) -> int:
        return self._pos

    def _at_end(self) -> bool:
        return self._pos >= self._len

    def _peek_char(self) -> str:
        return self._src[self._pos] if self._pos < self._len else "\0"

    def _advance(self) -> str:
        ch = self._src[self._pos]
        self._pos += 1
        return ch

    def _skip_ws_and_comments(self) -> None:
        """Skip whitespace, commas, // comments, /* */ comments, <!-- --> headers."""
        src = self._src
        length = self._len
        pos = self._pos
        while pos < length:
            ch = src[pos]
            # whitespace + commas (commas are array delimiters, treated as ws)
            if ch <= " " or ch == ",":
                pos += 1
                continue
            # // line comment → jump to end of line with find()
            if ch == "/" and src.startswith("//", pos):
                nl = src.find("\n", pos + 2)
                pos = nl + 1 if nl != -1 else length
                continue
            # /* block comment */
            if ch == "/" and src.startswith("/*", pos):
                end = src.find("*/", pos + 2)
                pos = end + 2 if end != -1 else length
                continue
            # <!-- kv3 header -->
            if ch == "<" and src.startswith("<!--", pos):
                end = src.find("-->", pos + 4)
                pos = end + 3 if end != -1 else length
                continue
            break
        self._pos = pos

    def _read_quoted_string(self) -> str:
        """Read a double-quoted string (opening " already consumed).
        Returns the content WITHOUT surrounding quotes."""
        src = self._src
        length = self._len
        pos = self._pos
        # Fast path: no escape characters (vast majority of KV3 strings)
        start = pos
        while pos < length:
            ch = src[pos]
            if ch == "\\":
                # Slow path: has escapes, switch to builder
                break
            if ch == '"':
                result = src[start:pos]
                self._pos = pos + 1
                return result
            pos += 1
        # Slow path with escape handling
        parts: list[str] = [src[start:pos]]
        while pos < length:
            ch = src[pos]
            if ch == "\\":
                pos += 1
                if pos < length:
                    parts.append(src[pos])
                    pos += 1
                continue
            if ch == '"':
                self._pos = pos + 1
                return "".join(parts)
            parts.append(ch)
            pos += 1
        # unterminated string
        self._pos = pos
        return "".join(parts)

    def _read_bare_token(self) -> str:
        """Read an unquoted token (identifier, number, bare value).
        Stops at whitespace or structural characters.
        Handles inline quoted sections so that braces inside quotes
        (e.g. panorama:\"file://{images}/...\") are not treated as structure."""
        src = self._src
        length = self._len
        pos = self._pos
        start = pos
        while pos < length:
            ch = src[pos]
            if ch <= " " or ch in "{}[]=,":
                break
            # inline quoted section — skip through it entirely
            if ch == '"':
                pos += 1
                while pos < length and src[pos] != '"':
                    if src[pos] == "\\":
                        pos += 1  # skip escaped char
                    pos += 1
                if pos < length:
                    pos += 1  # skip closing quote
                continue
            # stop at // or /* comment start
            if ch == "/" and pos + 1 < length and src[pos + 1] in "/*":
                break
            pos += 1
        self._pos = pos
        return src[start:pos]

    # -- public token reader -------------------------------------------------

    def next_token(self) -> str | None:
        """Return the next meaningful token, or None at end-of-input.

        Structural tokens: { } [ ] =
        Quoted strings: returned WITH surrounding quotes.
        Bare words / numbers: returned as-is.
        Valve prefixes (resource_name:"...") are stripped, returning
        the inner quoted value with quotes.
        """
        self._skip_ws_and_comments()
        if self._at_end():
            return None

        ch = self._peek_char()

        # structural characters
        if ch in "{}[]=":
            self._advance()
            return ch

        # quoted string — returned WITH quotes so caller can distinguish
        if ch == '"':
            self._advance()
            content = self._read_quoted_string()
            return '"' + content + '"'

        # bare token (identifier, number, true/false, prefixed value …)
        token = self._read_bare_token()
        if not token:
            # shouldn't happen, but be safe
            self._advance()
            return self.next_token()

        # Handle Valve prefix tokens: resource_name:"...", panorama:"..."
        # The prefix ends with : and the next char is "
        if token.endswith(":") and not self._at_end() and self._peek_char() == '"':
            prefix = token[:-1].lower()
            if prefix in _VALVE_PREFIXES:
                self._advance()  # consume opening "
                inner = self._read_quoted_string()
                return '"' + inner + '"'  # return as plain quoted string

        # Handle prefix:value all in one token (prefix:"quoted" already read
        # through by _read_bare_token's inline-quote handling)
        colon_idx = token.find(":")
        if colon_idx > 0 and colon_idx < len(token) - 1:
            prefix = token[:colon_idx].lower()
            if prefix in _VALVE_PREFIXES:
                rest = token[colon_idx + 1:]
                # strip surrounding quotes if present
                if len(rest) >= 2 and rest[0] == '"' and rest[-1] == '"':
                    rest = rest[1:-1]
                return '"' + rest + '"'

        # If token ENDS with a colon (e.g., subclass: {), drop the token entirely
        # and just return the next dict block as the value.
        if token.endswith(":") and token[:-1].lower() in _VALVE_PREFIXES:
            return self.next_token()

        return token


# ── recursive descent parser ────────────────────────────────────────────────

_SENTINEL = object()


class _Parser:
    """Recursive-descent KV3 parser consuming tokens from a _Scanner."""

    __slots__ = ("_scanner", "_peeked")

    def __init__(self, scanner: _Scanner) -> None:
        self._scanner = scanner
        self._peeked: str | None | object = _SENTINEL

    def parse(self) -> dict:
        result = {}
        # The file may have an outer { ... } or just be a sequence of key-values.
        # It also might have an initial { generic_data_type = ... } followed by
        # other top-level abilities. We just parse key-value pairs until EOF.
        # If the very first token is {, we consume it, but we also ignore any
        # stray closing } at the root level so we can keep parsing.
        
        first = self._peek()
        if first == "{":
            self._consume()

        while True:
            tok = self._peek()
            if tok is None:
                break
            if tok == "}":
                # Stray closing brace at EOF level, consume and keep going
                self._consume()
                continue
            if tok in ("{", "[", "]", "="):
                self._consume()
                continue
            
            key = self._unquote(self._consume())
            nxt = self._peek()
            if nxt in ("=", ":"):
                self._consume()
            
            result[key] = self._parse_value()

        return result

    # -- token helpers -------------------------------------------------------

    def _peek(self) -> str | None:
        if self._peeked is _SENTINEL:
            self._peeked = self._scanner.next_token()
        return self._peeked

    def _consume(self) -> str | None:
        if self._peeked is not _SENTINEL:
            tok = self._peeked
            self._peeked = _SENTINEL
            return tok
        return self._scanner.next_token()

    # -- recursive rules -----------------------------------------------------

    def _parse_dict(self) -> dict:
        """Parse key=value (or key:value) pairs until } or EOF."""
        result: dict = {}
        iteration_count = 0
        while True:
            iteration_count += 1
            if iteration_count % 10000 == 0:
                print(f"DEBUG: _parse_dict loop iteration {iteration_count}, pos={self._scanner.pos}, peek={self._peek()}")
            tok = self._peek()
            if tok is None or tok == "}":
                self._consume()
                break

            # skip stray structural tokens in dict context
            if tok in ("{", "[", "]", "="):
                self._consume()
                continue

            # tok is a key (bare word or quoted string)
            key = self._unquote(self._consume())

            # expect = or : as assignment operator
            nxt = self._peek()
            if nxt == "=" or nxt == ":":
                self._consume()

            # parse the value
            result[key] = self._parse_value()

        return result

    def _parse_list(self) -> list:
        """Parse values until ] or EOF."""
        result: list = []
        while True:
            tok = self._peek()
            if tok is None or tok == "]":
                self._consume()
                break
            # stray } in list context — consume and stop
            if tok == "}":
                self._consume()
                break
            # stray = or : in list context — skip
            if tok == "=":
                self._consume()
                continue

            result.append(self._parse_value())

        return result

    def _parse_value(self):
        """Parse a single value: dict, list, or scalar."""
        tok = self._peek()
        if tok is None:
            return ""
        if tok == "{":
            self._consume()
            return self._parse_dict()
        if tok == "[":
            self._consume()
            return self._parse_list()
        if tok == "}" or tok == "]":
            # empty value before closing delimiter — do NOT consume
            return ""
        # scalar
        self._consume()
        return _normalise(tok)

    @staticmethod
    def _unquote(s: str | None) -> str:
        if s is None:
            return ""
        if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
            return s[1:-1]
        return s


# ── public API ──────────────────────────────────────────────────────────────

def parse_kv3(text: str) -> dict:
    """Parse a KV3 text string and return the top-level dict."""
    scanner = _Scanner(text)
    parser = _Parser(scanner)
    return parser.parse()


def parse_kv3_file(filepath: str | Path) -> dict:
    """Parse a KV3 .vdata file from disk and return a dict."""
    text = Path(filepath).read_text(encoding="utf-8")
    return parse_kv3(text)
