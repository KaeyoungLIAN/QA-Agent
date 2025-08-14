# flows.md
版本：v1.0  
最后更新：2025-08-14

> 本文档用于**流程逻辑（应该怎么做）**，与 `utterances.md` 通过完全一致的 `category / subcategory / id` 做一一映射，方便在 RAG 中进行“流程 + 话术”的组合生成。

---

## 顶层配置（可按需修改并在系统初始化时注入）
```yaml
vars:
  no_reason_days: 7             # 无理由退货期（自然日）
  quality_days: 15              # 质量问题退换期限（自然日/或按内部政策设定）
  refund_sla_days: 3            # 仓检通过后退款原路退回的承诺时效（工作日）
  invoice_apply_days: 90        # 允许申请发票的最长期限（自然日）
  invoice_issue_days: 2         # 发票审核通过后开具的承诺时效（工作日）

  warehouse_process_hours: 24   # 付款到出库的承诺时长（小时）
  city_days_min: 1
  city_days_max: 2
  province_days_min: 2
  province_days_max: 3
  cross_days_min: 3
  cross_days_max: 5
  remote_days_min: 4
  remote_days_max: 7

  restock_days: 5               # 缺货补货参考时长（自然日）
  policy_link: https://example.com/policy/returns
```

---

## 数据模型与安全
- 订单表（只列关键字段）：
  - `order_id (PK)`：订单唯一编号（如：`OD2408150001`）
  - `user_id`：用户内部 ID（仅用于权限校验，不向外展示）
  - `user_name (TEXT)`：收货人姓名（对外展示需脱敏或遵循合规）
  - `email (INDEX)`：邮箱（支持邮箱+时间范围检索；对外展示需脱敏）
  - `phone (INDEX)`：手机号（支持手机+时间范围检索；对外展示需脱敏）
  - `status`：状态（如：待支付 / 已支付待发货 / 已发货 / 已签收 / 退款中 / 已退款…）
  - `tracking_no`：运单号（跨系统查询物流）
  - `item_summary`：简要的商品摘要（便于客服和用户快速确认）
  - `total_amount (DECIMAL)`：订单总额
  - `created_at (DATETIME/TIMESTAMP)`：下单时间
  - `address (TEXT)`：收货地址（对外展示需脱敏）

- **隐私与合规模块（必须遵循）**：
  - 对外展示的个人信息一律脱敏：
    - `email` → `z***@example.com`
    - `phone` → `138****0000`
    - `address` → “北京市朝阳区**路**号…”（街道号后脱敏）
  - **严禁跨用户查询**：任意订单读取前必须核验 `user_id == current_user_id` 或完成 OTP 账号验证。
  - **审计与幂等**：修改动作写入审计日志（时间、操作者、变更前后哈希）；对重复指令使用幂等键（如 `order_id + action`）。

- **可调用工具（Agent）**（伪接口说明）：
  - `OrderDB.get(order_id) -> Order`
  - `OrderDB.find_by_contact(contact, start, end) -> [Order]`
  - `OrderDB.update_address(order_id, new_address) -> bool`
  - `LogisticsAPI.get(tracking_no) -> {carrier, events[], eta}`
  - `LogisticsAPI.intercept(tracking_no, new_address) -> {accepted: bool}`
  - `OMS.create_return_request(order_id, reason, attachments) -> {RMA, refund_amount}`
  - `Payment.refund(order_id, amount) -> {accepted: bool}`
  - `Ticket.create(severity, summary, attachments) -> {ticket_id}`
  - `Invoice.request(order_id, type, title, tax_id, email) -> {invoice_id}`
  - `Inventory.promise_or_cancel(order_id, option) -> {ok: bool}`

---

## 目录（统一分类映射）
1. 订单相关（`orders`）
   - 查询订单状态（`orders.status_query`）
   - 修改收货地址（`orders.address_update`）
   - 申请退货（`orders.return_request`）
2. 规则相关（`rules`）
   - 退换货政策（`rules.return_policy`）
   - 物流时效（`rules.shipping_sla`）
   - 支付方式（`rules.payment_methods`）
3. 售后相关（`aftersales`）
   - 投诉处理（`aftersales.complaint`）
   - 发票申请（`aftersales.invoice`）
   - 缺货处理（`aftersales.oos_handling`）

---

## 1. 订单相关（orders）

### 1.1 查询订单状态（id: `orders.status_query`）

**触发意图**  
- 关键词：查订单 / 物流 / 到哪了 / 单号 / 状态 / 快递 / ETA 等

