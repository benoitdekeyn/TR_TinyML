import re
from html.parser import HTMLParser
from pathlib import Path

WEB_ASSETS = Path(__file__).resolve().parent / "interface_web"
SLOT_RE = re.compile(r"\{\{(\w+)\}\}")
VOID_TAGS = {"br", "hr", "img", "input", "meta", "link", "wbr"}


class _BalanceChecker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.open_tags = []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID_TAGS:
            self.open_tags.append(tag)

    def handle_endtag(self, tag):
        if self.open_tags and self.open_tags[-1] == tag:
            self.open_tags.pop()
        else:
            self.open_tags.append(f"/{tag}")


def read_asset(name):
    return (WEB_ASSETS / name).read_text(encoding="utf-8")


def fill(template, values):
    """Remplace chaque {{clé}} du gabarit par values[clé]."""
    return SLOT_RE.sub(lambda match: str(values[match.group(1)]), template)


def _append_chunk(target, chunk):
    chunk = re.sub(r">\s+<", "><", chunk).strip()
    if not chunk:
        return
    checker = _BalanceChecker()
    checker.feed(chunk)
    checker.close()
    if checker.open_tags:
        raise ValueError(
            f"Un {{{{slot}}}} ne peut pas se trouver à l'intérieur d'un élément HTML "
            f"(balises non équilibrées : {checker.open_tags}) : {chunk[:80]!r}"
        )
    target.append_to_title(chunk)


def widget_slot(owner, attribute, factory):
    """Slot qui crée un widget VPython et le mémorise dans owner.attribute."""
    def create(position):
        widget = factory(position)
        setattr(owner, attribute, widget)
        return widget
    return create


def render_template(target, name, slots):
    """Insère un fragment HTML dans le titre d'un canevas VPython.

    Chaque {{slot}} est remplacé par le widget créé par slots[slot](position). VPython interprète
    chaque morceau de titre séparément : un slot doit donc se trouver au niveau racine du fragment,
    jamais à l'intérieur d'un élément.
    """
    template = read_asset(name)
    cursor = 0
    for match in SLOT_RE.finditer(template):
        _append_chunk(target, template[cursor:match.start()])
        slots[match.group(1)](target.title_anchor)
        cursor = match.end()
    _append_chunk(target, template[cursor:])
