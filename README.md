# VaultLedger · 加密个人记账（macOS）

本地优先的 macOS 记账客户端。原生 SwiftUI 构建，内置 SQLite 数据库，
所有业务数据以 **AES-256-GCM** 加密后落盘，密码经 **PBKDF2-HMAC-SHA512（210,000 次迭代）** 派生密钥。

作者：©️JohnJHZhang ｜ 版本：1.0.0

---

# 核心功能
概览：本月收支、结余、净资产、12 个月趋势、支出结构图、预算与债务一览
记一笔：收支分类（15 支出 + 9 收入）、5 种支付账户、金额快捷加算
收支流水：按月翻页、筛选、搜索、按日分组、双击编辑
报表：收支对比、双环形图、分类排行、消费洞察
预算与提醒：总预算/分类预算、自定义预警阈值、日均可用额度
债务与还款：待还/待收双向台账、利率与到期日、逐期还款记录
五险一金：8 城基数、五险一金明细、个税测算、税后到手与企业成本
数据导出：一键导出 Excel（.xlsx）或 CSV
安全中心：修改密码（全库重加密）、锁定、清空与删除账户


# 安全设计
密码经 PBKDF2-HMAC-SHA512（21 万次迭代） 派生 256 位密钥，仅存内存
每条记录整体加密，库文件被拷贝也无法读出内容；口令不落盘
多账户独立密钥、相互隔离；GCM 认证标签防篡改


# 数据位置
数据库：~/Library/Application Support/VaultLedger/vault.db（密文）
导出文件：.../Exports/


# 安装方式
双击 DMG 安装包，将 App 拖入 Applications 即可；首次启动创建账户（密码 ≥ 6 位）
ad-hoc 签名，若系统提示「无法验证开发者」，运行 xattr -dr com.apple.quarantine /Applications/VaultLedger.app 解除隔离

---

# 软件预览图
<img width="640" height="420" alt="00-DMG安装界面" src="https://github.com/user-attachments/assets/010b83a2-66be-44bc-ae49-733690ebe93e" />
<img width="1240" height="800" alt="01-登录" src="https://github.com/user-attachments/assets/d0f0e986-705d-485d-bcf0-4b96aadba14d" />
<img width="1240" height="800" alt="02-概览" src="https://github.com/user-attachments/assets/99ecfc38-4cc9-4195-a79c-e0830848246b" />
<img width="1240" height="800" alt="03-记一笔" src="https://github.com/user-attachments/assets/8302ead8-3419-4247-bbd2-7474c819ca53" />
<img width="1240" height="800" alt="04-收支流水" src="https://github.com/user-attachments/assets/30944030-45f0-4af9-b1be-a949c54592fb" />
<img width="1240" height="800" alt="05-报表" src="https://github.com/user-attachments/assets/cf473b3c-5252-408d-8543-667442e4754e" />
<img width="1240" height="800" alt="06-预算与提醒" src="https://github.com/user-attachments/assets/8829640b-3d51-42fe-ab47-eeb0ace4c2a4" />
<img width="1240" height="800" alt="07-债务与还款" src="https://github.com/user-attachments/assets/cd7eb643-7feb-46de-a840-90c4b3e3031b" />
<img width="1240" height="800" alt="08-五险一金" src="https://github.com/user-attachments/assets/242faa79-2035-4e15-88a4-238b3edcec54" />
<img width="1240" height="800" alt="09-数据导出" src="https://github.com/user-attachments/assets/9ee16118-6e87-41a2-a1c7-ad815ebe0ae0" />
<img width="1240" height="800" alt="10-安全中心" src="https://github.com/user-attachments/assets/743fdb33-f729-4f04-85bf-cbe72796dfb5" />

---

