---
tags: [错题本, 运维实习, W1, find, 权限]
date: 2026-07-21
source: W1D1 C3 + 实操2
retest: [2026-07-27]
status: 未清零
---

# 错题：find 命令细节与路径

## 错误 1：`-type` 参数多写短横线
**我写的**：`find /data -type -d -exec chmod 755 {} \;` ❌
**正确**：`find /data -type d -exec chmod 755 {} \;` ✅

`-type` 的值 `d`/`f`/`l` 都不带 `-`。`-exec` 结尾必须是 ` \;`（空格+反斜杠+分号）。

## 错误 2：find 漏写路径（严重）
**我写的**：`find -type d -exec chmod 755 {} \;` ❌
**后果**：默认从当前目录开始找，把整个 /tmp 权限全改了
**正确**：`find /tmp/webroot -type d -exec chmod 755 {} \;`

> 生产教训：find 和 rm 一样，路径必须**显式写明**，执行前 `pwd` 确认位置。在 / 下漏写路径=重置全系统权限，删库跑路级。

## 错误 3：批量改权限没区分文件类型
`chmod 644` 一刀切导致 `.sh` 脚本丢执行权限。
**正确**：
```bash
find /path -type f -name "*.sh" -exec chmod 755 {} \;
find /path -type f ! -name "*.sh" -exec chmod 644 {} \;
```

## 错误 4（W1D4 A2 变体重测新增）：漏 `-name` 限定文件类型
题目要求删"20 天前的 **.log** 文件"，写成：
```bash
find /data/logs -type f -mtime +20 -exec rm -rf {} \;   # ❌ 会删掉 20 天前的所有文件
```
正解：`find /data/logs -type f -name "*.log" -mtime +20 -exec rm -f {} \;`
（`+20` 方向这次对了；`-rf` 中 `-r` 多余，删文件 `rm -f` 即可）

## 变体重测记录
- [ ] 2026-07-22（W1D2 A2 变体：删 7 天前日志）❌——参数骨架未建立，当天新课重讲
- [ ] 2026-07-24（W1D4 A2 变体：删 20 天前 .log）⚠️——方向/路径/type 全对但漏 `-name`，1对1错 → 2026-07-27 重测
- [ ] 2026-07-28（第 7 天）：

> 连续 2 次变体答对才清零
