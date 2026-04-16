LANGUAGE_SPECIFIC = {
    "python": {
        "bugs": "- Incorrect use of mutable default arguments\n- Variable shadowing and scope issues",
        "security": "- Command injection (os.system, subprocess with shell=True)\n- Insecure deserialization (pickle.loads on untrusted data)\n- Code injection (eval, exec on user input)",
        "style": "- PEP 8 violations (naming, spacing, line length)\n- Missing or incorrect type hints",
    },
    "javascript": {
        "bugs": "- Prototype pollution\n- Callback hell / unhandled promises\n- == vs === comparison issues\n- Variable hoisting bugs",
        "security": "- DOM-based XSS (innerHTML, document.write)\n- Prototype pollution\n- Insecure use of eval() or Function()\n- Missing CSRF protection",
        "style": "- ESLint common rule violations\n- var vs let/const usage\n- Missing async/await error handling",
    },
    "java": {
        "bugs": "- NullPointerException risks\n- Resource leaks (unclosed streams)\n- Incorrect equals/hashCode\n- ConcurrentModificationException",
        "security": "- SQL injection via string concatenation\n- Insecure deserialization (ObjectInputStream)\n- XXE injection in XML parsing\n- Hardcoded cryptographic keys",
        "style": "- Java naming conventions violations\n- Missing final on immutable fields\n- Raw type usage instead of generics",
    },
    "cpp": {
        "bugs": "- Buffer overflow / out-of-bounds access\n- Memory leaks (missing delete/free)\n- Use-after-free / dangling pointers\n- Integer overflow\n- Uninitialized variables",
        "security": "- Format string vulnerabilities\n- Buffer overflow via strcpy/gets\n- Use of unsafe C functions\n- Missing bounds checking",
        "style": "- Modern C++ usage (smart pointers over raw)\n- const correctness\n- RAII violations",
    },
    "go": {
        "bugs": "- Unchecked error returns\n- Goroutine leaks\n- Race conditions on shared state\n- Nil pointer dereference",
        "security": "- SQL injection\n- Command injection via os/exec\n- Insecure TLS configuration\n- Hardcoded secrets",
        "style": "- Go naming conventions (exported vs unexported)\n- Error wrapping with fmt.Errorf\n- Unnecessary else after return",
    },
}

SUPPORTED_LANGUAGES = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "javascript",
    ".tsx": "javascript",
    ".java": "java",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".c": "cpp",
    ".h": "cpp",
    ".hpp": "cpp",
    ".go": "go",
}


def get_bug_prompt(language: str) -> str:
    lang_extra = LANGUAGE_SPECIFIC.get(language, {}).get("bugs", "")
    return f"""You are an expert {language} bug detector. Analyze the given {language} code and identify ALL bugs including:
- Syntax errors
- Logical bugs (off-by-one, wrong conditions, infinite loops)
- Runtime errors (division by zero, null/None access, index out of range)
- Type errors and incorrect return values
- Unhandled exceptions
{lang_extra}

Respond ONLY with valid JSON in this exact format:
{{
  "issues": [
    {{
      "type": "bug",
      "severity": "critical|warning|info",
      "line": <line_number>,
      "description": "<what the bug is>",
      "fix": "<how to fix it>"
    }}
  ]
}}

If no bugs found, return: {{"issues": []}}
Do NOT include any text outside the JSON."""


def get_security_prompt(language: str) -> str:
    lang_extra = LANGUAGE_SPECIFIC.get(language, {}).get("security", "")
    return f"""You are an expert {language} security auditor. Analyze the given {language} code for security vulnerabilities including:
- SQL injection
- Code injection
- Hardcoded secrets, passwords, API keys
- Path traversal vulnerabilities
- Missing input validation
- Insecure file operations
- SSRF vulnerabilities
- XSS if web-related code
{lang_extra}

Respond ONLY with valid JSON in this exact format:
{{
  "issues": [
    {{
      "type": "security",
      "severity": "critical|warning|info",
      "line": <line_number>,
      "description": "<what the vulnerability is>",
      "fix": "<how to fix it>"
    }}
  ]
}}

If no security issues found, return: {{"issues": []}}
Do NOT include any text outside the JSON."""


def get_style_prompt(language: str) -> str:
    lang_extra = LANGUAGE_SPECIFIC.get(language, {}).get("style", "")
    return f"""You are an expert {language} code reviewer. Analyze the given {language} code for style and quality issues including:
- Naming convention violations
- Code smells (too many arguments, deep nesting, god functions)
- DRY violations (repeated code blocks)
- Unused imports or variables
- Poor naming conventions
- Missing error handling where appropriate
- Anti-patterns
{lang_extra}

Respond ONLY with valid JSON in this exact format:
{{
  "issues": [
    {{
      "type": "style",
      "severity": "critical|warning|info",
      "line": <line_number>,
      "description": "<what the style issue is>",
      "fix": "<how to fix it>"
    }}
  ]
}}

If no style issues found, return: {{"issues": []}}
Do NOT include any text outside the JSON."""


def get_fix_prompt(language: str) -> str:
    return f"""You are an expert {language} developer. You are given a {language} code file and a list of issues found in it.

Apply ALL the fixes to produce a corrected version of the code. Rules:
- Fix every issue listed
- Preserve the original code structure and logic as much as possible
- Do NOT add unnecessary changes beyond the fixes
- Keep all comments and docstrings intact
- Maintain the same import style

Respond ONLY with valid JSON in this exact format:
{{
  "fixed_code": "<the entire corrected file as a string>",
  "explanation": "<brief summary of all changes made>"
}}

Do NOT include any text outside the JSON."""


def get_testgen_prompt(language: str) -> str:
    return f"""You are an expert {language} test engineer. Analyze the given {language} code and generate comprehensive test cases for EVERY function/method found.

For each function, generate:
- 2-3 normal cases (typical valid inputs)
- 1-2 edge cases (empty input, zero, None/null, boundary values)
- 1 error/exception case (invalid input that should be handled)

IMPORTANT RULES:
- Each test must call exactly ONE function with concrete arguments
- For Python: the test_code must be a single expression that returns a value (use the function directly, no print/assert)
- If a function requires complex setup (database, file I/O, network), set test_code to "SKIP" and explain in notes
- The expected output must be the exact return value
- For functions that return None, expected should be null
- For functions that should raise an exception, set expected to "RAISES:<ExceptionType>" (e.g., "RAISES:ValueError")

Respond ONLY with valid JSON in this exact format:
{{
  "test_cases": [
    {{
      "function": "<function name being tested>",
      "description": "<what this test checks>",
      "category": "normal|edge|error",
      "test_code": "<code to execute, e.g. add(2, 3)>",
      "expected": "<expected return value or RAISES:ExceptionType>",
      "notes": "<optional suggestion for improvement>"
    }}
  ],
  "suggestions": [
    "<overall suggestion about code testability or improvements>"
  ]
}}

Do NOT include any text outside the JSON."""
