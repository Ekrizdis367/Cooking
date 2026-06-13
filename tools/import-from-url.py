#!/usr/bin/env python3
"""Fetch approved recipe URLs, extract schema.org Recipe JSON-LD, and write
raw recipe notes (old-style frontmatter + ## Ingredients / ## Instructions).

Run normalize-recipes.py --reinfer afterwards to finalize formatting.
"""

from __future__ import annotations

import html
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# relative path -> source URL. None target means "rename handled below".
IMPORTS: list[tuple[str, str]] = [
    ("Baking/Irish Soda Bread.md", "https://sallysbakingaddiction.com/grandmas-irish-soda-bread/"),
    ("Breakfasts/Breakfast Burritos.md", "https://www.wellplated.com/breakfast-burrito-recipe/"),
    ("Breakfasts/Farmer's Breakfast.md", "https://www.tasteofhome.com/recipes/farmers-breakfast/"),
    ("Breakfasts/Pancakes.md", "https://sallysbakingaddiction.com/buttermilk-pancakes-recipe/"),
    ("Dinners/Cajun Shrimp Pasta.md", "https://preppykitchen.com/cajun-shrimp-pasta/"),
    ("Dinners/Chicken Parmesan.md", "https://www.allrecipes.com/recipe/223042/chicken-parmesan/"),
    ("Dinners/Chicken Sandwhiches.md", "https://www.tasteofhome.com/recipes/crispy-chicken-sandwich-recipe/"),
    ("Dinners/Crispy Honey Shrimp.md", "https://damndelicious.net/2013/07/16/honey-walnut-shrimp/"),
    ("Dinners/Fried Rice.md", "https://thedefineddish.com/simple-chicken-fried-rice/"),
    ("Dinners/Garlic Butter Shrimp Pasta.md", "https://damndelicious.net/2015/03/13/garlic-butter-shrimp-pasta/"),
    ("Dinners/Homemade Pizza.md", "https://www.simplyrecipes.com/recipes/homemade_pizza/"),
    ("Dinners/Marry Me Shrimp Pasta.md", "https://www.foodiecrush.com/marry-me-shrimp-pasta/"),
    ("Dinners/Mongolian Noodles.md", "https://izzycooking.com/mongolian-bbq/"),
    ("Dinners/Nachos.md", "https://www.theseasonedmom.com/homemade-nachos/"),
    ("Dinners/Orange Chicken.md", "https://www.tasteofhome.com/recipes/copycat-panda-express-orange-chicken/"),
    ("Dinners/Ribs.md", "https://cookingformysoul.com/oven-baked-ribs/"),
    ("Dinners/Shrimp Alfredo .md", "https://www.allrecipes.com/recipe/23979/shrimp-fettuccine-alfredo/"),
    ("Dinners/Shrimp Scampi.md", "https://natashaskitchen.com/shrimp-scampi-recipe/"),
    ("Dinners/Tacos.md", "https://www.allrecipes.com/recipe/265382/authentic-baja-mexican-street-tacos-carne-asada/"),
    ("Lunches/Gambas Al Ajillo.md", "https://www.themediterraneandish.com/gambas-al-ajillo-spanish-shrimp/"),
    ("Lunches/Mussels.md", "https://www.recipetineats.com/how-to-cook-mussels/"),
    ("Sauces/Spanish Alioli.md", "https://spanishsabores.com/easy-spanish-alioli-recipe-homemade-garlic-mayonnaise/"),
]

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    return raw.decode("utf-8", errors="replace")


def iter_jsonld(html_text: str):
    pattern = re.compile(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        re.DOTALL | re.IGNORECASE,
    )
    for m in pattern.finditer(html_text):
        block = m.group(1).strip()
        try:
            yield json.loads(block)
        except json.JSONDecodeError:
            continue


def _is_recipe(node) -> bool:
    if not isinstance(node, dict):
        return False
    t = node.get("@type")
    if isinstance(t, list):
        return any(str(x).lower() == "recipe" for x in t)
    return str(t).lower() == "recipe"


def find_recipe(data):
    stack = [data]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            if _is_recipe(node):
                return node
            if "@graph" in node:
                stack.extend(node["@graph"])
            stack.extend(v for v in node.values() if isinstance(v, (dict, list)))
        elif isinstance(node, list):
            stack.extend(node)
    return None


def clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", "", value)
    value = value.replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()


def extract_image(node) -> str:
    img = node.get("image")
    if isinstance(img, str):
        return img
    if isinstance(img, dict):
        return img.get("url", "")
    if isinstance(img, list) and img:
        first = img[0]
        if isinstance(first, str):
            return first
        if isinstance(first, dict):
            return first.get("url", "")
    return ""


def extract_yield(node) -> str:
    y = node.get("recipeYield")
    if isinstance(y, list):
        y = y[0] if y else ""
    m = re.search(r"\d+", str(y))
    return m.group(0) if m else ""


