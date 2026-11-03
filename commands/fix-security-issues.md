Read security-issues.md and fix the reported vulnerabilities.

Prioritize by severity (critical → high → medium → low).

For each security issue:
1. Locate the vulnerable code
2. Understand the security risk
3. Implement the recommended fix or your own solution
4. Test the fix to ensure it resolves the vulnerability without breaking functionality
5. Do not commit: leave the changes in the working tree and suggest a commit message for me

After all issues are addressed:
1. Delete security-issues.md
2. Run full test suite to ensure no regressions
3. Report which issues were fixed and any that were deferred/skipped with explanation (including rationale for deferring)
