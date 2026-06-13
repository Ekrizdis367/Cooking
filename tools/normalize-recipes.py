#!/usr/bin/env python3
"""Normalize Cooking vault recipes to the Pantry import template shape."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

UNIT_CANON = {
    "c": "cup",
    "cup": "cup",
    "cups": "cup",
    "tablespoon": "tbsp",
    "tablespoons": "tbsp",
    "tbsp": "tbsp",
    "tbsps": "tbsp",
    "tsp": "tsp",
    "tsps": "tsp",
    "teaspoon": "tsp",
    "teaspoons": "tsp",
    "ounce": "oz",
    "ounces": "oz",
    "oz": "oz",
    "fl oz": "fl oz",
    "floz": "fl oz",
    "fluid ounce": "fl oz",
    "fluid ounces": "fl oz",
    "pound": "lb",
    "pounds": "lb",
    "lb": "lb",
    "lbs": "lb",
    "gram": "g",
    "grams": "g",
    "g": "g",
    "kilogram": "kg",
    "kilograms": "kg",
    "kg": "kg",
    "milliliter": "ml",
    "milliliters": "ml",
    "ml": "ml",
    "liter": "l",
    "liters": "l",
    "l": "l",
    "clove": "clove",
    "cloves": "clove",
    "can": "can",
    "cans": "can",
    "jar": "jar",
    "jars": "jar",
    "bag": "bag",
    "bags": "bag",
    "box": "box",
    "boxes": "box",
    "bottle": "bottle",
    "bottles": "bottle",
    "pack": "pack",
    "packs": "pack",
    "package": "pack",
    "packages": "pack",
    "bunch": "bunch",
    "bunches": "bunch",
    "head": "head",
    "heads": "head",
    "slice": "slice",
    "slices": "slice",
    "stick": "stick",
    "sticks": "stick",
    "pinch": "pinch",
    "pinches": "pinch",
    "dash": "dash",
    "dashes": "dash",
    "sprig": "sprig",
    "sprigs": "sprig",
    "stalk": "stalk",
    "stalks": "stalk",
    "loaf": "loaf",
    "loaves": "loaf",
    "dozen": "dozen",
    "piece": "piece",
    "pieces": "piece",
}

SMALL_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "but",
    "by",
    "for",
    "from",
    "in",
    "into",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
    "without",
}

UNIT_PATTERN = "|".join(
    sorted({re.escape(k) for k in UNIT_CANON}, key=len, reverse=True)
)
QUANTITY_PATTERN = (
    r"(?:"
    r"\d+(?:\.\d+)?(?:\s*/\s*\d+)?"
    r"(?:\s+\d+\s*/\s*\d+)?"
    r"|[¼½¾⅓⅔⅛⅜⅝⅞]"
    r"|\d+\s+[¼½¾⅓⅔⅛⅜⅝⅞]"
    r")"
)
IGNORE_INGREDIENT_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"^water$",
        r"^(cold|warm|hot|ice|boiling|lukewarm|room temperature|filtered|tap) water$",
        r"^salt$",
        r"^(kosher|sea|table|fine sea|coarse|coarse sea|flaky|fine|himalayan|pink|pink himalayan|iodized) salt$",
        r"^pepper$",
        r"^(black|white|ground black|ground white|freshly ground black|freshly ground|fresh ground|cracked black|coarse black|ground) pepper$",
        r"^salt (and|&) (black )?pepper$",
        r"^(black )?pepper (and|&) salt$",
        r"^ice$",
        r"^ice cubes?$",
        r"^oil$",
        r"^(olive|extra-virgin olive|extra virgin olive|vegetable|canola|cooking|neutral|light olive|sunflower|safflower) oil$",
        r"^(nonstick |non-stick |non stick )?cooking spray$",
    )
]

IGNORE_TRAILING_RE = re.compile(
    r",?\s*(to taste|as needed|for serving|for garnish|divided|optional|for frying|"
    r"plus more|plus more to taste|for greasing|for dusting|if needed)\s*$",
    re.IGNORECASE,
)

# Recipe type/cuisine inference. Ordered specific -> general; first hit wins.
# Matching normalizes hyphens to spaces, so "banh-mi" matches "banh mi".
CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("bbq", ["bbq", "barbecue", "barbeque", "baby back rib", "ribs", "brisket", "pulled pork"]),
    ("mexican", ["taco", "burrito", "enchilada", "quesadilla", "fajita", "nacho", "salsa verde", "carnitas", "al pastor", "santa fe", "taqueria", "chilaquiles"]),
    ("dessert", ["cake", "cookie", "brownie", "muffin", "donut", "doughnut", "tres leches", "frosting", "cheesecake"]),
    ("breakfast", ["pancake", "omelet", "omelette", "waffle", "scrambled egg", "breakfast", "french toast", "eggs & toast", "eggs and toast", "avocado toast", "oatmeal", "malt o meal", "granola", "overnight oats"]),
    ("bread", ["naan", "bagel", "scone", "cinnamon roll", "levain", "baguette", "dinner roll", "monkey bread", "banana bread", "garlic bread", "lembas", "bread"]),
    ("pizza", ["pizza", "flatbread", "calzone"]),
    ("sandwich", ["sandwich", "sandwhich", "burger", "slider", "hero", "pita", "wrap", "philly", "cheesesteak", "hot dog", "brat", "pretzel dog", "french dip", "sub "]),
    ("asian", ["stir fry", "chow mein", "fried rice", "ramen", "bulgogi", "teriyaki", "hoisin", "moo shu", "banh mi", "yakisoba", "lo mein", "pad thai", "kung pao", "orange chicken", "gochujang", "soy sauce", "mongolian", "katsu", "potsticker", "egg roll", "spring roll", "sesame soy"]),
    ("soup", ["soup", "stew", "chowder", "bisque", "chili", "bouillabaisse", "bouillon"]),
    ("pasta", ["pasta", "spaghetti", "rigatoni", "penne", "lasagna", "alfredo", "mac and cheese", "mac & cheese", "manicotti", "ravioli", "raviolli", "bolognese", "fettuccine", "linguine", "gnocchi", "mizithra", "carbonara", "rosa", "noodle"]),
    ("seafood", ["shrimp", "prawn", "fish", "salmon", "tilapia", "crab", "mussel", "muscle", "scampi", "seafood", "gambas", "tuna", "cod", "scallop"]),
    ("rice", ["risotto", "pilaf", "arroz", "aroz", "paella", "rice"]),
    ("salad", ["salad", "slaw"]),
    ("drink", ["smoothie", "protein shake", "protein powder", "cocktail", "beer", "wine", "coffee", "latte", "margarita", "mixed drink"]),
    ("chicken", ["chicken", "wings"]),
    ("beef", ["steak", "beef", "bison", "meatloaf", "meatball", "meatloves", "pot roast"]),
    ("pork", ["pork", "sausage", "bacon"]),
]

FOLDER_DEFAULT_CATEGORY = {
    "Baking": "bread",
    "Breakfasts": "breakfast",
    "Drinks": "drink",
    "Snacks": "snack",
    "Sauces": "sauce",
    "Seasonings": "seasoning",
    "Alcohol": "drink",
}

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
NUMBERED_STEP_RE = re.compile(r"^\s*\d+[.)]\s+(.*)$")
LIST_ITEM_RE = re.compile(r"^\s*[-*+]\s+(.*)$")
TAGS_RE = re.compile(r"((?:\s+#[\w/-]+)+)\s*$")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(])")


def compress_blank_lines(lines: list[str]) -> list[str]:
    out: list[str] = []
    blank = False
    for line in lines:
        stripped = line.replace("\xa0", " ").rstrip()
        if not stripped:
            if not blank and out:
                out.append("")
                blank = True
            continue
        blank = False
        out.append(stripped)
    while out and not out[-1]:
        out.pop()
    return out


def strip_markdown_links(text: str) -> str:
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)


def section_is_ingredient_list(lines: list[str]) -> bool:
    non_empty = [l for l in lines if l.strip()]
    if not non_empty:
        return False
    return all(strip_list_markers(l) for l in non_empty)


def normalize_extra_section(lines: list[str]) -> list[str]:
    if section_is_ingredient_list(lines):
        normalized = [
            normalize_ingredient_line(line)
            for line in lines
            if strip_list_markers(line)
        ]
        return [line for line in normalized if line]
    return compress_blank_lines(lines)


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    block = text[3:end].strip("\n")
    body = text[end + 4 :].lstrip("\n")
    fm: dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fm[key.strip()] = value.strip()
    return fm, body


def split_sections(body: str) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    current_title = ""
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_title, current_lines
        if current_title or current_lines:
            sections.append((current_title, current_lines))
        current_title = ""
        current_lines = []

    for raw in body.splitlines():
        heading = HEADING_RE.match(raw.strip())
        if heading:
            flush()
            current_title = heading.group(2).strip()
            continue
        current_lines.append(raw)
    flush()
    return sections


def canonical_key(key: str) -> str:
    return key.strip().lower().replace(" ", "").replace("_", "")


def fm_lookup(fm: dict[str, str], *names: str) -> str:
    lowered = {canonical_key(k): v for k, v in fm.items()}
    for name in names:
        value = lowered.get(canonical_key(name), "")
        if value:
            return value
    return ""


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"true", "yes", "1", "on"}


def parse_number(value: str) -> str:
    if not value:
        return ""
    match = re.search(r"-?\d+(?:\.\d+)?", value)
    return match.group(0) if match else ""


def parse_minutes(value: str) -> str:
    if not value:
        return ""
    hours = re.search(r"(\d+(?:\.\d+)?)\s*(?:h|hr|hrs|hour|hours)\b", value, re.I)
    mins = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:m|min|mins|minute|minutes)\b", value, re.I
    )
    total = 0.0
    matched = False
    if hours:
        total += float(hours.group(1)) * 60
        matched = True
    if mins:
        total += float(mins.group(1))
        matched = True
    if matched:
        return str(int(round(total)))
    return parse_number(value)


def title_case_word(word: str) -> str:
    if not word:
        return word
    if word.isupper() and len(word) <= 4:
        return word
    parts = word.split("-")
    return "-".join(p[:1].upper() + p[1:] if p else p for p in parts)


def title_case_name(text: str) -> str:
    words = text.split()
    out: list[str] = []
    for i, word in enumerate(words):
        match = re.match(r"^([(\[]*)(.*?)([)\],.]*)$", word)
        if not match:
            out.append(word)
            continue
        prefix, core, suffix = match.groups()
        if i > 0 and core.lower() in SMALL_WORDS:
            cased = core.lower()
        else:
            cased = title_case_word(core)
        out.append(prefix + cased + suffix)
    return " ".join(out)


def extract_tags(text: str) -> tuple[str, list[str]]:
    match = TAGS_RE.search(text)
    if not match:
        return text.strip(), []
    tags = [t.lstrip("#") for t in match.group(1).split() if t.startswith("#")]
    cleaned = text[: match.start()].strip()
    return cleaned, tags


def strip_list_markers(line: str) -> str:
    text = line.strip()
    while True:
        prev = text
        text = re.sub(r"^\s*[-*+]\s+", "", text)
        text = re.sub(r"^\[.\]\s+", "", text)
        text = re.sub(r"^\d+[.)]\s+", "", text)
        text = text.strip()
        if text == prev:
            break
    return text


def normalize_unit(raw: str) -> str:
    key = raw.strip().lower()
    return UNIT_CANON.get(key, key)


def parse_qty_unit_name(body: str) -> tuple[str, str, str]:
    body = body.strip()
    qty_match = re.match(rf"^({QUANTITY_PATTERN})\s+", body, re.I)
    if not qty_match:
        return "", "", body
    qty = qty_match.group(1).strip()
    rest = body[qty_match.end() :].strip()
    for unit_key in sorted({k.lower() for k in UNIT_CANON}, key=len, reverse=True):
        unit_match = re.match(rf"^{re.escape(unit_key)}\b\s*", rest, re.I)
        if unit_match:
            unit = UNIT_CANON[unit_key.lower()]
            name = rest[unit_match.end() :].strip()
            return qty, unit, name
    return qty, "", rest


def should_ignore_ingredient(name: str) -> bool:
    cleaned = name.strip().lower()
    cleaned = re.sub(r"\s*\([^)]*\)\s*", " ", cleaned).strip()
    prev = ""
    while cleaned != prev:
        prev = cleaned
        cleaned = IGNORE_TRAILING_RE.sub("", cleaned).strip()
    cleaned = cleaned.strip(" ,.")
    return any(pat.match(cleaned) for pat in IGNORE_INGREDIENT_PATTERNS)


def with_ignore_tag(name: str, tags: list[str]) -> list[str]:
    if not should_ignore_ingredient(name):
        return tags
    if any(t.lower().replace("-", "").replace("_", "") == "ignoreingredient" for t in tags):
        return tags
    return tags + ["IgnoreIngredient"]


def normalize_ingredient_line(line: str) -> str:
    body = strip_list_markers(line)
    if not body:
        return ""
    body = body.replace("\xa0", " ")
    body = re.sub(r"[▢□☐]", "", body).strip()
    body = strip_markdown_links(body)
    body, tags = extract_tags(body)
    qty, unit, name = parse_qty_unit_name(body)
    if not qty and not unit:
        tags = with_ignore_tag(body, tags)
        return f"- {title_case_name(body)}" + ("".join(f" #{t}" for t in tags))

    tags = with_ignore_tag(name, tags)
    parts = [p for p in [qty, unit, title_case_name(name)] if p]
    formatted = "- " + " ".join(parts)
    if tags:
        formatted += "".join(f" #{t}" for t in tags)
    return formatted


def split_instruction_chunks(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    for bullet_part in re.split(r"\s*•\s*", text):
        part = bullet_part.strip()
        if not part:
            continue
        if len(part) > 160 and SENTENCE_SPLIT_RE.search(part):
            chunks.extend(p.strip() for p in SENTENCE_SPLIT_RE.split(part) if p.strip())
        else:
            chunks.append(part)
    return chunks


def normalize_instruction_lines(lines: list[str]) -> list[str]:
    steps: list[str] = []
    for line in lines:
        numbered = NUMBERED_STEP_RE.match(line)
        if numbered:
            steps.extend(split_instruction_chunks(numbered.group(1)))
            continue
        stripped = line.strip()
        if stripped:
            steps.extend(split_instruction_chunks(stripped))
    return [f"{i}. {step}" for i, step in enumerate(steps, start=1)]


def is_placeholder_line(text: str) -> bool:
    cleaned = strip_list_markers(text).strip().lower()
    cleaned = TAGS_RE.sub("", cleaned).strip()
    return cleaned in {"", "test", "tbd", "todo"}


def is_stub(ingredient_lines: list[str], instruction_lines: list[str]) -> bool:
    real_ing = [l for l in ingredient_lines if l.strip() and not is_placeholder_line(l)]
    real_inst = [l for l in instruction_lines if l.strip() and not is_placeholder_line(l)]
    if not real_ing or not real_inst:
        return True
    return False


def clean_scalar(value: str) -> str:
    return value.strip().strip('"').strip("'")


def yaml_scalar(value: str) -> str:
    cleaned = clean_scalar(value)
    if not cleaned:
        return ""
    if "://" in cleaned or re.search(r'[:,"]', cleaned) or " " in cleaned:
        return f'"{cleaned}"'
    return cleaned


def _norm_for_match(text: str) -> str:
    return re.sub(r"[-–—]", " ", text.lower())


def infer_category(name: str, folder: str, body: str) -> str:
    title = _norm_for_match(name)
    full = _norm_for_match(name + "\n" + body)
    for category, keywords in CATEGORY_RULES:
        if any(kw in title for kw in keywords):
            return category
    for category, keywords in CATEGORY_RULES:
        if any(kw in full for kw in keywords):
            return category
    return FOLDER_DEFAULT_CATEGORY.get(folder, "other")


def build_frontmatter(fm: dict[str, str], category: str) -> str:
    cook = fm_lookup(fm, "Cook")
    cook_val = "true" if parse_bool(cook) else "false"
    prep = parse_minutes(fm_lookup(fm, "Prep Time", "prepTime", "prep"))
    cook_time = parse_minutes(fm_lookup(fm, "Cook Time", "cookTime"))
    total = parse_minutes(fm_lookup(fm, "Total Time", "totalTime"))
    if not total and prep and cook_time:
        total = str(int(prep) + int(cook_time))

    servings = parse_number(fm_lookup(fm, "Servings", "Yield", "servings"))
    image = clean_scalar(fm_lookup(fm, "Image", "image"))
    source = clean_scalar(fm_lookup(fm, "Source", "source"))

    favorite = "true" if parse_bool(fm_lookup(fm, "favorite", "Favorite")) else "false"
    last_made = fm_lookup(fm, "lastMade", "LastMade")
    cooked_count = parse_number(fm_lookup(fm, "cookedCount", "CookedCount")) or "0"
    multiplier = parse_number(fm_lookup(fm, "multiplier", "Multiplier")) or "1"

    lines = [
        "---",
        "type: recipe",
        f"category: {category}" if category else "category:",
        f"source: {yaml_scalar(source)}" if source else "source:",
        f"image: {yaml_scalar(image)}" if image else "image:",
        f"Cook: {cook_val}",
        f"multiplier: {multiplier}",
        f"servings: {servings}" if servings else "servings:",
        f"calories: {parse_number(fm_lookup(fm, 'Calories', 'calories'))}"
        if parse_number(fm_lookup(fm, "Calories", "calories"))
        else "calories:",
        f"protein: {parse_number(fm_lookup(fm, 'Protein', 'protein'))}"
        if parse_number(fm_lookup(fm, "Protein", "protein"))
        else "protein:",
        f"fat: {parse_number(fm_lookup(fm, 'Fats', 'Fat', 'fat'))}"
        if parse_number(fm_lookup(fm, "Fats", "Fat", "fat"))
        else "fat:",
        f"carbs: {parse_number(fm_lookup(fm, 'Carbs', 'carbs'))}"
        if parse_number(fm_lookup(fm, "Carbs", "carbs"))
        else "carbs:",
        "diet: []",
        "allergens: []",
        f"prepTime: {prep}" if prep else "prepTime:",
        f"cookTime: {cook_time}" if cook_time else "cookTime:",
        f"totalTime: {total}" if total else "totalTime:",
        f"favorite: {favorite}",
        f"lastMade: {last_made}" if last_made else "lastMade:",
        f"cookedCount: {cooked_count}",
        "---",
    ]
    return "\n".join(lines)


INSTRUCTION_TITLES = {"instructions", "directions", "method", "steps"}
INGREDIENT_SUBSECTION_TITLES = {
    "rub",
    "ribs",
    "sauce",
    "marinade",
    "glaze",
    "topping",
    "filling",
    "dressing",
    "batter",
    "dough",
    "assembly",
}


def classify_sections(
    sections: list[tuple[str, list[str]]],
) -> tuple[list[str], list[str], list[str], list[tuple[str, list[str]]]]:
    intro_lines: list[str] = []
    ingredient_src: list[str] = []
    instruction_src: list[str] = []
    out_sections: list[tuple[str, list[str]]] = []

    if sections and not sections[0][0]:
        intro_lines = [line for line in sections[0][1] if line.strip()]
        sections = sections[1:]

    index = 0
    while index < len(sections):
        title, lines = sections[index]
        norm_title = title.strip().lower().rstrip(":")
        if norm_title == "ingredients":
            ingredient_src.extend(lines)
            index += 1
            while index < len(sections):
                next_title, next_lines = sections[index]
                next_norm = next_title.strip().lower().rstrip(":")
                if next_norm in INSTRUCTION_TITLES or next_norm == "notes":
                    break
                if next_norm in INGREDIENT_SUBSECTION_TITLES or section_is_ingredient_list(
                    next_lines
                ):
                    ingredient_src.extend(next_lines)
                    index += 1
                    continue
                break
            continue
        if norm_title in INSTRUCTION_TITLES:
            instruction_src.extend(lines)
            index += 1
            continue
        out_sections.append((title, lines))
        index += 1

    return intro_lines, ingredient_src, instruction_src, out_sections


def normalize_body(body: str) -> tuple[str, bool]:
    sections = split_sections(body)
    if not sections and body.strip():
        sections = [("", body.splitlines())]

    intro_lines, ingredient_src, instruction_src, out_sections = classify_sections(
        sections
    )

    if is_stub(ingredient_src, instruction_src):
        return body, True

    normalized_ingredients = [
        normalize_ingredient_line(line)
        for line in ingredient_src
        if strip_list_markers(line)
    ]
    normalized_ingredients = [l for l in normalized_ingredients if l]
    normalized_instructions = normalize_instruction_lines(instruction_src)

    parts: list[str] = []
    if intro_lines:
        parts.extend(intro_lines)
        parts.append("")

    parts.extend(["## Ingredients", ""])
    parts.extend(normalized_ingredients or ["-"])
    parts.append("")
    parts.extend(["## Instructions", ""])
    parts.extend(normalized_instructions or ["1."])

    for title, lines in out_sections:
        title_clean = title.rstrip(":").strip()
        normalized = normalize_extra_section(lines)
        if not normalized:
            continue
        parts.append("")
        parts.append(f"## {title_clean}")
        parts.append("")
        parts.extend(normalized)

    return "\n".join(compress_blank_lines(parts)).rstrip() + "\n", False


def normalize_file(path: Path, reinfer: bool = False) -> tuple[str | None, bool]:
    text = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    new_body, skipped = normalize_body(body)
    if skipped:
        return None, True
    existing_category = clean_scalar(fm_lookup(fm, "category"))
    folder = path.parent.name
    if reinfer or not existing_category:
        category = infer_category(path.stem, folder, body)
    else:
        category = existing_category
    return build_frontmatter(fm, category) + "\n\n" + new_body, False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reinfer", action="store_true", help="Recompute category even if already set")
    parser.add_argument("--paths", nargs="*", default=[])
    args = parser.parse_args()

    paths = [Path(p) for p in args.paths] if args.paths else sorted(ROOT.rglob("*.md"))
    paths = [p for p in paths if ".git" not in p.parts and p.name != "README.md"]

    changed = 0
    skipped: list[str] = []

    for path in paths:
        result, was_skipped = normalize_file(path, reinfer=args.reinfer)
        if was_skipped:
            skipped.append(str(path.relative_to(ROOT)))
            continue
        if result is None:
            skipped.append(str(path.relative_to(ROOT)))
            continue
        rel = path.relative_to(ROOT)
        if args.dry_run:
            print(f"WOULD UPDATE {rel}")
            changed += 1
            continue
        if path.read_text(encoding="utf-8") != result:
            path.write_text(result, encoding="utf-8")
            print(f"UPDATED {rel}")
            changed += 1

    print(f"\nDone. Changed: {changed}, skipped (stub/empty): {len(skipped)}")
    if skipped:
        print("\nSkipped files:")
        for item in skipped:
            print(f"  - {item}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