def iso_to_minutes(value) -> str:
    if not value or not isinstance(value, str):
        return ""
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?", value.strip())
    if not m:
        return ""
    days, hours, mins = (int(x) if x else 0 for x in m.groups())
    total = days * 1440 + hours * 60 + mins
    return str(total) if total else ""


def nutrition_value(nutrition, *keys) -> str:
    if not isinstance(nutrition, dict):
        return ""
    for key in keys:
        val = nutrition.get(key)
        if val:
            m = re.search(r"\d+(?:\.\d+)?", str(val))
            if m:
                return str(int(round(float(m.group(0)))))
    return ""


def flatten_instructions(instr) -> list[str]:
    steps: list[str] = []

    def handle(item):
        if isinstance(item, str):
            text = clean_text(item)
            if text:
                steps.append(text)
        elif isinstance(item, dict):
            itype = str(item.get("@type", "")).lower()
            if itype == "howtosection":
                for sub in item.get("itemListElement", []):
                    handle(sub)
            else:
                text = clean_text(item.get("text") or item.get("name") or "")
                if text:
                    steps.append(text)
        elif isinstance(item, list):
            for sub in item:
                handle(sub)

    handle(instr)
    return steps


def instructions_from_html(html_text: str) -> list[str]:
    """Fallback: pull steps from common recipe-card markup (WPRM, Tasty)."""
    steps: list[str] = []
    for m in re.finditer(
        r'<(?:div|li)[^>]*class="[^"]*(?:wprm-recipe-instruction-text|tasty-recipes-instructions?[^"]*|mv-create-instructions[^"]*)[^"]*"[^>]*>(.*?)</(?:div|li)>',
        html_text,
        re.DOTALL | re.IGNORECASE,
    ):
        text = clean_text(m.group(1))
        if text:
            steps.append(text)
    if steps:
        return steps
    # Generic: list items inside an element whose class mentions "instruction".
    block = re.search(
        r'(<(?:ol|ul)[^>]*class="[^"]*instruction[^"]*"[^>]*>.*?</(?:ol|ul)>)',
        html_text,
        re.DOTALL | re.IGNORECASE,
    )
    if block:
        for li in re.findall(r"<li[^>]*>(.*?)</li>", block.group(1), re.DOTALL | re.IGNORECASE):
            text = clean_text(li)
            if text:
                steps.append(text)
    return steps


def build_note(node: str, url: str, page: str = "") -> str:
    ingredients = [clean_text(i) for i in node.get("recipeIngredient", []) if clean_text(i)]
    steps = flatten_instructions(node.get("recipeInstructions"))
    if not steps and page:
        steps = instructions_from_html(page)
    nutrition = node.get("nutrition", {})

    fm = ["---"]
    image = extract_image(node)
    if image:
        fm.append(f"Image: {image}")
    fm.append(f"Source: {url}")
    yld = extract_yield(node)
    if yld:
        fm.append(f"Servings: {yld}")
    for label, keys in (
        ("Calories", ("calories",)),
        ("Protein", ("proteinContent",)),
        ("Fats", ("fatContent",)),
        ("Carbs", ("carbohydrateContent",)),
    ):
        v = nutrition_value(nutrition, *keys)
        if v:
            fm.append(f"{label}: {v}")
    prep = iso_to_minutes(node.get("prepTime"))
    cook = iso_to_minutes(node.get("cookTime"))
    total = iso_to_minutes(node.get("totalTime"))
    if prep:
        fm.append(f"Prep Time: {prep}")
    if cook:
        fm.append(f"Cook Time: {cook}")
    if total:
        fm.append(f"Total Time: {total}")
    fm.append("---")

    body = ["", "## Ingredients", ""]
    body += [f"- {i}" for i in ingredients] or ["-"]
    body += ["", "## Instructions", ""]
    body += [f"{idx}. {s}" for idx, s in enumerate(steps, 1)] or ["1."]

    return "\n".join(fm + body) + "\n"


def main() -> int:
    ok, failed = [], []
    for rel, url in IMPORTS:
        try:
            page = fetch(url)
            recipe = find_recipe(list(iter_jsonld(page)))
            if not recipe:
                failed.append((rel, url, "no Recipe JSON-LD"))
                continue
            note = build_note(recipe, url, page)
            ni = note.count("\n- ")
            ns = len(re.findall(r"^\d+\. ", note, re.MULTILINE))
            if ni == 0 or ns == 0:
                failed.append((rel, url, f"empty (ingredients={ni}, steps={ns})"))
                continue
            (ROOT / rel).write_text(note, encoding="utf-8")
            ok.append((rel, ni, ns))
        except Exception as exc:  # noqa: BLE001
            failed.append((rel, url, str(exc)[:80]))

    print(f"Imported: {len(ok)}")
    for rel, ni, ns in ok:
        print(f"  OK  {rel}  ({ni} ingredients, {ns} steps)")
    if failed:
        print(f"\nFailed: {len(failed)}")
        for rel, url, why in failed:
            print(f"  FAIL {rel}  [{why}]  {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
