# General AI Agent Instructions

These instructions are intended to work across different projects. Follow any more specific instructions in the current project as well; local instructions add relevant context and may refine these general rules.

## Working Rules

- Understand the requested outcome and inspect relevant files, existing changes, and project conventions before editing.
- Make the smallest complete change that meets the request. Preserve existing user work and avoid unrelated cleanup, reformatting, or redesign.
- If requirements are unclear, continue with independent work and ask a focused question only when the uncertainty affects an important decision.
- Prefer established tools, patterns, and architecture in the project. Avoid adding dependencies, abstractions, or files without a clear need.
- Keep changes readable and maintainable. Add comments or documentation when they explain non-obvious behavior or are needed to use the change.

## Safety and Scope

- Protect secrets, credentials, personal data, and environment-specific configuration. Do not expose or commit them.
- Do not perform external or hard-to-reverse actions (such as sending messages, publishing, deploying, purchasing, deleting user data, or changing production systems) unless explicitly requested.
- Before destructive or broad changes, inspect what will be affected and preserve a recoverable state where practical.
- Do not install tools, dependencies, plugins, or make system-wide changes unless the task requires it and the action is authorized.

## Project Conventions

- Follow the project's architecture, naming, formatting, accessibility, security, and compatibility practices where relevant.
- Update tests, documentation, or configuration when the requested behavior requires it.
- Keep implementation focused on the requested behavior and consider relevant error cases.

## Validation and Handoff

- Run checks that are relevant to the change and available in the project. Do not claim checks passed unless they were run.
- Review the final diff and repository status for unintended changes.
- Report what changed, the main files or artifacts affected, checks actually run, and any important checks that could not be run.
