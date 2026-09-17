# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Scope

This file covers the `starter/` directory only. `starter/` is its own uv project — separate
`pyproject.toml`, `uv.lock`, and `.venv` from the repository root, and a different Python floor
(`>=3.10` here vs. `>=3.13` at the root) with entirely different dependencies. **Run every
command below from `starter/`**, never from the repo root, or you will resolve against the
wrong environment.

## Commands

```bash
# Run the MCP server
uv run main.py

# Inspect the server interactively (MCP Inspector)
uv run mcp dev main.py

# Tests
uv run pytest                                # all (3 tests)
uv run pytest tests/test_document.py         # one file
uv run pytest -k docx                        # by name pattern
uv run pytest tests/test_document.py::TestBinaryDocumentToMarkdown::test_binary_document_to_markdown_with_pdf
```

No setup step is needed. `uv run` creates and syncs `.venv` from `uv.lock` on demand. The
README's `uv pip install -e .` is *not* required — neither the tests nor the server import the
`app` package (`main.py` resolves `from tools.math import add` via the working directory on
`sys.path`, and pytest resolves the same imports via rootdir insertion), and `pyproject.toml`
declares no `[build-system]`. The
package is in fact not currently installed, and everything passes.

`uv run main.py` uses stdio transport (`mcp.run()` with no transport argument). It prints
nothing and blocks on stdin — that is correct behavior, not a hang. Use `mcp dev main.py` when
you want to actually call tools by hand.

If another project's virtualenv is active (e.g. you came from `mcp/`), `uv run` will warn that
`VIRTUAL_ENV` doesn't match and ignore it — which is what you want. Do **not** "fix" that with
`uv run --active`: it installs this project's dependencies into the *other* project's venv and
breaks it.

There is no linter configured for this project. The root `pyproject.toml` declares a `[tool.ruff]`
section, but ruff is installed in neither venv and its single-quote style contradicts the
double-quoted code here. Don't reformat against it.

No environment variables and no `.env` are involved. This project is an MCP *server*; it never
calls the Claude API and needs no API key.

## Architecture

A deliberate two-layer split:

**`tools/` — plain, MCP-agnostic Python.** No decorators, no `mcp` imports, no framework
awareness. Functions here are ordinary callables, which is precisely what lets the tests import
and exercise them with MCP entirely out of the loop.

**`main.py` — the only MCP-aware module, and the single registration seam.** It constructs
`FastMCP("docs")` and registers each function by call, not by decorator:

```python
mcp.tool()(add)
```

So adding a tool is two steps: write the function in `tools/`, add one line to `main.py`.
Nothing else needs to change.

### Docstrings are prompts, not comments

FastMCP derives the entire wire schema from the function's **signature and docstring**. The
docstring becomes the tool description the model reads when deciding whether to call the tool,
and pydantic `Field(description=...)` defaults become the per-parameter descriptions. A vague
docstring is a functional defect here, not a style issue.

`tools/math.py:4-23` is the reference template — one-line summary, then detail, then a
`When to use:` section, then `Examples:`.

### Document conversion

`tools/document.py:6` wraps `markitdown`: `MarkItDown().convert()` over a `BytesIO`, with
`StreamInfo(extension=file_type)` telling it how to parse. It takes raw `bytes` plus an
extension string and returns markdown text. `docx` and `pdf` support comes from the
`markitdown[docx,pdf]` extras in `pyproject.toml`.

### Tests

`tests/test_document.py` imports `tools.document` directly and runs it against the binary
fixtures in `tests/fixtures/` (`mcp_docs.docx`, `mcp_docs.pdf`). Assertions are intentionally
loose — result is a non-empty `str` containing at least one of `#`, `-`, `*` — because the
exact markdown output depends on markitdown's version. Follow that pattern rather than
asserting on exact converted text.

Imports of `tools.*` resolve via pytest's rootdir `sys.path` insertion (`tests/__init__.py`
exists), so tests pass even when the `app` package is not installed editable — which is
currently the case.

## Current state

`binary_document_to_markdown` is implemented and tested, but it is **not registered** in
`main.py` — only `add` is. The document tool is therefore invisible over MCP. Wiring it up is
the obvious open thread.

Note that **nothing under `starter/` is tracked by git** — the directory is untracked rather
than ignored, so it appears in no diff, log, or commit. Don't rely on git history to understand
how this code evolved, and don't assume a clean `git status` means your changes here are saved.
