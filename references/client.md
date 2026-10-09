# 客户端命令

使用 Python 3.10+，并安装 scripts/requirements.txt。脚本相对本Skill目录为 `scripts/client.py`。后台唤醒需要已登录同一Windows用户的Codex桌面。

以下命令从本Skill根目录运行：

```powershell
python -X utf8 ./scripts/client.py probe
python -X utf8 ./scripts/client.py balance
python -X utf8 ./scripts/client.py submit --text-file '<原文路径>' --job-dir '<独立目录>' --thread-id $env:CODEX_THREAD_ID --credits-approved 10 --authorize-wake
```

首次configure-key通过stdin接收客户 API Key；可用 `--credential-file` 指向已存在的客户DPAPI密文。默认文件为当前Windows用户LocalAppData/Xiaomiao/cell_figure_ds-customer.txt。接口固定，无地址切换选项。

后台命令：`status --job-dir ...`、`stop --job-dir ...`、`resume --job-dir ...`、`acknowledge --job-dir ... --nonce ...`、`complete --job-dir ... --visual-checked`。所有路径需用实际值替换。

resume必须从原聊天运行。已有PNG会返回 `deliver_existing_png`，直接展示完成；未收到则继续查询原订单。`wake_uncertain`需要先核实原聊天回执再acknowledge，不自动重复发送。配置错误修复后沿用原目录恢复，不能换客户身份。

保存：原文requirements.txt、持久状态job.json、收到的result.png与日志均在job-dir。客户端保留最终PNG；后台核对SHA256和完整解码后才发送原聊天通知。

自动检测：`python -X utf8 ./scripts/client.py discover-key`。返回可用凭据路径，不输出密钥、不查询余额。顺序为显式路径、本分支DPAPI文件、实际桌面xiaomiao_api.txt、其他已知绘图分支同一客户Key。已选择的文件无效时停止，不切换账户。提交前传同一路径执行balance实时校验；恢复已有任务继续使用其job.json记录的路径。

无窗口监控：Windows Python 安装必须包含同目录的 pythonw.exe。首次提交会自动安装并启动；更新旧版后可先运行 `setup-waiter` 替换原来的每分钟 PowerShell 恢复任务，无需创建新订单。登录时启动常驻 Python，每30秒检查已有订单；重复安装不会重复监控，也不打断正在等待的任务。监控心跳写入当前用户 LocalAppData/CellFigureDsClient/recovery-monitor.json。
