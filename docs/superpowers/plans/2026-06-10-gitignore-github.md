# Git 配置与 GitHub 发布 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为心犀AI 项目创建 `.gitignore`、初始化 Git 仓库、验证敏感文件未被跟踪，并完成首次提交以便推送到 GitHub。

**Architecture:** 在仓库根目录放置单个 `.gitignore` 文件，采用 GitHub Python 标准忽略规则叠加项目定制规则（`.env`、`chroma_db/`）。初始化 Git 后通过 `git check-ignore` 与 `git status` 双重验证，再关联 GitHub 远程推送。

**Tech Stack:** Git、GitHub、Python 3、PowerShell（Windows）

**Spec:** `docs/superpowers/specs/2026-06-10-gitignore-github-design.md`

---

## 文件变更一览

| 操作 | 路径 | 职责 |
|------|------|------|
| Create | `.gitignore` | 定义忽略规则 |
| Create | `.git/` | Git 仓库（`git init` 生成） |
| 不修改 | `.env` | 保持本地，永不被跟踪 |
| 提交 | 其余源码与配置 | 见 spec「明确提交的内容」 |

---

### Task 1: 创建 `.gitignore`

**Files:**
- Create: `.gitignore`

- [ ] **Step 1: 写入 `.gitignore` 完整内容**

在项目根目录 `e:\study\python\xinxi_ai\.gitignore` 创建文件，内容如下：

```gitignore
# ============================================================
# 心犀AI - 项目定制
# ============================================================

# 环境变量（含 API Key，绝不提交）
.env
.env.local
.env.*.local

# 保留配置模板供他人参考
!.env.example

# Chroma 向量库本地持久化数据（运行时生成）
chroma_db/

# ============================================================
# Python（基于 GitHub 官方 Python.gitignore）
# ============================================================

# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/
cover/

# Translations
*.mo
*.pot

# Jupyter Notebook
.ipynb_checkpoints

# IPython
profile_default/
ipython_config.py

# pyenv
.python-version

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Pyre type checker
.pyre/

# pytype static type analyzer
.pytype/

# Cython debug symbols
cython_debug/

# ============================================================
# IDE
# ============================================================

.idea/

# ============================================================
# 操作系统
# ============================================================

.DS_Store
Thumbs.db
ehthumbs.db
Desktop.ini
```

- [ ] **Step 2: 确认文件已创建**

Run:

```powershell
Set-Location "e:\study\python\xinxi_ai"
Test-Path .gitignore
```

Expected: `True`

---

### Task 2: 初始化 Git 仓库

**Files:**
- Create: `.git/`（由 git 命令生成）

- [ ] **Step 1: 初始化仓库并设置默认分支为 main**

Run:

```powershell
Set-Location "e:\study\python\xinxi_ai"
git init -b main
```

Expected: `Initialized empty Git repository in .../xinxi_ai/.git/`

- [ ] **Step 2: 确认尚未误跟踪敏感文件**

Run:

```powershell
git status
```

Expected: `.env`、`.venv/`、`chroma_db/`、`.idea/` **不应**出现在 "Changes to be committed" 或 "Untracked files" 中（`.gitignore` 生效前可能短暂可见 untracked，Step 3 验证忽略规则）

---

### Task 3: 验证忽略规则

**Files:**
- Test: 无新文件，仅运行命令

- [ ] **Step 1: 验证敏感路径被忽略**

Run:

```powershell
Set-Location "e:\study\python\xinxi_ai"
git check-ignore -v .env
git check-ignore -v .venv
git check-ignore -v chroma_db
git check-ignore -v .idea
```

Expected: 每条命令均输出匹配规则（exit code 0），例如：

```
.gitignore:NN:.env    .env
```

- [ ] **Step 2: 验证 `.env.example` 不被忽略**

Run:

```powershell
git check-ignore -v .env.example
```

Expected: exit code 1（无输出，表示**不**被忽略，可以提交）

- [ ] **Step 3: 验证待提交列表安全**

Run:

```powershell
git add .
git status
```

Expected 应包含（示例，顺序可能不同）:

```
.env.example
main.py
requirements.txt
test_pipeline.py
config/
data/
src/
.gitignore
心犀AI.md
docs/
```

Expected **不应包含**:

```
.env
.venv/
chroma_db/
.idea/
```

若 `.env` 出现在列表中，**停止推送**，检查 `.gitignore` 后执行 `git rm --cached .env` 再重新验证。

---

### Task 4: 首次提交

**Files:**
- Modify: `.git/`（生成首次 commit）

- [ ] **Step 1: 创建首次提交**

Run:

```powershell
Set-Location "e:\study\python\xinxi_ai"
git add .
git commit -m "$( @'
Initial commit: 心犀AI 项目源码

添加 .gitignore 排除 .env、虚拟环境与 chroma_db 本地数据。
'@ )"
```

Expected: `N files changed`（N > 0），commit 成功

- [ ] **Step 2: 确认 commit 不含敏感文件**

Run:

```powershell
git ls-files | Select-String -Pattern '\.env$|chroma_db|\.venv|\.idea'
```

Expected: **无输出**（或仅匹配 `.env.example`，不含裸 `.env`）

允许出现: `.env.example`

不允许出现: `.env`（无 `.example` 后缀）

---

### Task 5: 关联 GitHub 并推送

**Files:**
- Modify: `.git/config`（添加 remote，由 git 命令生成）

**前置条件:** 用户已在 GitHub 创建空仓库（不勾选 "Add a README" 和 "Add .gitignore"）。

- [ ] **Step 1: 添加远程 origin**

将 `<YOUR_GITHUB_REPO_URL>` 替换为实际仓库地址，例如 `https://github.com/username/xinxi_ai.git`：

Run:

```powershell
Set-Location "e:\study\python\xinxi_ai"
git remote add origin <YOUR_GITHUB_REPO_URL>
git remote -v
```

Expected:

```
origin  https://github.com/username/xinxi_ai.git (fetch)
origin  https://github.com/username/xinxi_ai.git (push)
```

- [ ] **Step 2: 推送到 GitHub**

Run:

```powershell
git push -u origin main
```

Expected: 推送成功，GitHub 仓库页面可见源码与 `.env.example`

- [ ] **Step 3: 在 GitHub 上人工确认**

打开仓库页面，确认：

- [ ] 存在 `main.py`、`src/`、`requirements.txt`、`.env.example`
- [ ] **不存在** `.env` 文件
- [ ] 仓库中无 `.venv/`、`chroma_db/` 目录

---

## 故障排查

| 问题 | 处理方式 |
|------|----------|
| `.env` 已被 `git add` | `git rm --cached .env`，确认 `.gitignore` 后重新 commit |
| `git push` 认证失败 | 使用 GitHub Personal Access Token 或 SSH key |
| 远程已有 README 导致冲突 | `git pull origin main --rebase` 后再 push，或删除远程 README 后重试 |
| 分支名不是 main | `git branch -M main` 后再 push |

---

## Spec 覆盖自检

| Spec 要求 | 对应 Task |
|-----------|-----------|
| Python 模板 + 项目定制 | Task 1 |
| 忽略 `.env`、`chroma_db/`、`.idea/`、`.venv/` | Task 1, Task 3 |
| 保留 `.env.example` | Task 1, Task 3 Step 2 |
| `git init` + 首次提交 | Task 2, Task 4 |
| GitHub 远程关联与推送 | Task 5 |
| `git check-ignore` 验证 | Task 3 |
