# Modules Map
# Defines which rule modules are loaded into the generator prompt
# based on classifier output.

## Always Loaded (Base Layer)

    core_rules.md  →  ALWAYS loaded

## Object-specific Modules

    objects includes "card"      →  card.md
    visual_subtype = "pattern"   →  patterns.md

No other object types need a dedicated module — heading, text, table, chart,
and the remaining visual subtypes are fully covered by core_rules.md.

For visual subtypes other than "pattern", the composition AI only reserves
a placeholder; rendering is delegated to an external module:

    visual_subtype = "photo"               →  external image generator
    visual_subtype = "map"                 →  external map module
    visual_subtype = "custom_infographic"  →  external decomposer module
    visual_subtype = "flowchart"           →  external flowchart generator

These external modules are NOT loaded into the composition prompt.
The AI just produces a placeholder block with metadata.

## Header / Style / Footer

    header_type = A     →  headers/type_a_rigid.md
    header_type = B     →  headers/type_b_floating.md
    header_type = C     →  headers/type_c_top.md
    header_type = none  →  no header module

    style_mode = strict →  styles/strict.md
    style_mode = soft   →  styles/soft.md

Footer rules are covered by core_rules.md §11. No separate module.

## Special Slide Templates (SVG assets, not rule files)

    slide_role = title       →  templates/title.svg
    slide_role = divider     →  templates/divider.svg
    slide_role = final       →  templates/final.svg
    slide_role = full_bleed  →  use core_rules.md §16 directly

For these slide_roles, layout/object/header modules are NOT loaded.
The AI only swaps logo, image, and text content inside the template SVG.

## Estimated Context per Slide

Typical content slide loads:

    core_rules.md           ~280 lines
    card.md                 ~120 lines  (when cards are present)
    patterns.md             ~80 lines   (when a pattern is used)
    1 header module         ~40 lines
    1 style module          ~40 lines
    ─────────────────────────────────────
    TOTAL                   ~400-560 lines

Comfortable context size, well below the "lost in the middle" threshold.