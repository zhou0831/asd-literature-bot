# asd-literature-bot

最小可用版 ASD 社会认知 / 社会意图加工文献推荐系统。

它每天检索候选文献，和 Zotero 目标 collection 及历史推荐记录去重，选出 1 篇生成中文日报，并通过 Gmail 发到 `MAIL_TO`。每周会汇总最近推荐记录，选出 Top 3 生成周报。Zotero 导入必须手动确认，不会自动写入。

日报里的“文章讲了什么”会用题名、摘要和关键词生成中文概述，不直接粘贴英文摘要。当前版本是规则化中文概述；如果后续需要更接近人工阅读笔记的翻译和讲解，可以再接入 `OPENAI_API_KEY` 做 LLM 摘要。

## 安装

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Linux / GitHub Actions 环境使用：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 配置环境变量

复制示例文件：

```bash
copy .env.example .env
```

填写 `.env`：

```bash
OPENAI_API_KEY=
ZOTERO_API_KEY=
ZOTERO_USER_ID=
ZOTERO_LIBRARY_TYPE=user
ZOTERO_COLLECTION_KEY=Z7SCP3DE
MAIL_TO=841240617@qq.com
MAIL_FROM=你的Gmail地址
GMAIL_APP_PASSWORD=你的Gmail应用专用密码
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
TIMEZONE=Asia/Shanghai
```

不要把 `.env` 提交到 Git。

## Gmail app password

Gmail SMTP 发送需要 Google 账号开启两步验证，然后生成 16 位 app password。把它放到本地 `.env` 或 GitHub Secrets 的 `GMAIL_APP_PASSWORD`，不要写进代码、README、issue 或日志。

## GitHub Secrets

仓库页面进入：

`Settings -> Secrets and variables -> Actions -> New repository secret`

至少添加：

- `ZOTERO_API_KEY`
- `ZOTERO_USER_ID`
- `ZOTERO_LIBRARY_TYPE`，值通常为 `user`
- `ZOTERO_COLLECTION_KEY`，值为 `Z7SCP3DE`
- `MAIL_TO`，值为 `841240617@qq.com`
- `MAIL_FROM`
- `GMAIL_APP_PASSWORD`
- `OPENAI_API_KEY`，第一版暂不依赖它生成报告，但先预留

## 本地测试 Gmail

只构造邮件、不发送：

```bash
python scripts/test_email.py --dry-run
```

真实发送测试邮件：

```bash
python scripts/test_email.py
```

收到标题为 `[ASD文献推荐系统] Gmail测试成功` 的邮件，说明 SMTP 配置可用。

## 运行每日推荐

```bash
python scripts/run_daily.py
```

成功后会生成类似：

```text
reports/daily/2026-05-18.md
```

如果 `MAIL_FROM` 和 `GMAIL_APP_PASSWORD` 已配置，会自动发送日报到 `MAIL_TO`。

## 运行每周总结

```bash
python scripts/run_weekly.py
```

成功后会生成类似：

```text
reports/weekly/2026-week-21.md
```

如果邮件配置完整，会自动发送周报到 `MAIL_TO`。

## 手动导入 Zotero

日报里会包含 `candidate_id` 和命令。先人工打开 DOI/URL 复核，确认后运行：

```bash
python scripts/approve_import.py --candidate-id 2026-05-18_xxxxx --add-to-zotero
```

导入目标 collection：

- 名称：社会意图脉络——社会认知
- key：`Z7SCP3DE`
- 标签：`GPT推荐`

不加 `--add-to-zotero` 时只查看候选，不会导入：

```bash
python scripts/approve_import.py --candidate-id 2026-05-18_xxxxx
```

如果使用 GitHub Actions，不需要回到本机命令行。进入仓库页面：

`Actions -> Approve Zotero Import -> Run workflow`

把邮件里的 `candidate_id` 填进去，例如：

```text
2026-05-18_xxxxx
```

点击运行后，workflow 会把这篇候选文献导入 Zotero 目标 collection，并添加 `GPT推荐` 标签。

当前版本导入的是 Zotero 条目元数据、DOI、URL 和摘要，不会自动下载并上传 PDF 附件。如果需要自动抓取开放获取 PDF 并作为附件上传，需要后续单独扩展。

## 查看已经推荐过哪些文章

有三种方式：

1. 直接在邮箱里搜索：

```text
[ASD文献推荐]
```

2. 在 GitHub Actions 里查看每次日报/周报 artifact：

`Actions -> Daily Literature Recommendation -> 某次运行 -> Artifacts -> daily-reports`

周报同理：

`Actions -> Weekly Literature Summary -> 某次运行 -> Artifacts -> weekly-reports`

3. 导出历史推荐清单：

`Actions -> List Recommended Literature -> Run workflow`

运行结束后下载 artifact：

```text
recommended-literature-history
```

里面包含：

- `recommendations.md`：适合阅读的 Markdown 清单
- `recommendations.csv`：适合表格筛选的 CSV 清单

本地也可以运行：

```bash
python scripts/list_recommendations.py --limit 50 --format md --output reports/recommendations.md
python scripts/list_recommendations.py --limit 50 --format csv --output reports/recommendations.csv
```

## GitHub Actions

已创建：

- `.github/workflows/daily.yml`：每天北京时间约 08:17 运行 `scripts/run_daily.py`
- `.github/workflows/weekly.yml`：每周一北京时间约 08:37 运行 `scripts/run_weekly.py`
- `.github/workflows/list_recommendations.yml`：手动导出历史推荐清单
- `.github/workflows/import_zotero.yml`：手动批准某个 `candidate_id` 导入 Zotero

GitHub cron 使用 UTC，实际运行可能因 GitHub 调度负载延迟几分钟。

Actions 已使用 `actions/cache` 缓存 `data/recommended.sqlite` 和 `reports/`，用于保留历史推荐记录、去重信息和周报输入。第一次运行时缓存为空，后续运行会自动恢复最近一次缓存。

## 排查

- 收不到邮件：先运行 `python scripts/test_email.py --dry-run`，确认 `MAIL_TO` / `MAIL_FROM` 已读取；再运行真实发送，检查 Gmail app password。
- Zotero 去重无效：运行 `python scripts/sync_zotero.py`，确认 `ZOTERO_API_KEY`、`ZOTERO_USER_ID`、`ZOTERO_COLLECTION_KEY` 有效。
- 没有候选文献：调大 `config.yaml` 的 `days_back`，或增加/放宽 `queries`。
- GitHub Actions 失败：在 Actions 日志里看是依赖安装、Secrets 缺失、SMTP 认证还是检索 API 网络问题。

## 测试

```bash
python -m pytest
```
