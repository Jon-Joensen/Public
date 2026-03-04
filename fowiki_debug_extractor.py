import xml.etree.ElementTree as ET
import re
import html

INPUT_XML = "fowiki-latest-pages-articles.xml"
MAX_BYTES = 25 * 1024 * 1024
OUT_PREFIX = "fo_plain_part_"

print("Starting extractor...")
print("Opening:", INPUT_XML)

# minimal cleanup
RE_TAGS = re.compile(r"<[^>]+>")

def clean_text(t):
    if not t:
        return ""
    t = html.unescape(t)
    t = RE_TAGS.sub("", t)
    return t.strip()

def open_part(n):
    fn = f"{OUT_PREFIX}{n:03d}.txt"
    print("Opening output file:", fn)
    return fn, open(fn, "w", encoding="utf-8")

part = 1
out_name, out_f = open_part(part)
written = 0

page_count = 0
text_found = 0
kept_pages = 0

context = ET.iterparse(INPUT_XML, events=("start","end"))

for event, elem in context:

    if event == "start":
        if page_count < 5:
            print("DEBUG start tag:", elem.tag)

    if event == "end" and elem.tag.endswith("page"):

        page_count += 1
        if page_count % 100 == 0:
            print("Processed pages:", page_count)

        text_node = None

        for child in elem.iter():
            if child.tag.endswith("text"):
                text_node = child
                break

        if text_node is None:
            print("WARNING: page without text node")
            elem.clear()
            continue

        raw = text_node.text
        raw_len = len(raw) if raw else 0

        if raw_len == 0:
            print("Empty text block")
            elem.clear()
            continue

        text_found += 1

        cleaned = clean_text(raw)
        clean_len = len(cleaned)

        if page_count < 10:
            print("DEBUG page", page_count)
            print("Raw length:", raw_len)
            print("Clean length:", clean_len)

        # remove the strict filter for now
        if clean_len < 20:
            elem.clear()
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
        kept_pages += 1

        elem.clear()

out_f.close()

print("DONE")
print("Pages seen:", page_count)
print("Pages with text:", text_found)
print("Pages kept:", kept_pages)