# Core Layout Rules
# Always loaded into AI context. Foundation for all slide generation.

## 0. Rule Priority & Conflict Resolution

You will receive multiple rule modules in one prompt. Apply them in this priority
(higher number = higher priority, wins on conflict):

  1. core_rules.md (this file) — foundational, always applies
  2. style module (strict / soft) — visual treatment baseline
  3. header module (A / B / C) — header zone behavior
  4. card.md — when cards are on the slide
  5. patterns.md — when a pattern from the library is used
  6. user instructions in the current prompt — highest priority, override all
     EXCEPT: never violate §1 (no heading-only-text slides), §6 (no emptiness),
     §9 (style unity), §13 (card height equality, in card.md),
     §14 (min 12pt body), §17 (no content drop without permission).

If two modules contradict and neither has higher priority, prefer the more
SPECIFIC rule over the more GENERAL one. The TL;DR section of every module
is binding even if you skim the rest.

## 1. The Six Object Types (CRITICAL)

Every slide is composed from these six object types and ONLY these:

  1. heading   — slide title
  2. text      — paragraphs, bullet lists
  3. card      — composite block (icon / number / heading / body / image)
  4. table     — tabular data
  5. chart     — bar / line / pie / etc.
  6. visual    — everything complex visual (photo, map, custom infographic,
                 flowchart, pattern from the library)

CRITICAL RULE: a slide MUST NOT consist of only {heading, text}.
At least one object from {card, table, chart, visual} MUST be present,
OR the text MUST be reformatted into cards / block-elements.

A "block-element" = composite visual unit:
  icon + number + label, OR icon + heading + text, OR large number + caption.
  Block-elements (i.e. cards) are the primary tool for fighting emptiness.

## 2. Object Responsibility Split

The composition AI is responsible for layout — placement, sizing, proportions —
not for rendering every object's internals. Some objects are filled in by
external modules; the AI reserves space and produces a placeholder with metadata.

  heading   → AI renders fully
  text      → AI renders fully
  card      → AI renders fully (rules in card.md)
  table     → AI renders fully
  chart     → AI reserves placeholder. External chart-rendering module fills it.
              Placeholder must specify: chart type, data, dimensions, position.
  visual    → AI reserves placeholder. Source depends on subtype:
              - photo              → external image generator (Nano Banana 2)
              - map                → external map module (reverse_map)
              - custom_infographic → external decomposer module
              - flowchart          → external flowchart generator
              - pattern            → AI takes SVG from patterns/ library and
                                     edits it in place (only visual subtype
                                     the AI itself modifies — see patterns.md)

Placeholder format for external modules: a rectangle of the chosen size and
position, with metadata as XML comment listing what the module needs
(type, data, dimensions, source content).

## 3. Canvas & Grid

- viewBox: 1280 × 720 px
- Grid: 12 columns
- Horizontal margins (left/right): 43px
- Vertical margins (top/bottom): 20px
- Column width: 72px
- Gutter between columns: 30px
- Gutter between rows: 30px
- Working area: 1194 × 680 px

Standard block widths (formula: span × 72 + (span − 1) × 30):

| Columns | Width | Usage |
|---------|-------|-------|
| 12 | 1194 | full-width content |
| 8  | 786  | dominant block |
| 7  | 684  | primary side in 7+5 split |
| 6  | 582  | symmetric 6+6 split |
| 5  | 480  | secondary side in 7+5 split |
| 4  | 378  | side block next to 8-col dominant |
| 3  | 276  | quarter card / metric |

Block sizing:
- Width = fill assigned columns.
- Height = hug contents.
- Vertical gap between blocks = 30px. Internal gaps inside a block may differ.

## 4. Default Spatial Logic

DEFAULT: informational content (text, cards) → LEFT.
DEFAULT: visual content (chart, map, photo, schema, pattern) → RIGHT.
This is a default, invertible by composition needs.

## 5. Composition Sub-schemas (text/cards + visual)

