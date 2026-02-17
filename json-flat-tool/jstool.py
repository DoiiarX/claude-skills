#!/usr/bin/env python3
"""
jstool - JSON flat view and edit tool

Usage:
  jstool view [file]                        # flat view (stdin if no file)
  jstool set <path> <value> [file] [-f]     # set value
  jstool <path> = <value> [file] [-f]       # set, B-style syntax
  jstool before <path> <value> [file] [-f]  # insert before index (array only)
  jstool after  <path> <value> [file] [-f]  # insert after index  (array only)
  jstool del <path> [file] [-f]             # delete key or element
  jstool set-null <path> [file] [-f]        # set value to null

Flags:
  -f   Force: write change to file (default is preview only)

Paths:
  users[0].name   object key + array index
  tags[2]         array index only
  count           root-level key
  root            the root node itself
"""

import copy as _copy
import json
import re
import sys
from typing import Any, Optional


# ── ANSI ───────────────────────────────────────────────────────────────────────
C_PATH  = "\033[36m"    # cyan      path
C_TYPE  = "\033[33m"    # yellow    type
C_VAL   = "\033[32m"    # green     value
C_EMPTY = "\033[2m"     # dim       (empty)
C_NULL  = "\033[35m"    # magenta   (null) inferred
C_UNINF = "\033[31m"    # red       unknown (null)
C_ADD   = "\033[32m"    # green     insert
C_DEL   = "\033[31m"    # red       delete
C_MOD   = "\033[33m"    # yellow    modify
C_UND   = "\033[4m"     # underline
C_BOLD  = "\033[1m"
C_DIM   = "\033[2m"
C_RESET = "\033[0m"


# ── Type helpers ───────────────────────────────────────────────────────────────
def get_type_name(data: Any) -> str:
    if data is None:           return "null"
    if isinstance(data, bool): return "boolean"   # before int
    if isinstance(data, int):  return "integer"
    if isinstance(data, float):return "number"
    if isinstance(data, str):  return "string"
    if isinstance(data, dict): return "object"
    if isinstance(data, list): return "array"
    return "unknown"


def fmt_val(data: Any) -> str:
    """Format primitive value for display (JSON conventions)."""
    if isinstance(data, bool):
        return "true" if data else "false"
    return str(data)


# ── Flatten ────────────────────────────────────────────────────────────────────
def flatten(data: Any, path: str = "root", root_level: bool = True) -> list:
    """
    Returns list of (path, type_name, value_marker):
      value_marker = None      → container with children
      value_marker = "(empty)" → empty container
      value_marker = <Any>     → primitive value (None means JSON null)
    """
    rows = []
    if isinstance(data, dict):
        rows.append((path, "object", None if data else "(empty)"))
        for k, v in data.items():
            child = k if root_level else f"{path}.{k}"
            rows.extend(flatten(v, child, False))
    elif isinstance(data, list):
        rows.append((path, "array", None if data else "(empty)"))
        for i, v in enumerate(data):
            rows.extend(flatten(v, f"{path}[{i}]", False))
    else:
        rows.append((path, get_type_name(data), data))
    return rows


# ── Null inference ─────────────────────────────────────────────────────────────
_IDX = re.compile(r'\[\d+\]')

def sig(path: str) -> str:
    return _IDX.sub('[*]', path)


def infer_nulls(rows: list) -> list:
    """Replace null type with inferred type from sibling paths."""
    known: dict[str, str] = {}
    for path, type_name, value in rows:
        # Skip containers and already-null rows
        if value is None or value == "(empty)":
            continue
        if type_name in ("null", "object", "array"):
            continue
        s = sig(path)
        if s not in known:
            known[s] = type_name

    result = []
    for path, type_name, value in rows:
        # Null primitive: value is stored as Python None, type_name == "null"
        if type_name == "null" and value is None:
            inferred = known.get(sig(path))
            result.append((path, inferred or "unknown", "(null)"))
        else:
            result.append((path, type_name, value))
    return result


# ── Schema deduplication ───────────────────────────────────────────────────────
def schema_rows(rows: list) -> list:
    """
    Collapse array indices [N] → [*] and deduplicate by structural path.
    Primitive values are hidden (show type only).
    Order is preserved (first occurrence wins).
    """
    seen: set = set()
    result = []
    for path, type_name, value in rows:
        struct_path = sig(path)          # [N] → [*]
        key = (struct_path, type_name)
        if key in seen:
            continue
        seen.add(key)
        # Hide actual primitive values; keep special markers
        if value not in (None, "(empty)", "(null)"):
            value = None                 # suppress data, show type only
        result.append((struct_path, type_name, value))
    return result


def filter_rows(rows: list, prefix: str) -> list:
    """Keep rows whose path equals prefix or starts with prefix. / prefix["""
    out = []
    for row in rows:
        p = row[0]
        if p == prefix or p.startswith(prefix + '.') or p.startswith(prefix + '['):
            out.append(row)
    return out


