#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ledger+ · 记一记  (单文件版)
macOS 记账客户端 · 多用户 / iCloud 同步 / 月度 PDF / 菜单栏常驻
图标 SVG 内嵌，首次运行自动生成 .png 和 .icns

Copyright (c) 2026 JohnJHZhang · johnjhzhang@outlook.com
"""
import sys
import os
import json
import sqlite3
import uuid
import subprocess
import shutil
import re
from datetime import datetime, date
from pathlib import Path
from string import Template

from PySide6.QtCore import (Qt, QSize, QRect, QPoint, QDate, QLocale, QTimer,
                            QByteArray)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import (QFont, QColor, QPainter, QPen, QBrush, QIcon, QPixmap,
                           QImage, QAction)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton, QLineEdit,
    QComboBox, QStackedWidget, QVBoxLayout, QHBoxLayout, QLayout, QScrollArea,
    QDateEdit, QMessageBox, QFileDialog, QSizePolicy, QProgressBar, QDialog,
    QDialogButtonBox, QSystemTrayIcon, QMenu, QListWidget, QListWidgetItem,
    QAbstractItemView, QInputDialog)

# ─────────────────────────────────────────────────────────
# 内嵌 SVG 图标
# ─────────────────────────────────────────────────────────
SVG_DATA = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0a84ff"/><stop offset="100%" stop-color="#64d2ff"/>
  </linearGradient></defs>
  <rect x="0" y="0" width="512" height="512" rx="112" fill="url(#g)"/>
  <text x="256" y="322" font-family="Menlo,monospace" font-size="220"
        font-weight="800" fill="#ffffff" text-anchor="middle">L+</text>
</svg>"""


def _ensure_icons():
    """首次运行时从内嵌 SVG 自动生成 .png / .icns"""
    icons_dir = Path(__file__).parent / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)
    png_path = icons_dir / "icon.png"
    icns_path = icons_dir / "icon.icns"
    if png_path.exists() and icns_path.exists():
        return
    try:
        renderer = QSvgRenderer(QByteArray(SVG_DATA))
        # 主 PNG
        img = QImage(512, 512, QImage.Format_ARGB32)
        img.fill(0)
        p = QPainter(img)
        renderer.render(p)
        p.end()
        img.save(str(png_path), "PNG")
        # iconset
        iconset = icons_dir / "icon.iconset"
        if iconset.exists():
            shutil.rmtree(iconset, ignore_errors=True)
        iconset.mkdir(parents=True, exist_ok=True)
        specs = [(16, "16x16"), (32, "16x16@2x"), (32, "32x32"), (64, "32x32@2x"),
                 (128, "128x128"), (256, "128x128@2x"), (256, "256x256"),
                 (512, "256x256@2x"), (512, "512x512"), (1024, "512x512@2x")]
        for size, name in specs:
            im = QImage(size, size, QImage.Format_ARGB32)
            im.fill(0)
            pp = QPainter(im)
            renderer.render(pp)
            pp.end()
            im.save(str(iconset / f"icon_{name}.png"), "PNG")
        try:
            subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(icns_path)],
                           check=True, capture_output=True)
        except Exception:
            pass
        shutil.rmtree(iconset, ignore_errors=True)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────
# 常量
# ─────────────────────────────────────────────────────────
APP_NAME = "Ledger+"
APP_EN = "Ledger+"
APP_VERSION = "1.0.0"
AUTHOR = "JohnJHZhang"
EMAIL = "johnjhzhang@outlook.com"
COPYRIGHT = f"© 2026 {AUTHOR}"

LOCAL_DIR = Path.home() / "Library" / "Application Support" / "LedgerPlus"
ICLOUD_DIR = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "LedgerPlus"

LOCAL_DIR.mkdir(parents=True, exist_ok=True)
ICLOUD_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = LOCAL_DIR / "config.json"
USERS_FILE = LOCAL_DIR / "users.json"
USERS_DIR = LOCAL_DIR / "users"
ICLOUD_USERS_DIR = ICLOUD_DIR / "users"
USERS_DIR.mkdir(exist_ok=True)
ICLOUD_USERS_DIR.mkdir(exist_ok=True)

EXPENSE_CATS = ["food", "transport", "shopping", "entertainment",
                "housing", "medical", "study", "other"]
INCOME_CATS = ["salary", "bonus", "investment", "parttime", "otherincome"]
CAT_COLORS = {
    "food": "#ff6b6b", "transport": "#4d96ff", "shopping": "#ff9f43",
    "entertainment": "#a55eea", "housing": "#20c997", "medical": "#ff6b81",
    "study": "#00a8cc", "other": "#8d99ae",
    "salary": "#34c759", "bonus": "#0a84ff", "investment": "#30d158",
    "parttime": "#64d2ff", "otherincome": "#8e8e93",
}

