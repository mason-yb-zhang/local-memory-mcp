# local-memory-mcp

本地向量 + 知识图谱记忆 MCP Server，基于 [LanceDB](https://lancedb.com/) 和 [Kuzu](https://kuzudb.com/)。

所有数据保存在本地 `~/.kimi-memory/`，不依赖外部云服务，适合给 Kimi Code、workbuddy、Cursor 等 Agent 提供跨会话共享记忆。

## 特性

- **向量语义检索**：使用 BGE 中文 Embedding 模型，支持同义词召回
- **知识图谱关系**：用 Kuzu 存储记忆之间的主题、项目、工具、时间关系
- **短期 / 长期记忆**：自动分层，支持 promote、decay、consolidate
- **跨 Agent 共享**：通过 MCP 协议接入任意支持 MCP 的 Agent
- **本地备份**：一键导出 JSONL + 打包数据目录到百度网盘同步空间

## 快速开始

```bash
cd ~/.kimi-code/skills/local-memory-mcp
python scripts/install.py
```

安装脚本会：
1. 创建 Python 虚拟环境
2. 安装 LanceDB、Kuzu、sentence-transformers 等依赖
3. 预下载 BGE-small 中文 Embedding 模型
4. 注册 MCP Server 到 Kimi Code

然后**重启 Kimi Code CLI**即可使用。

## 数据目录

```
~/.kimi-memory/
├── lancedb/     # 向量数据库
├── kuzu/        # 图数据库
├── models/      # 本地 Embedding 模型
├── backups/     # 备份文件
└── config.yaml  # 配置文件
```

## 备份

```bash
# 导出 JSONL 并打包到百度网盘同步目录
python scripts/backup.py

# 只导出 JSONL
python scripts/backup.py --jsonl-only

# 指定目标目录
python scripts/backup.py --target D:\\Backups\\kimi-memory
```

## 环境变量

| 变量 | 说明 | 默认值 |
|---|---|---|
| `LOCAL_MEMORY_DATA_DIR` | 数据根目录 | `~/.kimi-memory` |
| `LOCAL_MEMORY_EMBEDDING_MODEL` | Embedding 模型 | `BAAI/bge-small-zh-v1.5` |
| `LOCAL_MEMORY_DEFAULT_TOP_K` | 默认搜索条数 | `5` |
| `LOCAL_MEMORY_DEFAULT_DECAY_DAYS` | 短期记忆过期天数 | `30` |

## License

MIT
