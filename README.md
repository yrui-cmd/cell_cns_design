# cell_cns_design

科研文字绘图客户端：提交摘要或绘图要求，无窗口后台接收 PNG，完成后在原 Codex 聊天展示。

提交后显示 **10 分钟预估进度条**；超时保持99%继续等待，收到并校验图片后到100%。

**每个新任务 10 额度。** 支持断线恢复，同一请求重试不重复扣费。客户端源码采用 [MIT 许可证](LICENSE)，绘图服务单独收费。

## 安装

需要 Windows、Python 3.10+、Node.js 和已登录的 Codex 桌面。

将仓库放入 Codex 的 skills 目录：

```powershell
$skillRoot = if ($env:CODEX_HOME) { Join-Path $env:CODEX_HOME 'skills' } else { Join-Path $env:USERPROFILE '.codex/skills' }
git clone https://github.com/yrui-cmd/cell_cns_design.git (Join-Path $skillRoot 'cell_cns_design')
python -m pip install -r (Join-Path $skillRoot 'cell_cns_design/scripts/requirements.txt')
```

## 使用

在 Codex 中调用 `$cell_cns_design`，提供科研文字，自动检测本地已保存的 API Key，缺失时再配置，确认费用即可。

[详细命令](references/client.md) · [网页入口](https://xiaomiao-ai.com/cell_figure_ds)

客户端固定连接 Cell Figure DS 服务；原文会发送到该服务用于绘图。自动唤醒依赖 Codex 桌面本机接口，桌面更新后可能需要适配。

## 测试

```powershell
python -m unittest discover -s tests
```

测试使用本地模拟数据，不提交收费订单。