# ─────────────────────────────────────────────────────────
# 多语言
# ─────────────────────────────────────────────────────────
L = {
"zh_CN": {
 "brand.name":"记一记","brand.sub":"本地优先 · 预算贴心提醒",
 "nav.overview":"概览","nav.add":"记一笔","nav.list":"流水","nav.stats":"报表","nav.settings":"设置",
 "top.lang":"语言","top.light":"浅色","top.dark":"深色",
 "ov.title":"概览","ov.income":"本月收入","ov.expense":"本月支出","ov.balance":"本月结余",
 "ov.budget":"本月预算","ov.budget_none":"在「设置」中设置分类预算后实时监控。",
 "ov.budget_over":"已超出预算 {v}，注意控制！","ov.budget_left":"剩余额度 {v}，继续保持。",
 "ov.trend":"近 6 个月趋势","ov.recent":"最近记录","ov.view_all":"全部 ›","ov.empty":"还没有记录。",
 "add.title":"记一笔","add.subtitle":"把每一笔花销或收入记下来",
 "add.expense":"支出","add.income":"收入","add.amount":"金额","add.category":"分类",
 "add.date":"日期","add.note":"备注","add.note_ph":"写了什么 / 花在哪（可选）","add.save":"保存记录",
 "add.updated":"记录已更新","add.saved_expense":"已记录一笔支出","add.saved_income":"已记录一笔收入",
 "add.invalid":"请输入有效金额",
 "list.title":"流水","list.income":"收入","list.expense":"支出","list.balance":"结余","list.empty":"本月还没有记录",
 "stats.title":"报表","stats.subtitle":"收支结构与趋势分析","stats.trend":"近 6 个月收支",
 "stats.composition":"本月支出构成","stats.ranking":"分类排行","stats.empty":"本月暂无支出",
 "set.title":"设置","set.subtitle":"预算、推送、数据与外观",
 "set.budget":"月度预算","set.budget_clear":"全部清零","set.budget_cleared":"预算已清零",
 "set.budget_updated":"{c} 预算已更新","set.push":"预算超支推送","set.push_enable":"开启通知",
 "set.push_test":"发送测试通知","set.push_threshold":"预警阈值",
 "set.push_desc":"支出达到阈值时推送「预警」，达 100% 时推送「超支」。每分类每月各一次。",
 "set.push_log":"通知记录","set.push_clear":"清空","set.push_log_empty":"暂无通知记录。",
 "set.appearance":"外观","set.dark":"深色模式",
 "set.data":"数据","set.export":"导出 JSON","set.import":"导入 JSON",
 "set.save_folder":"选择保存文件夹","set.clear":"清空数据",
 "set.exported":"已导出 JSON","set.imported":"导入成功","set.import_failed":"导入失败：{e}",
 "set.cleared":"已清空数据","set.confirm_clear":"确定清空所有记录、预算与设置？不可恢复。",
 "set.folder_changed":"保存文件夹已切换","set.db_info":"本地数据库：{path}","set.sysinfo":"系统信息",
 "set.version":"版本","set.notify":"系统通知","set.notify_on":"已开启 ✓","set.notify_off":"未开启",
 "set.cloud":"iCloud 同步","set.cloud_desc":"数据库存储于 iCloud Drive，多设备自动同步。",
 "set.cloud_enable":"启用 iCloud","set.cloud_disable":"关闭 iCloud","set.user":"当前用户",
 "msg.deleted":"已删除","msg.confirm_delete":"删除这条记录？",
 "cat.food":"饮食","cat.transport":"交通","cat.shopping":"购物","cat.entertainment":"娱乐",
 "cat.housing":"居住","cat.medical":"医疗","cat.study":"学习","cat.other":"其他",
 "cat.salary":"工资","cat.bonus":"奖金","cat.investment":"理财","cat.parttime":"兼职","cat.otherincome":"其他收入",
 "push.warn_title":"🔔 {n} 预算接近上限","push.warn_body":"已支出 {s} / 预算 {b}，已达 {p}%",
 "push.over_title":"⚠️ {n} 预算已超支","push.over_body":"已支出 {s} / 预算 {b}，超出 {o}（{p}%）",
 "push.test_title":"测试通知 🔔","push.test_body":"这是一条来自「记一记」的测试通知。",
 "chart.income":"收入","chart.expense":"支出","misc.total":"总预算","cat.total":"总计",
 "login.title":"选择用户","login.new":"新建用户","login.delete":"删除","login.name":"用户名",
 "login.hint":"输入用户名称","login.cloud":"iCloud 同步","login.cloud_on":"已启用","login.cloud_off":"未启用",
 "login.switch":"切换用户","login.deleted":"已删除用户 {n}","login.switched":"已切换至 {n}",
 "menu.quick":"快捷记账","menu.pdf":"生成月度 PDF","menu.show":"显示窗口","menu.hide":"隐藏",
 "menu.quit":"退出","menu.quick_title":"快捷记账",
 "pdf.title":"月度账单","pdf.month":"月份","pdf.total_income":"总收入","pdf.total_expense":"总支出",
 "pdf.balance":"结余","pdf.category":"分类","pdf.amount":"金额","pdf.ratio":"占比",
 "pdf.trend":"收支趋势","pdf.detail":"交易明细","pdf.generated":"PDF 已生成: {p}",
},
"zh_TW": {
 "brand.name":"記一記","brand.sub":"本機優先 · 預算貼心提醒",
 "nav.overview":"總覽","nav.add":"記一筆","nav.list":"流水","nav.stats":"報表","nav.settings":"設定",
 "top.lang":"語言","top.light":"淺色","top.dark":"深色",
 "ov.title":"總覽","ov.income":"本月收入","ov.expense":"本月支出","ov.balance":"本月結餘",
 "ov.budget":"本月預算","ov.budget_none":"在「設定」中設定分類預算後即時監控。",
 "ov.budget_over":"已超出預算 {v}，請注意！","ov.budget_left":"剩餘額度 {v}，繼續保持。",
 "ov.trend":"近 6 個月趨勢","ov.recent":"最近記錄","ov.view_all":"全部 ›","ov.empty":"還沒有記錄。",
 "add.title":"記一筆","add.subtitle":"把每一筆花費或收入記下來",
 "add.expense":"支出","add.income":"收入","add.amount":"金額","add.category":"分類",
 "add.date":"日期","add.note":"備註","add.note_ph":"寫了什麼 / 花在哪（選填）","add.save":"儲存記錄",
 "add.updated":"記錄已更新","add.saved_expense":"已記錄一筆支出","add.saved_income":"已記錄一筆收入",
 "add.invalid":"請輸入有效金額",
 "list.title":"流水","list.income":"收入","list.expense":"支出","list.balance":"結餘","list.empty":"本月還沒有記錄",
 "stats.title":"報表","stats.subtitle":"收支結構與趨勢分析","stats.trend":"近 6 個月收支",
 "stats.composition":"本月支出構成","stats.ranking":"分類排行","stats.empty":"本月暫無支出",
 "set.title":"設定","set.subtitle":"預算、推送、資料與外觀",
 "set.budget":"月度預算","set.budget_clear":"全部歸零","set.budget_cleared":"預算已歸零",
 "set.budget_updated":"{c} 預算已更新","set.push":"預算超支推送","set.push_enable":"開啟通知",
 "set.push_test":"傳送測試通知","set.push_threshold":"預警閾值",
 "set.push_desc":"支出達到閾值時推送「預警」，達 100% 時推送「超支」。每分類每月各一次。",
 "set.push_log":"通知記錄","set.push_clear":"清空","set.push_log_empty":"暫無通知記錄。",
 "set.appearance":"外觀","set.dark":"深色模式",
 "set.data":"資料","set.export":"匯出 JSON","set.import":"匯入 JSON",
 "set.save_folder":"選擇儲存資料夾","set.clear":"清空資料",
 "set.exported":"已匯出 JSON","set.imported":"匯入成功","set.import_failed":"匯入失敗：{e}",
 "set.cleared":"已清空資料","set.confirm_clear":"確定清空所有記錄、預算與設定？不可復原。",
 "set.folder_changed":"儲存資料夾已切換","set.db_info":"本機資料庫：{path}","set.sysinfo":"系統資訊",
 "set.version":"版本","set.notify":"系統通知","set.notify_on":"已開啟 ✓","set.notify_off":"未開啟",
 "set.cloud":"iCloud 同步","set.cloud_desc":"資料庫儲存於 iCloud Drive，多裝置自動同步。",
 "set.cloud_enable":"啟用 iCloud","set.cloud_disable":"關閉 iCloud","set.user":"目前使用者",
 "msg.deleted":"已刪除","msg.confirm_delete":"刪除這條記錄？",
 "cat.food":"飲食","cat.transport":"交通","cat.shopping":"購物","cat.entertainment":"娛樂",
 "cat.housing":"居住","cat.medical":"醫療","cat.study":"學習","cat.other":"其他",
 "cat.salary":"薪資","cat.bonus":"獎金","cat.investment":"理財","cat.parttime":"兼職","cat.otherincome":"其他收入",
 "push.warn_title":"🔔 {n} 預算接近上限","push.warn_body":"已支出 {s} / 預算 {b}，已達 {p}%",
 "push.over_title":"⚠️ {n} 預算已超支","push.over_body":"已支出 {s} / 預算 {b}，超出 {o}（{p}%）",
 "push.test_title":"測試通知 🔔","push.test_body":"這是一條來自「記一記」的測試通知。",
 "chart.income":"收入","chart.expense":"支出","misc.total":"總預算","cat.total":"總計",
 "login.title":"選擇使用者","login.new":"新建使用者","login.delete":"刪除","login.name":"使用者名稱",
 "login.hint":"輸入使用者名稱","login.cloud":"iCloud 同步","login.cloud_on":"已啟用","login.cloud_off":"未啟用",
 "login.switch":"切換使用者","login.deleted":"已刪除使用者 {n}","login.switched":"已切換至 {n}",
 "menu.quick":"快捷記帳","menu.pdf":"生成月度 PDF","menu.show":"顯示視窗","menu.hide":"隱藏",
 "menu.quit":"退出","menu.quick_title":"快捷記帳",
 "pdf.title":"月度賬單","pdf.month":"月份","pdf.total_income":"總收入","pdf.total_expense":"總支出",
 "pdf.balance":"結餘","pdf.category":"分類","pdf.amount":"金額","pdf.ratio":"佔比",
 "pdf.trend":"收支趨勢","pdf.detail":"交易明細","pdf.generated":"PDF 已生成: {p}",
},
"en": {
 "brand.name":"Ledger+","brand.sub":"Local-first · Smart budget alerts",
 "nav.overview":"Overview","nav.add":"Add","nav.list":"Records","nav.stats":"Reports","nav.settings":"Settings",
 "top.lang":"Language","top.light":"Light","top.dark":"Dark",
 "ov.title":"Overview","ov.income":"Income this month","ov.expense":"Expense this month","ov.balance":"Balance this month",
 "ov.budget":"Monthly budget","ov.budget_none":"Set category budgets in Settings.",
 "ov.budget_over":"Over budget by {v}.","ov.budget_left":"{v} left.",
 "ov.trend":"Last 6 months","ov.recent":"Recent records","ov.view_all":"View all ›","ov.empty":"No records yet.",
 "add.title":"Add record","add.subtitle":"Record every expense or income",
 "add.expense":"Expense","add.income":"Income","add.amount":"Amount","add.category":"Category",
 "add.date":"Date","add.note":"Note","add.note_ph":"What was it for (optional)","add.save":"Save",
 "add.updated":"Record updated","add.saved_expense":"Expense recorded","add.saved_income":"Income recorded",
 "add.invalid":"Please enter a valid amount",
 "list.title":"Records","list.income":"Income","list.expense":"Expense","list.balance":"Balance","list.empty":"No records this month",
 "stats.title":"Reports","stats.subtitle":"Structure and trends","stats.trend":"Income & expense, last 6 months",
 "stats.composition":"Expense composition","stats.ranking":"Category ranking","stats.empty":"No expense this month",
 "set.title":"Settings","set.subtitle":"Budget, alerts, data and appearance",
 "set.budget":"Monthly budget","set.budget_clear":"Clear all","set.budget_cleared":"Budgets cleared",
 "set.budget_updated":"{c} budget updated","set.push":"Budget alerts","set.push_enable":"Enable notifications",
 "set.push_test":"Send test","set.push_threshold":"Alert threshold",
 "set.push_desc":"Sends a warning at the threshold and an overspend alert at 100%. Once per category per month.",
 "set.push_log":"Notification log","set.push_clear":"Clear","set.push_log_empty":"No notifications yet.",
 "set.appearance":"Appearance","set.dark":"Dark mode",
 "set.data":"Data","set.export":"Export JSON","set.import":"Import JSON",
 "set.save_folder":"Choose save folder","set.clear":"Clear data",
 "set.exported":"JSON exported","set.imported":"Imported","set.import_failed":"Import failed: {e}",
 "set.cleared":"Data cleared","set.confirm_clear":"Clear all records, budgets and settings? This cannot be undone.",
 "set.folder_changed":"Save folder changed","set.db_info":"Local database: {path}","set.sysinfo":"System information",
 "set.version":"Version","set.notify":"Notifications","set.notify_on":"Enabled ✓","set.notify_off":"Disabled",
 "set.cloud":"iCloud Sync","set.cloud_desc":"Database stored in iCloud Drive for multi-device sync.",
 "set.cloud_enable":"Enable iCloud","set.cloud_disable":"Disable iCloud","set.user":"Current User",
 "msg.deleted":"Deleted","msg.confirm_delete":"Delete this record?",
 "cat.food":"Food","cat.transport":"Transport","cat.shopping":"Shopping","cat.entertainment":"Entertainment",
 "cat.housing":"Housing","cat.medical":"Medical","cat.study":"Study","cat.other":"Other",
 "cat.salary":"Salary","cat.bonus":"Bonus","cat.investment":"Investment","cat.parttime":"Part-time","cat.otherincome":"Other income",
 "push.warn_title":"🔔 {n} budget near limit","push.warn_body":"Spent {s} of {b} ({p}%)",
 "push.over_title":"⚠️ {n} budget exceeded","push.over_body":"Spent {s} of {b}, over by {o} ({p}%)",
 "push.test_title":"Test notification 🔔","push.test_body":"This is a test alert from Ledger+.",
 "chart.income":"Income","chart.expense":"Expense","misc.total":"Total","cat.total":"Total",
 "login.title":"Select User","login.new":"New User","login.delete":"Delete","login.name":"User Name",
 "login.hint":"Enter user name","login.cloud":"iCloud Sync","login.cloud_on":"Enabled","login.cloud_off":"Disabled",
 "login.switch":"Switch User","login.deleted":"Deleted user {n}","login.switched":"Switched to {n}",
 "menu.quick":"Quick Add","menu.pdf":"Generate Monthly PDF","menu.show":"Show Window","menu.hide":"Hide",
 "menu.quit":"Quit","menu.quick_title":"Quick Add",
 "pdf.title":"Monthly Bill","pdf.month":"Month","pdf.total_income":"Total Income","pdf.total_expense":"Total Expense",
 "pdf.balance":"Balance","pdf.category":"Category","pdf.amount":"Amount","pdf.ratio":"Percentage",
 "pdf.trend":"Income & Expense Trend","pdf.detail":"Transactions","pdf.generated":"PDF generated: {p}",
},
"ja": {
 "brand.name":"記一記","brand.sub":"ローカル優先 · 予算アラート",
 "nav.overview":"概要","nav.add":"記録","nav.list":"履歴","nav.stats":"レポート","nav.settings":"設定",
 "top.lang":"言語","top.light":"ライト","top.dark":"ダーク",
 "ov.title":"概要","ov.income":"今月の収入","ov.expense":"今月の支出","ov.balance":"今月の残高",
 "ov.budget":"今月の予算","ov.budget_none":"設定でカテゴリ別予算を設定してください。",
 "ov.budget_over":"予算を {v} 超過しました。","ov.budget_left":"残り {v} です。",
 "ov.trend":"直近6か月","ov.recent":"最近の記録","ov.view_all":"すべて ›","ov.empty":"記録がありません。",
 "add.title":"記録する","add.subtitle":"支出や収入を記録します",
 "add.expense":"支出","add.income":"収入","add.amount":"金額","add.category":"カテゴリ",
 "add.date":"日付","add.note":"メモ","add.note_ph":"用途・内容（任意）","add.save":"保存",
 "add.updated":"更新しました","add.saved_expense":"支出を記録しました","add.saved_income":"収入を記録しました",
 "add.invalid":"有効な金額を入力してください",
 "list.title":"履歴","list.income":"収入","list.expense":"支出","list.balance":"残高","list.empty":"今月の記録はありません",
 "stats.title":"レポート","stats.subtitle":"収支の構成と推移","stats.trend":"直近6か月の収支",
 "stats.composition":"今月の支出構成","stats.ranking":"カテゴリ別ランキング","stats.empty":"今月の支出はありません",
 "set.title":"設定","set.subtitle":"予算・通知・データ・外観",
 "set.budget":"月予算","set.budget_clear":"全解除","set.budget_cleared":"予算を解除しました",
 "set.budget_updated":"{c} の予算を更新しました","set.push":"予算超過アラート","set.push_enable":"通知を有効化",
 "set.push_test":"テスト通知を送信","set.push_threshold":"警告しきい値",
 "set.push_desc":"しきい値で警告、100%で超過を通知。カテゴリごとに月1回。",
 "set.push_log":"通知履歴","set.push_clear":"消去","set.push_log_empty":"通知はまだありません。",
 "set.appearance":"外観","set.dark":"ダークモード",
 "set.data":"データ","set.export":"JSON を書き出す","set.import":"JSON を読み込む",
 "set.save_folder":"保存フォルダを選択","set.clear":"データを消去",
 "set.exported":"JSON を書き出しました","set.imported":"読み込み完了","set.import_failed":"読み込み失敗：{e}",
 "set.cleared":"データを消去しました","set.confirm_clear":"すべての記録・予算・設定を消去しますか？",
 "set.folder_changed":"保存フォルダを変更しました","set.db_info":"ローカルDB：{path}","set.sysinfo":"システム情報",
 "set.version":"バージョン","set.notify":"通知","set.notify_on":"有効 ✓","set.notify_off":"無効",
 "set.cloud":"iCloud 同期","set.cloud_desc":"DBはiCloud Driveに保存され、複数デバイスで同期されます。",
 "set.cloud_enable":"iCloudを有効化","set.cloud_disable":"iCloudを無効化","set.user":"現在のユーザー",
 "msg.deleted":"削除しました","msg.confirm_delete":"この記録を削除しますか？",
 "cat.food":"食費","cat.transport":"交通","cat.shopping":"買い物","cat.entertainment":"娯楽",
 "cat.housing":"住居","cat.medical":"医療","cat.study":"学習","cat.other":"その他",
 "cat.salary":"給与","cat.bonus":"賞与","cat.investment":"投資","cat.parttime":"副業","cat.otherincome":"その他収入",
 "push.warn_title":"🔔 {n} が予算上限に接近","push.warn_body":"支出 {s} / 予算 {b}（{p}%）",
 "push.over_title":"⚠️ {n} が予算超過","push.over_body":"支出 {s} / 予算 {b}、{o} 超過（{p}%）",
 "push.test_title":"テスト通知 🔔","push.test_body":"記一記からのテスト通知です。",
 "chart.income":"収入","chart.expense":"支出","misc.total":"総予算","cat.total":"合計",
 "login.title":"ユーザー選択","login.new":"新規ユーザー","login.delete":"削除","login.name":"ユーザー名",
 "login.hint":"ユーザー名を入力","login.cloud":"iCloud 同期","login.cloud_on":"有効","login.cloud_off":"無効",
 "login.switch":"ユーザー切替","login.deleted":"ユーザー {n} を削除しました","login.switched":"{n} に切り替えました",
 "menu.quick":"クイック記録","menu.pdf":"月次PDF生成","menu.show":"ウィンドウ表示","menu.hide":"隠す",
 "menu.quit":"終了","menu.quick_title":"クイック記録",
 "pdf.title":"月次レポート","pdf.month":"月","pdf.total_income":"総収入","pdf.total_expense":"総支出",
 "pdf.balance":"残高","pdf.category":"カテゴリ","pdf.amount":"金額","pdf.ratio":"割合",
 "pdf.trend":"収支トレンド","pdf.detail":"取引明細","pdf.generated":"PDF生成完了: {p}",
},
"ko": {
 "brand.name":"기일기","brand.sub":"로컬 우선 · 예산 알림",
 "nav.overview":"개요","nav.add":"기록","nav.list":"내역","nav.stats":"리포트","nav.settings":"설정",
 "top.lang":"언어","top.light":"라이트","top.dark":"다크",
 "ov.title":"개요","ov.income":"이번 달 수입","ov.expense":"이번 달 지출","ov.balance":"이번 달 잔액",
 "ov.budget":"이번 달 예산","ov.budget_none":"설정에서 카테고리별 예산을 설정하세요.",
 "ov.budget_over":"예산을 {v} 초과했습니다.","ov.budget_left":"{v} 남았습니다.",
 "ov.trend":"최근 6개월","ov.recent":"최근 기록","ov.view_all":"전체 ›","ov.empty":"기록이 없습니다.",
 "add.title":"기록하기","add.subtitle":"지출과 수입을 기록하세요",
 "add.expense":"지출","add.income":"수입","add.amount":"금액","add.category":"카테고리",
 "add.date":"날짜","add.note":"메모","add.note_ph":"무엇에 사용했나요 (선택)","add.save":"저장",
 "add.updated":"기록이 수정되었습니다","add.saved_expense":"지출을 기록했습니다","add.saved_income":"수입을 기록했습니다",
 "add.invalid":"올바른 금액을 입력하세요",
 "list.title":"내역","list.income":"수입","list.expense":"지출","list.balance":"잔액","list.empty":"이번 달 기록이 없습니다",
 "stats.title":"리포트","stats.subtitle":"수지 구조와 추이","stats.trend":"최근 6개월 수지",
 "stats.composition":"이번 달 지출 구성","stats.ranking":"카테고리 순위","stats.empty":"이번 달 지출이 없습니다",
 "set.title":"설정","set.subtitle":"예산 · 알림 · 데이터 · 테마",
 "set.budget":"월 예산","set.budget_clear":"모두 초기화","set.budget_cleared":"예산을 초기화했습니다",
 "set.budget_updated":"{c} 예산이 수정되었습니다","set.push":"예산 초과 알림","set.push_enable":"알림 켜기",
 "set.push_test":"테스트 알림 보내기","set.push_threshold":"경고 임계값",
 "set.push_desc":"임계값 도달 시 경고, 100%면 초과 알림. 카테고리별 월 1회.",
 "set.push_log":"알림 기록","set.push_clear":"비우기","set.push_log_empty":"알림 기록이 없습니다.",
 "set.appearance":"테마","set.dark":"다크 모드",
 "set.data":"데이터","set.export":"JSON 내보내기","set.import":"JSON 가져오기",
 "set.save_folder":"저장 폴더 선택","set.clear":"데이터 비우기",
 "set.exported":"JSON을 내보냈습니다","set.imported":"가져왔습니다","set.import_failed":"가져오기 실패: {e}",
 "set.cleared":"데이터를 비웠습니다","set.confirm_clear":"모든 기록·예산·설정을 비우시겠습니까?",
 "set.folder_changed":"저장 폴더를 변경했습니다","set.db_info":"로컬 DB: {path}","set.sysinfo":"시스템 정보",
 "set.version":"버전","set.notify":"알림","set.notify_on":"켜짐 ✓","set.notify_off":"꺼짐",
 "set.cloud":"iCloud 동기화","set.cloud_desc":"데이터베이스가 iCloud Drive에 저장되어 동기화됩니다.",
 "set.cloud_enable":"iCloud 사용","set.cloud_disable":"iCloud 끄기","set.user":"현재 사용자",
 "msg.deleted":"삭제되었습니다","msg.confirm_delete":"이 기록을 삭제할까요?",
 "cat.food":"식비","cat.transport":"교통","cat.shopping":"쇼핑","cat.entertainment":"여가",
 "cat.housing":"주거","cat.medical":"의료","cat.study":"학습","cat.other":"기타",
 "cat.salary":"급여","cat.bonus":"상여","cat.investment":"투자","cat.parttime":"부업","cat.otherincome":"기타 수입",
 "push.warn_title":"🔔 {n} 예산 한도 근접","push.warn_body":"지출 {s} / 예산 {b} ({p}%)",
 "push.over_title":"⚠️ {n} 예산 초과","push.over_body":"지출 {s} / 예산 {b}, {o} 초과 ({p}%)",
 "push.test_title":"테스트 알림 🔔","push.test_body":"기일기에서 보내는 테스트 알림입니다.",
 "chart.income":"수입","chart.expense":"지출","misc.total":"총예산","cat.total":"합계",
 "login.title":"사용자 선택","login.new":"새 사용자","login.delete":"삭제","login.name":"사용자 이름",
 "login.hint":"사용자 이름 입력","login.cloud":"iCloud 동기화","login.cloud_on":"사용 중","login.cloud_off":"사용 안 함",
 "login.switch":"사용자 전환","login.deleted":"사용자 {n} 삭제됨","login.switched":"{n}(으)로 전환됨",
 "menu.quick":"빠른 기록","menu.pdf":"월간 PDF 생성","menu.show":"창 표시","menu.hide":"숨기기",
 "menu.quit":"종료","menu.quick_title":"빠른 기록",
 "pdf.title":"월간 청구서","pdf.month":"월","pdf.total_income":"총 수입","pdf.total_expense":"총 지출",
 "pdf.balance":"잔액","pdf.category":"카테고리","pdf.amount":"금액","pdf.ratio":"비율",
 "pdf.trend":"수지 추이","pdf.detail":"거래 내역","pdf.generated":"PDF 생성 완료: {p}",
},
}

