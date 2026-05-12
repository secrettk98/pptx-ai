# Card — Object Module
# Loaded when: classifier objects includes "card".
# Covers: a single card's anatomy, AND grids of multiple cards on a slide.

## TL;DR (read first)

- A card is a composite block built from optional slots: icon / number /
  heading / body / secondary text / image. Pick a slot configuration that
  fits the content; USE THE SAME CONFIGURATION for every card in the grid.
- Card orientation (vertical / horizontal) follows how body text reads best.
  All cards in one grid = SAME orientation (mixing only in edge cases).
- ALL cards on the slide = SAME height (within a row AND between rows).
- "Awkward" counts (5, 7, 10, 11) → asymmetric rows (e.g. 3+4).
  Card widths within a row are equal; row widths may differ between rows
  by content density.
- Up to 16 cards per slide is acceptable IF body ≥12pt AND each card has
  a visual element. Above 16 → split slide.
- Card content sticks to TOP (with padding). Never vertically centered.
- A card is NEVER just "a plate with text" — always include a visual element.

## Card Anatomy (slot-based)

Available slots:

    - icon
    - large number (metric)
    - heading (card-level, NOT slide heading)
    - body text (primary)
    - secondary text (smaller, gray, above or below body)
    - image / photo

Common configurations:

    - icon + heading + body
    - icon + number + heading + body
    - number + heading + secondary text
    - image (top) + heading + body (bottom)
    - icon + heading + body + secondary gray text

Rules for slot configuration:

    - Heading is RECOMMENDED. Skip only when clearly unnatural.
    - Icon is RECOMMENDED but not mandatory.
    - IF no icon → MUST include another visual element: divider line,
      accent color block, accent corner, large number.
      NEVER a flat plate with only text.
    - Sizes of icons and internal proportions: AI's judgment.
      Recommended baselines (from core_rules §13):
        padding 24px left/right, 16px icon→heading, 8px heading→body.

## Card Orientation

Vertical:    icon/number on top → heading → body below.
Horizontal:  icon/number on the left | heading + body on the right.

Choose orientation by how the body text reads best:

    - short labels / 1-2 lines       → horizontal usually reads cleaner
    - longer body / multi-line       → vertical usually reads cleaner
    - both work equally              → either is acceptable

ALL cards in one grid use the SAME orientation.
Mixing orientations in one grid = edge case only, when content forces it.

## Grid Selection (no fixed mapping)

There is NO default grid for a given card count. Selection is content-driven.

For each slide:

    STEP 1 → pick orientation (vertical / horizontal) by content shape.
    STEP 2 → arrange cards so that:
                - widths within a row are equal
                - all cards on the slide have equal HEIGHT
                  (within and between rows)
                - rows look balanced; no row half-empty
    STEP 3 → for "awkward" counts (5, 7, 10, 11, 13...) use asymmetric rows.
             Row widths may DIFFER between rows by content density:
               e.g. 7 cards as 3 + 4 → top row 3 wider cards,
                    bottom row 4 narrower cards.
             Card widths WITHIN a row remain equal.

Examples (illustrative, not prescriptive):

    3 cards    → row of 3 OR column of 3, by orientation
    4 cards    → 2×2 OR row of 4
    6 cards    → 3×2 OR row of 6 OR 2×3
    7 cards    → 3+4 asymmetric, OR accent pattern (see below)
    8 cards    → 4×2 OR 2×4
    9 cards    → 3×3
    10-12      → 4×3 / 3×4 with adjustments
    13-16      → dense grids, only if each card stays readable at ≥12pt

## Equal Height Across the Whole Slide

ALL cards on the slide MUST have equal height — within a row AND between rows.

If content per card is very uneven (one card has 3× the text of others):

    IF client_constraints.verbatim_text = true:
        OPTION A → stretch ALL cards to the tallest one's height
        OPTION B → extract the long card as an ACCENT card (see patterns below)

    IF text editing is allowed:
        → rephrase to equalize content length without losing meaning (preferred)

Card content alignment inside the card: TOP-aligned (with padding).
Never vertically center, never stretch internal gaps to fill height.

## Accent Card Patterns

Use when one card is semantically dominant (a generalizing item, a key metric,
or a primary subject) and should be visually emphasized.

Allowed accent patterns (closed list):

    PATTERN 1 — Tall right column:
      Regular cards in a grid on the left, one tall accent card on the right
      spanning the full slide height.
      Example: 7 items as 3 columns × 2 rows of regular cards + 1 tall accent.

    PATTERN 2 — Wide top banner:
      One accent card spanning full width on top, regular grid below.

    PATTERN 3 — Center accent:
      One accent card in the center, regular cards arranged around the perimeter.

    PATTERN 4 — Wide first card in a row:
      First card in a row is 2× the width of its siblings, same row, same height.

Accent card MUST share the same slot configuration family as regular cards
(don't introduce new slots), but MAY hold more content and uses larger
typographic emphasis.

When to use accent: classifier or content reading reveals a clearly
generalizing or dominant item. If all cards are equal in importance,
don't fabricate an accent.

## Cards in a Composition with Other Objects

Cards on the slide may share space with other objects (text, visual, chart,
table). Composition is governed by core_rules §4-§5 (spatial logic and
sub-schemas A/B/C/D), not by this module.

This module's rules — slot configuration, orientation uniformity, equal
height, accent patterns — apply to the cards themselves regardless of
what surrounds them on the slide.

## Density & Slide Split

    - ≤16 cards per slide is acceptable IF:
        - body font stays ≥12pt
        - each card has a visual element (no flat-plate cards)
        - cards remain visually "interesting", not crushed
    - >16 cards → split into 2+ slides in most cases.
    - Split is ALSO triggered earlier if content does not fit at ≥12pt.
    - Splitting requires client_constraints.allow_slide_split = true.
      If false → flag for manual review (per core_rules §17).

## Decision Tree

    Step 1: Count cards. >16?
              YES → plan a split. Group cards semantically across 2+ slides.
              NO  → continue.

    Step 2: Is one card semantically dominant?
              YES → choose an accent pattern (1-4 above).
              NO  → continue with a uniform grid.

    Step 3: Pick orientation by how body text reads best.
              All cards in the grid share this orientation.

    Step 4: Pick a grid arrangement that keeps:
              - equal width within each row
              - equal height across the entire slide
              - balanced rows (no row half-empty)
            For awkward counts → asymmetric rows (3+4, 2+3, etc).

    Step 5: Verify content fits at ≥12pt.
            If not → split or rephrase per client_constraints.

## Defaults Summary

    - Grid:           chosen by content, no fixed default per count.
    - Orientation:    by content readability; uniform within a grid.
    - Card height:    equal across the entire slide.
    - Card alignment: top, with padding.
    - Accent card:    only if a semantically dominant item exists.
    - Max per slide:  16 (split above).
    - Min body font:  12pt (core_rules §14, never overridden).