_ELEM_IDX = re.compile(r'\[(\d+)\]')

def elem_offset_rows(rows: list, filter_path: str, elem_skip: int) -> list:
    """
    Skip first elem_skip array elements within filtered rows.

    Element boundaries are identified by direct-child paths of filter_path:
      filter_path[N]  or  filter_path[N].anything

    Header rows (path == filter_path exactly) are always kept.
    Returns (result_rows, total_elements).
    """
    prefix_bracket = filter_path + '['
    # Regex: filter_path[N] optionally followed by . or end
    elem_re = re.compile(r'^' + re.escape(filter_path) + r'\[(\d+)\]')

    header_rows: list = []
    groups: dict = {}        # element_index (int) → [rows]
    order: list = []         # insertion-ordered element indices

    for row in rows:
        path = row[0]
        m = elem_re.match(path)
        if m:
            idx = int(m.group(1))
            if idx not in groups:
                groups[idx] = []
                order.append(idx)
            groups[idx].append(row)
        else:
            header_rows.append(row)

    total_elems = len(order)
    kept = order[elem_skip:]
    result = list(header_rows)
    for idx in kept:
        result.extend(groups[idx])
    return result, total_elems


def elem_limit_rows(rows: list, filter_path: str, elem_count: int) -> tuple:
    """
    Keep only the first elem_count array elements within filtered rows.
    Header rows (path == filter_path) are always kept.
    Returns (result_rows, total_elements).
    """
    elem_re = re.compile(r'^' + re.escape(filter_path) + r'\[(\d+)\]')

    header_rows: list = []
    groups: dict = {}
    order: list = []

    for row in rows:
        path = row[0]
        m = elem_re.match(path)
        if m:
            idx = int(m.group(1))
            if idx not in groups:
                groups[idx] = []
                order.append(idx)
            groups[idx].append(row)
        else:
            header_rows.append(row)

    total_elems = len(order)
    kept = order[:elem_count]
    result = list(header_rows)
    for idx in kept:
        result.extend(groups[idx])
    return result, total_elems


def print_row(path: str, type_name: str, value):
    p = f"{C_PATH}{path}{C_RESET}"
    t = f"{C_TYPE}{type_name}{C_RESET}"
    if value is None:
        print(f"{p} {t}")
    elif value == "(empty)":
        print(f"{p} {t} {C_EMPTY}(empty){C_RESET}")
    elif value == "(null)":
        if type_name == "unknown":
            print(f"{p} {C_UNINF}{type_name}{C_RESET} {C_UNINF}(null){C_RESET}")
        else:
            print(f"{p} {t} {C_NULL}(null){C_RESET}")
    else:
        print(f"{p} {t} {C_VAL}{fmt_val(value)}{C_RESET}")


# ── View ───────────────────────────────────────────────────────────────────────
def cmd_view(data: Any, schema: bool = False,
             filter_path: Optional[str] = None,
             limit: Optional[int] = None,
             offset: int = 0,
             elem_offset: int = 0,
             elem_limit: Optional[int] = None):
    rows = infer_nulls(flatten(data))

    if schema:
        rows = schema_rows(rows)

    if filter_path is not None:
        rows = filter_rows(rows, filter_path)

    # Element-level operations (-E / -L): must be applied before row ops
    elem_footer = ""
    total_elems: Optional[int] = None

    if (elem_offset > 0 or elem_limit is not None) and filter_path is not None:
        # Apply offset first
        if elem_offset > 0:
            rows, total_elems = elem_offset_rows(rows, filter_path, elem_offset)
        # Then apply limit
        if elem_limit is not None:
            rows, te = elem_limit_rows(rows, filter_path, elem_limit)
            if total_elems is None:
                total_elems = te
        elif total_elems is None:
            # compute total for footer without slicing
            _, total_elems = elem_offset_rows(rows, filter_path, 0)

        shown_elems = elem_limit if elem_limit is not None else (total_elems - elem_offset)
        elem_footer = (f"  (elements {elem_offset}–{elem_offset + shown_elems - 1}"
                       f" of {total_elems})")
    elif elem_offset > 0:
        offset = elem_offset   # fallback: no -F, treat as row offset

    # Row-level offset + limit
    total = len(rows)
    rows = rows[offset:]
    if limit is not None:
        rows = rows[:limit]

    for path, type_name, value in rows:
        print_row(path, type_name, value)

    # Footer
    pagination = offset > 0 or limit is not None or elem_offset > 0 or elem_limit is not None
    if pagination:
        shown_start = offset + 1
        shown_end   = offset + len(rows)
        line = f"── showing rows {shown_start}–{shown_end} of {total}{elem_footer} ──"
        print(f"{C_DIM}{line}{C_RESET}")


