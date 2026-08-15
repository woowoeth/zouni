/* 走你·引擎层 v76 */
/* ─工具─ */
const $=id=>document.getElementById(id);
/* 时间格式化：分钟数超过 1440（24 小时）要回绕到次日，
   否则「现在出发」在深夜点会算出 25:01 这种不存在的时间。 */
const fmt=m=>{
  var v=((Math.round(m)%1440)+1440)%1440;
  return String(Math.floor(v/60)).padStart(2,'0')+':'+String(v%60).padStart(2,'0');
};
/* 需要区分「次日」时用这个 */
const fmtDay=m=>{
  var s2=fmt(m);
  return m>=1440 ? '次日 '+s2 : (m<0 ? '前一日 '+s2 : s2);
};
const money=n=>Math.round(n).toLocaleString('en-US');
/* 导航：境内直接打开高德搜索（免 Key）；境外城市换 Google，同一个按钮 */
const gq=s=>encodeURIComponent(s);
const navQ=q=> (RT&&RT.nav==='google') ? `https://www.google.com/maps/search/?api=1&query=${gq(q)}` : `https://uri.amap.com/search?keyword=${gq(q)}`;
/* 导航按钮走 data-nav，由统一处理器唤起高德 App 的「关键词直接导航」，
   而不是打开搜索页让用户再点一次。国外线路仍走 Google Maps。 */
const A=(url,label,q)=> q!=null
  ? `<button class="act" data-nav="${esc(q)}">${label} ↗</button>`
  : `<a class="act" target="_blank" rel="noopener" href="${url}">${label} ↗</a>`;


/* ═══════════════════════════════════════════════════════
   国际化基建 · i18n + 多币种
   语言：zh / en（LS 记忆 > 浏览器语言自动检测）
   货币：CNY 计价，按汇率换算展示（LS 记忆 > 时区自动检测）
   内容层（行程详情）逐步翻译：路线可挂 i18n:{en:{...}} 覆盖层
   ═══════════════════════════════════════════════════════ */
var LANG='zh', CUR='CNY';
var NO_LIMIT=999999;   /* 预算不设上限哨兵值 */
var FX={ CNY:{s:'¥',r:1}, USD:{s:'$',r:7.2}, EUR:{s:'€',r:7.85},
         HKD:{s:'HK$',r:0.92}, JPY:{s:'JP¥',r:0.048} };
var CUR_LOOP=['CNY','USD','EUR','HKD','JPY'];

var I18N={
zh:{
 'tab.home':'首页','tab.trips':'行程',
 'mh.title':'这趟去哪儿？','mh.meta':'搜目的地，或从精选线路点开即走',
 'mh.back.home':'‹ 首页','mh.back.trips':'‹ 行程',
 'sheet.dest':'目的地','sheet.dest.ph':'想去哪儿','sheet.days':'几天','sheet.budget':'预算（每人含住宿）','sheet.taste':'这趟想要 · 可多选',
 'sheet.go':'安排行程 →','sheet.edit':'修改行程','sheet.per':'每人','sheet.day':'天','day.add':'+1 天','day.added':'已加到 {n} 天 · 从备选里排','day.nomore':'已无景点，请自行安排','sheet.nolimit':'不设上限',
 'budget.loose':'宽松','budget.thrift':'精打细算',
 'sheet.onlyplan':'目前只有 {n} 天方案','sheet.budget.k':'预算 · 每人','sheet.budget.car':'（含租车油费）',
 'tab.me':'我的','me.head':'我的','me.settings':'设置','me.lang':'语言','me.cur':'货币',
 'me.taste':'我的口味','me.taste.sub':'全局偏好 · 安排行程时默认带上','me.rec':'旅行记录','me.rec.want':'想去','me.rec.gone':'去过','me.rec.empty':'还没有想去或去过的地方 · 点线路会记在这里',
 'me.data':'数据','me.privacy':'所有数据只存在这台设备上 · 不上传','me.clear':'清除全部数据','me.clear.confirm':'再点一次确认清除',
 'me.privacy.link':'隐私政策','me.about':'走你 v11 · 计划赶得上变化',
  'me.export':'导出备份（复制到剪贴板）','me.import':'导入备份','me.export.ok':'备份已复制 · 粘贴保存到任意地方',
 'me.import.ph':'粘贴 ZOUNI-BACKUP 备份内容','me.import.ok':'导入成功 · 正在刷新','me.import.bad':'备份格式不对 · 检查后重试',
 'share.received':'已还原朋友分享的行程',
 'depart.set':'设出发日期','depart.on':'{d} 出发','share.days':'天','share.link':'链接',
 'taste.photo':'拍照','taste.food':'美食','taste.art':'历史','taste.geo':'山水',
 'taste.hike':'徒步','taste.chill':'躺平','taste.folk':'人文','taste.star':'星空',
 'seasons.addnow':'本次加入','seasons.added':'已加入本次',
 'extras.upday':'改 {n} 天可排入','toast.upday':'已改成 {n} 天 · 这站已排进行程',
 'me.credits':'图片来源与授权','me.credits.sub':'实景图来自维基共享资源 · 地图来自 OpenStreetMap',
 'credits.title':'图片来源','credits.intro':'本产品的线路封面来自维基共享资源（Wikimedia Commons）的自由授权图片，地图来自 OpenStreetMap。以下为逐条署名。',
 'credits.map':'全部地图 © OpenStreetMap 贡献者 · ODbL 授权',
 'extras.can':'其中 {n} 处能直接加进当天','extras.pool':'另有 {n} 处备选 · 用「+1 天」排成新的一天','extras.none':'这条线的备选还在整理','free':'免费','err.route':'这条线路暂时打不开 · 已退回上一条','err.nav':'这条行程还没有定位信息','cta.copy':'复制到微信','cta.save':'保存','sim.rain':'遇上下雨 / 管制',
 'dp.title':'哪天出发','dp.clear':'不设日期','dp.set':'出发日 {d} · 已按日期重排','dp.cleared':'已取消出发日期',
 'cmp.title':'换成天气方案？','cmp.lead':'先看清代价再决定 —— 下面是换方案后的变化。',
 'cmp.keep':'保持原计划','cmp.apply':'换成这个',
 'cmp.k.change':'行程调整','cmp.k.km':'里程变化','cmp.k.cost':'花费变化','cmp.k.drop':'让位站点','cmp.k.flag':'受影响站点',
 'cmp.v.reroute':'绕行改线','cmp.v.swap':'{n} 站换室内','cmp.v.none':'无需换站','cmp.v.same':'不变',
 'cmp.v.drop':'多让 {n} 站','cmp.v.no':'无','cmp.v.flagged':'{n} 站受影响','cmp.k.hint':'具体怎么应对',
 'cmp.done.alt':'已绕行改线 · 按新路线重排','cmp.done.swap':'已换 {n} 站室内 · 其余不变',
 'cmp.revert':'天气好转 · 已换回原线','sim.reset':'恢复原计划',
 'stat.drive':'全程自驾','stat.per':'人均','stat.nights':'{n} 晚住宿','stat.oneday':'一日往返','stat.spots':'片区','stat.spots.u':'片','stat.night':'住宿','stat.night.u':'晚','stat.strength':'强度',
 'str.轻':'轻','str.中':'中','str.重':'重',
 'cost.title':'费用怎么花','cost.tix':'门票与体验','cost.food':'餐饮','cost.car':'交通','cost.lodge':'住宿 · {n} 晚（按房均摊）','cost.total':'合计',
 'cost.margin':'≤{b} · 余量 {m}','cost.over':'≤{b} · <span class="over">超 {m}</span> · ','cost.fuel':' · 油费按 {km} km 实时估','cost.arrive':'不含往返大交通 · ','cost.nolimit':'不设上限',
 'lodge.tonight':'今晚住','lodge.by':'{t} 前抵店','lodge.night':'/晚',
 'search.ph':'搜索目的地，如西藏、黄山、额济纳…','search.cancel':'取消','search.close':'关闭',
 'search.recent':'最近搜索','search.hot':'热门目的地','search.rec':'推荐线路','search.rel':'"{q}" 相关线路',
 'search.none':'没有找到"{q}"的相关线路','search.try':'试试 西藏 · 黄山 · 新疆','search.from':'人均约 {p} 起',
 'sc.back':'‹ 返回','sc.days':'几天','sc.avail':'已有 {d} 天方案','sc.ext':'自由延伸',
 'sc.extnote':'先按 {n} 天排好 · 多出的 {x} 天路上随意加','sc.budget':'预算级别（每人含住宿）','sc.taste':'这趟想要 · 可多选',
 'sc.per':'≈ {p}/人','sc.go':'安排行程',
 'tier.compact':'紧凑','tier.compact.d':'能省就省，住宿选经济款','tier.normal':'宽松','tier.normal.d':'不将就，舒适出行',
 'tier.premium':'轻奢','tier.premium.d':'好住好吃，住得再好一点','tier.luxury':'顶级','tier.luxury.d':'最好的房间，不看预算',
 'trips.head':'行程','trips.mine':'我的行程','trips.add':'创建新行程','trips.add.sub':'选目的地 · 设天数 · 一键出发',
 'trips.per':'约 {p}/人','trips.draft':'设计稿 · 制作中','trips.empty':'还没有自己的行程','trips.empty.sub':'点上面「创建新行程」，一分钟出一份',
 'trips.del':'✕','trips.del.confirm':'确认删除',
 'toast.drawn':'行程已安排好','toast.redrawn':'已重新安排','toast.deleted':'已删除',
 'toast.saved':'已存入行程 · 在「行程」里查看','toast.copied':'链接已复制 · 发到微信','toast.copyfail':'复制失败 · 长按地址栏手动复制',
 'toast.extdays':'已按 {n} 天安排 · 多出的 {x} 天随意加','toast.mindays':'最短 {n} 天 · 已按 {n} 天安排',
 'eb.why':'为什么这样排','eb.enroute':'路上遇到状况？','eb.season':'赶季节 · 过期不候','eb.map':'路线动线',
 'eb.lodge':'今晚住','eb.cost':'费用 · 每人','eb.todo':'出发前','eb.extras':'路上还有',
 'plan.note':'','eyebrow':'先挑一条 · 点了就安排',
 'sect.alpine':'长线 · 高原雪山','sect.grass':'环线 · 大漠草原','sect.water':'山水 · 短假刚好','sect.city':'城市漫步 · 地铁可达','sect.weekend':'周末与出境',
 'lang.note':'',
},
en:{
 'tab.home':'Home','tab.trips':'Trips',
 'mh.title':'Where to next?','mh.meta':'Search a destination, or tap a curated route to go',
 'mh.back.home':'‹ Home','mh.back.trips':'‹ Trips',
 'sheet.dest':'Destination','sheet.dest.ph':'Where to?','sheet.days':'Days','sheet.budget':'Budget (per person, incl. stay)','sheet.taste':'What you want · pick any',
 'sheet.go':'Plan my trip →','sheet.edit':'Edit trip','sheet.per':'pp','sheet.day':'d','day.add':'+1 day','day.added':'Extended to {n} days','day.nomore':'No more spots — plan this day yourself','sheet.nolimit':'No limit',
 'budget.loose':'Comfort','budget.thrift':'Budget',
 'sheet.onlyplan':'Only a {n}-day plan for now','sheet.budget.k':'Budget · per person','sheet.budget.car':' (incl. car & fuel)',
 'tab.me':'Me','me.head':'Me','me.settings':'Settings','me.lang':'Language','me.cur':'Currency',
 'me.taste':'My travel style','me.taste.sub':'Global preferences · applied when planning','me.rec':'Travel notes','me.rec.want':'Want to go','me.rec.gone':'Been','me.rec.empty':'Nowhere yet · tap routes and they land here',
 'me.data':'Data','me.privacy':'Everything stays on this device · nothing uploaded','me.clear':'Clear all data','me.clear.confirm':'Tap again to confirm',
 'me.privacy.link':'Privacy policy','me.about':'Zouni v11 · Plans that keep up with change',
  'me.export':'Export backup (copy)','me.import':'Import backup','me.export.ok':'Backup copied · paste anywhere to keep',
 'me.import.ph':'Paste ZOUNI-BACKUP content','me.import.ok':'Imported · reloading','me.import.bad':'Invalid backup · check and retry',
 'share.received':'Restored a trip shared with you',
 'depart.set':'Set departure','depart.on':'Departs {d}','share.days':'d','share.link':'Link',
 'taste.photo':'Photo','taste.food':'Food','taste.art':'History','taste.geo':'Nature',
 'taste.hike':'Hike','taste.chill':'Chill','taste.folk':'Culture','taste.star':'Stars',
 'seasons.addnow':'Add this trip','seasons.added':'Added',
 'extras.upday':'Fits in {n} days','toast.upday':'Switched to {n} days · now included',
 'me.credits':'Image credits','me.credits.sub':'Photos from Wikimedia Commons · Maps from OpenStreetMap',
 'credits.title':'Image credits','credits.intro':'Route covers come from freely licensed images on Wikimedia Commons; maps come from OpenStreetMap. Full attribution below.',
 'credits.map':'All maps © OpenStreetMap contributors · ODbL',
 'extras.can':'{n} of these can be slotted into the day','extras.pool':'{n} more spots · use “+1 day” to add another day','extras.none':'More options coming for this route','free':'Free','err.route':'That route failed to open · went back','err.nav':'No location for this trip yet','cta.copy':'Copy link','cta.save':'Save','sim.rain':'Rain or road closure?',
 'dp.title':'Departure date','dp.clear':'No date','dp.set':'Departing {d} · replanned','dp.cleared':'Departure date cleared',
 'cmp.title':'Switch to the wet-weather plan?','cmp.lead':'See the trade-offs first — here is what changes.',
 'cmp.keep':'Keep original','cmp.apply':'Switch to this',
 'cmp.k.change':'Itinerary','cmp.k.km':'Distance','cmp.k.cost':'Cost','cmp.k.drop':'Stops dropped','cmp.k.flag':'Affected stops',
 'cmp.v.reroute':'Rerouted','cmp.v.swap':'{n} stops moved indoors','cmp.v.none':'No swap needed','cmp.v.same':'Unchanged',
 'cmp.v.drop':'{n} more dropped','cmp.v.no':'None','cmp.v.flagged':'{n} stops affected','cmp.k.hint':'What to do',
 'cmp.done.alt':'Rerouted · replanned','cmp.done.swap':'Swapped {n} stops indoors · rest unchanged',
 'cmp.revert':'Weather cleared · back to the original','sim.reset':'Back to plan',
 'stat.drive':'Self-drive','stat.per':'per person','stat.nights':'{n} nights','stat.oneday':'Day trip','stat.spots':'areas','stat.spots.u':'','stat.night':'nights','stat.night.u':'','stat.strength':'Intensity',
 'str.轻':'Easy','str.中':'Medium','str.重':'Hard',
 'cost.title':'Cost breakdown','cost.tix':'Tickets & activities','cost.food':'Food','cost.car':'Transport','cost.lodge':'Stay · {n} nights (per room, split)','cost.total':'Total',
 'cost.margin':'≤{b} · {m} under','cost.over':'≤{b} · <span class="over">{m} over</span> · ','cost.fuel':' · fuel est. on {km} km','cost.arrive':'Excludes travel to/from · ','cost.nolimit':'No budget cap',
 'lodge.tonight':'Tonight','lodge.by':'arrive by {t}','lodge.night':'/night',
 'search.ph':'Search destinations: Tibet, Kansai, Guilin…','search.cancel':'Cancel','search.close':'Close',
 'search.recent':'Recent','search.hot':'Popular','search.rec':'Suggested routes','search.rel':'Routes for "{q}"',
 'search.none':'Nothing found for "{q}"','search.try':'Try Tibet · Huangshan · Xinjiang','search.from':'from {p} pp',
 'sc.back':'‹ Back','sc.days':'Days','sc.avail':'Ready-made: {d} days','sc.ext':'flex',
 'sc.extnote':'{n}-day plan · {x} spare days are yours','sc.taste':'What matters this trip · multi-select','sc.budget':'Budget tier (per person, incl. stay)',
 'sc.per':'≈ {p} pp','sc.go':'Plan my trip',
 'tier.compact':'Lean','tier.compact.d':'Save where it counts, budget stays','tier.normal':'Comfort','tier.normal.d':'No compromises, travel easy',
 'tier.premium':'Premium','tier.premium.d':'Eat well, sleep better','tier.luxury':'Top','tier.luxury.d':'Best rooms, budget-free',
 'trips.head':'Trips','trips.mine':'My trips','trips.add':'New trip','trips.add.sub':'Pick a place · set days · go',
 'trips.per':'≈ {p} pp','trips.draft':'Draft · in the making','trips.empty':'No trips yet','trips.empty.sub':'Tap "New trip" above — one minute to plan',
 'trips.del':'✕','trips.del.confirm':'Delete?',
 'toast.drawn':'Trip planned','toast.redrawn':'Re-planned','toast.deleted':'Deleted',
 'toast.saved':'Saved · see it in Trips','toast.copied':'Link copied','toast.copyfail':'Copy failed · copy from address bar',
 'toast.extdays':'Planned as {n} days · {x} spare','toast.mindays':'Minimum {n} days · planned as {n}',
 'eb.why':'Why this route','eb.enroute':'Hit a snag?','eb.season':'In season · won\'t wait','eb.map':'Route map',
 'eb.lodge':'Tonight\'s stay','eb.cost':'Costs · per person','eb.todo':'Before you go','eb.extras':'Also nearby',
 'plan.note':'Route details are in Chinese for now — full English versions rolling out.',
 'eyebrow':'Pick one · planned instantly',
 'sect.alpine':'Long haul · Alpine & plateau','sect.grass':'Loops · Steppe & desert','sect.water':'Scenic · Short breaks','sect.city':'City walks · metro-friendly','sect.weekend':'Weekends & abroad',
 'lang.note':'Route details are in Chinese for now — English versions rolling out.',
}};
/* 卡片区双语（name/meta/line；meta 中 {p} = 精打档价格） */
I18N.zh.cards={
 xj10:['🚗 北疆环线 · 8–15 天','约 2,400 km 起 · 人均约 {p} 起','喀纳斯、独库公路、伊犁草原，一次画完这个圈。'],
 xz7:['🏔 西藏 · 7–10 天','拉萨→羊湖→日喀则→纳木错 · 人均约 {p} 起','世界屋脊的经典圈，布达拉宫和纳木错银河。'],
 sc5:['🏔 稻城·亚丁 · 5–6 天','约 1,165 km · 人均约 {p} 起','三神山近照，高原最难辜负的一趟。'],
 mls6:['🗻 梅里雪山·雨崩 · 5–6 天','丽江进出 · 两天徒步 · 人均约 {p} 起','蹲一次日照金山，走进雪山脚下的村子。'],
 cx4:['🚗 川西小环线 · 4–5 天','约 780 km · 人均约 {p} 起','四姑娘山到新都桥，高原新手刚刚好。'],
 qg7:['🚗 青甘大环线 · 7–8 天','约 2,600 km · 人均约 {p} 起','青海湖、莫高窟、七彩丹霞，大西北一次走完。'],
 hlb5:['🌾 呼伦贝尔 · 5 天','海拉尔进满洲里出 · 人均约 {p} 起','九曲十八弯到中俄界河，草原不走回头路。'],
 nm4:['🌾 额济纳·胡杨林 · 3–4 天','约 740 km · 人均约 {p} 起 · 10 月最佳','金黄胡杨只有一周，错过要等明年。'],
 dxb6:['🚗 滇西北 · 5–6 天','约 770 km · 人均约 {p} 起','洱海躺平，一路开到雪山门口。'],
 gl4:['🚢 桂林·阳朔 · 3–4 天','约 205–330 km · 人均约 {p} 起','站进 20 元人民币，竹筏漂过遇龙河。'],
 zjj4:['🏞 张家界 · 4–5 天','三山一桥 · 人均约 {p} 起','天门洞穿云，悬浮山等一场雨后。'],
 hs3:['🏔 黄山·宏村 · 2–3 天','杭州出发 · 约 640 km · 人均约 {p} 起','住一晚山顶等日出，云海从脚下开始。'],
 jz4:['🍁 九寨沟黄龙 · 4 天','约 940 km · 人均约 {p} 起','五花海一个湖看出五种蓝，黄龙三千池叠在坡上。'],
 yl6:['🐎 伊犁 · 6 天','约 910 km · 人均约 {p} 起','把河谷走透，日落时河的每道弯嵌一个太阳。'],
 tl3:['🏘 福建土楼 · 3 天','厦门进出 · 人均约 {p} 起','四菜一汤的土楼群，住进天井看星星。'],
 ts3:['⛰ 泰山曲阜 · 3 天','高铁直达 · 人均约 {p} 起','七千级台阶爬上去，四点起床等日出。'],
 njg8:['🕌 南疆 · 8 天','约 2,700 km · 人均约 {p} 起','喀什土城、帕米尔倒影、五百公里沙漠公路。'],
 bn4:['🌴 西双版纳 · 4 天','不含机票 · 人均约 {p} 起','走树冠层看野象，傣族园天天泼水。'],
 yy3:['🌾 元阳梯田 · 3 天','昆明出发 · 人均约 {p} 起','灌水期的三千七百级梯田，日出时全是镜子。'],
 qd3:['🌊 青岛 · 3 天','地铁公交 · 人均约 {p} 起','八大关十条路各种一种树，崂山直接扎进海。'],
 wh3:['🌉 武汉 · 3 天','地铁轮渡 · 人均约 {p} 起','黄鹤楼看两江，东湖比西湖大六倍。'],
 cs3:['🌶 长沙 · 3 天','地铁步行 · 人均约 {p} 起','白天在岳麓山，夜里在夜宵摊。'],
 gz5:['🪘 贵州 · 5 天','约 870 km · 人均约 {p} 起','苗寨的灯全亮起来，水帘洞从瀑布背面走过。'],
 sz3:['🏯 苏州 · 3–4 天','地铁步行 · 人均约 {p} 起','开园就进拙政园，下午泡在平江路。'],
 nj3:['🏛 南京 · 3 天','地铁直达 · 人均约 {p} 起','钟山走完中山陵，夜里看秦淮河的灯。'],
 hz3:['🌿 杭州 · 3–4 天','地铁公交 · 人均约 {p} 起','沿苏堤走一圈，进山喝一杯明前龙井。'],
 cq3:['🌉 重庆 · 3 天','轻轨索道 · 人均约 {p} 起','坐索道过江，等洪崖洞灯全亮。'],
 xm3:['🏝 厦门 · 3 天','轮渡公交 · 人均约 {p} 起','早班船进鼓浪屿，傍晚骑车看海。'],
 sy4:['🏖 三亚 · 4 天','不含机票 · 人均约 {p} 起','落地先下海，一整天泡在蜈支洲。'],
 sh3:['🌆 上海 · 3–4 天','全程地铁 · 人均约 {p} 起','外滩看对岸亮灯，梧桐区泡一整天。'],
 bj4:['🏛 北京 · 4 天','全程地铁公交 · 人均约 {p} 起','故宫走到底，景山看日落，长城挑安静那段。'],
 xa3:['🏯 西安 · 3 天','全程地铁 · 人均约 {p} 起','骑一圈城墙，看一次兵马俑，吃三天碳水。'],
 cd3:['🐼 成都 · 3–4 天','全程地铁步行 · 人均约 {p} 起','茶馆躺一下午，早起看熊猫，走之前一顿火锅。'],
 djy1:['⛲ 都江堰·青城山 · 1–2 日','成都动车往返 · 人均约 {p} 起','拜水问道一日装下，不用请假的旅行。'],
 hk3:['🚢 香港周末 · 2–3 天','全程地铁渡轮 · 人均约 {p} 起','叮叮车摇过中环，维港的风免费。'],
 kansai5:['🇯🇵 日本·关西 · 4–5 天','大阪京都奈良 · 人均约 {p} 起（不含机票）','难波连住四晚，电车串起三座城。'],
};
I18N.en.cards={
 xj10:['North Xinjiang Loop · 8–15d','~2,400 km+ · from {p} pp','Kanas, the Duku Highway, Ili grasslands — one great circle.'],
 xz7:['Tibet · 7–10d','Lhasa→Yamdrok→Shigatse→Namtso · from {p} pp','The classic roof-of-the-world loop: Potala and Namtso stars.'],
 sc5:['Daocheng Yading · 5–6d','~1,165 km · from {p} pp','Three holy peaks up close — the plateau at its finest.'],
 mls6:['Meili · Yubeng · 5–6d','Lijiang loop · 2 trek days · from {p} pp','Catch the golden sunrise, walk into the village under the peaks.'],
 cx4:['West Sichuan Mini Loop · 4–5d','~780 km · from {p} pp','Mt. Siguniang to Xinduqiao — a perfect plateau starter.'],
 qg7:['Qinghai–Gansu Loop · 7–8d','~2,600 km · from {p} pp','Qinghai Lake, Mogao Caves, rainbow Danxia in one sweep.'],
 hlb5:['Hulunbuir · 5d','Hailar in, Manzhouli out · from {p} pp','River bends to the Russian border — no backtracking.'],
 nm4:['Ejina Poplars · 3–4d','~740 km · from {p} pp · best in Oct','Golden poplars last one week a year. Miss it, wait a year.'],
 dxb6:['NW Yunnan · 5–6d','~770 km · from {p} pp','Laze by Erhai, then drive to the foot of the snow mountain.'],
 gl4:['Guilin · Yangshuo · 3–4d','~205–330 km · from {p} pp','Stand inside the ¥20 note, drift the Yulong River by raft.'],
 zjj4:['Zhangjiajie · 4–5d','Three peaks + glass bridge · from {p} pp','Through Heaven\'s Gate, then the floating peaks after rain.'],
 hs3:['Huangshan · Hongcun · 2–3d','From Hangzhou · ~640 km · from {p} pp','Sleep on the summit, wake above a sea of clouds.'],
 jz4:['🍁 Jiuzhaigou · 4d','~940 km · from {p} pp','Five shades of blue in one lake, 3,000 terraced pools.'],
 yl6:['🐎 Ili Valley · 6d','~910 km · from {p} pp','Nine suns in the river bends at sunset.'],
 tl3:['🏘 Fujian Tulou · 3d','From Xiamen · from {p} pp','Round earth castles, stars from the courtyard.'],
 ts3:['⛰ Taishan & Qufu · 3d','By high-speed rail · from {p} pp','7,000 steps up, up at four for sunrise.'],
 njg8:['🕌 South Xinjiang · 8d','~2,700 km · from {p} pp','Kashgar\'s old town, Pamir reflections, 500 km of desert road.'],
 bn4:['🌴 Xishuangbanna · 4d','Flights excluded · from {p} pp','A canopy walk for wild elephants, water splashing every day.'],
 yy3:['🌾 Yuanyang Terraces · 3d','From Kunming · from {p} pp','3,700 flooded terraces turning to mirrors at dawn.'],
 qd3:['🌊 Qingdao · 3d','Metro & bus · from {p} pp','Ten leafy streets of old villas, and Laoshan meeting the sea.'],
 wh3:['🌉 Wuhan · 3d','Metro & ferry · from {p} pp','Two rivers from the Yellow Crane Tower, a lake six times West Lake.'],
 cs3:['🌶 Changsha · 3d','Metro & on foot · from {p} pp','Days on Yuelu Hill, nights at the street stalls.'],
 gz5:['🪘 Guizhou · 5d','~870 km · from {p} pp','A thousand stilt houses lit at dusk, and a walk behind the falls.'],
 sz3:['🏯 Suzhou · 3–4d','Metro & on foot · from {p} pp','First into the Humble Administrator\'s Garden, then Pingjiang Road.'],
 nj3:['🏛 Nanjing · 3d','All by metro · from {p} pp','Climb to Sun Yat-sen\'s tomb, then the Qinhuai lights.'],
 hz3:['🌿 Hangzhou · 3–4d','Metro & bus · from {p} pp','Walk the Su Causeway, then tea in the hills.'],
 cq3:['🌉 Chongqing · 3d','Monorail & cable car · from {p} pp','Cross the river by cable car, wait for the lights.'],
 xm3:['🏝 Xiamen · 3d','Ferry & bus · from {p} pp','First ferry to Gulangyu, cycle the coast at dusk.'],
 sy4:['🏖 Sanya · 4d','Flights excluded · from {p} pp','Swim on arrival, a full day on Wuzhizhou.'],
 sh3:['🌆 Shanghai · 3–4d','All by metro · from {p} pp','The Bund at dusk, a full day in the plane-tree quarter.'],
 bj4:['🏛 Beijing · 4d','All by metro & bus · from {p} pp','The Forbidden City end to end, sunset from Jingshan, a quieter stretch of the Wall.'],
 xa3:['🏯 Xi\'an · 3d','All by metro · from {p} pp','Cycle the city wall, meet the Terracotta Army, eat carbs for three days.'],
 cd3:['🐼 Chengdu · 3–4d','All by metro & on foot · from {p} pp','An afternoon in a teahouse, pandas at dawn, hotpot before you leave.'],
 djy1:['Dujiangyan · Qingcheng · 1–2d','Rail trip from Chengdu · from {p} pp','Ancient waterworks and a Taoist mountain — no leave needed.'],
 hk3:['Hong Kong Weekend · 2–3d','All by MTR & ferry · from {p} pp','Ding-ding trams through Central; the harbour breeze is free.'],
 kansai5:['Kansai, Japan · 4–5d','Osaka Kyoto Nara · from {p} pp (excl. flights)','Four nights in Namba; trains string three cities together.'],
};
/* 类目与杂 chips 映射 */
var CNG_EN={'最美湖泊':'Top Lakes','最美古镇':'Top Old Towns','最美雅丹':'Top Yardangs','最美梯田':'Top Terraces','季节限定':'Season only','全年短袖':'Warm all year','最美草原':'Top Grasslands',
 '最美湿地':'Top Wetlands','最美沙漠':'Top Deserts','最美丹霞':'Top Danxia','最美峡谷':'Top Gorges',
 '最美海岸':'Top Coasts','最美名山':'Top Mountains','最美峰林':'Top Peak Forests',
 '徒步':'Trek','秋色限定':'Autumn only','新手友好':'Beginner-friendly','进阶':'Advanced',
 '动车直达':'By rail','免签证':'No visa','出境':'Abroad','电车通勤':'By train','地铁直达':'By metro'};