LANGS = [("zh_CN", "简体中文"), ("zh_TW", "繁體中文"),
         ("en", "English"), ("ja", "日本語"), ("ko", "한국어")]
LOCALE_MAP = {
    "zh_CN": QLocale(QLocale.Chinese, QLocale.China),
    "zh_TW": QLocale(QLocale.Chinese, QLocale.Taiwan),
    "en":    QLocale(QLocale.English, QLocale.UnitedStates),
    "ja":    QLocale(QLocale.Japanese, QLocale.Japan),
    "ko":    QLocale(QLocale.Korean, QLocale.SouthKorea),
}


class I18n:
    lang = "zh_CN"

    @classmethod
    def set(cls, lang):
        cls.lang = lang if lang in L else "en"

    @classmethod
    def t(cls, key, **kw):
        s = L.get(cls.lang, L["en"]).get(key) or L["en"].get(key, key)
        return s.format(**kw) if kw else s

    @classmethod
    def locale(cls):
        return LOCALE_MAP.get(cls.lang, LOCALE_MAP["en"])


def tr(key, **kw):
    return I18n.t(key, **kw)


# ─────────────────────────────────────────────────────────
# 主题 & QSS
# ─────────────────────────────────────────────────────────
THEMES = {
    "light": dict(bg="#f2f2f7", bg2="#e9e9ef", surface="#ffffff", surface_alt="#f7f7fa",
                  ink="#1d1d1f", ink2="#6e6e73", line="#0000001a", line2="#00000033",
                  accent="#0a84ff", accent2="#64d2ff", green="#34c759", red="#ff3b30",
                  orange="#ff9500", nav_active="#e5f1ff"),
    "dark":  dict(bg="#000000", bg2="#0a0a0c", surface="#1c1c1e", surface_alt="#252529",
                  ink="#f5f5f7", ink2="#98989d", line="#ffffff1f", line2="#ffffff33",
                  accent="#0a84ff", accent2="#64d2ff", green="#30d158", red="#ff453a",
                  orange="#04abf9", nav_active="#1e3a5f"),
}
CUR_THEME = dict(THEMES["light"])


def tc(key):
    return CUR_THEME.get(key, "#000")


QSS = Template("""
* { font-family: "PingFang SC","SF Pro Text","Helvetica Neue",sans-serif; }
QWidget { color: $ink; font-size: 13px; }
QMainWindow, #root { background: $bg; }
#sidebar { background: $surface; border-right: 1px solid $line; }
#brandmark { border-radius: 12px; background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 $accent, stop:1 $accent2); color: #fff; font-weight: 800; }
.navBtn { text-align: left; padding: 10px 14px; border-radius: 10px; background: transparent; color: $ink2; font-size: 13px; font-weight: 600; }
.navBtn:hover { background: $bg2; color: $ink; }
.navBtn[active="true"] { background: $nav_active; color: $accent; }
#topbar { background: $surface; border-bottom: 1px solid $line; }
#pagetitle { font-size: 20px; font-weight: 800; }
[cls="card"] { background: $surface; border: 1px solid $line; border-radius: 16px; }
[cls="cardtitle"] { font-size: 14px; font-weight: 700; }
[cls="sub"] { color: $ink2; font-size: 12px; }
[cls="kpiLabel"] { color: $ink2; font-size: 12px; font-weight: 600; }
[cls="kpiVal"] { font-size: 24px; font-weight: 800; }
[cls="kpiValIncome"] { color: $green; font-size: 24px; font-weight: 800; }
[cls="kpiValExpense"] { color: $red; font-size: 24px; font-weight: 800; }
[cls="mono"] { font-family: "SF Mono","Menlo",monospace; }
QPushButton { border: 1px solid $line; border-radius: 10px; background: $surface; padding: 8px 14px; font-weight: 600; }
QPushButton:hover { border-color: $accent; }
QPushButton[cls="primary"] { background: $accent; border-color: $accent; color: #fff; padding: 11px 16px; font-size: 14px; }
QPushButton[cls="primary"]:hover { background: $accent2; border-color: $accent2; }
QPushButton[cls="ghost"] { background: $surface; color: $ink; }
QPushButton[cls="danger"] { color: $red; border-color: $line; }
QPushButton[cls="danger"]:hover { border-color: $red; }
QPushButton[cls="link"] { border: none; background: transparent; color: $accent; padding: 2px; }
QPushButton[cls="chip"] { border-radius: 14px; padding: 8px 14px; background: $surface; color: $ink2; }
QPushButton[cls="chip"][active="true"] { border-color: $accent; color: $accent; background: $nav_active; }
QPushButton[cls="seg"] { border: none; border-radius: 9px; padding: 9px; color: $ink2; background: transparent; }
QPushButton[cls="seg"][active="true"] { background: $surface; color: $ink; }
#segbg { background: $bg2; border-radius: 12px; }
QLineEdit, QComboBox, QDateEdit { border: 1px solid $line; border-radius: 10px; padding: 9px 12px; background: $surface_alt; color: $ink; min-height: 24px; }
QLineEdit:focus, QComboBox:focus, QDateEdit:focus { border-color: $accent; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView { background: $surface; border: 1px solid $line; selection-background-color: $nav_active; }
#amountEdit { font-size: 40px; font-weight: 800; border: none; background: transparent; padding: 6px; }
#amountCur { font-size: 24px; font-weight: 700; color: $ink2; }
QProgressBar { border: none; background: $bg2; border-radius: 5px; height: 10px; }
QProgressBar::chunk { background: $accent; border-radius: 5px; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: $line2; border-radius: 5px; min-height: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
#statusbar { background: $surface; border-top: 1px solid $line; }
[cls="status"], [cls="copyright"], [cls="version"] { color: $ink2; font-size: 11px; }
[cls="divider"] { background: $line; max-height: 1px; min-height: 1px; }
""")


def apply_theme(name):
    CUR_THEME.clear()
    CUR_THEME.update(THEMES[name])
    a = QApplication.instance()
    if a:
        a.setStyleSheet(QSS.substitute(CUR_THEME))


# ─────────────────────────────────────────────────────────
# 配置 / 用户 / iCloud
# ─────────────────────────────────────────────────────────
def load_config():
    try:
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text("utf-8"))
    except Exception:
        pass
    return {}


def save_config(cfg):
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), "utf-8")


def load_users():
    try:
        if USERS_FILE.exists():
            u = json.loads(USERS_FILE.read_text("utf-8"))
            if u:
                return u
    except Exception:
        pass
    return [{"id": "default", "name": "默认用户", "created": datetime.now().isoformat()}]


def save_users(users):
    USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2), "utf-8")


def user_db_path(uid, icloud=False):
    base = ICLOUD_USERS_DIR if icloud else USERS_DIR
    return base / f"{uid}.db"


def icloud_available():
    try:
        t = ICLOUD_DIR / ".icloud_test"
        t.write_text("ok")
        ok = t.exists()
        t.unlink(missing_ok=True)
        return ok
    except Exception:
        return False


