# translation_issues

Automatically translate GitHub issues/discussions/pull requests into English using AI.

[中文](README_zh.md)

## Acknowledgements
This project references and utilizes some code from the [ossrs/discussion-translation](https://github.com/ossrs/issues-translation) project. Special thanks to the original author for their work.

## Features
- [x] Automatically translate specified issues into English
- [x] Automatically translate specified discussions into English
- [x] Automatically translate specified pull requests into English
- [x] Batch translate all issues/discussions/pull requests of a repository into English
- [x] Option to use GPT4 or GEMINI-PRO/GEMINI-FLASH models for translation (or any model compatible with the openAI interface)
- [x] Preserve original text after translation to English
- [x] Automatically add tags to translated content to prevent duplicate translations
- [x] Built-in webhook server for automatic translation of issues/discussions/pull requests into English
- [x] Support pre-translation by modifying json files in the data directory
- [x] Use asynchronous coroutines for translation to improve efficiency
- [x] Provide two translation backends: sentence splitting translation or direct translation, and support custom translation backends
- 

## Deployment

Deploy on Ubuntu 20.04:

```bash
git clone https://github.com/ZLMediaKit/translation_issues.git
cd translation_issues
chmod +x ./run.sh
sudo ./run.sh
```

Deploy on other systems:

```bash

git clone https://github.com/ZLMediaKit/translation_issues.git
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
![2023-12-30](https://github.com/ZLMediaKit/translation_issues/assets/24582085/282c5183-acb6-4173-881e-1e088b53996c)

View help for a specific command:

```bash
./run.sh trans_issues --help
```
![2023-12-30](https://github.com/ZLMediaKit/translation_issues/assets/24582085/839afbc1-fac5-491c-804a-1b5aaf289fcd)

Set environment variables:

```bash
./run.sh update_env
```
[Note: If you are using the GEMINI-PRO model, keep OPENAI_API_KEY empty, as it will prioritize translation using the GPT4 model.]

Translate a specific issue:

```bash
./run.sh trans_issues --input-url https://github.com/your-org/your-repository/issues/1
```

[Note: If you haven't set environment variables in .env, you need to specify the github-token and gemini-key or openai-key]
```bash
./run.sh trans_issues --input-url https://github.com/your-org/your-repository/issues/1 --github-token ghp_xxx --gemini-key xxxx
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

Start the GitHub webhook server:

```bash
./run.sh webhook start
```

After enabling the webhook server, you need to configure a webhook in GitHub. Please refer to [this guide](https://docs.github.com/en/developers/webhooks-and-events/webhooks/creating-webhooks) for configuration.

The Payload URL for the webhook is: http://your-ip:port/api/v1/hooks
