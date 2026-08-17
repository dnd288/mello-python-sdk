# Mello MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a full read/write MCP server for the existing Mello Python SDK.

**Architecture:** Create a focused `mello/mcp_server.py` module that builds a FastMCP app and exposes one tool per existing `MelloClient` method. Tool wrappers serialize SDK dataclasses into JSON-compatible responses and preserve omitted versus explicit nullable update values.

**Tech Stack:** Python 3.8+, `mcp.server.fastmcp.FastMCP`, existing `requests` SDK, `pytest`.

---

### Task 1: Serialization And Configuration Helpers

**Files:**
- Create: `tests/test_mcp_server.py`
- Create: `mello/mcp_server.py`

- [ ] **Step 1: Write failing tests**

Add tests for recursive serialization, ISO date parsing, and environment-driven client creation in `tests/test_mcp_server.py`.

- [ ] **Step 2: Verify tests fail**

Run: `pytest tests/test_mcp_server.py -q`
Expected: FAIL because `mello.mcp_server` does not exist.

- [ ] **Step 3: Implement helpers**

Create `mello/mcp_server.py` with `_serialize`, `_parse_datetime`, `_client_from_env`, and `main` placeholders.

- [ ] **Step 4: Verify tests pass**

Run: `pytest tests/test_mcp_server.py -q`
Expected: PASS for helper tests.

### Task 2: MCP Tool Wrappers

**Files:**
- Modify: `tests/test_mcp_server.py`
- Modify: `mello/mcp_server.py`

- [ ] **Step 1: Write failing tests**

Add tests that call registered tool functions directly with a fake client for representative read, create, update, nullable update, delete, reorder, move, and search operations.

- [ ] **Step 2: Verify tests fail**

Run: `pytest tests/test_mcp_server.py -q`
Expected: FAIL because `create_mcp_server` and tools are not implemented.

- [ ] **Step 3: Implement tools**

Add `create_mcp_server(client_factory=None)` and register all SDK-backed tools with FastMCP.

- [ ] **Step 4: Verify tests pass**

Run: `pytest tests/test_mcp_server.py -q`
Expected: PASS.

### Task 3: Packaging And Documentation

**Files:**
- Modify: `pyproject.toml`
- Modify: `README.md`

- [ ] **Step 1: Write failing packaging/doc checks**

Add tests or assertions that the console script and optional MCP extra are declared.

- [ ] **Step 2: Verify checks fail**

Run: `pytest tests/test_mcp_server.py -q`
Expected: FAIL until package metadata is updated.

- [ ] **Step 3: Update packaging and docs**

Add `[project.scripts]`, append `mcp` optional dependency, and document `MELLO_API_KEY`, `MELLO_BASE_URL`, `MELLO_TIMEOUT`, and `mello-mcp-server`.

- [ ] **Step 4: Verify checks pass**

Run: `pytest tests/test_mcp_server.py -q`
Expected: PASS.

### Task 4: Full Verification

**Files:**
- All touched files

- [ ] **Step 1: Run unit tests**

Run: `pytest -q`
Expected: PASS for non-integration tests.

- [ ] **Step 2: Run quality checks if available**

Run: `python -m compileall mello`
Expected: PASS.

- [ ] **Step 3: Review git diff**

Run: `git diff -- mello/mcp_server.py tests/test_mcp_server.py pyproject.toml README.md docs/superpowers`
Expected: only MCP server, tests, docs, and plan/spec changes.
