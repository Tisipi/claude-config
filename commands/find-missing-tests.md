Use a subagent to review all code in the project and identify missing test cases.

For each file or module, identify:
- Unit tests that should exist but don't
- Edge cases that aren't covered
- Integration tests that should be added
- Error handling scenarios that need tests
- Important business logic that lacks test coverage

Be specific and concrete. Do not hallucinate or suggest vague tests. Think carefully about what should actually be tested based on the code logic.

Document findings in `missing-tests.md` with:
1. File path
2. Specific test case description
3. What scenario it should cover
4. Expected test behavior

Save the file even if no gaps are found.
