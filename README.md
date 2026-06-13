# Cooking

My personal, ever-growing collection of recipes — everything from weeknight
dinners and breakfasts to baking projects, sauces, and drinks. It's all here in
plain Markdown so it stays readable forever, works in any editor, and plays
nicely with version control.

**Free to use.** Cook from it, fork it, copy a recipe into your own vault, or
borrow the whole thing. No attribution required. Where a recipe came from an
external source, that page is linked in the note's `source` frontmatter.

## How it's organized

Recipes are grouped into folders by meal/type:

```
Baking/        Breakfasts/    Dinners/      Drinks/
Lunches/       Sauces/        Seasonings/   Snacks/
```

Every recipe note shares the same normalized frontmatter and body shape, which
is what makes the whole vault scriptable and tool-friendly:

```markdown
---
type: recipe
category: pasta
source: "https://example.com/the-original-recipe"
image: "https://example.com/photo.jpg"
Cook: false
multiplier: 1
servings: 4
calories: 540
protein: 26
fat: 27
carbs: 44
diet: []
allergens: []
prepTime: 15
cookTime: 25
totalTime: 40
favorite: false
lastMade:
cookedCount: 0
---

## Ingredients

- 1 lb Ground Beef #Meat
- 2 cup Marinara #Pantry
- 1 tsp Salt #Seasoning #IgnoreIngredient

## Instructions

1. Brown the beef.
2. Add the marinara and simmer.
```

A few conventions worth knowing:

- **`category`** is a single cuisine/type tag (`pasta`, `mexican`, `bbq`,
  `dessert`, `soup`, ...) used to slice the library into views.
- **Ingredient tags** like `#Produce`, `#Dairy`, `#Meat`, `#Pantry` group items
  for shopping.
- **`#IgnoreIngredient`** marks pantry staples (water, salt, pepper, oil, ...)
  that should never land on a grocery list.
- Macro values (`calories`, `protein`, `fat`, `carbs`) are kept on notes
  wherever they're known; unknown fields are intentionally left blank.

The included `Recipes.base` is an [Obsidian Bases](https://help.obsidian.md/bases)
view for browsing and filtering the collection by category, favorites, and more.

## Works great with Pantry

These recipes are designed to pair with **Pantry**, my Obsidian plugin that
turns recipe notes into a consolidated, category-grouped grocery list and
renders each note as an interactive cooking card. Because every recipe here
already uses Pantry's canonical frontmatter and ingredient format, the whole
vault drops in with zero conversion:

- **Recipes as the source of truth.** Flag any note for the week and Pantry adds
  its ingredients to the list.
- **Automatic consolidation.** Shared ingredients merge across recipes
  (`1 cup milk` + `2 cups milk` → `3 cup milk`).
- **Smart grouping.** Items are grouped by the `#`-category tags so the list
  matches your store's layout.
- **`#IgnoreIngredient` aware.** Staples tagged here are skipped automatically.
- **Recipe view.** `type: recipe` notes render with a hero image, scaled
  ingredients (via `multiplier`/`servings`), nutrition, and numbered steps.
- **Meal planner, last-made tracking, favorites, allergens, and a cook-count
  leaderboard** all read straight from this frontmatter.

Pantry can also **import new recipes from a URL or pasted text** into this exact
shape, so growing the collection stays consistent.

> Don't use Pantry? No problem — these are still just clean Markdown files you
> can read or render anywhere.

## Contributing — PR your own recipes!

I'd love for this list to grow, so **pull requests with your own recipes are
very welcome.** To keep everything consistent and Pantry-compatible:

1. Add your `.md` file to the most fitting folder (or propose a new one).
2. Match the frontmatter shape above — at minimum set `type: recipe` and a
   `category`. Fill in macros and times if you have them; leave unknowns blank.
3. Use `## Ingredients` and `## Instructions` sections. Tag ingredients by group
   (`#Produce`, `#Dairy`, ...) and add `#IgnoreIngredient` to pantry staples.
4. If the recipe is adapted from somewhere, put the original link in `source`.
5. Open a PR. Tweaks and improvements to existing recipes are great too.

Don't stress about perfect formatting — open the PR and we can polish it
together.

## License

Shared freely for personal use. Take what's useful and happy cooking!