# ── Path parser ────────────────────────────────────────────────────────────────
def parse_path(path_str: str) -> list:
    """
    'users[0].name' → ['users', 0, 'name']
    'tags[2]'       → ['tags', 2]
    'count'         → ['count']
    'root'          → []
    'root.count'    → ['count']
    'root[0]'       → [0]
    """
    s = path_str.strip()
    if s == "root":
        return []
    if s.startswith("root."):
        s = s[5:]
    elif s.startswith("root["):
        s = s[4:]   # keep the leading '['

    segments: list = []
    # Split on '.' but not inside brackets
    # Strategy: tokenize character by character
    # Tokens: identifier, [N]
    i = 0
    while i < len(s):
        if s[i] == '[':
            # array index
            j = s.index(']', i)
            idx_str = s[i+1:j]
            if not idx_str.isdigit():
                raise ValueError(f"Non-integer index in path: {s[i:j+1]!r}")
            segments.append(int(idx_str))
            i = j + 1
            if i < len(s) and s[i] == '.':
                i += 1   # skip dot after ']'
        else:
            # key name
            j = i
            while j < len(s) and s[j] not in ('.', '['):
                j += 1
            key = s[i:j]
            if not key:
                raise ValueError(f"Empty key in path: {path_str!r}")
            segments.append(key)
            i = j
            if i < len(s) and s[i] == '.':
                i += 1   # skip dot
    return segments


def navigate(data: Any, segments: list) -> tuple:
    """
    Walk data by segments. Returns (parent, key, node).
    parent: the container holding node
    key:    str (dict key) or int (list index)
    node:   the target value
    """
    parent = None
    key: Any = None
    node = data
    for seg in segments:
        parent = node
        key = seg
        if isinstance(seg, str):
            if not isinstance(node, dict):
                raise TypeError(f"Expected object to look up key {seg!r}, got {type(node).__name__}")
            if seg not in node:
                raise KeyError(f"Key not found: {seg!r}")
            node = node[seg]
        else:  # int
            if not isinstance(node, list):
                raise TypeError(f"Expected array for index {seg}, got {type(node).__name__}")
            if not (-len(node) <= seg < len(node)):
                raise IndexError(f"Index {seg} out of range (len={len(node)})")
            node = node[seg]
    return parent, key, node


# ── Value parser ───────────────────────────────────────────────────────────────
def parse_value(val_str: str) -> Any:
    """
    Try JSON parse first (handles true/false/null/numbers/objects/arrays).
    Fall back to plain string.
    If val_str starts with '@', read value from that file path.
    """
    if val_str.startswith("@"):
        filepath = val_str[1:]
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    try:
        return json.loads(val_str)
    except json.JSONDecodeError:
        return val_str


# ── Preview helpers ────────────────────────────────────────────────────────────
def _find_first(lines: list, search: str) -> Optional[tuple]:
    """Find search in lines. Returns (line_idx, col_start, col_end) or None."""
    for i, line in enumerate(lines):
        col = line.find(search)
        if col != -1:
            return (i, col, col + len(search))
    return None


def _show_with_underline(pretty: str, line_idx: int,
                         ul_start: int, ul_end: int,
                         label: str, color: str):
    """
    Print pretty-printed JSON with an underline + label on a specific line.
    Lines far from the target are dimmed.
    """
    lines = pretty.split('\n')
    context = 3   # lines before/after to show in full

    for i, line in enumerate(lines):
        dist = abs(i - line_idx)
        prefix = "  "
        if dist > context:
            # Print nothing - skip distant lines
            if dist == context + 1:
                print(f"{C_DIM}  ...{C_RESET}")
            continue
        if i == line_idx:
            # Split line into before / target / after and colorize target
            before = line[:ul_start]
            target = line[ul_start:ul_end]
            after  = line[ul_end:]
            print(f"{prefix}{before}{color}{C_UND}{target}{C_RESET}{after}")
            # Print underline tilde row
            spaces = " " * (len(prefix) + ul_start)
            tildes = "~" * (ul_end - ul_start)
            print(f"{spaces}{color}{tildes} {label}{C_RESET}")
        else:
            print(f"{prefix}{line}")


def _find_closing_line(lines: list, open_li: int) -> int:
    """
    Given the line of an opening bracket ({ or [), find the line of its
    matching closing bracket. Simple depth counter, good enough for
    well-formed JSON.
    """
    open_char  = None
    close_char = None
    for c in lines[open_li]:
        if c == '{':
            open_char, close_char = '{', '}'
            break
        if c == '[':
            open_char, close_char = '[', ']'
            break
    if open_char is None:
        return open_li   # no bracket found, fallback

    depth = 0
    in_str = False
    escaped = False
    for li in range(open_li, len(lines)):
        for c in lines[li]:
            if escaped:
                escaped = False
                continue
            if c == '\\' and in_str:
                escaped = True
                continue
            if c == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if c == open_char:
                depth += 1
            elif c == close_char:
                depth -= 1
                if depth == 0:
                    return li
    return open_li   # fallback


