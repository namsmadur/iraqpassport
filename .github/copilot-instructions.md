# AI Coding Agent Instructions

## Working Style

- Understand the existing code before making changes.
- Make the smallest change that fully solves the request.
- Preserve existing user changes and do not overwrite unrelated work.
- Follow the project's existing architecture, naming, formatting, and dependency conventions.
- Do not invent abstractions unless they remove real complexity.
- Keep explanations concise and technically precise.
- Ask a clarifying question only when the requirement cannot be inferred safely.

## Before Editing

1. Identify the relevant file, symbol, failing test, or command.
2. Read the nearby implementation and related tests.
3. State a brief hypothesis about the cause or intended behavior.
4. Choose the smallest test or validation that can disprove the hypothesis.
5. Make the change only after understanding the controlling code path.

## Implementation Rules

- Fix root causes instead of masking symptoms.
- Keep changes focused and avoid unrelated refactoring.
- Reuse existing utilities and patterns.
- Do not add unnecessary comments.
- Do not add secrets, credentials, tokens, or environment-specific configuration.
- Do not modify generated files unless the project requires it.
- Do not commit changes unless explicitly requested.

## Testing

After every substantive edit:

1. Run the narrowest relevant test or validation.
2. Fix failures in the same area before expanding scope.
3. Run formatting, linting, type checking, or tests appropriate to the project.
4. Check whitespace and review the final diff.
5. Clearly report what passed and what could not be run.

Never claim a test passed unless it was actually executed.

## Safety

- Never use destructive commands such as hard reset or force deletion without explicit approval.
- Do not revert changes you did not make.
- Treat unrelated working-tree changes as user-owned.
- Do not expose private data in responses.
- Do not change deployment infrastructure, production settings, or database data without explicit confirmation.

## Final Response

Summarize:

- What changed
- Which files changed
- Validation commands that were run
- Any remaining risks or blockers
- Any required follow-up steps
