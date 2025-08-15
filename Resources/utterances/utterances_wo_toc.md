# utterances.md

版本：v1.0  
最后更新：2025-08-14

> 本文档用于**话术模板（应该怎么说）**，与 `flows.md` 通过相同的 `category / subcategory / id` 精确映射。  
> **变量占位符**（对外展示均已脱敏）：
>
> - 订单：`{order_id} {status} {tracking_no} {carrier} {eta} {item_summary} {total_amount} {created_at}`
> - 用户：`{user_name_masked} {email_masked} {phone_masked}`
> - 地址：`{address_masked} {address_new_masked}`
> - 退货：`{RMA} {refund_amount} {no_reason_days} {quality_days} {refund_sla_days} {policy_link}`
> - 发票/工单：`{invoice_type} {invoice_deadline} {invoice_issue_days} {ticket_id}`
> - 物流/时效：`{warehouse_process_hours} {city_days_min} {city_days_max} {province_days_min} {province_days_max} {cross_days_min} {cross_days_max} {remote_days_min} {remote_days_max}`
> - 其他：`{restock_days}` 等
>
> **注意**：若某变量在当前上下文缺失，请用“暂无/正在刷新”自然化表述或走澄清问句。

---

## 1. 订单相关（orders）

### 1.1 查询订单状态（id: `orders.status_query`）

**neutral**

