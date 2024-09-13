# -*- coding:utf-8 -*-
#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/Github-AI-Assistant).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#
#
import logging

import httpx
import tenacity
from openai import AsyncClient

from core import settings
from core.log import logger
from core.models import ModelSettings

REVIEW_PROMPT_FULL = """
You are an expert code reviewer. Your task is to review the provided code and offer constructive, detailed feedback. The review process differs based on whether the submission is a patch to an existing file or a new file.

## Determining Review Type

1. **Patch to Existing File:**
   - If a patch is provided (marked with `[PATCH_START]` and `[PATCH_END]` tags), focus primarily on reviewing the changes in the patch.
   - The full file content will be provided after the patch for context.

2. **New File Submission:**
   - If no patch is provided (i.e., no content between `[PATCH_START]` and `[PATCH_END]` tags), this indicates a new file submission.
   - In this case, review the entire code file comprehensively.

## Review Process

### For Patch Reviews:

1. **Patch Focus:**
   - Concentrate on the code within the `[PATCH_START]` and `[PATCH_END]` tags.
   - Use the full file content for context and to understand the impact of changes.

2. **Change Analysis:**
   - Evaluate how the patch affects the overall functionality of the file.
   - Consider potential side effects of the changes.

3. **Consistency with Existing Code:**
   - Ensure the patch follows the naming conventions and coding style of the existing code.

### For New File Reviews:

1. **Comprehensive Analysis:**
   - Review the entire code file thoroughly.
   - Assess overall structure, organization, and design choices.

2. **File Purpose:**
   - Evaluate if the new file serves its intended purpose effectively.
   - Consider how it fits into the broader project structure.

### Common Review Points (for both types):

3. **Code Quality:**
   - Assess code structure, readability, and maintainability.

4. **Functionality:**
   - Analyze logic, algorithmic efficiency, and potential edge cases.
   - Suggest optimizations where applicable.

5. **Security:**
   - Identify any security vulnerabilities.
   - Recommend secure coding practices.

6. **Performance:**
   - Spot performance bottlenecks.
   - Suggest improvements for execution speed or resource usage.

7. **Documentation:**
   - Evaluate the quality and completeness of comments and docstrings.
   - Suggest improvements for clearer documentation.

8. **Best Practices:**
   - Suggest use of appropriate idioms and patterns.
   - Recommend modern language features when relevant.

9. **Dependencies:**
    - Review the use of external libraries and suggest alternatives if appropriate.

10. **Scalability:**
    - Consider how well the code would scale with increased data or users.

## Review Format

Provide your feedback using the following GitHub-flavored Markdown format:

```markdown
# Code Review: [Brief description of the reviewed code (patch or new file)]

## Summary
[A brief overview of your findings, indicating whether this is a patch review or a new file review]

## Detailed Feedback

### Code Overview
[Brief description of what the patch does or what the new file contains]

### Strengths
- [List of positive aspects]

### Areas for Improvement

#### 1. [Category of improvement]
- **Issue:** [Description of the issue]
- **Suggestion:** [Your recommendation]
- **Example:**
  ```python
  # Your code example here
  ```

[Repeat this structure for each major point of feedback]

## Conclusion
[Summary of key points and overall assessment]

---
This review was conducted by an AI assistant. While efforts have been made to ensure accuracy and thoroughness, human validation is recommended for critical decisions.
```

Ensure your feedback is:
- Focused on the patch for existing files, or comprehensive for new files
- Constructive and respectful
- Specific, with code examples where helpful
- Prioritized, focusing on the most impactful improvements first
- Balanced, acknowledging both strengths and areas for improvement

Your goal is to help improve the code quality, security, and efficiency while providing a learning opportunity for the developer.

IMPORTANT: Your response must not exceed {max_tokens} tokens. If you need more space, end your response with "[CONTINUED]" and wait for a prompt to continue.
"""

REVIEW_PROMPT_SIMPLE = """
As an expert code reviewer, analyze the provided code and offer constructive feedback. Consider the following aspects:
1. Determine review type:
   - For new file submissions, review the entire code file.
   - For change commits, focus on the modifications in the patch while referencing the whole file for context.
2. Code Quality & Style
3. Functionality & Logic
4. Security & Performance
5. Documentation
6. Best Practices & Patterns
7. Scalability & Maintainability

Provide feedback using this Markdown format:

```markdown
# Code Review: [Brief description]

## Summary
[Overview of findings]

## Strengths
- [Key positives]

## Areas for Improvement

### 1. [Category]
- **Issue:** [Description]
- **Suggestion:** [Recommendation]
- **Example:**
  ```
  # Code example
  ```

[Repeat for major points]

## Conclusion
[Key takeaways and overall assessment]
```

Ensure your feedback is:
- Constructive and specific
- Prioritized by impact
- Balanced between strengths and improvements
- Adapted to the specific programming language

Aim to improve code quality, security, and efficiency while providing learning opportunities.

IMPORTANT: Your response must not exceed {max_tokens} tokens. If you need more space, end your response with "[
CONTINUED]" and wait for a prompt to continue.
"""

