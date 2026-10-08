# 客户端命令

使用 Python 3.10+，并安装 scripts/requirements.txt。脚本相对本Skill目录为 `scripts/client.py`。后台唤醒需要已登录同一Windows用户的Codex桌面。

以下命令从本Skill根目录运行：

```powershell
python -X utf8 ./scripts/client.py probe
python -X utf8 ./scripts/client.py balance
python -X utf8 ./scripts/client.py submit --text-file '<原文路径>' --job-dir '<独立目录>' --thread-id $env:CODEX_THREAD_ID --credits-approved 10 --authorize-wake
```

首次configure-key通过stdin接收客户登录号；可用 `--credential-file` 指向已存在的客户DPAPI密文。默认文件为当前Windows用户LocalAppData/Xiaomiao/cell_figure_ds-customer.txt。接口固定，无地址切换选项。

后台命令：`status --job-dir ...`、`stop --job-dir ...`、`resume --job-dir ...`、`acknowledge --job-dir ... --nonce ...`、`complete --job-dir ... --visual-checked`。所有路径需用实际值替换。

resume必须从原聊天运行。已有PNG会返回 `deliver_existing_png`，直接展示完成；未收到则继续查询原订单。`wake_uncertain`需要先核实原聊天回执再acknowledge，不自动重复发送。配置错误修复后沿用原目录恢复，不能换客户身份。

保存：原文requirements.txt、持久状态job.json、收到的result.png与日志均在job-dir。客户端保留最终PNG；后台核对SHA256和完整解码后才发送原聊天通知。
