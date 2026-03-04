#!/usr/bin/env python3
"""
clean_fowiki_wikitext.py

Input:  fo_raw_part_*.txt  (your earlier extractor output with blocks starting "### Title")
Output: fo_clean_part_###.txt (plain Faroese-looking text, <= 25MB each)

Core rule (as you corrected):
- The allowlist is used ONLY when counting occurrence of LETTERS.
- Other metrics (length, digits, etc.) are computed on the raw line.

Pipeline:
1) Remove common Wikipedia wikitext junk (templates, refs, tables, categories, links, urls).
2) Split into lines.
3) Keep lines that pass Faroese heuristics:
   - Raw length >= MIN_LINE_LEN_RAW
   - Total letters (all alphabetic) >= MIN_TOTAL_LETTERS
   - Allowed letters (in allowlist) >= MIN_ALLOWED_LETTERS
   - allowed_letters / total_letters >= MIN_ALLOWED_RATIO
   - Digits count <= MAX_DIGITS
4) Write to rotating output files (<= 25MB).

Run:
  python .\clean_fowiki_wikitext.py
"""

import re
import glob
from pathlib import Path
import html
from collections import Counter

# =========================
# Config
# =========================
MAX_BYTES = 25 * 1024 * 1024
OUT_PREFIX = "fo_clean_part_"

# Only used for counting "allowed letters"
ALLOWED_LETTERS = set("qwertyuiopåasdfghjklæøzxcvbnmáóíúý")

# Line filters (tune if needed)
MIN_LINE_LEN_RAW = 20        # raw (post-markup-strip) characters
MIN_TOTAL_LETTERS = 10       # all alphabetic letters (NOT filtered)
MIN_ALLOWED_LETTERS = 8      # letters in allowlist
MIN_ALLOWED_RATIO = 0.80     # allowed_letters / total_letters
MAX_DIGITS = 4               # drop lines with too many digits (tables, stats, coords)

# Drop entire article blocks if they end up too small
MIN_BLOCK_CHARS = 120

# =========================
# Regexes (wikitext cleanup)
# =========================
RE_COMMENTS = re.compile(r"<!--.*?-->", re.DOTALL)

# <ref>...</ref> and <ref .../>
RE_REF_BLOCK = re.compile(r"<ref\b[^>]*>.*?</ref\s*>", re.IGNORECASE | re.DOTALL)
RE_REF_SELF  = re.compile(r"<ref\b[^>]*/\s*>", re.IGNORECASE)

# Wiki tables: {| ... |}
RE_TABLES = re.compile(r"\{\|.*?\|\}", re.DOTALL)

# Templates: {{...}} (iterative)
RE_TEMPLATES_SIMPLE = re.compile(r"\{\{[^{}]*\}\}")

# Categories, files/images, interwiki
RE_CATEGORY = re.compile(r"\[\[\s*(Bólkur|Kategori|Category)\s*:[^\]]+\]\]", re.IGNORECASE)
RE_FILE     = re.compile(r"\[\[\s*(File|Fíla|Mynd|Image)\s*:[^\]]+\]\]", re.IGNORECASE)
RE_INTERWIKI = re.compile(r"\[\[\s*[a-z\-]{2,12}\s*:[^\]]+\]\]")

# External link: [http(s)://.. label] OR [http(s)://..]
RE_EXT_LINK = re.compile(r"\[(https?://[^\s\]]+)(?:\s+([^\]]+))?\]", re.IGNORECASE)

# Bare URLs
RE_BARE_URL = re.compile(r"\bhttps?://[^\s<>\]]+\b", re.IGNORECASE)

# Internal links: [[A|B]] -> B ; [[A]] -> A ; [[A#Sec|B]] -> B ; [[A#Sec]] -> A
RE_LINK_PIPE = re.compile(r"\[\[([^\|\]]+)\|([^\]]+)\]\]")
RE_LINK_SIMPLE = re.compile(r"\[\[([^\]]+)\]\]")