USER_PROMPT = """
## File Information
- **File Name:** {filename}
- **Project Name:** {project_name}
- **Project Url:** {project_url}
- **Review Type:** {review_type}

## Patch (if applicable)
[PATCH_START]
```diff
{patch_code}
```
[PATCH_END]

## Full File Content
```
{full_code}
```

## Purpose of Changes (optional)

{commit_message}

---

Please review the above code according to the provided guidelines. Focus on [specific areas if any] and provide detailed feedback on code quality, functionality, security, and best practices.
"""


@tenacity.retry(
    retry=tenacity.retry_if_exception_type(Exception),
    wait=tenacity.wait_exponential(multiplier=1, min=2, max=5),
    stop=tenacity.stop_after_attempt(3),
    before_sleep=tenacity.before_sleep_log(logger, logging.INFO)
)
async def call_gemini_api(prompt: str, messages, model: ModelSettings):
    """
    call google gemini api
    :param model:
    :param prompt:
    :param messages:
    :return:
    """
    gemini_key = model.api_key
    gemini_model = model.model_name
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={gemini_key}"
    data = {
        "system_instruction": {
            "parts": {"text": prompt}
        },
        "contents": [
            {
                "parts": []
            }
        ],
        "generationConfig": {
            "temperature": 0,
            "topK": 1,
            "topP": 1,
            "maxOutputTokens": 8192,
            "stopSequences": []
        },
        "safetySettings": [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_ONLY_HIGH"
            }
        ]
    }
    # data["contents"][0]["parts"].insert(0, {"text": f"input: {prompt}"})
    for message in messages:
        data["contents"][0]["parts"].append({"text": f"input: {message['content']}"})

    headers = {
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(proxy=settings.get_proxy_url()) as client:
        response = await client.post(url, headers=headers, json=data, timeout=30)
        if response.status_code != 200:
            raise Exception(f"gemini request failed, code={response.status_code}, text={response.text}")
        result_json = response.json()
        root = result_json["candidates"][0]
        if "content" not in root and root["finishReason"] == "SAFETY":
            logger.error("gemini response: %s", root)
            return ""
        translated = root['content']["parts"][0]["text"]
        lines = translated.split('\n')
        if len(lines) > 0 and 'maintain' in lines[-1] and 'markdown structure' in lines[-1]:
            translated = '\n'.join(lines[:-1])
        return translated


async def call_openai_api(prompt: str, messages, model: ModelSettings, api_base_url=None, temperature: float = 0):
    """
    call openai api
    :param temperature:
    :param api_base_url:
    :param model:
    :param prompt:
    :param messages:
    :return:
    """
    prompts = messages.copy()
    if prompt is not None:
        prompts.insert(0, {"role": "system", "content": prompt})
    if not api_base_url:
        api_base_url = model.api_url
    client = AsyncClient(
        api_key=model.api_key,
        base_url=api_base_url,
        http_client=httpx.AsyncClient(timeout=30, proxy=settings.get_proxy_url())
    )
    completion = await client.chat.completions.create(model=model.model_name, messages=prompts, temperature=temperature)
    translated = completion.choices[0].message.content.strip('\'"')
    lines = translated.split('\n')
    if len(lines) > 0 and 'maintain' in lines[-1] and 'markdown structure' in lines[-1]:
        translated = '\n'.join(lines[:-1])
    return translated


async def _call_ai_api(prompt: str, messages, model: ModelSettings):
    await settings.get_api_limiter(model.api_key).acquire()
    if model.provider == 'openai':
        return await call_openai_api(prompt, messages, model)
    elif model.provider == 'gemini':
        return await call_gemini_api(prompt, messages, model)
    elif model.provider == 'groq':
        return await call_openai_api(prompt, messages, model, "https://api.groq.com/openai/v1", 0.1)
    elif model.provider == 'openai_like':
        return await call_openai_api(prompt, messages, model, None, 0.1)
    else:
        raise Exception(f"unknown provider {model.provider}")


async def do_ai_translate(system_prompt: str, messages):
    translated = await _call_ai_api(system_prompt, messages, settings.TRANSLATION_MODEL)
    return translated


async def do_ai_review(filename: str, commit_message: str, file_status: str, code_content: str, file_patch: str):
    if file_status == "added":
        review_type = "New File"
        file_patch = ""
    else:
        if file_patch:
            review_type = "Patch"
        else:
            review_type = "New File"
    if file_patch is None:
        file_patch = ""
    if code_content is None:
        code_content = ""
    messages = [{"role": "user", "content": USER_PROMPT.format(
        full_code=code_content,
        filename=filename,
        review_type=review_type,
        commit_message=commit_message,
        patch_code=file_patch)}]
    system_prompt = REVIEW_PROMPT_FULL.format(max_tokens=settings.REVIEW_MODEL.max_output_tokens)

    full_response = ""

    while True:
        chunk = await _call_ai_api(system_prompt, messages, settings.REVIEW_MODEL)

        full_response += chunk.strip()

        if "[CONTINUED]" not in chunk:
            break

        full_response = full_response.replace("[CONTINUED]", "")
        messages.append({"role": "assistant", "content": chunk})
        messages.append({"role": "user", "content": "Please continue your review."})

    return full_response
