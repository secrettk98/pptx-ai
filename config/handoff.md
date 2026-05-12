# Project Handoff — Layout System for AI Slide Redesign

> Read this file FIRST when continuing work in a new chat session.
> It contains everything needed to resume without re-explaining context.

---

## 1. Project Overview

**What is being built:** an AI service that redesigns PowerPoint presentations.
The user uploads a PPTX, the AI analyzes each slide, and generates a new design
as SVG.

**The core problem:** the AI does not know HOW the human designer (Alisher)
lays out slides. We are formalizing his layout system as a set of `.md` rule
files that will be fed into the AI (Gemini, possibly Claude) at runtime.

**Output of this work:** a modular configuration system in `config/` that the
backend assembles into a per-slide prompt for the generator AI.

---

## 2. About the User (Alisher)

- Professional presentation designer, NOT a programmer.
- Explain technical things simply, no jargon without unpacking.
- Works with two broad presentation styles: "strict" (formal/government, ~20%
  of cases) and "soft" (marketing/startup/product, ~80% of cases, the default).
- Cares deeply about reliability: "client won't pay for sometimes-it-works".
- Prefers iterative refinement: "AI makes a mistake, I come back, we fix the rule".
- Communicates in Russian. Rule files are in English (AI follows English better);
  example content inside rules can be Russian.

---

## 3. Communication Style With the User

- Ask questions in tight batches, minimum needed, no padding/water questions.
- Accept "depends on context" / "I do it differently each time" as valid —
  record as ranges or content-driven decisions, not as rigid rules.
- After each batch of answers, summarize what was captured before moving on.
- Never assume a "default" without confirming.
- When he pushes back on phrasing or architecture — engage seriously, rewrite.
  He has good design intuition AND good architectural intuition. He proactively
  raises structural concerns ("won't context overflow?", "why so many modules?").
- He prefers ONE question batch → his answer → finished module → next module.
  No long preambles.
- Long lists of bullet questions on simple topics annoy him. Cut to essentials.

---

## 4. Architecture (CURRENT — major rewrite happened in session 2)

### 4.1 Core insight: 6 object types, NOT N layout combinations

A slide is composed from exactly six object types:

  1. **heading** — slide title
  2. **text** — paragraphs, bullet lists
  3. **card** — composite block (icon / number / heading / body / image)
  4. **table** — tabular data
  5. **chart** — bar / line / pie / etc.
  6. **visual** — everything complex visual: photo, map, custom infographic,
     flowchart, pattern from the library

The OLD architecture had ~14 layout modules (single_table, table_plus_text,
chart_plus_text, text_plus_visual, ...). It was a combinatorial explosion that
duplicated rules across files. **It was deleted.**

The NEW architecture has only TWO object-specific modules: `card.md` and
`patterns.md`. Everything else (heading, text, table, chart, plain visuals) is
covered by composition rules in `core_rules.md`. AI receives object list from
classifier and composes the slide using core principles.

### 4.2 CRITICAL slide rule

A content slide MUST NOT consist of only {heading, text}. It MUST contain at
least one of {card, table, chart, visual}, OR the text must be reformatted
into cards/block-elements. This is the #1 rule against "empty wordy slides".

### 4.3 Object responsibility split

Composition AI is responsible for **layout** (placement, sizing), not for
rendering every object's internals.

| Object | Who renders | AI's role |
|---|---|---|
| heading | AI | renders fully |
| text | AI | renders fully |
| card | AI (per card.md) | renders fully |
| table | AI | renders fully |
| chart | external chart module | reserves placeholder + metadata |
| visual: photo | external (Nano Banana 2) | reserves placeholder + prompt |
| visual: map | external (reverse_map) | reserves placeholder + params |
| visual: custom_infographic | external decomposer | reserves placeholder + source |
| visual: flowchart | external flowchart gen | reserves placeholder + structure |
| visual: pattern | AI | takes SVG from patterns/, edits in place |

Pattern is the ONLY visual subtype the composition AI itself modifies.

### 4.4 Two-pass AI flow

- **Pass 1 — Classifier:** AI reads the slide + `core_rules.md` + `classifier.md`,
  returns JSON with: slide_role, objects[], visual_subtype, pattern_hint,
  header_type, style_mode, series_context, overload, client_constraints.
