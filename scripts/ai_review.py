from __future__ import annotations

import json
import os
import subprocess
import urllib.request

from google import genai


def get_pr_context() -> tuple[int, str]:
    event_path = os.environ["GITHUB_EVENT_PATH"]

    with open(event_path, encoding="utf-8") as f:
        payload = json.load(f)

    pull_request = payload.get("pull_request")

    if pull_request is None:
        raise RuntimeError(
            "This workflow only supports pull_request events."
        )

    return (
        pull_request["number"],
        pull_request["base"]["ref"],
    )


def get_diff(base_ref: str) -> str:
    result = subprocess.run(
        [
            "git",
            "diff",
            f"origin/{base_ref}...HEAD",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    return result.stdout


def generate_review(diff: str) -> str:
    prompt = f"""
# コードレビュー
- あなたはエンジニアです．私が作成しているWebアプリについて，コードレビューをお願いします．

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

    if api_key is None:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )
    client = genai.Client(
        api_key=os.environ["GEMINI_API_KEY"],
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    return response.text or "AI review result was empty."


def post_comment(
    pr_number: int,
    body: str,
) -> None:
    repository = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GITHUB_TOKEN"]

    url = (
        f"https://api.github.com/repos/"
        f"{repository}/issues/{pr_number}/comments"
    )

    payload = json.dumps(
        {
            "body": body,
        }
    ).encode("utf-8")

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

    with urllib.request.urlopen(request):
        pass


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