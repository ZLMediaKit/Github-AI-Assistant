# Github AI Assistant

[![GitHub issues](https://img.shields.io/github/issues/ZLMediaKit/Github-AI-Assistant)]

您Github存储库的最佳AI助手, 它不但可以帮助您自动翻译issues/discussions/pr/commit到指定语言, 
还可以通过类似于[cursor](https://www.cursor.com/)的实现方式, 通过对整个项目向量化后生成详尽的上下文并提交给AI来进行代码审查, 代码自动修复等功能.

[English](README.md)


## 特性
- [x] 自动翻译指定的issues/discussions/pr/commit为英文或指定语言
- [x] 可批量翻译某个仓库的所有issues/discussions/pr为英文或指定语言
- [x] 可选择使用GPT系列或者GEMINI系列模型进行翻译(也可以使用任何兼容openAI接口的模型)
- [x] 翻译为英文后同时保留原文
- [x] 翻译为英文后自动添加标记，防止重复翻译
- [x] 内建webhook服务器, 可以通过webhook自动翻译issues/discussions/pr/commit为英文或其他语言
- [x] 支持预翻译, 可以通过修改data目录中的json文件进行预翻译
- [x] 使用异步协程进行翻译, 提高翻译效率
- [x] 提供两种翻译后端, 可以选择使用切分语句翻译或者直接翻译, 也可以自己扩展翻译后端
- [x] 支持手动或者通过webhook自动对提交的pr或者commit进行代码审查并提供修复优化建议,例如:[这里](https://github.com/ZLMediaKit/ZLToolKit/pull/246#discussion_r1760667617)
- [x] **支持基于代码树分割并向量化的方式进行代码审查, 类似于[cursor](https://www.cursor.com/)的实现. 由于可以提供AI足够的上下文, 因此可以提供更加准确的代码审查和修复建议.**

## 部署

ubuntu20.04下部署:

```bash
git clone https://github.com/ZLMediaKit/Github-AI-Assistant.git
cd translation_issues
chmod +x ./run.sh
sudo ./run.sh
```

其他系统下部署:

```bash
git clone https://github.com/ZLMediaKit/Github-AI-Assistant.git
cd translation_issues
# 安装python3.11或以上版本
# 创建虚拟环境
python3 -m venv venv
# 激活虚拟环境
source venv/bin/activate
# 安装依赖
pip install -r requirements.txt
```

启用webhook服务器并开机自动启动(ubuntu环境下):

```bash
sudo ./run.sh auto_start
```

## 用法

查看帮助:
    
```bash
./run.sh --help
```
![2023-12-30](https://github.com/ZLMediaKit/Github-AI-Assistant/assets/24582085/282c5183-acb6-4173-881e-1e088b53996c)

查看某个命令的帮助:

```bash
./run.sh trans_issues --help
```
![2023-12-30](https://github.com/ZLMediaKit/Github-AI-Assistant/assets/24582085/839afbc1-fac5-491c-804a-1b5aaf289fcd)

设置环境变量:

```bash
./run.sh update_env
```
[注意: 如果您使用GEMINI-PRO模型,那么请保持OPENAI_API_KEY为空,否则会优先使用GPT4模型进行翻译.]


翻译指定的issue:

```bash
./run.sh trans_issues --input-url https://github.com/your-org/your-repository/issues/1
```

[注意: 如果您没有在.env中设置环境变量, 那么您需要指定github-token,model_name和api_key等参数]
```bash
./run.sh trans_issues --input-url https://github.com/your-org/your-repository/issues/1 --github-token ghp_xxx --model_name gemini/gemini-1.5-flash --api_key xxxx
```

翻译指定的discussion:

```bash
./run.sh trans_discussions --input-url https://github.com/your-org/your-repository/discussions/1

```

翻译指定的PR:

```bash
./run.sh trans_pr --input-url https://github.com/your-org/your-repository/pull/1
```

批量翻译指定的仓库中所有的issues/discussions/pull requests:

```bash
# 翻译issues, 限制每次翻译10个
./run.sh batch_trans --input-url https://github.com/your-org/your-repository --query-filter issue --query-limit 10
# 翻译discussions, 限制每次翻译10个
./run.sh batch_trans --input-url https://github.com/your-org/your-repository --query-filter discussion --query-limit 10
# 翻译pull requests, 限制每次翻译10个
./run.sh batch_trans --input-url https://github.com/your-org/your-repository --query-filter pr --query-limit 10

```

使用AI审查指定的PR或者commit:

```bash
# 审查PR
./run.sh review_pr --input-url https://github.com/ZLMediaKit/ZLMediaKit/pull/3758
# 审查commit
./run.sh review_commit --input-url https://github.com/ZLMediaKit/ZLMediaKit/commit/e322db0a044fec82c66cc4e0b0daaa5e3b75b079
```

## 使用webhook

启动GitHub webhooks服务器:

```bash
./run.sh webhook start
```

启用webhook服务器后, 您需要在GitHub中配置webhook, 请参考[这里](https://docs.github.com/en/developers/webhooks-and-events/webhooks/creating-webhooks)进行配置.

webhook的Payload URL为: http://your-ip:port/api/v1/hooks


## 如何启用基于代码树分割并向量化的代码审查功能

目前只支持python和c/c++代码的审查, 如果您需要审查其他语言的代码, 请继承CodeElementAnalyzer类并自行扩展.

目前使用的嵌入式模型是jinaai/jina-embeddings-v2-base-code, 你可以根据自己的需求选择其他模型.

目前使用的向量数据库是milvus/milvus, 你可以根据自己的需求选择其他数据库.

您可以编辑.env文件中的EMBEDDING_MODEL和MILVUS_URI来选择自己的模型和数据库.

```allykeynamelanguage
EMBEDDING_MODEL=jinaai/jina-embeddings-v2-base-code
MILVUS_URI=milvus://
```

然后您需要先对代码库进行向量化和建立索引:

```bash
./run make_project_index --repo-url https://github.com/ZLMediaKit/ZLToolKit    
```

项目向量化和索引建立完成后, 将会优先使用向量化的方式进行代码审查.
其他功能和普通的代码审查一样, 不需要任何改动.

但是需要注意, 如果是测试使用那么不需要在.env中设置MILVUS_URI, 将会自动使用lite方式的向量数据库.
如果是生产环境, 则一定要部署milvus数据库并设置MILVUS_URI.