**输入优先级**  
1) `order_id`（首选） → 2) 账号验证 + `email/phone` → 3) 通过 `created_at` 时间范围回溯定位最近订单（回退方案）。

**流程步骤**  
1. **识别与收集**：尝试获取 `order_id`。若缺失，引导用户提供 `email/phone` 与时间范围。  
2. **权限校验**：从 `OrderDB.get(order_id)` 读取，校验 `order.user_id == current_user_id`，否则拒绝并提供 OTP 验证流程。  
3. **信息返回**：返回字段 `status、tracking_no、item_summary、total_amount、created_at、address(脱敏)`。  
4. **物流查询**：若存在 `tracking_no`，调用 `LogisticsAPI.get(tracking_no)` 获取 `carrier/轨迹/eta`。  
5. **状态解释与建议下一步**：
   - 待支付：给出支付指引（链接/入口）。
   - 已支付待发货：提示 `{warehouse_process_hours}` 小时内出库，若需改地址引导到“地址修改”。
   - 已发货：展示物流轨迹与 `eta`，提供拦截/自提/改约送达的可能性（取决于承运商）。
   - 已签收：提示可在 `{vars.no_reason_days}` 内按政策发起退货。
   - 退款中/已退款：展示退款节点与原路退回时效 `{refund_sla_days}`。  
6. **异常分支**：
   - 查无结果 / 多单匹配：要求补充 `order_id` 或更精确的时间范围。  
   - 物流接口超时：返回订单核心状态并声明“物流刷新中”。  
7. **审计与指标**：记录查询耗时、接口成功率、用户满意度标签。

**伪代码**  
```python
order = OrderDB.get(order_id) or locate_by_contact(contact, start, end)
assert_user_access(order, current_user_id)  # raise if fail

resp = {
  "status": order.status,
  "item_summary": order.item_summary,
  "total_amount": order.total_amount,
  "created_at": order.created_at,
  "address_masked": mask(order.address)
}

if order.tracking_no:
    track = LogisticsAPI.get(order.tracking_no)
    resp.update({"tracking_no": order.tracking_no, "carrier": track.carrier, "eta": track.eta})
return resp
```

---

### 1.2 修改收货地址（id: `orders.address_update`）

**前置**  
- 允许：`status ∈ {已支付待发货, 待发货}` → 直接改地址。  
- 已发货：尝试承运商拦截改派（不保证成功）。  
- 已签收：不支持改地址。

**输入**  
- 新地址结构：`{收件人, 手机, 省市区, 详细地址, 邮编}`。必要时二次验证手机号。

**流程步骤**  
1. **订单确认 + 权限校验**：同 1.1。  
2. **可改性判断**：根据状态决定“直接修改 / 尝试拦截 / 不支持”。  
3. **风控校验**：高风险地址策略（频繁变更、黑名单小区、异常邮编等）→ 人工复核队列。  
4. **执行与回执**：
   - 未发货：`OrderDB.update_address(order_id, new_address)`，记录审计日志（旧地址哈希/新地址哈希）。
   - 已发货：`LogisticsAPI.intercept(tracking_no, new_address)`，返回是否受理与预计影响的 `eta` 变化。  
5. **通知与确认**：向原留 `email/phone` 发送变更确认，防止冒用。

**失败处理**  
- 拦截失败：提供改约/自提/签收后退货的替代方案。

---

### 1.3 申请退货（id: `orders.return_request`）

**联动规则**  
- 无理由退货：`{no_reason_days}` 天，保持完好不影响二次销售。  
- 质量问题：`{quality_days}` 天内可退/换，需问题证明（照片/视频）。  
- 特殊类目：定制/食品/虚拟等不支持无理由。退款原路退回，`{refund_sla_days}` 个工作日内到账。

**流程步骤**  
1. **状态核验**：仅 `已签收` 或 `在途拒收` 可走退货；`待发货` 建议取消而非退货。  
2. **资格判断**：根据签收时间/下单时间 + 类目判定是否在退货窗口。  
3. **信息收集**：`reason`（枚举）、`attachments`（图片/视频/面单）、退回方式（上门揽收/自寄）。  
4. **创建 RMA**：`OMS.create_return_request(order_id, reason, attachments)` → 得到 `{RMA, refund_amount}` 与退回地址。  
5. **退款规则**：根据责任方判定运费是否退还；明确到账时效 `{refund_sla_days}`。  
6. **跟踪与闭环**：仓检通过 → 触发退款；不通过 → 说明原因并提供申诉通道。  
7. **异常与替代**：超期/不可退品类/风控频繁退货 → 建议换新/补发/部分退款/优惠券补偿。

---

## 2. 规则相关（rules）

