# Cellular MQTT (ATK-D40-B) 功能更新说明

## 1. UI 布局系统化 (Systematized UI Layout)
Cellular MQTT 标签页的布局已与 Internet MQTT 标签页实现完全统一，提升了用户体验的一致性：
- **紧凑化布局**：COM 端口配置、Topic、QoS 选项均采用了同行多列的紧凑设计，去除了多余的空行和冗余的文本标签，彻底解决了页面溢出问题。
- **防止竞态条件 (Race Condition)**：`Subscribe`, `Unsub`, `Publish` 以及 `Clear` 等操作按钮已全面重构为 `on_click` 回调模式。这意味着即使用户开启了 `Auto RX` 后台高频刷新，按钮的点击事件也不会被系统刷新循环吞噬，确保操作必定生效。

## 2. 动态订阅管理 (Dynamic Subscription Management)
在保持透明传输（Transparent Mode）特性的同时，增加了动态修改 DTU 硬件底层订阅配置的能力：
- **Subscribe 按钮**：动态打断透明传输，通过 `+++` 和 `ATK` 进入硬件配置模式，向 DTU 发送 `AT+MQTTSUB1` 指令修改订阅通道，完成后自动通过 `ATO` 恢复透明传输。
- **Unsub 按钮**：同样通过 AT 指令动态发送 `AT+MQTTSUB1="0","<topic>","0"`，从 DTU 硬件中移除指定订阅。
- **状态同步显示**：页面中的 `ACTIVE` 栏位会与底层 AT 指令的返回状态（`OK` 或 `ERROR`）保持一致。只有 DTU 真正接受了指令，页面才会显示当前活跃的订阅通道。

## 3. 纯净硬件通信日志 (Pure Hardware Communication Logs)
移除了日志中所有无关的系统提示（如表情符号、诊断辅助文本），将其打造为专业的串口分析工具：
- **拦截底层读写**：现在日志系统直接拦截串口的实际字节流。
- **TX>> 与 RX<< 模式**：所有发出的 AT 指令和透传 Payload 均会以 `[时间戳] TX>> <数据>` 的原始格式呈现，收到的回应同样以 `RX<< <数据>` 呈现。
- 帮助用户直观地观察 DTU 在透传模式和指令模式之间切换的完整握手过程，便于排查如 `Please check GPRS !!!` 等硬件级网络警告。

## 4. 透传发布机制 (Transparent Publish Mechanism)
- 当前 `Publish` 按钮采用的是**瞬间透传模式**。当 DTU 配置完毕后，发送的消息无需经过任何额外的 AT 指令包装，直接推入串口即可被 DTU 发送至其固化在内存中的发布主题（`PUB1`）。
- 该模式确保了数据发送的最高实时性（延迟为毫秒级），避免了每次发送都需进出 AT 模式所带来的 3-4 秒阻滞。
