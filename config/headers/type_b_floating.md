# Header Type B — Floating
# Loaded when: classifier header_type = "B".
# Covers: title as the first block inside the content area, frame centered.

## TL;DR (read first)

- Type B = no separate header zone. Slide title is the FIRST block inside
  the content area, rendered as a normal `heading` object.
- Title + content = one frame, vertically centered in the working area
  (equal air above and below).
- Minimum air: 10-15px top and 10-15px bottom. If frame > 650-660px →
  trigger redistribution / split per core_rules §17.
- Per-slide decision (B or C), not presentation-wide.
- Excluded from slide_role IN [title, divider, final, full_bleed].

## When Type B Is Used

Set by classifier when:
  - user selected "Without header" globally AND visual block is NOT
    significantly taller than the informational block, OR
  - user selected "Auto" AND the deck is informal / marketing / startup
    AND visual block is NOT significantly taller than text.

If the visual block is significantly taller than the informational block
on a given slide → use Type C instead (per-slide decision).

## Mechanics

Step 1 — Render the slide heading as the topmost block of the content
        area, full width by default (12 cols), or narrower if composition
        sub-schema dictates (core_rules §5).

Step 2 — Lay out the remaining objects below the heading per
        core_rules §4-§5 (spatial logic and sub-schemas A/B/C/D).

Step 3 — Compute frame height = heading + 26px gap + content blocks
        (with internal 26px gaps between blocks).

Step 4 — Center the frame vertically in the working area (680px).
        Air above frame = air below frame = (680 - frame_height) / 2.

Step 5 — If air < 10-15px on either side → frame is too tall.
        Trigger core_rules §17 (redistribution → split → drop tertiary).
        NEVER reduce body font below 12pt to fit.

## Layout Implications

- The working area is the full 680px (no header zone reserved).
- The `heading` object from classifier IS rendered as a normal block.
- Footer (if present) sits independently at the bottom and does NOT
  participate in frame centering.

## What You MUST NOT Do

- Do NOT reserve a separate header zone.
- Do NOT pin the heading to the top of the working area — center the
  whole frame.
- Do NOT let air shrink below 10-15px; redesign instead.
- Do NOT render Type B on title / divider / final / full_bleed slides.

## Defaults Summary

- Heading = first block inside content area.
- Frame (heading + content) centered vertically in 680px working area.
- Min air: 10-15px top and bottom; otherwise → redistribute / split.
- Per-slide decision; siblings in the deck may be Type C.