When the slide combines an informational block with a visual block, choose one:

  A — Symmetric side-by-side (default)
      Two columns, balanced content. Common ratios: 6+6, 7+5, 8+4.
      Vertically center the shorter column to the taller, IF the height
      gap is small. If gap is large, switch to B or D.

  B — Asymmetric wrap
      Visual is shorter than total text height.
      Layout: header on top-left (4-5 cols), visual on top-right (7-8 cols),
      secondary text flows under the visual or shifts horizontally.
      Eliminates dead space next to a short visual.

  C — Mosaic
      Visual is one peer block among 3+ blocks (text + cards + visual tiled).
      Visual occupies 3-5 columns, treated as equal to other blocks, not as hero.

  D — Horizontal stack
      Visual has wide aspect ratio (panorama, wide chart, landscape map).
      Layout (top to bottom): header full width → visual full width
      → text/cards below in 2 or 3 columns.
      Variant: visual below text blocks if it reads better.

Decision order:
  Step 1: Wide-aspect visual? → D
  Step 2: Visual is one of 3+ peer blocks? → C
  Step 3: Visual significantly shorter than text column? → B
  Step 4: Otherwise → A.

## 6. The "No Emptiness" Principle (CRITICAL)

If the slide has little content and large empty areas:
  → enrich with one of:
    - generated topic-related image
    - reformat data into cards / metric-blocks / pattern
    - split a single text block into text + cards
    - duplicate key info visually (e.g. map shows summary, side text expands it)

Never stretch a block by adding empty space.

## 7. Visual Weight Balance (CRITICAL)

  - "heavy" block = dense informational content (text, metrics, data, cards)
  - "light" block = visual content (image, map, chart, pattern)

  - Heavy CAN be shorter than light — small whitespace around dense content is ok.
  - Light CANNOT be significantly shorter than heavy — empty space around a
    visual reads as broken.

If light < heavy: enlarge the visual, switch sub-schema (B or D),
or add a secondary visual element. Never leave the visual surrounded by emptiness.

## 8. Series Consistency

  - Identical structural slides (same object set, same role) → IDENTICAL layout
    across the series (same widths, positions, heights).
  - Similar but not identical → checkerboard alternation
    (slide 1: text-left/visual-right; slide 2: visual-left/text-right; ...).

## 9. Style Unity (CRITICAL)

A presentation is in ONE of two style modes:
  - "strict" — no border-radius anywhere (~20% of cases, formal/gov)
  - "soft"   — consistent border-radius (~80% of cases, default)

NEVER mix rounded cards with sharp icons, or vice versa.

Icon style unity:
  - Either ALL icons outlined (same stroke width) OR ALL filled.
  - NEVER mix outlined and filled icons in one presentation.

## 10. Header Types (3 modes)

TYPE A — RIGID
  Fixed top header zone, separate from content. Same position on every content
  slide. Decided ONCE per presentation. Excluded from title/divider/full-bleed.
  Use when: formal/government/reporting, OR client template uses it,
  OR user selected "With header".

TYPE B — FLOATING
  Title is the first block inside content area. Title + content vertically
  centered together as one frame. Use when: informal/marketing/startup, balanced.

TYPE C — TOP HYBRID
  Header is a separate zone, joined with content into one frame, all centered
  together. Use when: visual block is significantly taller than text — separate
  header rebalances composition.

A is presentation-wide. B and C are chosen per-slide.

## 11. Footer

Optional. Bottom zone, NOT part of content area. Present only if client requires
page numbers, copyright, or section name. Appears only on content slides.
Excluded from title, divider, final.

## 12. Icons

  - One presentation = one icon style (all outlined OR all filled — see §9).
  - Stroke width consistent across all icons.
  - Size: AI's judgment, scaled to context. Recommended baseline 24-32px
    inside cards, larger when icon is the centerpiece of a block.

## 13. Card Anatomy (summary; full rules in card.md)

  - Padding: left/right CONSTANT (baseline 24px), top/bottom adaptive.
  - Internal hierarchy gap: gap(icon→heading) > gap(heading→body). Mandatory.
  - All cards on the slide MUST have equal height (within and between rows).
  - Top-aligned content inside the card (with padding). Never vertically centered.
  - A card NEVER consists of just "a plate with text" — always a visual element.

