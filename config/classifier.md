# Slide Classifier
# First-pass AI prompt. Returns JSON describing the slide.
# Output drives which modules are loaded for the second-pass generator.

## Output Schema

    {
      "slide_role": "content | title | divider | final | full_bleed",

      "objects": [
        "heading", "text", "card", "table", "chart", "visual"
      ],

      "visual_subtype": "photo | map | custom_infographic | flowchart | pattern | null",

      "pattern_hint": "timeline | process | swot | matrix_2x2 | hierarchy | cycle | funnel | pyramid | venn | null",

      "header_type": "A | B | C | none",

      "needs_footer": true,

      "style_mode": "strict | soft",

      "series_context": "standalone | identical_series | similar_series",

      "overload": false,

      "client_constraints": {
        "verbatim_text": false,
        "preserve_template": false,
        "allow_slide_split": true,
        "allow_content_removal": false
      }
    }

## Decision Rules

### slide_role

    IF first slide of deck                              → "title"
    IF section divider (large title only, no content)   → "divider"
    IF last slide AND contains contacts / "thank you"   → "final"
    IF single dominant visual filling viewport          → "full_bleed"
    ELSE                                                → "content"

### objects

Multi-select. List EVERY object type present on the slide, from the 6 allowed:
heading, text, card, table, chart, visual.

Mapping hints from source content:

  - slide title                                         → "heading"
  - paragraphs / bullet lists                           → "text"
  - composite blocks (icon+text, number+label,
    image+caption tile)                                 → "card"
  - tabular data with rows and columns                  → "table"
  - bar / line / pie / area / scatter                   → "chart"
  - photo, map, schema, flowchart, custom client
    infographic, structured graphic
    (timeline/funnel/swot/etc.)                         → "visual"

CRITICAL: a content slide MUST include at least one of
{card, table, chart, visual}. If the source has only heading + text,
flag the long text for reformatting into cards (the generator will
handle the actual transformation; classifier just notes the absence).

### visual_subtype

Set ONLY if "visual" is in objects. Choose one:

    photo               → photographic image
    map                 → geographic map
    custom_infographic  → client-built composite (PPT shapes + arrows + icons
                          + text assembled by hand into one figure)
    flowchart           → block-scheme with connected nodes (decision flow,
                          system diagram, process boxes with arrows)
    pattern             → matches one of the library patterns: timeline,
                          process, swot, matrix_2x2, hierarchy, cycle,
                          funnel, pyramid, venn
    null                → no visual on the slide

If multiple visuals on one slide, pick the dominant one. Edge cases
(e.g. map + photo) are rare; pick the primary subject.

### pattern_hint

Set ONLY if visual_subtype = "pattern". Pick the pattern that matches the
source content's semantic structure:

    timeline    → sequence of events along a time axis
    process     → linear sequence of steps with directional flow
    swot        → 4 quadrants labeled S/W/O/T (or equivalent)
    matrix_2x2  → 4 quadrants defined by two axes with labels
    hierarchy   → tree structure (org chart, taxonomy, parent-child)
    cycle       → circular flow returning to start
    funnel      → narrowing stages (top-wide → bottom-narrow)
    pyramid     → stacked levels (often bottom-wide → top-narrow)
    venn        → overlapping sets showing intersections

If unsure → null. The generator will decide.

### header_type

    IF user selected "With header" globally
      → "A" for all content slides

    IF user selected "Without header" globally
      → per-slide:
        IF visual block height >> informational block height → "C"
        ELSE                                                 → "B"

    IF user selected "Auto"
      → presentation-level decision (decide once for the deck):
        IF source PPTX has consistent header on every slide  → "A"
        IF domain is formal / government / reporting         → "A"
        ELSE → per-slide "B" or "C" by the rule above

    IF slide_role IN [title, divider, final, full_bleed]    → "none"

### style_mode

    IF source presentation uses rounded corners       → "soft"
    IF source is formal / government / strict corp.   → "strict"
    DEFAULT                                           → "soft"

### series_context

    "standalone"        → unrelated to neighbors
    "identical_series"  → multiple slides with the same object set and
                          structure (e.g. 5 region slides each
                          "heading + text + map")
    "similar_series"    → multiple slides with same object set but varying
                          content shapes (e.g. text+photo slides with
                          different photo sizes)

### overload

    overload = true IF:
      count of distinct object types on the source slide >= 4
      AND the mix is heterogeneous (data + visual + narrative together)
      AND the slide is visibly content-dense

    ELSE overload = false.

### needs_footer

    true IF the deck uses page numbers / copyright / section names on every slide.
    false otherwise.

### client_constraints

Carried in from user input. Default values if unspecified:

    verbatim_text:         false
    preserve_template:     false
    allow_slide_split:     true
    allow_content_removal: false

## Classifier Output Validation

Before returning, verify:

  - objects is non-empty for content slides.
  - For content slides: objects contains at least one of
    {card, table, chart, visual}, OR a note flagging "text-only source,
    needs reformatting".
  - If visual_subtype is set → "visual" is in objects.
  - If pattern_hint is set → visual_subtype = "pattern".
  - If slide_role IN [title, divider, final, full_bleed] → header_type = "none".