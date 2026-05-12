# Style — Strict
# Loaded when: classifier style_mode = "strict".
# Covers: visual baseline for the ~20% formal case (government, official
#         reporting, regulated corporate).

## TL;DR (read first)

- Sharp corners everywhere. Radius = 0 on all cards, images, blocks.
- No shadows anywhere. Borders only when there is no fill.
- All lines and borders: 0.75pt thickness.
- Typography hierarchy same as soft (see §3).
- Icons: outlined OR filled, AI's choice — but uniform across the deck
  (core_rules §9, §12).
- Color tokens same as soft (see §4): white bg, #F8F8F8 cards, black
  body, gray auxiliary, brand accent (+ optional secondary set).
- Visual restraint: minimal decoration, more reliance on typography
  and grid alignment than on color/shape accents.

## 1. Corner Radius

- ZERO. All cards, image containers, backplates, chips: sharp corners.
- NEVER mix sharp and rounded on the same deck (core_rules §9).

## 2. Icons

- Style: outlined OR filled — AI chooses, but the SAME style across the
  whole deck.
- Stroke width for outlined icons: 1.5-2px, fixed once per deck.
- Prefer simpler, geometric icons over playful or illustrative ones.
- Size baseline: 24-32px inside cards (core_rules §12).
- Icon backplate (if used): brand accent or gray, sharp corners.

## 3. Typography

Font family: ONE font for the whole presentation, picked from:

    - Google Sans       (balanced, modern)
    - Century Gothic    (wider, geometric, more air)
    - Roboto            (compact, fits dense formal reports)

AI picks based on content density (same logic as soft).

Size hierarchy (pt):

    - slide heading             24pt
    - slide subheading / kicker 12pt   (above or below slide heading)
    - block heading             14-16pt
    - body text                 12pt   (minimum, NEVER smaller for body)
    - caption / footnote /
      copyright / dense card
      auxiliary text            10pt   (minimum, ONLY for auxiliary roles)
    - large numbers (metrics)   AI decides by context, scaled to block

Rules:

    - Body text NEVER goes below 12pt (core_rules §14).
    - 10pt only for caption / footnote / copyright / auxiliary text.
    - No first-line indent.
    - Vertical paragraph spacing 8-12px.

## 4. Color Tokens

    - Slide background          white (#FFFFFF)
    - Card / backdrop fill      #F8F8F8
    - Primary text              black (#000000 or near-black)
    - Auxiliary text            gray
    - Accent (brand)            user-provided OR extracted from client
                                logo / source slides
    - Secondary accent set      allowed when needed (see below)

Accent palette rules:

    - Single accent by default. Use accent sparingly — strict mode
      relies more on typography and structure than on color emphasis.
    - Charts / diagrams with 3+ segments → gradation of brand accent.
    - Charts / diagrams with 3-4 categorical segments may use:
      brand accent + gray + black + one supplementary color.
    - Do NOT introduce colors outside this set.

## 5. Lines, Borders, Dividers

- All lines and borders: 0.75pt thickness.
- Borders are used ONLY when the element has no fill.
  Filled cards (#F8F8F8) → no border.
- Dividers (thin lines between sections, under headings) are MORE
  common in strict mode — they replace the visual emphasis that
  rounded shapes / accent fills provide in soft mode.

## 6. Shadows

- NONE. No drop shadows on any element.

## 7. Images & Photos

- Sharp corners. No radius.
- No drop shadows. No filters beyond color correction.
- 0.75pt gray border only if photo sits on white with no card backdrop
  AND needs visual separation.

## 8. Visual Restraint (mode-specific)

Strict mode prioritizes:

    - clean grid alignment over decorative emphasis
    - typographic hierarchy over color emphasis
    - thin dividers over filled accent blocks
    - more whitespace tolerance (still bounded by core_rules §6 anti-emptiness)

When in doubt between two equally valid layouts, pick the one with
fewer accent elements and stronger grid alignment.

## Defaults Summary

    - Radius:        0 everywhere
    - Icons:         AI's choice, uniform style + stroke, geometric preferred
    - Font:          one of Google Sans / Century Gothic / Roboto
    - Sizes:         24 / 14-16 / 12 / 10 (heading / block / body / aux)
    - Colors:        white bg, #F8F8F8 cards, black/gray text, brand accent
    - Lines:         0.75pt, borders only when no fill, dividers preferred
    - Shadows:       none
    - Tone:          restrained, typography-first