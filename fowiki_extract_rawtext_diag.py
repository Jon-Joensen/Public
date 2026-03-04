import xml.etree.ElementTree as ET
from collections import Counter

INPUT_XML = "fowiki-latest-pages-articles.xml"
MAX_BYTES = 25 * 1024 * 1024
OUT_PREFIX = "fo_raw_part_"

SKIP_REDIRECTS = True
SKIP_NON_MAIN_NS = True  # titles containing ":" (Kategori:, Fíla:, etc.)

def open_part(n: int):
    fn = f"{OUT_PREFIX}{n:03d}.txt"
    print(f"[OUT] opening {fn}")
    return fn, open(fn, "w", encoding="utf-8", newline="\n")

def main():
    part = 1
    out_name, out_f = open_part(part)
    written = 0

    pages_seen = 0
    pages_with_text = 0
    pages_written = 0
    redirects_skipped = 0
    nonmain_skipped = 0
    empty_text = 0

    # Diagnostics on sizes
    top_raw_sizes = []
    ns_counter = Counter()

    context = ET.iterparse(INPUT_XML, events=("end",))

    for event, elem in context:
        if not elem.tag.endswith("page"):
            continue

        pages_seen += 1

        title = None
        ns_val = None
        has_redirect = False
        text_content = None

        # One-pass walk over direct children + revision/text
        for c in elem:
            if c.tag.endswith("title"):
                title = c.text or ""
            elif c.tag.endswith("ns"):
                ns_val = c.text or ""
            elif c.tag.endswith("redirect"):
                has_redirect = True
            elif c.tag.endswith("revision"):
                for r in c:
                    if r.tag.endswith("text"):
                        text_content = r.text

        ns_counter[ns_val] += 1

        if SKIP_NON_MAIN_NS and title and ":" in title:
            nonmain_skipped += 1
            elem.clear()
            continue

        if SKIP_REDIRECTS and has_redirect:
            redirects_skipped += 1
            elem.clear()
            continue

        if text_content is None:
            elem.clear()
            continue

        pages_with_text += 1

        raw = text_content.strip()
        if not raw:
            empty_text += 1
            elem.clear()
            continue

        # Keep some trace of where text came from (optional, but useful)
        payload = f"\n\n### {title}\n\n{raw}\n"
        b = payload.encode("utf-8")

        # rotate file
        if written + len(b) > MAX_BYTES:
            out_f.close()
            part += 1
            out_name, out_f = open_part(part)
            written = 0

        out_f.write(payload)
        written += len(b)
        pages_written += 1

        # track top sizes
        sz = len(raw)
        if len(top_raw_sizes) < 10:
            top_raw_sizes.append((sz, title))
            top_raw_sizes.sort(reverse=True)
        else:
            if sz > top_raw_sizes[-1][0]:
                top_raw_sizes[-1] = (sz, title)
                top_raw_sizes.sort(reverse=True)

        if pages_seen % 1000 == 0:
            print(f"[PROG] pages={pages_seen} written={pages_written} out={out_name}")

        elem.clear()

    out_f.close()

    print("\n[DONE]")
    print(f"pages_seen:        {pages_seen}")
    print(f"pages_with_text:   {pages_with_text}")
    print(f"pages_written:     {pages_written}")
    print(f"redirects_skipped: {redirects_skipped}")
    print(f"nonmain_skipped:   {nonmain_skipped}")
    print(f"empty_text:        {empty_text}")
    print(f"files_written:     {part}")
    print("\n[NS distribution] (top 10)")
    for k, v in ns_counter.most_common(10):
        print(f"  ns={k!r}: {v}")

    print("\n[Top 10 largest pages]")
    for sz, t in top_raw_sizes:
        print(f"  {sz:7d} chars : {t}")

if __name__ == "__main__":
    main()