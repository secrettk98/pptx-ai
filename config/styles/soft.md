# Style — Soft
# Loaded when: classifier style_mode = "soft".
# Covers: visual baseline for the ~80% default case (marketing, startup,
#         product, general business).

## TL;DR (read first)

- Rounded corners on cards, image containers, accent blocks. One radius
  family across the deck.
- No shadows anywhere. Borders only when there is no fill.
- All lines and borders: 0.75pt thickness.
- Typography hierarchy fixed (see §3); body min 12pt, caption min 10pt.
- Icons: outlined OR filled, AI's choice — but uniform across the whole
  deck (core_rules §9, §12).
- Color tokens fixed (see §4): white slide bg, #F8F8F8 cards, black body
  text, gray caption, brand accent (+ optional secondary set).

## 1. Corner Radius

- One radius family across the entire presentation.
- Recommended baseline: 12px for cards and large containers.
  Acceptable range: 8-16px. Pick once per deck, reuse everywhere.
- Smaller decorative elements (icon backplates, small chips) may use
  a proportionally smaller radius (e.g. 6-8px) but visually consistent
  with the main radius.
- NEVER mix rounded and sharp on the same deck (core_rules §9).

## 2. Icons

- Style: outlined OR filled — AI chooses, but the SAME style across the
  whole deck.
- Stroke width for outlined icons: 1.5-2px, fixed once per deck.
- Size baseline: 24-32px inside cards; larger when icon is the
  centerpiece of a block (core_rules §12).
- Icon backplate (if used): brand accent color, with the same radius
  family.

## 3. Typography

Font family: ONE font for the whole presentation, picked from:

    - Google Sans       (balanced, modern)
    - Century Gothic    (wider, geometric, more air)
    - Roboto            (compact, fits dense slides)

AI picks based on content density: more text → Roboto;
less text / more air → Century Gothic; balanced → Google Sans.

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
    - 10pt is allowed ONLY for caption / footnote / copyright /
      auxiliary text inside dense cards. Never for primary body.
    - No first-line indent.
    - Vertical paragraph spacing 8-12px.

## 4. Color Tokens

    - Slide background          white (#FFFFFF)
    - Card / backdrop fill      #F8F8F8
    - Primary text              black (#000000 or near-black)
    - Auxiliary text            gray  (caption, footnote, copyright)
    - Accent (brand)            user-provided OR extracted from client
                                logo / source slides
    - Secondary accent set      allowed when needed (see below)

Accent palette rules:

    - Single accent by default.
    - Charts / diagrams with 3+ segments → use a gradation of the
      brand accent (lighter/darker shades of the same hue).
    - Charts / diagrams with 3-4 categorical segments may use:
      brand accent + gray + black + one supplementary color.
    - Do NOT introduce colors outside this set.

## 5. Lines, Borders, Dividers

- All lines and borders: 0.75pt thickness.
- Borders are used ONLY when the element has no fill.
  Filled cards (#F8F8F8) → no border.
- Dividers (thin lines between sections, under headings) allowed,
  same 0.75pt, in gray or brand accent.

## 6. Shadows

- NONE. No drop shadows on cards, images, icons, or any element.

## 7. Images & Photos

- Photo containers use the same radius family as cards.
- No drop shadows. No glow. No filters beyond color correction.
- Borders only if the photo sits on white with no card backdrop AND
  needs visual separation — then 0.75pt gray.

## Defaults Summary

    - Radius:        ~12px (range 8-16), uniform across deck
    - Icons:         AI's choice, uniform style + stroke
    - Font:          one of Google Sans / Century Gothic / Roboto
    - Sizes:         24 / 14-16 / 12 / 10 (heading / block / body / aux)
    - Colors:        white bg, #F8F8F8 cards, black/gray text, brand accent
    - Lines:         0.75pt, borders only when no fill
    - Shadows:       none