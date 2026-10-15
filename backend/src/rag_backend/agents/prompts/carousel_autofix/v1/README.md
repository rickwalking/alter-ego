# Carousel autofix prompts v1 (AE-0367)

Used by the owner's Telegram **🛠 Fix issues** button. The fix is deterministic
except for one step: EN texts that are still Portuguese (or the PT copy pasted
as-is) are translated again, field by field, in one bounded call.

| File | Renders | Variables |
|------|---------|-----------|
| `en_retranslate.yaml` | `build_autofix_retranslate_prompt` | `items_json`: `[{"id": "<slide>:<path>", "text": "<PT source>"}]` |

The model answers `{"translations": [{"id", "text"}]}`. An answer that is empty
or still Portuguese is discarded and the current EN text is kept.
