---
name: sec-paper
description: Search cybersecurity academic papers via DeepSec (deepsec.chat) with outbound network on first request, English-first keywords, and concurrent queries for speed; summarize hits in detail when ≤20 papers (compact list when more). HTML report is opt-in only when the user asks. Portable Agent Skill for any SKILL.md-compatible agent. Use when the user asks to find, search, or look up security papers, conference papers (CCS, IEEE S&P, NDSS, USENIX Security), authors, institutions, or topics like fuzzing, TEE, side-channel, malware, 越权 / BAC / IDOR, or when SecPaper / DeepSec paper search is mentioned.
---

# SecPaper — 网络安全论文检索

通过 [DeepSec](http://deepsec.chat/) 公开 HTTP API 检索顶会网络安全论文。仅使用下方论文检索相关接口；不要调用访问统计或其他非论文接口。

本 skill 为标准 `SKILL.md` 包，可在任意支持 Agent Skills 的环境中使用，不绑定单一产品。

**Skill 根目录 `SKILL_DIR`**：本 `SKILL.md` 所在目录（本仓库为 `skills/sec-paper`）。脚本与样式均相对该目录解析，勿写死用户主目录或某一 IDE 的绝对路径。

效果示意见仓库 [`assets/demo.png`](../../assets/demo.png)（或本 skill 内 `assets/demo.png`）。

## Base URL

```
http://deepsec.chat
```

无需鉴权。所有请求均为 `GET`，参数放在 query string；中文/特殊字符需 URL 编码。

## 网络与执行约束（必须）

凡访问 `deepsec.chat` 的命令（`curl` / `python` `urllib` 等）：

- **第一次**请求就必须具备出网能力。若当前 Agent/沙箱默认拦截外网，须在**首轮**显式申请完整出网权限（按其环境等价开关办理）。
- **禁止**先无权限试跑、被拦后再重试——避免无谓的二次往返与耗时。
- 本机 Python 版本检查、写 JSON/HTML、起 `127.0.0.1` 预览服务不依赖外网，可与检索分开；但**任何** DeepSec HTTP 请求都按上条办理。

## 工作流

1. 从用户问题提炼检索意图（关键词 / 作者 / 机构 / 筛选条件）。
2. **优先提炼英文技术词**作主查询（见「检索策略」）；需要时再并行补中文或近义词。
3. 需要时先拉元数据：`/api/conferences`、`/api/years`、`/api/application-scenarios`、`/api/attack-surfaces`（可与首轮检索并行）。
4. **并发**发起多路检索（多关键词 / 多接口），合并去重；结果不足时再换词或增大 `offset` 翻页——不要串行慢试。
5. **先在对话里给总结**（见「回答格式」：本次展示 ≤20 篇给详细解读，>20 篇给精简列表）。
6. **默认不生成 HTML 报告**。仅当用户明确要求生成报告 / HTML / 本地预览时，才走「HTML 报告」流程。
7. 用户说「只要列表」等时按精简列表回答即可。

## 接口

### 关键词搜索（主入口）

`GET /api/papers/search`

| 参数 | 必填 | 说明 |
|------|------|------|
| `keyword` | 是 | 搜索词；勿传空串 |
| `search_in` | 否 | 可重复：`title` / `abstract` / `full_text` / `structured`。默认 `title`+`abstract` |
| `conference` | 否 | 会议名模糊匹配，如 `CCS`、`IEEE S&P`、`NDSS`、`USENIX Security` |
| `year` | 否 | 年份整数 |
| `limit` | 否 | 1–100，默认 20 |
| `offset` | 否 | 分页偏移，默认 0 |

说明：

- ASCII 关键词按整词匹配（大小写不敏感）；非 ASCII（如中文）按子串匹配。
- `search_in=abstract` 会同时匹配中文摘要；`structured` 匹配结构化字段文本。
- 结果按年份、id 降序。

示例：

```bash
curl -sG "http://deepsec.chat/api/papers/search" \
  --data-urlencode "keyword=fuzzing" \
  -d "search_in=title" -d "search_in=abstract" \
  -d "conference=CCS" -d "year=2024" -d "limit=10"
```

### 列表 / 结构化筛选

`GET /api/papers/all`

无关键词时浏览或按结构化标签筛选。

| 参数 | 必填 | 说明 |
|------|------|------|
| `conference` / `year` | 否 | 同上 |
| `maturity` | 否 | 成熟度英文枚举（见下） |
| `application_scenario` | 否 | 应用场景关键词（中英文均可） |
| `attack_surface` | 否 | 攻击面关键词（中英文均可） |
| `limit` | 否 | 1–1000，默认 20 |
| `offset` | 否 | 默认 0 |

`maturity` 取值：

| 值 | 含义 |
|----|------|
| `RESEARCH_PROPOSAL` | 理论/算法提出 |
| `RESEARCH_PROTOTYPE` | 研究原型 |
| `LAB_SIMULATION_EVALUATION` | 实验/仿真评估 |
| `FORMAL_VERIFICATION` | 形式化验证 |
| `USER_STUDY` | 用户研究 |
| `PILOT_VALIDATION` | 现场试点/产业验证 |
| `DEPLOYED_IN_PRODUCTION` | 生产部署 |
| `LARGE_SCALE_EMPIRICAL` | 大规模实证 |

### 按作者

`GET /api/papers/by-author`

参数：`author`（必填，模糊匹配）、可选 `conference`、`year`、`limit`(1–100)、`offset`。

### 按机构

`GET /api/papers/by-institution`

参数：`institution`（必填，在作者字段中模糊匹配）、可选 `conference`、`year`、`limit`(1–100)、`offset`。

### 单篇详情

`GET /api/papers/{paper_id}`

返回单篇 `Paper` 对象；不存在时 404。

### 元数据

| 接口 | 返回 |
|------|------|
| `GET /api/conferences` | `string[]` 会议名 |
| `GET /api/years` | `int[]` 年份（降序） |
| `GET /api/application-scenarios` | `string[]` 常用应用场景（中文） |
| `GET /api/attack-surfaces` | `string[]` 常用攻击面（中文） |

## 响应结构

列表类接口统一为：

```json
{
  "total": 41,
  "papers": [ /* Paper */ ]
}
```

`Paper` 字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 论文 ID |
| `title` | string | 标题 |
| `authors` | string \| null | 作者（可能含机构信息） |
| `abstract` | string \| null | 英文摘要 |
| `url` | string | 原文链接 |
| `conference` | string | 会议 |
| `year` | int | 年份 |
| `chinese_summary` | string \| null | 中文概要（可能为空） |
| `chinese_abstract` | object \| string \| null | 结构化中文解读，或纯文本 |
| `structured_info` | object \| null | 成熟度 / 应用场景 / 攻击面 |

`chinese_abstract` 常见对象键：`scenario_zh`、`problem_zh`、`existing_issues_zh`、`approach_zh`、`validation_zh`。

`structured_info` 常见形状：

```json
{
  "maturity": { "en": "LAB_SIMULATION_EVALUATION", "zh": "实验/仿真评估" },
  "application_scenarios": { "en": ["Fuzzing"], "zh": ["模糊测试"] },
  "attack_surfaces": { "en": ["Memory Safety Vulnerability"], "zh": ["内存安全漏洞"] }
}
```

## 选用策略

| 用户意图 | 接口 |
|----------|------|
| 按主题/技术词找论文 | `/api/papers/search` |
| 只要某会议/年份/成熟度/场景列表 | `/api/papers/all` |
| 找某人的论文 | `/api/papers/by-author` |
| 找某学校/机构的论文 | `/api/papers/by-institution` |
| 看一篇完整信息 | `/api/papers/{id}` |

## 检索策略（速度与命中）

### 关键词：英文优先

- **主查询必须优先用较短英文技术词**（领域通行说法），例如：`broken access control`、`IDOR`、`BOLA`、`fuzzing`，而不是先搜宽泛中文（如「越权」——易假阳性且索引弱）。
- 用户用中文提问时：先映射到 1–3 个英文术语再搜；中文词仅作**补充**（`structured` / 中文摘要），不要单独作为唯一首轮关键词。
- 结果偏少时再：放宽 `search_in`（加 `full_text` 或 `structured`）、去掉会议/年份限制、换近义词。

### 并发查询（鼓励）

- **允许且鼓励**同一轮并行多个 HTTP 请求：多英文近义词、`/api/papers/search` + `/api/papers/all` 标签筛选、作者/机构等互不依赖的查询。
- 实现方式任选其一即可：
  - 单个 Shell 内用后台 `&` + `wait`，或 `python`/`curl` 并发；
  - 或多个独立 Shell / 工具调用并行发出。
- 合并结果时按 `id` 去重，再按相关度/年份整理展示；单次报告仍建议 ≤30 篇。
- 详情补全（`/api/papers/{id}`）也可对缺失字段的若干篇并行拉取。

## HTML 报告（可选，需用户明确要求；需本机 Python 2.7+ 或 3.x）

**默认跳过本段。** 检索与对话总结不生成 HTML。仅当用户明确要求（如「生成 HTML 报告」「本地预览」「导出报告」）时才执行。

检索与对话总结**不依赖** Python。仅在按需生成 HTML 报告 / 本地预览时需要解释器。

### Python 前置检查（必须）

生成 HTML 前先检查本机是否有可用的 `python` / `python3` / `python2`（脚本已兼容 **Python 2.7+ 与 Python 3.x**，仅用标准库）：

```bash
PY="$(command -v python3 || command -v python || command -v python2 || true)"
[ -n "$PY" ] && "$PY" -c 'import sys; print(sys.version)'
```

- **有可用解释器**：用该解释器继续生成 HTML 并起本地预览（优先 `python3`，否则 `python` / `python2`）。
- **没有**：不要安装、不要用其他方式硬生成 HTML；只在对话里给文字总结，并简短说明「本机无 Python，已跳过 HTML 报告」。

### 生成步骤（仅当用户要求 HTML 且有 Python）

1. 将论文写成 JSON：

```json
{
  "query": "用户检索意图简述",
  "total": 41,
  "papers": [ /* 完整 Paper 对象 */ ]
}
```

   - 列表不够完整时再调 `/api/papers/{id}` 补全。
   - 写入：`deepsec-papers/<slug>-<timestamp>.json`

2. 渲染 HTML（将 `$PY` 换为上面检测到的解释器）：

```bash
"$PY" "$SKILL_DIR/scripts/render_papers_html.py" \
  deepsec-papers/<slug>.json \
  -o deepsec-papers/<slug>.html \
  --title "DeepSec：<检索主题>"
```

3. **仅绑定本机回环地址**启动静态服务（禁止 `0.0.0.0` / 局域网网卡）：

```bash
URL=$("$PY" "$SKILL_DIR/scripts/serve_report.py" deepsec-papers/<slug>.html)
echo "$URL"
# 形如：http://127.0.0.1:8765/<slug>.html
```

`serve_report.py` 固定 `--bind 127.0.0.1`，只监听本地，不对外网/局域网暴露。

4. 展示给用户：
   - 用 `open_resource` 打开该 `http://127.0.0.1:...` URL（按网页渲染）。
   - 对话里用 Markdown 链接写出同一 URL。
   - **不要**把工作区 `.html` 路径或 `file://` 当作主入口。

### 展示内容与样式要求

- **必须**使用 `scripts/render_papers_html.py` + `assets/paper-report.css`。
- 卡片结构对齐官网：标题链接、作者 / 年份 / 会议、摘要折叠、结构化标签、五段中文解读（场景 / 问题 / 现有方法的局限 / 新理念和思路 / 验证结果）。
- 默认展开摘要；需要折叠时加 `--collapse`。
- 单次报告建议 ≤30 篇。

## 回答格式

先给 1–2 句总览（命中 `total`、筛选条件、本次展示篇数）。

### 本次展示 ≤ 20 篇：详细卡片式文字

对每篇用固定小卡片结构（便于扫读），优先中文结构化字段；缺省再退回英文摘要前 2–3 句：

```markdown
### 1. <标题>
<会议> · <年份> · [原文](<url>)

- 作者：...
- 标签：成熟度 / 应用场景 / 攻击面（有则写）
- 问题：...
- 方法：...
- 结果：...（有 validation 则写；否则可省略）
```

规则：

- 「问题」取 `problem_zh`；「方法」取 `approach_zh`；「结果」取 `validation_zh`。
- 若无结构化中文，用 `chinese_summary` 一段，或英文 `abstract` 压缩为 2–3 句，不要整段粘贴超长摘要。
- 篇与篇之间空一行；不要做成难扫的大表。

### 本次展示 > 20 篇：精简列表

每篇一行要点即可：

```markdown
1. **标题** — 会议 年份 — [原文](url)
   一句话要点（问题或方法）
```

并说明命中总数与「可翻页 / 可再缩小范围」。

### 其他

- **默认不附 HTML**；仅用户明确要求且本机有 Python 时，才附上 `http://127.0.0.1:...` 预览链接。
- 不要编造未出现在 API 结果中的论文。
- 不要向用户展示本 skill 未列出的内部接口，也不要讨论系统实现细节。
