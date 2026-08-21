# Runtime Data

`var/` 是本项目所有应用运行数据的唯一默认根目录。

预期布局：

```text
var/
├── db/          # SQLite
├── uploads/     # 用户输入素材
├── outputs/     # 生成视频、音频、缩略图和 sidecar metadata
├── runs/        # Workflow/Run 快照和执行日志
├── cache/       # Hugging Face、Torch、SGLang 等项目缓存
├── logs/        # 服务日志
└── tmp/         # 临时文件
```

除本说明文件外，`var/` 下内容均被 `.gitignore` 排除。

规则：

- 应用不得默认将运行数据写入用户主目录或系统临时目录
- 启动入口应设置 `HF_HOME`、`TORCH_HOME`、`XDG_CACHE_HOME` 和 `TMPDIR`
- 生成媒体本身已压缩时，不再进行无收益的二次压缩
- 大型 JSON 快照和已完成日志可以按阈值压缩
- 删除 Run 时应通过 artifact 索引清理关联文件
- 现有外部模型目录不复制到 `var/`
