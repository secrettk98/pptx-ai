# Header Type C — Top Hybrid
# Loaded when: classifier header_type = "C".
# Covers: header as a separate top zone, joined with content into one
#         centered frame.

## TL;DR (read first)

- Type C = heading sits in its own top zone (separate band, full width),
  but the heading + content together form ONE frame that is vertically
  centered in the working area.
- Used when the visual block is significantly taller than the
  informational block — separating the heading rebalances the slide.
- Minimum air: 10-15px top and 10-15px bottom. If frame doesn't fit →
  trigger core_rules §17.
- Per-slide decision (B or C), not presentation-wide.
- Excluded from slide_role IN [title, divider, final, full_bleed].

## When Type C Is Used

Set by classifier when:
  - user selected "Without header" globally AND the visual block is
    significantly taller than the informational block, OR
  - user selected "Auto" AND the same height imbalance applies.

Heuristic for "significantly taller": visual block height > informational
block height by roughly 1.5× or more, such that Type B would leave
the visual surrounded by emptiness (violates core_rules §7).

## Mechanics

Step 1 — Render the heading as a full-width band at the top of the frame
        (not the top of the working area — frame is centered later).
        Heading band = 12 cols wide, height = hugs heading content.

Step 2 — Below the heading band, lay out remaining objects per
        core_rules §4-§5. Typical pairing: heading on top → text-left +
        visual-right below (sub-schema A inside the frame), OR heading
        on top → visual full-width below (sub-schema D).

Step 3 — Compute frame height = heading band + 26px gap + content blocks.

Step 4 — Center the frame vertically in the working area (680px).
        Air above = air below = (680 - frame_height) / 2.

Step 5 — If air < 10-15px → redistribute / split per core_rules §17.

## Difference From Type B

Both center the frame vertically. The difference is structural:

  - Type B: heading is just the first block of a normal stacked layout.
  - Type C: heading is a distinct top band, visually separated from the
    content blocks below it, treated as its own zone within the frame.

Type C reads as "header on top + content below", but the whole pair
floats in the middle of the working area instead of pinning to the top.

## Layout Implications

- Working area = full 680px (no fixed header zone reserved).
- Heading band MAY use a subtle visual separator (thin divider line,
  accent bar) per styles/<mode>.md, but is NOT a Type A rigid header.
- Footer (if present) sits independently and does NOT participate in
  frame centering.

## What You MUST NOT Do

- Do NOT pin the heading band to the top of the working area —
  center the whole frame.
- Do NOT use Type C when text and visual blocks are roughly balanced —
  use Type B instead.
- Do NOT let air shrink below 10-15px; redesign instead.
- Do NOT render Type C on title / divider / final / full_bleed slides.

## Defaults Summary

- Heading = full-width top band of the frame.
- Frame (heading band + content) centered vertically in 680px.
- Triggered by visual >> text height imbalance.
- Min air: 10-15px top and bottom; otherwise → redistribute / split.
- Per-slide decision; siblings in the deck may be Type B.