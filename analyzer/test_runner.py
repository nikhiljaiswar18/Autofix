import asyncio
import json
import subprocess
import sys
import os
from .llm_client import call_llm, extract_json
from .prompts import get_testgen_prompt
from .code_analyzer import detect_language

TIMEOUT_SECONDS = 5


def run_single_test(code: str, test_code: str, expected) -> dict:
    """Execute a single test case in an isolated subprocess."""
    if test_code == "SKIP":
        return {"status": "skipped", "actual": None, "error": None}

    is_exception_test = isinstance(expected, str) and expected.startswith("RAISES:")

    # Build the runner script
    escaped_code = _escape_triple(code)
    runner = (
        "import json, sys\n"
        "try:\n"
        f"    exec(compile('''{escaped_code}''', '<user_code>', 'exec'), globals())\n"
        f"    result = eval({repr(test_code)})\n"
        "    print(json.dumps({'status': 'ok', 'result': result}, default=str))\n"
        "except Exception as e:\n"
        "    print(json.dumps({'status': 'error', 'exception': type(e).__name__, 'message': str(e)}))\n"
    )

    try:
        proc = subprocess.run(
            [sys.executable, "-c", runner],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )

        output = proc.stdout.strip()
        if not output:
            stderr = proc.stderr.strip()[:200]
            return {"status": "error", "actual": None, "error": stderr or "No output"}

        data = json.loads(output)

        if is_exception_test:
            expected_exc = expected.split(":", 1)[1]
            if data["status"] == "error" and data["exception"] == expected_exc:
                return {"status": "pass", "actual": f"RAISES:{data['exception']}", "error": None}
            elif data["status"] == "error":
                return {"status": "fail", "actual": f"RAISES:{data['exception']}", "error": data.get("message")}
            else:
                return {"status": "fail", "actual": repr(data["result"]), "error": f"Expected {expected_exc} but got a result"}

        if data["status"] == "error":
            return {"status": "error", "actual": None, "error": f"{data['exception']}: {data['message']}"}

        # Compare results
        actual = data["result"]
        if _values_match(actual, expected):
            return {"status": "pass", "actual": repr(actual), "error": None}
        else:
            return {"status": "fail", "actual": repr(actual), "error": f"Expected {repr(expected)}"}

    except subprocess.TimeoutExpired:
        return {"status": "error", "actual": None, "error": "Timeout (>5s) — possible infinite loop"}
    except json.JSONDecodeError:
        return {"status": "error", "actual": None, "error": "Could not parse test output"}
    except Exception as e:
        return {"status": "error", "actual": None, "error": str(e)[:200]}


def _escape_triple(code: str) -> str:
    """Escape triple quotes in user code for safe embedding."""
    return code.replace("\\", "\\\\").replace("'''", "\\'\\'\\'")


def _values_match(actual, expected) -> bool:
    """Flexible comparison of actual vs expected values."""
    if actual == expected:
        return True
    # Compare as strings as fallback
    if str(actual) == str(expected):
        return True
    # Numeric tolerance
    try:
        if abs(float(actual) - float(expected)) < 0.001:
            return True
    except (TypeError, ValueError):
        pass
    return False


async def generate_and_run_tests(filename: str, code: str, progress_callback=None) -> dict:
    """Generate test cases via LLM, then execute them."""
    language = detect_language(filename)

    async def send_progress(step, detail):
        if progress_callback:
            await progress_callback(step, "running", detail)

    await send_progress("generate", "Generating test cases...")

    # Step 1: Ask LLM to generate test cases
    user_msg = f"Generate test cases for this {language} file:\n\n```{language}\n{code}\n```"
    raw = await call_llm(get_testgen_prompt(language), user_msg, max_tokens=4096)
    parsed = extract_json(raw)

    test_cases = parsed.get("test_cases", [])
    suggestions = parsed.get("suggestions", [])

    if not test_cases:
        return {
            "filename": filename,
            "language": language,
            "test_cases": [],
            "suggestions": suggestions or ["Could not generate test cases. Try a different file."],
            "summary": {"total": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0},
        }

    await send_progress("execute", f"Running {len(test_cases)} test cases...")

    # Step 2: Execute each test case (Python only)
    results = []
    for i, tc in enumerate(test_cases):
        test_code = tc.get("test_code", "SKIP")
        expected = tc.get("expected")

        if language == "python" and test_code != "SKIP":
            # Run in subprocess
            outcome = await asyncio.to_thread(run_single_test, code, test_code, expected)
        else:
            # Non-Python or SKIP: mark as skipped
            outcome = {"status": "skipped", "actual": None, "error": None}

        results.append({
            "function": tc.get("function", "unknown"),
            "description": tc.get("description", ""),
            "category": tc.get("category", "normal"),
            "test_code": test_code,
            "expected": str(expected) if expected is not None else "None",
            "actual": outcome["actual"],
            "status": outcome["status"],
            "error": outcome["error"],
            "notes": tc.get("notes", ""),
        })

        if progress_callback:
            done = i + 1
            await progress_callback("execute", "running", f"Running test {done}/{len(test_cases)}...")

    # Summary
    summary = {
        "total": len(results),
        "passed": sum(1 for r in results if r["status"] == "pass"),
        "failed": sum(1 for r in results if r["status"] == "fail"),
        "errors": sum(1 for r in results if r["status"] == "error"),
        "skipped": sum(1 for r in results if r["status"] == "skipped"),
    }

    await send_progress("complete", "Test execution complete!")

    return {
        "filename": filename,
        "language": language,
        "test_cases": results,
        "suggestions": suggestions,
        "summary": summary,
    }