def _show_insert_marker(pretty: str, open_line_idx: int,
                        indent_str: str, new_json: str, mode: str):
    """
    Show insertion marker.
    - before: marker appears BEFORE the element's opening line
    - after:  marker appears AFTER the element's closing line
    """
    lines = pretty.split('\n')
    context = 2
    insert_label = f"{indent_str}{new_json}"

    if mode == "before":
        anchor = open_line_idx        # insert before opening line
    else:
        anchor = _find_closing_line(lines, open_line_idx)  # insert after closing line

    for i, line in enumerate(lines):
        dist = abs(i - anchor)
        if dist > context:
            if dist == context + 1:
                print(f"{C_DIM}  ...{C_RESET}")
            continue
        if i == anchor and mode == "before":
            print(f"  {C_ADD}{insert_label}  ← INSERT HERE{C_RESET}")
            print(f"  {line}")
        elif i == anchor and mode == "after":
            print(f"  {line}")
            print(f"  {C_ADD}{insert_label}  ← INSERT HERE{C_RESET}")
        else:
            print(f"  {line}")


# ── Preview commands ───────────────────────────────────────────────────────────
def preview_set(data: Any, segments: list, new_val: Any, path_str: str):
    parent, key, old_val = navigate(data, segments)
    old_json = json.dumps(old_val, ensure_ascii=False)
    new_json = json.dumps(new_val, ensure_ascii=False)
    pretty   = json.dumps(data, indent=2, ensure_ascii=False)
    lines    = pretty.split('\n')

    print()
    # Find the key+value in pretty text
    if isinstance(key, str):
        search = f'"{key}": {old_json}'
        found  = _find_first(lines, search)
        if found:
            li, cs, ce = found
            # Underline only the value portion
            val_start = cs + len(f'"{key}": ')
            val_end   = cs + len(search)
            _show_with_underline(pretty, li, val_start, val_end,
                                 f"→ {new_json}", C_MOD)
        else:
            print(f"  (could not locate value in JSON text)\n")
    else:
        # Array index: search for old value literally
        found = _find_first(lines, old_json)
        if found:
            li, cs, ce = found
            _show_with_underline(pretty, li, cs, ce,
                                 f"→ {new_json}", C_MOD)
        else:
            print(f"  (could not locate value in JSON text)\n")

    print(f"\n{C_BOLD}[PREVIEW]{C_RESET} "
          f"set {C_PATH}{path_str}{C_RESET}: "
          f"{C_DEL}{old_json}{C_RESET} → {C_ADD}{new_json}{C_RESET}")
    print("Run with -f to apply.\n")


def preview_del(data: Any, segments: list, path_str: str):
    parent, key, old_val = navigate(data, segments)
    old_json = json.dumps(old_val, ensure_ascii=False)
    pretty   = json.dumps(data, indent=2, ensure_ascii=False)
    lines    = pretty.split('\n')

    print()
    if not isinstance(old_val, (dict, list)):
        # Leaf: find and underline
        if isinstance(key, str):
            search = f'"{key}": {old_json}'
        else:
            search = old_json
        found = _find_first(lines, search)
        if found:
            li, cs, ce = found
            _show_with_underline(pretty, li, cs, ce, "← DELETE", C_DEL)
        else:
            print(f"  (could not locate value in JSON text)\n")
    else:
        # Container: show compact summary
        short = old_json if len(old_json) <= 60 else old_json[:57] + "..."
        print(f"  Will delete {C_DEL}{short}{C_RESET}")
        print(f"  at path {C_PATH}{path_str}{C_RESET}")

    print(f"\n{C_BOLD}[PREVIEW]{C_RESET} "
          f"del {C_PATH}{path_str}{C_RESET}: "
          f"{C_DEL}{old_json[:60]}{'...' if len(old_json)>60 else ''}{C_RESET}")
    print("Run with -f to apply.\n")


def _find_element_line(lines: list, val: Any) -> Optional[int]:
    """
    Find the line index of a JSON element's opening character.
    For primitives: search directly. For dicts/lists: use a specific
    key-value or child value to locate the element, then backtrack to its
    opening bracket.
    """
    if not isinstance(val, (dict, list)):
        found = _find_first(lines, json.dumps(val, ensure_ascii=False))
        return found[0] if found else None

    # For dict: search for first key-value pair (more specific than just '{')
    if isinstance(val, dict) and val:
        first_key = next(iter(val))
        first_v   = val[first_key]
        if not isinstance(first_v, (dict, list)):
            # Search for "key": primitive_value
            search = f'"{first_key}": {json.dumps(first_v, ensure_ascii=False)}'
            found = _find_first(lines, search)
            if found:
                li = found[0]
                # Walk backwards to find the opening '{' of this element
                for back in range(li, max(li - 5, -1), -1):
                    stripped = lines[back].strip()
                    if stripped == '{' or stripped == '{,':
                        return back
                return li  # fallback: return the key line itself

    # For list: search for first child element
    if isinstance(val, list) and val:
        child = val[0]
        if not isinstance(child, (dict, list)):
            found = _find_first(lines, json.dumps(child, ensure_ascii=False))
            if found:
                li = found[0]
                for back in range(li, max(li - 5, -1), -1):
                    stripped = lines[back].strip()
                    if stripped == '[' or stripped == '[,':
                        return back
                return li

    return None


