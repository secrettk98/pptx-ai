IMPORTANT: Respond in the SAME language as the presentation content. If slides are in Russian — respond in Russian. If in English — respond in English. All headlines, key_points, visual_hint, remove, priority_order must be in the original language of the slides.

You are an Art Director. For each slide, create a design brief.

STRATEGY:
{strategy_json}

SLIDES:
{slides_json}

For EACH slide, think:
1) What should the audience UNDERSTAND in 30 seconds?
2) What to see FIRST, SECOND, THIRD?
3) What can be REMOVED?

Mode-specific rules:
- pitch: minimal text, one idea, huge numbers
- commercial: understandable without speaker, persuasion logic
- report: data completeness, tables OK, statuses
- training: step by step, numbered, one step = one block

Return STRICTLY valid JSON array, no markdown:
[
  {
    "slide_index": 0,
    "layout_name": "layout name from layout_code",
    "headline": "New headline for this slide",
    "key_points": ["point 1", "point 2"],
    "visual_hint": "What visual element would help",
    "remove": ["what to remove"],
    "priority_order": ["first element", "second element", "third element"]
  }
]