# Headings == Title ==
RE_HEADING = re.compile(r"^\s*(=+)\s*(.*?)\s*\1\s*$", re.MULTILINE)

# Formatting/list/magic words
RE_BOLDITAL = re.compile(r"'''+|''")
RE_LIST_PREFIX = re.compile(r"^[\*\#\:\;]+\s*", re.MULTILINE)
RE_MAGIC = re.compile(r"__\w+__")

# Any leftover HTML tags
RE_HTML_TAGS = re.compile(r"</?[^>]+>")

# Whitespace
RE_WS = re.compile(r"[ \t]+")
RE_BLANKS = re.compile(r"\n{3,}")

# Meta line prefixes to drop (optional; conservative)
META_LINE_PREFIXES = (
    "Høvuðsgrein:", "Main article:",
    "Sí eisini:", "See also:",
    "Keldur:", "Tilvísingar:", "References:",
    "External links:", "Útvísingar:",
    "Bólkar:", "Kategori:", "Category:",
)

# Split your raw extracted blocks: "\n\n### Title"
BLOCK_SPLIT = re.compile(r"\n{2,}###\s+")


def strip_templates_iteratively(text: str, max_rounds: int = 200) -> str:
    """Remove {{...}} templates iteratively (good enough for most Wikipedia dumps)."""
    for _ in range(max_rounds):
        new = RE_TEMPLATES_SIMPLE.sub("", text)
        if new == text:
            return text
        text = new
    return text


def line_is_faroese(line: str, stats: Counter) -> bool:
    """
    Your rule:
    - Use allowlist ONLY for counting allowed letters.
    - Other metrics are computed on the raw line.
    """
    ln = line.strip()
    if len(ln) < MIN_LINE_LEN_RAW:
        stats["drop_short_raw_line"] += 1
        return False

    # Count digits (raw metric)
    digit_count = sum(ch.isdigit() for ch in ln)
    if digit_count > MAX_DIGITS:
        stats["drop_too_many_digits"] += 1
        return False

    # Count letters
    total_letters = 0           # all alphabetic letters (NOT filtered)
    allowed_letters = 0         # only allowlist letters
    for ch in ln.lower():
        if ch.isalpha():
            total_letters += 1
            if ch in ALLOWED_LETTERS:
                allowed_letters += 1

    if total_letters < MIN_TOTAL_LETTERS:
        stats["drop_too_few_total_letters"] += 1
        return False

    if allowed_letters < MIN_ALLOWED_LETTERS:
        stats["drop_too_few_allowed_letters"] += 1
        return False

    ratio = allowed_letters / total_letters
    if ratio < MIN_ALLOWED_RATIO:
        stats["drop_low_allowed_ratio"] += 1
        return False

    stats["keep_lines"] += 1
    return True


