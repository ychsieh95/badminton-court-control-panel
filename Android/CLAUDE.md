# Claude Code instructions

Read and follow the shared Android instructions:

@AGENTS.md

Every task that changes user-visible text must update `tools/extra_strings.json` or `TRANSLATIONS` in `../Web/app.py` and regenerate both string resource files with `python3 tools/gen_strings.py`, keeping English and Traditional Chinese (Taiwan) in step.

## Git commits

- Do not add a `Co-Authored-By:` trailer or any other AI attribution line to commit messages or pull request descriptions, including when you only suggest a message for the user to commit.