### 2.1 退换货政策（id: `rules.return_policy`）

**输出要点**  
- 列出：无理由天数 `{no_reason_days}`、质量问题天数 `{quality_days}`、完好标准、不可退类目、运费承担、退款时效 `{refund_sla_days}`、条款链接 `{policy_link}`。  
- 为保证可追溯，回复中应包含“条款链接或版本编号”。

**结构化字段（供 Agent 拼装）**  
```json
{
  "no_reason_days": "${vars.no_reason_days}",
  "quality_days": "${vars.quality_days}",
  "refund_sla_days": "${vars.refund_sla_days}",
  "policy_link": "${vars.policy_link}"
}
```

---

### 2.2 物流时效（id: `rules.shipping_sla`）

**输出要点**  
- 仓内处理：`{warehouse_process_hours}` 小时出库（高峰期顺延）。  
- 区域派送（按站点配置区间值）：同城、省内、跨省、偏远。最终以承运商轨迹为准。

**结构化字段**  
```json
{
  "warehouse_process_hours": "${vars.warehouse_process_hours}",
  "city_days_min": "${vars.city_days_min}",
  "city_days_max": "${vars.city_days_max}",
  "province_days_min": "${vars.province_days_min}",
  "province_days_max": "${vars.province_days_max}",
  "cross_days_min": "${vars.cross_days_min}",
  "cross_days_max": "${vars.cross_days_max}",
  "remote_days_min": "${vars.remote_days_min}",
  "remote_days_max": "${vars.remote_days_max}"
}
```

---

### 2.3 支付方式（id: `rules.payment_methods`）

**输出要点**  
- 支持的渠道：银行卡（Visa/Master/银联）、第三方钱包（支付宝/微信/PayPal/Apple Pay 等，按站点差异化展示）、分期（部分银行）。  
- 常见失败原因：额度不足、风控拒绝、网络异常、3D 验证失败。  
- 退款路径与时效：原路退回，`{refund_sla_days}` 个工作日内到账（钱包渠道通常更快）。

---

## 3. 售后相关（aftersales）

### 3.1 投诉处理（id: `aftersales.complaint`）

**分级与 SLA（示例）**  
- 严重：涉及安全/财产/隐私 → 4 小时响应，24 小时内结论或阶段性结果。  
- 一般：服务体验/承诺不符 → 24 小时响应，3 个工作日内处理。

**流程步骤**  
1. 收集：订单号、时间、诉求、证据（截图/录音/快递凭证）。  
2. 立案：`Ticket.create(severity, summary, attachments)` → `ticket_id`。  
3. 调查：调取订单/物流/仓内记录/通话与聊天历史。  
4. 结果：道歉/解释/补发/退款/补偿券/流程优化与培训。  
5. 升级：用户不满意可申请管理层复核；保留书面结论。  
6. 关闭：用户确认或 SLA 内未反馈自动关闭（允许在一定时间内重开）。

---

### 3.2 发票申请（id: `aftersales.invoice`）

**规则与步骤**  
1. 资格：支持开具电子发票（默认）/纸质发票（如政策支持）；申请窗口 `{invoice_apply_days}` 天内。  
2. 信息：抬头（个人/公司）、税号、邮箱、（公司抬头需）地址/电话/开户行及账号。  
3. 执行：`Invoice.request(order_id, type, title, tax_id, email)` → `invoice_id`。  
4. 时效：审核通过后 `{invoice_issue_days}` 个工作日内开具并发送至邮箱；纸票说明邮寄时效与运费规则。  
5. 异常：信息不全/资质不符 → 补正通知；超期不予受理（如有特批渠道需说明）。

---

### 3.3 缺货处理（id: `aftersales.oos_handling`）

**场景**  
- 下单后仓内缺货或系统超卖。

**策略**  
1. 向用户提供三选一：  
   - 等待补货（预计 `{restock_days}` 天，可分批发）。  
   - 立即取消并全额退款。  
   - 替代方案：同价/更高价替换（差额由商家承担或补偿券）。  
2. 执行：`Inventory.promise_or_cancel(order_id, option)`；同步触发退款/补差逻辑。  
3. 告知：明确时效、补偿规则、承诺编号（便于追溯）。

---

## 附：统一的错误处理与兜底
- **工具超时/失败**：优先返回已知信息 + 明确说明“正在刷新/已提交工单”，并提供查询入口（ticket/RMA）。  
- **权限拒绝**：提供账号验证/OTP 流程，拒绝跨账号查询。  
- **多轮澄清**：缺少关键字段（如 `order_id`、新地址要素）时，按优先级逐项追问。