def preview_insert(data: Any, segments: list,
                   new_val: Any, path_str: str, mode: str):
    parent, key, cur_val = navigate(data, segments)
    if not isinstance(parent, list):
        raise ValueError(
            f"'{mode}' only works on array elements. "
            f"{path_str!r} is not an array element."
        )

    new_json = json.dumps(new_val, ensure_ascii=False)
    pretty   = json.dumps(data, indent=2, ensure_ascii=False)
    lines    = pretty.split('\n')

    # For simple primitives, search directly; for containers, use heuristic
    if not isinstance(cur_val, (dict, list)):
        found = _find_first(lines, json.dumps(cur_val, ensure_ascii=False))
        ref_li = found[0] if found else None
    else:
        ref_li = _find_element_line(lines, cur_val)

    print()
    if ref_li is not None:
        ref_line   = lines[ref_li]
        indent_len = len(ref_line) - len(ref_line.lstrip())
        indent_str = " " * indent_len
        _show_insert_marker(pretty, ref_li, indent_str, new_json, mode)
    else:
        ins_idx = key if mode == "before" else key + 1
        print(f"  Will insert {C_ADD}{new_json}{C_RESET} at index {ins_idx}\n")

    print(f"\n{C_BOLD}[PREVIEW]{C_RESET} "
          f"{mode} {C_PATH}{path_str}{C_RESET}: "
          f"{C_ADD}{new_json}{C_RESET}")
    print(f"  Array length: {len(parent)} → {len(parent)+1}")
    print("Run with -f to apply.\n")


def preview_set_null(data: Any, segments: list, path_str: str):
    parent, key, old_val = navigate(data, segments)
    old_json = json.dumps(old_val, ensure_ascii=False)
    pretty   = json.dumps(data, indent=2, ensure_ascii=False)
    lines    = pretty.split('\n')

    print()
    if isinstance(key, str):
        search    = f'"{key}": {old_json}'
        found     = _find_first(lines, search)
        if found:
            li, cs, ce = found
            val_start = cs + len(f'"{key}": ')
            val_end   = cs + len(search)
            _show_with_underline(pretty, li, val_start, val_end,
                                 "→ null", C_MOD)
        else:
            print("  (could not locate value in JSON text)\n")
    else:
        found = _find_first(lines, old_json)
        if found:
            li, cs, ce = found
            _show_with_underline(pretty, li, cs, ce, "→ null", C_MOD)
        else:
            print("  (could not locate value in JSON text)\n")

    print(f"\n{C_BOLD}[PREVIEW]{C_RESET} "
          f"set-null {C_PATH}{path_str}{C_RESET}: "
          f"{C_DEL}{old_json}{C_RESET} → {C_NULL}null{C_RESET}")
    print("Run with -f to apply.\n")


# ── Apply changes ──────────────────────────────────────────────────────────────
def apply_set(data: Any, segments: list, new_val: Any) -> Any:
    if not segments:
        return new_val
    parent, key, _ = navigate(data, segments)
    parent[key] = new_val
    return data


def apply_del(data: Any, segments: list) -> Any:
    if not segments:
        raise ValueError("Cannot delete root")
    parent, key, _ = navigate(data, segments)
    if isinstance(parent, dict):
        del parent[key]
    else:
        parent.pop(key)
    return data


def apply_before(data: Any, segments: list, new_val: Any) -> Any:
    if not segments:
        raise ValueError("Cannot insert before root")
    parent, key, _ = navigate(data, segments)
    if not isinstance(parent, list):
        raise ValueError("'before' only works on array elements")
    parent.insert(key, new_val)
    return data


def apply_after(data: Any, segments: list, new_val: Any) -> Any:
    if not segments:
        raise ValueError("Cannot insert after root")
    parent, key, _ = navigate(data, segments)
    if not isinstance(parent, list):
        raise ValueError("'after' only works on array elements")
    parent.insert(key + 1, new_val)
    return data


def apply_set_null(data: Any, segments: list) -> Any:
    if not segments:
        return None
    parent, key, _ = navigate(data, segments)
    parent[key] = None
    return data


# ── copy ───────────────────────────────────────────────────────────────────────
def apply_copy(data: Any, src_segs: list, dst_segs: list) -> Any:
    _, _, src_val = navigate(data, src_segs)
    return apply_set(data, dst_segs, _copy.deepcopy(src_val))


def preview_copy(data: Any, src_segs: list, dst_segs: list,
                 src_str: str, dst_str: str):
    _, _, src_val = navigate(data, src_segs)
    new_json = json.dumps(src_val, ensure_ascii=False)
    short = new_json if len(new_json) <= 80 else new_json[:77] + "..."

    print()
    print(f"  {C_PATH}{src_str}{C_RESET}")
    print(f"    {C_DIM}{short}{C_RESET}")
    print(f"  → {C_PATH}{dst_str}{C_RESET}")
    print(f"\n{C_BOLD}[PREVIEW]{C_RESET} "
          f"copy {C_PATH}{src_str}{C_RESET} → {C_PATH}{dst_str}{C_RESET}")
    print("Run with -f to apply.\n")


