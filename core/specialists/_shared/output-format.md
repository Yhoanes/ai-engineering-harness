# Output Format Rules

All specialist outputs must follow these formatting standards.

## General

- Use Markdown for all documentation and reports.
- Use YAML for structured data and configuration.
- Use code blocks with language identifiers for code snippets.

## Reports and Analysis

- Start with a clear summary of what was done or found.
- Use tables for structured comparisons.
- Use bullet lists for findings and recommendations.
- Include file paths as clickable references when applicable.
- Separate sections with headers for readability.

## Implementation Output

- Show what files were modified and why.
- Include relevant diffs or change summaries.
- Report test results with pass/fail counts.
- Report linting results.

## Review Output

- List each finding with a unique identifier (e.g., CR-01, SR-01).
- Classify findings as: blocker, warning, or informational.
- State the decision clearly: APPROVED, CHANGES_REQUESTED, or FLAGGED.
- Do not modify files during review — reviews are read-only.

## Evidence

- Evidence must be written to persistent files, not just conversation.
- Evidence files must be referenced in the Task Contract.
- Include timestamps, reviewer identifiers, and validator results.