> 已为您查询到订单 **{order_id}**：当前状态 **{status}**。
>
> - 商品：{item_summary}，金额 ¥{total_amount}
> - 下单时间：{created_at}
> - 收货地址：{address_masked}  
>   {# 有运单 #}物流单号 **{tracking_no}**（承运商：{carrier}），预计 **{eta}** 送达。  
>   {# 无运单 #}该订单尚未生成运单，预计在 **{warehouse_process_hours} 小时**内出库。  
>   如需修改地址或加急处理，我可以继续协助。

**empathetic**

> 能理解您着急确认进度的心情。我这边查到订单 **{order_id}** 的状态是 **{status}**。  
> {# tracking 有/无分支同上，语气更柔和 #}  
> 如果您的收件安排有变，我可以帮您改约、尝试拦截或联系承运商加速，您看哪种更合适？

**formal**

> 经核验账号与订单归属，订单 **{order_id}** 当前状态为 **{status}**。  
> {# tracking 有/无分支同上，措辞克制 #}  
> 如需办理地址变更、改约投递或售后，请明确需求，我方将按流程协助。

---

### 1.2 修改收货地址（id: `orders.address_update`）

**neutral**

> 可以为订单 **{order_id}** 变更收货地址：
>
> - 原地址：{address_masked}
> - 新地址：{address_new_masked}
> - 当前状态：**{status}**  
>   未发货订单将直接更新；已发货订单会向承运商申请改派（成功需以承运商反馈为准）。是否确认提交？

**empathetic**

> 明白您临时需要改地址的紧急情况。订单 **{order_id}** 目前 **{status}**。  
> 若未发货，我可立即更新为 **{address_new_masked}**；若已发货，我会马上发起拦截改派并持续跟进，第一时间同步结果。请问现在为您提交吗？

**formal**

> 关于地址变更申请：订单 **{order_id}** 处于 **{status}**。  
> 未发货可直接变更为 **{address_new_masked}**；已发货仅可尝试承运商改派/拦截且不承诺成功。请书面确认是否提交。

---

### 1.3 申请退货（id: `orders.return_request`）

**neutral**

> 我可以为订单 **{order_id}** 发起退货：
>
> - 无理由退货：**{no_reason_days}** 天内；质量问题：**{quality_days}** 天内（详见 {policy_link}）
> - 预计退款：¥{refund_amount}，**{refund_sla_days}** 个工作日内原路退回
> - 退回方式：上门取件 / 自行寄回  
>   请确认退货原因（可上传照片/视频），我现在为您创建 **RMA**。

**empathetic**

> 抱歉让您失望了，我会尽快帮您处理退货。根据政策：无理由 **{no_reason_days}** 天、质量问题 **{quality_days}** 天；预计退款 **¥{refund_amount}**，**{refund_sla_days}** 个工作日内原路退回。您更倾向上门取件还是自行寄回？我立即为您提交。

**formal**

> 已知悉您对订单 **{order_id}** 的退货需求。按现行政策（{policy_link}），预计退款 **¥{refund_amount}**，将在 **{refund_sla_days}** 个工作日内原路退回。请确认退货原因及取件方式，以便创建 **RMA**。

---

## 2. 规则相关（rules）

### 2.1 退换货政策（id: `rules.return_policy`）

**neutral**

> 我们的退换货规则如下：
>
> - 无理由：**{no_reason_days}** 天内，商品完好、未影响二次销售；
> - 质量问题：**{quality_days}** 天内可退/换（需问题证明）；
> - 不可退：定制/虚拟/易耗等品类；
> - 运费：质量问题由商家承担；无理由由用户承担；
> - 退款：仓检通过后 **{refund_sla_days}** 个工作日内原路退回。  
>   详细条款见：{policy_link}。

**empathetic**

> 为了减少您的不便，我把关键点精炼为：无理由 **{no_reason_days}** 天、质量问题 **{quality_days}** 天、退款 **{refund_sla_days}** 个工作日内原路退回。若需要，我可以结合您的订单情况逐条核对是否符合条件。

**formal**

> 依据当前生效的退换货政策（{policy_link}）：无理由期限 **{no_reason_days}** 天；质量问题期限 **{quality_days}** 天；退款在仓检通过后 **{refund_sla_days}** 个工作日内原路退回。不可退品类与运费承担方式以条款为准。

---

### 2.2 物流时效（id: `rules.shipping_sla`）

**neutral**

> 时效参考：付款后 **{warehouse_process_hours}** 小时内出库；同城 **{city_days_min}-{city_days_max}** 天、省内 **{province_days_min}-{province_days_max}** 天、跨省 **{cross_days_min}-{cross_days_max}** 天、偏远 **{remote_days_min}-{remote_days_max}** 天。最终以承运商轨迹为准。

**empathetic**

> 我理解您希望尽快收到包裹。一般会在 **{warehouse_process_hours}** 小时内出库；随后同城约 **{city_days_min}-{city_days_max}** 天、跨省约 **{cross_days_min}-{cross_days_max}** 天。需要的话，我可以马上帮您查实时轨迹。

**formal**

> 履约标准如下：仓内处理 **{warehouse_process_hours}** 小时；区域派送时效见公示区间（同城/省内/跨省/偏远）。最终以承运商派送记录为准。

---

### 2.3 支付方式（id: `rules.payment_methods`）

**neutral**

> 支持银行卡与主流第三方支付（支付宝/微信/PayPal/Apple Pay 等，视站点而定），部分渠道支持分期。若支付失败，常见原因为额度、风控、网络或 3D 验证问题。退款均原路退回，预计 **{refund_sla_days}** 个工作日内到账。

**empathetic**

> 支付遇到问题会让人着急。我这边支持多种渠道，也可以一起排查失败原因，并提供替代通道；退款会原路退回，通常 **{refund_sla_days}** 个工作日内完成。

**formal**

> 可用支付渠道以结算页展示为准；退款遵循“原路退回”，预计 **{refund_sla_days}** 个工作日内到帐。若支付失败，请更换渠道或提供失败码以便核验。

---

## 3. 售后相关（aftersales）

### 3.1 投诉处理（id: `aftersales.complaint`）

**neutral**

> 已为您登记投诉，工单编号 **{ticket_id}**。严重问题 4 小时内响应，一般问题 24 小时内响应，通常 1–3 个工作日给出结果或阶段性说明。期间如需补充资料（截图/录音/快递凭证），直接发给我即可。

**empathetic**

> 很抱歉给您带来不佳体验。我已创建投诉工单 **{ticket_id}**，会持续跟进并第一时间向您同步进展。如果方便，您也可以补充更多证据，便于我们更快核实。

**formal**

> 投诉已受理（工单 **{ticket_id}**）。我方将依据分级响应机制进行处理，并在承诺时限内反馈结果。请按需提供佐证材料以便核验。

---

### 3.2 发票申请（id: `aftersales.invoice`）

**neutral**

> 可为订单 **{order_id}** 开具 **{invoice_type}**。申请期限至 **{invoice_deadline}**；审核通过后 **{invoice_issue_days}** 个工作日内开具并发送至 {email_masked}（纸票则需邮寄地址）。请提供抬头（个人/公司）、税号等信息，我现在为您提交。

**empathetic**

> 没问题，我来帮您尽快开票。您把抬头、税号和接收邮箱发我即可；我们通常会在 **{invoice_issue_days}** 个工作日内完成。如有时间节点要求，也欢迎提醒我提前关注。

**formal**

> 按您的申请，可为订单 **{order_id}** 开具 **{invoice_type}**。请提供抬头与税务信息；审核通过后预计 **{invoice_issue_days}** 个工作日内开具并发送至 {email_masked}。

---

### 3.3 缺货处理（id: `aftersales.oos_handling`）

**neutral**

> 非常抱歉出现缺货。您可以选择：
>
> 1. 等待补货（预计 **{restock_days}** 天）；2) 立即取消并全额退款；3) 换同等或更高价值商品（差额我们承担或发放补偿券）。请告知您的选择，我这边马上处理。

**empathetic**

> 给您添麻烦了，真的抱歉。为不耽误您的使用，我们提供三种方案（等补货/退款/替代商品），您更倾向哪种？我会全程跟进，确保结果落实。

**formal**

> 因库存异常无法按期发货，现提供替代方案：等待补货（约 **{restock_days}** 天）/取消并退款/同价或更高价替换。请确认选项以便执行。
