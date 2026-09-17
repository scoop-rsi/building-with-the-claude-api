# Findings (13), highest severity first

## High

### *core/tools.py:102*

The except handler reads tool_output, which is unbound whenever `client.call_tool()` itself raised,
so the handler dies with `UnboundLocalError` and takes the whole agent loop down.

**Reproduced**: a client whose call_tool raises `RuntimeError("network down")` yields
`UnboundLocalError: cannot access local variable 'tool_output'`. Separately, the status expression
is wrong in this branch — on an exception the result should unconditionally be "error", but as
written it would report "success" while shipping `{"error": ...}` to Claude as a normal result.

### *core/cli_chat.py:58*

`_process_command` indexes `words[1]` unguarded, so typing `/format` (or any bare command) raises
`IndexError`, which propagates out of `CliApp.run` and kills the REPL. It also never checks that
command is in the server's prompt list, so `/bogus x` raises from session.`get_prompt`, and it
hardcodes `{"doc_id": ...}` so any future prompt with a differently-named argument breaks.

## Medium

### *core/cli.py:98*

The len(parts) >= 2 branch treats self.resources as a list of dicts ("id" in resource, resource["id"]), but update_resources is fed list_docs_ids(), i.e. a list of plain strings (the two other branches at lines 60 and 90 correctly treat them as strings). Today this means typing /format dep + Tab silently offers no completions ("id" in "deposition.md" is False); add a doc whose id contains the substring id (e.g. guide.md) and it becomes TypeError: string indices must be integers.

### *core/cli.py:34*

`prompt.arguments[0].name` assumes every prompt has at least one argument. `Prompt.arguments` is
`list | None` in the MCP SDK, so a zero-arg prompt on the server makes the autosuggester raise
`TypeError/IndexError` inside prompt_toolkit's render path on every keystroke after /name.

### *core/cli.py:209*

The REPL only catches KeyboardInterrupt. Pressing Ctrl-D raises `EOFError` and exits with a
traceback (skipping the AsyncExitStack clean shutdown of the child server), and any exception from
`agent.run` (API error, the IndexError in #2, a tool failure) terminates the session instead of
printing an error and re-prompting.

### *core/chat.py:24*

The agent loop is while True with no iteration cap or token/time budget: a model that keeps
emitting tool_use (e.g. edit_document whose old_str never matches, so it retries forever) loops
indefinitely burning API spend with no way out but Ctrl-C. It also re-calls
`ToolManager.get_all_tools()` (a list_tools round-trip per client) on every single iteration, and
`claude_service.chat()` is a blocking sync call made from inside the async event loop.

### *mcp_server.py:75*

The new format prompt ends mid-sentence: "After the document has been reformatted...". The literal
ellipsis is shipped to the model as the final instruction, so the intended completion/stop condition
is simply missing. The two stale # TODO comments around it (lines 58 and 82) are now misleading —
line 58's TODO sits directly above its own implementation, and the line 82 TODO is the summarize
prompt that the README already advertises (see #9).

### *README.md:16*

The *.env* setup step lists only `ANTHROPIC_API_KEY`, but main.py:19 asserts `CLAUDE_MODEL` is
non-empty. A reader who follows the README exactly gets "AssertionError: Error: CLAUDE_MODEL cannot
be empty". Update *.env* on first run. `CLAUDE_MODEL` is never mentioned anywhere in the README.

### *main.py:31*

The `USE_UV` env var that selects `uv run mcp_server.py` vs `python mcp_server.py` is undocumented
(it appears nowhere but this line). Following README Option 1 (`uv run main.py` without exporting
`USE_UV=1`) spawns the server with bare python, which fails with
`ModuleNotFoundError: No module named 'mcp'` unless the venv happens to be on PATH. Related
inconsistency at line 46: extra server scripts from `sys.argv` always hardcode `command="uv"`,
ignoring `USE_UV` entirely, so the non-uv path can never load additional servers. Both also rely on
*mcp_server.py* being resolvable from the process CWD.

## Low

### *README.md:91*

Usage documents > `/summarize deposition.md`, but the only prompt the server registers is format;
summarize is still a TODO. Running the documented example raises from `get_prompt` and (per #5)
kills the CLI.

### *README.md:7*

"Python 3.9+" contradicts pyproject.toml (requires-python = ">=3.10") and the code itself:
runtime-evaluated PEP 604 annotations such as `env: dict | None = None` (mcp_client.py:18) and
`Literal["success"] | Literal["error"]` (core/tools.py:42) raise TypeError on 3.9. Line 63's
`pip install ... "mcp[cli]==1.8.0"` also pins == where *pyproject.toml* declares `>=1.8.0`, so the
two install paths can resolve different SDK versions.

### *main.py:19*

Required-config validation uses bare assert, which is stripped under `python -O/PYTHONOPTIMIZE=1`; the app then proceeds with `model=""` and fails much later with an opaque API error. Raise SystemExit/ValueError instead. Also note `anthropic_api_key` is validated but never passed to `Anthropic()` — it works only via the implicit `load_dotenv() → os.environ` side effect.

### *mcp_client.py:74*

`read_resource` does `result.contents[0]` with no emptiness check, so a resource that returns no contents raises IndexError rather than the intended ValueError on the line below. Minor related nits in the same file: call_tool's return type is annotated CallToolResult | None although the session never returns None (which is what forces the dead if tool_output checks in core/tools.py), and cleanup() closes self._exit_stack without recreating it, so an MCPClient instance can never be reconnected after use.

## Other

Also worth a quick cleanup (not a code defect): mcp/failed.log and mcp/cli_project.zip are untracked build/debug artifacts not covered by mcp/.gitignore, and core/tools.py:10 annotates get_all_tools as -> list[Tool] while it actually returns a list of Anthropic-shaped dicts.
