# translation_issues

使用 AI 自动将 GitHub issues/discussions/pull requests翻译成英文。

[English](README.md)

## 感谢
本项目参考并使用了[ossrs/discussion-translation](https://github.com/ossrs/issues-translation)项目的部分代码,感谢原作者的工作.

## 特性
- [x] 自动翻译指定的 issues为英文
- [x] 自动翻译指定的 discussions为英文
- [x] 自动翻译指定的 pull requests为英文
- [x] 可批量翻译某个仓库的所有 issues/discussions/pull requests为英文
- [x] 可选择使用GPT4或者GEMINI-PRO/GEMINI-FLASH模型进行翻译(也可以使用任何兼容openAI接口的模型)
- [x] 翻译为英文后同时保留原文
- [x] 翻译为英文后自动添加标记，防止重复翻译
- [x] 内建webhook服务器, 可以通过webhook自动翻译issues/discussions/pull requests为英文
- [x] 支持预翻译, 可以通过修改data目录中的json文件进行预翻译
- [x] 使用异步协程进行翻译, 提高翻译效率
- [x] 提供两种翻译后端, 可以选择使用切分语句翻译或者直接翻译, 也可以自己扩展翻译后端

## 部署

ubuntu20.04下部署:

```bash
git clone https://github.com/ZLMediaKit/translation_issues.git
cd translation_issues
chmod +x ./run.sh
sudo ./run.sh
```

其他系统下部署:

```bash
git clone https://github.com/ZLMediaKit/translation_issues.git
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
![2023-12-30](https://github.com/ZLMediaKit/translation_issues/assets/24582085/282c5183-acb6-4173-881e-1e088b53996c)

查看某个命令的帮助:

```bash
./run.sh trans_issues --help
```
![2023-12-30](https://github.com/ZLMediaKit/translation_issues/assets/24582085/839afbc1-fac5-491c-804a-1b5aaf289fcd)

设置环境变量:

```bash
./run.sh update_env
```
[注意: 如果您使用GEMINI-PRO模型,那么请保持OPENAI_API_KEY为空,否则会优先使用GPT4模型进行翻译.]


翻译指定的issue:

```bash
./run.sh trans_issues --input-url https://github.com/your-org/your-repository/issues/1
```

[注意: 如果您没有在.env中设置环境变量, 那么您需要指定github-token以及gemini-key或者openai-key]
```bash
./run.sh trans_issues --input-url https://github.com/your-org/your-repository/issues/1 --github-token ghp_xxx --gemini-key xxxx
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

启动GitHub webhooks服务器:

```bash
./run.sh webhook start
```

启用webhook服务器后, 您需要在GitHub中配置webhook, 请参考[这里](https://docs.github.com/en/developers/webhooks-and-events/webhooks/creating-webhooks)进行配置.

webhook的Payload URL为: http://your-ip:port/api/v1/hooks