- **Pass 2 — Generator:** backend uses JSON to assemble only relevant modules
  into a focused prompt, then AI generates the SVG.

### 4.5 Directory structure (CURRENT)

    config/
    ├── handoff.md           ← this file
    ├── core_rules.md        ← foundation, 6 objects, composition rules ✅
    ├── classifier.md        ← classifier prompt + JSON schema ✅
    ├── modules_map.md       ← trigger table ✅
    ├── card.md              ← card anatomy + grid rules ✅
    ├── patterns.md          ← how to use pre-built SVG patterns ✅
    ├── headers/
    │   ├── type_a_rigid.md     ✅
    │   ├── type_b_floating.md  ✅
    │   └── type_c_top.md       ✅
    ├── styles/
    │   ├── soft.md             ✅
    │   └── strict.md           ✅
    ├── patterns/            ← SVG library (Alisher draws in pptx → svg)
    │   ├── timeline_1.svg, timeline_2.svg, ...
    │   ├── process_1.svg, ...
    │   ├── swot_1.svg
    │   ├── matrix_2x2_1.svg
    │   ├── hierarchy_1.svg
    │   ├── cycle_1.svg
    │   ├── funnel_1.svg
    │   ├── pyramid_1.svg
    │   └── venn_1.svg
    └── templates/
        ├── title.svg
        ├── divider.svg
        ├── final.svg
        ├── headers/        ← SVG templates for Type A rigid header (NEW)
        │   ├── header_a_1.svg, header_a_2.svg, ...
        └── free_composition/

### 4.6 Token budget per slide

Typical generator prompt: ~400-560 lines. Comfortable, well below
"lost in the middle" threshold.

### 4.7 Anti-overflow techniques in every module

- **TL;DR section at the top** (5-8 lines, binding even on skim).
- **Decision Tree at the bottom** — algorithmic shortcut.
- **CRITICAL / NEVER markers** for high-priority rules.
- **IF / THEN / ELSE format** — AI follows code-like structure well.
- **Target: 100-200 lines per module.** If over 250 → split.

### 4.8 Rule priority (defined in core_rules.md §0)

  1. core_rules.md (foundational)
  2. style module
  3. header module
  4. card.md
  5. patterns.md
  6. user instructions in the prompt (highest, but cannot override §1, §6, §9,
     §13 card height equality, §14 min 12pt body, §17 no content drop without
     permission)

### 4.9 SVG patterns library

`patterns/` = SVG assets Alisher draws himself in PowerPoint, exports as SVG,
adds metadata header. AI inserts and edits them in place (slot fills, segment
adjustment within stated range, color from palette). AI never improvises a
custom pattern.

`templates/` ≠ `patterns/`. Templates = whole slides (title/divider/final) OR
header bands (templates/headers/ for Type A). Patterns = blocks within a slide.

### 4.10 Off-grid / free composition slides — out of scope (v1)

Hero slides, magazine-style asymmetric layouts → only via SVG templates in
`templates/free_composition/`. AI does NOT generate them from scratch in v1.
If no matching template → fall back to closest grid layout, flag for review.

---

## 5. Key Design Principles (Captured From Alisher)

### 5.1 No emptiness (CRITICAL)
If a slide has little content with large empty areas, enrich with: AI-generated
topic image, reformat text into cards/metric blocks, split text into text+visual,
or duplicate info visually.

### 5.2 Visual weight balance (CRITICAL)
- "Heavy" block = dense informational content. "Light" = visual.
- Heavy CAN be shorter than light (small whitespace ok).
- Light CANNOT be significantly shorter than heavy (reads as broken).

### 5.3 Series consistency
- Identical structure across slides → IDENTICAL layout.
- Similar but not identical → checkerboard alternation.

### 5.4 Style unity (CRITICAL)
- Either ALL elements rounded or NONE (per presentation).
- Either ALL icons outlined (same stroke) or ALL filled. Never mix.

### 5.5 Cards: equal height across the whole slide (CRITICAL)
Within and between rows. "Column-chart effect" forbidden.

### 5.6 Body font ≥12pt; 10pt only for auxiliary
Body text NEVER below 12pt. 10pt allowed ONLY for caption / footnote /
copyright / auxiliary text inside dense cards. If primary content can't fit
at 12pt → redistribute → split slide → drop tertiary content (if allowed) →
manual review.

