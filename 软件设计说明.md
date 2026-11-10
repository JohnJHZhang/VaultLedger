# VaultLedger · 加密个人记账（macOS）

本地优先的 macOS 记账客户端。原生 SwiftUI 构建，内置 SQLite 数据库，
所有业务数据以 **AES-256-GCM** 加密后落盘，密码经 **PBKDF2-HMAC-SHA512（210,000 次迭代）** 派生密钥。

作者：©️JohnJHZhang ｜ 版本：1.0.0

---

## 一、安装与运行

### 方式 A：DMG 安装包（推荐）

```
发布包/VaultLedger-1.0.0.dmg      ← 4.1 MB，双击打开
```

1. 双击 `VaultLedger-1.0.0.dmg` 挂载
2. 把左侧 **VaultLedger.app** 拖到右侧 **Applications** 文件夹
3. 从「应用程序」或启动台启动

安装盘已配置自定义背景、图标位置与卷图标（见 `预览图/00-DMG安装界面.png`）。

### 方式 B：直接运行 .app

```bash
open build/VaultLedger.app
# 或
open 发布包/VaultLedger.app
```

### 首次启动

进入「创建新账户」：

- **账户名称**：用于区分不同账本（同名不允许）
- **密码**：至少 6 位，用于派生该账户专属的 AES-256 密钥
- 可勾选「载入示例数据」快速体验（约 70 笔流水 + 预算 + 债务）

### 关于首次打开的安全提示

应用为 **ad-hoc 签名**（未使用付费 Apple 开发者证书公证）。若系统提示
「无法验证开发者」或「已损坏」：

```bash
# 方式一：解除隔离属性
xattr -dr com.apple.quarantine /Applications/VaultLedger.app

# 方式二：系统设置 → 隐私与安全性 → 仍要打开
```

> 这是 macOS 对未公证应用的标准限制，不影响功能与加密强度。

### 校验安装包完整性

```bash
cd 发布包 && shasum -a 256 -c SHA256SUMS.txt
```


---

## 二、功能地图

| 模块 | 说明 |
| --- | --- |
| **概览** | 本月收入/支出/结余、净资产、近 12 月收支趋势、支出结构环形图、最近流水、预算执行、债务概览 |
| **记一笔** | 收入/支出切换、15 个支出分类 + 9 个收入分类、5 种支付账户、金额快捷加算、日期与备注 |
| **收支流水** | 按月翻页、全部/收入/支出筛选、关键字搜索（分类/备注/金额/账户）、按日分组、双击编辑、右键删除 |
| **报表** | KPI 条、近 6/12 月收支对比、支出与收入双环形图、分类明细排行、消费洞察（最大单笔 / 超预算项） |
| **预算与提醒** | 总预算 + 分类预算、自定义预警阈值（50%–100%）、执行环、日均可用额度、提醒记录 |
| **债务与还款** | 待偿还 / 待收回双向台账、房贷车贷信用卡等类型、年利率、到期日、逐期还款记录、进度条 |
| **五险一金** | 8 城基数区间、养老/医疗/失业/工伤/生育/公积金明细、个人与单位双向对比、月度个税与税后到手、企业总成本 |
| **数据导出** | 导出 .xlsx（多工作表）或 .csv，可选时间范围与包含的工作表 |
| **安全中心** | 加密状态、密钥指纹、修改密码（全库重加密）、锁定、清空数据、删除账户 |

侧边栏左下角固定显示 **©️JohnJHZhang** 与 **版本 1.0.0**。

---

## 三、加密设计

```
密码 ──PBKDF2-HMAC-SHA512(210,000, 16B 随机盐)──▶ 256-bit 密钥（仅内存）
                                                      │
流水/预算/债务 ──JSON 序列化──▶ AES-256-GCM 加密 ──▶ 密文 BLOB ──▶ SQLite
```

- **字段级整包加密**：一条记录的完整 JSON 作为一个明文整体加密，
  随机 96-bit nonce，落库只有密文 BLOB。数据库被直接拷贝无法读出任何内容。
- **口令不落盘**：磁盘上只保存随机盐与一段「校验块」（固定明文的密文），
  用于验证密码是否正确，不泄露任何口令信息。
- **账户隔离**：每个账户独立盐值与密钥，同机多账户互不可解密。
- **完整性校验**：GCM 认证标签确保密文未被篡改，改动即解密失败。
- **密钥轮换**：修改密码时重新派生密钥，对全部记录逐条重新加密后写回。

