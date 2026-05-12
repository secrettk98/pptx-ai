# Header Type A — Rigid
# Loaded when: classifier header_type = "A".
# Covers: fixed top header zone, same position on every content slide.

## TL;DR (read first)

- Type A = fixed top header zone, separate from content area.
- AI does NOT draw the header from scratch. Use an SVG template from
  config/templates/headers/ and fill its slots (slide title, optional
  logo / section / page number).
- Header position and height are IDENTICAL on every content slide of
  the deck. Decided ONCE per presentation.
- Excluded from slide_role IN [title, divider, final, full_bleed].
- Content area sits BELOW the header zone, with standard 26px gap.

## When Type A Is Used

Set by classifier when:
  - user selected "With header" globally, OR
  - source PPTX has a consistent header on every slide, OR
  - domain is formal / government / reporting.

Type A is presentation-wide: if one content slide is A, all content slides
in the deck are A.

## Mechanics

Step 1 — Pick a header template.
        Take an SVG from config/templates/headers/ (e.g. header_a_1.svg).
        The choice is made ONCE for the deck and reused on every content slide.

Step 2 — Read the template metadata header.
        Each template SVG starts with a metadata comment listing:
          @height          fixed header zone height in px
          @slots           named placeholders (title, logo, section,
                           page_number, date, divider, ...)
          @adapts          what is allowed to change (text, logo image,
                           accent color)

Step 3 — Reserve the header zone.
        Header occupies the top of the viewBox, full width (1280px),
        height = template's @height. Content area starts 26px below.

Step 4 — Fill slots.
        Replace each @slots placeholder with the slide's content
        (slide title text, client logo, section name, page number, etc.).
        Do NOT add slots beyond those declared.

Step 5 — Apply accent color from styles/<mode>.md palette to recolorable
        elements only.

## Layout Implications

- Working area for content shrinks: content_height = 680 - header_height - 26.
- Title is rendered INSIDE the header template (slot fill), NOT as a
  separate "heading" object on the content slide. The slide's `heading`
  object from classifier maps to the template's title slot.
- Header zone is OUTSIDE the 12-column grid. The grid still applies to
  the content area below.
- Footer (if present, per core_rules §11) sits at the bottom independently.

## What You MUST NOT Do

- Do NOT draw the header from scratch.
- Do NOT change @height between slides of the same deck.
- Do NOT introduce slots beyond those in @slots.
- Do NOT place the slide heading as a separate block when Type A is active —
  it lives inside the template.
- Do NOT render Type A on title / divider / final / full_bleed slides.

## Defaults Summary

- Header = SVG template from config/templates/headers/, fixed per deck.
- Position: top of viewBox, full width, fixed height.
- Slide title goes into the template's title slot.
- Content area starts 26px below the header zone.
- Outside slide_role = content → no header at all.