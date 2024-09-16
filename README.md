# Github AI Assistant

[![GitHub issues](https://img.shields.io/github/issues/ZLMediaKit/Github-AI-Assistant)]

Your best AI assistant for GitHub repositories, it not only helps you automatically translate issues/discussions/PRs/commits into the specified language, but also performs code review and automatic code fixes by vectorizing the entire project to generate detailed context and submitting it to the AI, similar to the implementation of [cursor](https://www.cursor.com/).

[中文](README_zh.md)

## Acknowledgements
This project references and utilizes some code from the [ossrs/discussion-translation](https://github.com/ossrs/issues-translation) project. Special thanks to the original author for their work.

## Features
- [x] Automatically translate specified issues/discussions/PRs/commits to English or a designated language
- [x] Batch translate all issues/discussions/PRs of a repository to English or a designated language
- [x] Option to use GPT series or GEMINI series models for translation (or any model compatible with OpenAI interface)
- [x] Retain the original text alongside the English translation
- [x] Automatically add markers after translation to English to prevent duplicate translations
- [x] Built-in webhook server for automatic translation of issues/discussions/PRs/commits to English or other languages
- [x] Support for pre-translation by modifying JSON files in the data directory
- [x] Use of asynchronous coroutines for translation to improve efficiency
- [x] Provide two translation backends, with options to use sentence splitting translation or direct translation, and the ability to extend translation backends
- [x] Support for manual or webhook-triggered automatic code review of submitted PRs or commits, providing suggestions for fixes and optimizations, for example: [here](https://github.com/ZLMediaKit/ZLToolKit/pull/246)
- [x] **Supports code review based on code tree segmentation and vectorization, similar to the implementation of [cursor](https://www.cursor.com/). By providing the AI with sufficient context, it can offer more accurate code review and fix suggestions.**

## Deployment

Deploy on Ubuntu 20.04:

```bash
git clone https://github.com/ZLMediaKit/Github-AI-Assistant.git
cd translation_issues
chmod +x ./run.sh
sudo ./run.sh
```

Deploy on other systems:

```bash

git clone https://github.com/ZLMediaKit/Github-AI-Assistant.git
cd translation_issues
# Install python3.11 or later
# Create a virtual environment
python3 -m venv venv
# Activate the virtual environment
source venv/bin/activate
# Install dependencies
pip install -r requirements.txt
```

Enable webhook server and auto-start on boot:

```bash
sudo ./run.sh auto_start
```

## Usage

View help:

```bash
./run.sh --help
```
![2023-12-30](https://github.com/ZLMediaKit/Github-AI-Assistant/assets/24582085/282c5183-acb6-4173-881e-1e088b53996c)

View help for a specific command:

```bash
./run.sh trans_issues --help
```
![2023-12-30](https://github.com/ZLMediaKit/Github-AI-Assistant/assets/24582085/839afbc1-fac5-491c-804a-1b5aaf289fcd)

Set environment variables:

```bash
./run.sh update_env
```
[Note: If you are using the GEMINI-PRO model, keep OPENAI_API_KEY empty, as it will prioritize translation using the GPT4 model.]

Translate a specific issue:

```bash
./run.sh trans_issues --input-url https://github.com/your-org/your-repository/issues/1
```

[Note: If you haven't set environment variables in .env, you will need to specify parameters such as github-token, model_name and api_key]
```bash
./run.sh trans_issues --input-url https://github.com/your-org/your-repository/issues/1 --github-token ghp_xxx --model_name gemini/gemini-1.5-flash --api_key xxxx
```

Translate a specific discussion:

```bash
./run.sh trans_discussions --input-url https://github.com/your-org/your-repository/discussions/1

```

Translate a specific PR:

```bash
./run.sh trans_pr --input-url https://github.com/your-org/your-repository/pull/1
```

Batch translate all issues/discussions/pull requests of a specific repository:

```bash
# Translate issues, limit 10 translations per batch
./run.sh batch_trans --input-url https://github.com/your-org/your-repository --query-filter issue --query-limit 10
# Translate discussions, limit 10 translations per batch
./run.sh batch_trans --input-url https://github.com/your-org/your-repository --query-filter discussion --query-limit 10
# Translate pull requests, limit 10 translations per batch
./run.sh batch_trans --input-url https://github.com/your-org/your-repository --query-filter pr --query-limit 10

```

Use AI to review the specified PR or commit:

```bash
# Review PR
./run.sh review_pr --input-url https://github.com/ZLMediaKit/ZLMediaKit/pull/3758
# Review commit
./run.sh review_commit --input-url https://github.com/ZLMediaKit/ZLMediaKit/commit/e322db0a044fec82c66cc4e0b0daaa5e3b75b079
```

## Use webhook

Start the GitHub webhook server:

```bash
./run.sh webhook start
```

After enabling the webhook server, you need to configure a webhook in GitHub. Please refer to [this guide](https://docs.github.com/en/developers/webhooks-and-events/webhooks/creating-webhooks) for configuration.

The Payload URL for the webhook is: http://your-ip:port/api/v1/hooks

## How to Enable Code Review Based on Code Tree Segmentation and Vectorization

Currently, only Python and C/C++ code reviews are supported. If you need to review code in other languages, please extend the `CodeElementAnalyzer` class.

The current embedding model used is `jinaai/jina-embeddings-v2-base-code`, but you can choose other models according to your needs.

The current vector database used is `milvus/milvus`, but you can choose other databases according to your needs.

You can edit the `EMBEDDING_MODEL` and `MILVUS_URI` in the `.env` file to select your model and database.

```plaintext
EMBEDDING_MODEL=jinaai/jina-embeddings-v2-base-code
MILVUS_URI=milvus://
```

Then, you need to vectorize the codebase and build the index:

```bash
./run make_project_index --repo-url https://github.com/ZLMediaKit/ZLToolKit    
```

Once the project is vectorized and the index is built, code reviews will prioritize using the vectorized method. Other functionalities remain the same as regular code reviews, without any modifications needed.

However, please note that if it is for testing purposes, you do not need to set `MILVUS_URI` in the `.env` file, as it will automatically use the lite version of the vector database. For production environments, you must deploy the Milvus database and set `MILVUS_URI`.
