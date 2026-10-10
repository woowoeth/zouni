# 走你（zouni.app）· 交接总入口

> 写于 2026-10-07。接手的 bot 先读这一页，再按顺序读 `docs/handoff/` 里的六份。
> 根目录的 `README.md`、`CLAUDE.md` 和 `docs/` 下的其他文档是早期“单文件版”留下的，**很多已过时**（如“56 条线路”“ourword.ai/zouni”“npm test 21 项”），以本文件和 `docs/handoff/` 为准。

## 一句话

走你是一个**杂志风的旅行攻略静态站**：按季节挑地方，按天排好每一站（几点到、待多久、怎么过去、吃什么、住哪、门票、要提前办的事），手机上能直接照着走。线上 https://zouni.app 。

## 现状（2026-10-07）

| 项 | 数 |
|---|---|
| 行程页 | 565（`data/itineraries.json` 555 条手写行程 + 少量引擎线路） |
| 目的地页 | 82：国内 34 · 亚洲 22 · 更远 26 |
| 纪录片和杂志榜单（“跟片走”） | 21 项（19 部纪录片 + 孤独星球、国家地理两个年度榜） |
| “懂一点”段落块 | 约 980 |
| 三个频道 | 本期（首页）· 走哪儿（`/where/`）· 跟片走（`/pian/`） |

## 东西在哪

| 位置 | 是什么 |
|---|---|
| `data/` | 所有手写数据（行程、目的地、坐标、门票、酒店、纪录片），见 `docs/handoff/03-数据结构.md` |
| `tools/*.py` | 生成和建站脚本；**核心是 `tools/build_site.py`**（页面模板、景点一句话 `SIGHT`、补充段 `DEEP`、频道页、“怎么去”规则都在里面） |
| `site_src/` | 网页的 `site.css`、`site.js`、`sw.js`、字体样式表、图标 |
| `build/` | 中间产物 `routes.js`、`catalog.js`（每次重新生成，不手改） |
| `tests/` | 回归测试（Chrome 内核用 puppeteer，WebKit 用 playwright） |
| `os/receipt.md` | 每回合的回执（做了什么、查出什么、结果），倒着读最快了解最近的事 |
| 输出目录 | 建站输出到 `/home/claude/zouni-site`（不在仓库里，每次重建） |

GitHub：`woowoeth/zouni`
- `main` 分支 = 线上网站（GitHub Pages，域名 zouni.app），由 `tools/deploy_site.sh` 推送
- `source` 分支 = 本项目源码（数据、脚本、样式、测试），每回合发布后同步

## 接手顺序

1. `docs/handoff/01-做了什么.md` —— 功能和内容全貌、关键决定
2. `docs/handoff/02-UI规范.md` —— 杂志风、颜色和层次、对齐、组件、写字规矩
3. `docs/handoff/03-数据结构.md` —— 每个数据文件的字段
4. `docs/handoff/04-流程和命令.md` —— 改完怎么生成、测试、发布
5. `docs/handoff/05-注意事项.md` —— 踩过的坑（**加线前必读**）
6. `docs/handoff/06-待办.md` —— 没做完的事

## 和 Jerry 合作的规矩

- 说话直接、简短，不要自夸；有错直接认、直接改
- 他倾向你自己判断、直接做完，不要反复来问确认
- 不在聊天里宣布“完成”，结果写进 `os/receipt.md`，回复里讲清楚改了什么、查出什么问题、还剩什么
- 发布前跑测试；发布后到线上核对（Pages 偶尔构建失败，要看到线上真的变了）
- 令牌（GitHub）不进仓库、不打印；需要时找 Jerry 要
