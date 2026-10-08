---
name: cell_cns_design
description: 将科研文字提交到 Cell Figure DS 的10额度接口，独立Python后台接收PNG并唤醒原聊天展示结果；用于客户收发，不在客户端生图。
---

# cell_cns_design

科研文字 → 网站独立接口 → 后台等待 → 原聊天展示 PNG。

- 仅接受科研文字；无文字只问“请提供科研文字。”图片任务不提交此接口。
- 每个新订单10额度；同一请求重试不重复扣费，查询和下载免费。已有本图10额度授权直接使用，否则提交前只问“本次10额度，继续吗？”
- 输出为PNG，不要求用户选择PPT或AI，不做矢量转换。
- 此 Skill 的任务包含“结果返回后通知原聊天继续”的授权。只通知原聊天；真实 `CODEX_THREAD_ID` 必须持久化，不能借用其他聊天ID。
- 客户只使用个人登录号，不使用服务端或管理员密钥。已有客户凭据可直接使用；缺失时询问登录号，通过stdin交给configure-key，保存DPAPI密文，不复述密钥。

## 提交

读取[客户端命令](references/client.md)。保存文字为UTF-8，确定独立job-dir，核对10额度授权。运行probe确认桌面原聊天可达，balance读取实时可用额度；submit先保存request_id、原文哈希及账户身份，再提交并启动独立Python等待。

收到 `charged_credits=10` 与 `background_waiter_verified=true` 后，只提示“已提交，结果返回后自动继续。”并结束本轮。结果不明时保留原目录、原request_id，不能另建订单再次收费。独立进程与Windows登录恢复负责等待，不创建Codex定时任务。

## 结果返回

1. 读取回执中的原目录job.json，确认service为 `/api/cell_figure_ds`、当前聊天等于thread_id。运行acknowledge核对nonce。
2. 有有效PNG时实际打开查看，确认完整显示。运行complete --visual-checked记录交付；它会再次完整解码并核对下载哈希。
3. 回复“已完成。”，嵌入最终PNG绝对路径图像并给文件链接。客户不需要执行后处理。
4. 回执为异常时简短说明真实原因并保留订单；修复后resume接续原订单。通知响应不明时先检查原聊天，不盲目重复发送。停止仅停止本地等待，不声称远端取消或退款。

维护本Skill时不创建真实收费测试订单。可做隔离本地HTTP、模拟队列、只读桌面连接测试。