# ── merge ──────────────────────────────────────────────────────────────────────
def deep_merge(base: Any, patch: Any) -> Any:
    """Recursively merge patch into base. Dicts are merged; all other types replaced."""
    if isinstance(base, dict) and isinstance(patch, dict):
        result = dict(base)
        for k, v in patch.items():
            result[k] = deep_merge(result[k], v) if k in result else v
        return result
    return patch


def apply_merge(data: Any, segs: list, patch: Any) -> Any:
    if not segs:
        return deep_merge(data, patch)
    parent, key, node = navigate(data, segs)
    parent[key] = deep_merge(node, patch)
    return data


def preview_merge(data: Any, segs: list, patch: Any,
                  path_str: str, patch_src: str):
    node = navigate(data, segs)[2] if segs else data

    print()
    if isinstance(patch, dict) and isinstance(node, dict):
        new_keys = [k for k in patch if k not in node]
        upd_keys = [k for k in patch if k in node]
        if new_keys:
            print(f"  {C_ADD}+ add:{C_RESET}    {', '.join(new_keys)}")
        if upd_keys:
            print(f"  {C_MOD}~ update:{C_RESET}  {', '.join(upd_keys)}")
    else:
        short = json.dumps(patch, ensure_ascii=False)
        if len(short) > 80:
            short = short[:77] + "..."
        print(f"  Replace {C_PATH}{path_str}{C_RESET} with: {C_ADD}{short}{C_RESET}")

    print(f"\n{C_BOLD}[PREVIEW]{C_RESET} "
          f"merge {C_PATH}{path_str}{C_RESET} ← {C_ADD}{patch_src}{C_RESET}")
    print("Run with -f to apply.\n")


# ── JSON Schema inference ──────────────────────────────────────────────────────
_SCHEMA_SAMPLE = 20   # max array elements to sample for type merging


def _merge_schemas(schemas: list) -> dict:
    """Merge a list of schemas into one (used for array item inference)."""
    if not schemas:
        return {}
    if len(schemas) == 1:
        return schemas[0]

    types: set = set()
    for s in schemas:
        t = s.get("type")
        if t:
            types.add(t)

    if len(types) == 0:
        return {}

    if len(types) == 1:
        t = list(types)[0]

        if t == "object":
            all_props: dict = {}
            required_sets: list = []
            for s in schemas:
                for k, v in s.get("properties", {}).items():
                    if k not in all_props:
                        all_props[k] = v
                req = s.get("required", [])
                required_sets.append(set(req))
            result: dict = {"type": "object", "properties": all_props}
            if required_sets:
                common = required_sets[0].intersection(*required_sets[1:])
                if common:
                    result["required"] = sorted(common)
            return result

        if t == "array":
            sub = [s.get("items", {}) for s in schemas]
            return {"type": "array", "items": _merge_schemas(sub)}

        return {"type": t}

    # Multiple primitive types
    non_null = types - {"null"}
    if non_null and len(non_null) == 1 and "null" in types:
        return {"type": list(non_null)[0], "nullable": True}
    return {"oneOf": [{"type": t} for t in sorted(types)]}


def _infer(data: Any) -> dict:
    """Recursively infer JSON Schema for a value."""
    if data is None:
        return {"type": "null"}
    if isinstance(data, bool):
        return {"type": "boolean"}
    if isinstance(data, int):
        return {"type": "integer"}
    if isinstance(data, float):
        return {"type": "number"}
    if isinstance(data, str):
        return {"type": "string"}

    if isinstance(data, list):
        if not data:
            return {"type": "array", "items": {}}
        samples = data[:_SCHEMA_SAMPLE]
        item_schemas = [_infer(item) for item in samples]
        return {"type": "array", "items": _merge_schemas(item_schemas)}

    if isinstance(data, dict):
        if not data:
            return {"type": "object", "properties": {}}
        properties = {k: _infer(v) for k, v in data.items()}
        required = sorted(
            k for k, v in data.items()
            if v is not None and v != "" and v != [] and v != {}
        )
        result = {"type": "object", "properties": properties}
        if required:
            result["required"] = required
        return result

    return {}


def cmd_schema(data: Any, title: str = "Inferred Schema"):
    """Output JSON Schema Draft 7 inferred from data."""
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": title,
    }
    schema.update(_infer(data))
    print(json.dumps(schema, indent=2, ensure_ascii=False))


# ── I/O ────────────────────────────────────────────────────────────────────────
def read_json(file_arg: Optional[str]) -> tuple:
    """Returns (data, filepath_or_None)."""
    if file_arg:
        with open(file_arg, "r", encoding="utf-8") as f:
            raw = f.read()
        return json.loads(raw), file_arg
    raw = sys.stdin.read()
    return json.loads(raw), None


