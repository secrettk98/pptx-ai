# Patterns — Object Module
# Loaded when: classifier visual_subtype = "pattern".
# Covers: how to use a pre-built SVG from config/patterns/ as a slide block.

## TL;DR (read first)

- A pattern is a pre-drawn SVG asset stored in config/patterns/.
  Never draw these structures from scratch.
- Pattern is the ONLY visual subtype the composition AI itself edits.
  All other visuals (photo / map / custom_infographic / flowchart) are
  filled by external modules.
- Workflow: pick the matching SVG → read its metadata header → place it
  in the chosen slide block → fill slot placeholders with slide content
  → adapt colors and segment count if needed.
- Do NOT redraw the pattern's geometry. Move only the slots, recolor,
  add/remove segments per the SVG's stated capabilities.
- Pattern is one block among the slide's objects, not a whole-slide layout.
  Composition with surrounding objects follows core_rules §4-§5.

## Available Patterns

The library at config/patterns/ contains SVG files grouped by type:

    timeline    — sequence of events along a time axis
    process     — linear sequence of steps with directional flow
    swot        — 4 quadrants labeled S/W/O/T (or equivalent)
    matrix_2x2  — 4 quadrants defined by two axes with labels
    hierarchy   — tree structure (org chart, taxonomy, parent-child)
    cycle       — circular flow returning to start
    funnel      — narrowing stages (top-wide → bottom-narrow)
    pyramid     — stacked levels (often bottom-wide → top-narrow)
    venn        — overlapping sets showing intersections

Each pattern type has one or more variants:

    config/patterns/funnel_1.svg
    config/patterns/funnel_2.svg
    config/patterns/timeline_1.svg
    ...

Variants differ in orientation, segment count, or visual treatment.
Pick the variant whose stated capabilities best fit the slide's content.

## Pattern SVG Metadata

Every pattern SVG begins with a metadata comment describing the asset:

    <!--
    @pattern: funnel
    @variant: 1
    @aspect: vertical
    @dimensions: 380x520
    @segments: 4 (min 3, max 5)
    @adapts: segment_count, colors, text
    @slots:
      - segment_1_label
      - segment_1_value
      - segment_2_label
      - segment_2_value
      ...
    -->

Read this header BEFORE editing the SVG. It states:

    - what the pattern is and which variant
    - natural aspect ratio and dimensions (for placement on the slide)
    - default and acceptable segment counts
    - what is allowed to change (colors, text, count)
    - the named slot placeholders to fill with slide content

NEVER change anything outside the @adapts list.

## Workflow

Step 1 — Match content to a pattern type.
        Use classifier's pattern_hint when set. If hint is null, infer
        from the source content's semantic structure (sequence in time
        → timeline; narrowing stages → funnel; tree → hierarchy; etc.).

Step 2 — Pick a variant.
        Read each candidate SVG's @aspect and @segments range.
        Choose the variant whose aspect fits the slide block you reserved
        and whose segment range covers the data count.

Step 3 — Reserve the block.
        Allocate columns/rows on the grid for the pattern, sized to its
        @aspect ratio (per core_rules §3 grid). The pattern is one peer
        block — surrounding heading/text/cards follow core_rules §4-§5.

Step 4 — Insert the SVG into the reserved block.
        Scale uniformly to fit the block. Do not distort.

Step 5 — Fill slots.
        Replace each @slots placeholder with the corresponding slide
        content (label, value, short text). Preserve typography rules
        (≥12pt body, core_rules §14).

Step 6 — Adapt segment count, IF needed.
        If data count differs from the SVG's default segments, AND
        @adapts includes segment_count, AND the new count is within
        @segments range → duplicate or remove a segment using the
        SVG's existing geometry as the template. Keep spacing rules
        consistent across all segments.

Step 7 — Adapt colors.
        Apply presentation's accent palette (from styles/<mode>.md)
        to elements marked recolorable. Do not introduce new colors
        outside the palette.

## What You MUST NOT Do

    - Do NOT redraw the pattern's geometry from scratch.
    - Do NOT change @dimensions ratio (only uniform scale).
    - Do NOT rearrange the pattern's structural elements.
    - Do NOT introduce new slots beyond those declared in @slots.
    - Do NOT modify segment count outside the @segments range.
    - Do NOT mix two patterns into one (e.g. funnel + cycle hybrid).

If no variant fits the content within its declared limits:
    → fall back to the closest pattern that does fit, OR
    → flag the slide as requires_manual_review = true.
    Do NOT improvise a custom pattern.

## Composition Notes

A pattern is a block, not a slide. It is placed alongside other objects
(heading / text / card / table / chart) according to:

    - core_rules §4 (spatial logic: text left, visual right by default)
    - core_rules §5 (sub-schemas A/B/C/D for combining text and visual)
    - core_rules §7 (visual weight balance — pattern = light block)

Examples of typical compositions:

    - heading + text on the left, funnel pattern on the right (sub-schema A)
    - heading + cards on the left, hierarchy pattern on the right (A)
    - heading on top full-width, timeline pattern below full-width (D)
    - heading + matrix_2x2 pattern as the dominant visual, supporting
      text below (D)

## Defaults Summary

    - Pick variant by @aspect and @segments fit.
    - Modify only what @adapts allows: segment_count, colors, text.
    - Pattern is one block among objects — composition by core_rules §4-§5.
    - On no-fit → fallback pattern OR manual review flag. Never improvise.