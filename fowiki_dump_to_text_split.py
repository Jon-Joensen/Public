import re
import html
import xml.etree.ElementTree as ET

INPUT_XML = "fowiki-latest-pages-articles.xml"
MAX_BYTES = 24 * 1024 * 1024
OUT_PREFIX = "fo_plain_part_"

# --- Wikitext cleanup (pragmatic, not perfect) ---
RE_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
RE_REF_TAG = re.compile(r"<ref\b[^>/]*?/?>", re.IGNORECASE)
RE_REF_BLOCK = re.compile(r"<ref\b[^>]*>.*?</ref\s*>", re.IGNORECASE | re.DOTALL)
RE_ANY_TAG = re.compile(r"</?[^>]+>")  # leftover HTML tags
RE_CATEGORY = re.compile(r"\[\[\s*(Kategori|Category)\s*:[^\]]+\]\]", re.IGNORECASE)
RE_FILE = re.compile(r"\[\[\s*(Fíla|File|Mynd|Image)\s*:[^\]]+\]\]", re.IGNORECASE)
RE_INTERWIKI = re.compile(r"\[\[\s*[a-z\-]{2,12}\s*:[^\]]+\]\]")  # [[en:...]] etc.
RE_URL = re.compile(r"\[https?://[^\s\]]+(?:\s+([^\]]+))?\]")     # [url label]
RE_BOLDITAL = re.compile(r"'''''|'''|''")                         # formatting quotes
RE_HEADING = re.compile(r"^\s*=+\s*(.*?)\s*=+\s*$", re.MULTILINE) # == Heading ==
RE_TABLE = re.compile(r"\{\|.*?\|\}", re.DOTALL)                  # wiki tables
RE_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")                       # simple templates (looped)
RE_LINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]")  # [[target|label]]
RE_BRACES = re.compile(r"\{|\}")                                  # leftover braces
RE_MULTISPACE = re.compile(r"[ \t]+")
RE_MULTINEWLINE = re.compile(r"\n{3,}")

def strip_templates(text: str) -> str:
    # Remove templates iteratively (handles nesting poorly but works surprisingly well in practice)
    prev = None
    while prev != text:
        prev = text
        text = RE_TEMPLATE.sub("", text)
    return text

def wikitext_to_plain(text: str) -> str:
    if not text:
        return ""

    text = html.unescape(text)
    text = RE_COMMENT.sub("", text)
    text = RE_REF_BLOCK.sub("", text)
    text = RE_REF_TAG.sub("", text)
    text = RE_TABLE.sub("", text)
    text = strip_templates(text)

    # Remove common non-content links
    text = RE_CATEGORY.sub("", text)
    text = RE_FILE.sub("", text)
    text = RE_INTERWIKI.sub("", text)

    # Replace external links: [url label] -> label (or nothing if no label)
    def _url_repl(m):
        label = m.group(1)
        return label if label else ""
    text = RE_URL.sub(_url_repl, text)

    # Replace internal links: [[target|label]] -> label or target
    def _link_repl(m):
        target = (m.group(1) or "").strip()
        label = (m.group(2) or "").strip()
        return label if label else target
    text = RE_LINK.sub(_link_repl, text)

    # Remove formatting quotes
    text = RE_BOLDITAL.sub("", text)

    # Headings: keep heading text as a line
    text = RE_HEADING.sub(r"\1", text)

    # Remove leftover HTML tags
    text = RE_ANY_TAG.sub("", text)

    # Final whitespace cleanup
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = RE_BRACES.sub("", text)
    text = RE_MULTISPACE.sub(" ", text)
    text = RE_MULTINEWLINE.sub("\n\n", text)
    return text.strip()

def open_part(n: int):
    fn = f"{OUT_PREFIX}{n:03d}.txt"
    return fn, open(fn, "w", encoding="utf-8", newline="\n")

def main():
    part = 1
    out_name, out_f = open_part(part)
    written = 0
    pages_kept = 0

    # We'll stream end events; when a <page> ends we have its full subtree.
    ns = "{http://www.mediawiki.org/xml/export-0.10/}"
    context = ET.iterparse(INPUT_XML, events=("end",))

    for event, elem in context:
        if elem.tag == f"{ns}page":
            # Skip non-article namespaces (titles containing ':', e.g. "Kategori:", "Fíla:", etc.)
            title_el = elem.find(f"{ns}title")
            title = title_el.text if title_el is not None else ""
            if ":" in (title or ""):
                elem.clear()
                continue

            # Grab latest revision text
            text_el = elem.find(f"{ns}revision/{ns}text")
            raw = text_el.text if text_el is not None else ""
            plain = wikitext_to_plain(raw)

            # Only keep meaningful text
            if plain and len(plain) >= 200:
                payload = plain + "\n\n"
                b = payload.encode("utf-8")
                if written + len(b) > MAX_BYTES:
                    out_f.close()
                    part += 1
                    out_name, out_f = open_part(part)
                    written = 0

                out_f.write(payload)
                written += len(b)
                pages_kept += 1

                if pages_kept % 200 == 0:
                    print(f"[OK] kept {pages_kept} pages; current file: {out_name}")

            elem.clear()

    out_f.close()
    print(f"Done. Kept {pages_kept} pages. Wrote {part} file(s). Last: {out_name}")

if __name__ == "__main__":
    main()