def clean_wikitext(text: str, stats: Counter) -> str:
    if not text:
        return ""

    text = html.unescape(text)

    # Comments & refs
    t2 = RE_COMMENTS.sub(" ", text)
    if t2 != text:
        stats["comments_removed"] += 1
    text = t2

    t2 = RE_REF_BLOCK.sub(" ", text)
    if t2 != text:
        stats["ref_blocks_removed"] += 1
    text = t2

    t2 = RE_REF_SELF.sub(" ", text)
    if t2 != text:
        stats["ref_self_removed"] += 1
    text = t2

    # Tables
    t2 = RE_TABLES.sub("\n", text)
    if t2 != text:
        stats["tables_removed"] += 1
    text = t2

    # Templates
    before = text
    text = strip_templates_iteratively(text)
    if text != before:
        stats["templates_removed"] += 1

    # Categories / files / interwiki
    for rx, key in (
        (RE_CATEGORY, "categories_removed"),
        (RE_FILE, "files_removed"),
        (RE_INTERWIKI, "interwiki_removed"),
    ):
        t2 = rx.sub(" ", text)
        if t2 != text:
            stats[key] += 1
        text = t2

    # External links: keep label if present; else remove
    def _ext_link_repl(m):
        label = (m.group(2) or "").strip()
        if label:
            stats["ext_links_labeled_kept"] += 1
            return label
        stats["ext_links_unlabeled_removed"] += 1
        return ""
    text = RE_EXT_LINK.sub(_ext_link_repl, text)

    # Remove bare URLs
    t2 = RE_BARE_URL.sub("", text)
    if t2 != text:
        stats["bare_urls_removed"] += 1
    text = t2

    # Headings: keep heading text
    text = RE_HEADING.sub(r"\2", text)

    # Internal links -> visible text
    text = RE_LINK_PIPE.sub(r"\2", text)
    text = RE_LINK_SIMPLE.sub(r"\1", text)

    # Formatting/list/magic/html
    text = RE_BOLDITAL.sub("", text)
    text = RE_LIST_PREFIX.sub("", text)
    text = RE_MAGIC.sub(" ", text)
    text = RE_HTML_TAGS.sub(" ", text)

    # Remove leftover brackets aggressively (common in partially-stripped markup)
    text = text.replace("[[", " ").replace("]]", " ")
    text = text.replace("[", " ").replace("]", " ")

    # Normalize whitespace/newlines
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = RE_WS.sub(" ", text)
    text = RE_BLANKS.sub("\n\n", text)

    # Line filtering
    out_lines = []
    for ln in text.split("\n"):
        ln = ln.strip()
        if not ln:
            continue

        if ln.startswith(META_LINE_PREFIXES):
            stats["meta_lines_dropped"] += 1
            continue

        if line_is_faroese(ln, stats):
            out_lines.append(ln)
        else:
            stats["lines_dropped"] += 1

    return "\n".join(out_lines).strip()


def open_part(n: int):
    fn = f"{OUT_PREFIX}{n:03d}.txt"
    print(f"[OUT] opening {fn}")
    return fn, open(fn, "w", encoding="utf-8", newline="\n")


def main():
    inputs = sorted(glob.glob("fo_raw_part_*.txt"))
    if not inputs:
        raise SystemExit("No fo_raw_part_*.txt files found in current folder.")

    part = 1
    out_name, out_f = open_part(part)
    written = 0

    stats = Counter()
    total_raw = 0
    total_clean = 0
    blocks_kept = 0
    blocks_dropped = 0

    for path in inputs:
        raw_text = Path(path).read_text(encoding="utf-8", errors="replace")
        chunks = BLOCK_SPLIT.split(raw_text)

        # chunks[0] is preamble; chunks[1:] are per-article blocks
        for ch in chunks[1:]:
            lines = ch.splitlines()
            if not lines:
                continue

            # title = lines[0].strip()  # available if you need it
            body = "\n".join(lines[1:])
            total_raw += len(body)

            cleaned = clean_wikitext(body, stats)
            total_clean += len(cleaned)

            if len(cleaned) < MIN_BLOCK_CHARS:
                blocks_dropped += 1
                continue

            payload = cleaned + "\n\n"
            b = payload.encode("utf-8")

            if written + len(b) > MAX_BYTES:
                out_f.close()
                part += 1
                out_name, out_f = open_part(part)
                written = 0

            out_f.write(payload)
            written += len(b)
            blocks_kept += 1

            if (blocks_kept + blocks_dropped) % 500 == 0:
                ratio = (total_clean / total_raw) if total_raw else 0
                print(f"[PROG] blocks={blocks_kept+blocks_dropped} kept={blocks_kept} "
                      f"clean/raw={ratio:.3f} out={out_name}")

    out_f.close()

    ratio = (total_clean / total_raw) if total_raw else 0
    print("\n[DONE]")
    print(f"raw_chars_total:    {total_raw}")
    print(f"clean_chars_total:  {total_clean}")
    print(f"clean/raw ratio:    {ratio:.3f}")
    print(f"blocks kept:        {blocks_kept}")
    print(f"blocks dropped:     {blocks_dropped}")
    print(f"files written:      {part}")
    print("\n[Stats]")
    for k in sorted(stats):
        print(f"  {k}: {stats[k]}")


if __name__ == "__main__":
    main()