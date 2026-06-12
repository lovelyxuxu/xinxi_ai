# 心犀AI Git 配置与 GitHub 发布设计

**日期：** 2026-06-10  
**状态：** 已批准

## 背景

心犀AI（`xinxi_ai`）是一个 Python + LangChain + Chroma 向量库项目，使用 DeepSeek LLM 与硅基流动 Embedding API。项目根目录尚无 `.gitignore`，尚未初始化 Git 仓库。用户需要将代码安全地上传到 GitHub，避免泄露 API Key 及提交无关本地文件。

## 目标

1. 创建根目录 `.gitignore`，排除敏感配置与本地运行时数据
2. 初始化 Git 仓库并完成首次提交
3. 关联 GitHub 远程仓库并推送

## 方案选择

采用 **GitHub 官方 Python 模板 + 项目定制规则**（方案 B）。

理由：覆盖 Python 生态常见忽略项，同时追加 `.env`、`chroma_db/` 等项目特有规则，适合开源发布。

## 忽略规则

| 分类 | 忽略项 | 原因 |
|------|--------|------|
| 敏感配置 | `.env`、`.env.local`、`.env.*.local` | 含 API Key |
| 配置模板 | `!.env.example`（白名单） | 供他人复制配置 |
| 虚拟环境 | `.venv/`、`venv/`、`env/` | 本地依赖，体积大 |
| 运行时数据 | `chroma_db/` | 向量库持久化，克隆后本地重建 |
| Python 缓存 | `__pycache__/`、`*.py[cod]`、`.pytest_cache/` 等 | 编译/测试缓存 |
| IDE | `.idea/` | PyCharm 个人配置 |
| 系统文件 | `.DS_Store`、`Thumbs.db` | OS 自动生成 |
| 构建产物 | `dist/`、`build/`、`*.egg-info/` | 打包中间文件 |

## 明确提交的内容

- 源码：`main.py`、`config/`、`src/`、`data/mock_data.py`
- 配置模板：`.env.example`
- 依赖与测试：`requirements.txt`、`test_pipeline.py`
- 文档：`心犀AI.md`

## `.gitignore` 结构

单个根目录 `.gitignore`，分块注释：

1. 心犀AI 项目定制（`.env`、`chroma_db/`、`!.env.example`）
2. Python 标准模板（字节码、测试缓存、打包产物）
3. 虚拟环境
4. IDE（`.idea/`）
5. 操作系统文件

## GitHub 发布流程

| 步骤 | 操作 |
|------|------|
| 1 | `git init` |
| 2 | 创建 `.gitignore` |
| 3 | `git add .` |
| 4 | `git commit` 首次提交 |
| 5 | 在 GitHub 创建空仓库（不勾选 README / .gitignore） |
| 6 | `git remote add origin <url>` |
| 7 | `git push -u origin main` |

## 验证标准

```powershell
git status                    # 不出现 .env、.venv/、chroma_db/、.idea/
git check-ignore -v .env      # 被忽略
git check-ignore -v .env.example  # 不被忽略
```

成功标准：GitHub 上可见源码与 `.env.example`，不可见 API Key、虚拟环境、向量库数据、IDE 配置。

## 不在范围内

- GitHub Actions CI 配置
- README 撰写（除非用户另行要求）
- `.env` 内容修改或密钥轮换
