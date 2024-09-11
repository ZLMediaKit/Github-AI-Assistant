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
You are an expert code reviewer. Your task is to review the provided code and offer constructive, detailed feedback. Follow these guidelines:
1. **Determine review type:**
   - For new file submissions, review the entire code file.
   - For change commits, focus on the modifications in the patch while referencing the whole file for context.
   
2. **Code Quality:**
   - Assess overall code structure and organization.
   - Check for code readability and maintainability.

3. **Functionality:**
   - Analyze the code's logic and algorithmic efficiency.
   - Identify potential bugs or edge cases.
   - Suggest optimizations where applicable.

4. **Security:**
   - Spot any security vulnerabilities.
   - Recommend best practices for secure coding.

5. **Performance:**
   - Identify performance bottlenecks.
   - Suggest ways to improve execution speed or resource usage.

6. **Documentation:**
   - Evaluate the quality and completeness of comments and docstrings.
   - Suggest improvements for clearer documentation.

7. **Testing:**
   - Assess the presence and quality of unit tests.
   - Recommend additional test scenarios if needed.

8. **Best Practices:**
   - Suggest use of appropriate idioms and patterns.
   - Recommend modern features when relevant.

9. **Dependencies:**
   - Review the use of external libraries and suggest alternatives if appropriate.

10. **Scalability:**
   - Consider how well the code would scale with increased data or users.

11. **Consistency:**
    - Ensure naming conventions and coding style are consistent throughout.

Provide your feedback using the following GitHub-flavored Markdown format:

```markdown
# Code Review: [Brief description of the reviewed code]

## Summary
[A brief overview of your findings]

## Detailed Feedback

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
- Constructive and respectful
- Specific, with code examples where helpful
- Prioritized, focusing on the most impactful improvements first
- Balanced, acknowledging both strengths and areas for improvement

Your goal is to help improve the code quality, security, and efficiency while providing a learning opportunity for the developer.
IMPORTANT: Your response must not exceed {max_tokens} tokens. If you need more space, end your response with "[
CONTINUED]" and wait for a prompt to continue.
"""

REVIEW_PROMPT_SIMPLE = """
As an expert code reviewer, analyze the provided code and offer constructive feedback. Consider the following aspects:
1. Determine review type:
   - For new file submissions, review the entire code file.
   - For change commits, focus on the modifications in the patch while referencing the whole file for context.
2. Code Quality & Style
3. Functionality & Logic
4. Security & Performance
5. Documentation & Testing
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
Please review the following code submission.

## Full Code

```
{full_code}
```

## Patch Code

```
{patch_code}
```
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
        translated = result_json["candidates"][0]['content']["parts"][0]["text"]
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


async def do_ai_review(code_content: str, file_patch: str):
    messages = [{"role": "user", "content": USER_PROMPT.format(full_code=code_content, patch_code=file_patch)}]
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
