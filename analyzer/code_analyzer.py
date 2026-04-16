import asyncio
import json
import os
from .llm_client import call_llm, extract_json
from .prompts import (
    get_bug_prompt,
    get_security_prompt,
    get_style_prompt,
    get_fix_prompt,
    SUPPORTED_LANGUAGES,
)


def detect_language(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return SUPPORTED_LANGUAGES.get(ext, "python")


def calculate_grade(issues: list) -> dict:
    """Calculate A-F code quality grade based on issues."""
    severity_weights = {"critical": 10, "warning": 3, "info": 1}
    penalty = sum(severity_weights.get(i.get("severity", "info"), 1) for i in issues)

    if penalty == 0:
        grade, score, color = "A+", 100, "#3fb950"
    elif penalty <= 5:
        grade, score, color = "A", 90, "#3fb950"
    elif penalty <= 15:
        grade, score, color = "B", 75, "#58a6ff"
    elif penalty <= 30:
        grade, score, color = "C", 60, "#d29922"
    elif penalty <= 50:
        grade, score, color = "D", 40, "#f0883e"
    else:
        grade, score, color = "F", max(10, 100 - penalty), "#f85149"

    return {"grade": grade, "score": score, "color": color, "penalty": penalty}


async def analyze_code(filename: str, code: str, progress_callback=None) -> dict:
    """Run full analysis pipeline: bugs + security + style + auto-fix."""
    language = detect_language(filename)

    async def send_progress(step, status, detail=""):
        if progress_callback:
            await progress_callback(step, status, detail)

    await send_progress("bugs", "running", "Scanning for bugs...")

    # Phase 1: Run analysis calls with staggered delays to avoid rate limits
    user_msg = f"Analyze this {language} file:\n\n```{language}\n{code}\n```"

    async def run_bug_analysis():
        result = await call_llm(get_bug_prompt(language), user_msg)
        await send_progress("bugs", "done", "Bug scan complete")
        return result

    async def run_security_analysis():
        await asyncio.sleep(2)
        await send_progress("security", "running", "Checking security vulnerabilities...")
        result = await call_llm(get_security_prompt(language), user_msg)
        await send_progress("security", "done", "Security scan complete")
        return result

    async def run_style_analysis():
        await asyncio.sleep(4)
        await send_progress("style", "running", "Reviewing code style...")
        result = await call_llm(get_style_prompt(language), user_msg)
        await send_progress("style", "done", "Style review complete")
        return result

    bug_raw, security_raw, style_raw = await asyncio.gather(
        run_bug_analysis(), run_security_analysis(), run_style_analysis()
    )

    # Parse results
    bug_result = extract_json(bug_raw)
    security_result = extract_json(security_raw)
    style_result = extract_json(style_raw)

    # Combine all issues
    all_issues = []
    for result in [bug_result, security_result, style_result]:
        if "issues" in result:
            all_issues.extend(result["issues"])

    # Count by type
    summary = {
        "bugs": sum(1 for i in all_issues if i.get("type") == "bug"),
        "security": sum(1 for i in all_issues if i.get("type") == "security"),
        "style": sum(1 for i in all_issues if i.get("type") == "style"),
    }
    summary["total"] = summary["bugs"] + summary["security"] + summary["style"]

    # Phase 2: Generate fixed code (only if issues found)
    fixed_code = code
    explanation = "No issues found — code looks clean!"

    if all_issues:
        await send_progress("fix", "running", "Generating fixed code...")
        issues_text = json.dumps(all_issues, indent=2)
        fix_prompt = (
            f"Here is the {language} code:\n\n```{language}\n{code}\n```\n\n"
            f"Here are the issues found:\n\n```json\n{issues_text}\n```\n\n"
            f"Fix ALL issues and return the corrected code."
        )
        fix_raw = await call_llm(get_fix_prompt(language), fix_prompt, max_tokens=8192)
        fix_result = extract_json(fix_raw)

        if "fixed_code" in fix_result:
            fixed_code = fix_result["fixed_code"]
            explanation = fix_result.get("explanation", "All issues have been fixed.")
        elif "error" not in fix_result:
            fixed_code = code
            explanation = "Could not generate fixed code. Please review the issues manually."

        await send_progress("fix", "done", "Code fixed!")

    await send_progress("complete", "done", "Analysis complete!")

    # Sort issues: critical first, then warning, then info
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    all_issues.sort(key=lambda x: severity_order.get(x.get("severity", "info"), 3))

    # Calculate grade
    grade_info = calculate_grade(all_issues)

    return {
        "original_file": filename,
        "language": language,
        "summary": summary,
        "grade": grade_info,
        "issues": all_issues,
        "fixed_code": fixed_code,
        "explanation": explanation,
    }