已验证：`strings vault.db` 中无法检索到任何中文备注、分类名或 JSON 字段名。

---

## 四、数据位置

| 内容 | 路径 |
| --- | --- |
| 数据库（密文） | `~/Library/Application Support/VaultLedger/vault.db` |
| 账户索引 | `~/Library/Application Support/VaultLedger/accounts.json` |
| 导出文件 | `~/Library/Application Support/VaultLedger/Exports/` |

> 忘记密码无法找回 —— 这是加密的代价。请务必记住密码，并定期导出 Excel 备份。

---

## 五、从源码构建

```bash
./build.sh
```

一键完成全部步骤：

1. 用 CLT SDK 编译 Swift 源码（`-O -whole-module-optimization`）
2. 写入 `Info.plist`（版本号、作者、图标、分类）
3. 拷贝 `AppIcon.icns`
4. Ad-hoc 签名并校验
5. 生成 DMG 背景图（`@1x` / `@2x`）
6. 用 dmgbuild 打包 `.dmg`（背景、图标位置、卷图标、Applications 链接）
7. 校验镜像校验和
8. 整理 `发布包/` 并生成 SHA256

**产物**

| 路径 | 说明 |
| --- | --- |
| `build/VaultLedger.app` | 应用本体 |
| `build/VaultLedger-1.0.0.dmg` | 安装包 |
| `发布包/` | 对外分发的完整交付目录 |

**依赖**（仅构建时需要，运行时不依赖）

```bash
pip3 install --user dmgbuild    # 会自动带上 ds_store、mac_alias
```

重新生成应用图标：

```bash
swiftc -sdk /Library/Developer/CommandLineTools/SDKs/MacOSX26.5.sdk -o build/icongen Tools/IconGen.swift
./build/icongen Resources/VaultLedger.iconset
iconutil -c icns Resources/VaultLedger.iconset -o Resources/AppIcon.icns
```

> 为什么固定 `MacOSX26.5.sdk`：本机 Xcode 27 SDK 的 `swift-plugin-server`
> 在命令行编译时无法启动，会导致 `@State` 等 SwiftUI 宏报错；
> 换用 CommandLineTools 的 26.5 SDK 即可绕过。


---

## 六、源码结构

```
Sources/
  VaultLedgerApp.swift   程序入口、窗口配置、关于面板
  Theme.swift            配色、字体、卡片/按钮/分段控件、Logo
  VaultCrypto.swift      PBKDF2 派生 + AES-256-GCM 加解密 + 校验块
  VaultStore.swift       SQLite 封装（只存密文）、路径管理
  Models.swift           流水/预算/债务/设置/告警模型与聚合
  AppStore.swift         账户认证、加密读写、预算评估与推送、统计
  Charts.swift           趋势柱状图、环形图、迷你折线、预算环
  AuthView.swift         登录 / 注册
  ShellView.swift        侧边栏、顶栏、消息中心、横幅
  DashboardView.swift    概览
  EntryView.swift        记一笔 / 编辑
  LedgerView.swift       收支流水
  ReportsView.swift      报表
  BudgetView.swift       预算与提醒
  DebtView.swift         债务与还款
  InsuranceView.swift    五险一金与个税
  ExportView.swift       导出界面
  XLSXWriter.swift       零依赖 xlsx 生成（ZIP + SpreadsheetML）
  SecurityView.swift     安全中心
Tools/
  IconGen.swift          应用图标渲染
  DMGBackground.swift    DMG 安装盘背景图渲染
  build_dmg.py           早期自研打包脚本（保留参考）
  dmg_settings.py        dmgbuild 布局配置（窗口/图标/背景）
  dmg_preview.py         DMG 安装界面效果图合成
  Snapshot.swift         离线 UI 快照（自动化校验用）
  SelfTest.swift         加密与计算单元自检（20 项）
  E2ETest.swift          全流程验证（30 项）
```

发布包/                    对外分发目录
  VaultLedger-1.0.0.dmg    分发用安装包
  VaultLedger.app          免安装副本
  DMG安装界面预览.png      安装盘效果图
  SHA256SUMS.txt           校验和

测试运行方式（隔离数据目录，不影响真实账本）：

```bash
VL_ROOT=/tmp/vl_test ./build/selftest
```


## 七、软件预览图
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


