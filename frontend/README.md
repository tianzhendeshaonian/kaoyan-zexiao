## 仓库说明（uni-app + Vue3 + Vite）

## 开发
```bash
# HBuilderX：直接导入本目录运行到微信小程序
# CLI：
npm install
npm run dev:mp-weixin   # 输出 dist/dev/mp-weixin
# 用微信开发者工具打开 dist/dev/mp-weixin 预览
```

## 配置
1. 在 `utils/config.js` 修改 `BASE_URL` 指向你的后端
2. 在 `manifest.json` 配置 `mp-weixin.appid`
3. 在 `.env` 中配置 `WECHAT_APP_ID`/`WECHAT_APP_SECRET` 后端侧

## 页面
- 首页：热门院校 + 快捷入口
- 院校检索/详情（Tab：开设专业 / 复试线 / 招生目录）
- 专业检索
- 复试线 / 复录比 / 招生目录 三独立页
- 上岸分数填报（含二次确认）+ 我的填报
- 冲稳保推荐（三档分类）
- VIP 套餐 + 订单（dev 模拟支付按钮）
- 个人中心（含合规与隐私说明）

## 合规
- 不收集考生姓名/证件号
- 上岸分数默认匿名
- 爬虫仅本地测试（详见 backend/docs/CRAWLER_COMPLIANCE.md）
