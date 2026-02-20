Use a subagent to review a specific area of the codebase for security vulnerabilities.

**User to specify (before running this command):**
- The specific files, directories, modules, or features to review
- Any particular security concerns or vulnerability types to focus on

Focus on:
- **SQL Injection & Database Security** — Parameterized queries, prepared statements, ORM safe usage
- **Authentication & Authorization** — Credential handling, session management, access control, privilege escalation
- **XSS & Injection Attacks** — Input validation, output encoding, sanitization, template safety
- **Sensitive Data Exposure** — Hardcoded secrets, API keys, PII handling, proper encryption, password hashing
- **CORS & HTTP Security** — CORS configuration, security headers (CSP, HSTS, X-Frame-Options), HTTPS enforcement
- **Dependency Vulnerabilities** — Outdated packages, known CVEs, vulnerable third-party code
- **Cryptography & Hashing** — Weak algorithms, proper key management, salt usage, random number generation
- **File & Path Security** — Path traversal, unsafe file operations, directory traversal protection
- **Error Handling** — Information disclosure, stack traces in responses, error message leakage

Document findings in `security-issues.md` with:
1. File path and line number
2. Severity (critical, high, medium, low)
3. Vulnerability type
4. Description of the issue
5. Recommended fix

Save the file even if no issues are found.