### 5.7 Default spatial logic
Information (text) → LEFT. Visual → RIGHT. Default, invertible.

### 5.8 Preserve client content by default
First strategy: redistribution. Then split. Then drop only tertiary, only with
permission. Never copy 1:1 if unreadable.

### 5.9 Custom infographics → semantic decomposition (delegated)
Composition AI identifies semantic intent (process? hierarchy? timeline?),
reserves space, passes to external decomposer module.

### 5.10 Special slides use templates, not freestyle
Title, divider, final → AI swaps logo/image/text inside hand-crafted SVG.
Type A header → AI swaps slots inside a hand-crafted SVG header template.

### 5.11 A card is NEVER just "a plate with text"
Always include a visual element (icon / divider / accent / number).

---

## 6. Grid Specs (memorize)

- viewBox: 1280 × 720 px
- 12 columns, gutter 26px
- Horizontal margins: 43px (left/right)
- Vertical margins: 20px (top/bottom)
- Column width: 76px
- Working area: 1194 × 680 px
- Standard widths: 12=1194, 8=790, 7=688, 6=582, 5=480, 4=382, 3=280

Block sizing: width = fill container, height = hug contents.
Vertical gap between blocks: 26px.

---

## 7. Three Header Types

- **Type A — Rigid:** fixed top header zone, separate from content. Same
  position on every content slide. Decided ONCE per presentation. AI does
  NOT draw it from scratch — uses an SVG template from
  `config/templates/headers/`, fills declared slots (title, optional logo /
  section / page number). Excluded from title/divider/full-bleed. Use for:
  formal/government/reporting.

- **Type B — Floating:** title is the first block inside content area.
  Title + content vertically centered together as one frame in the 680px
  working area. Min air 10-15px top and bottom; otherwise → redistribute /
  split. Use for: balanced content, marketing/startup/product.

- **Type C — Top hybrid:** heading is a separate top band, joined with
  content into one frame, all centered together. Triggered when visual is
  significantly taller than text (~1.5× or more). Same min air rule as B.

A is presentation-wide. B and C are chosen per-slide.
User selects globally: With header / Without header / Auto.

---

## 8. Composition Sub-schemas (in core_rules.md §5)

When combining text/cards with a visual block:

- **A — Symmetric side-by-side** (default, 6+6 / 7+5 / 8+4)
- **B — Asymmetric wrap** (visual short, text wraps under it)
- **C — Mosaic** (visual is one peer block among 3+)
- **D — Horizontal stack** (wide visual full-width on top, content below)

These are universal across all object types (chart, map, photo, pattern, etc.)
and live in core_rules.md, not in a separate `text_plus_visual` module.

---

## 9. Style Baselines (summary; full rules in styles/<mode>.md)

Both modes share:

- White slide background, #F8F8F8 card/backdrop fill.
- Black primary text, gray auxiliary text.
- Brand accent: user-provided or extracted from client logo / source slides.
- Charts with 3+ segments → gradation of brand accent. With 3-4 categorical
  segments → brand accent + gray + black + one supplementary color.
- Font: ONE per deck, picked from Google Sans / Century Gothic / Roboto by
  content density (Roboto = compact, Century Gothic = airy, Google Sans =
  balanced). Not tied to mode.
- Sizes: slide heading 24pt, slide subheading/kicker 12pt, block heading
  14-16pt, body 12pt (min), caption/footnote/auxiliary 10pt (min, auxiliary
  only). Large numbers — AI decides by context.
- Lines and borders: 0.75pt. Borders only when there is no fill.
- No shadows anywhere.

Mode differences:

- **soft:** rounded corners (~12px, range 8-16, uniform across deck).
- **strict:** sharp corners (radius 0 everywhere). Visual restraint —
  dividers preferred over accent fills, typography-first.

Icons: outlined OR filled, AI's choice, but uniform across the deck (both
modes). Stroke width 1.5-2px for outlined, fixed once per deck.

---

## 10. Status — Done / Next

### ✅ Done

- `core_rules.md` — full rewrite under 6-object model (§0–§21), §14 updated
  to allow 10pt for auxiliary text only.
