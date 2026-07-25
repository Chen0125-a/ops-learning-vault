---
tags: [错题本, 运维实习, W1, Nginx, 排错]
date: 2026-07-21
source: W1D1 C4
retest: [2026-07-24, 2026-07-28]
status: 未清零
---

# 错题：Nginx 403 Forbidden 排查

## 原题
Nginx 访问网页报 403 Forbidden，怀疑权限问题，至少 3 个可能原因 + 验证命令。

## 我当时的回答
"不知道"

## 正确答案（5 个排查方向，从最常见到最少见）

| 序号 | 原因 | 验证命令 | 说明 |
|---|---|---|---|
| 1 | 网页文件没 r 权限 | `ls -l /var/www/html/index.html` | Nginx 用户读不了 |
| 2 | **目录缺 x（⭐ 最常踩）** | `ls -ld` 查每一级父目录 | 父目录没 x 进不去 |
| 3 | 属主属组不对 | `ps aux \| grep nginx` 对照 `ls -l` | Nginx 用户非属主不在属组 |
| 4 | SELinux 拦截（CentOS） | `getenforce` + `ls -Z` | context type 不匹配（如文件放 /root 下） |
| 5 | nginx.conf 配置 deny | 查配置文件 `deny all`/`allow` 段 | 配置层主动拒绝 |

## 排错套路
**先读 `/var/log/nginx/error.log` 再猜原因**——日志会直接告诉你是 "Permission denied"（权限层）还是 "forbidden by rule"（配置层），比瞎试快 10 倍。

## 关联知识点
- SELinux context：`httpd_t` 进程只能读 `httpd_sys_content_t` 文件，`restorecon -Rv` 修复
- 目录 x 权限 = 进入/穿越，没 x 连 ls 都不行

## 变体重测记录
- [ ] 2026-07-24（第 3 天）：
- [ ] 2026-07-28（第 7 天）：

> 连续 2 次变体答对才清零