## 14. Text Density & Readability

  - Body font minimum: 12pt. NEVER smaller. 10pt allowed ONLY for caption / footnote / copyright / auxiliary text in dense cards. Body itself never below 12pt
  - If a 12-col text block exceeds ~30% of slide height:
    → split into 2 columns (rarely 3),
    → OR reformat part of it into cards / block-elements.
  - No first-line indent. Vertical paragraph spacing ~8-12px.
  - Use bullets / numbering only when semantically appropriate.

## 15. Special Slides Use Pre-built Templates

Title slide, section divider, final/contacts slide → use SVG templates from
config/templates/. AI swaps only logo, image, and text content.
DO NOT generate these layouts from scratch.

## 16. Full-bleed Slides

If slide content is a single dominant element (full image, full schema, full map):
  - Element extends to viewBox edges (1280×720), bypassing margins.
  - Header optional; if present, place on semi-transparent backdrop.
  - Footer usually omitted.

## 17. Overloaded Slides (content-dense)

DEFINITION: a single source slide containing 4+ heterogeneous object types
(e.g. map + table + chart + text + cards together).

CORE PRINCIPLE: preserve all content by default. Source content is intentional
unless the client explicitly allows removal.

If overload = true:

  STEP 1 — Identify content priority: primary / secondary / tertiary.

  STEP 2 — Allocate area by priority:
    - primary:   ~50-60% of working area, full readability
    - secondary: ~25-35%, compact but readable (≥12pt body)
    - tertiary:  ~10-15%, compressed into block-elements / footnote-style

  STEP 3 — Choose strategy in order:
    A. Redistribution on one slide. Resize per priority. Reformat
       (long text → bullets, wide table → key rows, decorative → icons).
       Keep ALL content readable at ≥12pt. PREFERRED.
    B. Split into 2-3 slides. ONLY IF allow_slide_split = true.
       Group by semantic relatedness. Title each split slide clearly
       ("Регион в цифрах — часть 1 из 2").
    C. Drop content. ONLY IF allow_content_removal = true.
       Drop only tertiary/decorative. NEVER primary or secondary.

  STEP 4 — If none works → flag for manual review. Do not silently crush content.

NEVER reduce body font below 12pt.
NEVER drop content without explicit client permission.
NEVER copy the source layout 1:1 if it is unreadable — redesign arrangement,
keep information.

## 18. Custom Infographics — Semantic Decomposition

Client-built composite visuals (assembled from PPT shapes/arrows/icons/photos)
are NOT copied visually. Decompose semantically:
  - process? → match to process pattern
  - hierarchy? → match to hierarchy pattern
  - comparison? → cards in two columns
  - timeline? → match to timeline pattern
  - other → describe content as objects, lay out per core_rules.

The composition AI delegates the actual rebuild to the external decomposer
module (see §2). Composition AI's job here: identify the semantic intent,
reserve space, pass source content to the decomposer.

## 19. Off-Grid / Free Composition (Out of Scope)

Hero slides, overlay graphics, magazine-style asymmetric layouts are handled
ONLY via pre-built SVG templates in config/templates/free_composition/.
AI does NOT generate these from scratch.

If source slide is clearly free composition AND no matching template exists:
  → fall back to closest grid layout (usually sub-schema A or D)
  → flag slide as requires_manual_review: true.

## 20. Patterns Library (Brief)

If the slide needs a structured graphic with fixed geometry (timeline, process,
swot, matrix_2x2, hierarchy, cycle, funnel, pyramid, venn) → take a base SVG
from config/patterns/ and edit it in place. Full rules in patterns.md.

This is the ONLY visual subtype the composition AI itself modifies.
All other complex visuals (photo, map, custom infographic, flowchart) are
filled by external modules.

## 21. Module Index

The current prompt may include the following modules beyond core_rules.md.
Each has its own TL;DR — read first.

[loader inserts list at runtime]