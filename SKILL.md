---
slug: local-memory
name: local-memory
displayName: 本地向量图谱记忆
version: 1.0.0
description: |
  基于 LanceDB + Kuzu 的本地记忆 MCP Server。
  支持向量语义检索、知识图谱关系、短期/长期记忆分层、自动清理与合并。
  所有数据保存在 ~/.kimi-memory/，可用于 Kimi Code / workbuddy / Cursor 等 Agent 共享记忆。
examples:
  - 记住我喜欢用 TypeScript
  - 搜索之前关于数据库选型的记忆
  - 列出我的所有长期记忆
  - 清理 30 天前的短期记忆
  - 备份记忆到百度网盘
---

# 前置条件

| 依赖 | 用途 | 验证方式 |
|------|------|----------|
| Python 3.10-3.13 | 运行 MCP Server | `python --version` |
| 约 2.5GB 磁盘空间 | 环境 + 模型 + 数据 | 首次安装需要 |

# 触发条件

**日常记忆操作：**
- 用户说"记住这个"、"记下来"、"记录一下"、"别忘了"
- 用户说"你还记得吗"、"之前说过什么"、"回忆一下"
- 用户分享关键信息并要求记忆（偏好、决策、环境配置）
- 用户说"永远记住"、"这个很重要"

**记忆管理：**
- 用户要求清理/删除/合并记忆
- 用户要求备份记忆

**安装与配置：**
- 用户要求安装/配置本地记忆 MCP
- 排查本地记忆 MCP Server 问题

# 工具速查表

## 记忆管理

| 工具 | 功能 | 关键参数 |
|------|------|----------|
| add_memory | 存储新记忆 | content, memory_type, source, topic_tags |
| search_memories | 语义搜索记忆 | query, top_k, memory_type |
| get_memory_context | 向量+图谱综合检索 | query, top_k |
| list_memories | 列出最近记忆 | limit, memory_type |
| update_memory | 更新已有记忆 | memory_id, content, memory_type, topic_tags |
| delete_memory | 删除记忆 | memory_id |
| promote_memory | 短期记忆升级为长期 | memory_id |
| decay_memories | 清理过期短期记忆 | days |
| consolidate_memories | 合并相似短期记忆 | - |
| search_graph | 按图谱关系搜索 | topic, project, tool, memory_id, depth |

## 备份统计

| 工具 | 功能 | 关键参数 |
|------|------|----------|
| backup_memories | 导出 JSONL 备份 | - |
| memory_stats | 查看记忆统计 | - |

# 默认值

| 参数 | 默认值 | 说明 |
|------|--------|------|
| decay_days | 30 | 冷记忆清理阈值（天） |
| search_top_k | 5 | 搜索返回条数 |
| list_page_size | 20 | 列表每页条数 |
| memory_type | short_term | 新记忆默认为短期 |
| embedding_model | BAAI/bge-small-zh-v1.5 | 本地中文 Embedding 模型 |

# 存储说明

- **向量存储**：LanceDB 的 `memories` 表，保存记忆原文和 512 维向量。
- **图谱存储**：Kuzu 保存记忆节点与 Topic / Project / Tool / Person / 时间线关系。
- **数据目录**：`~/.kimi-memory/`，包含 `lancedb/`、`kuzu/`、`models/`、`backups/`。
- **备份**：运行 `python scripts/backup.py` 可导出 `memories.jsonl` 并打包数据目录到百度网盘同步空间。

# 安装流程

```bash
cd ~/.kimi-code/skills/local-memory-mcp
python scripts/install.py
```

安装完成后重启 Kimi Code CLI。

# 故障排除

| 错误场景 | 原因 | 解决方式 |
|----------|------|----------|
| Python not found | 系统未安装 Python 或不在 PATH | 安装 Python 3.10-3.13 |
| 模型下载失败 | 网络问题 | 设置 HF_ENDPOINT=https://hf-mirror.com 或手动下载模型到 ~/.kimi-memory/models/ |
| 搜索无结果 | 数据库为空 | 先调用 add_memory 写入记忆 |
| LanceDB/Kuzu 报错 | 多进程同时访问 | 确保只有一个 MCP Server 实例在运行 |
| 备份失败 | 百度网盘同步目录未找到 | 使用 `--target` 指定目录 |

# 安全约束

- 禁止在源码中 hardcode 凭据（本服务无需凭据）。
- 写入记忆前会过滤 `<private>...</private>` 内容。
- 所有数据本地存储，不上传云端。