function tCng(c){ return LANG==='en' ? (CNG_EN[c]||c) : c; }
function esc(x){ return String(x).replace(/[&<>"']/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }
function t(k,vars){
  var d=I18N[LANG]||I18N.zh; var v=(d[k]!=null?d[k]:(I18N.zh[k]!=null?I18N.zh[k]:k));
  if(vars) for(var key in vars) v=v.split('{'+key+'}').join(vars[key]);
  return v;
}
/* 路线级 i18n 覆盖层读取（兼容老内核，不用可选链） */
function LR(obj,field){
  var o=obj&&obj.i18n&&obj.i18n[LANG];
  return (o&&o[field]!=null)?o[field]:obj[field];
}
/* 货币：CNY → 当前币种 */

/* ═══ 文案内嵌金额的货币换算 ═══
   备选点说明、沿途提示这类文案里直接写着「¥130」，切到美元后仍显示人民币，
   用户会以为是两套价格。统一在渲染层把 ¥NNN 换算成当前货币。 */

/* ═══ 兜底：渲染完成后扫一遍残留的 ¥ ═══
   文案里的金额散落在几十个渲染点（费用表标题、待办、chip、备选说明…），
   逐个包 cnyText 容易漏。渲染后统一扫一次文本节点，把 ¥NNN 换成当前货币。
   只处理纯文本节点，不碰 DOM 结构。 */
function sweepCurrency(root){
  if(CUR==='CNY') return;
  const box=root||document.getElementById('plan');
  if(!box) return;
  const w=document.createTreeWalker(box, NodeFilter.SHOW_TEXT);
  const hits=[];
  let n;
  while(n=w.nextNode()){ if(/¥\s?\d/.test(n.nodeValue)) hits.push(n); }
  hits.forEach(function(node){
    node.nodeValue=node.nodeValue.replace(/¥\s?(\d[\d,]*)/g, function(_,d){
      return fm(parseInt(String(d).replace(/,/g,''),10));
    });
  });
}

function cnyText(str){
  if(str==null) return str;
  if(CUR==='CNY') return String(str);
  return String(str).replace(/¥\s?(\d[\d,]*)/g, function(_,n){
    return fm(parseInt(String(n).replace(/,/g,''),10));
  });
}

function fmN(cny){ var f=FX[CUR]; return money(Math.round(cny/f.r)); }
function fm(cny){ return FX[CUR].s+fmN(cny); }
function detectLocale(){
  try{
    var sl=localStorage.getItem('zouni_lang');
    if(sl&&I18N[sl]) LANG=sl;
    else{ var nl=(navigator.language||'zh').toLowerCase(); LANG=nl.indexOf('zh')===0?'zh':'en'; }
    var sc=localStorage.getItem('zouni_cur');
    if(sc&&FX[sc]) CUR=sc;
    else{
      var tz=''; try{ tz=Intl.DateTimeFormat().resolvedOptions().timeZone||''; }catch(e){}
      CUR = /Shanghai|Chongqing|Urumqi|Harbin/.test(tz)?'CNY'
          : /Hong_Kong|Macau/.test(tz)?'HKD'
          : /Tokyo/.test(tz)?'JPY'
          : /^Europe\//.test(tz)?'EUR'
          : (LANG==='zh'?'CNY':'USD');
    }
  }catch(e){ LANG='zh'; CUR='CNY'; }
}
function setLang(l){ LANG=l; try{localStorage.setItem('zouni_lang',l);}catch(e){} applyLang(); }
function setCur(c){ CUR=c; try{localStorage.setItem('zouni_cur',c);}catch(e){} applyLang(); }
function applyLang(){
  document.documentElement.lang = LANG==='zh'?'zh-CN':'en';
  /* 静态标记刷新 */
  var i,els=document.querySelectorAll('[data-i18n]');
  for(i=0;i<els.length;i++) els[i].textContent=t(els[i].getAttribute('data-i18n'));
  els=document.querySelectorAll('[data-i18n-ph]');
  for(i=0;i<els.length;i++) els[i].setAttribute('placeholder',t(els[i].getAttribute('data-i18n-ph')));
  els=document.querySelectorAll('[data-cng]');
  for(i=0;i<els.length;i++) els[i].textContent=tCng(els[i].getAttribute('data-cng'));
  els=document.querySelectorAll('[data-cur-sym]');
  for(i=0;i<els.length;i++) els[i].textContent=FX[CUR].s;
  /* 首页卡片（name/meta/line 按字典 + 价格换算） */
  var cards=document.querySelectorAll('.rec-card');
  for(i=0;i<cards.length;i++){
    var rid=cards[i].getAttribute('data-rec'), price=+cards[i].getAttribute('data-price');
    var C=(I18N[LANG].cards&&I18N[LANG].cards[rid])||I18N.zh.cards[rid];
    if(!C) continue;
    var n=cards[i].querySelector('.rec-name'), m=cards[i].querySelector('.rec-meta'), l=cards[i].querySelector('.rec-line');
    if(n) n.textContent=C[0];
    if(m) m.textContent=C[1].split('{p}').join(fm(price));
    if(l) l.textContent=C[2];
  }
  /* 目的地文本随语言切换（有 en 覆盖层的线路显示英文） */
  if(typeof RT!=='undefined'&&RT&&document.getElementById('dest-txt'))
    /* 已选线路 → 显示线路名；首屏空态 → 显示当前语言的占位文案 */
    document.getElementById('dest-txt').textContent =
      document.querySelector('.home-empty') ? t('sheet.dest.ph') : LR(RT,'dest');
  /* pill 状态 */
  var lp=document.getElementById('lang-pill'), cp=document.getElementById('cur-pill');
  if(lp) lp.textContent = LANG==='zh'?'中':'EN';
  if(cp) cp.textContent = FX[CUR].s;
  /* 英文态内容提示条 */
  var ln=document.getElementById('lang-note');
  if(ln){ ln.textContent=t('lang.note'); ln.style.display = (LANG==='en'&&t('lang.note'))?'':'none'; }
  /* 动态区重绘（若已初始化） */
  if(typeof RT!=='undefined'&&RT){
    if(typeof renderSheetChips==='function') renderSheetChips();
    var planOpen=document.getElementById('plan')&&document.getElementById('plan').style.display!=='none';
    if(planOpen){
      document.getElementById('mh-title').textContent=LR(RT,'title');
      document.getElementById('mh-meta').textContent=LR(RT,'meta');
      document.getElementById('why-card').textContent=LR(RT,'why');
      renderStrip(); renderStripDays(); renderDay(); renderTotals();
    } else if(document.getElementById('view-trips').style.display!=='none'){
      renderTrips();
    } else {
      document.getElementById('mh-title').textContent=t('mh.title');
      document.getElementById('mh-meta').textContent=t('mh.meta');
    }
    if(document.getElementById('search-view').style.display!==''){} 
  }
}

/* ═══ 线路封面图（缩略图内嵌，不依赖外网；实景来自 Wikimedia CC 授权，地图来自 OSM）═══ */
const COVERS={"img":{"xj10":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAGQAAAwEBAQAAAAAAAAAAAAAAAAIEAQMF/8QALBAAAgIBAQcEAgEFAAAAAAAAAQIAEQMhBBITMUFRcQUiYYEUMkJScpGxwf/EABcBAQEBAQAAAAAAAAAAAAAAAAABAgT/xAAYEQEBAQEBAAAAAAAAAAAAAAAAEQECEv/aAAwDAQACEQMRAD8A9dUnULGVY9TprmhN2bUcCNuDqwXzJvSxy3YVOmXh4lt8qjyZzXLicWmRD4aM6pIwiKUBNmzO1TCABZoD5ijkFA6Td0kcojbXsymjnS/g3Fb1DZFFnOD4BMlwjocRMJM/rOx41sb7nsFhM723nOOKeoZEBLMG+GEx/WGH6qs8QZN7+RExi45ZGP1Melj2B6rnJJJQg9CsXJ6ltGS6YL/aJ43Ey3+1/U6plyDTnJu6RW2Rna3JY9zFJM48exqD/iHFXeonWu0zdWKV2jKoAXI4HSmMTJmd/wBmZvJuct6xesW9dWMvohix7zmzDxAk71EHzBq10koRjf8AyEw7t69ISUdQmMHRRNpKrdF+J6BbCARwb7UJhzbOrWcQI+RMVvyh3FYbqoN/p2M1gqH3JXbSWDaMBHQH4ExcqFgFpz2qKeUZZSNAPmBda6TqdvVaHAvXWxNXb0YspwgWf6eUEThxZrlzqYcntsmWZ8q46PDYKw0Kr0nEbbjbe31rooA6wROHs87mk+eUs42IXQGuvLkYpyoTpXLvFIicDqCPAhLCUJvf+r5QikTPtKDlbeJyfa7BPu/3IOJrAvNZhuqjtbXoK+4v5rjpf3JS1mLc1EV/n5Yy7azNrY8SKyTDW5ZhXpptehvroLPKadpBQKRY86CQJkFakD6j8UCvdz56SQqsZqFhVs86i71X8/BkrZ+xJitnY9T5MFVtmYkNvC652YSLitVE/MIKUQ7whABM6QhKNPWYeUIQjBM6whA0ResIQA84QhCv/9k=","dxb6":"data:image/jpeg;base64,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","hk3":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD//gBlRmlsZSBzb3VyY2U6IGh0dHA6Ly9jb21tb25zLndpa2ltZWRpYS5vcmcvd2lraS9GaWxlOkhvbmdfS29uZ19Ta3lsaW5lX3ZpZXdlZF9mcm9tX1ZpY3RvcmlhX1BlYWsuanBn/9sAQwAVDhASEA0VEhESGBYVGR80Ih8dHR9ALjAmNExDUE9LQ0lIVF55ZlRZclpISWmPanJ8gIeIh1FllJ+Tg515hIeC/9sAQwEWGBgfHB8+IiI+glZJVoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKC/8AAEQgAQgBYAwEiAAIRAQMRAf/EABkAAAIDAQAAAAAAAAAAAAAAAAACAwQFAf/EADAQAAIBAwMCBAUCBwAAAAAAAAECEQADIQQSMRNBIlFhcRQygZGxBSMzQlJyocHx/8QAFwEBAQEBAAAAAAAAAAAAAAAAAgEAA//EAB8RAQEAAgICAwEAAAAAAAAAAAABAhExQRIhAzJhcf/aAAwDAQACEQMRAD8ArL+noBLzHvVV7KW7xEFo4rSZ5tKxBZCYIJjP0pkvaVFldNn0NbdVUsOS0GzA8ttNfOmvpsQEP2gVYOtA+WwPvUdm86E9NAJzxNWUazjproMdNvtQdJfx+02fStXq3niQPTw1Ily+7hDtE92FdJlR1GQuhuES3hqNtM4aFUkVq3tTdt3CnSUwYwDmovinB/gKCPQ1fKrqM4ady0BDP2qQaR1yU/zV34olt3RE+tSfG7lg6dGnzo+S6V7VrHyUV1nYtNtCo/p5oqaRp3Ua0AqgbwZOAcUjXHVQNmG7gDFIbdptPbL7dxkEscVn39wgIPAPLiudws5dP40ULnJtlR3LLUqtbOQW3TztwazE1D2gemSQU2yRx7VY0ere5eRHO7k544rSVK07bDdtBBA4Bz2pHL7WdiQFECRUGl1IGcZgfmK5qtQz6vYpYJ5GcGPWnYG1PV6p7bsF5mPEM1VOsvEEAgA84qe9pupqn3Mynf5VxtEPhOspZm3REepqy4sNNqFElmcMREiCPtV60tq6+0Xd2O9UtPo7q3V3rtg9x/qtEum8pHEruACyfetrG8VdlSxZdYyJ5JP4opGZksXCpIhcYiiljfQW+1S8SumBB3AEAA8e9VZYhjcUSPKfxVncG09q0xUCN3uYpAIZVgzIIA+vnXC5W3TubSXFGjvBiIgciJqeyltU6kpbYCFIBzOKgRN67RgwQwJ9aDcVSls/MkyexFaUViyj2XG4LtJBYk/KAa7eubzKsvSkcCCD6+VVL+odpJ3DcoX3AqIjfuIVhLSQR51LV009yXXUMwnJYjJEV1bVy9awVKGSY85rPtdRFa2p8B4nkdjUjahjY6fTTiJJ570eh7WL+sm3eBOxmEDxTjzmqxuKDbuDxPMMfwRNRyWsGIy0RxUtpANOBcgmfSp5eJa2kuaov1ENthJ2ntFFRXekl4s91TxJnM4orTOtqGt2EZJYZCjvWerTeuRuAKtGa1Re02yOrEwKppbUqyncTDEGMcGjhSvJv08QNmd5IORwJp7tsnVj6zPtUekbpG4xOAoIP1qxdub7i3bc5yZPbE07sZpCVcm8pGEwPvmnZAGInJYd6j1Gpti44MSR/Ixg+4pLmqe5LJ4QvEjNC/q7SnqAyoQjJAM8TStct22UsqEpAYDJqoRfugF7nhHGMmuNYhlhgWE4JrXKB7Nc1hI22lCiZJqNtRqbqlQdy+YFMbVoZ3bz5VxtoWSwQHsPOpuDdhbeCbjAKR2opRDN4zJb1wBRWHZtQALkDiKXTswaAxGSOaKK2PDreSqSJAJj/tPJhjJmKKKVQAkDBp9Ofn/tNFFG8Nj9lkk9JzOYFVdMAdQs5z3oornj2fydItYALaEDkVxM3FByINFFduo5O2yemuTRRRUB/9k=","qg7":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAGgAAAgMBAQAAAAAAAAAAAAAAAAIDBAUBBv/EADEQAAIBAgQEBAUDBQAAAAAAAAECAAMRBBIhMRNBUWEycYGRBRQiI6EVQtEkRFJigv/EABgBAQEBAQEAAAAAAAAAAAAAAAABAgQD/8QAHBEBAAMBAQADAAAAAAAAAAAAAAECEVEhEhMx/9oADAMBAAIRAxEAPwDczER1aVjWAH1RRiVB0M1ki+HtHWqJQp4lWOpkxddDmjBcDqTtGurSkKy8jeMK4HOQWiL7TgBBkIxSc3X3gcSp0Dr7x6LGYASGvico0iFs27TnCDcyRKIvmSTCP8so2GsIHmX+IudgfeIcZUblGb4fUvpTMVcFXU3Wk06sq55mxkq1n8KsT0EuYUYuozLTOUrurtb8RFfGquWnTFMW2UWMRVqirmrOb9jczP61rQWjiM16gQdwZOEGX66hXuGlVKiNYBql7fucARhhKj/3CgdtZ551veJuAmrDEl/+ReSYZ0By8FrdWW0QYEgWGJceggcLiRomKB7MJNjq+r2fL4aYiNXcHw27CQ0hiEW1TIe4gwr5r2UiYaD4tiLbGERqbE3NGx84S+HquaxGyzgxFQHb8zO+4XJ4wC9LGAVje9fy5y7HGclqjEMws1MH1geC2pogmYpXEccWqjJbkSB/M4RiRigMuZemY5ffeSZiFyWy1OgdqZHkZHamhurWI/3mbiWZEa1DJ0fMWt+ZSo5ab6Vwbm5Uga/mPsw+GvQfMMBY1l9TecXHqpK8amxAvMvE0EZC2epTX/EEH+TKLUqeuWqT35yTeOEVnr0Z+KqNyp9DF/V6YPh9p53grcWrVPYSenhKl7q7MvRrayxavDJ62z8Xo9D6QmQ6MaLf0vDYfuzX/F4RtDLLJxCDfN7RBiadxrtuLWj0wjcgZ16CNug9JjYaySPjKZFlOXzO8Vsa/IrbrErYFRdlJHY6ytTp1ASdhfci0uwuSuGu9XRnFuh0naGHWmxYMNeXSQ3fbOD2tIijbgn0MmmNQU1t4tepnEw9NXzWUta2Y9JnKalj9bicBVjY1STA1s1EaWQnsJ3PT6qPSZ1MKgnWKk3k0xocRCPEtvKEzWrW0UC0JAuEJsNTzl9eUISS06/hHnKuI3bzhCIFPEAK4sLeUakdYQlROfEsSoPvN6QhADtFO0IQAiEISD//2Q==","cx4":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAGgAAAwEBAQEAAAAAAAAAAAAAAAIDBAEFBv/EADAQAAICAQMCBAQEBwAAAAAAAAECABEDEiExBEETIlFhBTJxgRSRodEGI0JScvDx/8QAFwEBAQEBAAAAAAAAAAAAAAAAAAECA//EABsRAQEBAAMBAQAAAAAAAAAAAAABEQISQSED/9oADAMBAAIRAxEAPwDVkKN5i28GCKga6Ai4sClfOjFvrsJ3J0ZyGwSo9L4nX45/UWzoMhcDUarjiSxsFJNmzNuLogvzNY9pRuiwnej+cvaRMrIMrBbZbXiLhfGT504mxehRz5rWvQzTi6XAmwQH1J3kvKLlQXMljcj6RnzBF+bb3jZOjxlgy0tdhO4+mxi9Y1fWZ2LlSwFn1Fd/WowGffSp273NNUulRQnQJNXGFcrvk06Wsc3CayKJPcwjTHNE7pMdnVRbGI+cBGKoSQL32Emq6B7QdvCTUUJEipyOo1Nu3Ydo+Oy642sjfauIDqVdQw4M6VrgyTgYPMRoDGrG4+8g+XqWZggpB35MDZR9ou9xBlyFRoTXY5O36SON+owvkbNWTV8ouq+3bmEagTO3tI5M2JkIGdFPF6qImVsirqf8UXA3Ogjn2/0wrfVwmXp+s8TGGADV8wJpx9u8IEA7ZCz5H3bi9vtBs+NcZB7g2Sa/7PKy9eqWuMa241E7D6Tz8uZ8rancs3qTLOJr30+LYnA1alK3V1xEz/GyGP4PEAzcMbNfaeAW3h4hqu3pLia9vos2Xqs3i9Tm1FBahjsT+00t8R6dDWdxqDEsEANH2P7T5zW5FaiBFLAQr3c38QANp6TCqjjU/cTz+q+L9V1BP8wqPaYSuoXCtPP6zOrjVgZ8gCi2J3I5uXXqHwf0BBfZdj9Z53iMBpBIHf1M14cq6VVSQBtVbTFrWN+Pq+nYlnxqrVu17/lCZPBxMbIr/AwjtDqyvgcVFzYigBlV6jUpB4gtZEpueYn6X1bwnjMCJ3aKVNXW1xsa6234nS1zkFluIyY63MqQmGxY59ZPZ2A1AX+sx2b6gm9lgmEsLY1GLrjcAbnv7RM+RifKQb95nWsivhLR0myIqFwWtqvaRR3G/eOcn9xu5BpVqFat757wmQMQbPcwjDSJxKdN8x+kISEXUD8Mdu0m23TLUIS+HqnRIjYHLKCdtyJf4civkzK6hlHYixCEKTqMWMeLSKKG1Cefj3u/eEJUUb5DJDtCEJVMnDQhCB//2Q==","sc5":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAGgAAAQUBAAAAAAAAAAAAAAAAAAECAwQFBv/EADAQAAEEAQIEBAUDBQAAAAAAAAEAAgMRIQQSBTFRcRMiQWEUMkKB0VKhwSOCkbHh/8QAGAEAAwEBAAAAAAAAAAAAAAAAAQIDAAT/xAAgEQACAQMFAQEAAAAAAAAAAAAAAQIDERIhMUFRYSIT/9oADAMBAAIRAxEAPwDADiDgrS0nERTY5+wf+VlJbpXUmtibinudLQIsZHUJpCxtLrJYQA11t/SeS2NLOzVghmHgWWk5H5VYzTIuDQhCYQrxgaQADzANkK3o9JAfI5ge76i7+FnUSMoNmIQkDC4gAEk4AC1tXw5m5xgdQug1x/lWuGcM8B4mmIL68rR9Pug6itcKg72KUvCGxaDc4n4g0eeB7LFkY5ji1wIcDRB9F2crN0o9QAQquu4ZFrPMTslGA8evdTjVtuUcOjknBC0dTwfVROIG2Sv0n8oVlKL5J4vo5w3fZF2FJmuXNMdQseq5EzosIHUn+KbBBoj1CiSIgNnRcZkYWs1RMjBQDvVo/lbsOqy2WFwN/uFxdilY0usl0zv6bsHm08kyfYGujt4xFNBtjdTi6yPVW2Oo+Gz6QNw6LmuGcU0Dp2v1LpoXjobj79V0DNVoaMrNQwB2S4HBSNoZXJ/EaXkYtAkYS7zDHNZztXo4NPIHakS77ssNuKxdVxCKFhGmfIC47i9+CPskk0hkmzX1nEIdEC54E0ziTtB+Xpf7IXITaovtziXEnJJQkykw6IH2Wi66Uo3MxyT3FjgBu8vqCnNIGMV2ystBmrlUtNbtpA9wmK6XbuhTCyM5LR74TqXYuJWCcGOqwMKdrYxYoUUmza2vEHZbIGJCLDsGipGzOAIznoU50YzZBJ5ZThGC3aDi7Qcg4sYyd1ggEkDNpjnSPPmu/W1MGbTiqSigMFo62gGxA4Fxp3L2CFPWSC4IQuHElZpGDLmv7BOdBHd+BKT0A/6lPEIG43uPZA4iD8kMz/spfb4K/KEbGwA1pZh77T+UXBdPie3FW5hCU6vWPFM0233cUkg1c5HiGHHpVplGXIrlFCRjSPa0hrm4v5CU/wAPRjJruQo4YJIc7w72LcBTvMj2sAa2muDiK50nw9E/TwIpNIwHY5n+VJ40Dqp0eOWeSkYC6rgB/tBVgaaN4v4CMnqaH+krpehVXwolkEhseGSffmnVXl2N29xSnn0cQje8aTZQJsSE19k2Fg8ECrxndm0ko48jxllwJ4JNgNaXejQcnshL8Ix8gcC9h6A4QgppBcWzL0jG7L2i+tK0ORQhXIAeSczl90IRQrFeBjupI+SEJhS3BzVxgyhCwUNm+V/YrOiJJNlCFz1jopFhqEIUCp//2Q==","xz7":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAGgAAAgMBAQAAAAAAAAAAAAAAAAMBAgQFBv/EAC8QAAEEAAQEBQMEAwAAAAAAAAEAAgMRBBIhMSJBUWEFEzJxgSNi0RRCkaFSseH/xAAZAQADAQEBAAAAAAAAAAAAAAABAgMABAX/xAAgEQACAgICAwEBAAAAAAAAAAAAAQIRAxIxURMyQQRh/9oADAMBAAIRAxEAPwD07nitEl8tDdKMhISnEroUSDkWfN3STNruqOCWWOJoH+VRRRNtjvMB3cFYOA2cFgkinB9JrsqkzM3Y5NqgWdF0g6pRffNZPMcRporNEjjuf4W1o1mka805jLGyQ/y8LD5uIkyDkDufYLlYnxTEvdliuOM6AN9R+fwpymkUjFs62Kx2GwI+s63/AODdXf8APlC8xNDNMCJBkANkHS0KDyMqoI9oWcVKj20r3m5rL4hi4MFHmkc5zjswblWuiVWBY46BZpp42PDDIC7sbpcrF+KYrEcLKhjP7Wmyfcq0DHR8Rp3UFB5K4GWPs6zZyRYNhDps2hC578SWgxtto31URSykFzXF17oLN2jPF0zeAM1gBIxWNMfBh6Lhu92w/JSg6Zzcr5AT9opIe+OP7nDkEs898DQxdinsfI4y4iRznHck6lWgdU2cscAz06KwxHFTzlAGw3+VYT2ac1+t0cunZc21l9aHvna7D0DlLgBrohZ7a6EWD6dRSEUwGuKR8VuE78x72kzxxPlDnF73n1WSlfqYsvJo7hWE4eMoA21F18KlsWhmHZASSY20DQF/2myQB1iOzWtELM6RgoAUdrG1KJcU2GEZJM5PfZLYaLnCtlkB1AriCaWRtZRcAOo0CyHFSviMdNZ23PylPJIFmx0SNjJDZZ84cyMZWjdySX0TQAVb4rZdjsqOouFmz1BSXZRRoDeahdA69FpYC9geD+0ggbFThmtDczmktduK1UD6MoAdmBKFmophJssT3OcW0RvyQtJgha94fflya106oR2BRMTYNAbDRzcLUOw0LrLHSPBOrfL3VA90dHKXDqBqPcLQwRvdYyssXfJbyTXKA4xfDKCEcIMFgbZjQHwkzYXjL87b7H/S0mN7Tr6ffdQWmrqwrR1kQnKUPlowOjcwZQ3Izmeqq1zbvUjoRsuhka71NB91BgiduwJniv6Iv0/wxSEekWb6JuFw7XO4tK1OqcMPG023M09nFSBTr3PdJ42h/OmPm/TQfTjIFG3A8xWnssckkYf6iW8rFEKXst5cA2z9qGloNuha7Xk4hK8bHWZFzIGnhPFzI/KFVgY6Qlxc0cg7Uf0hLUhlOPZobrGL11XO8WAbJoK329kIRx8sMuDZ4KfMwoL+LirXVa5wA14AAAchCMfcSfqIClCF1nnglyIQkY8RZJ6qlm0ISFCUIQgZH//Z","hs3":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAGwAAAwEBAQEBAAAAAAAAAAAAAAMEAgUBBgf/xAA2EAABBAAFAQUFBQkAAAAAAAABAAIDEQQSITFBUQUTMmGBFCJxkaFCscHR8AYjMzVDUmJy4f/EABgBAAMBAQAAAAAAAAAAAAAAAAECAwAE/8QAHBEBAQEAAgMBAAAAAAAAAAAAAAERAiESMUFR/9oADAMBAAIRAxEAPwD0YT+1xWhh5Bzajhx0TzlJLHee3zVjJCQC11jyK6pd9OfG2iRv2T6KiOdw3BCSJXJjZSdx9EKMVsxAO6YJh0UrXX9lMFdEmG1Yx4K0pmPA5KpYQRulpoYDpaU5ulpgFaZgjKgJVdAhMOiFmfnYzgNJsgHgbK2GWVnvBzmgkCq8Xosxx3hnsy0XeJ3O/wCSdgIyInd4PeYc7bN7KV5Z2fx118EWztvTMNwNvmrWiv6a4OEn9kDSxwGYatqydTqPRdsYyL2U4jMSxoBOmo/Vqs56neGGZpBswBeZpTyB6Lm4ftd0/afdj3YMpGUgXmHmuyCCARqDsRym0MJDZTubTWtI3YfQrYK9Q1seA1w4JgcOteizR6FDiWi3aAcnZAW82mpBQlk0LNAdShYXx0BABygf7dVh8pjieYwdSQW/RaZbGmhxtVWlTOzNNEEjWiVy8eX6rvTeHLZGyOv941uxGpVDpHvikijBa97Rm06aj5bKfCADENcd+dN76ofIGSOB1aT13CbfxvhbLw8zHAEZXZrvkFUjGywYk+zvIa4kC9QAddkjFAOgEjDZzUfIVoQvI3NLjWUObqeFTyt7Jnx9Dh+0sQ+MGLDgjKCXF9C+eFO/t2SKQh8EWQOynKTfoVzC4Sxuhc4tAcMoBrYUNObUD3AUQLBP0VeNlifKXX00X7QQvOU960b2R+S5/afarsa4RMtsAOxO56n8Fy2ua7Voy3ZA4HRYc6zoLCaSB3HQlxUrsNGx0rnxgEAE6adeqFHHK0tyO0vZCMuFs1TNTOSNOqW0CQl1nNXPIWZ5MzrziqvyR3gDnVyK8/iuHHTfb0NLXFl6jdZmaXMtgJrfTdMDwBQcL1oHndYY4EgZmmgLABW9XQw6D+KGt1G1Hp+rSMvdzHWmv5PRbe2nB7He9e/K9ldnsubZqjl6hGcvrAkd/C6wLII1/XCjlJc97v8AIn6qpovKCbymweoP/UnER0S4DxeSpxslwLGcP4rddJ7mAvkaKu7+AS+7LPCPENK68qmctbMA46UNt9lWXstnSMxOYTzzYQqhE/I4vBI6g/ehN5E8SiBmea1rdTHQCkIXPPa9V4UB0RJFm9z8FmHW7QhJyanjc/BKod20VohCSFDSbdqdI/xQ3WB963f3IQqQfhjP5dCeb/NLxhJkJO9j7kIVeHsOXo6TQtA2IQhCcj//2Q==","mls6":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAGgAAAgMBAQAAAAAAAAAAAAAAAAQBAgMFBv/EAC0QAAEEAQMCBQMEAwAAAAAAAAEAAgMREgQhMQVREyIyQWEUgZEVQnHBYpLR/8QAFwEBAQEBAAAAAAAAAAAAAAAAAAECBP/EABsRAQEBAQEBAQEAAAAAAAAAAAABERICAzFB/9oADAMBAAIRAxEAPwApFK9IpdmuJnSKV6RSaYpSilpSKTRnSilpiik0Z0ilekUmjOkK9ITRvSKVwLNDcrVmlmeLbGVi+pP1vml6UUmvpJ/Ew8Mk/BWfhPyxxN3VAe6ncXmssUYp6Pp07/UAwf5FNx9PhY0tfbnEert/CzfpIs+drikKCE/JoJA4YOa9p4N0sJdLLG8Nc2yRYx3Wp7lS+KWpFK9IpXWcUpCvRPAv3QnS8uhPPp3Mts2F+WwzbvwszrpNhHUh2s0dwvLyaiaSs5XOriytIdfqYW4xzyNb2y2XHzXZr0cmrmwZgSYyMcm3f8hEuqZDqWObF5BsDwD3J+VxR1bUDE03y7ja7Kp+rarIkvH+oTmmx6GHqOfpkFN2s+k/e9tlpJ1MNIaYy4Xu4Efiu682epuGmLTGwyl1teBVD34VY9cx4LZgN/3Af85Cc02PTyTvfG3URFroncFw4HyodrGaZuePicAub6t9xt2XI0utdpnPLC4x35ozz9imNfFDqI3SQStD3CgAbDuw+Fn+qYk1MchfZ8zrA8uwHcfkJYykOjkALHNG+Av70ueNXNpnuyOJa3jbe/n+0t9fLllmcgQbO63PNZtjryhpkJa/Iub6jvsfev7QuS3qT2scwMGOWQF+nnj8oWs9JvkiXjuozHdK2VFrWM6bzHdV8QJa0WrhpgyDuo8RY2otXE0/F1GWNgZ5XtHGQ3H3G6hmvLZ/E8JhabthFijykbRanMNrpSObqXF8V9yy9wlnP3Npb5U5H3VkwtbZgjcoWQKFUUCEIUB7oQhBKgoQqIUoQoBQhCKkIQhVl//Z","hlb5":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAGAABAQEBAQAAAAAAAAAAAAAAAAIBAwT/xAArEAACAgADBwMEAwAAAAAAAAAAAQIREiExAxMUQVFhkVJxoQQiMoFCYsH/xAAYAQEBAQEBAAAAAAAAAAAAAAAAAQIDBP/EABgRAQEBAQEAAAAAAAAAAAAAAAAREgEh/9oADAMBAAIRAxEAPwD3YEbgOXEv0LybxL9C8np04Zdd2N2cuJl6F5N4mXoXkmjLruzN32I4mXoXk1fVPnBeRoyvdDd9iOK/p8jis/w+Rozx0WzV5qw9nbuq9iOKS/h8jil6fkUnFbsE8VHnF+QWk48dX0GnMlNhnlrtFX3F9yb7GOVa0iVYu+4vuc8a0FikXaGKjk5dUY2q1LWeuuNGYzjbeovsNI7bwHndoF0Om8bbrRdObE3cW4Td1pT1JS0pUbhZjTVFJ0ss3ouYxU9En75jDlTp+5lJaUiUbeWKV5Z30GJUu+S7kzWKNZkOUtnJTaTw86/wvnVdGmndZku/b3K2antFeywyvkRHauSvTkCClJ0nl3oW13QxMYupO9DF2AadWqa8AUdEiqVZ2/2YlS0samRtx5RRqnloQxkFdk4yWWTOcm06ZN8zNdXYCSTzjlLrHJnNRwqlkipSUWZKSlGrCMd9CW1avKy21arwHUoyXXVDiQlCVVGVpg5wm4fZL9MFV6ORoBFYTLUAIyOUn7MhgBR6MiQARa0Mf5IAozb6oABOv//Z","gl4":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAGgAAAwEBAQEAAAAAAAAAAAAAAAIDBAEFBv/EADUQAAICAQMDAgQDBQkAAAAAAAECABEDEiExBBNBIlEyYXGBFELRBSMzUmIkU3KRobHB4fD/xAAYAQEBAQEBAAAAAAAAAAAAAAABAAIDBP/EABwRAQEBAQADAQEAAAAAAAAAAAABERICITEDE//aAAwDAQACEQMRAD8Am2GkuyPnyIvB0MLJqjdVFGXtrpy4jXi+LlE6lXpQjN78bQ2jE9QVq2se28Zwin4gbPBj/hhXcKlwRY3i6cKgsUFV9SI9RYSgDqXYDkRrUVuZx8uJwEQEDxOUSdOIFvlUehh9YG9H2MqMtAMRt/pJLgzEblQfAZgCYjYMqYy+UdtPaxLqLmrZutTRSqSfrxJDq2Ueqr9pC0YkYgS3izJZAFF5HUDmhvD+kPNaT17FvSPSPEJkXJiJUq+3nbmEzf1XL6XHixqDS6ftcR+lxP8Ak44ra5UA2abSf8xJ5CwWgfNjeePqvRkZm6Zcf8NVS/JHA+soMLq37zQy/wCGxHaxpCsbLMxB9ohVWxqAPAarqv0jtJwbakyaRX92u33/AFi93GGNZcmavyqor/aMmBM2IMFyCviRa3Mz9cGwppKNhxE2rAgkN85exaTNmDLkbtsgrauZ43Uu+U6XXQoOw4npDH1GUVoDlfzDcERR0bKT39lAug3/AKpvx8s+jHnKxChUtb+c3p+zc3bBBxEtXoO1D3j5OzgxrkOABiaHy+cz5OrtQVYFVveVu/A1P+ye2urumxuVUbQkfxGXLQGUoo+I0doTPs5r3tQY1R+wk2yY8dgvf9I3nn5crNqD9VkfxSihOorgXjwhR/M3jxM41say4bHZGjUaUfKcU2xFUVoD7TLrYZDROXLdavA+nvKKNBCFgXJJZvYwVqyCh8RBIq4dTkcYmJI4+IjiJ3TQZU1G+LAlMtPj0PZB5FRTH+IfUUJCggAGtpLJnIyMAjNkIJAAsc8zS2AlWZ1UACkAEwFczDZH1KbCkmz4J/6jMZRDdXlZla9x8LfpOdllBfFjIPkONpq0Pkx9wr30G18MsfH0bHH3Omzmv5XmuhjFjydUotB6T/LxCa16fShd0XG4bgHY/pCHUWPSxpiRvRjH1sEwyf2he2WK3sQRVy+QMVsBXrcAiSK6Ra5WT+lhcw6WOdrtpowgBq3IiHEUwlAbvkmdZCRqok+TjO4+0UM2MnQwZT+V4DFMYRsSgDjao+ikNNuOLiK4JByIVscgygzKBQbV/wAx0EAcCrA9jzBcTK+y782dgJyyX9Lbb7XGsC2X1Hx5l9OlcphBAK6235q5JdKDQGCbXvyZQ4cZc5ThGoV6p3Lj2UuoWuD5+0fQYsjDRRNE3x4hGyoXGQfAoHp87QgzYvjY6m3PiayLXffaEJO6eQlfhJH0gQG+LfbzCEmUk8RerAAUgAEnmEIMVDo/4xHiuJtTa4QkzD4dy17xOpJ7xHiEItQiAfh7rc+ftCEIF//Z","zjj4":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAGgAAAwEBAQEAAAAAAAAAAAAAAAMEAgUBBv/EAC8QAAIBAwMCBQIFBQAAAAAAAAECEQADIQQSQTFREyIyYXEFsQYjgcHRFHKRoeH/xAAXAQEBAQEAAAAAAAAAAAAAAAACAQAD/8QAGxEBAQEAAwEBAAAAAAAAAAAAAAERAiExQRL/2gAMAwEAAhEDEQA/AODesgIGCnupry0SmQvlbAPFAd7o2nOI605IVYMSeqntU3RHh+EwLeg5n+a8trseCDt4JptsLlCd2MTyK8uKSgjoOhHFVn0P4ZdRavWWYB9wYLPURn7V1b+p0+nKi/eS2W6bj1r5HT32sXrOot4e2cjj3FY1GsfXalrlxtzHjhR2FLNbXX/Eets3ba6S1DvIdmGQMYg1wCowOg61tUgDoSc+1a2SZnHWsxLLCMwxPfvXiElYVcDGaeygqTMH4pSsVXYomaNqlAMQ3UjvRWnKqoUAM3UniipqJ7ZLnJg8Z609YYjdJYdD2+aUuwnzgkchcGmNLKDa3QMwT+1C+orKsLUooeBnvRbfeotRIPQ9x/NYs3gqgMTHGOlDAAA25ZerD96Ws93bLQ5ImTSbEbolSe6im7DdUIp9RgV3vrn0uxp9HYuWLSL4TbXIGWkc98inL0rijGw9xBr103Hyk4GRWmjcI96xcaUEA56RRvJSr1wKoUCSRS/Mq7iM9v5pyooJe4QDEKOxpZfcYVgoGOkE0d0S2D7ZbaSf9fFFBQ7l6k9yaKzMoBeKquM57mm3tObXmRiQeOaq0thbV1btxRgcDn4rF8FpMGD1J6n/AJVzosZ06eNaYbl3A4J4+aWGKmdqqZgieap0MK3mAUEQZry5aUXnfJBPI6VLg1m3c2srqsMhBiKt1et1OqtL4l5ireb2BqW3ZLO3iTGNhHBqjWaV3FtV9IQk7RU+N8RIzPK2yDxNMW0wgyNg6TWQjAbUDIg5JyaUbviMUPljiIxUSNMPGeAvp5nM0m4LVvygqxHbJmnei0d4MT1k/ehLVu2hgFmasqdfF2yF2g91orV5mdptsPecUVWUNqCHEjd3J4rFzdcYbXgHg8Uo228QItwOZ/SuzZ1N1fDsoLYEACVFLKvqLS2LrsUU7iYgAT/ntV/9Lp1gX2a9dOCFiB8mKqDrqQyWz4VwGSgAAeprk2j5iQynHHSt+YsmHrptLbcHwbhIwPzJH2rd4WCxGy5gRIeP2pZ1G9hsgS2Jpdy+peOScGts8LC9ZpTtD6YteVZ3LgMP0HWoGe1dGcNzBz8V1US49y4+/wAO2rSbhxFYv61Fu/l20Ktjc6AljHWpeMGxzjbJfDNtHEYpF6VcqiEk+/SrtZduXCtwIkmQIWKjKFiSdyCcmTQ8o0lQWc+k96KammYbihYHuDRWy3tsWWFXd6R6Z6e9MsZ1Q+KKK7H9e3iQ7EGDvOR81V9Uzp7LHLGJPNFFZkdj1r/dWrQm+Jzkfeiihx9Oqvq5OEk7dpxxXPJMDJoopUHuoMrZni5j2waoYAWFMCdxooqxqVYAOtAIwUOKKKKnL104+P/Z","djy1":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAGgAAAgMBAQAAAAAAAAAAAAAAAAMCBAUGAf/EADEQAAICAQMCBQIEBgMAAAAAAAECABEDBCExBRITIkFRgTJhM3GRwRQVUnKh8ILR4f/EABgBAAMBAQAAAAAAAAAAAAAAAAABAgME/8QAHxEBAQEAAgICAwAAAAAAAAAAAAERAhIxQQMTIVFh/9oADAMBAAIRAxEAPwB/ZI1JabU4s9dv11ZUi45vMbInZOW+HJeKvU9AjCvsJJFAIJF/aPSwrtnoEtOyutDGo/KKoWQK25i0+pfrPRJKAwtTYurhkIx42diAFF7mPYMqSsZMEk1zMjHrtSzWEXtO9faaeg1JzA5FQ4yp97MznyS+FdbDqagSOYSbsXNsbMJcpWOUDFFBxDw75KnmWOm61cTE53IDA7XdG+ZmDM6HtHmF7xrAOR4titwb3nDLeN1vmupWmUMNwRYkc7+FiZwvcQLC3VzF6d1A4GK5XZlCny3+kfq9bi1GHvV8iOdqB2E2+yYnqXm6yfp7XxEG7C2TKj6zJla0xZHYnnIf2kPEyMo7ipra23PxPKNFWyd5HrdTO898tJJFjHqs+Fu5cOVN7IDWCfeWepdQXNhTGAVO5a/f2qZxzOlAMzb7G+JWyt5jS7n1h29CyLo1GMeUNsVP+iWsOtfThjjbZhVtuTMfE5LAtLQylu4Y9q/z8SbbCxpY+r5xktqYVxVQmYfOAzNwL9oQnO/ssVe6gF7d+LjTjyY1AU8i6sf6JtDo2EbksfmPXpmIAHsDf8f+41Y5vGxAr22jXIIVtyoHE6fFo8aDbFi+Ui8/StPlfxMibn2YgQwY5zszMKCsAdwKkcoyKx8RWAPFDmdD/KtIT2qGr+8mDdK0hFHvNencYjxz+JFAAo+9k7Q8nBNj2m4ej6PkDID9nMkel6ZT5myAV/Xf7QGM7QaDDqVZ31GPEA1UwvaU2Q4tSwUGwa+03Meh0gHkbKw9bIEDo9IT5kc19/8AyAxghszbUWPIocQnQ/wumVSTiIA3s+kIixoPnAOyoo+yyPjMeLHxFg9v07T0tfLfEszFyMBXdfxAkG7IAHpFse0AkEAmgTIZMqBSLX9YEkMuMMVDAn2raSQgfXv+R5mF3ONWWq1B235ltc+d6CmvirkzfZ/lc1Wfw8TM116D3lM63CaLBgfsbjDoGzspyMxregdojUdM7B3LkCA+hBMXLRdMXUkAkCweN5BMmZ8neMhXb0MXi05Um+4kcsRsfylnGqi7Ar3q5ltE/oyvkzKVcswbkWd4RpI53292r/EI9p5Da8sXk4hCbpJdjfJispPvCEr0KMIByqCLBM1GVfB4G1VtCEirhw/aZ3VSQcNepEISb4Kkc51vfb1kn/BEITKkUv4vzCEI4cf/2Q==","hz3":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAGgAAAgMBAQAAAAAAAAAAAAAAAAMCBAUBBv/EADMQAAIBAwMBBQYEBwAAAAAAAAECEQADIQQSMVEFExRBYSIycYGRwQahsdEWI0JDUnLw/8QAFwEAAwEAAAAAAAAAAAAAAAAAAAECA//EABkRAQEBAQEBAAAAAAAAAAAAAAARASFBQv/aAAwDAQACEQMRAD8AXc222tqRO4EmTz60qE3BGLGTgk+Uc0m6driCNgkiM7R0+FSJypMezP6VojErQUlbUZaCJ4xS9QFcptLFmJ3kGMcUK7d6JwQpk+lMt2bi222qSzIRINI0LFt2N/YwUI0EgA/T96uKLA0/dtp1XUE5YmcHzmqvZTNckETba7ycAwI5q5rnt94ZYDacEHJphVuS0AorMeIX60zTWFt2Bd7v+5jcJkGOfWnaVLlzc9tSwyqyYAUH7xNSF171i9Za2AoM5Y4E0EnctshKqCy+0QD/AEgGBz8vpT7Kq1xVEl1thgWEQQcYqL3mdrBKAZbBaTxxVhRF1LkHaykEehimWraGUDEQSJzRULXsWwhM7RE9aKvEPJtCtAB+X2oUkl7dtDiCAM4NQmefrUn2D30nb61k1CLcN8K4KnkhsYmu6m/ctBbKuEF4lS0+6oOahpA4NwAh4hlJbI60q3b8T2gyOSbdpSI/71NAaGkvpb0osIl65scj2Ek9Zx5U3wuq1RFxdO1kDALkAgdVH3NX9AqWkVUG2FICxEVfQQUt9bdVCqhpLFlNODbssnIBU5+fWnLaF11cDIAJPWZqxaTagSIEGRRYADEcRj8zTzCLSwgZdw3EcH1pxUQPSpY8q4apLhorhNFMnkFzFcuQ1pvIxHxqx4K7v7w22EcqPzpV21dCkvaYKZPHMVi1SS2t3UWHUmApLHgHzqGhYm7fvAA7259Krt3i6AXUVthwGIx0irHZ25NOpFuQ0mgPR6NWurbZ4IAnirrQbiN0Bz0rJ0mvWzZ2sjz0A4ovdpbwQEuCREha0S021VkH3pjoKX4uyuWJmsRrz4wT8orneEzGD60URsnX2591s0s9oD/EVkC4xJnHTBqLXYIm2W9QSBRSjUua52MIsCisdr9+SEBgcedFFEbrasHBZp6KKqt4ltTcKIPDm0YJOZ86lbTZEnk88zVkKCIbjpNOFXnQg/hpm7zEghQfOYq32Lpzd7NRwwEOwginfiA27XZYtqqqGcAACPWmfhuB2Qo5/mN+tROqvE71prC7mAKnGKQWUD2oAnBrTuneDbIUAiOftVY6BGDDcQ54YftVQVVfaDAIGOPOoyo5BxzTW7OvqGO5GzwJyKokNbdlIKkHIalDqwQp5gT1OagyqXiMdfSld4RJyZ5rjXXY7QQPlzSBmxGGCBmiq6kgNuG0zwfI9KKDrcXifORTBmZooq2TP7WVXKhgGAVuRPSp9kgLonC4G6cf6iiip+leL1jNoTn41JBlvjRRVEWrEFxJwTFVdeAdasiZsmfzooo0YzetLugb+B7hooqdViIJKrJn2hRRRSN//9k=","cq3":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAGgAAAwEBAQEAAAAAAAAAAAAAAAMEAgEFBv/EADAQAAICAQMCBAMIAwEAAAAAAAECAxEABBIhMVETIkFhcYGRBRRSobHB0fAyQuFy/8QAGAEAAwEBAAAAAAAAAAAAAAAAAQIDAAT/xAAeEQACAgIDAQEAAAAAAAAAAAAAAQIREiEDMUEyUf/aAAwDAQACEQMRAD8A+W+Yzl85Sux1shT8VGcljjERdRR9icARXQcHNRi6+OZ9M0pofPCYwenT/uWKNKykeCF56luchbPTEZuzagjjFkGJ5prc1cC+MKxkcTG327lU85k9SaAGGwUYYc8Zys3nNvlvCYxhnawzAK44ANMZDNGVB5AfzD5HOCKE6Xesx8UtRjC+nfNrpZSCQykDowqsYmnkUrtmUG/RgD+WJkimLMwxQkL4gJuxRbYR79ORmfuiuSUkVas7WYHj9z1ywxeFpxunpmJO0En8/wDuT6d0lDrI4CgA0zVuPbNmbCzej0MZMolflRakMByOor98o1emj04jeJSjMQVYz7gQflxmkn00CUVF+4v9M4+rRkCIbTs5AH074jlYyjQmdq0bqEQWQSySA+vSs81E32fERa/EeuXSEbZkj3MlEkDtkSRS7RIEDAcmyOnw64YdGn4YCk9CKHU9s6qMUZuKHvj4tOsqEuxDHng8AYmXYjkRkkdOcfK3QjjSsWMM1xV9KwwiHo6UpJPIETxCwPlTjbfpyMqRn2gxxCqHJYkCuK6gdMn8GXSkvAwKuOo5HuDXvnNK5VWvSNO34j5RV3z73nM1e0dSZ3VRSEoQse0XQjHT34/nFabTxPTvIqKfQ4zVTO3m1EiIoB2xRWb+eT6O5ZQRAZVXkjdtxknQLSZ6Kwadd1FTz+LnMSjTNt3TJCfULX1J65HujmmLCKZRfTcNvz4x+nWzeoljiQKeFoMR2FYMWlthyTekN01w6ovHMJ0ClpC44I+PfHTzCcRIVZNyjbSbmYXVD498lKROC2nEnhgDqeR/e5xyowYKiU5G5FA6m/ywGJYlEc80bsI9osLJz09PpnJoF+7SSbUd6FMLF2Tz+malREjd5ot0rtXJ5HuB/OIVPDRXaiAeBeWirIt1onWPbTS2in25wy6LTPrZlEx8JCNwJsD5GjhlCTdHoQzxyxhkYhLoWK57Z2RV2nyqfXqAPrmJNYqs0BTx4wvJXiqzy9WyzSmRZSAarcKPA9uucUeO2drnotMjCdl2pPEBusL0HxxZk0hnAbT7RzZPf4ZM0jRotOW3R0AGqh7/AMYxtRIYgksgYEfEjK4iZFUv2iFAi00S1fFrY+mLl0kzwNqJiqluTuP+WDiOWd3dCIgbEYFEg+39GJllhUy7d452rZsgZowro0p/p6GmiOmULJtdwdqjb5VN9v8AY/pmJ9QIpC5BbUN0F7gPc/D+9881dZMKsgkClYjzDm+Dm0oS7t271Zj6nKLjSdkZTb0bAKyPJMQ99TV0evHbESyb2AZjsHOb1EnPhigF7entk0jMoMe2rNn9soJZqLWaiEERyMt9mIwxQwzWCkW600igcAO9fliHA8aq4scYYZFdHUyn7V8swVeBtUUMxolBmjBAIKnivY4YYV8iP6Gahjvkazfhjm8TEA0chIs0vX5YYY6JCT/llKkiRSDRCkivTDDD4D0l/wBl/wDWE5JmYk3hhjeA9FnphhhihP/Z","xm3":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAGgAAAgMBAQAAAAAAAAAAAAAAAAMCBAUBBv/EACwQAAICAQMDAgUEAwAAAAAAAAECAAMRBBIhEzFRBUEiMmFxkSNCgdEUFaH/xAAYAQEBAQEBAAAAAAAAAAAAAAAAAQIDBP/EAB0RAQEBAAMBAAMAAAAAAAAAAAABEQISITFBUWH/2gAMAwEAAhEDEQA/ALQQjnEmFPiTXkcximejs44UFPiOqoaw8YH3MkMGNVV9mjsnU6rS1pWzHFhx/EpdNu+2XUqDH5o7oLt4mJzxu8dZy0MTg8SPRbnwJasDIcFhn6CR25HzzfasZFbokyY0ylfrHdLI+c/mRNGf3NHamEPRWPEJM6cjnMI3+r7+kUrbxGqgHdTFqmQPj58cx/RCgElpjWsC9OOUKe0WUXZkbs/eLu1iaNEZ0J3ttAEza1F9VAEYMYmHp/VmRxVYyWZOdxOO57R3+7pS7p31PSp7WNgqfxOe63mNC6pCNxBOPYGU3Az8IIH1lnT6qjUEim+uzjkKcyNldYz3H2nTjyc+XHfiuAPfE4zYPw4x9401rjO44+0WyKp9z5mtjMlhfUcdj+YTrqrDIhGxfSV1NLVqwIGR7nEmfUK1rYtYm1RyczxQYnODmTIUKS9u36Yzkzl3abmq9fDIV06sjH9xI4/iYr3222dRr3dvJOcSurKSRwZYpFAYA1liRn5jM2rIGtNfxJknHzGSOrtfT7GcHnIzIDaobG4jvgntJ16YO+XKhDycHn8Rq+/gurV3VWHpWshPBKnGR4mzovXbNOmy7fac9mPOPfmZV9dNRAVicjzFAtyQM8ceY1Pj2A9U07rlb6wuMkE8xWq9RSrS2WKwYqvAPGTPILYcnqJlR4MZq9XZbUEydo4AB4l7VZmerD+saywY6xxn24hM4kAcgg+ISestR9Fcr/p9Rge52Tp9NvbnpO3vnbLQMlmXquxRf06ysKa0cseThDxJ0aRlJLq6E+UxLYnHRLBh1DD6x1NhC6RnZQoYljg/LxC3S2BP00c4GdxI5/qPFVYAAUADmS2rtxjjxHU2PO2NYWJYkn6xujov1TmupSze/OMTZ/x6s5CAEduILTWjFlG1j3IjKmxTPpl5YVDGexd+Of6lHU6a6klGCbs/tYGbbJuGCTj7xL6Sh2LNWCT3JiSrsYaJbztH/RCbQ0lK/KgH2hLhsOkh3hCVkEnPeS9oQgGeJ0E4hCB0ThhCBEkwPaEJRyEIQP/Z","sy4":"data:image/jpeg;base64,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","sh3":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAGgAAAgMBAQAAAAAAAAAAAAAAAAMBAgQFBv/EACwQAAICAQMDAwQBBQEAAAAAAAECAxEABBIhEzFBIlFhBTJxkYEUIzNC8FL/xAAXAQADAQAAAAAAAAAAAAAAAAABAgMA/8QAHREAAgIDAQEBAAAAAAAAAAAAAAECEQMSMSFBMv/aAAwDAQACEQMRAD8A6qyRvexlajRo5as8+toygsQa9rJHt851PpurOo3xuSZF57Vxjwy7EpRo11hWXrINAgHue2WsUrWAGQ7ldRGgA2sCTjgPOazFAuWrLhfjJAxbNRl1JmXb0VYnvwO+c4M0iPPJGhUDYNzkUPP5zo/UZOnpWO4oasNVj8H85wtXqpNSAW2qinaB2GRyMpFFNWC7gR+nYlggfd7YYFRHON0gCMgFpz+8Ml6x6CJ5Wbc4Z/bxjY2ZpQS3RIP3X4zmLqJAotiQvA57Y1ZjItg8/OLWrtAuz1iTKqhZnUSADcB2/jM+ql6hAjbaF53g1R+M5SCbU6cb4gyRjaHD0R7DKJp4drtIhCqO9k8/vHnlb8RTHiTVs6Kay5l6zJvRSDsPf5+O+dDTyo8SbWB4o883nmJ9LHJrUWHckS+QKJ85o08UcU6tLLLEq2ygHhjxmWR2F4VVnqhIUX/UADFHVRb1VwLbttziSa1nvZKSl2B2rErOTJZJ3DnElnXxCaHomCSxEAhlax2zifVm0OljEaxo0vw3IGKf6o2nhZepRK2BXfOIJQSSAb9srGeysRqjZqJAI7WIKWoiifSP+84ZjkkZqs/B54wwUg+iWYXYx8EsKqQysQy1x4OU6JlbedwPkVk/020mmVR35OHUAw61oiUgDKh77qN5U6tyP8rKx5rbeRHCwcFnHHkDzlQI2nDbjvPINeRhUUhkxgnkaQP1pGbnkr+8fHq9Q/pUk1d+gE155OVRo3g6kkjFb7AAG8eFhgKmOWXqGwCFHGK0OmNBWQiFVpz4A55wlsuydKX0iztH7zMU26pXaeQSN5rnv3zVqpW63o1T2wG4XV/9zkXj9GtUZptJqJ2DxwOgb/0e+Z1g1LKJY47FXyO4GapPqGsCCFp2kYHgGszpq9QoI6hUVVXlYppekm0ZpWljQJJSj2I5wx0obUP1JWNng84YQbIv1TvtqBHsMhpuxLc/JzLvZuLr8ZAAsWa+TlLAOlkV3FFu1/jE7xvuh7ZoiSB0bqA7uKOVMKbWrmvOLsMolUeLphWFA+ccZIlKsikPyMQYkEgW+/vjItMJJghcC+2DrpB4rHFAziRm5JN5aUIrlI2pWq7rkjI1Gl6TbNxPGIaJmbhjiO0wpqi32tbe1jIaIh9xPHteUiZ1LKzV6b5GT69tG7ynwmyzyc12HvhiJT/cA/eGAWiF75A+04YYRh4JEBokWousIydvfDDBIfGL1XDL/Oa9IAZlsDzhhmj1Glxm7UAG7HnM+0bxwMMMM/0TjwpqEXpFtou+9Znl8/nDDC+GYgAGUXhhhimP/9k=","bj4":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAGQAAAwEBAQAAAAAAAAAAAAAAAAEDAgUE/8QAMxAAAQQABAQDBwIHAAAAAAAAAQACAxEEEiExE0FRYSJxgRQjMkKhseEkkTNSYnKDwfD/xAAYAQADAQEAAAAAAAAAAAAAAAAAAQIDBP/EACARAAICAQQDAQAAAAAAAAAAAAABAhIRAzFBYRMhUYH/2gAMAwEAAhEDEQA/AOlSVKuR3RLKV3WRx1J0tNjLtlrLolVFFgwZMZG4pLKrtlcRldr3VM0WWq16qbtcFUT2Z5MqKVgGXsSPNFR9T+ydxVIZUwwH5gFbT+Y0jIzm+knMagZEDz8JBHYoVWZdhKQELN6jLUEMN15plnqgvoi3CzoO6M2upWWWaVQjGVksIVM3dBcnZhRE+Glw+ypaE7MVETyp0VolK0WYqGcqMq1aLRljqhBqE7QjLCqOBxZXS22V1jdxGX9rVpPaD8MwB6HQKUYjZmthI1oFoJB87TdlIDc0mQCgCwE+vVYOcsm60449micY1gcZnFvSjX2SjfiA1pkcGm68Qskdllz25SGMlbWthpJ9NVIPxDmkjR1/M0jT/ad5MKRR6nuneS9jnUd7oJh8mUWfF3cptjxErfDbq3JcWD0WBBiydMO4/wCVS5SZSUVwVdxqB4xo99VJ8sjQXNlsVz5ladh52st7Q3mfeWQoOZMZC4GOuQs+ipTlyS4LhGzNOIw50hb9KUnYickjMSb3sKsTHAFh8WvPYdgnwXNIy3XQBV5GR4kxsxM7Izckb65HRCXCPDIOZ19dChK5VEeniYYg5cSNO34WXSQbDFXf9P4XJfmZRYBRG5P2REJH2A26312U/ordHWEkQ2xVen4XmlxNCjNmbsaZZXnmaWkAMZXO3Bed0xAIGXrogLHVwERna9xOVl6aKksLomD38lNaRZA3vfzXNixUrYywPOVxBItaxuOdPC3xDNfiAG6ItfB3ljGRzTlsjQJLBBG2q9EGKZlp01EDSmBccyFz7fufotMeGm7sofRNm9zvMfFIAfaqvYFv4WZJY48n6tzsxrQbd9lxo5cxAGwQJXF1A8+iXsdjrtfh5qvFmz1b9NkLlucQMza08WvNCEwt0Rm14N9R9kQOIY8gkajZCELYkq4nh1Z/4qQAuXTmUIQBv5Geam7+I9CEkDJu3H9qw7khCsDUWhVWaE10QhJgXGrTaEIUoD//2Q==","xa3":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAGgAAAgMBAQAAAAAAAAAAAAAAAAQCAwUBBv/EADEQAAIBAwMCBAQEBwAAAAAAAAECAAMRIQQSMUFREyJhcQUUMoEjM2LwQlKRkrHB0f/EABgBAQEBAQEAAAAAAAAAAAAAAAIBAAME/8QAGxEBAQEBAAMBAAAAAAAAAAAAAAERAgMhMUH/2gAMAwEAAhEDEQA/ANyBIAuTaVVNTTQHzbiDaw5iOq1FSubJupIpvxlv+CIcaXWcImZT1r0m31Nz38pwcj0mhR1NGv8AlVAxte0zOlZArLrThEusWZJWyxorK2WXUwqyyBEZZZWyxSjimEkywlRd8T09A6epW/LqgYdW2m/r3mMfmemqqY/VGNZV1FJ3DUaVdVI89jkkX7xU617E/JUxb9JnJ1FRazoRU1NRuwLR74LQFQVBUquQlgFGMZmcde1ifk6Qt7yyhra1OsxFLcNoUhSVCyM9OCAMcDE4ai3AuPe8QRnaoN7KbEmwPv8A1lm4iwKC9u/rK2G8EXius1dLTU2uwL8BRzeT8VQtmwDjPB/YmXqUq+MRp2qLTtgXH+5kMJ8Qpu67iFUjPp6xryuLqQR3BmLUoalyPEapYG+WAmrojTFNFT6mTcx6k+srJMsJW7tySO0IhZxUBQADbtaQLAHKPb0W8tVmJtgf5kr+YDFiZ550Wl2ANrqw6/TJ0beKt0br/Ce0vqXDkDiFJiKqcciNVxCfyN/aYvU1JV/BDncTjHA9Y+bxDWi2oNl5AzOfVyJ18dNfbgtz9xK3WiyWqC4PUdJxwxU7cNyL5i6u1NmpsoBJ6HmCaG1a2ipHKE4jej2pSupUEY+nJ6xNalRAGA2Dta8e0dZSG3G1zHO7+lOi9ZRUJZ2Y5xc8QkxyVBBtjMJJ5sTS9myzWHtJgYWxGMyhTsJJa495JqucY7iH4qys9mLbgQeLGQp1yLbzm4sR1kKqXQnzEHoRcGVbKjoCot6NidJ16OVsfO0GF1JMz9ZWNWuQp3IcDErp0wwy/n7Wl9EGhUDEkqccW+0l6iXLFNDczBCrFuxFpLV0a6gDaGW+ODb7x5XUHxFRC5xuA6TlVq1SidlJWNjcgce0G+xxnac1VqWJYKOcS6vXphAoa1uonPxUp+I1tuLjm0rqhSbutib36Q33R+JUqgIIC478ZhFySDtVDCa8stbn7zmp+pT13CEJ0IzpeLRpADkgG14QnJIiyqv0qBcngSNzcZhCFnG+k+xl2n/L/faEJYsQ04B+I01I8rU7sOh94a+mny1XyLg4xxkwhFGZeoG3ZbFxc264hCEVF//Z","cd3":"data:image/jpeg;base64,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","nm4":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAFgABAQEAAAAAAAAAAAAAAAAAAAEG/8QAFRABAQAAAAAAAAAAAAAAAAAAAAH/xAAWAQEBAQAAAAAAAAAAAAAAAAAAAQL/xAAWEQEBAQAAAAAAAAAAAAAAAAAAARH/2gAMAwEAAhEDEQA/ANUAigAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAlGLcFAbAAAAAAAAABB/9k=","kansai5":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAGgAAAgMBAQAAAAAAAAAAAAAAAAQBAgMFBv/EADMQAAIBAgQDBgQFBQAAAAAAAAECAwARBBIhMUFRYQUTIjJxgRRSkaEzQpKx4URUwdHx/8QAFwEBAQEBAAAAAAAAAAAAAAAAAQIDAP/EABwRAAIDAQEBAQAAAAAAAAAAAAABAhESMSETMv/aAAwDAQACEQMRAD8A9KQx2FVykcQPes7EjxOP2qCq/MK3oys0JtvIBWMpBH4l+l6gonFqgpHzJ96tJEtmWa3E/WpueJNTkW+lSFF9qu0QZkk/xUWIGgHuaYCE7JVhATvYUaQ0xYA8xVjmPE+2lNCFRuaMsa8qNjQqIyeP+aKYMijb9qK7TOpEkH5V+lVIJYDKBe9Z/GD5SPeuZj8ZImLjdZHCDa66Dnbn71nJ56XGOuHY7scSPpU5U4saRHaUIC5hLci9+7361ZsemRiinNwzWANdoMjtoxwJqC9tQoAHE1xsX2xJEto40eQ6ALc29aUlx88ozYqaNYhuACuvpUuaKwzrz9qWBEA7xvmt4f5pU9pY0jQKKSGKww/qIv1Cj4vDf3EX6hWTk2WopDXxeNY6yKK2wuPGbusQQG/K/A+vKkTiIhHnVs4OwQXvSonmZi7xZV4I3L151ylJC4pnpBLGzZVa56UVwcN35Yhp1sdQCMuXpein7NdD5IpPiXLeKQC4tlA1Na9mxSYnxzSEAHlfMOR6UtlijS5IY8SdfbSrQ9pjDpkMRsosrLy9Kzuzeaa4N4zAYdXBWeSIquUBNgKX0iXwzO53GfeqyTiUDI5zMLi2tVjw+WR5JWVm3HT0ot0CSfCsohkbNiIJO8N/EpA00rI9nwTKpSVo7/lk1PrpTUhNgCFJcaZgT9qTaRoMQEyBUOgstMWElXtkL2VFcE4tLaW13rRuzYSbCdB4txINqqQ5QEd4D6MOXI1DtIFe7kAG4uWFvtVEEvBhoj3cuIK2FyA19OQtvS4wuBaRAMUcrHbIbmokwzTY1rWN9Ta9OJhjC8Tl2KA2Y5zvqbda5ujqsrBHJC7IqtKinw6EEjmDRXQCuVuoGVtRvRWOrN1Hw5pYN4I5Cq5R5hw9+dUlCC4Ml+qrw9a2njklxcQXykKTwsKiVHhYm5kDHwhR5elUmZ6tlcEGVZHRXYcC1OqxVSXY5zvbgKqFzoiqQCNdzp1+tS0Fx4nJv5iLCi7BOmYStna4NzbQEWAtxpUxSTuRZ9Dx486dTBxk6gs3O+3Smo4Qqksdzzq7oOsUiwReONRGL33KnpyrU4IhHOYg34MR/wApsl0YZHYryYa/xVmJYFhcMp19anQc8FY8GfiH11PlN6bykMsaWBvrf/dBNxmIIJGoGmtZm5sbBr6ajWspStlgxLWDXFwdaKLN4swXNawNFTY0IwEtiosxvdNb+lVi1hJ4jPY0UVZmNRAaabLb7VC/he1FFaIqXSuH8q9Rr10rebyAcMt6KKJjHpbBEt3ebXxHepuchNzcytc+9FFQy3+zVNd9dKmIDvH0FFFQ+kPooxPdE8g37miiihgz/9k=","sz3":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAGgAAAgMBAQAAAAAAAAAAAAAAAAMCBAUBBv/EAC8QAAICAQMCBQMDBAMAAAAAAAECAxEABCExEkEFEyJRYSMygRRSkSQzQnFioeH/xAAYAQADAQEAAAAAAAAAAAAAAAABAgMABP/EAB0RAQEAAwADAQEAAAAAAAAAAAABAhEhAxIxQRP/2gAMAwEAAhEDEQA/AF6d1vpZSPY8C/nFSxPDIhoqx4vk74oalTNZYgH9235FZ13EkwkaQuLuzueclIa1oRapZIpW1aUrL6ekbtuef4xmkOm6xNGsq7AGjYa/fO6tAYEcsinmlqt//cVpNSYiWAT1c/Hx/q7ylzxwJq1rEYDK8Wqv+5VHcEZZoEWNxlcfJjnOEuNn0Z3fCsMdnC3ucrT62OFukHqbg12yOs1MSrYJLDbbtmZLIjsxJHF3VZDyeX15FcMN9rZ02oSddj6u4wzO0biOWM8dQqx3ww+PyzKbrZYWXjBRB2NrVgk3XbOx+YtigKHHvk4+pWsSlgdqOQd/qWRRyFsommR/LDA2PY7YCRx0hkNH5yUbCj1AN3rjHwyoqhWQ9PwMGpWLTWxh1WUyADaunqvNvT6+OOP63oQLak8k+1ZnK+nZlI6lIO7ViJk1EsZXqSS2H2tRr84ZPXLcazjdTxPRsyjrYdQvdePjJyauExgxyC2HpsZ5xI5YVPWGAf7esc4t5yu7AqeN8p/ShMYutKGlKimbgb7HFx8kvGoYnkZQSQM1g89scnUsnrayRsbOQu1JV1JnBIEe3aj2wxUcwVSFbgbmrwwc/TbZsMxlH3qPirrGSKwjZieqiKrNGPwKSmC6tI1a9gNsavhDGNfq+Zx9q7n5ylneJaZIIPT1EAHgg5HUROWDLKQnS3B7gWM19T4MY5bVjIvWLqloe+X4fBNOApkl9PJW9/5zTlbTykKalJh53nBf9kXttlyKJzYMjmm/cc9SPC/C1O4dj8uTkho/C0A/prHzeG02nk5pCHK+YduL7YtmkmTp2Nb43V6Vf1EgU3TEX75X8hqpSFuwcE0VNWhjJVT1PfIG2WFeY3YAANDYn/vK8EXlsaRSPYijxlkauZSUIPSR7VgsGBtPKgBKnfkDthlhNSCn3VXPbDE2OiZtakrqxWUsP8qAzv64jZeqt+ZKr8DEFdN1W8hodgbyUWqiioKnXvd1lA2uQSvKVDRqx25UnNIfqm49I+FAzMPjTcRwRqO175BvFNXJt5vSOfSKxKbbaGmnIuSYgfLHIMujjP1tUpI7DfMB9RI5tmZj/wAmvBJVB9a2PjtmD2MenmZxt6iRkXjsXvvlqFYHUdINj3ybxqq2DsO2PMaTbPII3BN4xCCGLc50qOo1v7Yscntiidfp7Vhik7hqrDN67bqgO+TT7ThhhrJDJDDDEZIZb06rXA/jDDDBWRg3BwwzonxP9Uzz+Mge2GGc9UiJ7YYYYYz/2Q==","nj3":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAGgAAAgMBAQAAAAAAAAAAAAAAAAMCBAUBBv/EADIQAAIBAwIEBAMHBQAAAAAAAAECEQADIQQSEzFBUQUiYZFxgaEUMkJSYrHxBjPB0eH/xAAYAQEBAQEBAAAAAAAAAAAAAAABAgAEA//EAB4RAQACAwACAwAAAAAAAAAAAAABEQISIRNRIjFB/9oADAMBAAIRAxEAPwCxFEVKuV3uJyKibiByhMGJzXL95NOge4YBMTWdfurqLm5JA9aJypWONtPen5196N6fnX3rJ2nuPejae496ndfjhqtdtqpJYY7VMZE1jgENP+av2dbZbZblgxwJEUxlacsK+lmKIqJvWgJN1BP6hSzrNOFniqemKraEVJ0UVUHiWnzO8fLnRRvj7OuXoy3rtO9svxAI6HnSn8TtDCIzepxWLany218ztyg8/nyqajzhWBmYrl82VPbxw3r9uzq9I1p7zIWGSLDMBmccqyrthbd1kkPH4trD6EV64WVFvHaOdYHiGm1J110oG2sRBAmcCo32n5PWMajjNNkdh7Gg2lJwkfFTVprGptqGbcFmJIrgtX2YKrEseQApuGqVfhqByHsafp/DrV8i6+qW2YMItpm9zFSOl1XOHx+mt7wey1rQWg+HAaenU1MzH4a9vN6rTjT3AqXFcdCFIPzBqq3TOPStr+prY4thh1BGPlWRbt3LhItW90cwIH70WmYLJKkAQR8aKXdIL5ECYxk0UdYlGIh1UEjM7zM1paTS3biC4QYIDieYMjHPMjrSNOdRplbTCwQSZY7Zk1qiE0itcZdwWWtgbTg8sdKVNi3rjckqkrmCR7UjVOL+oFvhI10pzcmBHpSdMRcUBWyzQOkCe1csObvil/7vkUwameE+24GjYLpwt4iQh8ygx0qOg4yX3GpUXEmUbhgEHHb1mureAubC0keUKBy9ac10rG1ZJMHFJoi4FbV7RpN1kn+8z5n+YqzpdenDIZSCpjn6xn6e9KQl7IwFYqDHY1R1D8DWKGUNbvST6H+aBJnjavq1tfZl3bCZBxAI+tV/DLTaa+7X7W48P7uDJntWkFhQABEYjt0qItHcDA9e9LU8neJa/c27QGJMdKKueIeEXrbF0MqSdvqT0/7RSmmsEjAiT610yC3IDbhisirPCtj8I7dRUHt2w+8IAYiO/vUrpAuLaFrU7VB8yiVHWajoV3m9qWYMSpG6Z3ev1pgS1wWtAKltuajA+lR0OktaRXG9roc5U8o7VV3FCurCcIneWRe7HtTBLRtJuT1B6d89KWUt/gVEUCABmKkCEWA3SOVSU2Vkjcsbvu5GRVDV6b7UpKbg9olgSOY6/WrBVTvw3nOckfxTeI7kBhPTJ6VuNRGlubtOpkSAPbl/r6U3ilIkEj0E10WoiFA+GK7tYRgY5VoYtit+2yYIMgg9qKLdkWt2xQN7bmgczRSOq0naM9KZbzYSewooqVIXxFlyOe2qdu44dodvf0oopC1Ydiolic9TT7RJQznzH9qKKxJVjtOTyFMsElATRRWYxefzpsZNFFZnU6fCiiisH//Z","qd3":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAGQAAAwEBAQAAAAAAAAAAAAAAAAIDAQQF/8QALhAAAgECBAQEBQUAAAAAAAAAAAERAiEDEjFBBBNRYRRScYEiMkKR8QViocHR/8QAFwEBAQEBAAAAAAAAAAAAAAAAAAECA//EABoRAQEBAQADAAAAAAAAAAAAAAARARIhMUH/2gAMAwEAAhEDEQA/APcpQ6EQ0nWucOhpJpmySiiNknJuYiqpjJkcxubuBdBJHOzc4FKtAJusAOJVDZjg8Zdxh29THxlX00Jerk3zrPWPRzG5l1PIx/1GvASdVKqdWlrF8Dj6MXDVXLrpe61JueYvyvQzG5jkp4nDcXa9UU5lPmX3JCujMgzI5+bTMSbzKepFdGYMxDmU+Y1V0+ZAXzASz0x8yAI8hS90Dpqd1U6Y6AtdvsMura+x1c3Fi8HiY9SqxKqc+WJpcSNgcNxOAm8OrCbiIf8Ap2QOkZjfW+nNR46brCS6zJShcVfPyk9oZVJew0LqiJXPUuNiaK8CZ0Y1Pjd+T7VF0l1NhN7gTT4iV8OFEebQVeLhfDhS3eHojoVKCKbXYEKvGw4WHKdr/Mv6A6UlMAB51Nt3I09JI0uVap69R/c2wou0x3GTh7MnddY7m5nETaNmRVZvogVTdrE1VLidugyajWe0oiqJ32g1PZ3ZNP8AdPuMm4m6IHT6pG5k/wAk0nHzO+8G97AUVdtP5AlU7TS0nAAcK29GPQk1DQAbZUaSdlFwba0YARTwoN0SACAeqB6oAIHaSulDNX1eoAFTx20lDj8AAFwf/9k=","wh3":"data:image/jpeg;base64,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","cs3":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAGgAAAgMBAQAAAAAAAAAAAAAAAAUCAwQBBv/EADgQAAEEAQIDBQQIBgMAAAAAAAEAAgMRIQQSBTFBEyJRYYEUI5GxJTIzQnFywdEVNFKSoeFT8PH/xAAWAQEBAQAAAAAAAAAAAAAAAAAAAQL/xAAZEQEAAwEBAAAAAAAAAAAAAAAAARExIQL/2gAMAwEAAhEDEQA/APPk5UXnulde4Puhm1U4I1MtDmg69rSLBLR8QrXFx01Bpc59Atr6vw/VUzOgkcHEyA0AcDwU3wDTPAMkrS5t2zqoDRueHOa5zqYL29OeVXK0jVBou8cuinDA2XtHRPkbsFnkDSrqNxsulz1rJVRo1ldmA0c3fHxRE2oW7aLhd0Oqi1jpIZHiaXYPrAnmq9sbg1u+XGACBhRXdXuEuR3do2nmCK5od9YX/SPkuzRCEiKSSShkACwFXKQZLF1QGRXRWDE0KDKvJQrS2qJ2iwt44aS0O7cZAOW/7S+T6vom88e57C6SmhgxuHl/6jDBqojpphG52+23dUiot32h8j6fvhT4rjWts3TBn4qm9L/VN06BRYWBsW4e9oGr+GfghrYrbclXV+V8/goXpKHfm6XgIHsuO/N/aEVIBlH3leV88/8ASuuEee/fP/SgPZMXLKOX3QitKT9rKOX3AgJXAS7WkOBIG4rY7hsgdXbs/tP7pe/sw5vZuLhY5iiMpxqY3e1hweACQaJVZLJ2OhndEXBxaRkIUuI44jJ6fJCDPLkeicaiFjpWuc8Nc5oDRSTyD/ATvVRN3tk7RrH8m341zQLeL/zwroxv6q/WwxQyNEYkLXN6uvN56eap4r/PgA33G5TjVRGWGMxHa5vMFl8yFJ06ywcNhl08crpntMlmhmheLsKyTg3Z7SHym+lDC0AvDY99ucG7cDw5futEssbtKKLmydWhuPiodKvYoGtB7WTd03NFfJY9OGyysjJ27iBuIGKvyTbe92Nm3N4AtZItPKyUPO2g4nAyLv8AdResPFIWwaljYy8sLQQXAWRfkmOrZetjcXM6d3cA4/FYeLuJmZYIptZPPKaTwg6qKbc0UBuBNYuvXK3CFPEh9ISfg35IUuKiuIv/ACt+SEGeQUdoHMDKdT6OZ+q7djm02iG3RNdL6JO+rN8qWmDQdrofaO0l3G9rQfNJmirR4tniR/K1aHh18zX4pa0d4Ve8HO49U13PLbOD1wgqLSeZPnld7xOXEevJda+V0j2g4FeCrvW7iP8APdUXie3FnPquHpRx5KF64Cqz491WvdNGGW4m3AEikOMevAc5ufunmnEulGpcJoyHgta3B8DlLdcLMZfyo48VzQ6VmpfkyNYcAh/VW6SrT4u36QfWfdgoVGpj9mnlhDiSPE3ikJork5+gTfSk/wAHZ+T9ShCz7a8k7Pth+JTIuO3meXihC0yz6gkGajWW8vwVjctBPPaEIUEgBtGPBZmOcXmyT7wcz5lCEEuIHLfVX8JH2R6l2T6oQp6xfOq+J54hJf8Ax/ohCFYwnX//2Q==","gz5":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAGgAAAwEBAQEAAAAAAAAAAAAAAAIDBAEFBv/EAC0QAAIBAwMBBwQCAwAAAAAAAAECEQADIQQSMSITQVFhcYGRBRQyoULBBnLw/8QAFwEBAQEBAAAAAAAAAAAAAAAAAQACA//EABsRAQEBAQADAQAAAAAAAAAAAAABERITMUEh/9oADAMBAAIRAxEAPwD3lmaYT4Vhtawvjg+Nard5iuHmK1zXPqNC7gOKeSEkRNZvuGxkH2phqDH4ijK11DhicRNDgs0xSfcMeAvxQ191zAPtVlXUVRIywk11lWYisx1LnM1Nr9w8t8U80dRrRAAfE0jAnEVkNyMs37qNy+AcT7U8UdtjJzvaBRXl3tU/AcgUU+OrtLtRbXcTGY8auLrczFeEzs2QST4d9Ol65nY0RkmaemeHqPdYNhiCKomquL5j1rzhrrg/JUKjvmqprEZetTbJ4B49qepWebG8fUFByCPStFvWW7qDMHzryH2lukifAGuC6oIDKfY0WxTXsPcCCTxUH1YmFFeab5TO5vnFOmoR43EA+ValgsrV2gJknNKziJzUzMSoY+EUu5f5GDyRWtikFzqGKKyanWBUAtETOTRWe43zSHtHKhjJjpECYoKDftwrd6sog+9KLltbRtu8qW5UkmnVbZ6ZZljHTHxXHddUioEMyRB4L4P6rhDLEd/dyI8q0IjXLqIq7wTEOACPXMim7PrCXNyR/IYx6cmrVjEYMFYB/wBp/uqDUOVKmGcnDYxVnFmDbZgbkyWEAemYzSdirFmUbYyYMfqpYpp1t3ujtAbiiWAmD+qLmnUGN0jwAqNvYhN4XnURG8W9w9JqvaXFXqIuk8eHyKzd38Z5rpLC3KlraASWgyfSoXAAqtkH5n37q7vtlpvC4G7gv/ZoF0nFoK8HkiIrWnCHYEDMFuGY2htpHt3iius6IAbkqxMkT0k0VFBE6wTbZlHnFW7V1cvaNtDtjaRII85p7d+bPZ27Ckjgkkg10DV4bs9pEzgADzmpKWHICtatC4QM73AA8TzUrpvMwt3mUHAYKQoUegMGq/bhraE6hUYCSojb81O7dRCqsmmG3EKh3MPM+NBLZssDuWwzICeFkjzgiP3XGYAJctB0GeqIB+MUn3Fom2gtNAP8nJn24pr15izIz7lA4VQBmjUcjUkjsWKvtggAZHJ45pn1h3bfz2cljAOI7hWT7ggCIYDlYxHl4VRQhUu9u2lskCSxP95NWozXrjLJDPuP5EYnyqg2rbUm4iPyU5b0qJa7b1HaWWG3Ik/iBWv6TpTdv77R7R4O47JVPnk+VGhBNQuXt2lZgZG4ce47qK1NoL2lV7du4UVlJLvaZY8iRIoq3CwXMKsY6xWtCRdKgwu447uKKK0mbUMwIIYyJIz31C0S2qYsZx30UVJu1PTcYLgSMD0rJzqkB4JIoorE9hp+mokk7ROcxU9YTtuicBhAooovsfSfUCVZ0BIQRCjgV9R9JAX6RptoAmJj1oop+NM/+QEro1AJANwAx30UUVmiv//Z","bn4":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAGgAAAgMBAQAAAAAAAAAAAAAAAAECAwQFBv/EAC4QAAICAQQAAwcDBQAAAAAAAAABAhEDBBIhMSJBUQUTFGFxscGRodEzQnKB8P/EABcBAQEBAQAAAAAAAAAAAAAAAAABAgP/xAAZEQEBAQEBAQAAAAAAAAAAAAAAARESIQL/2gAMAwEAAhEDEQA/AO4MVhZvWDAVgmNEhkbJWNDALAokgEhomhgAAZbFZVHLGV07FLJGPckv9mZdbsq5MdlKfgebe9tdJcBHLFw3pqrqy6mL0ySZW2vdxkn338xKRNMXpjTKJZFGLbdUrZl0ev8AiMzi1UXxH1GmOlY7K9wbii2wK9wAxwNLrU8G3Y/eeVLh9miGKWptYoVlVyl4r/Y5EPaKh7PelhGPKfj8+Wv4K9Nm1GLa8c58O2uUn/1HKeN7vj0EZOOkVNyah44qSS/VkKez4bj+2Tfmk7a+xz8muy5YPG8MluVNpeQoarKsyyVuW1R6rhKl+RaskdLJJTxLFuVw5fJlisuaTS3yim+OWjJKOoyZHswum7arv+OjZp8mtwrw4tvd736k0yJ41eDjumVaSGbTzi3jdt32hY8GeMf6+FRqqchvA1FxjODVUlFOQ6LNbJa5LqMn/iSWt3RuFr6nOjpoxrdJ/VJL8jWnwLmOXK5rntK/uan0zY3PVZfX9gM2GU0n71Ju+0B01gpz0HTyStLl70r/AEsqWo0yk1jwzml53KS/Bk9+1eyGOH0gn9webJPiWSTXpZwx16jfLUPitMoqu50vu2QWsnGknGPN+Hn7JGKl8h3yXlOmuWrco+NOa9Loj8Qne3HFcdvlmcSZeYnVXxzzSVS215JUHvJN8ybXzZSmvUafJZGbattEoyoqsaZpFyn8wK9wAY10SiAGRJgAFB5AuwAAXYLsAAmJdgBRJdgAAf/Z","yy3":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAGgAAAgMBAQAAAAAAAAAAAAAAAAQCAwUBBv/EADIQAAIBAwMDAgMHBAMAAAAAAAECEQADIQQSMRNBUSJhMnHRBRQjgaGxwUJSkfA0cuH/xAAXAQEBAQEAAAAAAAAAAAAAAAABAgAD/8QAHBEBAQEAAwEBAQAAAAAAAAAAAAERITFBEgJR/9oADAMBAAIRAxEAPwDQ1i27gKvcPwycgkAGsrWaPThUZrpdmMCBHahLDMpRrzMD3mJ7VYuigqVuBj7xj61EvPCrOGeyPMA7tvGK6lq+JCDgf7mtA6e5ZXdsQAtEg+atWw7MGuv6P7fcV1jnkZg0+9wttWYHPpBJB/inLP2XqroB2rZUGF6lTGma0xazqGD574/OtF/tBRpkOpbYx5RDJn6UXhozyLdu6OpZD7O4eBxTC62zesCVFtCRu7nbn94ri/cNQ7bzdUxgRz9a4NLp7VkvpiQGhiPz8djxRpyL7ljTMVHqmJID9uKlbXbZW2CuCTkzjxNLlepdDMQHHBAzUvWoPrkz/bVz8ptL3Lj27jbjHf0nAoq90t7Q95S2PlRTrYWUWw43etZxBq+5asNaJtH1xIVsD3pO1uW3u2kkT6RzXdLfu9PfdCCTIAU8Vx6XLfUrZIuszowAHpnzU5e4A2xwPJFVrqFWNyAgdycmo6tn6a7QEB7dyO59quCq72qZb46aSq4fdiflUX0l/UHq9TLZ28VC3c6ttAVADHIIzit7QMupV7LHESuB6fb9qmjjpmW9I/S3PvnkhliP1rhYuVxIUzzNaMQsGYBggHI+X0pPUaXYxe0p3gTCjDjz7GpvBn8QVmYyrhT4Mmpzdb4WV1GSRVVtuhcZtzLbM7yDlRPap7puekhlOQRiZ81X3W+Vq2SwV2hFnJJzRUg21fxGMDy2P1oq+xkJveEibUk8FTg1y4rL8SOp9xxSllbnQVQFU/0EzUepqJXa7AjDR5rnp06pCug3IHPE81G5cVy4yxiJzBpdbJ3hiYIysePnTKW9rgsTODU39N8+2qtMgtuYj2kcU9p7ht3BctmGGaoKgNuI7/xVluA8EEzgR5rbWya0dU63FS8ojfgrPepSrIjKQrIJBHEUojeghiIBkTUrJR7xLkx/SJx/7T4rty9ZUyyoCWMmTAP1+VRs2bUMmw2yT8BPPvinpAkggyZzS9y0y2QuSAIkQTH8062KruiVkK7GI/7/AFFFR9YYg2wQBIJkSP8ANFVEkLd3dbzzJIP+frUWcHNzjzSGmvJ00LEFgNsVbe1ds2iiltxBAJ71y+f4LPFybLiK9piVHaeaZ6kvLiGbsOP9+tZejv27am0GIzIJGK0Aykqd4OOCeKbPDmrtRcsobdtXZ2c8gcVzcyFDIJGJJgzSGn1a3ftFwpO3bCA+aae5DB4BjIPcU9RjmpdC34RgfpVHUYct+filz9oWWfazEH3XirVdXUMhBB88GqnR7NW7qnLakqfDY/ih77KPwr5n2yP2pYkKeAuOAaS0uquvq7hfcFOACeI4pyC8NYaz0jAR+0jE+R4opdblpYJyflNFTw2x52yT5PBqR5Hyooqyrs/E3yppSQQQYNFFTQin/IY9+a05I257A0UVmpS4qgKQoBk5j3q3SZ0snncc0UVvBDKAdFj86TgffbWOw/aiiszXdVCLCj4fFFFFck1//9k=","njg8":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAGQAAAgMBAAAAAAAAAAAAAAAAAgQAAQMF/8QALxAAAgIBBAEDAwIFBQAAAAAAAQIAAxEEEiExQSJRYRMU8HGRMlKxweEFFSPR8f/EABgBAQEBAQEAAAAAAAAAAAAAAAEAAgQD/8QAHBEBAQEBAQEAAwAAAAAAAAAAAAEREiETAjFB/9oADAMBAAIRAxEAPwDr7ZW2WWAOD3L59p79uXigKytsJnA7/PzMreI9jhW2VtlPfWhAZgD7QV1CW1F6mDqDyRLuL50RWVthBg1Au5CkZ5GJg2qUbiuGAz0eeIfSH51rtlbZbuEL7iAFxz+uYBuX6Qs3AIeiT3LtcUW2SY/d1FN6nK/zAcSS7i4NFGAKqjMD/KpMC0lXCgAM49Oe+PHyYV97ruwmQM4546H/AJF31tIt5KeluzyfP+Jw7XaF2UqCa2z2PT3+GWGKoCK3BcdbTwfnAmH+67BtrQtyceB3N0/1Amg2CvdaO0yRxn3xHasJa3VWUON+lXax4Y/PjP8Aab6dU1mh3smzaSAB7Dr85i+pt1Nln/FtAK+SODMCNSU2NY4BIHJx/Wa9Hjp3VaNlcKDWVyM/UPPHzOforGGhtP10pdXVgXPge37xO+h0bItBY8svZBizi3k+rI8Y4j+Muei2fx1/uksUtqtbYwrPpFa98fPUQNVl9m7To7AHpmHUVrDkk2biMZHMZVE+1stNtm5WAVAoOR5J9hGBr9xr1wFRwgBypGV59xJOhq9c5qVTXXtUYA29CSGrILUA6lxudUA6VXLZ/rMvpaYpuXeWB74UH9zzF/qWlcVvhQTghYBpvsCWuXdWHAb294eL0ytY3cV59t1nI/aErM+1d9dfhfSP7zKvT10oRaAWPZzxn4hNqaacnG7IwSOc/rNSqgufV6d8sTjHDE8DPxFPurEGAoyRkDA/DGDqabrWsNTFgDuPfEw4tLPTU2wgZGOI7AC3VNaoU1KhPe3zAN2cqDjByJncrUsMg4z/ABHv/MvYG7bB8YELIUL4AHZ/SaVWlAwU43DBPxAY1lwv1cYH8QHBmj6djQHB9DecYh4sqrLXJPqGDyBJFmOwYODx4Mk1BrvJcpZlrcZPg+3x7TQgDvo+PaKaKn6dLsyYubgWsc4HwI3kDx+8zGit9NhfIDWKfAOMStNpAljtYowwxtJziNFj14gKzHORkj26MsTNNJRUWGWIbnGfzMNKaqzla1B/SVY5UZ7X47mQsCjKepPI9oyLW1gDjDYIPg8xS7RI4A3vwMLz1GkcOO4LZztBJ/SWDSybqCPqqMAbQ3cYD7a0CgKh5XB4EELZ0Qcno54hqjH0FRgeRxCw6yfS1WcMoz7qMSTZEILDCgfAxJENfBlJ0JJJT9GhvJ29+ZiCfuCJJIwKs5GPmLji0Y4kkmoKlZIsUg85jTki5cSSTNUamV/3JJAqJORzJJJBP//Z","jz4":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAGgAAAwEBAQEAAAAAAAAAAAAAAAMEAgEFBv/EAC8QAAICAQIFBAAFBAMAAAAAAAECABEDEiEEEzFBUSIyYXEFFIGRwSNyodE0sfH/xAAYAQADAQEAAAAAAAAAAAAAAAAAAQIDBP/EAB4RAAICAwADAQAAAAAAAAAAAAABAhESITEDE0FR/9oADAMBAAIRAxEAPwDxhjW617HcVDHzEzAIQK9p1VRjUxY81gvR67j9ol7xkhrsGvmc6dM0aPr04/h2xYy7UzLZANkH9JVWpQyHYi58WMjAozOdQHbtPYxfifGJhUlVype7Mbapp7K6LFvh6nEBx7F6dhItJZjqj047FxD8kMyORYDir+poYSDOuEk1o55ppk+geJ0Y5SMR8TQxGXaJpkxVceNsj7Koszy+N4k8UhDAJjRvSNJtiY78X4wtkbhcOkqnvPz4nk5+J6KGIobjtc5PLNydI3hCtscHXDfKQY29tnr/AOwkDlwVLKwvtRhMaNLH4spJBBUV0MqbKMtsUFnr4uS48fKc6ALGxDCdUFm9AYsGF+I3FDGZ8LJpO5V/ijKMHEOihGtlOzKfEweI1YWTGFJB3PShKML/ANAEqpvYnzM5bGl+C85Rs68nJZXeqqv1lmP8ZzLiUPjR26ayTvIXx8viwcdgEWD1v4msTOraRtZNauxgnKHAaUulL/jWfIxVFGPwF3N/MDxnH4Crc0Nq2GvpvI+K4lkZ0CBFr3aanVyPlx2AwWvS5FCVnN7EoxKV4DhnfmZMrNkPUodifMVxvD8JhZWTADQra+sFGLHjI5prvUj55bIdNtR79KkpNvo7RUvGkkUKHzv+0IhiHopQoV9wl0hBkx40JYMzmjsNv3uBzZiihFZRXqoD9N6koykgbA1tsI9MrqRWEN02JoR0/pDmaVXbVRbexsN/oyrHiyHEAQFA6fXYRL5nClmwaR4DCcXjGo+ghQegHb43hRGb+GsyPzQ9AgCh6ukxryarYHvR1XD8xjdlPLIK9PTNYs+Ct1vfq3mXGNkOckTuvMyMwUspq6MayMVAPqA9pHX94zL+Vyg0uk9yooxePMuNTjd2avO0pwGvI2JfhmbdQzb7+reKOtV06WWutiU1ZJUsa6/EU4KmugkJF5GceUnJuQfG1VCZKkGgCRCGI80WJpHQAD6mrUXYHzJ9dnaaXc3/AIlUczHagy1tXiKCqSRt5/1B/ZtY/mCN/qAk6O8wINJ9N9CD/MUCgORdZNnYj/Ijsjqq7jV8SdVC5AdqLUfiVYIGL7lGPS+u8SzMGG/TtKGWtZ7HsPImMyczIpOx81HZSdGW1g8xTTHqQepmTxOSwS1/NTq3j2YCwbPzNcRjBQZcdFe4HaKi7M/mi3UgwiCO/aEKDRWvumx5hCSZsy/uH1NE7D+7+YQjJM5Pcf7oZfaftf8AuEIFI2/R/uYX3CEIxIxn/wCTj+jFYybq9qhCMtcOHvCEIFH/2Q==","tl3":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAGgAAAgMBAQAAAAAAAAAAAAAAAAMCBAUBBv/EADcQAAEDAwIFAQQGCwAAAAAAAAEAAgMEESESMQUTQVFxYRQigZEVMlKxwdEWIyQzQmJygqLh8P/EABkBAAMBAQEAAAAAAAAAAAAAAAABAgMEBf/EAB4RAQADAAIDAQEAAAAAAAAAAAABAhEDExIhUQQx/9oADAMBAAIRAxEAPwBAbcrvLPlN0oAI9F7Dj0nSjQn6QdwjQTsEDSNK7pT+U/7JRoO1rIGkgW8rv1htlN5R7KUcbdXv7IGkgP6A5UTG4G2k3Wox8TQAAFJ7oy3J+Sz85+KxkFlsFCtSxC923shaROpOLGuOCAoPj0N1EgDv0S681LKVxpGB8t9tyB6Lyk8tTO48+R7iN9R2XLfl8PTStPJ6OTiFLEcygns1KPGaVuwv8Vgx0krwS1jnW3IGysfRNVqDTC4OIJANsgb/AHrCf0WlpHFDU+n4hjR/kfyXPp2I5LQfj/pZreD1jgS2LY2ORhMHCKn2bncr3LFxyMAKO631XXC+ONUxNy0j+5OHF6R+C/T8liu4fMHlpicCGaz2t3UZKKRltcbm3OLjdPvuXVV6F9bSNi5rZw63QDKrTcYawDRCX3GTtZYDoCCbFcaXg2c73drlOee8l1w3BxxuqxiNrYzlCxywdTc22shR33+jrq031lQ0NDnSj0JsrtNQxgczSHyOyXOzul1Uss2gupJCW/aF7KcfFnQsDDRPv8lja0y1rkLFRI2mB1l1z0SGcRjcTcYOM9EmvnE8Yk9nla/tghUoHDnNY+MtBOXEbKcPXo4mMkjuGklxWlwpo1vaRs3YrOgqKZkbQZA47ABW46qSlL3NpgQbBpc8DV3RXdOVzWw1Og1EX1rcuwv4VXiga2oYALe7fAWcZJv0iNWB+z8rTvgFW56r2giSRhY4XADPeFlVo9FCnU0cE4/WxZ6OAsQvPT00dLVWnLnRB1xjcL0zpiQbNkNv5VjcQa+WVr2QyAAZJFt1NZmP6c4oSuie8cuB4BNhYbfFCuQuq6YgRw6sbkXCFWwhqBrCMtafBspGJlrBje+SVQbUtkNmuPgtITg84DhYD1SiYUst5XSEX8XXBLGDazO1rZVWbVLAWRzaHHYt6JDI6uMWAhNutyAfxTNrCVvQW8LmsatrnpZZ9GKhj3Gd7HBwsNHRWwd9sbXTI/mA2wQT6rpI9b+UgSOBNx+AUw4EC2Db/soCYIOx6d0EfH0SwRuRe/dDjaw2BuQe6Rp6j6/NCTzC45D/ACOiEwpDp5TP4R8UIWQKlwTbGE+50DJQhaQDgMjyou+sP6UITJMfvB6tXATzBnqhCA7C0c+1hg/moDMjQc56oQg3HdfJ+5CEID//2Q==","ts3":"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABUOEBIQDRUSERIYFhUZHzQiHx0dH0AuMCY0TENQT0tDSUhUXnlmVFlyWkhJaY9qcnyAh4iHUWWUn5ODnXmEh4L/2wBDARYYGB8cHz4iIj6CVklWgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoL/wAARCABCAFgDASIAAhEBAxEB/8QAGwAAAgMBAQEAAAAAAAAAAAAAAwQAAgUBBgf/xAAvEAACAQQBAgUDAwQDAAAAAAABAhEAAxIhBDFBBSJRYXETMoGRwdEVoeHwM0Lx/8QAGAEAAwEBAAAAAAAAAAAAAAAAAAECAwT/xAAcEQEBAQEAAwEBAAAAAAAAAAAAARECAyExQVH/2gAMAwEAAhEDEQA/APIbIkmYru4mRVZ1XUid9KAb4vPawAMFaD171p2+ZbuwFYa6g9KxPKuQxBPY1YsW0oCz6VUuM+uJWrymKXFKmJUMCuv0Nb3hPj1t0FnmsEuDo5EBh/NeRt8hvsckqBiBRTuRWks6iLMfReoBG5FcrH4fjtj+no92TdQhGQESe2Q9qd4niPH5dvMOtsyQVdhPzSBi46WkZ7jBVXZJ7Vm3vFLV4tY4+bE6LxAjvFZfiXNuc7kFEDfSBIVJ0fc0Gzft8W6iOpZrneft3Ap1P1zm3MuUtu2MQraIMzUq7LhyGIIyECSYxn1qUr1geXrtdwYCSpinPDrS3vqIVTQmWrJ0X0SA3vQp2w9i3aOVssx0GOh8UR+EttlUlCH+1hOvmmrlqxcZVtouCdRFCb1GW03LgYQdSaP58ZYdaYFhBk+lBMQDr4FVbMIBtU7xsRVy4m3VUuYEGP8ANNsEdARpfSl71tCoNpSuuhPWiW7ltbYymBFXLLEWab4yBUzudApMCg3cuR4hvaBgxYDtFUucotaIUEL7Ue0/07CIMisZSeo9Ki2wp6i1xvq3GMAqAGxB1v8AepQWckSxkDrFSlgYWTRE69KgkHrRrTWwMHWQSD+lMPwmuo1xcVIP2+o9RUbjo1S3ce+BbnInQk02thuLGYcOT2IIA/HWkbatbnyggiJ6EfmjWuS9pIMAEaJHT49KdRZ/Dd9sF+mpKgLA/n3qo5GTNBOI2N0rxuTD+dmIn/TTdtM0yNzMTuR9w9Pai0sAKvfbyKMR+KqGYArAkaq11rxOKAwOwiqIMjiZB76q5pYY49tboli6qp2PamjYIWCwChSco/T8UuJRQVcEMIJImPWj2C13/nKi2PaJA/8AKL0QYQkKoBgiZBjVSjKDfuG4JxAxUL1YH9qlZXyWUsefnv3o68i4tsoHOPpS1WBPrVN8HtXGKsmGanZHp71cWLhtmRiDuCf70GDcK4L5vYbNXui8D5gQV6r0oIKCNj+1N8S4YZROyCQDFAfEqCuj3E1axdVLg+ouS+lMqbxdcjkuUd4kUC1kXY/drce9Mpd4+vKVbcYrJ/SmosLbw463EyCsS6gHUyf99KJSLec3LYErCTA7yTRnvBr444AZisGdqT138VbjNbuvnokKBsb1XL/HuKVaycWYyxjfyTUdWb7L9FRiqshPliDGo/zUpe6rG+yhtFYwiBUqCYdd7ipUrZsJJBkGCO9XVi10SSd9zUqUkq3PuPzVew+alSnA0PDSek6np+KY5BOHJPf6fX8D+alSlPpfqlgkeIKoMLgNdulaVz7B8/tUqVl5PpUuxMJv/rUqVKlNf//Z"},"meta":{"xj10":{"t":"photo","c":"Nyx Ning / CC BY-SA 3.0"},"dxb6":{"t":"photo","c":"chensiyuan / CC BY-SA 4.0"},"hk3":{"t":"photo","c":"Haydn Hsin / CC BY-SA 3.0"},"qg7":{"t":"photo","c":"ZhengZhou / CC BY-SA 3.0"},"cx4":{"t":"photo","c":"Johannes Böckh / CC BY-SA 3.0"},"sc5":{"t":"photo","c":"Dcpeets / CC BY-SA 4.0"},"xz7":{"t":"photo","c":"This illustration was made by  / CC0"},"hs3":{"t":"photo","c":"Chi King / CC BY 2.0"},"mls6":{"t":"photo","c":"瑞丽江的河水 / CC BY-SA 4.0"},"hlb5":{"t":"photo","c":"Liuxingy / CC BY-SA 4.0"},"gl4":{"t":"photo","c":"King of Hearts / CC BY-SA 4.0"},"zjj4":{"t":"photo","c":"xiquinhosilva / CC BY 2.0"},"djy1":{"t":"photo","c":"xiquinhosilva / CC BY 2.0"},"hz3":{"t":"photo","c":"94rain / CC BY-SA 4.0"},"cq3":{"t":"photo","c":"Jonashtand / CC BY-SA 4.0"},"xm3":{"t":"photo","c":"Tiger@西北 / CC BY-SA 3.0"},"sy4":{"t":"photo","c":"song songroov / CC BY 3.0"},"sh3":{"t":"photo","c":"Stefan Fussan / CC BY-SA 3.0"},"bj4":{"t":"photo","c":"Han Zheng / CC BY-SA 2.0"},"xa3":{"t":"photo","c":"xiquinhosilva / CC BY 2.0"},"cd3":{"t":"photo","c":"JianEn Yu / CC BY 2.0"},"nm4":{"t":"map","c":"© OpenStreetMap"},"kansai5":{"t":"photo","c":"Martin Falbisoner / CC BY-SA 4.0"},"sz3":{"t":"photo","c":"King of Hearts / CC BY-SA 4.0"},"nj3":{"t":"photo","c":"Jiong Sheng from London, U / CC BY-SA 2.0"},"qd3":{"t":"photo","c":"StefanTsingtauer / CC BY-SA 4.0"},"wh3":{"t":"photo","c":"MonsieurRoi / CC BY-SA 3.0"},"cs3":{"t":"photo","c":"Zhangzhugang / CC BY-SA 4.0"},"gz5":{"t":"photo","c":"SONG1907 / CC BY-SA 4.0"},"bn4":{"t":"photo","c":"Cangminzho / CC BY-SA 4.0"},"yy3":{"t":"photo","c":"Jialiang Gao, www.peace-on / CC BY-SA 3.0"},"njg8":{"t":"photo","c":"w0zny / CC BY-SA 3.0"},"jz4":{"t":"photo","c":"Chensiyuan / CC BY-SA 4.0"},"tl3":{"t":"photo","c":"Gisling唐戈 / CC BY 3.0"},"ts3":{"t":"photo","c":"Charlie fong / Public domain"}}};


/* ═══ 往返大交通参考价（按族查表）═══
   费用表算的是落地之后的花费。用户拿人均 ¥7,496 做预算会漏掉两三千机票，
   这是最容易造成"钱不够"的一处。区间价按主要客源地估，只作量级参考。 */
const ARRIVE_COST={
 xj:['飞乌鲁木齐往返',1800,3000],  qg:['飞西宁/兰州往返',1200,2200],
 xz:['飞拉萨往返',2000,3500],      sc:['飞成都往返',1000,2000],
 cx:['飞成都往返',1000,2000],      dxb:['飞丽江/大理往返',1200,2200],
 mls:['飞丽江往返',1200,2200],     hlb:['飞海拉尔往返',1600,2800],
 nm:['飞额济纳往返',1800,3000,'金秋紧张'], zjj:['飞张家界往返',900,1800],
 gl:['飞桂林往返',800,1600],       hs:['高铁黄山北往返',400,900],
 djy:['高铁成都往返',600,1400],    hk:['飞香港往返',800,2000],
 kan:['飞大阪往返',2000,4000],     bj:['高铁或飞北京往返',600,1600],
 sh:['高铁或飞上海往返',500,1400], xa:['高铁西安往返',500,1200],
 cd:['高铁或飞成都往返',600,1400], hz:['高铁杭州往返',400,1100],
 cq:['高铁或飞重庆往返',600,1400], xm:['飞厦门往返',700,1600],
 sy:['飞三亚往返',1200,2800,'春节翻倍'], sz:['高铁苏州往返',400,1000],
 nj:['高铁南京往返',400,1100],     qd:['高铁或飞青岛往返',600,1400],
 wh:['高铁武汉往返',500,1200],     cs:['高铁长沙往返',500,1200],
 gz:['飞贵阳往返',900,1800],       bn:['飞西双版纳往返',1200,2400],
 yy:['飞昆明往返',900,1800],       jz:['飞成都往返',1000,2000],
 yl:['飞伊宁往返',1600,2800],      tl:['飞厦门往返',700,1600],
 ts:['高铁泰安往返',400,1000],     njg:['飞喀什往返',2000,3500]
};
/* 金额随当前货币换算——写死 ¥ 的话，选了美元还显示人民币，用户会以为是两套价 */
function arriveNoteOf(R){
  const a = R && ARRIVE_COST[R.fam];
  if(!a) return '';
  return a[0] + '约 ' + fm(a[1]) + '–' + fmN(a[2]) + (a[3]? '（'+a[3]+'）' : '');
}

const EXTRA_POOL = {
  /* ── 长线自驾 ── */
  xj:[{name:'可可托海三号矿坑深度',why:'额尔齐斯大峡谷全程徒步 8 km',dur:240,cost:90,q:'可可托海三号矿坑'},
      {name:'白哈巴村',why:'禾木往西 40 km · 西北第一村 · 需边防证',dur:300,cost:60,q:'白哈巴村'},
      {name:'五彩滩夜拍',why:'布尔津旁 · 日落后蓝调 40 分钟',dur:120,cost:65,q:'布尔津五彩滩'}],
  njg:[{name:'香妃墓 · 阿帕克霍加麻扎',why:'喀什东郊 · 伊斯兰建筑代表',dur:90,cost:30,q:'喀什香妃墓'},
       {name:'莎车老城 · 阿曼尼莎汗纪念陵',why:'和田路上 · 十二木卡姆发源地',dur:150,cost:40,q:'莎车阿曼尼莎汗纪念陵'},
       {name:'红其拉甫口岸',why:'中巴边境 4700m · 需另办边防证',dur:360,cost:100,q:'红其拉甫口岸'}],
  yl:[{name:'喀拉峻草原',why:'特克斯旁 · 空中草原 · 五花草甸六月最盛',dur:300,cost:145,q:'喀拉峻草原'},
      {name:'霍城薰衣草',why:'伊宁西 · 六月中下旬花期',dur:150,cost:40,q:'霍城薰衣草基地'},
      {name:'琼库什台村',why:'特克斯南 · 木屋与雪山 · 路况差',dur:300,cost:0,q:'琼库什台村'}],
  qg:[{name:'雅丹魔鬼城',why:'敦煌西 · 落日最佳 · 需坐区间车',dur:210,cost:120,q:'敦煌雅丹国家地质公园'},
      {name:'榆林窟',why:'瓜州南 · 比莫高窟安静 · 壁画同源',dur:180,cost:60,q:'瓜州榆林窟'},
      {name:'祁连卓尔山',why:'祁连县 · 丹霞与草原并置',dur:180,cost:70,q:'祁连卓尔山'}],
  cx:[{name:'党岭葫芦海',why:'丹巴西 · 徒步 6 小时往返 · 秋色最好',dur:420,cost:80,q:'党岭葫芦海'},
      {name:'塔公草原 · 木雅金塔',why:'新都桥旁 · 雅拉雪山正对',dur:150,cost:0,q:'塔公草原'},
      {name:'莫斯卡村',why:'金川方向 · 土拨鼠与格萨尔石刻',dur:300,cost:60,q:'莫斯卡村'}],
  sc:[{name:'牛奶海 · 五色海',why:'亚丁景区内 · 洛绒牛场往上徒步 4 小时',dur:360,cost:0,q:'稻城牛奶海'},
      {name:'兴伊措',why:'稻城北 · 高原湖泊 · 车行可达',dur:120,cost:0,q:'稻城兴伊措'},
      {name:'色拉草原晨雾',why:'稻城县城旁 · 日出前起雾',dur:90,cost:0,q:'稻城色拉草原'}],
  jz:[{name:'若尔盖草原 · 黄河九曲',why:'川主寺往北 · 日落最好',dur:300,cost:120,q:'若尔盖黄河九曲第一湾'},
      {name:'牟尼沟扎嘎瀑布',why:'松潘旁 · 钙华瀑布 · 人少',dur:210,cost:70,q:'牟尼沟风景区'},
      {name:'甲蕃古城',why:'九寨沟口 · 藏式建筑群',dur:90,cost:0,q:'甲蕃古城'}],
  dxb:[{name:'雨崩村徒步',why:'德钦方向 · 需两天 · 神瀑与冰湖',dur:600,cost:230,q:'雨崩村'},
       {name:'普达措国家公园',why:'香格里拉东 · 属都湖与碧塔海',dur:300,cost:258,q:'普达措国家公园'},
       {name:'沙溪古镇',why:'剑川 · 茶马古道唯一幸存集市',dur:180,cost:0,q:'沙溪古镇'}],
  mls:[{name:'雨崩神瀑',why:'雨崩村往上 · 往返 4 小时',dur:300,cost:0,q:'雨崩神瀑'},
       {name:'明永冰川',why:'德钦 · 梅里主峰下的冰舌',dur:240,cost:78,q:'明永冰川'},
       {name:'茨中教堂',why:'德钦南 · 藏区里的法式天主堂',dur:120,cost:0,q:'茨中教堂'}],
  xz:[{name:'桑耶寺',why:'山南 · 西藏第一座佛法僧俱全的寺',dur:180,cost:40,q:'桑耶寺'},
      {name:'扎什伦布寺',why:'日喀则 · 班禅驻锡地',dur:180,cost:100,q:'扎什伦布寺'},
      {name:'珠峰大本营',why:'定日方向 · 需另两天 · 边防证',dur:600,cost:180,q:'珠峰大本营'}],
  /* ── 草原沙漠湿地 ── */
  nm:[{name:'黑城遗址',why:'额济纳南 · 西夏古城 · 沙中残垣',dur:150,cost:60,q:'额济纳黑城遗址'},
      {name:'居延海日出',why:'额济纳北 · 芦苇与候鸟',dur:150,cost:60,q:'居延海'},
      {name:'策克口岸',why:'中蒙边境 · 需身份证',dur:180,cost:0,q:'策克口岸'}],
  hlb:[{name:'室韦 · 中俄边境',why:'额尔古纳河对岸就是俄罗斯 · 木刻楞民居',dur:240,cost:0,q:'室韦俄罗斯民族乡'},
       {name:'莫尔道嘎国家森林公园',why:'根河北 · 白桦林与林场小火车',dur:300,cost:160,q:'莫尔道嘎国家森林公园'},
       {name:'敖鲁古雅使鹿部落',why:'根河 · 中国最后的驯鹿民族',dur:150,cost:80,q:'敖鲁古雅使鹿部落'}],
  gz:[{name:'肇兴侗寨',why:'黎平 · 五座鼓楼 · 侗族大歌',dur:300,cost:80,q:'肇兴侗寨'},
      {name:'加榜梯田',why:'从江 · 云雾与梯田 · 需专程',dur:300,cost:0,q:'加榜梯田'},
      {name:'镇远古城',why:'舞阳河穿城 · 夜景灯火',dur:240,cost:0,q:'镇远古城'}],
  /* ── 山水短假 ── */
  hs:[{name:'塔川秋色',why:'宏村旁 · 十一月中下旬乌桕最红',dur:150,cost:35,q:'塔川村'},
      {name:'木坑竹海',why:'黟县 · 卧虎藏龙取景地',dur:120,cost:35,q:'木坑竹海'},
      {name:'齐云山',why:'休宁 · 道教名山 · 摩崖石刻',dur:240,cost:75,q:'齐云山'}],
  gl:[{name:'龙脊梯田',why:'龙胜 · 金坑大寨 · 五月灌水十月金黄',dur:300,cost:80,q:'龙脊梯田'},
      {name:'黄姚古镇',why:'贺州方向 · 需专程 · 比阳朔安静',dur:240,cost:100,q:'黄姚古镇'},
      {name:'漓江徒步 · 杨堤到兴坪',why:'沿江走 18 km · 精华段',dur:360,cost:0,q:'杨堤码头'}],
  zjj:[{name:'凤凰古城',why:'张家界南 · 需另一天 · 沱江吊脚楼',dur:420,cost:0,q:'凤凰古城'},
       {name:'黄龙洞',why:'武陵源旁 · 溶洞与地下河',dur:180,cost:100,q:'张家界黄龙洞'},
       {name:'宝峰湖',why:'武陵源 · 山顶湖泊 · 船游',dur:150,cost:96,q:'张家界宝峰湖'}],
  djy:[{name:'虹口漂流',why:'都江堰北 · 夏季限定',dur:240,cost:120,q:'都江堰虹口漂流'},
       {name:'安仁古镇 · 建川博物馆',why:'大邑 · 民国公馆群',dur:300,cost:100,q:'安仁古镇'},
       {name:'花水湾温泉',why:'大邑 · 泡汤收尾',dur:180,cost:150,q:'花水湾温泉'}],
  ts:[{name:'邹城孟庙孟府',why:'曲阜南半小时 · 比三孔安静',dur:180,cost:80,q:'邹城孟庙'},
      {name:'泰山桃花峪',why:'泰山西麓 · 索道上下 · 人少景秀',dur:240,cost:100,q:'泰山桃花峪'},
      {name:'尼山圣境',why:'曲阜东 · 夜间灯光秀',dur:240,cost:120,q:'尼山圣境'}],
  tl:[{name:'河坑土楼群',why:'南靖 · 北斗七星布局 · 人少',dur:150,cost:50,q:'河坑土楼群'},
      {name:'塔下村',why:'南靖 · 溪边土楼与张氏家庙',dur:120,cost:0,q:'塔下村'},
      {name:'中川古村落',why:'永定 · 胡文虎故居',dur:120,cost:40,q:'中川古村落'}],
  yy:[{name:'建水团山民居',why:'建水西 · 滇南民居博物馆',dur:180,cost:50,q:'团山民居'},
      {name:'建水小火车',why:'临安站到团山 · 米轨百年',dur:180,cost:120,q:'建水小火车'},
      {name:'沙甸大清真寺',why:'个旧 · 中国规模最大之一',dur:120,cost:0,q:'沙甸大清真寺'}],
  /* ── 海岛热带 ── */
  bn:[{name:'望天树空中走廊',why:'勐腊 · 36 米高树冠廊桥',dur:300,cost:130,q:'望天树景区'},
      {name:'中科院植物园夜游',why:'勐仑 · 夜观蛙虫与夜花',dur:150,cost:80,q:'中科院西双版纳热带植物园'},
      {name:'勐景来 · 中缅第一寨',why:'打洛 · 边境村寨',dur:180,cost:60,q:'勐景来'}],
  sy:[{name:'呀诺达雨林',why:'保亭 · 雨林徒步与踏瀑',dur:300,cost:170,q:'呀诺达雨林'},
      {name:'分界洲岛',why:'陵水 · 潜水能见度好',dur:300,cost:170,q:'分界洲岛'},
      {name:'后海村冲浪',why:'海棠湾 · 初学者友好',dur:180,cost:200,q:'三亚后海村'}],
  xm:[{name:'筼筜湖 · 白鹭洲',why:'市中心 · 夜景与白鹭',dur:120,cost:0,q:'厦门筼筜湖'},
      {name:'集美学村',why:'跨海 · 嘉庚建筑群',dur:180,cost:0,q:'集美学村'},
      {name:'园博苑',why:'集美 · 水上园林',dur:210,cost:60,q:'厦门园博苑'}],
  /* ── 城市漫步 ── */
  bj:[{name:'颐和园',why:'西郊 · 昆明湖与长廊',dur:240,cost:60,q:'颐和园'},
      {name:'圆明园',why:'颐和园旁 · 西洋楼遗址',dur:180,cost:35,q:'圆明园'},
      {name:'798 艺术区',why:'朝阳 · 包豪斯厂房改造',dur:180,cost:0,q:'798艺术区'}],
  sh:[{name:'朱家角水乡',why:'地铁 17 号线终点 · 放生桥',dur:240,cost:0,q:'上海朱家角'},
      {name:'上海中心大厦',why:'陆家嘴 · 118 层观光',dur:150,cost:180,q:'上海中心大厦'},
      {name:'思南公馆 · 田子坊',why:'黄浦 · 老洋房与弄堂',dur:180,cost:0,q:'思南公馆'}],
  xa:[{name:'华清池 · 骊山',why:'临潼 · 与兵马俑同线',dur:240,cost:120,q:'华清宫'},
      {name:'陕西历史博物馆',why:'小寨 · 需提前预约',dur:210,cost:0,q:'陕西历史博物馆'},
      {name:'大唐不夜城',why:'雁塔 · 夜间步行街',dur:150,cost:0,q:'大唐不夜城'}],
  cd:[{name:'三圣乡 · 白鹿镇',why:'城郊 · 花田与法式小镇',dur:300,cost:0,q:'成都三圣乡'},
      {name:'黄龙溪古镇',why:'双流南 · 府河边老街',dur:240,cost:0,q:'黄龙溪古镇'},
      {name:'东郊记忆',why:'成华 · 老厂房改造',dur:150,cost:0,q:'东郊记忆'}],
  hz:[{name:'西溪湿地',why:'城西 · 摇橹船与芦苇',dur:240,cost:80,q:'杭州西溪湿地'},
      {name:'九溪十八涧',why:'龙井南 · 溪边徒步',dur:180,cost:0,q:'九溪十八涧'},
      {name:'良渚古城遗址',why:'余杭 · 五千年城址',dur:210,cost:60,q:'良渚古城遗址公园'}],
  cq:[{name:'白公馆 · 渣滓洞',why:'歌乐山 · 近代史现场',dur:240,cost:0,q:'重庆白公馆'},
      {name:'四川美院黄桷坪',why:'九龙坡 · 涂鸦街',dur:150,cost:0,q:'黄桷坪涂鸦街'},
      {name:'武隆天生三桥',why:'需另加两天 · 喀斯特天坑',dur:480,cost:135,q:'武隆天生三桥'}],
  sz:[{name:'同里古镇',why:'城南 · 退思园与三桥',dur:300,cost:100,q:'同里古镇'},
      {name:'留园 · 网师园',why:'城西 · 网师园有夜花园',dur:210,cost:85,q:'苏州留园'},
      {name:'金鸡湖 · 诚品书店',why:'园区 · 现代苏州',dur:180,cost:0,q:'苏州金鸡湖'}],
  nj:[{name:'栖霞山',why:'城东北 · 十一月红叶',dur:240,cost:40,q:'南京栖霞山'},
      {name:'南京博物院',why:'中山门 · 民国馆最好',dur:210,cost:0,q:'南京博物院'},
      {name:'牛首山',why:'江宁 · 佛顶宫',dur:240,cost:98,q:'牛首山文化旅游区'}],
  qd:[{name:'小鱼山 · 信号山',why:'老城两处制高点 · 红瓦看得最全',dur:150,cost:30,q:'青岛小鱼山'},
      {name:'金沙滩',why:'黄岛 · 沙质最细',dur:210,cost:0,q:'青岛金沙滩'},
      {name:'即墨古城',why:'即墨 · 复建古城 · 夜景',dur:180,cost:0,q:'即墨古城'}],
  wh:[{name:'楚河汉街',why:'武昌 · 民国风步行街',dur:150,cost:0,q:'武汉楚河汉街'},
      {name:'木兰草原',why:'黄陂北 · 草原与马场',dur:300,cost:100,q:'木兰草原'},
      {name:'归元寺',why:'汉阳 · 数罗汉',dur:120,cost:20,q:'武汉归元寺'}],
  cs:[{name:'铜官窑古镇',why:'望城 · 唐代长沙窑遗址',dur:240,cost:100,q:'新华联铜官窑古镇'},
      {name:'湖南大学 · 岳麓书院夜游',why:'岳麓山下 · 夜里更静',dur:150,cost:0,q:'湖南大学'},
      {name:'靖港古镇',why:'望城 · 湘江边老街',dur:210,cost:0,q:'靖港古镇'}],
  /* ── 出境与周末 ── */
  hk:[{name:'南丫岛',why:'中环码头 · 渔村与海鲜',dur:300,cost:60,q:'南丫岛'},
      {name:'大澳渔村',why:'大屿山 · 棚屋与白海豚',dur:300,cost:80,q:'大澳渔村'},
      {name:'西九文化区 · M+',why:'尖沙咀西 · 视觉文化博物馆',dur:210,cost:120,q:'M+博物馆'}],
  kan:[{name:'姬路城',why:'兵库 · 现存最完整天守',dur:240,cost:80,q:'姬路城'},
       {name:'宇治 · 平等院',why:'京都南 · 十円硬币上那座',dur:210,cost:70,q:'平等院'},
       {name:'高野山',why:'和歌山 · 需住宿坊 · 另加一天',dur:480,cost:200,q:'高野山'}]
};

/* ═══ 动态 +1 天 ═══
   用户想多待一天却加不了 —— 备选点池就是为这个准备的。
   每加一天，从池子里取还没用过的景点排成新的一天；
   池子空了按钮置灰，点击提示「已无景点，请自行安排」。 */
var extraDays=0;                       /* 当前已加了几天 */
function poolOf(R){ return (EXTRA_POOL[R&&R.fam]||[]); }
function usedExtraKeys(){
  var used={};
  (DAYS||[]).forEach(function(d){ (d.stops||[]).forEach(function(s){ if(s._fromPool) used[s.name]=1; }); });
  return used;
}
function canAddDay(){
  if(!RT) return false;
  var pool=poolOf(RT), used=usedExtraKeys();
  return pool.some(function(x){ return !used[x.name]; });
}
function buildExtraDay(n){
  var pool=poolOf(RT), used=usedExtraKeys();
  /* 一天排一个主景点：备选点本来就是「专程去」的量级，
     硬塞两个反而赶。这样 3 个备选点能撑 3 天。 */
  var pick=pool.filter(function(x){ return !used[x.name]; }).slice(0,1);
  if(!pick.length) return null;
  var lastCity=(LODGES||[]).filter(Boolean).slice(-1)[0];
  var base=lastCity? lastCity.city : ((RT.dest||'').split(/[·・]/)[0]);
  return {
    tab:'D'+n, name:pick.map(function(x){return x.name.split(/[·・]/)[0];}).join(' · '),
    sub:'加出来的一天 · 从备选里排 · 轻',
    start:540, hardEnd:1200, drive:'0 h',
    pre:{mode:'transit',conn:'住处 → '+pick[0].name.split(/[·・]/)[0]+' · 按导航前往',min:45,cost:30},
    post:{mode:'transit',conn:'返回住处或直接离开',min:45,cost:30},
    stops:pick.map(function(x,i2){
      var st={k:'pool-'+n+'-'+i2, name:x.name, era:'', dur:x.dur, prio:i2===0?0:1,
              cost:x.cost||0, cat:(x.cost? 'tix':'free'), indoor:false,
              vibe:x.why, must:['必看', x.why], chips:[[x.cost?'':'up', x.cost? fm(x.cost) : '免票']],
              q:x.q, _fromPool:true};
      return st;
    })
  };
}
function addOneDay(){
  if(!canAddDay()){ toast(t('day.nomore')); return false; }
  var nd=buildExtraDay(DAYS.length+1);
  if(!nd){ toast(t('day.nomore')); return false; }
  DAYS.push(nd);
  /* mods 是按天索引的（rain/off/done 都存在里面），加天必须同步扩，
     否则 renderDay 读 mods[active].rain 会崩。 */
  if(typeof mods!=='undefined' && Array.isArray(mods) && mods.length){
    /* 照抄现有 mods 项的结构（skip 是 Set 不是对象，写错会 m.skip.has is not a function） */
    var proto=mods[0], fresh={};
    Object.keys(proto).forEach(function(k){
      var v=proto[k];
      fresh[k] = (v instanceof Set) ? new Set()
               : Array.isArray(v) ? []
               : (v && typeof v==='object') ? {}
               : (typeof v==='number') ? 0
               : (typeof v==='boolean') ? false : v;
    });
    mods.push(fresh);
  }
  /* 住宿链跟着延长。注意一天的行程原本 0 晚（LODGES 只有一个 null），
     加天后必须真的多出一晚，否则住宿链为空、费用表少算住宿。 */
  var L=LODGES.slice();
  var lastReal=L.filter(Boolean).slice(-1)[0];
  if(!lastReal){
    /* 原本没有住宿（当天往返），用目的地兜一个 */
    var city=(RT.dest||'').split(/[·・]/).pop().trim()||RT.name;
    lastReal={city:city, price:380, why:'加天后需过夜', q:city+' 酒店'};
  }
  L.splice(Math.max(0,L.length-1), 0, Object.assign({},lastReal));
  if(!L.length || L[L.length-1]!==null) L.push(null);
  LODGES=L;
  extraDays++;
  resolveAll();
  renderStripDays(); renderDay(); renderTotals(); renderStrip();
  try{ renderSheetChips(); }catch(e){}   /* 重绘天数区：+1 按钮的置灰态在这里算 */
  try{ renderLodges(); }catch(e){}
  /* 标题与副标题也要跟着改 —— 加到 6 天了还写「3 天」会让人以为没生效 */
  try{
    var nN=(LODGES||[]).filter(Boolean).length;
    var ttl=String(LR(RT,'title')).replace(/\d+\s*天/, DAYS.length+' 天');
    var mta=String(LR(RT,'meta')).replace(/\d+\s*天\s*\d+\s*晚/, DAYS.length+'天'+nN+'晚');
    $('mh-title').textContent=ttl;
    $('mh-meta').textContent=mta;
  }catch(e){}
  toast(t('day.added',{n:DAYS.length}));
  return true;
}
var RT=null,DAYS=[],LODGES=[],CLUSTER=null,INSERTS={};
var RENT=0,ROADFOOD=0,BUDGET=0,lodge4=0;
var sels={},selsM=new Set();
var addP=()=>{};
function snapDep(c,t){
  if(!c||!c.dep) return t;
  const d=c.dep;
  if(t<=d.first) return d.first;
  if(t>d.last) return t;
  const n=d.first+Math.ceil((t-d.first)/d.every)*d.every;
  return Math.min(n,d.last);
}
function resolveDay(di){
  const d=DAYS[di], m=mods[di];
  const {rs,cs}=dayMaterial(di); const conns=cs;
  const eff=c=>(c&&m.rain&&c.alt)?{...c,...c.alt,_alted:true}:c;
  const pre=eff(d.pre), post=eff(d.post);
  const doneKeys=new Set((m.done?m.done.list:[]).map(x=>x.k));
  const use=rs.map((s0,i)=>{
    if(s0.empty) return {...s0,_oi:i,_k:s0.k};
    let s=variantOf(s0); s._oi=i; s._k=s0.k; s._chooser=!!s0.opts; s._id=s0.id;
    s._cluster=s0._cluster; s._cFirst=s0._cFirst;
    const past=doneKeys.has(s0.k);
    if(m.rain && s.rainAlt && !past){
      const g={...s, ...s.rainAlt, swapped:true, chips:s.rainAlt.chips, detail:s.rainAlt.detail||s.detail, must:s.rainAlt.must||s.must};
      if(s.rainAlt.dur) delete g.openUntil;
      g._oi=i; g._k=s._k; g._chooser=s._chooser; g._id=s._id; g._cluster=s._cluster; g._cFirst=s._cFirst;
      g.prio=s.prio; g.cat=s.cat; s=g;
    } else if(m.rain && !past && s.flagRain){ s={...s, rainFlag:true}; }
    else if(m.rain && !past && s.indoor===false){
      /* ═══ 雨天方案自动推导 ═══
         全站只有 4 处手写 rainAlt，但有 547 个站点标了 indoor —— 数据本来就在。
         露天站点遇雨：当天有室内备选就提示可换，没有就标"带伞/可能受影响"。
         这样每条线路点「遇上下雨」都能看到真实差异，而不是清一色「不变」。 */
      const indoorAlt = rs.find(function(x){ return x && x.indoor===true && !doneKeys.has(x.k) && x.k!==s0.k; });
      s = indoorAlt
        ? {...s, rainFlag:true, rainHint:'可与「'+String(indoorAlt.name).split(/[·・]/)[0]+'」对调，室内不受影响'}
        : {...s, rainFlag:true, rainHint:'露天站点 · 带伞或缩短停留'};
    }
    return s;
  });
  const emptyAt=use.findIndex(s=>s.empty);
  const real=use.filter(s=>!s.empty);
  const userGhosts=real.filter(s=>m.skip.has(s._k));
  const carry={min:0,km:0,cost:0};
  const cutConns=(li,base)=>{ /* li=在剩余序列中的位置 · base=剩余序列在接驳数组中的偏移 */
    const ii=base+li-1;
    if(ii<0){ if(conns.length){ const c=conns.shift();
      carry.min+=c.min; carry.km+=c.km||0; carry.cost+=c.cost||0; } return; }
    const a=conns[ii], b=conns[ii+1];
    if(a&&b){ const km=(a.km||0)+(b.km||0);
      conns.splice(ii,2,{mode:a.mode,conn:`${km?`${km} km · `:''}续驶 ${a.min+b.min} 分 · 合并段`,
        min:a.min+b.min, km, cost:(a.cost||0)+(b.cost||0), via:b.via||a.via, dep:a.dep}); }
    else if(a){ conns.splice(ii,1); }
  };
  const durOf=(s,arr)=>{
    if(!s.openUntil) return s.dur;
    let dur=Math.max(s.openMin, s.openUntil-arr);
    if(s.openMax) dur=Math.min(dur,s.openMax);
    return dur;
  };
  let list=real.filter(s=>!m.skip.has(s._k));
  userGhosts.slice().sort((a,b)=>b._oi-a._oi).forEach(g=>{
    cutConns(real.indexOf(real.find(x=>x._k===g._k)),0);
  });
  const idxFirst=list.findIndex(x=>!doneKeys.has(x._k));
  const frozen=(m.done?m.done.list:[]).map(f=>{
    const s=list.find(x=>x._k===f.k);
    return s?{s:{...s,past:true},arr:f.arr,dur:f.dur,warn:0,squeezed:0,past:true}:null;
  }).filter(Boolean);
  const walk=(rem)=>{
    let t,out=[],viol=null;
    if(m.done){ t=m.done.anchor;
      if(m.done.preDepart){ if(pre){ t=snapDep(pre,t)+pre.min; } t+=carry.min; }
      else{ const c=conns[idxFirst-1];
        if(idxFirst>0 && c){ t=snapDep(c,t)+c.min; } } }
    else{ t=d.start+m.off; if(pre){ t=snapDep(pre,t)+pre.min; } t+=carry.min; }
    rem.forEach((s,i)=>{
      let arr=t;
      if(s.dep) arr=snapDep(s,arr);
      if(s.earliest && arr<s.earliest) arr=s.earliest;
      const dur=durOf(s,arr);
      if(s.latest && arr>s.latest) viol=viol||s;
      t=arr+dur;
      out.push({s,arr,dur,warn:s.latest&&arr>s.latest?arr-s.latest:0,
                squeezed:s.openUntil&&!s.openMax?Math.max(0,(s.baseDur||0)-dur):0});
      const ci=(m.done?idxFirst:0)+i;
      if(i<rem.length-1 && conns[ci]){ t=snapDep(conns[ci],t)+conns[ci].min; }
    });
    if(post) t+=post.min;
    if(t>d.hardEnd && !viol){ viol={hard:true}; }
    return {out,end:t,viol};
  };
  (function base(){ let t=d.start+(pre?pre.min:0);
    real.forEach((s,i)=>{ let arr=t;
      if(s.earliest&&arr<s.earliest)arr=s.earliest;
      const dur=durOf(s,arr);
      s.baseDur=dur; t=arr+dur+(i<real.length-1&&conns[i]?conns[i].min:0); }); })();
  let rem=list.filter(x=>!doneKeys.has(x._k)), dropped=[];
  let r=walk(rem);
  while(r.viol){
    const pool=(r.viol.latest && !r.viol.hard)?rem.slice(0,rem.indexOf(r.viol)):rem;
    const cand=pool.filter(x=>x.prio>0 && !m.pinned.has(x._k)).sort((a,b)=>b.prio-a.prio)[0];
    if(!cand) break;
    dropped.push(cand);
    const li=rem.indexOf(cand); rem.splice(li,1);
    cutConns(li, m.done?idxFirst:0);
    r=walk(rem);
  }
  const cats={tix:0,food:0,tolls:0,km:0};
  [...frozen.map(f=>f.s),...rem].forEach(x=>{ if(cats[x.cat]!==undefined) cats[x.cat]+=x.cost; if(x.km) cats.km+=x.km; });
  conns.forEach(c=>{ cats.tolls+=c.cost||0; cats.km+=c.km||0; });
  cats.tolls+=carry.cost; cats.km+=carry.km;
  if(pre){ cats.tolls+=pre.cost||0; cats.km+=pre.km||0; }
  if(post){ cats.tolls+=post.cost||0; cats.km+=post.km||0; }
  const end = r.out.length? r.end : (m.done? m.done.anchor+(post?post.min:0) : r.end);
  return {sched:[...frozen,...r.out],conns,dropped,userGhosts,emptyAt,cats,end,pre,post,
          doneCount:frozen.length,idxFirst,alted:!!(pre&&pre._alted),
          warnStop:r.out.find(x=>x.warn)};
}
function resolveAll(){ resolved=DAYS.map((_,i)=>resolveDay(i)); }
function lodgeOf(di){ const L=LODGES[di]; if(!L) return null; return L.opts?L.opts[lodge4]:L; }
/* 每天最低伙食基线：行程里排进去的"吃饭站"只是重点推荐的那几顿，
   没排到的天用户照样要吃三顿。之前只算排进去的 + 路餐，
   导致川西 4 天餐饮只有 ¥180（一天 45 元），明显不合常识。
   基线按当地物价分档，只补差额——已排够的天不会被重复计入。 */
const FOOD_FLOOR={
  intl:320,          /* 日本等境外 */
  tier1:180,         /* 北上广深港 */
  tourist:150,       /* 三亚、九寨、丽江等旅游目的地 */
  normal:130,        /* 多数省会与地级市 */
  remote:120         /* 高原、牧区、县城 */
};
function foodFloorOf(R){
  if(!R) return FOOD_FLOOR.normal;
  if(R.locale && R.locale.region==='intl') return FOOD_FLOOR.intl;
  const d=String(R.dest||'')+String(R.name||'');
  if(/北京|上海|香港|深圳|广州/.test(d)) return FOOD_FLOOR.tier1;
  if(/三亚|九寨|丽江|大理|阳朔|鼓浪屿|张家界|黄山/.test(d)) return FOOD_FLOOR.tourist;
  if(/西藏|新疆|青海|甘肃|内蒙古|帕米尔|草原|高原/.test(d)) return FOOD_FLOOR.remote;
  return FOOD_FLOOR.normal;
}
function totals(){
  const t={tix:0,food:ROADFOOD,tolls:0,km:0};
  resolved.forEach(r=>{ t.tix+=r.cats.tix; t.food+=r.cats.food; t.tolls+=r.cats.tolls; t.km+=r.cats.km; });
  /* 伙食兜底：按天算，排进去的餐费已够就不补 */
  if(RT && DAYS && DAYS.length){
    const floor=foodFloorOf(RT)*DAYS.length;
    if(t.food<floor) t.food=floor;
  }
  const car=(RT&&!RT.perCar) ? t.tolls : (RENT + t.km*FUEL + t.tolls)/2;
  const lodge=LODGES.reduce((a,L,i)=>a+(L?(L.opts?L.opts[lodge4].price:L.price):0),0)/2;
  return {...t, car, lodge, total:t.tix+t.food+car+lodge};
}