# ─────────────────────────────────────────────────────────
# 数据库
# ─────────────────────────────────────────────────────────
class DB:
    def __init__(self, uid, icloud=False):
        self.uid = uid
        self.icloud = icloud
        self.path = user_db_path(uid, icloud)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        try:
            self.conn.execute("PRAGMA journal_mode=WAL" if icloud else "PRAGMA journal_mode=DELETE")
        except Exception:
            pass
        self._create()

    def _create(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS transactions(
          id TEXT PRIMARY KEY, type TEXT NOT NULL, amount REAL NOT NULL,
          category TEXT NOT NULL, note TEXT DEFAULT '', date TEXT NOT NULL,
          created_at TEXT, updated_at TEXT);
        CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(date);
        CREATE TABLE IF NOT EXISTS budgets(category TEXT PRIMARY KEY, amount REAL NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY AUTOINCREMENT,
          level TEXT, title TEXT, body TEXT, ts TEXT);
        CREATE TABLE IF NOT EXISTS push_log(month TEXT, name TEXT, level INTEGER, ts TEXT,
          PRIMARY KEY(month, name));
        """)
        self.conn.commit()

    def get(self, k, d=None):
        r = self.conn.execute("SELECT value FROM settings WHERE key=?", (k,)).fetchone()
        return r["value"] if r else d

    def put(self, k, v):
        self.conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (k, str(v)))
        self.conn.commit()

    def txs(self):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM transactions ORDER BY date DESC, created_at DESC")]

    def add_tx(self, t):
        self.conn.execute(
            "INSERT INTO transactions(id,type,amount,category,note,date,created_at,updated_at)"
            " VALUES(?,?,?,?,?,?,?,?)",
            (t["id"], t["type"], t["amount"], t["category"], t["note"],
             t["date"], t["created_at"], t["updated_at"]))
        self.conn.commit()

    def upd_tx(self, t):
        self.conn.execute(
            "UPDATE transactions SET type=?,amount=?,category=?,note=?,date=?,updated_at=?"
            " WHERE id=?",
            (t["type"], t["amount"], t["category"], t["note"],
             t["date"], t["updated_at"], t["id"]))
        self.conn.commit()

    def del_tx(self, tid):
        self.conn.execute("DELETE FROM transactions WHERE id=?", (tid,))
        self.conn.commit()

    def budgets(self):
        return {r["category"]: r["amount"] for r in self.conn.execute("SELECT * FROM budgets")}

    def set_budget(self, c, a):
        if a > 0:
            self.conn.execute("INSERT OR REPLACE INTO budgets(category,amount) VALUES(?,?)", (c, a))
        else:
            self.conn.execute("DELETE FROM budgets WHERE category=?", (c,))
        self.conn.commit()

    def clear_budgets(self):
        self.conn.execute("DELETE FROM budgets")
        self.conn.commit()

    def alerts(self, n=50):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (n,))]

    def add_alert(self, lv, ti, bo):
        self.conn.execute("INSERT INTO alerts(level,title,body,ts) VALUES(?,?,?,?)",
                          (lv, ti, bo, datetime.now().isoformat()))
        self.conn.commit()

    def clear_alerts(self):
        self.conn.execute("DELETE FROM alerts")
        self.conn.commit()

    def push_level(self, m, n):
        r = self.conn.execute(
            "SELECT level FROM push_log WHERE month=? AND name=?", (m, n)).fetchone()
        return r["level"] if r else 0

    def set_push_level(self, m, n, lv):
        self.conn.execute(
            "INSERT OR REPLACE INTO push_log(month,name,level,ts) VALUES(?,?,?,?)",
            (m, n, lv, datetime.now().isoformat()))
        self.conn.commit()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass


# ─────────────────────────────────────────────────────────
# macOS 系统通知
# ─────────────────────────────────────────────────────────
def notify(title, body):
    try:
        t = title.replace('"', '\\"')
        b = body.replace('"', '\\"')
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{b}" with title "{t}" sound name "Ping"'],
            check=False, capture_output=True)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────
# PDF 导出
# ─────────────────────────────────────────────────────────
try:
    from reportlab.pdfgen import canvas as _pcanvas
    from reportlab.lib.units import mm as _mm
    from reportlab.lib import colors as _colors
    from reportlab.pdfbase import pdfmetrics as _pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont as _TTFont
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont as _CIDFont
    PDF_OK = True
except ImportError:
    PDF_OK = False


def _cjk_font():
    for p in ["/Library/Fonts/Arial Unicode.ttf",
              "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
              "/System/Library/Fonts/PingFang.ttc",
              "/System/Library/Fonts/STHeiti Light.ttc"]:
        if os.path.exists(p):
            try:
                _pdfmetrics.registerFont(_TTFont("CJK", p))
                return "CJK"
            except Exception:
                continue
    try:
        _pdfmetrics.registerFont(_CIDFont("STSong-Light"))
        return "STSong-Light"
    except Exception:
        return "Helvetica"


class PDFExporter:
    def __init__(self, db, lang, month):
        self.db = db
        self.lang = lang
        self.month = month
        self.y, self.m = map(int, month.split("-"))

    def generate(self, path):
        if not PDF_OK:
            raise ImportError("需要 reportlab：pip install reportlab")
        font = _cjk_font()
        w, h, mg = 210 * _mm, 297 * _mm, 20 * _mm
        c = _pcanvas.Canvas(path, pagesize=(w, h))
        c.setFont(font, 20)
        c.drawString(mg, h - 35 * _mm, f"{tr('pdf.title')} · {self.month}")
        c.line(mg, h - 40 * _mm, w - mg, h - 40 * _mm)

        inc = exp = 0.0
        cats = {}
        rows = [t for t in self.db.txs() if t["date"][:7] == self.month]
        for t in rows:
            if t["type"] == "income":
                inc += t["amount"]
            else:
                exp += t["amount"]
                cats[t["category"]] = cats.get(t["category"], 0) + t["amount"]

        y = h - 52 * _mm
        c.setFont(font, 12)
        c.drawString(mg, y, f"{tr('pdf.total_income')}: ¥{inc:,.2f}")
        y -= 7 * _mm
        c.setFillColor(_colors.HexColor("#ff3b30"))
        c.drawString(mg, y, f"{tr('pdf.total_expense')}: ¥{exp:,.2f}")
        y -= 8 * _mm
        bal = inc - exp
        c.setFont(font, 14)
        c.setFillColor(_colors.HexColor("#34c759") if bal >= 0 else _colors.HexColor("#ff3b30"))
        c.drawString(mg, y, f"{tr('pdf.balance')}: ¥{bal:,.2f}")
        y -= 14 * _mm
        c.setFillColor(_colors.black)

        c.setFont(font, 13)
        c.drawString(mg, y, tr("pdf.category"))
        y -= 7 * _mm
        tot = sum(cats.values())
        for cat, amt in sorted(cats.items(), key=lambda x: -x[1]):
            pct = amt / tot * 100 if tot else 0
            c.setFont(font, 10)
            c.drawString(mg + 8 * _mm, y, f"{tr('cat.' + cat)}   ¥{amt:,.2f}   {pct:.1f}%")
            y -= 6 * _mm
            if y < 30 * _mm:
                c.showPage()
                c.setFont(font, 10)
                y = h - 20 * _mm
        y -= 8 * _mm

        c.setFont(font, 13)
        c.drawString(mg, y, tr("pdf.detail"))
        y -= 7 * _mm
        for t in rows[:50]:
            sign = "+" if t["type"] == "income" else "-"
            txt = f"{t['date']}  {tr('cat.' + t['category'])}  {t['note'] or ''}  {sign}¥{t['amount']:,.2f}"
            c.setFont(font, 8)
            c.drawString(mg + 8 * _mm, y, txt[:60])
            y -= 5 * _mm
            if y < 25 * _mm:
                c.showPage()
                c.setFont(font, 8)
                y = h - 20 * _mm
        c.save()
        return path


# ─────────────────────────────────────────────────────────
# 辅助函数
# ─────────────────────────────────────────────────────────
def money(v):
    v = float(v or 0)
    return ("-" if v < 0 else "") + f"¥{abs(v):,.2f}"


def today_str():
    return date.today().isoformat()


def current_month():
    return date.today().strftime("%Y-%m")


def months_back(n):
    t = date.today()
    y, m = t.year, t.month
    out = []
    for _ in range(n):
        out.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(out))


def make_label(text, cls=None, wrap=False, size=None, bold=False):
    lbl = QLabel(text)
    if cls:
        lbl.setProperty("cls", cls)
    if wrap:
        lbl.setWordWrap(True)
    if size or bold:
        f = lbl.font()
        if size:
            f.setPointSize(size)
        if bold:
            f.setBold(True)
        lbl.setFont(f)
    return lbl


def make_card():
    f = QFrame()
    f.setProperty("cls", "card")
    return f


def hline():
    f = QFrame()
    f.setProperty("cls", "divider")
    f.setFixedHeight(1)
    return f


# ─────────────────────────────────────────────────────────
# FlowLayout
# ─────────────────────────────────────────────────────────
class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=8):
        super().__init__(parent)
        self.setContentsMargins(margin, margin, margin, margin)
        self._sp = spacing
        self._items = []

    def addItem(self, it):
        self._items.append(it)

    def count(self):
        return len(self._items)

    def itemAt(self, i):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientations(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, w):
        return self._do(QRect(0, 0, w, 0), True)

    def setGeometry(self, r):
        super().setGeometry(r)
        self._do(r, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        s = QSize()
        for it in self._items:
            s = s.expandedTo(it.minimumSize())
        m = self.contentsMargins()
        return s + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _do(self, rect, test):
        m = self.contentsMargins()
        eff = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y, lh = eff.x(), eff.y(), 0
        for it in self._items:
            sz = it.sizeHint()
            if x + sz.width() > eff.right() and lh > 0:
                x = eff.x()
                y += lh + self._sp
                lh = 0
            if not test:
                it.setGeometry(QRect(QPoint(x, y), sz))
            x += sz.width() + self._sp
            lh = max(lh, sz.height())
        return y + lh - rect.y() + m.bottom()


# ─────────────────────────────────────────────────────────
# 图表
# ─────────────────────────────────────────────────────────
class BarChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = []
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_data(self, d):
        self.data = d
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
        L, R, T, B = 62, 16, 16, 32
        gw, gh = W - L - R, H - T - B
        if not self.data or gw <= 0 or gh <= 0:
            return
        mx = max([d["income"] for d in self.data] +
                 [d["expense"] for d in self.data] + [1])
        p.setPen(QPen(QColor(120, 120, 130, 40), 1))
        for i in range(4):
            yy = T + gh * i / 3
            p.drawLine(L, int(yy), W - R, int(yy))
        p.setPen(QPen(QColor(tc("ink2"))))
        f = QFont()
        f.setPointSize(9)
        p.setFont(f)
        for i in range(4):
            yy = T + gh * i / 3
            v = mx * (1 - i / 3)
            if v >= 10000:
                vs = f"¥{v/10000:.1f}w"
            elif v >= 1000:
                vs = f"¥{v/1000:.1f}k"
            else:
                vs = f"¥{int(v)}"
            p.drawText(0, int(yy) - 8, L - 8, 16, Qt.AlignRight | Qt.AlignVCenter, vs)
        n = len(self.data)
        step = gw / n
        bw = min(24, step / 3)
        for i, d in enumerate(self.data):
            cx = L + step * i + step / 2
            ih = gh * (d["income"] / mx)
            eh = gh * (d["expense"] / mx)
            p.setBrush(QBrush(QColor(tc("green"))))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(int(cx - bw - 2), int(T + gh - ih), int(bw), int(ih), 6, 6)
            p.setBrush(QBrush(QColor(tc("red"))))
            p.drawRoundedRect(int(cx + 2), int(T + gh - eh), int(bw), int(eh), 6, 6)
            p.setPen(QPen(QColor(tc("ink2"))))
            p.drawText(int(cx - 30), H - 22, 60, 18, Qt.AlignCenter, str(d["m"]))
        p.end()


class Donut(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = []
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_data(self, d):
        self.data = d
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        side = min(self.width(), self.height())
        rect = QRect((self.width() - side) // 2 + 18,
                     (self.height() - side) // 2 + 18,
                     side - 36, side - 36)
        tot = sum(v for _, v in self.data)
        if tot <= 0 or not self.data:
            p.setPen(QPen(QColor(tc("line2")), 26))
            p.drawArc(rect, 0, 360 * 16)
            p.end()
            return
        start = 90 * 16
        for name, val in self.data:
            span = -int(360 * 16 * val / tot)
            p.setPen(QPen(QColor(CAT_COLORS.get(name, "#8d99ae")), 26,
                           Qt.SolidLine, Qt.FlatCap))
            p.drawArc(rect, start, span)
            start += span
        p.end()


# ─────────────────────────────────────────────────────────
# 主窗口
# ─────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self, user, icloud, cfg):
        super().__init__()
        self.user = user
        self.icloud = icloud
        self.cfg = cfg
        self.db = DB(user["id"], icloud)
        self.theme = self.db.get("theme", "light") or "light"
        self.lang = self.db.get("lang", "zh_CN") or "zh_CN"
        I18n.set(self.lang)
        self.setWindowTitle(f"{APP_EN} · {user['name']}  v{APP_VERSION}")
        self.setMinimumSize(1000, 700)
        self.resize(1120, 780)
        self.setWindowIcon(self._icon())
        self.offset = 0
        self.editing_id = None
        self.add_type = "expense"
        self.add_cat = "food"
        self._build()
        self._tray()
        self._refresh_all()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._check_all_budgets)
        self.timer.start(30 * 60 * 1000)

    def _icon(self):
        for p in [Path(__file__).parent / "icons" / "icon.icns",
                  Path(__file__).parent / "icons" / "icon.png",
                  Path(__file__).parent / "icons" / "icon.svg"]:
            if p.exists():
                ic = QIcon(str(p))
                if not ic.isNull():
                    return ic
        pm = QPixmap(128, 128)
        pm.fill(Qt.transparent)
        pa = QPainter(pm)
        pa.setRenderHint(QPainter.Antialiasing)
        pa.setBrush(QColor("#0a84ff"))
        pa.setPen(Qt.NoPen)
        pa.drawRoundedRect(0, 0, 128, 128, 28, 28)
        pa.setPen(QColor("#ffffff"))
        f = QFont()
        f.setPointSize(48)
        f.setBold(True)
        pa.setFont(f)
        pa.drawText(pm.rect(), Qt.AlignCenter, "L+")
        pa.end()
        return QIcon(pm)

    # ---------- UI：整体 ----------
    def _build(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        outer.addLayout(body, 1)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(230)
        body.addWidget(self.sidebar)
        self._build_sidebar()

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)
        body.addLayout(right, 1)
        self._build_topbar(right)

        self.stack = QStackedWidget()
        right.addWidget(self.stack, 1)
        self._build_pages()

        bar = QFrame()
        bar.setObjectName("statusbar")
        bar.setFixedHeight(30)
        sl = QHBoxLayout(bar)
        sl.setContentsMargins(16, 0, 16, 0)
        self.status_msg = make_label(tr("brand.sub"), "status")
        sl.addWidget(self.status_msg)
        sl.addStretch(1)
        sl.addWidget(make_label(f"{COPYRIGHT}  ·  {EMAIL}", "copyright"))
        outer.addWidget(bar)

    def _build_sidebar(self):
        lay = QVBoxLayout(self.sidebar)
        lay.setContentsMargins(16, 20, 16, 16)
        lay.setSpacing(6)
        row = QHBoxLayout()
        row.setSpacing(12)
        mk = QLabel("L+")
        mk.setObjectName("brandmark")
        mk.setFixedSize(42, 42)
        mk.setAlignment(Qt.AlignCenter)
        row.addWidget(mk)
        col = QVBoxLayout()
        col.setSpacing(1)
        col.addWidget(make_label(tr("brand.name"), None, size=15, bold=True))
        col.addWidget(make_label(tr("brand.sub"), "sub", wrap=True))
        row.addLayout(col)
        row.addStretch(1)
        lay.addLayout(row)
        lay.addSpacing(14)
        self.nav = {}
        for k, key in [("overview", "nav.overview"), ("add", "nav.add"),
                       ("list", "nav.list"), ("stats", "nav.stats"),
                       ("settings", "nav.settings")]:
            b = QPushButton(tr(key))
            b.setProperty("class", "navBtn")
            b.setProperty("active", "true" if k == "overview" else "false")
            b.setCursor(Qt.PointingHandCursor)
            b.setMinimumHeight(40)
            b.clicked.connect(lambda _=False, kk=k: self._go(kk))
            lay.addWidget(b)
            self.nav[k] = b
        lay.addStretch(1)
        urow = QHBoxLayout()
        urow.addWidget(make_label("👤 " + self.user["name"], "sub"))
        urow.addStretch(1)
        sw = QPushButton(tr("login.switch"))
        sw.setProperty("cls", "link")
        sw.setCursor(Qt.PointingHandCursor)
        sw.clicked.connect(self._switch_user)
        urow.addWidget(sw)
        lay.addLayout(urow)

    def _build_topbar(self, parent):
        bar = QFrame()
        bar.setObjectName("topbar")
        bar.setFixedHeight(60)
        l = QHBoxLayout(bar)
        l.setContentsMargins(20, 8, 20, 8)
        l.setSpacing(12)
        self.page_title = make_label(tr("ov.title"))
        self.page_title.setObjectName("pagetitle")
        l.addWidget(self.page_title)
        l.addStretch(1)
        l.addWidget(make_label(tr("top.lang")))
        self.lang_combo = QComboBox()
        self.lang_combo.setMinimumWidth(120)
        for code, name in LANGS:
            self.lang_combo.addItem(name, code)
        codes = [c for c, _ in LANGS]
        idx = codes.index(self.lang) if self.lang in codes else 0
        self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self._on_lang)
        l.addWidget(self.lang_combo)
        self.theme_btn = QPushButton(tr("top.dark") if self.theme == "light" else tr("top.light"))
        self.theme_btn.setProperty("cls", "ghost")
        self.theme_btn.clicked.connect(self._toggle_theme)
        l.addWidget(self.theme_btn)
        parent.addWidget(bar)

    def _build_pages(self):
        while self.stack.count():
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.deleteLater()
        self.p_overview = self._scroll(self._page_overview())
        self.p_add = self._scroll(self._page_add())
        self.p_list = self._scroll(self._page_list())
        self.p_stats = self._scroll(self._page_stats())
        self.p_settings = self._scroll(self._page_settings())
        for w in (self.p_overview, self.p_add, self.p_list, self.p_stats, self.p_settings):
            self.stack.addWidget(w)

    def _scroll(self, w):
        s = QScrollArea()
        s.setWidgetResizable(True)
        s.setWidget(w)
        s.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        return s

    # ---------- 页：概览 ----------
    def _page_overview(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 24)
        lay.setSpacing(16)
        h = QHBoxLayout()
        c = QVBoxLayout()
        c.setSpacing(2)
        c.addWidget(make_label(tr("ov.title"), None, size=20, bold=True))
        self.ov_date = make_label("", "sub")
        c.addWidget(self.ov_date)
        h.addLayout(c)
        h.addStretch(1)
        lay.addLayout(h)

        k = QHBoxLayout()
        k.setSpacing(12)

        def kpi(label_key, attr, cls):
            cc = make_card()
            v = QVBoxLayout(cc)
            v.setContentsMargins(16, 14, 16, 14)
            v.setSpacing(6)
            v.addWidget(make_label(tr(label_key), "kpiLabel"))
            lb = make_label("¥0", cls)
            v.addWidget(lb)
            setattr(self, attr, lb)
            return cc

        k.addWidget(kpi("ov.income", "lbl_income", "kpiValIncome"))
        k.addWidget(kpi("ov.expense", "lbl_expense", "kpiValExpense"))
        k.addWidget(kpi("ov.balance", "lbl_balance", "kpiVal"))
        lay.addLayout(k)

        bc = make_card()
        bv = QVBoxLayout(bc)
        bv.setContentsMargins(16, 14, 16, 16)
        bv.setSpacing(10)
        t = QHBoxLayout()
        t.addWidget(make_label(tr("ov.budget"), "cardtitle"))
        t.addStretch(1)
        self.ov_budget_text = make_label("0 / 0", "mono")
        t.addWidget(self.ov_budget_text)
        bv.addLayout(t)
        self.ov_bar = QProgressBar()
        self.ov_bar.setTextVisible(False)
        self.ov_bar.setFixedHeight(10)
        self.ov_bar.setRange(0, 100)
        bv.addWidget(self.ov_bar)
        self.ov_budget_note = make_label("", "sub", wrap=True)
        bv.addWidget(self.ov_budget_note)
        lay.addWidget(bc)

        tc_card = make_card()
        tv = QVBoxLayout(tc_card)
        tv.setContentsMargins(16, 14, 16, 14)
        tv.setSpacing(8)
        tv.addWidget(make_label(tr("ov.trend"), "cardtitle"))
        self.ov_chart = BarChart()
        tv.addWidget(self.ov_chart)
        lay.addWidget(tc_card)

        rc = make_card()
        rv = QVBoxLayout(rc)
        rv.setContentsMargins(16, 14, 16, 16)
        rv.setSpacing(8)
        rh = QHBoxLayout()
        rh.addWidget(make_label(tr("ov.recent"), "cardtitle"))
        rh.addStretch(1)
        vb = QPushButton(tr("ov.view_all"))
        vb.setProperty("cls", "link")
        vb.clicked.connect(lambda: self._go("list"))
        rh.addWidget(vb)
        rv.addLayout(rh)
        self.ov_recent = QVBoxLayout()
        self.ov_recent.setSpacing(0)
        rv.addLayout(self.ov_recent)
        lay.addWidget(rc)
        lay.addStretch(1)
        return w

    # ---------- 页：记一笔 ----------
    def _page_add(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 24)
        lay.setSpacing(16)
        c = QVBoxLayout()
        c.setSpacing(2)
        c.addWidget(make_label(tr("add.title"), None, size=20, bold=True))
        c.addWidget(make_label(tr("add.subtitle"), "sub"))
        lay.addLayout(c)

        card = make_card()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 18, 20, 20)
        cl.setSpacing(16)

        seg = QFrame()
        seg.setObjectName("segbg")
        seg.setFixedHeight(44)
        sl = QHBoxLayout(seg)
        sl.setContentsMargins(4, 4, 4, 4)
        sl.setSpacing(4)
        self.seg_expense = QPushButton(tr("add.expense"))
        self.seg_expense.setProperty("cls", "seg")
        self.seg_income = QPushButton(tr("add.income"))
        self.seg_income.setProperty("cls", "seg")
        self.seg_expense.setProperty("active", "true")
        self.seg_income.setProperty("active", "false")
        self.seg_expense.clicked.connect(lambda: self._set_type("expense"))
        self.seg_income.clicked.connect(lambda: self._set_type("income"))
        sl.addWidget(self.seg_expense)
        sl.addWidget(self.seg_income)
        cl.addWidget(seg)

        ar = QHBoxLayout()
        ar.addStretch(1)
        cur = make_label("¥")
        cur.setObjectName("amountCur")
        ar.addWidget(cur, 0, Qt.AlignVCenter)
        self.amount_edit = QLineEdit()
        self.amount_edit.setObjectName("amountEdit")
        self.amount_edit.setPlaceholderText("0.00")
        self.amount_edit.setFixedWidth(260)
        self.amount_edit.setAlignment(Qt.AlignCenter)
        self.amount_edit.setMinimumHeight(58)
        ar.addWidget(self.amount_edit, 0, Qt.AlignVCenter)
        ar.addStretch(1)
        cl.addLayout(ar)

        cl.addWidget(hline())
        cl.addWidget(make_label(tr("add.category"), "kpiLabel"))
        cw = QWidget()
        self.chip_flow = FlowLayout(cw, 0, 8)
        cl.addWidget(cw)

        cl.addWidget(make_label(tr("add.date"), "kpiLabel"))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setMinimumHeight(38)
        cl.addWidget(self.date_edit)

        cl.addWidget(make_label(tr("add.note"), "kpiLabel"))
        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText(tr("add.note_ph"))
        self.note_edit.setMaxLength(60)
        self.note_edit.setMinimumHeight(38)
        cl.addWidget(self.note_edit)

        self.add_save = QPushButton(tr("add.save"))
        self.add_save.setProperty("cls", "primary")
        self.add_save.setMinimumHeight(46)
        self.add_save.clicked.connect(self._save)
        cl.addWidget(self.add_save)

        lay.addWidget(card)
        lay.addStretch(1)
        self._build_chips()
        return w

    def _build_chips(self):
        if not hasattr(self, "chip_flow"):
            return
        while self.chip_flow.count():
            it = self.chip_flow.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        cats = INCOME_CATS if self.add_type == "income" else EXPENSE_CATS
        for cid in cats:
            b = QPushButton(f"● {tr('cat.' + cid)}")
            b.setProperty("cls", "chip")
            b.setProperty("active", "true" if cid == self.add_cat else "false")
            b.setCursor(Qt.PointingHandCursor)
            b.setMinimumHeight(36)
            b.clicked.connect(lambda _=False, cc=cid: self._set_cat(cc))
            self.chip_flow.addWidget(b)

    # ---------- 页：流水 ----------
    def _page_list(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 24)
        lay.setSpacing(16)
        h = QHBoxLayout()
        c = QVBoxLayout()
        c.setSpacing(2)
        c.addWidget(make_label(tr("list.title"), None, size=20, bold=True))
        self.list_month = make_label("", "sub")
        c.addWidget(self.list_month)
        h.addLayout(c)
        h.addStretch(1)
        for txt, d in [("‹", -1), ("›", 1)]:
            b = QPushButton(txt)
            b.setProperty("cls", "ghost")
            b.setFixedWidth(44)
            b.clicked.connect(lambda _=False, dd=d: self._shift_month(dd))
            h.addWidget(b)
        lay.addLayout(h)

        r = QHBoxLayout()
        r.setSpacing(12)
        for key, attr, cls in [("list.income", "l_income", "kpiValIncome"),
                               ("list.expense", "l_expense", "kpiValExpense"),
                               ("list.balance", "l_balance", "kpiVal")]:
            cc = make_card()
            v = QVBoxLayout(cc)
            v.setContentsMargins(14, 12, 14, 12)
            v.setSpacing(4)
            v.addWidget(make_label(tr(key), "kpiLabel"))
            lb = make_label("¥0", cls)
            lb.setStyleSheet("font-size:17px;")
            v.addWidget(lb)
            setattr(self, attr, lb)
            r.addWidget(cc)
        lay.addLayout(r)

        card = make_card()
        self.list_v = QVBoxLayout(card)
        self.list_v.setContentsMargins(16, 10, 16, 14)
        self.list_v.setSpacing(0)
        lay.addWidget(card)
        lay.addStretch(1)
        return w

    # ---------- 页：报表 ----------
    def _page_stats(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 24)
        lay.setSpacing(16)
        c = QVBoxLayout()
        c.setSpacing(2)
        c.addWidget(make_label(tr("stats.title"), None, size=20, bold=True))
        c.addWidget(make_label(tr("stats.subtitle"), "sub"))
        lay.addLayout(c)

        c1 = make_card()
        v1 = QVBoxLayout(c1)
        v1.setContentsMargins(16, 14, 16, 14)
        v1.setSpacing(8)
        v1.addWidget(make_label(tr("stats.trend"), "cardtitle"))
        self.big_chart = BarChart()
        v1.addWidget(self.big_chart)
        lay.addWidget(c1)

        row = QHBoxLayout()
        row.setSpacing(16)
        c2 = make_card()
        v2 = QVBoxLayout(c2)
        v2.setContentsMargins(16, 14, 16, 14)
        v2.setSpacing(8)
        v2.addWidget(make_label(tr("stats.composition"), "cardtitle"))
        self.donut = Donut()
        v2.addWidget(self.donut)
        self.donut_legend = QVBoxLayout()
        self.donut_legend.setSpacing(4)
        v2.addLayout(self.donut_legend)
        row.addWidget(c2, 1)

        c3 = make_card()
        v3 = QVBoxLayout(c3)
        v3.setContentsMargins(16, 14, 16, 14)
        v3.setSpacing(8)
        v3.addWidget(make_label(tr("stats.ranking"), "cardtitle"))
        self.rank_v = QVBoxLayout()
        self.rank_v.setSpacing(8)
        v3.addLayout(self.rank_v)
        v3.addStretch(1)
        row.addWidget(c3, 1)
        lay.addLayout(row)
        lay.addStretch(1)
        return w

    # ---------- 页：设置 ----------
    def _page_settings(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 24)
        lay.setSpacing(16)
        c = QVBoxLayout()
        c.setSpacing(2)
        c.addWidget(make_label(tr("set.title"), None, size=20, bold=True))
        c.addWidget(make_label(tr("set.subtitle"), "sub"))
        lay.addLayout(c)

        # 预算
        bc = make_card()
        bv = QVBoxLayout(bc)
        bv.setContentsMargins(16, 14, 16, 16)
        bv.setSpacing(10)
        bh = QHBoxLayout()
        bh.addWidget(make_label(tr("set.budget"), "cardtitle"))
        bh.addStretch(1)
        clr = QPushButton(tr("set.budget_clear"))
        clr.setProperty("cls", "link")
        clr.clicked.connect(self._clear_budgets)
        bh.addWidget(clr)
        bv.addLayout(bh)
        self.budget_edit = {}
        for cid in EXPENSE_CATS:
            r = QHBoxLayout()
            r.setSpacing(10)
            dot = QLabel("●")
            dot.setStyleSheet(f"color:{CAT_COLORS[cid]};")
            dot.setFixedWidth(16)
            r.addWidget(dot)
            nm = make_label(tr("cat." + cid))
            nm.setMinimumWidth(90)
            r.addWidget(nm)
            r.addStretch(1)
            ed = QLineEdit()
            ed.setFixedWidth(150)
            ed.setPlaceholderText("0")
            ed.setMinimumHeight(34)
            ed.editingFinished.connect(lambda cc=cid, ee=ed: self._on_budget(cc, ee))
            r.addWidget(ed)
            sp = make_label("", "sub")
            sp.setFixedWidth(110)
            sp.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            r.addWidget(sp)
            setattr(self, f"spent_{cid}", sp)
            self.budget_edit[cid] = ed
            bv.addLayout(r)
        lay.addWidget(bc)

        # 推送
        pc = make_card()
        pv = QVBoxLayout(pc)
        pv.setContentsMargins(16, 14, 16, 16)
        pv.setSpacing(10)
        ph = QHBoxLayout()
        ph.addWidget(make_label(tr("set.push"), "cardtitle"))
        ph.addStretch(1)
        self.notify_state = make_label(tr("set.notify_off"), "sub")
        ph.addWidget(self.notify_state)
        pv.addLayout(ph)

        pr = QHBoxLayout()
        pr.setSpacing(10)
        bn = QPushButton(tr("set.push_enable"))
        bn.setProperty("cls", "ghost")
        bn.clicked.connect(self._enable_notify)
        pr.addWidget(bn)
        bt = QPushButton(tr("set.push_test"))
        bt.setProperty("cls", "ghost")
        bt.clicked.connect(self._test_notify)
        pr.addWidget(bt)
        pr.addStretch(1)
        pv.addLayout(pr)

        th = QHBoxLayout()
        th.setSpacing(10)
        th.addWidget(make_label(tr("set.push_threshold")))
        self.warn_combo = QComboBox()
        for v in (50, 60, 70, 80, 90, 100):
            self.warn_combo.addItem(f"{v}%", v)
        cur = int(float(self.db.get("warn_ratio", "0.8")) * 100)
        self.warn_combo.setCurrentText(f"{cur}%")
        self.warn_combo.setFixedWidth(110)
        self.warn_combo.currentIndexChanged.connect(
            lambda _: self.db.put("warn_ratio", str(self.warn_combo.currentData() / 100.0)))
        th.addWidget(self.warn_combo)
        th.addStretch(1)
        pv.addLayout(th)
        pv.addWidget(make_label(tr("set.push_desc"), "sub", wrap=True))

        lh = QHBoxLayout()
        lh.addWidget(make_label(tr("set.push_log"), "kpiLabel"))
        lh.addStretch(1)
        cl2 = QPushButton(tr("set.push_clear"))
        cl2.setProperty("cls", "link")
        cl2.clicked.connect(self._clear_alerts)
        lh.addWidget(cl2)
        pv.addLayout(lh)
        self.alert_v = QVBoxLayout()
        self.alert_v.setSpacing(4)
        pv.addLayout(self.alert_v)
        lay.addWidget(pc)

        # 外观
        ac = make_card()
        av = QHBoxLayout(ac)
        av.setContentsMargins(16, 14, 16, 14)
        av.addWidget(make_label(tr("set.appearance"), "cardtitle"))
        av.addStretch(1)
        av.addWidget(make_label(tr("set.dark")))
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(tr("top.light"), "light")
        self.theme_combo.addItem(tr("top.dark"), "dark")
        self.theme_combo.setCurrentIndex(1 if self.theme == "dark" else 0)
        self.theme_combo.setFixedWidth(120)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_combo)
        av.addWidget(self.theme_combo)
        lay.addWidget(ac)

        # iCloud
        cc2 = make_card()
        cv = QVBoxLayout(cc2)
        cv.setContentsMargins(16, 14, 16, 16)
        cv.setSpacing(8)
        ch = QHBoxLayout()
        ch.addWidget(make_label(tr("set.cloud"), "cardtitle"))
        ch.addStretch(1)
        self.cloud_state = make_label("", "sub")
        ch.addWidget(self.cloud_state)
        cv.addLayout(ch)
        cv.addWidget(make_label(tr("set.cloud_desc"), "sub", wrap=True))
        cb = QHBoxLayout()
        self.cloud_btn = QPushButton("")
        self.cloud_btn.setProperty("cls", "ghost")
        self.cloud_btn.clicked.connect(self._toggle_cloud)
        cb.addWidget(self.cloud_btn)
        cb.addStretch(1)
        cv.addLayout(cb)
        lay.addWidget(cc2)

        # 数据
        dc = make_card()
        dv = QVBoxLayout(dc)
        dv.setContentsMargins(16, 14, 16, 16)
        dv.setSpacing(12)
        dv.addWidget(make_label(tr("set.data"), "cardtitle"))
        bh2 = QHBoxLayout()
        bh2.setSpacing(10)
        for key, fn in [("set.export", self._export), ("set.import", self._import)]:
            b = QPushButton(tr(key))
            b.setProperty("cls", "ghost")
            b.clicked.connect(fn)
            bh2.addWidget(b)
        self.folder_btn = QPushButton(tr("set.save_folder"))
        self.folder_btn.setProperty("cls", "ghost")
        self.folder_btn.clicked.connect(self._choose_folder)
        bh2.addWidget(self.folder_btn)
        clr3 = QPushButton(tr("set.clear"))
        clr3.setProperty("cls", "danger")
        clr3.clicked.connect(self._clear_data)
        bh2.addWidget(clr3)
        bh2.addStretch(1)
        dv.addLayout(bh2)

        vr = QHBoxLayout()
        vr.addStretch(1)
        self.version_label = make_label(f"{tr('set.version')} {APP_VERSION}", "version")
        vr.addWidget(self.version_label)
        dv.addLayout(vr)
        self.db_info = make_label("", "sub", wrap=True)
        dv.addWidget(self.db_info)
        lay.addWidget(dc)

        # 系统信息
        sc = make_card()
        sv = QVBoxLayout(sc)
        sv.setContentsMargins(16, 14, 16, 16)
        sv.setSpacing(8)
        sv.addWidget(make_label(tr("set.sysinfo"), "cardtitle"))
        self.sys_info = make_label("", "mono", wrap=True)
        sv.addWidget(self.sys_info)
        lay.addWidget(sc)

        foot = QHBoxLayout()
        foot.addStretch(1)
        foot.addWidget(make_label(f"{COPYRIGHT}  ·  {EMAIL}", "copyright"))
        lay.addLayout(foot)
        lay.addStretch(1)
        return w

    # ---------- 事件处理 ----------
    def _go(self, key):
        idx = {"overview": 0, "add": 1, "list": 2, "stats": 3, "settings": 4}[key]
        self.stack.setCurrentIndex(idx)
        for k, b in self.nav.items():
            active = "true" if k == key else "false"
            b.setProperty("active", active)
            b.style().unpolish(b)
            b.style().polish(b)
        titles = {"overview": "ov.title", "add": "add.title", "list": "list.title",
                  "stats": "stats.title", "settings": "set.title"}
        self.page_title.setText(tr(titles[key]))
        if key == "list":
            self._refresh_list()
        elif key == "stats":
            self._refresh_stats()
        elif key == "settings":
            self._refresh_settings()

    def _toggle_theme(self):
        self.theme = "dark" if self.theme == "light" else "light"
        self.db.put("theme", self.theme)
        apply_theme(self.theme)
        self.theme_btn.setText(tr("top.dark") if self.theme == "light" else tr("top.light"))
        if hasattr(self, "theme_combo"):
            self.theme_combo.blockSignals(True)
            self.theme_combo.setCurrentIndex(1 if self.theme == "dark" else 0)
            self.theme_combo.blockSignals(False)
        self._refresh_all()

    def _on_theme_combo(self, _):
        self.theme = self.theme_combo.currentData()
        self.db.put("theme", self.theme)
        apply_theme(self.theme)
        self.theme_btn.setText(tr("top.dark") if self.theme == "light" else tr("top.light"))
        self._refresh_all()

    def _on_lang(self, _):
        self.lang = self.lang_combo.currentData()
        self.db.put("lang", self.lang)
        I18n.set(self.lang)
        self.setWindowTitle(f"{APP_EN} · {self.user['name']}  v{APP_VERSION}")
        self._rebuild()

    def _rebuild(self):
        idx = self.stack.currentIndex() if hasattr(self, "stack") else 0
        old = self.centralWidget()
        self._build()
        key = ["overview", "add", "list", "stats", "settings"][min(idx, 4)]
        for k, b in self.nav.items():
            b.setProperty("active", "true" if k == key else "false")
        self.page_title.setText(tr({"overview": "ov.title", "add": "add.title",
                                    "list": "list.title", "stats": "stats.title",
                                    "settings": "set.title"}[key]))
        self._refresh_all()
        self.stack.setCurrentIndex(min(idx, 4))
        if old:
            old.deleteLater()

    def _switch_user(self):
        self.db.close()
        dlg = LoginDialog(load_users())
        if dlg.exec() == QDialog.Accepted:
            self.user = dlg.selected_user
            self.icloud = dlg.use_icloud
            self.db = DB(self.user["id"], self.icloud)
            self.lang = self.db.get("lang", "zh_CN") or "zh_CN"
            self.theme = self.db.get("theme", "light") or "light"
            I18n.set(self.lang)
            apply_theme(self.theme)
            self.setWindowTitle(f"{APP_EN} · {self.user['name']}  v{APP_VERSION}")
            self._rebuild()
            self._toast(tr("login.switched", n=self.user["name"]))
        else:
            self.db = DB(self.user["id"], self.icloud)

    def _set_type(self, t):
        self.add_type = t
        self.add_cat = INCOME_CATS[0] if t == "income" else EXPENSE_CATS[0]
        self.seg_expense.setProperty("active", "true" if t == "expense" else "false")
        self.seg_income.setProperty("active", "true" if t == "income" else "false")
        for b in (self.seg_expense, self.seg_income):
            b.style().unpolish(b)
            b.style().polish(b)
        self._build_chips()

    def _set_cat(self, c):
        self.add_cat = c
        self._build_chips()

    def _save(self):
        try:
            amt = float(self.amount_edit.text().strip())
        except ValueError:
            amt = 0
        if amt <= 0:
            QMessageBox.warning(self, APP_EN, tr("add.invalid"))
            return
        ds = self.date_edit.date().toString("yyyy-MM-dd")
        now = datetime.now().isoformat()
        tx = dict(id=self.editing_id or uuid.uuid4().hex, type=self.add_type,
                  amount=amt, category=self.add_cat,
                  note=self.note_edit.text().strip()[:60],
                  date=ds, created_at=now, updated_at=now)
        if self.editing_id:
            self.db.upd_tx(tx)
            self.editing_id = None
            self.add_save.setText(tr("add.save"))
            self._toast(tr("add.updated"))
        else:
            self.db.add_tx(tx)
            self._toast(tr("add.saved_income") if tx["type"] == "income" else tr("add.saved_expense"))
            if tx["type"] == "expense":
                self._check_budget(tx["category"], ds[:7])
        self.amount_edit.clear()
        self.note_edit.clear()
        self.date_edit.setDate(QDate.currentDate())
        self._refresh_all()
        self._go("overview")

    def _check_budget(self, cat, month):
        warn = float(self.db.get("warn_ratio", "0.8"))
        budgets = self.db.budgets()
        txs = [t for t in self.db.txs()
               if t["type"] == "expense" and t["date"][:7] == month]

        def one(name_key, disp, spent, budget):
            if budget <= 0:
                return
            ratio = spent / budget
            lv = 2 if ratio >= 1 else (1 if ratio >= warn else 0)
            if lv <= self.db.push_level(month, name_key):
                return
            self.db.set_push_level(month, name_key, lv)
            if lv >= 2:
                title = tr("push.over_title", n=disp)
                body = tr("push.over_body", s=money(spent), b=money(budget),
                          o=money(spent - budget), p=int(ratio * 100))
                tag = "exceed"
            else:
                title = tr("push.warn_title", n=disp)
                body = tr("push.warn_body", s=money(spent), b=money(budget),
                          p=int(ratio * 100))
                tag = "warn"
            notify(title, body)
            self.db.add_alert(tag, title, body)

        cat_spent = sum(t["amount"] for t in txs if t["category"] == cat)
        one(cat, tr("cat." + cat), cat_spent, budgets.get(cat, 0))
        tot_b = sum(budgets.values())
        tot_s = sum(t["amount"] for t in txs)
        one("__total__", tr("misc.total"), tot_s, tot_b)

    def _check_all_budgets(self):
        month = current_month()
        txs = [t for t in self.db.txs()
               if t["type"] == "expense" and t["date"][:7] == month]
        seen = set()
        for t in txs:
            if t["category"] not in seen:
                seen.add(t["category"])
                self._check_budget(t["category"], month)

    def _record_row(self, t, actions=True):
        row = QFrame()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 8, 0, 8)
        rl.setSpacing(12)
        ico = QLabel("＋" if t["type"] == "income" else "－")
        ico.setFixedSize(40, 40)
        ico.setAlignment(Qt.AlignCenter)
        ico.setStyleSheet(
            f"background:{CAT_COLORS.get(t['category'], '#8d99ae')};"
            f"color:#fff;border-radius:12px;font-size:18px;font-weight:700;")
        rl.addWidget(ico)
        mid = QVBoxLayout()
        mid.setSpacing(2)
        title = tr("cat." + t["category"]) + ("  ·  " + t["note"] if t["note"] else "")
        mid.addWidget(make_label(title))
        mid.addWidget(make_label(t["date"], "sub"))
        rl.addLayout(mid, 1)
        right = QVBoxLayout()
        right.setSpacing(2)
        amt = QLabel(("+" if t["type"] == "income" else "-") + money(t["amount"]))
        amt.setStyleSheet(
            f"font-family:'SF Mono',Menlo,monospace;font-size:15px;font-weight:700;"
            f"color:{tc('green') if t['type'] == 'income' else tc('red')};")
        amt.setAlignment(Qt.AlignRight)
        right.addWidget(amt)
        if actions:
            ar = QHBoxLayout()
            ar.setSpacing(6)
            ar.addStretch(1)
            ed = QPushButton("✎")
            ed.setProperty("cls", "link")
            ed.setFixedWidth(26)
            dl = QPushButton("🗑")
            dl.setProperty("cls", "link")
            dl.setFixedWidth(26)
            ed.clicked.connect(lambda _=False, x=t: self._edit(x))
            dl.clicked.connect(lambda _=False, x=t: self._delete(x))
            ar.addWidget(ed)
            ar.addWidget(dl)
            right.addLayout(ar)
        rl.addLayout(right)
        return row

    def _edit(self, t):
        self.editing_id = t["id"]
        self.add_type = t["type"]
        self.add_cat = t["category"]
        self.seg_expense.setProperty("active", "true" if t["type"] == "expense" else "false")
        self.seg_income.setProperty("active", "true" if t["type"] == "income" else "false")
        for b in (self.seg_expense, self.seg_income):
            b.style().unpolish(b)
            b.style().polish(b)
        self._build_chips()
        self.amount_edit.setText(str(t["amount"]))
        d = QDate.fromString(t["date"], "yyyy-MM-dd")
        if d.isValid():
            self.date_edit.setDate(d)
        self.note_edit.setText(t["note"])
        self.add_save.setText(tr("add.save") + " ✎")
        self._go("add")

    def _delete(self, t):
        if QMessageBox.question(self, APP_EN, tr("msg.confirm_delete")) != QMessageBox.Yes:
            return
        self.db.del_tx(t["id"])
        self._refresh_all()
        self._toast(tr("msg.deleted"))

    def _shift_month(self, d):
        self.offset += d
        self._refresh_list()

    def _on_budget(self, cid, edit):
        try:
            v = max(0.0, float(edit.text() or 0))
        except ValueError:
            v = 0.0
        self.db.set_budget(cid, v)
        self._refresh_settings()
        self._refresh_overview()

    def _clear_budgets(self):
        self.db.clear_budgets()
        self._refresh_settings()
        self._refresh_overview()
        self._toast(tr("set.budget_cleared"))

    def _enable_notify(self):
        self.db.put("notify_enabled", "1")
        notify(tr("push.test_title"), tr("push.test_body"))
        self.db.add_alert("info", tr("push.test_title"), tr("push.test_body"))
        self._refresh_settings()

    def _test_notify(self):
        notify(tr("push.test_title"), tr("push.test_body"))
        self.db.add_alert("info", tr("push.test_title"), tr("push.test_body"))
        self._refresh_settings()

    def _clear_alerts(self):
        self.db.clear_alerts()
        self._refresh_settings()

    def _toggle_cloud(self):
        new_state = not self.icloud
        if new_state and not icloud_available():
            QMessageBox.information(
                self, APP_EN,
                "iCloud Drive 不可用，请先在系统设置中登录 iCloud。")
            return
        self.db.close()
        old_path = user_db_path(self.user["id"], self.icloud)
        new_path = user_db_path(self.user["id"], new_state)
        try:
            new_path.parent.mkdir(parents=True, exist_ok=True)
            if old_path.exists() and old_path != new_path:
                shutil.copy2(old_path, new_path)
            self.icloud = new_state
            self.db = DB(self.user["id"], new_state)
            self._refresh_settings()
            self._refresh_overview()
            self._toast(tr("set.cloud_enable") if new_state else tr("set.cloud_disable"))
        except Exception as e:
            QMessageBox.warning(self, APP_EN, str(e))
            self.icloud = not new_state
            self.db = DB(self.user["id"], self.icloud)

    def _export(self):
        default_dir = self.cfg.get("export_dir") or str(Path.home())
        p, _ = QFileDialog.getSaveFileName(
            self, tr("set.export"),
            str(Path(default_dir) / f"ledger-plus-{today_str()}.json"),
            "JSON (*.json)")
        if not p:
            return
        data = {"app": "ledger-plus", "version": 2,
                "exportedAt": datetime.now().isoformat(),
                "state": {"transactions": self.db.txs(),
                          "budgets": self.db.budgets()}}
        Path(p).write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
        self._toast(tr("set.exported"))

    def _import(self):
        p, _ = QFileDialog.getOpenFileName(self, tr("set.import"),
                                            str(Path.home()), "JSON (*.json)")
        if not p:
            return
        try:
            data = json.loads(Path(p).read_text("utf-8"))
            st = data.get("state", data)
            if not isinstance(st.get("transactions"), list):
                raise ValueError("bad file")
            self.db.conn.execute("DELETE FROM transactions")
            for t in st["transactions"]:
                self.db.conn.execute(
                    "INSERT OR REPLACE INTO transactions"
                    "(id,type,amount,category,note,date,created_at,updated_at)"
                    " VALUES(?,?,?,?,?,?,?,?)",
                    (t.get("id", uuid.uuid4().hex), t.get("type", "expense"),
                     float(t.get("amount", 0)), t.get("category", "other"),
                     t.get("note", ""), t.get("date", today_str()),
                     t.get("created_at", datetime.now().isoformat()),
                     t.get("updated_at", datetime.now().isoformat())))
            self.db.clear_budgets()
            for c, a in (st.get("budgets") or {}).items():
                self.db.set_budget(c, float(a))
            self.db.conn.commit()
            self._refresh_all()
            self._toast(tr("set.imported"))
        except Exception as e:
            QMessageBox.warning(self, APP_EN, tr("set.import_failed", e=str(e)))

    def _clear_data(self):
        if QMessageBox.question(self, APP_EN, tr("set.confirm_clear")) != QMessageBox.Yes:
            return
        self.db.conn.execute("DELETE FROM transactions")
        self.db.clear_budgets()
        self.db.clear_alerts()
        self.db.conn.commit()
        self._refresh_all()
        self._toast(tr("set.cleared"))

    def _choose_folder(self):
        d = QFileDialog.getExistingDirectory(
            self, tr("set.save_folder"), str(Path.home() / "Documents"))
        if not d:
            return
        self.cfg["export_dir"] = d
        save_config(self.cfg)
        self._toast(tr("set.folder_changed"))

    def _generate_pdf(self):
        if not PDF_OK:
            QMessageBox.information(self, APP_EN, "请先安装：pip install reportlab")
            return
        month, ok = QInputDialog.getText(self, tr("pdf.title"), tr("pdf.month"),
                                          text=current_month())
        if not ok or not re.match(r"^\d{4}-\d{2}$", month or ""):
            return
        default_dir = self.cfg.get("export_dir") or str(Path.home() / "Documents")
        default = str(Path(default_dir) / f"ledger-plus-{month}.pdf")
        path, _ = QFileDialog.getSaveFileName(self, tr("pdf.title"), default, "PDF (*.pdf)")
        if not path:
            return
        try:
            PDFExporter(self.db, self.lang, month).generate(path)
            self._toast(tr("pdf.generated", p=path))
            notify(tr("pdf.title"), tr("pdf.generated", p=path))
        except Exception as e:
            QMessageBox.warning(self, APP_EN, str(e))

    # ---------- 菜单栏 ----------
    def _tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(self._icon(), self)
        self.tray.setToolTip(f"{APP_EN} · {self.user['name']}")
        menu = QMenu()
        a1 = QAction(tr("menu.quick"), self)
        a1.triggered.connect(self._quick_add)
        a2 = QAction(tr("menu.pdf"), self)
        a2.triggered.connect(self._generate_pdf)
        a3 = QAction(tr("menu.show"), self)
        a3.triggered.connect(self.show)
        a4 = QAction(tr("menu.hide"), self)
        a4.triggered.connect(self.hide)
        a5 = QAction(tr("menu.quit"), self)
        a5.triggered.connect(lambda: QApplication.instance().quit())
        menu.addAction(a1)
        menu.addAction(a2)
        menu.addSeparator()
        menu.addAction(a3)
        menu.addAction(a4)
        menu.addSeparator()
        menu.addAction(a5)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda r: self.show() if r == QSystemTrayIcon.DoubleClick else None)
        self.tray.show()
        self.setAttribute(Qt.WA_QuitOnClose, False)

    def _quick_add(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("menu.quick_title"))
        dlg.setFixedSize(360, 260)
        v = QVBoxLayout(dlg)
        v.setSpacing(12)
        v.setContentsMargins(20, 16, 20, 16)
        amt = QLineEdit()
        amt.setPlaceholderText(tr("add.amount"))
        amt.setMinimumHeight(38)
        v.addWidget(amt)
        cats = QComboBox()
        for c in EXPENSE_CATS:
            cats.addItem(tr("cat." + c), c)
        v.addWidget(cats)
        note = QLineEdit()
        note.setPlaceholderText(tr("add.note"))
        note.setMinimumHeight(34)
        v.addWidget(note)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        def ok():
            try:
                a = float(amt.text())
            except ValueError:
                return
            if a <= 0:
                return
            now = datetime.now().isoformat()
            tx = dict(id=uuid.uuid4().hex, type="expense", amount=a,
                      category=cats.currentData(), note=note.text().strip()[:60],
                      date=today_str(), created_at=now, updated_at=now)
            self.db.add_tx(tx)
            self._check_budget(tx["category"], today_str()[:7])
            self._refresh_all()
            dlg.accept()
            self._toast(tr("add.saved_expense"))

        btns.accepted.connect(ok)
        btns.rejected.connect(dlg.reject)
        v.addWidget(btns)
        dlg.exec()

    def closeEvent(self, e):
        e.ignore()
        self.hide()

    # ---------- 刷新 ----------
    def _toast(self, msg):
        if hasattr(self, "status_msg"):
            self.status_msg.setText(msg)
            QTimer.singleShot(2600, lambda: self.status_msg.setText(tr("brand.sub")))

    def _month_totals(self, key):
        inc = exp = 0.0
        for t in self.db.txs():
            if t["date"][:7] == key:
                if t["type"] == "income":
                    inc += t["amount"]
                else:
                    exp += t["amount"]
        return inc, exp

    def _refresh_all(self):
        self._refresh_overview()
        self._refresh_list()
        self._refresh_stats()
        self._refresh_settings()

    def _refresh_overview(self):
        try:
            self.ov_date.setText(I18n.locale().toString(QDate.currentDate(), QLocale.LongFormat))
        except Exception:
            self.ov_date.setText(today_str())
        inc, exp = self._month_totals(current_month())
        self.lbl_income.setText(money(inc))
        self.lbl_expense.setText(money(exp))
        bal = inc - exp
        self.lbl_balance.setText(money(bal))
        self.lbl_balance.setStyleSheet(
            f"font-size:24px;font-weight:800;color:{tc('green') if bal >= 0 else tc('red')};")

        budgets = self.db.budgets()
        tb = sum(budgets.values())
        if tb > 0:
            self.ov_budget_text.setText(f"{money(exp)} / {money(tb)}")
            self.ov_bar.setValue(min(100, int(exp / tb * 100)))
            over = exp > tb
            self.ov_bar.setStyleSheet(
                f"QProgressBar{{border:none;background:{tc('bg2')};border-radius:5px;}}"
                f"QProgressBar::chunk{{background:"
                f"{tc('red') if over else tc('accent')};border-radius:5px;}}")
            if over:
                self.ov_budget_note.setText(tr("ov.budget_over", v=money(exp - tb)))
            else:
                self.ov_budget_note.setText(tr("ov.budget_left", v=money(tb - exp)))
        else:
            self.ov_budget_text.setText("0 / 0")
            self.ov_bar.setValue(0)
            self.ov_budget_note.setText(tr("ov.budget_none"))

        data = []
        for (yy, mm) in months_back(6):
            i, e = self._month_totals(f"{yy:04d}-{mm:02d}")
            data.append({"y": yy, "m": mm, "income": i, "expense": e})
        self.ov_chart.set_data(data)

        while self.ov_recent.count():
            it = self.ov_recent.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        recs = self.db.txs()[:5]
        if not recs:
            self.ov_recent.addWidget(make_label(tr("ov.empty"), "sub", wrap=True))
        for t in recs:
            self.ov_recent.addWidget(self._record_row(t, actions=False))

    def _refresh_list(self):
        t = date.today()
        y, m = t.year, t.month + self.offset
        while m <= 0:
            m += 12
            y -= 1
        while m > 12:
            m -= 12
            y += 1
        key = f"{y:04d}-{m:02d}"
        try:
            self.list_month.setText(I18n.locale().toString(QDate(y, m, 1), "yyyy MMMM"))
        except Exception:
            self.list_month.setText(key)
        inc, exp = self._month_totals(key)
        self.l_income.setText(money(inc))
        self.l_expense.setText(money(exp))
        self.l_balance.setText(money(inc - exp))
        while self.list_v.count():
            it = self.list_v.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        rows = [t for t in self.db.txs() if t["date"][:7] == key]
        if not rows:
            self.list_v.addWidget(make_label(tr("list.empty"), "sub", wrap=True))
        for i, t in enumerate(rows):
            if i:
                self.list_v.addWidget(hline())
            self.list_v.addWidget(self._record_row(t, actions=True))

    def _refresh_stats(self):
        data = []
        for (yy, mm) in months_back(6):
            i, e = self._month_totals(f"{yy:04d}-{mm:02d}")
            data.append({"y": yy, "m": mm, "income": i, "expense": e})
        self.big_chart.set_data(data)

        mk = current_month()
        totals = {}
        for t in self.db.txs():
            if t["type"] == "expense" and t["date"][:7] == mk:
                totals[t["category"]] = totals.get(t["category"], 0) + t["amount"]
        items = sorted(totals.items(), key=lambda x: -x[1])
        self.donut.set_data(items)

        while self.donut_legend.count():
            it = self.donut_legend.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        while self.rank_v.count():
            it = self.rank_v.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

        total = sum(totals.values())
        if not items:
            self.donut_legend.addWidget(make_label(tr("stats.empty"), "sub"))
            self.rank_v.addWidget(make_label(tr("stats.empty"), "sub"))
            return

        for cid, amt in items[:6]:
            r = QHBoxLayout()
            dot = QLabel("●")
            dot.setStyleSheet(f"color:{CAT_COLORS.get(cid, '#8d99ae')};")
            dot.setFixedWidth(14)
            r.addWidget(dot)
            r.addWidget(make_label(tr("cat." + cid)))
            r.addStretch(1)
            pct = int(amt / total * 100) if total else 0
            r.addWidget(make_label(f"{pct}%", "sub"))
            av = QLabel(money(amt))
            av.setStyleSheet("font-family:'SF Mono',Menlo,monospace;font-weight:700;")
            r.addWidget(av)
            w = QWidget()
            w.setLayout(r)
            self.donut_legend.addWidget(w)

        mx = items[0][1] if items else 1
        for cid, amt in items:
            head = QHBoxLayout()
            head.addWidget(make_label(tr("cat." + cid)))
            head.addStretch(1)
            av = QLabel(money(amt))
            av.setStyleSheet("font-family:'SF Mono',Menlo,monospace;font-weight:700;")
            head.addWidget(av)
            bar = QProgressBar()
            bar.setTextVisible(False)
            bar.setFixedHeight(8)
            bar.setRange(0, 100)
            bar.setValue(int(amt / mx * 100))
            bar.setStyleSheet(
                f"QProgressBar{{border:none;background:{tc('bg2')};border-radius:4px;}}"
                f"QProgressBar::chunk{{background:{CAT_COLORS.get(cid, '#8d99ae')};border-radius:4px;}}")
            box = QVBoxLayout()
            box.setSpacing(4)
            box.addLayout(head)
            box.addWidget(bar)
            w = QWidget()
            w.setLayout(box)
            self.rank_v.addWidget(w)

    def _refresh_settings(self):
        mk = current_month()
        budgets = self.db.budgets()
        spent = {}
        for t in self.db.txs():
            if t["type"] == "expense" and t["date"][:7] == mk:
                spent[t["category"]] = spent.get(t["category"], 0) + t["amount"]
        for cid, ed in self.budget_edit.items():
            if not ed.hasFocus():
                ed.setText(str(int(budgets.get(cid, 0))) if budgets.get(cid) else "")
            getattr(self, f"spent_{cid}").setText(money(spent[cid]) if spent.get(cid) else "")

        self.cloud_state.setText(
            tr("login.cloud_on") if self.icloud else tr("login.cloud_off"))
        self.cloud_btn.setText(
            tr("set.cloud_disable") if self.icloud else tr("set.cloud_enable"))
        self.notify_state.setText(
            tr("set.notify_on") if self.db.get("notify_enabled", "0") == "1"
            else tr("set.notify_off"))

        while self.alert_v.count():
            it = self.alert_v.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        alerts = self.db.alerts(50)
        if not alerts:
            self.alert_v.addWidget(make_label(tr("set.push_log_empty"), "sub"))
        for a in alerts:
            r = QHBoxLayout()
            badge = QLabel("超支" if a["level"] == "exceed" else "预警")
            badge.setFixedWidth(46)
            badge.setAlignment(Qt.AlignCenter)
            col = tc("red") if a["level"] == "exceed" else tc("orange")
            badge.setStyleSheet(
                f"background:{col}33;color:{col};border-radius:8px;"
                f"font-size:11px;font-weight:700;")
            r.addWidget(badge)
            r.addWidget(make_label(a["body"], None, wrap=True), 1)
            r.addWidget(make_label(a["ts"][5:16].replace("T", " "), "sub"))
            w = QWidget()
            w.setLayout(r)
            self.alert_v.addWidget(w)

        try:
            size = self.db.path.stat().st_size
        except Exception:
            size = 0
        self.db_info.setText(
            tr("set.db_info", path=str(self.db.path))
            + f"   ·   {len(self.db.txs())} 条   ·   {size/1024:.1f} KB")
        self.version_label.setText(f"{tr('set.version')} {APP_VERSION}")
        self.sys_info.setText(
            f"core        ledger-plus v{APP_VERSION}\n"
            f"engine      SQLite ({'WAL/iCloud' if self.icloud else 'local'})\n"
            f"storage     {self.db.path}\n"
            f"language    {self.lang}\n"
            f"theme       {self.theme}\n"
            f"author      {AUTHOR}\n"
            f"contact     {EMAIL}")


# ─────────────────────────────────────────────────────────
# 登录 / 用户选择
# ─────────────────────────────────────────────────────────
class LoginDialog(QDialog):
    def __init__(self, users, parent=None):
        super().__init__(parent)
        self.users = users
        self.selected_user = None
        self.use_icloud = False
        self.setWindowTitle(tr("login.title"))
        self.setFixedSize(400, 480)
        v = QVBoxLayout(self)
        v.setSpacing(14)
        v.setContentsMargins(24, 20, 24, 20)
        t = make_label(tr("login.title"), None, size=20, bold=True)
        t.setAlignment(Qt.AlignCenter)
        v.addWidget(t)
        self.icloud_ok = icloud_available()
        ci = make_label(
            f"☁️ {tr('login.cloud')}: "
            f"{tr('login.cloud_on') if self.icloud_ok else tr('login.cloud_off')}",
            "sub")
        ci.setAlignment(Qt.AlignCenter)
        v.addWidget(ci)
        self.list_w = QListWidget()
        self.list_w.setSelectionMode(QAbstractItemView.SingleSelection)
        for u in users:
            it = QListWidgetItem(f"👤 {u['name']}")
            it.setData(Qt.UserRole, u)
            self.list_w.addItem(it)
        if self.list_w.count():
            self.list_w.setCurrentRow(0)
        v.addWidget(self.list_w)
        bh = QHBoxLayout()
        bh.setSpacing(10)
        nb = QPushButton(tr("login.new"))
        db = QPushButton(tr("login.delete"))
        ok = QPushButton(tr("login.title"))
        ok.setProperty("cls", "primary")
        nb.clicked.connect(self._new)
        db.clicked.connect(self._del)
        ok.clicked.connect(self._accept)
        bh.addWidget(nb)
        bh.addWidget(db)
        bh.addStretch(1)
        bh.addWidget(ok)
        v.addLayout(bh)

    def _new(self):
        name, ok = QInputDialog.getText(
            self, tr("login.new"), tr("login.name"),
            text="", placeholder=tr("login.hint"))
        if ok and name.strip():
            uid = uuid.uuid4().hex[:12]
            self.users.append({"id": uid, "name": name.strip(),
                               "created": datetime.now().isoformat()})
            save_users(self.users)
            it = QListWidgetItem(f"👤 {name.strip()}")
            it.setData(Qt.UserRole, self.users[-1])
            self.list_w.addItem(it)
            self.list_w.setCurrentItem(it)

    def _del(self):
        it = self.list_w.currentItem()
        if not it or len(self.users) <= 1:
            QMessageBox.information(self, APP_EN, "至少保留一个用户")
            return
        u = it.data(Qt.UserRole)
        if QMessageBox.question(self, APP_EN, tr("login.deleted", n=u["name"])) != QMessageBox.Yes:
            return
        self.users = [x for x in self.users if x["id"] != u["id"]]
        save_users(self.users)
        self.list_w.takeItem(self.list_w.row(it))
        for ic in (False, True):
            try:
                user_db_path(u["id"], ic).unlink(missing_ok=True)
            except Exception:
                pass

    def _accept(self):
        it = self.list_w.currentItem()
        if not it:
            return
        self.selected_user = it.data(Qt.UserRole)
        self.use_icloud = self.icloud_ok
        self.accept()


# ─────────────────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────────────────
def main():
    QApplication.setApplicationName(APP_NAME)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    apply_theme("light")
    _ensure_icons()  # 首次运行生成图标
    cfg = load_config()
    dlg = LoginDialog(load_users())
    if dlg.exec() != QDialog.Accepted:
        sys.exit(0)
    win = MainWindow(dlg.selected_user, dlg.use_icloud, cfg)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

    