- `classifier.md` — full rewrite, returns objects[] + visual_subtype + pattern_hint.
- `modules_map.md` — full rewrite, drastically simplified.
- `card.md` — full rewrite under 6-object model.
- `patterns.md` — written from scratch.
- `headers/type_a_rigid.md` — uses SVG templates from templates/headers/.
- `headers/type_b_floating.md` — frame centered, min air 10-15px.
- `headers/type_c_top.md` — heading band + content, frame centered.
- `styles/soft.md` — rounded, ~12px radius, full token set.
- `styles/strict.md` — sharp, radius 0, full token set.
- `handoff.md` — this file (current state).

### ⏭ Next (in order)

1. **SVG templates** — Alisher draws in PowerPoint, exports SVG, adds
   metadata headers:
   - `templates/title.svg`
   - `templates/divider.svg`
   - `templates/final.svg`
   - `templates/headers/header_a_1.svg`, `header_a_2.svg`, ... (Type A)
2. **Patterns SVG library** — Alisher populates `config/patterns/` with
   hand-drawn SVGs per `patterns.md` metadata spec (timeline, process, swot,
   matrix_2x2, hierarchy, cycle, funnel, pyramid, venn).
3. **Real-world testing:** run the system on actual decks, collect failure
   modes, iterate on rules.

### 🔮 Architectural topics deferred

- How to organize PowerPoint reference library mapped to .md files.
- How AI requests SVG references at runtime (tool-call mechanics).
- Multi-provider consistency (Gemini vs Claude).
- Auto-generation of templates via vision-AI (extracts structure from
  reference images → normalized SVG with slot metadata).

### ❌ Removed from earlier plan

OLD architecture's ~14 layout modules (text_plus_visual, cards_grid,
chart_plus_text, single_table, table_plus_text, map_plus_text, photo_plus_text,
single_text, metrics_row, text_plus_cards, overloaded, custom_infographic,
schema, components/*) were all deleted — replaced by core_rules + card.md +
patterns.md.

Most pattern modules also collapsed into one `patterns.md` + SVG library.
Comparison, before_after, agenda, big_number, testimonial, logos_grid, team,
qa, quote → handled as standard cards/text via core_rules. Kept as patterns
(with SVG library): timeline, process, swot, matrix_2x2, hierarchy, cycle,
funnel, pyramid, venn.

---

## 11. Question-Asking Methodology

Working pattern (per Alisher's preference):

1. **Minimum essential questions** in one batch. No "warming up" questions.
2. **Concrete phrasing**, not abstract ("4+8? 6+6?" not "how do you split?").
3. **Accept "depends" answers** — record as content-driven decisions.
4. **After answers, write the module** in a code block, then ask
   "ok / what to fix?" before moving on.
5. **No splitting one module's questions across multiple batches** unless
   the module is genuinely large.

Pattern that works:
  AI: 3-5 questions in one message
  Alisher: short answers
  AI: full module .md in code block, ready to use
  Alisher: ok / fix this
  AI: next module, repeat

---

## 12. Open Questions / To Calibrate Later

- Exact px values for paddings and internal gaps (24px/16px/8px placeholders
  in card.md — confirm or adjust during real testing).
- How AI determines `series_context` across a multi-slide deck.
- Hero / free-composition slides (v2 project).
- Pattern SVG metadata format — current spec in patterns.md, will calibrate
  during real SVG library creation.
- Header SVG template metadata format (templates/headers/) — calibrate when
  Alisher draws the first header template.

---

## 13. Quick Resume Checklist for New Chat

When opening a new chat, paste:

1. This `handoff.md` (full)
2. `core_rules.md` (full)
3. `classifier.md` (full)
4. `modules_map.md` (full)
5. `card.md` (full)
6. `patterns.md` (full)
7. Three header modules (`headers/type_a_rigid.md`, `type_b_floating.md`,
   `type_c_top.md`)
8. Two style modules (`styles/soft.md`, `styles/strict.md`)

Then say what to work on next.

The new assistant should:

- Confirm it has read everything.
- NOT propose architectural rewrites unless Alisher asks — the architecture
  in §4 is the result of explicit decisions made by Alisher and should be
  treated as stable.
- Use the question-asking methodology from §11 (tight, minimum, concrete).
- Follow the communication style from §3.
- Remember: 6 objects, NOT N layout combinations. card.md and patterns.md
  are the ONLY object-specific modules. Everything else lives in core_rules.