def write_json(data: Any, filepath: str):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def emit_result(data: Any, filepath: Optional[str], force: bool):
    """Write to file (if -f + filepath) or print to stdout."""
    if force and filepath:
        write_json(data, filepath)
        print(f"{C_ADD}Written to {filepath}{C_RESET}")
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))


# ── Fuzzy command suggestion ───────────────────────────────────────────────────
COMMANDS = ["view", "schema", "set", "before", "after", "del", "set-null", "copy", "merge", "help"]


def _levenshtein(a: str, b: str) -> int:
    """Edit distance between two strings."""
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            temp = dp[j]
            dp[j] = prev if a[i-1] == b[j-1] else 1 + min(prev, dp[j], dp[j-1])
            prev = temp
    return dp[n]


def suggest_commands(typo: str) -> list:
    """Return commands within edit-distance 3 of typo, sorted by distance."""
    scored = [(c, _levenshtein(typo.lower(), c)) for c in COMMANDS]
    threshold = max(2, len(typo) // 2)   # scale threshold with length
    close = [(c, d) for c, d in scored if d <= threshold]
    close.sort(key=lambda x: x[1])
    return [c for c, _ in close]


def unknown_command_error(cmd: str):
    print(f"{C_DEL}Unknown command: {cmd!r}{C_RESET}")
    suggestions = suggest_commands(cmd)
    if suggestions:
        print(f"  Did you mean: ", end="")
        print("  |  ".join(f"{C_PATH}{s}{C_RESET}" for s in suggestions))
    else:
        print(f"  Run {C_PATH}jstool help{C_RESET} to see available commands.")
    sys.exit(1)


# ── Arg helpers ────────────────────────────────────────────────────────────────
def pop_flag(args: list, flag: str) -> bool:
    if flag in args:
        args.remove(flag)
        return True
    return False


def is_bstyle(args: list) -> bool:
    """True if: jstool <path> = <value> ..."""
    return (len(args) >= 2 and args[1] == "="
            and args[0] not in ("view", "set", "before", "after",
                                 "del", "set-null", "help"))


# ── Usage ──────────────────────────────────────────────────────────────────────
def usage():
    U = C_BOLD
    R = C_RESET
    D = C_DIM
    print(f"{U}jstool{R} - JSON flat view and edit tool")
    print()
    print(f"{U}USAGE{R}")
    print(f"  jstool view   [file] [-s] [-F <path>] [-n <N>] [-O <N>] [-E <N>] [-L <N>]")
    print(f"  jstool schema [file] [--title <title>]")
    print(f"  jstool set    <path> <value> [file] [-f]")
    print(f"  jstool <path> = <value> [file] [-f]          {D}# B-style{R}")
    print(f"  jstool before <path> <value> [file] [-f]     {D}# insert before (array){R}")
    print(f"  jstool after  <path> <value> [file] [-f]     {D}# insert after  (array){R}")
    print(f"  jstool del    <path> [file] [-f]")
    print(f"  jstool set-null <path> [file] [-f]")
    print()
    print(f"{U}FLAGS{R}")
    print(f"  -f   Apply change to file (default: preview only)")
    print()
    print(f"{U}PATHS{R}")
    print(f"  root              root node")
    print(f"  count             root-level key")
    print(f"  users[0]          array element")
    print(f"  users[0].name     nested key")
    print(f"  root[0].key       root-array element key")
    print()
    print(f"{U}VALUES{R}")
    print(f"  Alice             → string")
    print(f"  42                → integer")
    print(f"  3.14              → number")
    print(f"  true / false      → boolean")
    print(f"  null              → null")
    print(f"  '{{\"k\":\"v\"}}'     → object (JSON)")
    print(f"  '[1,2,3]'         → array  (JSON)")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help", "help"):
        usage()
        sys.exit(0)

    force = pop_flag(args, "-f")

    # ── B-style: <path> = <value> [file] ──────────────────────────────────────
    if is_bstyle(args):
        path_str  = args[0]
        value_str = args[2] if len(args) > 2 else ""
        file_arg  = args[3] if len(args) > 3 else None
        data, filepath = read_json(file_arg)
        segs = parse_path(path_str)
        new_val = parse_value(value_str)
        if not force:
            preview_set(data, segs, new_val, path_str)
        else:
            apply_set(data, segs, new_val)
            emit_result(data, filepath, force)
        return

    cmd  = args[0]
    rest = args[1:]

    # ── view ──────────────────────────────────────────────────────────────────
    if cmd == "view":
        # Options: [-s] [-F <path>] [-n <N>] [-O <N>] [-E <N>] [-L <N>] [file]
        schema      = pop_flag(rest, "-s")
        filter_path = None
        limit       = None
        offset      = 0
        elem_offset = 0
        elem_limit  = None

        # Parse options (may appear in any order)
        i = 0
        positional = []
        while i < len(rest):
            a = rest[i]
            if a == "-F" and i + 1 < len(rest):
                filter_path = rest[i + 1]; i += 2
            elif a == "-n" and i + 1 < len(rest):
                limit = int(rest[i + 1]); i += 2
            elif a == "-O" and i + 1 < len(rest):
                offset = int(rest[i + 1]); i += 2
            elif a == "-E" and i + 1 < len(rest):
                elem_offset = int(rest[i + 1]); i += 2
            elif a == "-L" and i + 1 < len(rest):
                elem_limit = int(rest[i + 1]); i += 2
            else:
                positional.append(a); i += 1

        file_arg = positional[0] if positional else None
        data, _ = read_json(file_arg)
        cmd_view(data, schema=schema, filter_path=filter_path,
                 limit=limit, offset=offset,
                 elem_offset=elem_offset, elem_limit=elem_limit)

    # ── schema ────────────────────────────────────────────────────────────────
    elif cmd == "schema":
        title = "Inferred Schema"
        i = 0
        positional = []
        while i < len(rest):
            if rest[i] == "--title" and i + 1 < len(rest):
                title = rest[i + 1]; i += 2
            else:
                positional.append(rest[i]); i += 1
        file_arg = positional[0] if positional else None
        data, _ = read_json(file_arg)
        cmd_schema(data, title)

    # ── set ───────────────────────────────────────────────────────────────────
    elif cmd == "set":
        if len(rest) < 2:
            print("Usage: jstool set <path> <value> [file] [-f]")
            sys.exit(1)
        path_str, value_str = rest[0], rest[1]
        file_arg = rest[2] if len(rest) > 2 else None
        data, filepath = read_json(file_arg)
        segs    = parse_path(path_str)
        new_val = parse_value(value_str)
        if not force:
            preview_set(data, segs, new_val, path_str)
        else:
            apply_set(data, segs, new_val)
            emit_result(data, filepath, force)

    # ── before / after ────────────────────────────────────────────────────────
    elif cmd in ("before", "after"):
        if len(rest) < 2:
            print(f"Usage: jstool {cmd} <path> <value> [file] [-f]")
            sys.exit(1)
        path_str, value_str = rest[0], rest[1]
        file_arg = rest[2] if len(rest) > 2 else None
        data, filepath = read_json(file_arg)
        segs    = parse_path(path_str)
        new_val = parse_value(value_str)
        if not force:
            preview_insert(data, segs, new_val, path_str, cmd)
        else:
            if cmd == "before":
                apply_before(data, segs, new_val)
            else:
                apply_after(data, segs, new_val)
            emit_result(data, filepath, force)

    # ── del ───────────────────────────────────────────────────────────────────
    elif cmd == "del":
        if not rest:
            print("Usage: jstool del <path> [file] [-f]")
            sys.exit(1)
        path_str = rest[0]
        file_arg = rest[1] if len(rest) > 1 else None
        data, filepath = read_json(file_arg)
        segs = parse_path(path_str)
        if not force:
            preview_del(data, segs, path_str)
        else:
            apply_del(data, segs)
            emit_result(data, filepath, force)

    # ── set-null ──────────────────────────────────────────────────────────────
    elif cmd == "set-null":
        if not rest:
            print("Usage: jstool set-null <path> [file] [-f]")
            sys.exit(1)
        path_str = rest[0]
        file_arg = rest[1] if len(rest) > 1 else None
        data, filepath = read_json(file_arg)
        segs = parse_path(path_str)
        if not force:
            preview_set_null(data, segs, path_str)
        else:
            apply_set_null(data, segs)
            emit_result(data, filepath, force)

    # ── copy ──────────────────────────────────────────────────────────────────
    elif cmd == "copy":
        if len(rest) < 2:
            print("Usage: jstool copy <src-path> <dst-path> [file] [-f]")
            sys.exit(1)
        src_str, dst_str = rest[0], rest[1]
        file_arg = rest[2] if len(rest) > 2 else None
        data, filepath = read_json(file_arg)
        src_segs = parse_path(src_str)
        dst_segs = parse_path(dst_str)
        if not force:
            preview_copy(data, src_segs, dst_segs, src_str, dst_str)
        else:
            apply_copy(data, src_segs, dst_segs)
            emit_result(data, filepath, force)

    # ── merge ─────────────────────────────────────────────────────────────────
    elif cmd == "merge":
        if len(rest) < 2:
            print("Usage: jstool merge <path> <patch.json> [file] [-f]")
            sys.exit(1)
        path_str, patch_src = rest[0], rest[1]
        file_arg = rest[2] if len(rest) > 2 else None
        data, filepath = read_json(file_arg)
        segs = parse_path(path_str)
        with open(patch_src, "r", encoding="utf-8") as pf:
            patch = json.load(pf)
        if not force:
            preview_merge(data, segs, patch, path_str, patch_src)
        else:
            data = apply_merge(data, segs, patch)
            emit_result(data, filepath, force)

    else:
        unknown_command_error(cmd)


if __name__ == "__main__":
    main()
