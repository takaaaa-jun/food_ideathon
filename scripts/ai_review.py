from __future__ import annotations

import json
import os
import random
import subprocess
import time
import urllib.error
import urllib.request

from google import genai
from google.genai.errors import ServerError


def get_pr_context() -> tuple[int, str]:
    event_path = os.environ["GITHUB_EVENT_PATH"]

    with open(event_path, encoding="utf-8") as f:
        payload = json.load(f)

    pull_request = payload.get("pull_request")

    if pull_request is None:
        raise RuntimeError("This workflow only supports pull_request events.")

    pr_number = pull_request["number"]
    base_ref = pull_request["base"]["ref"]

    return pr_number, base_ref


def get_diff(base_ref: str) -> str:
    # In CI this fetches remote base; for local/docker testing,
    # set SKIP_GIT_FETCH=1 to avoid network fetch.
    if not os.environ.get("SKIP_GIT_FETCH"):
        subprocess.run(
            ["git", "fetch", "origin", base_ref],
            check=True,
            capture_output=True,
            text=True,
        )

    left = f"origin/{base_ref}"
    if os.environ.get("SKIP_GIT_FETCH"):
        # when skipping fetch, fall back to local ref
        left = base_ref

    base = subprocess.run(
        ["git", "merge-base", left, "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    result = subprocess.run(
        ["git", "diff", f"{base}...HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )

    return result.stdout


def generate_review(diff: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return "GEMINI_API_KEY / GOOGLE_API_KEY is not configured."

    prompt = f"""
# コードレビュー
- あなたはエンジニアです.
- 私が作成しているWebアプリについて, コードレビューをお願いします.

## 出力要件
- 以下の**差分**をレビューしてください．

### 観点:
- バグの可能性
- 可読性
- 命名
- 責務分離
- 保守性
- Flaskアプリとしての設計

### その他の要件
- 重大な問題がなければ，「重大な問題は見つかりませんでした」と回答してください．

### 差分:

{diff}
"""

    client = genai.Client(api_key=api_key)

    max_attempts = 4
    base_sleep_seconds = 2.0

    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            text = response.text or "AI review result was empty."
            return text

        except ServerError as e:
            last_error = e
            if attempt == max_attempts:
                break

            sleep_seconds = base_sleep_seconds * (2 ** (attempt - 1))
            sleep_seconds += random.uniform(0.0, 1.0)
            print(
                f"""
                Gemini API is temporarily unavailable
                (attempt {attempt}/{max_attempts}).
                """
                f"Retrying in {sleep_seconds:.1f} seconds..."
            )
            time.sleep(sleep_seconds)

    return (
        """
        Gemini API was temporarily unavailable, so the AI review could not be generated
        """
        f"after {max_attempts} attempts.\n\n"
        f"Last error: {last_error}"
    )


def post_comment(pr_number: int, body: str) -> None:
    repository = os.environ["GITHUB_REPOSITORY"]
    token = os.environ.get("GITHUB_TOKEN")

    if not token:
        print("GITHUB_TOKEN is not set. Skipping posting PR comment.")
        return

    url = f"https://api.github.com/repos/{repository}/issues/{pr_number}/comments"
    payload = json.dumps({"body": body}).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request):
            pass
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        # Handle common CI permission errors (e.g. token from forked PRs)
        if e.code == 403:
            print(
                "Failed to post PR comment: HTTP 403 Forbidden.\n"
                "This usually means the provided token cannot access the resource"
                "(e.g. GITHUB_TOKEN lacks permissions"
                "or the run is from a forked PR).\n"
                "If this is running in GitHub Actions, consider granting"
                "`issues: write`/`pull-requests: write` permissions in the workflow,\n"
                "or use a personal access token stored in"
                "repository secrets for cross-repo/forked-PR comments.\n"
                f"Response body:\n{error_body}"
            )
            return

        raise RuntimeError(
            f"Failed to post PR comment: HTTP {e.code} {e.reason}\n{error_body}"
        ) from e


def main() -> None:
    pr_number, base_ref = get_pr_context()

    diff = get_diff(base_ref)

    if not diff.strip():
        print("No diff found.")
        return

    review = generate_review(diff)

    post_comment(
        pr_number,
        f"## AI Code Review\n\n{review}",
    )


if __name__ == "__main__":
    main()
