---
tags: [错题本, 运维实习, W1, 权限]
date: 2026-07-21
source: W1D1 Q2
retest: [2026-07-24, 2026-07-28]
status: 已清零（2026-07-24）
---

# 错题：root 绕过 DAC 权限

## 原题
文件 644 属主 dev，root 执行 `chmod 000` 后，dev 还能读吗？root 还能读吗？为什么？

## 我当时的错误
"dev 不能读，root 不知道能不能读"

## 正确答案
- dev 不能读 ✅
- **root 能读、能写、能删**——root 不受 DAC（rwx）限制

## 核心知识点
1. rwx 权限 = **DAC（自主访问控制）**，只对普通用户生效
2. 内核权限检查第一步：看 uid 是否为 0（root），是则**直接放行，不看 rwx**
3. 类比：rwx 是门锁，root 是物业万能钥匙，`chmod 000` 换锁挡不住万能钥匙
4. 唯一能拦 root 的是 **MAC（SELinux/AppArmor）**，CentOS 默认开 SELinux

## 生产后果
程序不能用 root 跑——被攻破=拿到万能钥匙，所有文件权限形同虚设。这是 Nginx/MySQL 用专用低权用户运行的原因。

## 变体重测记录
- [x] 2026-07-22（W1D2 A1 变体：小李 chmod 000 防别人看）✅——答出 root 仍能读、DAC 只拦普通用户、SELinux 才能拦 root
- [x] 2026-07-24（W1D4 A1 二次变体：chmod 000 挡 root 被领导驳回场景）✅——答出 DAC 本质 + SELinux context。**连续 2 次变体答对，清零出本**

> 连续 2 次变体答对才清零
