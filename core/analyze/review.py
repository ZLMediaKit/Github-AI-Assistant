# -*- coding:utf-8 -*-
#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/Github-AI-Assistant).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#
"""
@author:alex
@date:2024/9/16
@time:上午3:39
"""
__author__ = 'alex'

import json

from core import settings, llm
from core.analyze.core import CodeAnalyzer

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

USER_PROMPT_FULL = """
## File Information
- **File Name:** {filename}
- **Project Name:** {project_name}
- **Project Url:** {project_url}
- **Review Type:** {review_type}

## Project Overview

{project_overview}

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

## Related context information (optional):

{related_context}

## Patch dependencies (optional):

{patch_dependencies}

---

Please review the above code according to the provided guidelines. Focus on [specific areas if any] and provide detailed feedback on code quality, functionality, security, and best practices.
"""


async def do_ai_review(filename: str, commit_message: str, file_status: str,
                       code_content: str, file_patch: str, repo_name: str = ""):
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
    if repo_name:
        project_name = repo_name.split('/')[1]
        project_url = f"https://github.com/{repo_name}"
    else:
        project_name = ""
        project_url = ""
    if CodeAnalyzer.can_use(repo_name):
        analyzer = CodeAnalyzer(repo_name)
        context = await analyzer.get_review_context(filename, file_patch)
        related_context = context.get("context_info", "")
        if related_context:
            related_context = json.dumps(related_context, indent=2, ensure_ascii=False)
        dependencies = context.get("dependencies", "")
        if dependencies:
            dependencies = json.dumps(dependencies, indent=2, ensure_ascii=False)
        messages = [{"role": "user", "content": USER_PROMPT_FULL.format(
            full_code=code_content,
            filename=filename,
            review_type=review_type,
            commit_message=commit_message,
            project_url=project_url,
            project_name=project_name,
            patch_code=file_patch,
            project_overview=context.get("overview", ""),
            related_context=related_context,
            patch_dependencies=dependencies)}]
    else:
        messages = [{"role": "user", "content": USER_PROMPT.format(
            full_code=code_content,
            filename=filename,
            review_type=review_type,
            commit_message=commit_message,
            project_url=project_url,
            project_name=project_name,
            patch_code=file_patch)}]
    system_prompt = REVIEW_PROMPT_FULL.format(max_tokens=settings.REVIEW_MODEL.max_output_tokens)

    full_response = ""

    while True:
        chunk = await llm.call_ai_api(system_prompt, messages, settings.REVIEW_MODEL, 0.2, 40, 0.85)

        full_response += chunk.strip()

        if "[CONTINUED]" not in chunk:
            break

        full_response = full_response.replace("[CONTINUED]", "")
        messages.append({"role": "assistant", "content": chunk})
        messages.append({"role": "user", "content": "Please continue your review."})

    return full_response
