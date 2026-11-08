# Opening Radar — 无 API Key 公开网页监测版

## 全新仓库部署
1. 创建 GitHub 公共仓库 `opening-radar`，先不添加 README。
2. 将 ZIP 内文件直接上传仓库根目录。确认根目录有 `index.html`、`data/`、`scripts/`、`.github/workflows/daily.yml`。
3. Settings → Pages → Build and deployment → Source 选择 **GitHub Actions**（不是 Deploy from a branch）。
4. Settings → Actions → General → Workflow permissions 选择 **Read and write permissions** 保存。
5. Actions → **Opening Radar - Scan and Deploy** → Run workflow → Run workflow。
6. 运行完成，Settings → Pages → Visit site，网址形如 `https://USERNAME.github.io/opening-radar/`。

GitHub Pages 第一次启用后才运行工作流通常最稳妥。

## 工作机制及限制
- 每日 01:15 UTC（约新加坡09:15，实际启动可能延迟）尝试读取七个平台的公开 HTML 列表。
- 网页候选写入 `data/events.json`，不等于已确认未开票。动态页面/防护可能造成失败。
- 只有人工核实、并在最近7天复核、且首次预售时间仍在未来90天内的记录才进入正式榜单。将记录添加到 `data/verified_events.json` 后重跑工作流。
- 未接入 X/小红书互动量抓取；页面只有搜索入口，不能提供真正社交热度排名。
- 无需 Ticketmaster API 或任何 API Key，不绕过登录或反机器人限制。
- 初次部署页面显示0个正式演出可能完全正常，原因是 `data/verified_events.json` 初始为空。请查看“发现线索 / 待核实”。

## 添加人工核实的演出
在 `data/verified_events.json` 中填入对象数组，例如（仅为演示，非真实演出）：

```json
[
  {
    "id": "sample-1",
    "platform": "Ticketmaster SG",
    "artist": "示例艺人",
    "title": "示例演唱会",
    "country": "Singapore",
    "timezone": "Asia/Singapore",
    "first_sale_utc": "2027-01-01T02:00:00Z",
    "event_date_utc": "2027-04-01T12:00:00Z",
    "official_url": "https://ticketmaster.sg/",
    "verified": true,
    "verification": "人工核实官方首次预售公告",
    "verified_at": "2026-12-31",
    "social_score": null
  }
]
```

## 排查
- 404：检查是否根目录存在 `index.html`，Pages Source 是否 GitHub Actions，workflow 是否成功。
- Actions 失败：展开对应步骤查看日志；如果 `git push` 无权限，检查 Workflow permissions。
- 页面无正式演出：未核实官方首次开票信息；不是自动故障。
- 抓取全部失败：可能被站点拒绝、网络问题或动态加载，不能断言无未开票演出。
