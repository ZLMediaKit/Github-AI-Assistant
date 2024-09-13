您提出的方案非常好，确实更加简洁高效，特别适合代码审查的场景。这个方案既能提供足够的上下文，又能有效控制输入到AI模型的数据量。让我根据您的思路来实现这个方案。



```python
import os
import networkx as nx
import ast
from git import Repo
import re

def clone_repo(repo_url, local_path):
    if not os.path.exists(local_path):
        Repo.clone_from(repo_url, local_path)
    return Repo(local_path)

def generate_dependency_graph(repo_path):
    G = nx.DiGraph()
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith(('.py', '.cpp', '.c', '.h')):
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as f:
                    content = f.read()
                dependencies = extract_dependencies(content, file)
                relative_path = os.path.relpath(file_path, repo_path)
                G.add_node(relative_path)
                for dep in dependencies:
                    G.add_edge(relative_path, dep)
    return G

def extract_dependencies(content, filename):
    dependencies = set()
    if filename.endswith('.py'):
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    dependencies.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    dependencies.add(node.module)
    elif filename.endswith(('.cpp', '.c', '.h')):
        # 简单的正则表达式来匹配 #include 语句
        includes = re.findall(r'#include\s*[<"]([^>"]+)[>"]', content)
        dependencies.update(includes)
    return dependencies

def get_changed_files(repo, commit_sha):
    commit = repo.commit(commit_sha)
    return [item.a_path for item in commit.diff(commit.parents[0])]

def get_related_files(G, changed_files, max_files=10, max_depth=2):
    related_files = set(changed_files)
    to_process = list(changed_files)
    depth = 0

    while to_process and len(related_files) < max_files and depth < max_depth:
        current_file = to_process.pop(0)
        for neighbor in G.neighbors(current_file):
            if neighbor not in related_files:
                related_files.add(neighbor)
                to_process.append(neighbor)
        for predecessor in G.predecessors(current_file):
            if predecessor not in related_files:
                related_files.add(predecessor)
                to_process.append(predecessor)
        depth += 1

    return list(related_files)[:max_files]

def simplify_function(func_def):
    # 保留函数定义和注释，去掉函数体
    return f"{func_def.split(':', 1)[0]}:\n    pass  # Function body removed for brevity"

def prepare_context(repo_path, files, max_tokens=10000):
    context = ""
    total_tokens = 0
    token_estimate = lambda s: len(s.split())  # 简单估算token数量

    for file in files:
        file_path = os.path.join(repo_path, file)
        with open(file_path, 'r') as f:
            content = f.read()

        file_tokens = token_estimate(content)
        if total_tokens + file_tokens > max_tokens:
            # 如果添加整个文件会超过token限制，尝试简化函数
            simplified_content = ""
            for line in content.split('\n'):
                if line.strip().startswith('def ') or line.strip().startswith('class '):
                    simplified_content += simplify_function(line + '\n')
                else:
                    simplified_content += line + '\n'
            
            simplified_tokens = token_estimate(simplified_content)
            if total_tokens + simplified_tokens <= max_tokens:
                context += f"\n--- {file} ---\n{simplified_content}\n"
                total_tokens += simplified_tokens
            else:
                # 如果简化后仍然超过限制，只包含文件名
                context += f"\n--- {file} --- (Content omitted due to token limit)\n"
        else:
            context += f"\n--- {file} ---\n{content}\n"
            total_tokens += file_tokens

        if total_tokens >= max_tokens:
            break

    return context

def main(repo_url, local_path, commit_sha, max_files=10, max_depth=2, max_tokens=10000):
    repo = clone_repo(repo_url, local_path)
    
    dependency_graph_path = os.path.join(local_path, 'dependency_graph.gpickle')
    if os.path.exists(dependency_graph_path):
        G = nx.read_gpickle(dependency_graph_path)
    else:
        G = generate_dependency_graph(local_path)
        nx.write_gpickle(G, dependency_graph_path)

    changed_files = get_changed_files(repo, commit_sha)
    related_files = get_related_files(G, changed_files, max_files, max_depth)
    context = prepare_context(local_path, related_files, max_tokens)

    print("Context for AI review:")
    print(context)

    # 更新依赖图
    G = generate_dependency_graph(local_path)
    nx.write_gpickle(G, dependency_graph_path)

    # 这里可以调用AI模型API进行代码审查
    # ai_review = call_ai_model_api(context)
    # print("AI Review:", ai_review)

if __name__ == "__main__":
    repo_url = "https://github.com/username/repo.git"
    local_path = "/path/to/local/repo"
    commit_sha = "abc123"  # 替换为实际的commit SHA
    main(repo_url, local_path, commit_sha)

```

这个实现遵循了您提出的方案，并且有以下特点：

1. 从commit中提取修改的文件：使用`get_changed_files`函数实现。

2. 依赖图的生成和使用：
   - 使用`generate_dependency_graph`函数生成依赖图。
   - 如果依赖图已存在，直接加载；否则生成新的依赖图。

3. 查找相关文件：
   - `get_related_files`函数实现了查找依赖和被依赖的文件。
   - 可以设置最大文件数量和最大依赖深度。

4. 控制上下文大小：
   - `prepare_context`函数根据设置的最大token数量来准备上下文。
   - 如果某个文件过大，会尝试简化函数定义，只保留函数签名和注释。

5. 依赖图更新：
   - 在每次commit的Review处理完成后，重新生成依赖图。

这个方案的优点包括：

- 效率高：不需要进行耗费资源的向量化操作。
- 上下文相关：优先提供与修改直接相关的文件内容。
- 灵活可控：可以通过参数调整最大文件数、依赖深度和token数量。
- 适应性强：可以处理Python、C++和C语言的项目。

使用此方案时，您可能需要根据具体项目和AI模型的特点调整以下参数：

- `max_files`：最大相关文件数量
- `max_depth`：最大依赖深度
- `max_tokens`：最大token数量

此外，您可能还需要：

1. 实现调用AI模型API的函数（`call_ai_model_api`）。
2. 根据您的版本控制系统调整获取commit信息的方法。
3. 可能需要优化依赖图的生成和更新策略，特别是对于大型项目。

这个方案应该能够有效地为AI模型提供足够的上下文来进行代码审查，同时避免了不必要的复杂性。如果您有任何问题或需要进一步的调整，请随时告诉我。
