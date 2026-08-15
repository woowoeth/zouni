/* 走你·数据层 v76 · 56 条方案 */

/* ============================================================
   走你 ZOU · 引擎 X1（自驾形态）
   三形态同构：接驳件 conn={mode,min,km,cost,via,dep,alt}
   · 本地/城市游：mode walk|metro，km 缺省，单锚住宿（香港版）
   · 长途自驾：mode drive，km 计油，路桥入 cost，每晚换宿（本版）
   · 火车/轮渡：mode train|ferry，dep 班次吸附（本版 D4 区间车同机制）
   「现在出发」键在接驳缝上：锚=手机此刻，已过定格，后面顺排。
   ============================================================ */

const FUEL=0.65;                              /* 油费 ¥/km · 各线路共用 */
var RENT=4000, ROADFOOD=620, BUDGET=7500, RT=null;
var lodge4=0;

/* 每晚住宿链（D10 还车无宿）。D4 喀纳斯真取舍：湖边晨雾 vs 山下省钱 */
const XJ10_LODGES=[
 {city:'乌鲁木齐',price:350,why:'南门商圈 · 明早出城顺',q:'乌鲁木齐 南门',pt:[512,242]},
 {city:'富蕴县',price:360,why:'县城东侧 · 楼下有夜市',q:'富蕴县',pt:[548,108]},
 {city:'布尔津',price:380,why:'河堤夜市步行 5 分',q:'布尔津 河堤夜市',pt:[336,68]},
 {opts:[
   {city:'喀纳斯 · 湖区山庄',price:680,why:'晨雾就在门口 · 免早起进山',q:'喀纳斯 景区',pt:[272,44]},
   {city:'贾登峪',price:420,why:'省 ¥130/人 · 翌日出山更顺',q:'贾登峪',pt:[298,58]}]},
 {city:'禾木村 · 小木屋',price:520,why:'夜里能听见河 · 观景台步行可达',q:'禾木村',pt:[332,86]},
 {city:'乌尔禾镇',price:340,why:'魔鬼城 12 km · 镇上唯一主街',q:'乌尔禾',pt:[306,158]},
 {city:'赛里木湖 · 房车营地',price:460,why:'湖畔日出免赶路',q:'赛里木湖',pt:[124,208]},
 {city:'伊宁 · 喀赞其边',price:420,why:'蓝房子巷口 · 夜市步行圈',q:'伊宁 喀赞其',pt:[150,252]},
 {city:'那拉提镇',price:400,why:'明早直上独库',q:'那拉提镇',pt:[252,266]},
 null];
/* 相邻片区（多选）：可可托海三点，勾几个串几个 */
const XJ_CLUSTER={
 id:'d2-koko', label:'可可托海 · 相邻可多选',
 emptyConn:null,
 opts:[
 {k:'mine3',name:'三号矿坑',era:'功勋矿 · 地质圣坑',dur:90,cost:90,cat:'tix',indoor:false,
  vibe:'一个挖了七十年的螺旋大坑，半部共和国矿业史。',
  must:['必看','观景台俯瞰整坑 · 陈列馆里的矿石墙'],
  chips:[['','人文'],['','地质']],why:'环线上最重的一站人文',
  join:{mode:'drive',conn:'景区驳车 ＋ 步行 · 20 分',min:20,cost:0},
  q:'可可托海三号矿坑',pt:[556,88]},
 {k:'gorge',name:'额尔齐斯大峡谷 · 神钟山',era:'花岗岩峰',dur:60,cost:60,cat:'tix',indoor:false,
  vibe:'一口青灰色巨钟扣在河边，额河从脚下流向北冰洋。',
  must:['必看','神钟山正面栈道尽头 · 河滩卵石滩'],
  chips:[['','徒步 2 km'],['','地质']],why:'峡谷正主，体力小消耗',
  join:{mode:'drive',conn:'自驾短驳 · 12 km · 15 分',min:15,km:12,cost:0},
  q:'额尔齐斯大峡谷',pt:[562,72]},
 {k:'kekesu',name:'可可苏里 · 野鸭湖',era:'湿地',dur:30,cost:30,cat:'tix',indoor:false,
  vibe:'芦苇荡里一面镜子湖，顺路二十分钟的温柔。',
  must:['必看','西岸栈道逆光芦苇'],
  chips:[['up','顺路'],['','湿地']],why:'摄影加站 · 时间紧先让',
  profile:'摄影晨雾党', join:{mode:'drive',conn:'返程顺路 · 8 km · 12 分',min:12,km:8,cost:0},
  q:'可可苏里',pt:[544,102]}]
};

/* 十日路书：pre=当日进程大接驳 · post=进店段 · lodge 见上 */
const XJ10_DAYS=[
{ tab:'D1', name:'乌鲁木齐', sub:'提车 · 市区 8 km', start:840, hardEnd:1320, drive:'0.5 h',
  pre:null, post:{mode:'drive',conn:'回住处 · 6 km · 20 分',min:20,km:6,cost:0},
  stops:[
  {k:'pickup',name:'机场提车 · 验车',era:'租车站',dur:60,prio:0,cost:0,cat:'tix',indoor:true,
   vibe:'环线成败一半在这一小时。',
   must:['必做','绕车拍视频 · 查备胎胎压 · 记油位公里数'],
   chips:[['up','SUV 建议'],['','确认玻璃石子险']],
   q:'乌鲁木齐地窝堡机场 租车',pt:[506,252]},
  {mode:'drive',conn:'市区 · 8 km · 25 分',min:25,km:8,cost:0,via:'沿途 · 先加满油，记下这家站的位置'},
  {k:'bazaar',name:'新疆国际大巴扎',era:'二道桥',dur:0,openUntil:1260,openMin:120,openMax:180,prio:1,cost:68,cat:'food',indoor:false,
   vibe:'先用一座巴扎把胃和眼睛调到新疆频道。',
   must:['必吃','馕坑肉 ＋ 现打酸奶 · 顶楼观景台看夕礼'],
   chips:[['','夜市'],['','人多看包']],
   q:'新疆国际大巴扎',pt:[514,246]}
]},
{ tab:'D2', name:'可可托海', sub:'480 km · 驾驶约 6.8 h · 重', start:570, hardEnd:1290, drive:'6.8 h',
  pre:{mode:'drive',conn:'乌鲁木齐 → 可可托海 · 480 km · 约 6 小时 50 分',min:410,km:480,cost:0,
    via:'沿途 · 火烧山雅丹（停 20 分）· 恰库尔图午餐补给 · 中途换驾一次'},
  post:{mode:'drive',conn:'→ 富蕴县城 · 55 km · 50 分',min:50,km:55,cost:0,via:'沿途 · 额河沿线牧道，牛羊横穿减速'},
  stops:[ {clusterRef:true} ]},
{ tab:'D3', name:'布尔津', sub:'340 km · 驾驶约 4.7 h · 中', start:600, hardEnd:1305, drive:'4.7 h',
  pre:{mode:'drive',conn:'富蕴 → 布尔津 · 340 km · 约 4 小时 40 分',min:280,km:340,cost:0,
    via:'沿途 · 乌伦古湖观鸥（停 30 分）· 全程区间测速'},
  post:{mode:'walk',conn:'步行回住处 · 10 分',min:10,cost:0},
  stops:[
  {k:'bj-town',name:'布尔津 · 童话边城闲逛',era:'俄式小城',dur:60,prio:2,cost:0,cat:'tix',indoor:false,
   vibe:'额河边最干净的小城，木屋立面刷成糖果色。',
   must:['必看','中苏航运纪念碑 · 老码头一段河堤'],
   chips:[['up','免票'],['','好停车']],
   q:'布尔津',pt:[330,62]},
  {mode:'walk',conn:'步行 · 8 分 · 沿河堤',min:8,cost:0,via:'沿途 · 傍晚河面起风，长椅都朝着水'},
  {k:'bj-bank',name:'额河河堤 · 落日长椅',era:'河堤公园',dur:0,openUntil:1165,openMin:45,prio:2,cost:0,cat:'free',indoor:false,
   vibe:'等一场 21 点半才谢幕的日落。',
   must:['必看','对岸沙丘被落日点着的十分钟'],
   chips:[['up','免票']],
   q:'布尔津 河堤公园',pt:[338,64]},
  {mode:'walk',conn:'步行 · 10 分',min:10,cost:0,via:'沿途 · 夜市牌坊起就有烤肉烟'},
  {k:'d3-night',id:'d3-night',prio:1,cat:'food',optLabel:'河堤夜市 · 选一家',
   opts:[
   {name:'冷水鱼 · 烤狗鱼',era:'额河特产',dur:90,cost:148,indoor:false,
    vibe:'额尔齐斯河的冷水鱼，炭火烤到皮脆。',
    must:['必点','烤狗鱼 ＋ 卡瓦斯 · 鱼汤最后喝'],
    chips:[['','夜市'],['','现杀现烤']],why:'到布尔津的理由',
    q:'布尔津河堤夜市',pt:[336,70]},
   {name:'家常抓饭馆',era:'巷内',dur:60,cost:58,indoor:true,
    vibe:'一盘抓饭一碗奶茶，省出的钱明天加油。',
    must:['必点','羊肉抓饭 · 皮牙子凉菜'],
    chips:[['','快'],['','省']],why:'省 ¥90 · 快 30 分',
    profile:'路上省着花', q:'布尔津 抓饭',pt:[334,72]}]}
]},
{ tab:'D4', name:'喀纳斯', sub:'150 km 山路 ＋ 区间车 · 轻', start:570, hardEnd:1290, drive:'2.5 h',
  pre:{mode:'drive',conn:'布尔津 → 贾登峪 换区间车进景区 · 150 km ＋ 40 分 · 约 3 小时 10 分',min:190,km:150,cost:0,
    via:'沿途 · 冲乎尔盘山段限速 40 · 贾登峪 10:00 起每 20 分一班'},
  post:{mode:'shuttle',conn:'区间车＋步行进住处 · 40 分',min:40,cost:0},
  stops:[
  {k:'sanwan',name:'喀纳斯三湾',cng:'最美湖泊',era:'月亮湾 · 卧龙湾 · 神仙湾',dur:150,prio:0,cost:290,cat:'tix',indoor:false,
   vibe:'区间车沿河谷把三个湾串成一条蓝绿色项链。',
   must:['必看','月亮湾栈道走到底 · 神仙湾晨雾位记下明天用'],
   chips:[['','票含区间车'],['','栈道 3 km']],
   detail:'<p><b>动线</b>　贾登峪上车 → 神仙湾 → 月亮湾 → 卧龙湾，回程车随上随下。</p>',
   q:'喀纳斯景区',pt:[276,40]},
  {mode:'shuttle',conn:'区间车 · 20 分 · 每 20 分一班（首末 10:00–20:30）',min:20,cost:0,dep:{first:600,every:20,last:1230},
   via:'沿途 · 右侧靠窗看河'},
  {k:'guanyu',name:'观鱼台',cng:'最美湖泊',era:'湖区制高点',dur:90,prio:1,cost:120,cat:'tix',indoor:false,latest:1140,
   rainAlt:{name:'湖边栈道 · 换塘坝子',era:'湖区',dur:60,cost:0,chips:[['up','雨天方案'],['up','省 ¥120']],vibe:'索道停驶就贴着湖走，雾里另一种喀纳斯。',must:['必看','一道湾回望主湖']},
   vibe:'一千级台阶换一整面湖的蓝。',
   must:['必看','正面观景台的"喀纳斯蓝" · 下午顺光'],
   chips:[['','索道＋门票'],['down','大风雷雨停驶']],
   q:'喀纳斯观鱼台',pt:[268,34]}
]},
{ tab:'D5', name:'禾木', sub:'70 km 山路 · 限速 40 · 轻', start:570, hardEnd:1320, drive:'2 h',
  pre:{mode:'drive',conn:'喀纳斯 → 禾木 · 70 km · 约 1 小时 50 分',min:110,km:70,cost:0,
    via:'沿途 · 全程限速 40 多弯 · 禾木桥前观景台可停 10 分'},
  post:{mode:'walk',conn:'步行下台回木屋 · 20 分',min:20,cost:0},
  stops:[
  {k:'hemu-vill',name:'禾木村 · 闲逛',cng:'最美古镇',era:'图瓦人村落',dur:0,openUntil:1140,openMin:60,prio:1,cost:140,cat:'tix',indoor:false,
   vibe:'木屋、桦林与炊烟，把下午整段交给无所事事。',
   must:['必看','禾木桥下河滩 · 村口小卖部的酸奶疙瘩'],
   chips:[['','票含区间'],['','海拔 1,200 m']],
   q:'禾木村',pt:[336,90]},
  {mode:'walk',conn:'步行上观景台 · 25 分 · 缓坡',min:25,cost:0,via:'沿途 · 白桦林步道，蚊虫多备驱蚊'},
  {k:'hemu-view',name:'禾木观景台 · 日落',cng:'最美古镇',era:'村后山坡',dur:0,openUntil:1290,openMin:60,prio:0,cost:0,cat:'free',indoor:false,
   vibe:'全村炊烟在 21 点后一起升起来。',
   must:['必看','日落后再等 20 分，蓝调时刻的木屋灯'],
   chips:[['up','免票'],['','风大带外套']],
   q:'禾木观景台',pt:[328,80]}
]},
{ tab:'D6', name:'魔鬼城', sub:'400 km · 驾驶约 5.5 h · 重', start:420, hardEnd:1320, drive:'5.5 h',
  pre:{mode:'walk',conn:'摸黑上观景台 · 25 分',min:25,cost:0},
  post:{mode:'drive',conn:'→ 乌尔禾镇 · 12 km · 15 分',min:15,km:12,cost:0},
  stops:[
  {k:'hemu-fog',name:'禾木晨雾 · 观景台',cng:'最美古镇',era:'07:00 窗口',dur:60,prio:2,cost:0,cat:'free',indoor:false,
   vibe:'雾从河谷漫上来盖住半个村子，只给早起的人。',
   must:['必看','雾海裂开露出屋顶的那几分钟'],
   chips:[['up','免票'],['down','贪睡可跳过']],
   q:'禾木观景台',pt:[326,82]},
  {mode:'drive',conn:'禾木 → 乌尔禾 · 400 km · 约 5 小时 30 分',min:330,km:400,cost:0,
   via:'沿途 · 布尔津加满油 · 克拉玛依段侧风大 · 中途换驾一次'},
  {k:'urhe-rest',name:'乌尔禾镇 · 进店休整',era:'白日歇脚',dur:0,openUntil:1130,openMin:45,prio:2,cost:0,cat:'free',indoor:true,
   vibe:'把午后交给房间，黄昏才是魔鬼城的正片。',
   must:['必做','补水补电 · 19 点前别晒'],
   chips:[['up','避暑']],
   q:'乌尔禾',pt:[306,156]},
  {mode:'drive',conn:'→ 魔鬼城 · 12 km · 15 分',min:15,km:12,cost:0,via:'沿途 · 进门前加油站是明早唯一一家'},
  {k:'ghost-city',name:'世界魔鬼城 · 黄昏场',cng:'最美雅丹',era:'雅丹地貌',dur:120,prio:0,cost:106,cat:'tix',indoor:false,flagRain:true,
   vibe:'侧光把雅丹烧成铁锈红，风声就是配乐。',
   must:['必看','小火车 2 号台下车走到"孔雀台" · 末班 21:30'],
   chips:[['','票含小火车'],['down','大风沙尘看公告']],
   q:'乌尔禾魔鬼城',pt:[298,148]}
]},
{ tab:'D7', name:'赛里木湖', sub:'440 km · 驾驶约 6 h · 重', start:600, hardEnd:1320, drive:'6 h',
  pre:{mode:'drive',conn:'乌尔禾 → 赛里木湖 · 440 km · 约 6 小时',min:360,km:440,cost:85,
    via:'沿途 · 独山子服务区加油＋换驾 · G30 全程区间测速'},
  post:{mode:'drive',conn:'→ 湖畔营地 · 5 km · 10 分',min:10,km:5,cost:0},
  stops:[
  {k:'sailimu-loop',name:'环湖自驾 · 顺时针',era:'湖周 90 km',dur:150,km:90,prio:0,cost:145,cat:'tix',indoor:false,
   vibe:'一小时看完四季的湖，每个海角都想停。',
   must:['必看','点将台看"大西洋最后一滴眼泪" · 西海草原侧牛羊入画'],
   chips:[['','票含环湖'],['','车不出景区']],
   q:'赛里木湖',pt:[118,202]},
  {mode:'walk',conn:'营地旁步行 · 5 分',min:5,cost:0},
  {k:'sailimu-dusk',name:'湖畔 · 等日落',era:'营地前滩',dur:0,openUntil:1290,openMin:60,prio:2,cost:0,cat:'free',indoor:false,
   vibe:'湖水在 21 点变成深蓝，冷得很干净。',
   must:['必看','日落后半小时的粉紫色湖面'],
   chips:[['up','免票'],['','夜里 8°C 穿抓绒']],
   q:'赛里木湖 营地',pt:[126,212]}
]},
{ tab:'D8', name:'伊宁', sub:'90 km · 驾驶约 2 h · 轻', start:630, hardEnd:1290, drive:'2 h',
  pre:{mode:'drive',conn:'赛里木湖 → 果子沟 · 30 km · 40 分',min:40,km:30,cost:0,
    via:'沿途 · 出景区南门直接上桥方向'},
  post:{mode:'drive',conn:'→ 喀赞其旁住处 · 3 km · 10 分',min:10,km:3,cost:0},
  stops:[
  {k:'guozigou',name:'果子沟大桥 · 观景台',era:'高架双螺旋',dur:30,prio:1,cost:0,cat:'free',indoor:false,
   vibe:'桥从松林里两次转身跳下河谷。',
   must:['必看','回望桥＋赛湖同框位，停车区拍完就走'],
   chips:[['up','免票'],['','大车多注意']],
   q:'果子沟大桥观景台',pt:[146,222]},
  {mode:'drive',conn:'→ 伊宁 · 60 km · 70 分 · 隧道群',min:70,km:60,cost:0,via:'沿途 · 出隧道就是伊犁河谷的绿'},
  {k:'d8-kzq',id:'d8-kzq',prio:1,cat:'food',optLabel:'喀赞其 · 选一种逛法',
   opts:[
   {name:'手工冰淇淋 ＋ 烤包子',era:'蓝房子巷',dur:100,cost:45,indoor:false,
    vibe:'一路蓝墙一路吃，马车叮当从身边过。',
    must:['必点','老字号手工冰淇淋 · 出炉五分钟内的烤包子'],
    chips:[['','边走边吃']],why:'轻逛 · 拍蓝房子',
    q:'伊宁喀赞其',pt:[148,250]},
   {name:'馕坑肉小馆 · 正餐',era:'民居院',dur:100,cost:88,indoor:true,
    vibe:'坐进维吾尔院子里吃一顿正经的。',
    must:['必点','馕坑肉 ＋ 手工酸奶 · 配刚出馕坑的馕'],
    chips:[['','院子座']],why:'吃透一顿',
    profile:'偏院子里吃饭', q:'伊宁喀赞其 馕坑肉',pt:[150,254]}]},
  {mode:'walk',conn:'步行 · 15 分',min:15,cost:0,via:'沿途 · 巷口手风琴常有人拉'},
  {k:'six-star',name:'六星街 · 黄昏',cng:'最美草原',era:'1930s 街区',dur:0,openUntil:1230,openMin:60,openMax:120,prio:2,cost:0,cat:'free',indoor:false,
   vibe:'六条街从圆心放射出去，家家院里葡萄架。',
   must:['必看','中心亭子傍晚的手风琴 · 面包房买明天路餐'],
   chips:[['up','免票']],
   q:'伊宁六星街',pt:[156,246]}
]},
{ tab:'D9', name:'那拉提', sub:'260 km · 驾驶约 3.7 h · 中', start:600, hardEnd:1305, drive:'3.7 h',
  pre:{mode:'drive',conn:'伊宁 → 那拉提 · 260 km · 约 3 小时 40 分',min:220,km:260,cost:0,
    via:'沿途 · 巩乃斯河谷牧群横穿减速 · 观景带随停随走'},
  post:{mode:'drive',conn:'→ 那拉提镇 · 8 km · 15 分',min:15,km:8,cost:0},
  stops:[
  {k:'d9-grass',id:'d9-grass',prio:0,cat:'tix',optLabel:'草原玩法 · 选一种',
   opts:[
   {name:'空中草原 · 区间车',era:'雪山接草甸',dur:180,cost:210,indoor:false,
    vibe:'区间车爬到 2,200 米，草毯一直铺到雪线。',
    must:['必看','游客大道尽头的雪山正面位 · 哈萨克毡房奶茶'],
    chips:[['','票含区间'],['','日晒强']],why:'那拉提正主',
    q:'那拉提空中草原',pt:[256,258]},
   {name:'河谷草原 · 步道',era:'巩乃斯河沿',dur:120,cost:90,indoor:false,
    vibe:'沿河走进草原的近景，省下的时间给日落。',
    must:['必看','河湾牧道的马群过河'],
    chips:[['','省 ¥120'],['','步行 4 km']],why:'省钱省时版',
    profile:'路上省着花', q:'那拉提河谷草原',pt:[254,262]}]},
  {mode:'drive',conn:'→ 镇边草坡 · 6 km · 12 分',min:12,km:6,cost:0},
  {k:'nlt-dusk',name:'镇边草坡 · 日落',cng:'最美草原',era:'免费机位',dur:0,openUntil:1290,openMin:45,prio:2,cost:0,cat:'free',indoor:false,
   vibe:'不进景区也有整片金色的草。',
   must:['必看','逆光的草穗 · 21 点后的粉天'],
   chips:[['up','免票']],
   q:'那拉提镇',pt:[250,268]}
]},
{ tab:'D10', name:'独库 · 还车', sub:'500 km · 驾驶约 8.2 h · 重', start:540, hardEnd:1290, drive:'8.2 h',
  pre:{mode:'drive',conn:'独库公路北段 · 那拉提 → 独山子 · 250 km · 约 5 小时 30 分',min:330,km:250,cost:0,
    via:'沿途 · 哈希勒根达坂 · 老虎口栈桥段慢行 · 全程区间测速禁停拍照区',
    alt:{conn:'独库临时管制 · 绕行 G218 经巴音布鲁克—和静 · 590 km · 约 8 小时',min:480,km:590,cost:60,
      via:'沿途 · 和静县城午餐加油 · 出发前看交警放行公告'}},
  post:null,
  stops:[
  {k:'dsz-canyon',name:'独山子大峡谷',era:'亿年切谷',dur:60,prio:2,cost:54,cat:'tix',indoor:false,
   vibe:'大地在这里裂开一道灰绿色的口子。',
   must:['必看','玻璃栈桥下望辫状河 · 谷沿风大扶稳手机'],
   chips:[['','顺路 15 分'],['down','时间紧先让']],
   q:'独山子大峡谷',pt:[362,206]},
  {mode:'drive',conn:'独山子 → 乌鲁木齐 · 250 km · 约 2 小时 40 分 · G30',min:160,km:250,cost:75,
   via:'沿途 · 乌苏服务区最后一次加油 · 还车前顺路洗车'},
  {k:'return-car',name:'还车 · 乌鲁木齐',era:'满油交车',dur:45,prio:0,cost:0,cat:'tix',indoor:true,
   vibe:'环线画圆的最后一步。',
   must:['必做','满油 · 对公里数 · 验车拍视频 · 问押金解冻时限'],
   chips:[['','留足 45 分']],
   q:'乌鲁木齐地窝堡机场 租车还车',pt:[508,246]}
]}];

/* 真插入：五彩滩（D3 河堤前）· 白哈巴（D4 三湾后 · 触发边防证清单） */
const XJ_INSERTS={
 wucai:{day:2, afterK:'bj-town', label:'D3', brief:'布尔津北 24 km · 日落雅丹 · 约 75 分 · ¥48',
   stop:{k:'wucai',name:'五彩滩',era:'额河北岸雅丹',dur:75,prio:2,cost:48,cat:'tix',indoor:false,
     vibe:'一河隔开两个世界：北岸烧着的丹霞，南岸安静的白桦。',
     must:['必看','一道桥观景台 · 日落前一小时颜色最烈'],
     chips:[['','日落场'],['down','正午白晃别去']],
     q:'五彩滩',pt:[314,48]},
   conns:[{mode:'drive',conn:'布尔津 → 五彩滩 · 24 km · 35 分',min:35,km:24,cost:0},
          {mode:'drive',conn:'返布尔津河堤 · 24 km · 35 分',min:35,km:24,cost:0}],
   profile:'地质奇观控'},
 baihaba:{day:3, afterK:'sanwan', label:'D4', brief:'喀纳斯换区间往返 · 需边防证 · 约 80 分 · ¥130',
   stop:{k:'baihaba',name:'白哈巴村',era:'西北第一村',dur:80,prio:2,cost:130,cat:'tix',indoor:false,
     vibe:'再往西就是国境线，木屋比禾木更旧更静。',
     must:['必看','界碑观景台 · 村口白桦道'],
     chips:[['down','需边防证'],['','票含区间']],
     q:'白哈巴村',pt:[252,28]},
   conns:[{mode:'shuttle',conn:'喀纳斯换区间 ＋ 边防检查 · 70 分',min:70,cost:0},
          {mode:'shuttle',conn:'返喀纳斯 · 60 分',min:60,cost:0}],
   profile:'边境村寨控'}
};
const inserted=new Set();
const tastes=new Set();
const checked=new Set();
const newMods=()=>({off:0,rain:false,pinned:new Set(),skip:new Set(),done:null});
var sels={}, selsM=new Set();                  /* 引擎共享状态 */
var DAYS=[], LODGES=[], CLUSTER=null, INSERTS={};
var addP=()=>{};
let mods=[], active=0, resolved=[], drawn=0, curDays=10;  /* UI 状态 */

/* ========== 新疆 8 / 12 天：同一套站点积木，换拼法 ========== */
const _cd=(d,p)=>Object.assign({},d,p);
const XJ8_DAYS=[XJ10_DAYS[0],XJ10_DAYS[1],XJ10_DAYS[2],XJ10_DAYS[3],
 _cd(XJ10_DAYS[5],{tab:'D5',sub:'380 km · 驾驶约 5 h · 重',start:600,
   pre:{mode:'drive',conn:'贾登峪 → 乌尔禾 · 380 km · 约 5 小时',min:300,km:380,cost:0,
     via:'沿途 · 布尔津加满油 · 克拉玛依段侧风大 · 中途换驾一次'},
   stops:XJ10_DAYS[5].stops.slice(2)}),
 _cd(XJ10_DAYS[6],{tab:'D6'}),
 _cd(XJ10_DAYS[8],{tab:'D7',sub:'380 km · 驾驶约 5.2 h · 中',
   pre:{mode:'drive',conn:'赛里木湖 → 那拉提 · 380 km · 约 5 小时 10 分',min:310,km:380,cost:45,
     via:'沿途 · 果子沟大桥观景台停 20 分 · 出景区直接上桥'}}),
 _cd(XJ10_DAYS[9],{tab:'D8'})];
const XJ8_LODGES=[XJ10_LODGES[0],XJ10_LODGES[1],XJ10_LODGES[2],XJ10_LODGES[3],
 XJ10_LODGES[5],XJ10_LODGES[6],XJ10_LODGES[8],null];

const XJ_HEMU_TREK={tab:'D6',name:'禾木 · 徒步日',sub:'村内徒步 · 极轻',start:600,hardEnd:1320,drive:'0 h',
 pre:null,post:{mode:'walk',conn:'步行回木屋 · 20 分',min:20,cost:0},
 stops:[
 {k:'hemu-trek',name:'禾木河谷 · 半日徒步',cng:'最美古镇',era:'白桦林线 8 km',dur:0,openUntil:1140,openMin:150,openMax:300,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'不赶路的一天，把村子四周的河谷走透。',
  must:['必看','美丽峰方向的河湾 · 桦林里的牛铃声'],
  chips:[['up','免票'],['','带路餐']],q:'禾木村'},
 {mode:'walk',conn:'步行上观景台 · 25 分',min:25,cost:0},
 XJ10_DAYS[4].stops[2]]};
const XJ_BYBL_DAY={tab:'D11',name:'巴音布鲁克',sub:'85 km 独库中段 · 轻',start:600,hardEnd:1320,drive:'1.8 h',
 pre:{mode:'drive',conn:'那拉提 → 巴音布鲁克 · 85 km · 约 1 小时 50 分',min:110,km:85,cost:0,
   via:'沿途 · 独库中段同窗口开放 · 巴音郭楞乡加油'},
 post:{mode:'shuttle',conn:'区间车返镇 · 40 分',min:40,cost:0},
 stops:[
 {k:'jiuqu',name:'九曲十八弯 · 日落',cng:'最美湿地',era:'开都河湿地',dur:0,openUntil:1290,openMin:120,openMax:230,prio:0,cost:145,cat:'tix',indoor:false,earliest:1050,
  vibe:'太阳落进河湾，九个太阳同时亮起来。',
  must:['必看','2 号观景台等 21:30 · 高台风大裹紧'],
  chips:[['','票含区间'],['','日落场']],q:'巴音布鲁克九曲十八弯'}]};
const XJ12_DAYS=[...XJ10_DAYS.slice(0,5),XJ_HEMU_TREK,
 _cd(XJ10_DAYS[5],{tab:'D7'}),_cd(XJ10_DAYS[6],{tab:'D8'}),
 _cd(XJ10_DAYS[7],{tab:'D9'}),_cd(XJ10_DAYS[8],{tab:'D10'}),
 XJ_BYBL_DAY,
 _cd(XJ10_DAYS[9],{tab:'D12',sub:'470 km · 驾驶约 7.5 h · 重',
   pre:{mode:'drive',conn:'独库北段 · 巴音布鲁克 → 独山子 · 220 km · 约 4 小时 50 分',min:290,km:220,cost:0,
     via:'沿途 · 哈希勒根达坂 · 全程区间测速',
     alt:{conn:'独库管制 · 绕行 G218 经和静 · 420 km · 约 5 小时 30 分',min:330,km:420,cost:55,
       via:'沿途 · 和静县城午餐加油'}}})];
const XJ12_LODGES=[...XJ10_LODGES.slice(0,5),XJ10_LODGES[4],...XJ10_LODGES.slice(5,9),
 {city:'巴音布鲁克镇',price:380,why:'镇中心 · 明早直上独库北段',q:'巴音布鲁克镇'},null];

const XJ_NODES=[
 {n:'乌鲁木齐',x:552,y:234,lx:14,ly:4,a:'start'},
 {n:'富蕴',x:505,y:88,lx:13,ly:4,a:'start'},
 {n:'布尔津',x:322,y:58,lx:-2,ly:-12,a:'middle'},
 {n:'喀纳斯',x:218,y:40,lx:-11,ly:4,a:'end'},
 {n:'禾木',x:295,y:92,lx:12,ly:12,a:'start'},
 {n:'乌尔禾',x:300,y:168,lx:12,ly:4,a:'start'},
 {n:'赛里木湖',x:92,y:196,lx:-2,ly:-12,a:'middle'},
 {n:'伊宁',x:128,y:252,lx:0,ly:17,a:'middle'},
 {n:'那拉提',x:312,y:258,lx:0,ly:17,a:'middle'},
 {n:'巴音布鲁克',x:356,y:284,lx:13,ly:4,a:'start'}];

/* ========== 青甘大环线 8 天 ========== */
const QG_DAYS=[
{tab:'D1',name:'西宁',sub:'提车 · 塔尔寺 55 km',start:600,hardEnd:1320,drive:'1.5 h',
 pre:null,post:{mode:'drive',conn:'回市区住处 · 3 km · 10 分',min:10,km:3,cost:0},
 stops:[
 {k:'qg-pickup',name:'西宁提车 · 验车',era:'租车站',dur:45,prio:0,cost:0,cat:'tix',indoor:true,
  vibe:'大环线的钥匙，先拿稳。',must:['必做','绕车拍视频 · 查备胎 · 记油位'],chips:[['up','SUV 建议']],q:'西宁 租车'},
 {mode:'drive',conn:'→ 塔尔寺 · 28 km · 45 分',min:45,km:28,cost:0},
 {k:'taersi',name:'塔尔寺',era:'黄教六大寺',dur:120,prio:1,cost:70,cat:'tix',indoor:false,
  vibe:'酥油花、壁画与堆绣，先把心放慢。',must:['必看','大金瓦殿 · 全程顺时针走'],chips:[['','肃穆场合']],q:'塔尔寺'},
 {mode:'drive',conn:'回市区 · 26 km · 40 分',min:40,km:26,cost:0},
 {k:'mojia',name:'莫家街夜市',era:'老街',dur:0,openUntil:1320,openMin:90,openMax:150,prio:2,cost:68,cat:'food',indoor:false,
  vibe:'酿皮、老酸奶、羊肠面，一条街吃到饱。',must:['必吃','马忠酿皮 · 老酸奶'],chips:[['','夜市']],q:'西宁莫家街'}]},
{tab:'D2',name:'青海湖',sub:'220 km · 驾驶约 3.7 h · 轻',start:600,hardEnd:1305,drive:'3.7 h',
 pre:{mode:'drive',conn:'西宁 → 青海湖南线 · 150 km · 约 2 小时 30 分',min:150,km:150,cost:35,
   via:'沿途 · 日月山垭口停 15 分 · 倒淌河加油'},
 post:{mode:'drive',conn:'→ 黑马河住处 · 4 km · 10 分',min:10,km:4,cost:0},
 stops:[
 {k:'qhlake',name:'青海湖 · 湖边牧场',cng:'最美湖泊',era:'免票下水位',dur:0,openUntil:1080,openMin:60,openMax:150,prio:1,cost:20,cat:'tix',indoor:false,
  vibe:'不进景区，找一段牧民的湖岸走到水边。',must:['必看','湖水和油菜花田的分界线'],chips:[['up','人少'],['','留 ¥20 过路钱']],q:'青海湖'},
 {mode:'drive',conn:'环湖西路 · 70 km · 70 分',min:70,km:70,cost:0,via:'沿途 · 想停就停，别压草场'},
 {k:'heimahe',name:'黑马河 · 日落',cng:'最美湖泊',era:'湖西岸',dur:0,openUntil:1260,openMin:60,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'整片湖替太阳收场。',must:['必看','日落后 20 分钟的紫色湖面'],chips:[['up','免票'],['','夜里 5°C']],q:'黑马河'}]},
{tab:'D3',name:'茶卡 · 大柴旦',sub:'426 km · 驾驶约 5.8 h · 重',start:570,hardEnd:1305,drive:'5.8 h',
 pre:{mode:'drive',conn:'黑马河 → 茶卡 · 80 km · 约 1 小时 20 分',min:80,km:80,cost:0,via:'沿途 · 橡皮山垭口 3,817 m 缓行'},
 post:{mode:'drive',conn:'→ 大柴旦镇 · 6 km · 12 分',min:12,km:6,cost:0},
 stops:[
 {k:'chaka',name:'茶卡盐湖',era:'天空之镜',dur:150,prio:0,cost:94,cat:'tix',indoor:false,
  vibe:'白到发蓝的一面镜子，赤脚下盐滩。',must:['必看','小火车坐到湖心 · 备拖鞋擦脚布'],chips:[['','票含小火车'],['','正午反光最强']],q:'茶卡盐湖'},
 {mode:'drive',conn:'茶卡 → 大柴旦 · 340 km · 约 4 小时 20 分',min:260,km:340,cost:45,
  via:'沿途 · 德令哈午餐加油 · 全程区间测速'},
 {k:'feicui',name:'翡翠湖 · 黄昏',era:'盐湖群',dur:0,openUntil:1260,openMin:60,openMax:120,prio:2,cost:0,cat:'free',indoor:false,
  vibe:'一格一格的绿宝石色盐池。',must:['必看','高处俯拍色块分界'],chips:[['up','免票']],q:'大柴旦翡翠湖'}]},
{tab:'D4',name:'敦煌',sub:'357 km · 驾驶约 5.2 h · 重',start:570,hardEnd:1380,drive:'5.2 h',
 pre:{mode:'drive',conn:'大柴旦 → 敦煌 · 340 km · 约 5 小时',min:300,km:340,cost:40,
   via:'沿途 · 当金山垭口 · 阿克塞加油'},
 post:{mode:'drive',conn:'回市区住处 · 6 km · 15 分',min:15,km:6,cost:0},
 stops:[
 {k:'dh-rest',name:'敦煌 · 进店休整',era:'避午晒',dur:0,openUntil:1000,openMin:45,prio:2,cost:0,cat:'free',indoor:true,
  vibe:'把正午交给房间，鸣沙山属于黄昏。',must:['必做','补水补电 · 17 点前别进沙漠'],chips:[['up','避暑']],q:'敦煌'},
 {mode:'drive',conn:'→ 鸣沙山 · 6 km · 15 分',min:15,km:6,cost:0},
 {k:'mingsha',name:'鸣沙山月牙泉 · 黄昏场',cng:'最美沙漠',era:'沙漠日落',dur:180,prio:0,cost:110,cat:'tix',indoor:false,earliest:1020,
  vibe:'爬上沙脊看月牙泉点灯。',must:['必看','东沙梁看日落 · 光脚下山最快'],chips:[['','门票三日有效'],['','鞋套 ¥15 自选']],q:'鸣沙山月牙泉'},
 {mode:'drive',conn:'→ 沙洲夜市 · 5 km · 12 分',min:12,km:5,cost:0},
 {k:'qg-night',id:'qg-night',prio:1,cat:'food',optLabel:'敦煌晚饭 · 选一家',
  opts:[
  {name:'沙洲夜市 · 烤肉套',era:'夜市',dur:90,cost:98,indoor:false,vibe:'红柳枝烤肉配杏皮水。',
   must:['必点','红柳烤肉 · 杏皮水'],chips:[['','夜市']],why:'到敦煌的仪式感',q:'沙洲夜市'},
  {name:'驴肉黄面 · 老店',era:'巷内',dur:60,cost:45,indoor:true,vibe:'一碗面解决，省出的钱给门票。',
   must:['必点','驴肉黄面 · 凉拌驴肉小份'],chips:[['','快'],['','省']],why:'省 ¥53 · 快 30 分',profile:'路上省着花',q:'敦煌 驴肉黄面'}]}]},
{tab:'D5',name:'莫高窟 · 嘉峪关',sub:'399 km · 驾驶约 5.2 h · 重',start:540,hardEnd:1290,drive:'5.2 h',
 pre:{mode:'drive',conn:'→ 莫高窟数字中心 · 25 km · 30 分',min:30,km:25,cost:0,via:'沿途 · 提前 30 分到场检票'},
 post:{mode:'drive',conn:'→ 关城边住处 · 4 km · 10 分',min:10,km:4,cost:0},
 stops:[
 {k:'mogao',name:'莫高窟 · A 类票',era:'千年石窟',dur:180,prio:0,cost:238,cat:'tix',indoor:true,dep:{first:555,every:30,last:900},
  vibe:'两部球幕电影之后，走进真正的洞窟。',must:['必看','跟紧讲解员 · 窟内禁拍'],
  chips:[['down','需提前官网预约'],['','按批次进场']],q:'莫高窟'},
 {mode:'drive',conn:'敦煌 → 嘉峪关 · 370 km · 约 4 小时 40 分',min:280,km:370,cost:55,
  via:'沿途 · 瓜州服务区加油 · 风区侧风注意'},
 {k:'jiayuguan',name:'嘉峪关关城',era:'天下第一雄关',dur:90,prio:1,cost:110,cat:'tix',indoor:false,latest:1130,
  vibe:'城楼后面就是雪山和戈壁。',must:['必看','角楼上看祁连雪线'],chips:[['','闭园前 90 分停止入场']],q:'嘉峪关关城'}]},
{tab:'D6',name:'张掖',sub:'275 km · 驾驶约 3.8 h · 中',start:600,hardEnd:1305,drive:'3.8 h',
 pre:{mode:'drive',conn:'嘉峪关 → 张掖 · 230 km · 约 3 小时',min:180,km:230,cost:40,via:'沿途 · 清水服务区加油'},
 post:{mode:'drive',conn:'→ 丹霞口住处 · 5 km · 10 分',min:10,km:5,cost:0},
 stops:[
 {k:'zy-lunch',name:'张掖 · 搓鱼子午饭',era:'本地面食',dur:60,prio:2,cost:38,cat:'food',indoor:true,
  vibe:'一碗搓鱼子垫底，下午留给丹霞。',must:['必点','搓鱼子 · 灰豆汤'],chips:[['','快']],q:'张掖 搓鱼子'},
 {mode:'drive',conn:'→ 七彩丹霞 · 40 km · 45 分',min:45,km:40,cost:0},
 {k:'danxia',name:'七彩丹霞 · 黄昏场',cng:'最美丹霞',era:'彩色丘陵',dur:150,prio:0,cost:75,cat:'tix',indoor:false,earliest:1050,
  vibe:'太阳越低，山越红。',must:['必看','4 号观景台收官 · 区间车末班 21:00'],chips:[['','票含区间'],['','日落场']],q:'张掖七彩丹霞'}]},
{tab:'D7',name:'祁连',sub:'208 km · 驾驶约 3.5 h · 中',start:600,hardEnd:1290,drive:'3.5 h',
 pre:{mode:'drive',conn:'张掖 → 祁连 · 200 km · 约 3 小时 20 分',min:200,km:200,cost:0,
   via:'沿途 · 扁都口风光带随停随走'},
 post:{mode:'drive',conn:'→ 县城住处 · 3 km · 8 分',min:8,km:3,cost:0},
 stops:[
 {k:'zhuoer',name:'卓尔山',era:'东方小瑞士',dur:150,prio:0,cost:60,cat:'tix',indoor:false,
  vibe:'红色丹霞顶着绿草甸，对面是牛心山雪顶。',must:['必看','西观景台看祁连县全景'],chips:[['','海拔 3,100 m 慢走']],q:'卓尔山'},
 {mode:'drive',conn:'→ 县城 · 5 km · 10 分',min:10,km:5,cost:0},
 {k:'qilian-pot',name:'祁连 · 牦牛肉汤锅',era:'县城老店',dur:80,prio:2,cost:88,cat:'food',indoor:true,
  vibe:'高原的晚上要一锅热的。',must:['必点','牦牛肉汤锅 · 青稞饼'],chips:[['','暖']],q:'祁连县 牦牛肉'}]},
{tab:'D8',name:'回西宁 · 还车',sub:'280 km · 驾驶约 4.3 h · 中',start:570,hardEnd:1200,drive:'4.3 h',
 pre:{mode:'drive',conn:'祁连 → 西宁 · 280 km · 约 4 小时 20 分',min:260,km:280,cost:45,
   via:'沿途 · 门源观景台停 20 分 · 达坂山隧道'},
 post:null,
 stops:[
 {k:'qg-return',name:'还车 · 西宁',era:'满油交车',dur:45,prio:0,cost:0,cat:'tix',indoor:true,
  vibe:'大环画圆。',must:['必做','满油 · 对公里数 · 验车拍视频'],chips:[['','留足 45 分']],q:'西宁 租车还车'}]}];
const QG_LODGES=[
 {city:'西宁 · 力盟街区',price:280,why:'夜市步行圈 · 明早出城顺',q:'西宁力盟'},
 {opts:[{city:'黑马河 · 湖景房',price:320,why:'开窗就是日出位',q:'黑马河'},
        {city:'黑马河 · 院子房',price:240,why:'省 ¥40/人 · 步行 5 分到湖',q:'黑马河'}]},
 {city:'大柴旦镇',price:300,why:'镇上补给最全的一家',q:'大柴旦'},
 {city:'敦煌 · 沙洲夜市旁',price:380,why:'夜市步行 3 分 · 鸣沙山 15 分车程',q:'敦煌沙洲夜市'},
 {city:'嘉峪关关城边',price:300,why:'明早出发直上高速',q:'嘉峪关'},
 {city:'张掖 · 丹霞口',price:320,why:'看完日落 10 分钟到床',q:'张掖丹霞口'},
 {city:'祁连县城',price:280,why:'牦牛汤锅楼下',q:'祁连县'},
 null];
const QG_NODES=[
 {n:'西宁',x:560,y:240,lx:13,ly:4,a:'start'},
 {n:'黑马河',x:430,y:252,lx:0,ly:17,a:'middle'},
 {n:'大柴旦',x:230,y:160,lx:0,ly:-12,a:'middle'},
 {n:'敦煌',x:92,y:78,lx:12,ly:4,a:'start'},
 {n:'嘉峪关',x:252,y:66,lx:0,ly:-12,a:'middle'},
 {n:'张掖',x:392,y:96,lx:12,ly:4,a:'start'},
 {n:'祁连',x:472,y:162,lx:12,ly:4,a:'start'}];

/* ========== 川西小环线 5 天 ========== */
const CX_DAYS=[
{tab:'D1',name:'成都 → 日隆',sub:'232 km 翻巴朗山 · 中',start:570,hardEnd:1290,drive:'4.3 h',
 pre:null,post:{mode:'drive',conn:'→ 日隆镇住处 · 2 km · 5 分',min:5,km:2,cost:0},
 stops:[
 {k:'cx-pickup',name:'成都提车 · 验车',era:'租车站',dur:45,prio:0,cost:0,cat:'tix',indoor:true,
  vibe:'上高原前，先把车况摸清。',must:['必做','绕车拍视频 · 查防冻液 · 记油位'],chips:[['up','SUV 建议']],q:'成都 租车'},
 {mode:'drive',conn:'成都 → 日隆 · 230 km · 约 4 小时 10 分',min:250,km:230,cost:45,
  via:'沿途 · 映秀出高速 · 巴朗山隧道 3,850 m 缓行防高反'},
 {k:'maobiliang',name:'猫鼻梁 · 四姑娘全景',era:'国道观景台',dur:45,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'四座雪峰第一次整队亮相。',must:['必看','黄昏侧光下的幺妹峰'],chips:[['up','免票'],['','海拔 3,400 m 慢走']],q:'猫鼻梁观景台'}]},
{tab:'D2',name:'双桥沟',sub:'沟内观光车 · 轻',start:570,hardEnd:1290,drive:'0.5 h',
 pre:{mode:'drive',conn:'→ 双桥沟游客中心 · 8 km · 15 分',min:15,km:8,cost:0},
 post:{mode:'drive',conn:'回日隆镇 · 8 km · 15 分',min:15,km:8,cost:0},
 stops:[
 {k:'shuangqiao',name:'双桥沟 · 观光车全线',era:'雪山峡谷',dur:300,prio:0,cost:150,cat:'tix',indoor:false,dep:{first:570,every:30,last:960},
  vibe:'车到红杉林，雪山贴着车窗走。',must:['必看','四姑娘山观景平台 · 撵鱼坝栈道走一段'],
  chips:[['','票含观光车'],['','按班次进沟']],q:'四姑娘山双桥沟'}]},
{tab:'D3',name:'丹巴',sub:'118 km · 驾驶约 2.8 h · 轻',start:600,hardEnd:1305,drive:'2.8 h',
 pre:{mode:'drive',conn:'日隆 → 丹巴 · 110 km · 约 2 小时 30 分',min:150,km:110,cost:0,
   via:'沿途 · 小金河谷 · 落石段勿停车'},
 post:{mode:'drive',conn:'→ 县城住处 · 6 km · 15 分',min:15,km:6,cost:0},
 stops:[
 {k:'jiaju',name:'甲居藏寨',cng:'最美古镇',era:'千碉之国',dur:150,prio:0,cost:50,cat:'tix',indoor:false,
  vibe:'白色藏房撒在整面山坡上。',must:['必看','2 号观景台 · 进寨喝碗酥油茶'],chips:[['','盘山窄路会车慢']],q:'甲居藏寨'},
 {mode:'drive',conn:'回县城 · 8 km · 20 分',min:20,km:8,cost:0},
 {k:'cx-dinner',id:'cx-dinner',prio:2,cat:'food',optLabel:'丹巴晚饭 · 选一家',
  opts:[
  {name:'藏家宴 · 石锅鸡',era:'院子座',dur:90,cost:88,indoor:true,vibe:'坐进藏家院子吃一顿正经的。',
   must:['必点','石锅松茸鸡 · 青稞酒抿一口'],chips:[['','院子座']],why:'吃透一顿',q:'丹巴 藏家乐'},
  {name:'牛肉面馆',era:'街边',dur:45,cost:38,indoor:true,vibe:'一碗面收工，早点休息。',
   must:['必点','红烧牦牛肉面'],chips:[['','快'],['','省']],why:'省 ¥50',profile:'路上省着花',q:'丹巴 面馆'}]}]},
{tab:'D4',name:'新都桥',sub:'201 km 经八美 · 中',start:600,hardEnd:1305,drive:'3.9 h',
 pre:{mode:'drive',conn:'丹巴 → 八美 → 塔公 · 160 km · 约 3 小时',min:180,km:160,cost:0,
   via:'沿途 · 八美土石林随停 · 亚拉雪山观景台'},
 post:{mode:'drive',conn:'→ 镇上住处 · 3 km · 8 分',min:8,km:3,cost:0},
 stops:[
 {k:'tagong',name:'塔公草原 · 寺前',era:'木雅金塔',dur:75,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'金塔、草原和雅拉雪山同框。',must:['必看','寺后草坡的经幡阵'],chips:[['up','免票']],q:'塔公草原'},
 {mode:'drive',conn:'塔公 → 新都桥 · 38 km · 50 分',min:50,km:38,cost:0},
 {k:'xdq-light',name:'新都桥 · 光影长廊',era:'摄影天堂',dur:0,openUntil:1260,openMin:60,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'白杨、溪流、藏房，等光把它们镀一遍金。',must:['必看','日落前一小时的斜射光'],chips:[['up','免票']],q:'新都桥'}]},
{tab:'D5',name:'折多山 → 还车',sub:'392 km · 驾驶约 5.5 h · 重',start:540,hardEnd:1260,drive:'5.5 h',
 pre:{mode:'drive',conn:'新都桥 → 折多山垭口 · 35 km · 约 50 分',min:50,km:35,cost:0,
   via:'沿途 · 垭口 4,298 m 慢行防高反'},
 post:null,
 stops:[
 {k:'zheduo',name:'折多山垭口',era:'康巴第一关',dur:30,prio:2,cost:0,cat:'free',indoor:false,
  vibe:'翻过这座山，就从高原回到盆地。',must:['必看','观景台回望贡嘎方向'],chips:[['up','免票'],['down','高反者车内远观']],q:'折多山垭口'},
 {mode:'drive',conn:'折多山 → 成都 · 355 km · 约 4 小时 40 分',min:280,km:355,cost:85,
  via:'沿途 · 康定下高原 · 泸定服务区加油 · 雅康高速隧道群'},
 {k:'cx-return',name:'还车 · 成都',era:'满油交车',dur:45,prio:0,cost:0,cat:'tix',indoor:true,
  vibe:'五天小环画圆。',must:['必做','满油 · 对公里数 · 验车拍视频'],chips:[['','留足 45 分']],q:'成都 租车还车'}]}];
const CX_LODGES=[
 {city:'日隆镇',price:380,why:'猫鼻梁 10 分钟 · 明早进沟顺',q:'日隆镇'},
 {city:'日隆镇 · 连住',price:380,why:'不挪窝 · 行李不动',q:'日隆镇'},
 {city:'丹巴县城',price:360,why:'河边一排 · 晚饭步行圈',q:'丹巴'},
 {opts:[{city:'新都桥 · 观景房',price:420,why:'窗外就是光影长廊',q:'新都桥'},
        {city:'新都桥 · 普通房',price:320,why:'省 ¥50/人 · 步行 8 分到机位',q:'新都桥'}]},
 null];
const CX_NODES=[
 {n:'成都',x:560,y:232,lx:13,ly:4,a:'start'},
 {n:'日隆',x:392,y:150,lx:12,ly:-8,a:'start'},
 {n:'丹巴',x:232,y:96,lx:-2,ly:-12,a:'middle'},
 {n:'新都桥',x:150,y:214,lx:0,ly:17,a:'middle'}];

/* ========== 滇西北 6 天 ========== */
const DXB_DAYS=[
{tab:'D1',name:'大理',sub:'提车 · 古城＋才村 · 轻',start:600,hardEnd:1320,drive:'0.5 h',
 pre:null,post:{mode:'drive',conn:'→ 古城边住处 · 3 km · 10 分',min:10,km:3,cost:0},
 stops:[
 {k:'db-pickup',name:'大理提车 · 验车',era:'租车站',dur:45,prio:0,cost:0,cat:'tix',indoor:true,
  vibe:'环洱海前把车验清爽。',must:['必做','绕车拍视频 · 记油位'],chips:[['up','小车即可']],q:'大理 租车'},
 {mode:'drive',conn:'→ 大理古城 · 14 km · 25 分',min:25,km:14,cost:0},
 {k:'dali-old',name:'大理古城 · 慢逛',era:'南门进',dur:0,openUntil:1140,openMin:90,openMax:180,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'先把节奏降到洱海的速度。',must:['必看','人民路一路往下 · 洋人街喝一杯'],chips:[['up','免票']],q:'大理古城'},
 {mode:'drive',conn:'→ 才村码头 · 5 km · 12 分',min:12,km:5,cost:0},
 {k:'caicun',name:'才村码头 · 日落',era:'洱海西岸',dur:0,openUntil:1260,openMin:60,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'苍山在背后，海在脚下。',must:['必看','栈道尽头的落日'],chips:[['up','免票']],q:'才村码头'}]},
{tab:'D2',name:'环洱海 → 双廊',sub:'环湖 132 km · 中',start:570,hardEnd:1305,drive:'3 h',
 pre:{mode:'drive',conn:'古城 → 环海西路 · 8 km · 15 分',min:15,km:8,cost:0},
 post:{mode:'walk',conn:'步行进双廊住处 · 8 分',min:8,cost:0},
 stops:[
 {k:'erhai-loop',name:'环洱海 · 顺时针',era:'湖周精华段',dur:240,km:112,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'喜洲、海舌、小普陀，想停就停。',must:['必看','海舌公园步道 · 小普陀回望'],
  chips:[['up','免票'],['','网红位限停 10 分']],q:'环海西路'},
 {mode:'drive',conn:'挖色 → 双廊 · 12 km · 20 分',min:20,km:12,cost:0},
 {k:'dl-chill',name:'双廊 · 海边躺平',era:'客栈露台',dur:0,openUntil:1075,openMin:60,prio:2,cost:0,cat:'free',indoor:false,
  vibe:'下午的洱海只干一件事：什么都不干。',must:['必做','找个临水位晒背'],chips:[['up','免票']],q:'双廊'},
 {mode:'walk',conn:'步行 · 5 分',min:5,cost:0},
 {k:'db-dinner',id:'db-dinner',prio:1,cat:'food',optLabel:'双廊晚饭 · 选一家',
  opts:[
  {name:'海景酸辣鱼',era:'临水位',dur:90,cost:128,indoor:false,vibe:'洱海鱼配洱海日落。',
   must:['必点','酸辣鱼 · 海菜芋头汤'],chips:[['','临水位']],why:'到双廊的理由',q:'双廊 酸辣鱼'},
  {name:'白族小馆',era:'巷内',dur:60,cost:58,indoor:true,vibe:'生皮乳扇尝个鲜，省出的给客栈。',
   must:['必点','乳扇 · 破酥粑粑'],chips:[['','快'],['','省']],why:'省 ¥70',profile:'路上省着花',q:'双廊 白族菜'}]}]},
{tab:'D3',name:'丽江',sub:'180 km · 驾驶约 3 h · 轻',start:600,hardEnd:1320,drive:'3 h',
 pre:{mode:'drive',conn:'双廊 → 丽江 · 180 km · 约 3 小时',min:180,km:180,cost:55,
   via:'沿途 · 大丽高速 · 上关服务区加油'},
 post:{mode:'walk',conn:'步行回客栈 · 10 分',min:10,cost:0},
 stops:[
 {k:'lj-old',name:'丽江古城 · 四方街',cng:'最美古镇',era:'水巷',dur:0,openUntil:1170,openMin:90,openMax:180,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'顺着水声走就不会迷路。',must:['必看','大石桥 · 现打铜器铺'],chips:[['up','免票']],q:'丽江古城'},
 {mode:'walk',conn:'步行上山 · 15 分',min:15,cost:0},
 {k:'lion-hill',name:'狮子山 · 万古楼日落',era:'古城制高点',dur:90,prio:0,cost:50,cat:'tix',indoor:false,
  vibe:'整片灰瓦屋顶被落日点亮。',must:['必看','顶层西侧栏杆位 · 等亮灯'],chips:[['','日落场']],q:'万古楼'}]},
{tab:'D4',name:'虎跳峡 → 香格里拉',sub:'193 km · 驾驶约 3.7 h · 中',start:570,hardEnd:1305,drive:'3.7 h',
 pre:{mode:'drive',conn:'丽江 → 上虎跳 · 80 km · 约 1 小时 40 分',min:100,km:80,cost:30,
   via:'沿途 · 长江第一湾观景台停 15 分'},
 post:{mode:'walk',conn:'步行进古城住处 · 10 分',min:10,cost:0},
 stops:[
 {k:'hutiao',name:'上虎跳 · 峡谷栈道',cng:'最美峡谷',era:'金沙江',dur:100,prio:0,cost:45,cat:'tix',indoor:false,
  vibe:'江水在虎跳石上炸开。',must:['必看','栈道下到江边平台 · 水声里喊一嗓'],chips:[['','台阶 800 级 · 护膝']],q:'虎跳峡上虎跳'},
 {mode:'drive',conn:'虎跳峡 → 独克宗 · 110 km · 约 2 小时',min:120,km:110,cost:25,
  via:'沿途 · 小中甸花海季随停'},
 {k:'dukezong',name:'独克宗古城 · 转经',era:'月光城',dur:0,openUntil:1230,openMin:60,openMax:120,prio:2,cost:0,cat:'free',indoor:false,
  vibe:'把世界最大的转经筒推一圈。',must:['必看','龟山公园大转经筒 · 三人才推得动'],
  chips:[['up','免票'],['','海拔 3,300 m 慢走']],q:'独克宗古城'}]},
{tab:'D5',name:'普达措 · 松赞林',sub:'区间车进园 · 轻',start:570,hardEnd:1290,drive:'1.5 h',
 pre:{mode:'drive',conn:'→ 普达措游客中心 · 25 km · 40 分',min:40,km:25,cost:0},
 post:{mode:'drive',conn:'回古城住处 · 25 km · 40 分',min:40,km:25,cost:0},
 stops:[
 {k:'pudacuo',name:'普达措 · 属都湖线',era:'高原湖',dur:240,prio:0,cost:138,cat:'tix',indoor:false,dep:{first:570,every:30,last:900},
  vibe:'木栈道贴着湖走，松萝挂满冷杉。',must:['必看','属都湖环湖栈道走全 · 留意小松鼠'],
  chips:[['','票含区间车'],['','按班次进园']],q:'普达措国家公园'},
 {mode:'drive',conn:'→ 松赞林寺 · 18 km · 30 分',min:30,km:18,cost:0},
 {k:'songzanlin',name:'松赞林寺',era:'小布达拉',dur:100,prio:1,cost:90,cat:'tix',indoor:false,latest:1140,
  vibe:'金顶在高原光里晃眼。',must:['必看','拉姆央措湖倒影位'],chips:[['','含摆渡车']],q:'松赞林寺'}]},
{tab:'D6',name:'回丽江 · 还车',sub:'175 km · 驾驶约 3 h · 轻',start:600,hardEnd:1230,drive:'3 h',
 pre:{mode:'drive',conn:'香格里拉 → 丽江 · 175 km · 约 2 小时 50 分',min:170,km:175,cost:55,
   via:'沿途 · 金沙江沿线 · 拉市海口加油'},
 post:null,
 stops:[
 {k:'db-return',name:'还车 · 丽江',era:'满油交车',dur:45,prio:0,cost:0,cat:'tix',indoor:true,
  vibe:'滇西北一线画完。',must:['必做','满油 · 对公里数 · 验车拍视频'],chips:[['','留足 45 分']],q:'丽江 租车还车'}]}];
const DXB_LODGES=[
 {city:'大理古城边',price:300,why:'南门步行 5 分',q:'大理古城'},
 {opts:[{city:'双廊 · 海景房',price:420,why:'床头就是洱海日出',q:'双廊'},
        {city:'双廊 · 巷内房',price:300,why:'省 ¥60/人 · 步行 3 分到海边',q:'双廊'}]},
 {city:'丽江古城客栈',price:340,why:'四方街步行圈',q:'丽江古城'},
 {city:'独克宗古城客栈',price:360,why:'转经筒脚下 · 有供氧',q:'独克宗古城'},
 {city:'独克宗 · 连住',price:360,why:'不挪窝 · 行李不动',q:'独克宗古城'},
 null];
const DXB_NODES=[
 {n:'大理',x:500,y:248,lx:13,ly:4,a:'start'},
 {n:'双廊',x:544,y:168,lx:12,ly:4,a:'start'},
 {n:'丽江',x:372,y:120,lx:0,ly:-12,a:'middle'},
 {n:'香格里拉',x:200,y:62,lx:12,ly:4,a:'start'}];

/* ========== 香港周末 3 天（地铁·渡轮·缆车 · 班次同机制） ========== */
const HK_DAYS=[
{tab:'D1',name:'中环 · 上环',sub:'地铁＋叮叮车＋渡轮 · 轻',start:600,hardEnd:1350,drive:'—',
 pre:{mode:'metro',conn:'地铁 · 佐敦 → 中环 · 14 分',min:14,cost:10,via:'沿途 · 荃湾线过海'},
 post:{mode:'ferry',conn:'天星小轮 · 中环 → 尖沙咀 · 12 分 · 约 12 分一班',min:12,cost:5,
   dep:{first:440,every:12,last:1410},via:'沿途 · 上层右舷看岛侧天际线'},
 stops:[
 {k:'taikwun',name:'大馆',era:'前中区警署',dur:100,prio:1,cost:0,cat:'tix',indoor:true,
  vibe:'监狱操场改成了美术馆院子。',must:['必看','B 仓监仓复原 · 检阅广场'],chips:[['up','免费'],['','展览另购']],q:'Tai Kwun Hong Kong'},
 {mode:'walk',conn:'步行 · 荷李活道 · 8 分',min:8,cost:0},
 {k:'manmo',name:'文武庙',era:'1847',dur:30,prio:2,cost:0,cat:'free',indoor:true,
  vibe:'塔香从房梁垂下来，光柱里全是烟。',must:['必看','门口回望摩天楼夹古庙'],chips:[['up','免费']],q:'Man Mo Temple Hong Kong'},
 {mode:'walk',conn:'步行 · 摩罗上街 · 6 分',min:6,cost:0},
 {k:'hk-tea',id:'hk-tea',prio:1,cat:'food',optLabel:'下午这顿 · 选一家',
  opts:[
  {name:'陆羽茶室 · 港式饮茶',era:'1933',dur:90,cost:130,indoor:true,vibe:'老侍应、铜壶与虾饺，慢慢叹。',
   must:['必点','虾饺 · 叉烧包 · 普洱'],chips:[['','老字号']],why:'到香港的仪式感',q:'Luk Yu Tea House'},
  {name:'兰芳园 · 茶记',era:'丝袜奶茶创始',dur:45,cost:48,indoor:true,vibe:'一杯奶茶一份捞丁，快而准。',
   must:['必点','丝袜奶茶 · 葱油鸡扒捞丁'],chips:[['','快'],['','省']],why:'省 ¥82 · 快 45 分',profile:'路上省着花',q:'Lan Fong Yuen Central'}]},
 {mode:'tram',conn:'叮叮车 · 上环 → 中环码头 · 15 分',min:15,cost:3,via:'沿途 · 坐二层最前排'},
 {k:'pier-dusk',name:'中环码头 · 黄昏',cng:'最美海岸',era:'维港西望',dur:0,openUntil:1200,openMin:45,prio:2,cost:0,cat:'free',indoor:false,
  vibe:'渡轮进进出出，对岸灯一盏盏亮。',must:['必看','7 号码头天台'],chips:[['up','免费']],q:'Central Pier 7'}]},
{tab:'D2',name:'西九文化区',sub:'地铁直达 · 轻',start:600,hardEnd:1350,drive:'—',
 pre:{mode:'metro',conn:'地铁 · 佐敦 → 柯士甸 · 8 分',min:8,cost:6},
 post:{mode:'metro',conn:'地铁回佐敦 · 10 分',min:10,cost:6},
 stops:[
 {k:'mplus',name:'M+ 博物馆',era:'亚洲当代视觉文化',dur:180,prio:0,cost:110,cat:'tix',indoor:true,earliest:600,
  vibe:'一整面希克藏品墙，看到腿软。',must:['必看','希克展厅 · 天台海景'],chips:[['','周一闭馆'],['','特展另购']],q:'M+ Museum Hong Kong'},
 {mode:'walk',conn:'步行 · 海滨长廊 · 10 分',min:10,cost:0},
 {k:'artpark',name:'艺术公园 · 草坪',cng:'最美海岸',era:'维港正面',dur:0,openUntil:1170,openMin:60,openMax:120,prio:2,cost:0,cat:'free',indoor:false,
  vibe:'草坪尽头就是海，海对面就是岛。',must:['必看','买杯咖啡坐防波堤'],chips:[['up','免费']],q:'West Kowloon Art Park'},
 {mode:'metro',conn:'地铁 · 柯士甸 → 油麻地 · 6 分',min:6,cost:5},
 {k:'temple-st',name:'庙街夜市',era:'油麻地',dur:90,prio:1,cost:88,cat:'food',indoor:false,earliest:1140,
  vibe:'塑料凳、煲仔饭与霓虹灯管。',must:['必吃','煲仔饭加腊肠 · 冻柠茶'],chips:[['','夜市'],['','19 点后才热闹']],q:'Temple Street Night Market'}]},
{tab:'D3',name:'太平山 · 返程',sub:'缆车＋高铁 · 轻',start:570,hardEnd:1140,drive:'—',
 pre:{mode:'metro',conn:'地铁 · 佐敦 → 中环 · 14 分',min:14,cost:10},
 post:null,
 stops:[
 {k:'peak',name:'太平山 · 山顶缆车',era:'1888',dur:150,prio:0,cost:118,cat:'tix',indoor:false,dep:{first:570,every:15,last:1380},
  vibe:'车厢以 27 度仰角把整座城市放倒。',must:['必看','右侧座位看楼群倾斜 · 卢吉道走 20 分'],
  chips:[['','票含摩天台'],['','按班次排队']],q:'Peak Tram Lower Terminus'},
 {mode:'metro',conn:'地铁 · 中环 → 西九龙站 · 18 分',min:18,cost:12},
 {k:'hk-back',name:'西九龙站 · 高铁返程',era:'口岸',dur:45,prio:0,cost:0,cat:'tix',indoor:true,
  vibe:'一地两检，留足 45 分。',must:['必做','先过港方后过内地 · 别卡饭点'],chips:[['','提前 45 分到']],q:'Hong Kong West Kowloon Station'}]}];
const HK_LODGE={opts:[
 {city:'佐敦 · 高层房',price:880,why:'窗缝里有维港一角',q:'Jordan Hotel Hong Kong'},
 {city:'佐敦 · 标准房',price:680,why:'省 ¥100/人 · 地铁口 2 分',q:'Jordan Hotel Hong Kong'}]};
const HK_LODGES=[HK_LODGE,HK_LODGE,null];
const HK_NODES=[
 {n:'佐敦 · 住这',x:340,y:104,lx:12,ly:4,a:'start'},
 {n:'中环 · 上环',x:268,y:222,lx:0,ly:17,a:'middle'},
 {n:'西九文化区',x:186,y:138,lx:-10,ly:4,a:'end'},
 {n:'太平山',x:452,y:238,lx:12,ly:4,a:'start'}];

/* ========== 线路注册表 ========== */
function xjTodos(){
  const t=[];
  if(inserted.has('baihaba'))
    t.push({k:'permit',tag:['down','证件'],text:'边防证 · 白哈巴需要（乌市或布尔津口岸办 · 带身份证）',v:''});
  t.push({k:'car',tag:['down','租车'],text:'确认石子 / 玻璃单独险 · 备胎工具齐',v:''});
  t.push({k:'dk',tag:['','公告'],text:`${DAYS[DAYS.length-1].tab} 出发早查独库放行公告（防洪常临时管制）`,v:'更新 08-03',url:navQ('独库公路')});
  t.push({k:'lodge4',tag:['up','确认'],text:`D4 住 ${lodgeCity(3)} · 已订`,v:''});
  t.push({k:'speed',tag:['','驾驶'],text:'区间测速全程 · 车机/手机开提醒',v:''});
  t.push({k:'fuel',tag:['','纪律'],text:'低于半箱见站就加 · 北线站距最长 180 km',v:''});
  t.push({k:'coat',tag:['','装备'],text:'抓绒外套人手一件 · 昼夜温差 15°C+',v:''});
  t.push({k:'water',tag:['','补给'],text:'每车囤一箱水 ＋ 防晒',v:''});
  return t;
}
function xjThrift(){ lodge4=1;
  if('d3-night' in sels) sels['d3-night']=1;
  if('d9-grass' in sels) sels['d9-grass']=1;
  const gi=DAYS.findIndex(d=>d.stops&&d.stops.some(s=>s.k==='guanyu'));
  if(gi>=0) mods[gi].skip.add('guanyu'); }
const XJ_TASTES=[
 {id:'photo',label:'摄影晨雾',apply(){ selsM.add(2); addP('摄影晨雾党'); }},
 {id:'geo',label:'地质奇观',apply(){ inserted.add('wucai'); addP('地质奇观控'); }},
 {id:'folk',label:'边境村寨',apply(){ inserted.add('baihaba'); addP('边境村寨控'); }},
 {id:'food',label:'美食夜市',apply(){ sels['d3-night']=0; addP('夜市优先'); }}];
const xjSeasons=tag=>[
 {in:true,name:'独库公路 · 北段',why:'每年 6–10 月开放 · 现开放中',tag,ver:1},
 {in:false,name:'喀纳斯金秋',why:'白桦转黄约 9 月中旬起 · 本次未到季',pick:{key:'autumn',name:'喀纳斯金秋',ptext:'秋色控'}}];
const XJ_EXTRAS=[{ins:'wucai'},{ins:'baihaba'},
 {later:{key:'bybl',name:'巴音布鲁克 · 九曲十八弯',why:'需多住一晚 · 本天数装不下',ptext:'想看九曲日落',inDay:'巴音布鲁克',needDays:12}}];
const xjBase={name:'北疆环线',dest:'新疆 · 北疆环线',fam:'xj',
 cluster:XJ_CLUSTER,inserts:XJ_INSERTS,
 defSels:{'d3-night':0,'d9-grass':0},defSelsM:[0,1],
 perCar:true,nav:'amap',roadfood:620,strength:'中',
 carLabel:'租车 · 油费 · 路桥',tixLabel:'门票与区间车',foodLabel:'餐饮 · 含路餐',
 overTip:'可换 D4 山下住 / 河谷线 / 跳过观鱼台',
 defTasteIds:['photo','geo'],
 tastes:XJ_TASTES,thrift:xjThrift,todos:xjTodos,
 weather:'北疆 8 月 · 昼 22–31°C 夜 8–14°C · 日落约 21:30（新疆作息整体晚 2 小时）',
 extrasSub:'还没排进来的备选：玩 54 · 吃 37 · 住 41，下面是最顺路的'};

const ROUTES={
 xj8:Object.assign({},xjBase,{days:XJ8_DAYS,lodges:XJ8_LODGES,nights:7,rent:3200,
  budgets:[{l:'宽松',v:7100},{l:'精打细算',v:6300}],
  title:'🚗 北疆环线 8 天 · 四大件速通',meta:'北疆环线 · 8 天 7 晚 · 08-15 出发',
  why:'八天速通：砍掉禾木整住与伊宁河谷，保住可可托海、喀纳斯、赛里木湖与独库四大件。天天赶路，但每晚都在天黑前抵店。',
  seasons:xjSeasons('已排入 D8'),extras:XJ_EXTRAS,
  map:{nodes:XJ_NODES,order:[0,1,2,3,5,6,8],loop:true,
   seg:[null,[0,1],[1,2],[2,3],[3,5],[5,6],[6,8],[8,0]],tonight:[0,1,2,3,5,6,8,-1]}}),
 xj10:Object.assign({},xjBase,{days:XJ10_DAYS,lodges:XJ10_LODGES,nights:9,rent:4000,
  budgets:[{l:'宽松',v:8500},{l:'精打细算',v:7550}],
  title:'🚗 北疆环线 10 天 · 矿坑到草原的大回环',meta:'北疆环线 · 10 天 9 晚 · 08-15 出发',
  why:'顺时针大环：先北上阿尔泰把长途拆成两天，喀纳斯—禾木连住进山里；回程沿准噶尔西缘南下，赛里木湖—伊犁河谷收草原，最后一天走独库北段回乌市还车。每天车程压在 6.5 小时内，天黑前抵店。',
  seasons:xjSeasons('已排入 D10'),extras:XJ_EXTRAS,
  map:{nodes:XJ_NODES,order:[0,1,2,3,4,5,6,7,8],loop:true,
   seg:[null,[0,1],[1,2],[2,3],[3,4],[4,5],[5,6],[6,7],[7,8],[8,0]],tonight:[0,1,2,3,4,5,6,7,8,-1]}}),
 xj12:Object.assign({},xjBase,{days:XJ12_DAYS,lodges:XJ12_LODGES,nights:11,rent:4800,roadfood:700,
  budgets:[{l:'宽松',v:9900},{l:'精打细算',v:8800}],
  title:'🚗 北疆环线 12 天 · 徒步与九曲加宽版',meta:'北疆环线 · 12 天 11 晚 · 08-15 出发',
  why:'十二天加宽：禾木多住一晚给徒步和晨雾，独库中段进巴音布鲁克看九曲日落，最后一天独库北段收官还车。',
  seasons:xjSeasons('已排入 D12'),extras:[{ins:'wucai'},{ins:'baihaba'}],
  map:{nodes:XJ_NODES,order:[0,1,2,3,4,5,6,7,8,9],loop:true,
   seg:[null,[0,1],[1,2],[2,3],[3,4],null,[4,5],[5,6],[6,7],[7,8],[8,9],[9,0]],
   tonight:[0,1,2,3,4,4,5,6,7,8,9,-1]}}),
 qg8:{name:'青甘大环线',dest:'青甘 · 大环线',fam:'qg',days:QG_DAYS,lodges:QG_LODGES,
  cluster:null,inserts:null,defSels:{'qg-night':0},defSelsM:null,
  nights:7,rent:3000,roadfood:400,perCar:true,nav:'amap',strength:'中',
  carLabel:'租车 · 油费 · 路桥',tixLabel:'门票与区间车',foodLabel:'餐饮 · 含路餐',
  overTip:'可换黑马河院子房 / 驴肉黄面',
  budgets:[{l:'宽松',v:5950},{l:'精打细算',v:5300}],
  defTasteIds:['star','art'],
  thrift(){ lodge4=1; sels['qg-night']=1; },
  tastes:[{id:'star',label:'星空控',apply(){ addP('星空控 · 黑马河守日出'); }},
          {id:'art',label:'石窟迷',apply(){ addP('石窟迷 · 莫高窟听全讲解'); }}],
  title:'🚗 青甘大环线 8 天 · 从湖到窟',meta:'青甘环线 · 8 天 7 晚 · 08-20 出发',
  why:'顺时针小环：先湖后漠，茶卡与丹霞都压在光最好的时段，莫高窟按预约批次定 D5 的节奏，每天车程压在 5 小时上下，天黑前抵店。',
  weather:'河西走廊 8 月 · 昼 20–33°C 夜 10–16°C · 日落约 20:40',
  seasons:[{in:true,name:'莫高窟 A 类票',why:'旺季常售罄 · 提前 7 天官网抢',tag:'已排入 D5',ver:1},
   {in:false,name:'门源油菜花',why:'花期 7 月 · 本次已过季',pick:{key:'menyuan',name:'门源油菜花',ptext:'花海控'}},
   {in:false,name:'额济纳胡杨',why:'10 月上旬金黄 · 另一条线',pick:{key:'ejina',name:'额济纳胡杨',ptext:'秋色控'}}],
  extras:[{later:{key:'yadan',name:'水上雅丹',why:'单程多绕 200 km · 本次不排',ptext:'雅丹控'}},
   {later:{key:'yulin',name:'榆林窟',why:'瓜州方向单程 170 km · 需另半天',ptext:'石窟迷'}}],
  extrasSub:'备着的还有 玩 28 · 吃 19 · 住 22',todos(){ return [
   {k:'mogao',tag:['down','预约'],text:'莫高窟 A 类票 · 提前 7 天官网抢（对护照/身份证）',v:'更新 08-03',url:navQ('莫高窟参观预约售票中心')},
   {k:'car',tag:['down','租车'],text:'确认石子 / 玻璃单独险 · 备胎工具齐',v:''},
   {k:'speed',tag:['','驾驶'],text:'区间测速全程 · 车机/手机开提醒',v:''},
   {k:'alt',tag:['','装备'],text:'橡皮山/当金山垭口 3,800 m · 高反药备一份',v:''},
   {k:'fuel',tag:['','纪律'],text:'大柴旦—敦煌段站距 120 km · 低于半箱就加',v:''},
   {k:'lodge1',tag:['up','确认'],text:`D2 住 ${lodgeCity(1)} · 已订`,v:''}]; },
  map:{nodes:QG_NODES,order:[0,1,2,3,4,5,6],loop:true,
   seg:[null,[0,1],[1,2],[2,3],[3,4],[4,5],[5,6],[6,0]],tonight:[0,1,2,3,4,5,6,-1]}},
 cx5:{name:'川西小环线',dest:'川西 · 小环线',fam:'cx',days:CX_DAYS,lodges:CX_LODGES,
  cluster:null,inserts:null,defSels:{},defSelsM:null,
  nights:4,rent:2000,roadfood:260,perCar:true,nav:'amap',strength:'中',
  carLabel:'租车 · 油费 · 路桥',tixLabel:'门票与观光车',foodLabel:'餐饮 · 含路餐',
  overTip:'可换新都桥普通房 / 面馆',
  budgets:[{l:'宽松',v:3400},{l:'精打细算',v:3000}],
  defTasteIds:['photo','hike'],
  thrift(){ lodge4=1; sels['cx-dinner']=1; },
  tastes:[{id:'photo',label:'雪山控',apply(){ addP('雪山控'); }},
          {id:'geo',label:'光影摄影',apply(){ addP('光影摄影 · 新都桥早晚出片'); }}],
  title:'🚗 川西小环线 5 天 · 高原第一课',meta:'川西小环 · 5 天 4 晚 · 08-14 出发',
  why:'先翻巴朗山直插四姑娘山，双桥沟坐观光车不费腿；回程走丹巴—八美—新都桥的光影线，折多山垭口收官下高原。海拔逐级上，给身体留适应时间。',
  weather:'川西 8 月 · 昼 12–24°C · 午后常阵雨 · 海拔 2,700–4,298 m',
  seasons:[{in:true,name:'双桥沟观光车',why:'旺季 9 点前进沟人最少',tag:'已排入 D2',ver:1},
   {in:false,name:'子梅垭口看贡嘎',why:'需硬派越野 · 本次不排',pick:{key:'zimei',name:'子梅垭口',ptext:'雪山控'}}],
  extras:[{later:{key:'changping',name:'长坪沟徒步',why:'需整天 · 5 天装不下',ptext:'徒步控'}}],
  extrasSub:'备着的还有 玩 15 · 吃 9 · 住 12',todos(){ return [
   {k:'alt',tag:['down','高反'],text:'垭口不跑跳 · 氧气罐每人一瓶 · 头痛即下撤',v:''},
   {k:'car',tag:['down','租车'],text:'确认石子 / 玻璃单独险',v:''},
   {k:'road',tag:['','驾驶'],text:'巴朗山隧道货车多 · 保持车距开雾灯',v:''},
   {k:'lodge3',tag:['up','确认'],text:`D4 住 ${lodgeOf(3)?lodgeCity(3):'—'} · 已订`,v:''},
   {k:'cash',tag:['','补给'],text:'现金少量 · 寨子里扫码偶尔没信号',v:''}]; },
  map:{nodes:CX_NODES,order:[0,1,2,3],loop:false,
   seg:[[0,1],null,[1,2],[2,3],[3,0]],tonight:[1,1,2,3,-1]}},
 dxb6:{name:'滇西北',dest:'云南 · 滇西北',fam:'dxb',days:DXB_DAYS,lodges:DXB_LODGES,
  cluster:null,inserts:null,defSels:{'db-dinner':0},defSelsM:null,
  nights:5,rent:2400,roadfood:300,perCar:true,nav:'amap',strength:'轻',
  carLabel:'租车 · 油费 · 路桥',tixLabel:'门票与区间车',foodLabel:'餐饮 · 含路餐',
  overTip:'可换巷内房 / 白族小馆',
  budgets:[{l:'宽松',v:4000},{l:'精打细算',v:3550}],
  defTasteIds:['chill','hike'],
  thrift(){ lodge4=1; sels['db-dinner']=1; },
  tastes:[{id:'chill',label:'湖边发呆',apply(){ addP('湖边发呆型'); }},
          {id:'hike',label:'轻徒步',apply(){ addP('轻徒步 · 上虎跳走全'); }}],
  title:'🚗 滇西北 6 天 · 洱海到雪山门口',meta:'滇西北 · 6 天 5 晚 · 08-18 出发',
  why:'海拔从 1,900 米慢慢抬到 3,300 米：大理躺平、环海一天、丽江过渡，再进峡谷上高原。香格里拉连住两晚，行李不挪窝。',
  weather:'滇西北 8 月 · 昼 15–26°C · 紫外线强 · 午后阵雨带伞',
  seasons:[{in:true,name:'普达措班次票',why:'区间车按班次 · 提前一天订',tag:'已排入 D5',ver:1},
   {in:false,name:'雨崩徒步',why:'需另加 3 天 · 本次装不下',pick:{key:'yubeng',name:'雨崩',ptext:'想走进雪山里'}}],
  extras:[{later:{key:'lugu',name:'泸沽湖',why:'往返多两天 · 本次不排',ptext:'想住湖边'}}],
  extrasSub:'备着的还有 玩 21 · 吃 14 · 住 18',todos(){ return [
   {k:'sun',tag:['','装备'],text:'高原紫外线 · 防晒帽墨镜人手一套',v:''},
   {k:'car',tag:['down','租车'],text:'确认石子 / 玻璃单独险',v:''},
   {k:'knee',tag:['','体力'],text:'上虎跳台阶 800 级 · 护膝建议带',v:''},
   {k:'lodge3',tag:['up','确认'],text:`D4–D5 连住 ${lodgeCity(3)} · 已订`,v:''},
   {k:'rain',tag:['','天气'],text:'午后阵雨 · 车里备伞',v:''}]; },
  map:{nodes:DXB_NODES,order:[0,1,2,3],loop:false,
   seg:[null,[0,1],[1,2],[2,3],null,[3,2]],tonight:[0,1,2,3,3,-1]}},
 hk3:{name:'香港周末',dest:'香港 · 周末',fam:'hk',days:HK_DAYS,lodges:HK_LODGES,
  cluster:null,inserts:null,defSels:{'hk-tea':0},defSelsM:null,
  nights:2,rent:0,roadfood:0,perCar:false,nav:'google',strength:'轻',
  carLabel:'地铁 · 渡轮（每人实付）',tixLabel:'门票与缆车',foodLabel:'餐饮',
  hero1v:'2<small>晚</small>',hero1k:'住佐敦不挪窝',
  i18n:{en:{name:'Hong Kong Weekend',dest:'Hong Kong · Weekend',
   title:'🚢 Hong Kong Weekend · 3 days',
   meta:'Hong Kong · 3d 2n · all by MTR & ferry',
   hero1k:'2 nights in Jordan, no repacking',
   why:'A weekend that runs on transit: trams through Central, the Star Ferry at dusk, dim sum before the flight home. The harbour breeze is free.'}},
  overTip:'可换标准房 / 茶记',
  budgets:[{l:'宽松',v:2000},{l:'精打细算',v:1750}],
  defTasteIds:['art','food'],
  thrift(){ lodge4=1; sels['hk-tea']=1; },
  tastes:[{id:'art',label:'看展控',apply(){ addP('看展控'); }},
          {id:'food',label:'茶记控',apply(){ addP('茶记控'); }}],
  title:'🚢 香港周末 3 天 · 美术馆与渡轮',meta:'香港 · 3 天 2 晚 · 周五出发 · 高铁往返另计',
  why:'两天半三个片区：D1 中环上环步行圈，用叮叮车和天星小轮串起来；D2 整块给西九；D3 早班缆车上山、午后高铁返程。全程住佐敦不挪窝。',
  weather:'香港 8 月 · 28–33°C 湿热 · 场馆冷气 22°C 带薄外套 · 日落约 19:00',
  inserts:{
 dalo:{day:2, afterK:'peak', label:'D3', brief:'太平山下山顺东涌线 · 棚屋水道 · 约 170 分 · ¥75/人',
   stop:{k:'dalo',name:'大澳渔村',era:'香港最后的棚屋',dur:170,prio:2,cost:20,cat:'tix',indoor:false,
     vibe:'水道两侧的高脚棚屋，晒着虾酱和咸鱼，船一开全是海风。',
     must:['坐一趟 ¥20 小船 · 穿棚屋水道看白海豚碰运气','虾酱和鸡蛋仔带一份走'],
     chips:[['up','免门票'],['','半日']],
     q:'大澳',pt:[58,152]},
   conns:[{mode:'',conn:'山顶缆车下山 → 东涌线转 11 号巴士 · 约 75 分',min:75,km:0,cost:30},
          {mode:'',conn:'大澳 → 东涌 → 西九龙站 · 约 65 分',min:65,km:0,cost:25}]},
  },
  seasons:[{in:true,name:'M+ 特展档期',why:'常设免费预约 · 特展看当期',tag:'已排入 D2',ver:1},
   {in:false,name:'大澳渔村半日',why:'东涌转巴士 · 顺返程线可加',ins:'dalo',pick:{key:'taio',name:'大澳',ptext:'离岛控'}}],
  extras:[{later:{key:'taio2',name:'大澳 · 棚屋水道',why:'需多半天 · 本次装不下',ptext:'离岛控'}}],
  extrasSub:'备着的还有 玩 26 · 吃 33 · 住 12',todos(){ return [
   {k:'pass',tag:['down','证件'],text:'港澳签注有效期先查 · 高铁票候补开着',v:''},
   {k:'pay',tag:['','支付'],text:'AlipayHK 或八达通 App 先开好',v:''},
   {k:'mplus',tag:['','预约'],text:'M+ 周一闭馆 · 常设免费票提前约',v:'更新 08-03',url:navQ('M+ Museum')},
   {k:'peak',tag:['','排队'],text:'山顶缆车按班次 · 09:30 前到少排一半',v:''}]; },
  map:{nodes:HK_NODES,loop:false,order:[0,1,2,3],
   base:'M340,104 L268,222 M340,104 L186,138 M340,104 L452,238',
   seg:[[0,1],[0,2],[0,3]],tonight:[0,0,-1]}}
};

/* ======================================================
   ADDON ROUTES — 注入到 routes_block.js 末尾
   QG7 · CX4 · SC5/SC6 (稻城亚丁)
   + TAGS_ALL 全局标签
   ====================================================== */

/* ── 全局标签（8 枚，所有线路共用，apply 可为空）─── */
const TAGS_ALL=[
 /* 前四：想看什么 · 后四：怎么玩（id 被 21 条线路引用，勿改） */
 {id:'photo', label:'拍照'},
 {id:'food',  label:'美食'},
 {id:'art',   label:'历史'},   /* 古城 · 遗址 · 寺庙 · 博物馆 */
 {id:'geo',   label:'山水'},   /* 湖泊 · 雪山 · 草原 · 雅丹峡谷 */
 {id:'hike',  label:'徒步'},
 {id:'chill', label:'躺平'},
 {id:'folk',  label:'人文'},   /* 村寨 · 市集 · 非遗 · 在地生活（区别于「历史」的遗存） */
 {id:'star',  label:'星空'},
];


/* ═══ 新疆 15 天：北疆全线+伊犁河谷 ═══ */
const XJ_TEKESI = {tab:'D10',name:'特克斯·八卦城',sub:'200 km · 约 3 h · 轻',start:570,hardEnd:1290,drive:'3 h',
 pre:{mode:'drive',conn:'伊宁 → 特克斯 · 200 km · 约 3 小时',min:180,km:200,cost:0,
   via:'沿途 · 伊昭公路 · 依山傍水全程好看'},
 post:{mode:'walk',conn:'步行回住处 · 10 分',min:10,cost:0},
 stops:[
 {k:'tekesi',name:'特克斯八卦城',era:'太极城格局',dur:120,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'全国唯一没有红绿灯的城市，整座城是一幅太极图。',
  must:['必看','钟鼓楼登顶俯瞰全城格局 · 八条大街环环相扣'],
  chips:[['up','免票'],['','骑自行车逛最好']],q:'特克斯八卦城'},
 {mode:'drive',conn:'→ 喀拉峻草原 · 30 km · 40 分',min:40,km:30,cost:0},
 {k:'kalajun',name:'喀拉峻草原 · 黄昏',cng:'最美草原',era:'天山花园',dur:0,openUntil:1260,openMin:60,prio:1,cost:60,cat:'tix',indoor:false,
  vibe:'油绿的山坡上密密麻麻开满野花，风吹过来草浪一道道。',
  must:['必看','4 号观景台 · 等下午侧光'],chips:[['','门票¥60']],q:'喀拉峻草原'}]};
const XJ_ZHAOSU = {tab:'D11',name:'昭苏·天鹅湖',sub:'80 km · 约 1.2 h · 轻',start:570,hardEnd:1290,drive:'1.2 h',
 pre:{mode:'drive',conn:'特克斯 → 昭苏 · 80 km · 约 1 小时 10 分',min:70,km:80,cost:0,
   via:'沿途 · 昭苏草原 · 三面天山合围的大坝子'},
 post:{mode:'drive',conn:'→ 住处 · 5 km · 10 分',min:10,km:5,cost:0},
 stops:[
 {k:'zhaosu-tian',name:'天鹅湖',era:'高山湖泊 2,000 m',dur:90,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'大白天鹅把湖面压出涟漪，六月之后一天能看到几十只。',
  must:['必看','湖边慢走 · 找角度把雪山压进来'],chips:[['up','免票']],q:'昭苏天鹅湖'},
 {mode:'drive',conn:'→ 波马草原 · 20 km · 25 分',min:25,km:20,cost:0},
 {k:'zhaosu-grass',name:'昭苏草原 · 马场',cng:'最美草原',era:'新疆最大草原',dur:120,prio:1,cost:80,cat:'tix',indoor:false,
  vibe:'找一匹哈萨克马，让自己彻底消失在草原里。',
  must:['必做','骑马 1 小时 · 别拒绝马夫的酒'],chips:[['','骑马体验']],q:'昭苏草原'}]};
const XJ_XIATA = {tab:'D12',name:'夏塔入口·那拉提',sub:'190 km · 约 3 h · 轻',start:570,hardEnd:1290,drive:'3 h',
 pre:{mode:'drive',conn:'昭苏 → 夏塔景区入口 → 那拉提 · 190 km · 约 3 小时',min:180,km:190,cost:0,
   via:'沿途 · 夏塔古道入口拍一张 · 不进景区 · 继续东行'},
 post:{mode:'drive',conn:'→ 镇边草坡住处 · 8 km · 15 分',min:15,km:8,cost:0},
 stops:[
 {k:'xiata',name:'夏塔古道入口 · 停车拍照',era:'天山穿越起点',dur:30,prio:2,cost:0,cat:'free',indoor:false,
  vibe:'古代丝路翻越天山的关口，进去是 58 公里徒步，我们只在门口看一眼。',
  must:['必看','入口雪峰 · 拍完就走'],chips:[['up','免票']],q:'夏塔景区'},
 {mode:'drive',conn:'→ 那拉提 · 150 km · 约 2 小时',min:120,km:150,cost:0},
 {k:'nlt-sc',name:'镇边草坡 · 空中草原',cng:'最美草原',era:'那拉提',dur:0,openUntil:1260,openMin:60,prio:0,cost:65,cat:'tix',indoor:false,
  vibe:'坐空中索道上去，俯瞰整个那拉提山谷。',
  must:['必看','索道上山 · 草坡牧道走一圈'],chips:[['','含索道']],q:'那拉提景区'}]};

const XJ15_DAYS=[
 ...XJ12_DAYS.slice(0,9),   /* D1–D9: XJ12 前9天（含禾木徒步） */
 _cd(XJ_TEKESI,{}),          /* D10 */
 _cd(XJ_ZHAOSU,{}),          /* D11 */
 _cd(XJ_XIATA,{}),           /* D12 */
 _cd(XJ12_DAYS[9], {tab:'D13'}),  /* D13 那拉提（xj12 D10） */
 _cd(XJ12_DAYS[10],{tab:'D14'}),  /* D14 巴音布鲁克（xj12 D11） */
 _cd(XJ12_DAYS[11],{tab:'D15'}),  /* D15 独库北段还车（xj12 D12） */
];
const XJ15_LODGES=[
 ...XJ12_LODGES.slice(0,9),
 {city:'特克斯县城',price:320,why:'八卦城步行圈 · 骑车出发',q:'特克斯'},
 {city:'昭苏草原民宿',price:380,why:'就在草原里 · 晚上能听马嘶',q:'昭苏'},
 {opts:[{city:'那拉提 · 观景客栈',price:400,why:'草坡近处 · 早起索道',q:'那拉提'},
        {city:'那拉提 · 镇区标准',price:280,why:'省¥60/人 · 步行 15 分到景区',q:'那拉提'}]},
 {city:'那拉提 · 连住',price:320,why:'不挪窝 · 行李不动',q:'那拉提'},
 {city:'巴音布鲁克镇',price:380,why:'九曲步行圈',q:'巴音布鲁克镇'},
 null];
const XJ15_NODES=[
 ...XJ_NODES,
 {n:'特克斯',x:64,y:230,lx:-2,ly:17,a:'middle'},
 {n:'昭苏',x:56,y:282,lx:-2,ly:17,a:'end'}];

/* ── 青甘大环线 7 天（速通版：跳过祁连单独住宿）─── */
const QG7_DAYS=[
 ...QG_DAYS.slice(0,6),
 _cd(QG_DAYS[7],{tab:'D7',sub:'350 km · 门源→西宁 · 5 h · 重',
   pre:{mode:'drive',conn:'张掖 → 西宁 · 350 km · 约 5 小时（经门源）',min:300,km:350,cost:45,
     via:'沿途 · 门源油菜花 7 月花期 · 扁都口随停 · 达坂山隧道'},
   stops:[QG_DAYS[7].stops[0]]}),
];
const QG7_LODGES=[...QG_LODGES.slice(0,6),null];

/* ── 川西小环线 4 天（压缩版：丹巴只玩半天，当天进新都桥）── */
const CX4_D3=_cd(CX_DAYS[2],{tab:'D3',sub:'198 km · 丹巴→八美→新都桥 · 4 h · 中',
 pre:{mode:'drive',conn:'日隆 → 丹巴 · 110 km · 约 2 小时 30 分',min:150,km:110,cost:0,
   via:'沿途 · 小金河谷 · 落石段勿停车'},
 post:{mode:'drive',conn:'丹巴 → 八美 → 新都桥 · 88 km · 约 2 小时',min:120,km:88,cost:0,
   via:'沿途 · 亚拉雪山观景台 · 八美土石林随停'},
 hardEnd:1290,
 stops:[
  {k:'jiaju',name:'甲居藏寨',cng:'最美古镇',era:'千碉之国',dur:120,prio:0,cost:50,cat:'tix',indoor:false,
   vibe:'白色藏房撒在整面山坡，留 2 小时走清楚。',must:['必看','2 号观景台 · 进寨喝碗酥油茶'],chips:[['','半天快览']],q:'甲居藏寨'}]});
const CX4_DAYS=[CX_DAYS[0],CX_DAYS[1],CX4_D3,
 _cd(CX_DAYS[4],{tab:'D4',pre:CX_DAYS[4].pre})];
const CX4_LODGES=[CX_LODGES[0],CX_LODGES[1],CX_LODGES[3],null];

/* ── 稻城·亚丁 5 天（三神山近照）─────────────── */
const SC_NODES=[
 {n:'成都',x:576,y:248,lx:13,ly:4,a:'start'},
 {n:'新都桥',x:424,y:176,lx:13,ly:4,a:'start'},
 {n:'理塘',x:296,y:150,lx:13,ly:-8,a:'start'},
 {n:'稻城',x:224,y:220,lx:0,ly:17,a:'middle'},
 {n:'亚丁',x:172,y:256,lx:-2,ly:15,a:'end'},
 {n:'康定',x:500,y:212,lx:13,ly:4,a:'middle'}];
const SC5_DAYS=[
{tab:'D1',name:'成都 → 新都桥',sub:'380 km 翻折多山 · 重',start:540,hardEnd:1290,drive:'6 h',
 pre:null,post:{mode:'drive',conn:'→ 新都桥住处 · 3 km · 8 分',min:8,km:3,cost:0},
 stops:[
 {k:'sc-pickup',name:'成都提车 · 验车',era:'租车站',dur:45,prio:0,cost:0,cat:'tix',indoor:true,
  vibe:'高原线必须 SUV，满箱出发。',must:['必做','绕车拍视频 · 查备胎防冻液'],chips:[['up','SUV 必须']],q:'成都 租车'},
 {mode:'drive',conn:'成都 → 康定 → 折多山 · 235 km · 约 4 小时 20 分',min:260,km:235,cost:55,
  via:'沿途 · 泸定泸定桥随停 · 折多山垭口 4,298 m 高反药备好'},
 {k:'sc-zheduo',name:'折多山垭口',era:'康巴第一关',dur:20,prio:2,cost:0,cat:'free',indoor:false,
  vibe:'翻越这道坎，就进了高原世界。',must:['必看','垭口远眺贡嘎雪线'],chips:[['up','免票'],['down','高反者车内']],q:'折多山垭口'},
 {mode:'drive',conn:'→ 新都桥 · 40 km · 50 分',min:50,km:40,cost:0},
 {k:'xdq-sc',name:'新都桥 · 光影长廊',era:'摄影天堂',dur:0,openUntil:1260,openMin:45,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'白杨、溪流、藏房，等光把它们镀一遍金。',must:['必看','日落前斜射光'],chips:[['up','免票']],q:'新都桥'}]},
{tab:'D2',name:'新都桥 → 理塘',sub:'170 km · 驾驶约 3 h · 中',start:570,hardEnd:1290,drive:'3 h',
 pre:{mode:'drive',conn:'→ 理塘勒通古镇 · 170 km · 约 3 小时',min:180,km:170,cost:0,
   via:'沿途 · 雅江峡谷 · 剪子弯山口 4,659 m 缓行'},
 post:{mode:'walk',conn:'步行回县城住处 · 10 分',min:10,cost:0},
 stops:[
 {k:'litang-town',name:'勒通古镇',era:'世界高城 4,014 m',dur:120,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'全世界最高的城，空气薄，光线却异常干净。',must:['必看','长青春科尔寺 · 广场上的牧人'],chips:[['up','免票'],['down','海拔 4,014 m 慢走']],q:'理塘勒通古镇'},
 {mode:'walk',conn:'步行 · 5 分',min:5,cost:0},
 {k:'litang-yak',name:'牦牛肉火锅 · 县城',era:'理塘本地',dur:75,prio:1,cost:68,cat:'food',indoor:true,
  vibe:'高原暖一暖，不要空腹早睡。',must:['必点','牦牛肉火锅 · 青稞酒小份'],chips:[['','暖']],q:'理塘 牦牛肉'}]},
{tab:'D3',name:'理塘 → 亚丁村',sub:'130 km · 驾驶约 3 h · 中',start:570,hardEnd:1290,drive:'3 h',
 pre:{mode:'drive',conn:'→ 亚丁景区游客中心 · 130 km · 约 3 小时',min:180,km:130,cost:0,
   via:'沿途 · 稻城县城加满油 · G318/G227 景观段'},
 post:{mode:'shuttle',conn:'区间车到亚丁村 · 30 分',min:30,cost:0},
 stops:[
 {k:'yadingvc',name:'亚丁景区 · 购票进场',era:'三神山脚',dur:60,prio:0,cost:220,cat:'tix',indoor:false,
  vibe:'检票进去，把时间留给神山。票含2天进场+全程区间车。',must:['必做','刷身份证 · 核对 2 天有效期'],chips:[['down','限流 1000 人/天 · 提前官网抢'],['','2 天有效']],q:'亚丁景区'},
 {mode:'shuttle',conn:'区间车进村 · 30 分',min:30,cost:0},
 {k:'chongu',name:'冲古寺 · 仙乃日近照',cng:'最美名山',era:'稻城三神山',dur:120,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'第一面仙乃日，雪峰倒进冲古湖里。',must:['必看','冲古寺湖倒影 · 黄昏侧光'],chips:[['up','免票（门票已含)'],['down','海拔 3,900 m 慢走']],q:'冲古寺'}]},
{tab:'D4',name:'亚丁 · 全天',sub:'央迈勇·夏诺多吉·三神山 · 重',start:540,hardEnd:1320,drive:'0 h',
 pre:{mode:'shuttle',conn:'区间车早班 · 进洛绒牛场 · 6:30 首班',min:40,cost:0,
   dep:{first:390,every:30,last:900}},
 post:{mode:'shuttle',conn:'末班区间车出场 · 45 分',min:45,cost:0},
 stops:[
 {k:'luorong',name:'洛绒牛场 · 央迈勇近照',cng:'最美名山',era:'4,180 m 高山牧场',dur:120,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'最标准的三神山合影位，早到等上午光。',must:['必看','央迈勇倒三角形雪峰 · 牦牛散场的清晨'],chips:[['','需徒步 4 km']],q:'洛绒牛场'},
 {mode:'walk',conn:'徒步上行 · 90 分',min:90,cost:0},
 {k:'shenxian-wan',name:'珍珠海 · 夏诺多吉脚',cng:'最美名山',era:'海拔 4,600 m',dur:90,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'碧绿的高原湖，夏诺多吉的雪裙正正挂在后面。',
  must:['必看','别贪高 · 感觉胸闷立刻下撤'],chips:[['down','高反敏感者止步牛场']],q:'珍珠海 稻城'}]},
{tab:'D5',name:'亚丁 → 成都还车',sub:'410 km · 驾驶约 7 h · 重',start:510,hardEnd:1230,drive:'7 h',
 pre:{mode:'drive',conn:'亚丁 → 稻城 → 雅江 → 康定 → 成都 · 410 km · 约 7 小时',min:420,km:410,cost:85,
   via:'沿途 · 稻城加满油 · 雅康高速隧道 · 泸定服务区补给'},
 post:null,
 stops:[
 {k:'sc-return',name:'还车 · 成都',era:'满油交车',dur:45,prio:0,cost:0,cat:'tix',indoor:true,
  vibe:'五天画圆，三神山住进记忆里。',must:['必做','满油 · 对公里数 · 拍视频'],chips:[['','留足 45 分']],q:'成都 租车还车'}]}];
const SC5_LODGES=[
 {opts:[{city:'新都桥 · 观景房',price:420,why:'窗外就是光影长廊',q:'新都桥'},
        {city:'新都桥 · 普通房',price:300,why:'省 ¥60/人 · 步行 5 分到机位',q:'新都桥'}]},
 {city:'理塘县城',price:300,why:'长青春科尔寺步行 10 分',q:'理塘'},
 {city:'亚丁村 · 神山脚',price:500,why:'明早第一班区间车不用赶路',q:'亚丁村'},
 {city:'亚丁村 · 连住',price:500,why:'不挪窝 · 行李不动',q:'亚丁村'},
 null];

const SC6_DAYS=[
 _cd(SC5_DAYS[0],{sub:'220 km 成都→康定 · 中',
   pre:null,post:{mode:'drive',conn:'→ 康定城住处 · 3 km · 8 分',min:8,km:3,cost:0},
   stops:[SC5_DAYS[0].stops[0],
    {mode:'drive',conn:'成都 → 康定 · 220 km · 约 3 小时 30 分',min:210,km:220,cost:45,via:'沿途 · 二郎山隧道 · 泸定大渡河'},
    {k:'kangding-muta',name:'木雅圣地 · 转经筒',era:'康定城',dur:60,prio:1,cost:0,cat:'free',indoor:false,
     vibe:'世界最大转经筒城里，跑马溜溜的那个地方。',must:['必看','大转经筒推三圈 · 城边跑马山远眺'],chips:[['up','免票']],q:'康定木雅圣地'}]}),
 _cd(SC5_DAYS[0],{tab:'D2',name:'康定 → 折多山 → 新都桥',sub:'170 km 康定→折多山→新都桥 · 中',
   pre:{mode:'drive',conn:'康定 → 折多山 → 新都桥 · 170 km · 约 3 小时',min:180,km:170,cost:0,via:'沿途 · 折多山垭口 · 雪山出来就是草甸'},
   post:{mode:'drive',conn:'→ 住处 · 3 km · 8 分',min:8,km:3,cost:0},
   stops:SC5_DAYS[0].stops.slice(2)}),
 _cd(SC5_DAYS[1],{tab:'D3'}),
 _cd(SC5_DAYS[2],{tab:'D4'}),
 _cd(SC5_DAYS[3],{tab:'D5'}),
 _cd(SC5_DAYS[4],{tab:'D6'})];
const SC6_LODGES=[
 {city:'康定城',price:380,why:'城里最热闹 · 转经筒步行圈',q:'康定'},
 ...SC5_LODGES];    /* 新都桥opts·理塘·亚丁·亚丁连住·null，共6晚对6天 */

/* ── 将新路线注册进 ROUTES ────────────────────────── */
Object.assign(ROUTES,{
 qg7:Object.assign({},ROUTES.qg8,{days:QG7_DAYS,lodges:QG7_LODGES,nights:6,
  fam:'qg',rent:2600,dayVariants:[7,8],
  budgets:[{l:'宽松',v:5300},{l:'精打细算',v:4700}],
  title:'🚗 青甘大环线 7 天 · 速通版',meta:'青甘环线 · 7 天 6 晚 · 08-20 出发',
  why:'压缩版：跳过祁连单独住宿，D6 看完丹霞后 D7 直走门源回西宁。全程仍保留茶卡、莫高窟、七彩丹霞三大件。',
  map:Object.assign({},ROUTES.qg8.map,{
   order:[0,1,2,3,4,5,6],
   seg:[null,[0,1],[1,2],[2,3],[3,4],[4,5],[5,0]],
   tonight:[0,1,2,3,4,5,-1]})}),
 cx4:Object.assign({},ROUTES.cx5,{days:CX4_DAYS,lodges:CX4_LODGES,nights:3,
  fam:'cx',rent:1600,roadfood:180,dayVariants:[4,5],
  budgets:[{l:'宽松',v:2750},{l:'精打细算',v:2450}],
  todos(){ return [
   {k:'alt',tag:['down','高反'],text:'垭口不跑跳 · 氧气罐每人一瓶 · 头痛即下撤',v:''},
   {k:'car',tag:['down','租车'],text:'确认石子 / 玻璃单独险',v:''},
   {k:'road',tag:['','驾驶'],text:'巴朗山隧道货车多 · 保持车距开雾灯',v:''},
   {k:'lodge3',tag:['up','确认'],text:`D3 住 ${lodgeOf(2)?lodgeCity(2):'新都桥'} · 已订`,v:''},
   {k:'cash',tag:['','补给'],text:'现金少量 · 寨子里扫码偶尔没信号',v:''}]; },
  title:'🚗 川西小环线 4 天 · 快速版',meta:'川西小环 · 4 天 3 晚 · 08-14 出发',
  why:'最短可行版：四姑娘山双桥沟不删，甲居藏寨半天快览后当天进新都桥，最后一天折多山收官回成都。',
  map:Object.assign({},ROUTES.cx5.map,{
   seg:[[0,1],null,[1,2,3],[3,0]],
   tonight:[1,1,3,-1]})}),
 sc5:{name:'稻城·亚丁',dest:'四川 · 稻城·亚丁',fam:'sc',days:SC5_DAYS,lodges:SC5_LODGES,
  cluster:null,inserts:null,defSels:{},defSelsM:null,
  nights:4,rent:2200,roadfood:280,perCar:true,nav:'amap',strength:'重',
  dayVariants:[5,6],
  carLabel:'租车 · 油费 · 路桥',tixLabel:'门票与区间车',foodLabel:'餐饮 · 含路餐',
  overTip:'可换新都桥普通房',
  budgets:[{l:'宽松',v:3650},{l:'精打细算',v:3250}],
  thrift(){ lodge4=1; },
  tastes:[],defTasteIds:['hike','photo'],
  title:'🏔 稻城·亚丁 5天 · 三神山近照',meta:'四川稻城·亚丁 · 5天4晚 · 08-22 出发',
  why:'最短可行版：D1翻折多山到新都桥，D2抵理塘适应高海拔，D3-D4两天在亚丁，D5一路下撤回成都。每天都是长途但节奏清晰，高反是唯一变量。',
  weather:'高原 8 月 · 昼 14–22°C 夜 3–8°C · 午后雷阵雨 · 紫外线极强',
  seasons:[{in:true,name:'亚丁限流 1000 人/天',why:'旺季常售罄 · 提前 10 天官网抢',tag:'已排入 D3',ver:1},
   {in:false,name:'洛绒牛场秋色',why:'红叶约 10 月初 · 本次未到季',pick:{key:'sc-autumn',name:'亚丁秋色',ptext:'秋色控'}}],
  extras:[{later:{key:'haluogou',name:'海螺沟冰川',why:'贡嘎山西坡 · 需绕路加一天',ptext:'冰川控'}}],
  extrasSub:'备着的还有 玩 18 · 吃 7 · 住 9',
  todos(){ return [
   {k:'yading',tag:['down','预约'],text:'亚丁限流票 · 提前 10 天官网预约（www.yadingpark.com）',v:'更新 08-03',url:'https://www.yadingtour.com'},
   {k:'alt',tag:['down','高反'],text:'4,000 m+ 全程 · 高反药+氧气罐人手一份 · 头痛即下撤',v:''},
   {k:'car',tag:['down','租车'],text:'SUV 必须 · 确认石子/玻璃险 · 查备胎防冻液',v:''},
   {k:'speed',tag:['','驾驶'],text:'折多山/雅康高速区间测速 · 全程开提醒',v:''},
   {k:'fuel',tag:['','纪律'],text:'成都满箱出发 · 稻城二次满箱 · D5 出发前检查',v:''},
   {k:'lodge3',tag:['up','确认'],text:'亚丁村住宿旺季必须提前订',v:'',url:'https://www.yadingtour.com'}]; },
  map:{nodes:SC_NODES,order:[0,1,2,3,4],loop:false,
   seg:[[0,1],[1,2],[2,3],[3,4],[4,0]],
   tonight:[1,2,3,4,-1]}},
 sc6:{name:'稻城·亚丁',dest:'四川 · 稻城·亚丁',fam:'sc',days:SC6_DAYS,lodges:SC6_LODGES,
  cluster:null,inserts:null,defSels:{},defSelsM:null,
  nights:5,rent:2600,roadfood:320,perCar:true,nav:'amap',strength:'重',
  dayVariants:[5,6],
  carLabel:'租车 · 油费 · 路桥',tixLabel:'门票与区间车',foodLabel:'餐饮 · 含路餐',
  overTip:'可换新都桥普通房',
  budgets:[{l:'宽松',v:4300},{l:'精打细算',v:3800}],
  thrift(){ lodge4=1; },
  tastes:[],defTasteIds:['hike','photo'],
  title:'🏔 稻城·亚丁 6天 · 含康定版',meta:'四川稻城·亚丁 · 6天5晚 · 08-22 出发',
  why:'加一天在康定，高反适应更从容，不急着翻折多山。其余同5天版。',
  weather:'高原 8 月 · 昼 14–22°C 夜 3–8°C · 午后雷阵雨 · 紫外线极强',
  seasons:[{in:true,name:'亚丁限流 1000 人/天',why:'旺季常售罄 · 提前 10 天官网抢',tag:'已排入 D4',ver:1},
   {in:false,name:'洛绒牛场秋色',why:'红叶约 10 月初 · 本次未到季',pick:{key:'sc-autumn',name:'亚丁秋色',ptext:'秋色控'}}],
  extras:[{later:{key:'haluogou',name:'海螺沟冰川',why:'贡嘎山西坡 · 需绕路加一天',ptext:'冰川控'}}],
  extrasSub:'备着的还有 玩 18 · 吃 7 · 住 9',
  todos(){return ROUTES.sc5.todos();},
  map:{nodes:SC_NODES,order:[0,5,1,2,3,4],loop:false,
   seg:[[0,5],[5,1],[1,2],[2,3],null,[4,0]],
   tonight:[5,1,2,4,4,-1]}},
});

/* ── QG 和 CX 补 dayVariants ─────────────────────── */
ROUTES.qg8.dayVariants=[7,8];
ROUTES.cx5.dayVariants=[4,5];
/* XJ 系已在 routes_block.js 里，补一下 */
ROUTES.xj8.dayVariants=[8,10,12,15];
ROUTES.xj10.dayVariants=[8,10,12,15];
ROUTES.xj12.dayVariants=[8,10,12,15];
Object.assign(ROUTES,{xj15:Object.assign({},ROUTES.xj10,{
  fam:'xj',days:XJ15_DAYS,lodges:XJ15_LODGES,nights:14,rent:5800,roadfood:800,
  extras:[{ins:'wucai'},{ins:'baihaba'}],
  dayVariants:[8,10,12,15],
  budgets:[{l:'宽松',v:11900},{l:'精打细算',v:10600}],
  title:'🚗 北疆全线 15 天 · 加特克斯·昭苏·夏塔',
  meta:'北疆全线 · 15天14晚 · 08-15 出发',
  why:'在 12 天版基础上，加三天伊犁腹地：特克斯八卦城 → 昭苏天鹅湖草原 → 夏塔古道入口，最后独库北段收官。全程不走回头路。',
  map:{nodes:XJ15_NODES,order:[0,1,2,3,4,5,6,7,10,11,8,9],loop:true,
   seg:[null,[0,1],[1,2],[2,3],[3,4],null,[4,5],[5,6],[6,7],[7,10],[10,11],[11,8],null,[8,9],[9,0]],
   tonight:[0,1,2,3,4,4,5,6,7,10,11,8,8,9,-1]}})});
ROUTES.xj10.dayVariants=[8,10,12];
ROUTES.xj12.dayVariants=[8,10,12];

/* ======================================================
   新路线数据 xz7 · nm4 · hs3
   ====================================================== */

/* ── 西藏拉萨入藏线 7 天 ──────────────────────────── */
const XZ_NODES=[
 {n:'拉萨',x:360,y:224,lx:12,ly:4,a:'start'},
 {n:'羊卓雍错',x:396,y:286,lx:12,ly:4,a:'start'},
 {n:'日喀则',x:224,y:222,lx:-2,ly:-12,a:'middle'},
 {n:'纳木错',x:318,y:122,lx:12,ly:-8,a:'start'},
 {n:'巴松措',x:470,y:210,lx:12,ly:-8,a:'middle'},
 {n:'林芝',x:520,y:250,lx:12,ly:4,a:'middle'},
 {n:'大峡谷',x:570,y:214,lx:-6,ly:-12,a:'end'}];
const XZ7_DAYS=[
{tab:'D1',name:'拉萨 · 抵达适应',sub:'高反缓冲日 · 步行为主 · 极轻',start:600,hardEnd:1380,drive:'— h',
 pre:null,post:{mode:'walk',conn:'步行回住处 · 10 分',min:10,cost:0},
 stops:[
 {k:'xz-arrive',name:'拉萨到达 · 不抢行程',era:'海拔 3,650 m',dur:60,prio:2,cost:0,cat:'free',indoor:true,
  vibe:'到了先睡觉，下午轻轻走，不要洗澡蒸桑拿，不要跑步。',must:['必做','睡够·多喝水·不剧烈运动'],chips:[['down','高反 24 h 内最严重']],q:'拉萨'},
 {mode:'walk',conn:'步行到八廓街 · 15 分',min:15,cost:0},
 {k:'barkhor',name:'八廓街 · 转经道',era:'千年朝圣道',dur:90,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'磕长头的朝圣者，转经筒的铃声，下午光最好。',must:['必看','顺时针方向走 · 大昭寺金顶就在头顶'],chips:[['up','免票']],q:'八廓街'},
 {mode:'walk',conn:'步行 · 5 分',min:5,cost:0},
 {k:'jokhang-night',name:'大昭寺 · 傍晚广场',era:'公元 7 世纪',dur:45,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'外广场不用票，松赞干布的结婚礼堂。傍晚的光最厚。',must:['必看','广场上的磕头者 · 把人放进来'],chips:[['up','夜逛免票']],q:'大昭寺'}]},
{tab:'D2',name:'布达拉宫 · 色拉寺',sub:'步行为主 · 轻',start:570,hardEnd:1320,drive:'— h',
 pre:null,post:{mode:'walk',conn:'步行回住处 · 20 分',min:20,cost:0},
 stops:[
 {k:'potala',name:'布达拉宫',era:'公元 7 世纪',dur:150,prio:0,cost:240,cat:'tix',indoor:true,dep:{first:540,every:30,last:720},
  vibe:'一千个台阶，十三层，世界最高的宫殿。进去是另一个宇宙。',must:['必看','松赞干布法王洞 · 五世达赖灵塔 · 从不同角度看布宫体量'],
  chips:[['down','限 2300 人/天 · 提前官网预约'],['','按批次入场']],q:'布达拉宫'},
 {mode:'walk',conn:'步行→龙王潭公园 · 15 分',min:15,cost:0},
 {k:'lukhang',name:'龙王潭 · 布宫倒影',era:'药王山对面',dur:45,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'水里的那座布达拉，和天上那座一样大。',must:['必看','荷花池边最正位'],chips:[['up','免票']],q:'龙王潭公园'},
 {mode:'walk',conn:'打车前往色拉寺 · 20 min · ¥15',min:20,cost:15},
 {k:'sera',name:'色拉寺 · 辩经院',era:'黄教六大寺',dur:90,prio:1,cost:50,cat:'tix',indoor:false,earliest:870,
  vibe:'14:30–17:00 辩经，僧侣击掌拍手声震天，可以围观。',must:['必看','14:30 准时到辩经院 · 别打扰'],chips:[['','辩经 14:30 开始']],q:'色拉寺'}]},
{tab:'D3',name:'羊卓雍错',sub:'130 km 往返 · 中',start:570,hardEnd:1320,drive:'3 h',
 pre:{mode:'drive',conn:'拉萨 → 羊卓雍错 · 65 km · 约 1 小时 30 分',min:90,km:65,cost:0,
   via:'沿途 · 甘巴拉垭口 5,030 m · 一翻垭口湖就出现了'},
 post:{mode:'drive',conn:'羊湖 → 拉萨 · 65 km · 约 1 小时 20 分',min:80,km:65,cost:0},
 stops:[
 {k:'yamdrok',name:'羊卓雍错',cng:'最美湖泊',era:'天空之镜',dur:180,prio:0,cost:30,cat:'tix',indoor:false,
  vibe:'蓝到不真实，海拔 4441 米的镜面，四周是雪山。',must:['必看','垭口俯瞰全湖 · 湖边捡石头走走'],chips:[['up','门票¥30'],['down','高原呼吸·缓慢行走']],q:'羊卓雍错'},
 {mode:'drive',conn:'→ 白居寺 · 60 km · 50 分',min:50,km:60,cost:0},
 {k:'palkhor',name:'白居寺 · 菊扎神变殿',era:'江孜宗山',dur:90,prio:1,cost:40,cat:'tix',indoor:true,
  vibe:'唯一融合了萨迦、噶举、格鲁三派的寺，菊扎佛塔在里面。',must:['必看','菊扎塔9层· 77 个佛殿层层绕'],chips:[['','门票¥40']],q:'白居寺'}]},
{tab:'D4',name:'拉萨 → 日喀则',sub:'280 km · 约 4 小时 · 中',start:570,hardEnd:1290,drive:'4 h',
 pre:{mode:'drive',conn:'拉萨 → 日喀则 · 280 km · 约 4 小时',min:240,km:280,cost:0,
   via:'沿途 · 318 国道雅鲁藏布江谷地 · 里孜服务区补给'},
 post:{mode:'walk',conn:'步行进住处 · 10 分',min:10,cost:0},
 stops:[
 {k:'tashilhunpo',name:'扎什伦布寺',era:'班禅驻锡地',dur:150,prio:0,cost:85,cat:'tix',indoor:true,
  vibe:'世界最大的弥勒佛像在这里，26.2 米。光线充足的上午最好。',must:['必看','未来佛殿内巨型弥勒 · 历代班禅灵塔'],chips:[['','门票¥85']],q:'扎什伦布寺'},
 {mode:'walk',conn:'步行→日喀则古镇 · 15 分',min:15,cost:0},
 {k:'shigatse-market',name:'日喀则市集 · 藏族手工区',era:'老城',dur:0,openUntil:1200,openMin:45,prio:2,cost:0,cat:'free',indoor:false,
  vibe:'磕金属的工匠，卖风马旗的老店，大量真品唐卡。',must:['必买','酥油花茶暖一碗'],chips:[['up','免票']],q:'日喀则藏族手工艺'}]},
{tab:'D5',name:'日喀则 → 纳木错',sub:'480 km · 约 7 小时 · 重',start:510,hardEnd:1350,drive:'7 h',
 pre:{mode:'drive',conn:'日喀则 → 拉萨 → 纳木错 · 480 km · 约 7 小时',min:420,km:480,cost:0,
   via:'沿途 · 拉萨换加油 · 那根拉垭口 5,190 m（湖面正视角）'},
 post:{mode:'walk',conn:'步行进湖边住处 · 5 分',min:5,cost:0},
 stops:[
 {k:'namtso',name:'纳木错 · 扎西岛日落',cng:'最美湖泊',era:'海拔 4,718 m 圣湖',dur:120,prio:0,cost:80,cat:'tix',indoor:false,
  vibe:'世界海拔最高的湖，扎西岛上扎营过夜看银河。',must:['必看','扎西岛东面看日落·夜晚银河不遮光'],chips:[['down','海拔 4,718 m 行动极缓']],q:'纳木错'}]},
{tab:'D6',name:'纳木错 · 全天',sub:'湖边 · 日出日落银河 · 轻',start:300,hardEnd:1380,drive:'0 h',
 pre:null,post:{mode:'walk',conn:'步行 · 10 分',min:10,cost:0},
 stops:[
 {k:'namtso-dawn',name:'纳木错 · 日出',cng:'最美湖泊',era:'4,718 m 星光下',dur:120,prio:0,cost:0,cat:'free',indoor:false,earliest:300,
  vibe:'5 点就要站在湖边等，雪山先亮，然后湖面铺金。',must:['必看','扎西岛东面 · 裹最厚的衣服'],chips:[['up','免票（昨天门票含）'],['down','夜里接近 0°C']],q:'纳木错日出'},
 {k:'namtso-loop',name:'纳木错 · 扎西岛绕岛',era:'湖心半岛',dur:150,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'绕岛2小时，神山在背后，脚下是圣湖。',must:['必走','玛尼石堆 · 经幡林 · 喇嘛庙'],chips:[['up','免票']],q:'纳木错扎西岛'}]},
{tab:'D7',name:'纳木错 → 拉萨出发',sub:'200 km · 约 3 小时 · 轻',start:540,hardEnd:1200,drive:'3 h',
 pre:{mode:'drive',conn:'纳木错 → 拉萨 · 200 km · 约 3 小时',min:180,km:200,cost:0,
   via:'沿途 · 念青唐古拉山口 · 拉萨河谷'},
 post:null,
 stops:[
 {k:'xz-out',name:'拉萨·还车·出发',era:'终点',dur:60,prio:0,cost:0,cat:'tix',indoor:true,
  vibe:'七天画圆，世界屋脊的意义，只有来过才懂。',must:['必做','还车·满油·对公里数'],chips:[['','留足 45 分']],q:'拉萨贡嘎机场'}]}];
const XZ7_LODGES=[
 {city:'拉萨八廓街区',price:500,why:'转经道步行 3 分',q:'拉萨八廓街酒店'},
 {city:'拉萨 · 连住',price:500,why:'不挪窝 · 行李不动',q:'拉萨布达拉宫区'},
 {city:'拉萨 · 连住',price:500,why:'D3 返回仍住拉萨',q:'拉萨'},
 {city:'日喀则古城区',price:450,why:'扎什伦布寺步行 20 分',q:'日喀则'},
 {opts:[{city:'纳木错湖边营地',price:480,why:'扎西岛上 · 银河无遮挡',q:'纳木错住宿'},
        {city:'纳木错旗政府区',price:340,why:'省¥70/人 · 上午进湖',q:'纳木错'}]},
 {city:'纳木错 · 连住',price:480,why:'D6 全天留在湖边（与D5同住）',q:'纳木错住宿'},
 null];

/* ═══ 西藏 10 天：先下林芝低海拔适应，再上纳木错 ═══ */
const XZ10_LINZHI_1={tab:'D3',name:'拉萨 → 巴松措 → 林芝',sub:'500 km · 下降 600 m 助适应 · 中',start:450,hardEnd:1350,drive:'7 h',
 pre:{mode:'drive',conn:'拉萨 → 巴松措 · 380 km · 林拉高速约 5 小时',min:300,km:380,cost:80,
   via:'沿途 · 米拉山隧道已通 · 不再翻 5013 m 山口'},
 post:{mode:'drive',conn:'巴松措 → 林芝八一镇 · 120 km · 约 2 小时',min:120,km:120,cost:20},
 stops:[
 {k:'basumtso',name:'巴松措 · 湖心岛',cng:'最美湖泊',era:'红教圣湖 · 海拔 3480 m',dur:150,prio:0,cost:120,cat:'tix',indoor:false,
  vibe:'雪山围着一池碧水，湖心岛上那座错宗工巴寺比湖还老。',
  must:['必看','走过木桥上湖心岛 · 寺后看生殖崇拜壁画'],
  chips:[['','门票¥120'],['up','海拔比拉萨低 170 m']],q:'巴松措'}]};
const XZ10_LINZHI_2={tab:'D4',name:'雅鲁藏布大峡谷 · 南迦巴瓦',sub:'160 km 往返 · 等金山 · 中',start:420,hardEnd:1350,drive:'3 h',
 pre:{mode:'drive',conn:'林芝 → 派镇景区入口 · 80 km · 约 1 小时 30 分',min:90,km:80,cost:20},
 post:{mode:'drive',conn:'派镇 → 索松村住处 · 20 km · 40 分（土路慢行）',min:40,km:20,cost:0},
 stops:[
 {k:'gtcanyon',name:'雅鲁藏布大峡谷',cng:'最美峡谷',era:'世界第一大峡谷',dur:240,prio:0,cost:290,cat:'tix',indoor:false,
  vibe:'江水在脚下拐出一个大湾，抬头就是南迦巴瓦的锥形雪顶。',
  must:['必看','大渡卡到直白村四个观景台 · 观光车含在票内'],
  chips:[['','门票+车¥290'],['down','云遮山概率高 · 清晨最清']],q:'雅鲁藏布大峡谷'},
 {k:'namcha-set',name:'索松村 · 日照金山',era:'正对南迦巴瓦 7782 m',dur:90,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'桃花村的田埂上支起脚架，等最后一线光爬上那座羞女峰。',
  must:['必等','日落前 40 分到位 · 云开就有金山'],
  chips:[['up','村里免票'],['down','看不看得到靠运气']],q:'索松村'}]};
const XZ10_LINZHI_3={tab:'D5',name:'林芝 → 拉萨',sub:'430 km · 尼洋河一路 · 中',start:420,hardEnd:1320,drive:'6 h',
 pre:{mode:'drive',conn:'索松村 → 卡定沟 · 100 km · 约 2 小时',min:120,km:100,cost:20},
 post:{mode:'drive',conn:'卡定沟 → 拉萨 · 330 km · 约 4 小时 30 分',min:270,km:330,cost:60},
 stops:[
 {k:'kadinggou',name:'卡定沟 · 天佛瀑布',era:'落差 200 m',dur:90,prio:1,cost:60,cat:'tix',indoor:false,
  vibe:'水从崖顶砸下来，水汽里能看出一尊天然佛影，看不出也凉快。',
  must:['必看','栈道走到瀑布正下方 · 备雨衣'],chips:[['','门票¥60']],q:'卡定沟'},
 {k:'niyang',name:'尼洋河风光带',era:'318 国道最柔一段',dur:60,prio:2,cost:0,cat:'free',indoor:false,
  vibe:'河水是奶蓝色的，河滩上白石头堆成一片，随便停车就是照片。',
  must:['必停','中流砥柱观景台 · 河滩边慢走'],chips:[['up','免票'],['','路边观景']],q:'尼洋河风光带'}]};
const XZ10_DAYS=[XZ7_DAYS[0], XZ7_DAYS[1], XZ10_LINZHI_1, XZ10_LINZHI_2, XZ10_LINZHI_3,
  Object.assign({},XZ7_DAYS[2],{tab:'D6'}), Object.assign({},XZ7_DAYS[3],{tab:'D7'}),
  Object.assign({},XZ7_DAYS[4],{tab:'D8'}), Object.assign({},XZ7_DAYS[5],{tab:'D9'}),
  Object.assign({},XZ7_DAYS[6],{tab:'D10'})];
const XZ10_LODGES=[
 XZ7_LODGES[0], XZ7_LODGES[1],
 {city:'林芝八一镇',price:380,why:'镇上吃住方便 · 明早进峡谷近',q:'林芝八一镇酒店'},
 {opts:[{city:'索松村 · 正对南迦巴瓦',price:420,why:'开窗就是雪山 · 等金山不用赶路',q:'索松村民宿'},
        {city:'林芝八一镇 · 回镇住',price:380,why:'土路不好走 · 回镇更稳',q:'林芝八一镇酒店'}]},
 {city:'拉萨 · 连住',price:500,why:'林芝回来仍住拉萨',q:'拉萨'},
 XZ7_LODGES[2], XZ7_LODGES[3], XZ7_LODGES[4], XZ7_LODGES[5],
 null];


/* ── 额济纳·胡杨林 4 天（10 月金秋）──────────────── */
const NM_NODES=[
 {n:'酒泉',x:192,y:134,lx:12,ly:4,a:'start'},
 {n:'额济纳',x:380,y:74,lx:12,ly:4,a:'start'}];
const NM4_DAYS=[
{tab:'D1',name:'酒泉 → 额济纳',sub:'350 km · 约 4.5 h · 中',start:570,hardEnd:1290,drive:'4.5 h',
 pre:null,post:{mode:'drive',conn:'→ 旗政府住处 · 5 km · 10 分',min:10,km:5,cost:0},
 stops:[
 {k:'nm-pickup',name:'酒泉提车 · 验车',era:'出发点',dur:45,prio:0,cost:0,cat:'tix',indoor:true,
  vibe:'这段路没有加油站，出发前满箱。',must:['必做','满油出发 · 带备胎工具 · 信号极差'],chips:[['up','SUV 建议'],['down','G7 国道侧风大']],q:'酒泉 租车'},
 {mode:'drive',conn:'酒泉 → 额济纳 · 350 km · 约 4 小时 30 分',min:270,km:350,cost:0,
  via:'沿途 · G7 国道全程 · 无高速 · 约 120 km/h 限速'},
 {k:'nm-dusk',name:'达来呼布镇 · 傍晚',era:'黑河绿洲',dur:0,openUntil:1230,openMin:45,prio:2,cost:0,cat:'free',indoor:false,
  vibe:'进沙漠之前先把小镇摸清，明天一早进林区。',must:['必做','买景区联票·打听今年黄叶情况'],chips:[['up','免票']],q:'额济纳旗'}]},
{tab:'D2',name:'一二三道桥 · 黑城',sub:'区间车全天 · 中',start:540,hardEnd:1290,drive:'0.5 h',
 pre:{mode:'drive',conn:'→ 胡杨林一道桥 · 20 km · 25 分',min:25,km:20,cost:0},
 post:{mode:'drive',conn:'→ 住处 · 8 km · 15 分',min:15,km:8,cost:0},
 stops:[
 {k:'nm-hulun',name:'胡杨林 · 一二三道桥',era:'金色走廊',dur:240,prio:0,cost:100,cat:'tix',indoor:false,dep:{first:480,every:30,last:960},
  vibe:'10 月的一道桥，每一棵树都是一面金镜。拍不完的光。',must:['必看','二道桥主拍位 · 三道桥林中小路'],chips:[['','票含区间车'],['','10 月下旬最金']],q:'额济纳胡杨林'},
 {mode:'drive',conn:'→ 黑城遗址 · 25 km · 30 分',min:30,km:25,cost:0},
 {k:'heicheng',name:'黑城·西夏遗址',era:'公元 1372 年灭',dur:90,prio:1,cost:20,cat:'tix',indoor:false,
  vibe:'沙漠里的西夏土城，马可波罗来过，赫定挖过。',must:['必看','黄昏侧光下的夯土墙'],chips:[['','门票¥20']],q:'黑城遗址'}]},
{tab:'D3',name:'四道桥 · 怪树林',sub:'区间车 + 居延海 · 轻',start:540,hardEnd:1290,drive:'0.5 h',
 pre:{mode:'drive',conn:'→ 四道桥 · 18 km · 20 分',min:20,km:18,cost:0},
 post:{mode:'drive',conn:'→ 居延海 · 15 km · 20 分',min:20,km:15,cost:0},
 stops:[
 {k:'nm-4bridge',name:'四至八道桥 · 英雄林',era:'胡杨最密处',dur:210,prio:0,cost:80,cat:'tix',indoor:false,dep:{first:480,every:30,last:900},
  vibe:'七号桥附近的疏林，拍散点透视最好。',must:['必看','七号桥疏林 · 等下午斜光'],chips:[['','票含区间车']],q:'额济纳七道桥'},
 {mode:'drive',conn:'→ 怪树林 · 12 km · 15 分',min:15,km:12,cost:0},
 {k:'ghost-trees',name:'怪树林 · 枯木滩',era:'三千年枯木',dur:90,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'胡杨死了三千年不倒，枯枝在夕阳里像在生长。',must:['必看','广角贴着树根拍天空'],chips:[['up','免票']],q:'额济纳怪树林'},
 {mode:'drive',conn:'→ 居延海 · 15 km',min:20,km:15,cost:0},
 {k:'juyan',name:'居延海 · 候鸟',era:'内蒙最大湖泊',dur:60,prio:2,cost:0,cat:'free',indoor:false,
  vibe:'秋天的候鸟在这里路过，背景是胡杨金黄。',must:['必看','芦苇荡里的鸬鹚群'],chips:[['up','免票']],q:'居延海'}]},
{tab:'D4',name:'额济纳 → 酒泉',sub:'350 km · 约 4.5 h · 中',start:540,hardEnd:1200,drive:'4.5 h',
 pre:{mode:'drive',conn:'额济纳 → 酒泉 · 350 km · 约 4 小时 30 分',min:270,km:350,cost:0,
   via:'沿途 · G7 · 返程注意侧风'},
 post:null,
 stops:[
 {k:'nm-return',name:'还车 · 酒泉',era:'满油交车',dur:45,prio:0,cost:0,cat:'tix',indoor:true,
  vibe:'胡杨的金黄收进记忆里。',must:['必做','满油 · 验车 · 拍视频'],chips:[['','留足 45 分']],q:'酒泉 租车还车'}]}];
const NM4_LODGES=[
 {city:'额济纳旗中心',price:360,why:'景区穿梭车起点步行圈',q:'额济纳旗'},
 {opts:[{city:'胡杨林区民宿',price:420,why:'骑车 5 分直进林区',q:'额济纳胡杨林民宿'},
        {city:'旗中心标准房',price:280,why:'省 ¥70/人 · 班车 20 分到林区',q:'额济纳旗'}]},
 {city:'额济纳旗 · 连住',price:420,why:'不搬家 · 明早直进林',q:'额济纳旗'},
 null];

/* ── 黄山·徽州 3 天（华东周末线）──────────────────── */
const HS_NODES=[
 {n:'杭州',x:568,y:220,lx:13,ly:4,a:'start'},
 {n:'黄山市',x:428,y:272,lx:12,ly:4,a:'start'},
 {n:'宏村',x:372,y:298,lx:-2,ly:15,a:'end'}];
const HS3_DAYS=[
{tab:'D1',name:'杭州 → 黄山市 · 徽州古城',sub:'260 km · 约 3.5 h · 轻',start:570,hardEnd:1320,drive:'3.5 h',
 pre:null,post:{mode:'walk',conn:'步行回客栈 · 10 分',min:10,cost:0},
 stops:[
 {k:'hs-pickup',name:'杭州提车 · 验车',era:'租车站',dur:40,prio:0,cost:0,cat:'tix',indoor:true,
  vibe:'沪杭一带租车很方便，中午出发下午到。',must:['必做','绕车拍视频 · 检验车况'],chips:[['up','小车即可']],q:'杭州 租车'},
 {mode:'drive',conn:'杭州 → 黄山市 · 260 km · 约 3 小时 30 分',min:210,km:260,cost:45,
  via:'沿途 · 千岛湖隧道 · 歙县服务区加油'},
 {k:'huizhou-old',name:'徽州古城 · 许国石坊',era:'明代八脚牌坊',dur:90,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'唯一的八脚石坊，明代的宰相刚好经过正门。',must:['必看','从南门进 · 石坊前找光影'],chips:[['up','免票']],q:'徽州古城'},
 {mode:'walk',conn:'步行 · 5 分',min:5,cost:0},
 {k:'bishan-food',name:'黄山毛豆腐 · 老字号',era:'徽菜',dur:75,prio:0,cost:68,cat:'food',indoor:true,
  vibe:'霉豆腐煎到酥脆，这是安徽人的臭豆腐。',must:['必点','毛豆腐 · 火腿炖甲鱼汤'],chips:[['','徽菜本味']],q:'黄山毛豆腐'}]},
{tab:'D2',name:'黄山全天',sub:'索道上山 · 山上住宿 · 中',start:540,hardEnd:1380,drive:'0.5 h',
 pre:{mode:'drive',conn:'→ 黄山温泉站 · 25 km · 35 分',min:35,km:25,cost:0},
 post:null,
 stops:[
 {k:'huangshan-up',name:'黄山 · 云谷索道上山',cng:'最美名山',era:'海拔 1,864 m',dur:30,prio:0,cost:270,cat:'tix',indoor:false,dep:{first:480,every:20,last:960},
  vibe:'8:30 上山，赶在云海散前到达白鹅岭。',must:['必做','云谷→北海·先去北海再南走迎客松'],chips:[['down','限流·旺季提前 7 天预约'],['','票含索道']],q:'黄山景区'},
 {mode:'walk',conn:'步行北海→西海大峡谷 · 60 分',min:60,cost:0},
 {k:'xihai-valley',name:'西海大峡谷 · 地轨列车',cng:'最美名山',era:'悬谷峰林',dur:180,prio:0,cost:80,cat:'tix',indoor:false,
  vibe:'峰从脚下往下长，云从峰里往上走。',must:['必看','地轨列车到谷底 · 步道走 S 形'],chips:[['','缆车¥80']],q:'黄山西海大峡谷'},
 {mode:'walk',conn:'步行→光明顶 · 40 分',min:40,cost:0},
 {k:'bright-peak',name:'光明顶 · 日落',cng:'最美名山',era:'1,860 m 顶',dur:60,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'黄山第二高峰，日落时光整个山头变成铁锈色。',must:['必看','18 点后的长影子'],chips:[['up','免票（景区票已含）']],q:'光明顶'},
 {k:'huangshan-lodge',name:'山上住宿 · 等明日日出',era:'夜宿峰顶',dur:60,prio:0,cost:0,cat:'free',indoor:true,
  vibe:'黄山最值钱的体验：一觉睡到云海里。',must:['必做','带保暖层 · 日出前 1 小时到观景台排位'],chips:[['down','山上住宿需提前官网预订']],q:'黄山山上住宿'}]},
{tab:'D3',name:'宏村 · 返程',sub:'下山 + 宏村 + 还车 · 轻',start:390,hardEnd:1290,drive:'3 h',
 pre:null,post:{mode:'drive',conn:'宏村 → 杭州 · 270 km · 约 3 小时 30 分',min:210,km:270,cost:45},
 stops:[
 {k:'hs-dawn',name:'黄山 · 日出',cng:'最美名山',era:'6:30 黄金时刻',dur:90,prio:0,cost:0,cat:'free',indoor:false,earliest:360,
  vibe:'排好了，日出从莲花峰后面出来，整片云海一下亮了。',must:['必看','清凉台·始信峰选一 · 太热门早到'],chips:[['up','免票']],q:'黄山日出'},
 {mode:'walk',conn:'步行下山 · 慈光阁索道 · 50 分',min:50,cost:80},
 {mode:'drive',conn:'→ 宏村 · 25 km · 30 分',min:30,km:25,cost:0},
 {k:'hongcun',name:'宏村 · 徽派古村',cng:'最美古镇',era:'900 年徽商村',dur:150,prio:0,cost:104,cat:'tix',indoor:false,
  vibe:'牛形村落，月沼是它的胃，南湖是它的肚子。南屏比宏村更安静。',must:['必看','月沼倒影 · 承志堂木雕 · 走到村后山坡'],chips:[['','门票¥104']],q:'宏村'},
 {k:'hs-return',name:'还车 · 杭州',era:'满油交车',dur:40,prio:0,cost:0,cat:'tix',indoor:true,
  vibe:'三天，黄山在身上的松香还没散。',must:['必做','满油 · 对公里数'],chips:[['','留足 40 分']],q:'杭州 租车还车'}]}];
const HS3_LODGES=[
 {city:'黄山市屯溪老街',price:280,why:'古城步行圈 · 明早出发顺',q:'屯溪老街'},
 {city:'黄山山上 · 北海宾馆',price:800,why:'日出最佳机位 50 m · 提前预订',q:'黄山北海宾馆'},
 null];

/* ═══ 黄山 2 天：直接上山过夜，日出后下山收宏村 ═══ */
const HS2_D1={tab:'D1',name:'杭州 → 黄山 · 直接上山',sub:'300 km + 索道 · 中',start:450,hardEnd:1380,drive:'4 h',
 pre:null,post:null,
 stops:[
 {k:'hs-pickup',name:'杭州提车 · 验车',era:'租车站',dur:40,prio:0,cost:0,cat:'tix',indoor:true,
  vibe:'高速为主，小车够用。',must:['必做','绕车拍视频 · 查胎压'],chips:[['','小车即可']],q:'杭州 租车'},
 {mode:'drive',conn:'杭州 → 黄山风景区南大门 · 300 km · 约 4 小时',min:245,km:300,cost:120,
  via:'沿途 · 杭瑞高速 · 山区路段雨天慢行'},
 {k:'huangshan-up',name:'黄山 · 云谷索道上山',era:'8 分钟垂直 700 m',dur:30,prio:0,cost:270,cat:'tix',indoor:false,
  vibe:'缆车一出树线，整片花岗岩峰林铺开。',
  must:['必做','门票+索道当日现场 · 旺季提前网购'],chips:[['','门票¥190+索道¥80'],['down','旺季排队 30 分+']],q:'黄山云谷索道'},
 {k:'xihai-valley',name:'西海大峡谷 · 地轨列车',cng:'最美名山',era:'黄山最险栈道',dur:180,prio:0,cost:80,cat:'tix',indoor:false,
  vibe:'栈道贴着崖壁绕进谷底，云从脚下涌上来。',
  must:['必走','一环二环走到底 · 地轨¥80 省 1.5 h 腿力'],chips:[['','地轨¥80'],['down','雨天路滑']],q:'黄山西海大峡谷'},
 {k:'bright-peak',name:'光明顶 · 日落',era:'黄山第二高峰',dur:60,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'一天里最后的光把莲花峰烧红。',must:['必看','日落前 40 分占位'],chips:[['up','免票']],q:'黄山光明顶'},
 {k:'huangshan-lodge',name:'山上住宿 · 等明日日出',era:'日出机位 50 m',dur:60,prio:0,cost:0,cat:'free',indoor:true,
  vibe:'山上房间小而贵，但明早不用赶路。',must:['必做','问清日出时间 · 借军大衣'],chips:[['down','必须提前预订']],q:'黄山北海宾馆'}]};
const HS2_DAYS=[HS2_D1, Object.assign({},HS3_DAYS[2],{tab:'D2'})];
const HS2_LODGES=[
 {city:'黄山山上 · 北海宾馆',price:800,why:'日出最佳机位 50 m · 提前预订',q:'黄山北海宾馆'},
 null];


/* ── 注册三条新路线 ──────────────────────────────── */
Object.assign(ROUTES,{
 xz7:{name:'西藏拉萨线',dest:'西藏 · 拉萨入藏',fam:'xz',days:XZ7_DAYS,lodges:XZ7_LODGES,
  cluster:null,inserts:null,defSels:{},defSelsM:null,
  nights:6,rent:4200,roadfood:400,perCar:true,nav:'amap',strength:'中',
  dayVariants:[7],
  carLabel:'租车 · 油费（向导费¥2,000 含组内）',tixLabel:'门票与入场批次',foodLabel:'餐饮 · 含路餐',
  overTip:'可换日喀则平价房',
  budgets:[{l:'宽松',v:7500},{l:'精打细算',v:6500}],
  thrift(){ lodge4=1; },
  tastes:[{id:'photo',apply(){ addP('拍照控 · 纳木错银河') }},{id:'hike',apply(){ addP('走走走 · 布达拉宫台阶') }}],
  defTasteIds:['photo','folk'],
  title:'🏔 西藏拉萨 7 天 · 入藏经典圈',meta:'西藏 · 7天6晚 · 拉萨→羊湖→日喀则→纳木错',
  why:'经典入藏圈：拉萨两晚适应高反，羊卓雍错日间转，日喀则班禅寺，最后两晚留在纳木错等银河。全程无需走回头路，自驾环形一圈完成。',
  weather:'西藏 8 月 · 拉萨昼 22°C 夜 10°C · 雨季午后多阵雨 · 高原紫外线极强',
  seasons:[{in:true,name:'布达拉宫限流',why:'2300 人/天 · 提前 10 天官网抢',tag:'已排入 D2',ver:1},
   {in:false,name:'冬季朝圣',why:'10-12 月少雨，人少，朝圣者最多',pick:{key:'xz-winter',name:'西藏冬季',ptext:'冬季控'}}],
  extras:[{later:{key:'ebc',name:'珠峰大本营',why:'需多住定日两晚·本次不排',ptext:'登山控'}},
   {later:{key:'namcha',name:'南迦巴瓦·雅鲁藏布',why:'需加3天·林芝段',ptext:'峡谷控'}}],
  extrasSub:'备着的还有 玩 34 · 吃 12 · 住 18',
  todos(){ return [
   {k:'permit',tag:['down','证件'],text:'西藏旅游证（藏旅证）· 提前 10 天在藏旅互联网预约',v:'更新 08-03',url:'https://www.xzta.gov.cn'},
   {k:'potala',tag:['down','预约'],text:'布达拉宫限流票 · 提前 10 天官网预约（potalapalace.cn）',v:'更新 08-03',url:'https://www.potalapalace.cn'},
   {k:'guide',tag:['down','向导'],text:'进藏自驾须有持证向导同行（法规要求）· 导游费约 ¥2,000/车',v:''},
   {k:'alt',tag:['down','高反'],text:'前 24h 最严重 · 高反药+氧气罐 · 头痛立刻下山',v:''},
   {k:'car',tag:['down','租车'],text:'拉萨当地 SUV 租车 · 验车时确认备胎防冻液',v:''},
   {k:'fuel',tag:['','纪律'],text:'日喀则至额济纳加满油 · 高原燃油消耗比平原高 15%',v:''}]; },
  map:{nodes:XZ_NODES,order:[0,1,2,3],loop:true,
   seg:[null,null,[0,1],[0,2],[2,3],null,[3,0]],
   tonight:[0,0,0,2,3,3,-1]}},

 nm4:{name:'额济纳胡杨',dest:'内蒙古 · 额济纳',fam:'nm',days:NM4_DAYS,lodges:NM4_LODGES,
  cluster:null,inserts:null,defSels:{},defSelsM:null,
  nights:3,rent:1800,roadfood:200,perCar:true,nav:'amap',strength:'轻',
  dayVariants:[4],
  carLabel:'租车 · 油费',tixLabel:'景区联票',foodLabel:'餐饮 · 含路餐',
  overTip:'可换旗中心标准房',
  budgets:[{l:'宽松',v:2750},{l:'精打细算',v:2450}],
  thrift(){ lodge4=1; },
  tastes:[{id:'photo',apply(){ addP('拍照控 · 胡杨金黄') }},{id:'chill',apply(){ addP('躺平型 · 林间散步') }}],
  defTasteIds:['photo'],
  title:'🌾 额济纳·胡杨林 4 天 · 10 月金秋',meta:'内蒙古额济纳 · 4天3晚 · 10月最佳',
  why:'十月初到中旬是胡杨最黄的时候，错过就要再等一年。D2 走一二三道桥主拍位，D3 走四到八道桥和怪树林，两天节奏不同，互不重复。',
  weather:'额济纳 10 月 · 昼 18–25°C 夜 0–5°C · 昼夜温差大 · 晴天多',
  seasons:[{in:false,name:'胡杨最金 10 月上中旬',why:'最佳窗口窄·峰值约5-7天',pick:{key:'nm-oct',name:'胡杨金秋',ptext:'最佳时机'}}],
  extras:[{later:{key:'juyan',name:'居延海候鸟',why:'已排进 D3 下午',inDay:'居延海',ptext:'观鸟控'}}],
  extrasSub:'备着的还有 玩 9 · 吃 6 · 住 8',
  todos(){ return [
   {k:'leaf',tag:['down','时机'],text:'提前查当年胡杨黄叶进度 · 颜色到80%时出发',v:'每年不同'},
   {k:'tix',tag:['down','门票'],text:'额济纳胡杨林联票 · 旺季网上抢购',v:''},
   {k:'fuel',tag:['','纪律'],text:'酒泉满箱出发 · 旗里加油补满 · 无高速无油站',v:''},
   {k:'cold',tag:['','装备'],text:'夜里 0°C+ · 抓绒+羽绒人手一件',v:''}]; },
  map:{nodes:NM_NODES,order:[0,1],loop:false,
   seg:[[0,1],null,null,[1,0]],
   tonight:[1,1,1,-1]}},

 hs3:{name:'黄山·徽州',dest:'安徽 · 黄山',fam:'hs',days:HS3_DAYS,lodges:HS3_LODGES,
  cluster:null,inserts:null,defSels:{},defSelsM:null,
  nights:2,rent:900,roadfood:160,perCar:true,nav:'amap',strength:'中',
  dayVariants:[2,3],
  carLabel:'租车 · 油费 · 路桥',tixLabel:'黄山门票 · 宏村门票',foodLabel:'餐饮',
  overTip:'可换山下住宿（轻便版）',
  budgets:[{l:'宽松',v:2900},{l:'精打细算',v:2600}],
  thrift(){ lodge4=1; },
  tastes:[{id:'photo',apply(){ addP('拍照控 · 云海等位') }},{id:'hike',apply(){ addP('走走走 · 西海大峡谷') }}],
  defTasteIds:['photo'],
  title:'🏔 黄山·宏村 3 天 · 华东最强周末',meta:'安徽黄山 · 3天2晚 · 周五出发 · 杭州/上海高铁/自驾',
  why:'杭州出发 3.5 小时到黄山，D1 徽州古城落脚，D2 全天黄山必须住山上才能等日出，D3 宏村收官返杭。山上住宿必须提前预订。',
  weather:'黄山 8 月 · 山顶昼 18°C 夜 12°C · 云海概率高 · 带雨衣',
  seasons:[{in:true,name:'黄山云海',why:'雨后第二天出现概率最高',tag:'进山时查预报',ver:0},
   {in:false,name:'黄山冬雪',why:'12-2 月雾凇雪景 · 本季未到',pick:{key:'hs-snow',name:'黄山冬雪',ptext:'雪景控'}}],
  inserts:{
   xidi:{day:2, afterK:'hongcun', label:'D3', brief:'宏村南 15 km · 徽派牌坊与私塾 · 约 90 分 · ¥104',
     profile:'古村控',
     stop:{k:'xidi',name:'西递古村',era:'胡氏聚族 900 年',dur:90,prio:2,cost:104,cat:'tix',indoor:false,
       vibe:'比宏村安静，青石巷子里晒着笋干，门楣上的砖雕还留着当年的讲究。',
       must:['必看','胡文光牌坊 · 走进追慕堂看藻井'],
       chips:[['','门票¥104'],['up','人比宏村少']],
       q:'西递古村',pt:[268,132]},
     conns:[{mode:'drive',conn:'宏村 → 西递 · 15 km · 20 分',min:20,km:15,cost:0},
            {mode:'drive',conn:'西递 → 杭州方向 · 并入返程',min:20,km:15,cost:0}]}
  },
  extras:[{ins:'xidi'}],
  extrasSub:'备着的还有 玩 12 · 吃 8 · 住 5',
  todos(){ return [
   {k:'hs-tix',tag:['down','预约'],text:'黄山限流 · 官网提前 3 天预约 · 山上住宿同步订',v:'更新 08-03',url:'https://www.huangshan.com.cn'},
   {k:'hongcun',tag:['','预约'],text:'宏村旺季周末可以提前买好门票',v:''},
   {k:'car',tag:['','租车'],text:'杭州周末租车提前一周预订 · 长假前后难租',v:''},
   {k:'jacket',tag:['','装备'],text:'山上比山下低 8-10°C · 抓绒+雨衣必备',v:''}]; },
  map:{nodes:HS_NODES,order:[0,1,2],loop:false,
   seg:[[0,1],null,[1,2]],
   tonight:[1,1,-1]}},
});


/* ── 梅里雪山·雨崩 6 天（丽江进出）───────────────── */
const MLS_NODES=[
 {n:'丽江',x:500,y:300,lx:13,ly:4,a:'start'},
 {n:'香格里拉',x:400,y:200,lx:13,ly:4,a:'start'},
 {n:'飞来寺',x:280,y:120,lx:-2,ly:-10,a:'middle'},
 {n:'雨崩',x:240,y:168,lx:-2,ly:16,a:'end'}];
const MLS6_DAYS=[
{tab:'D1',name:'丽江 → 香格里拉',sub:'180 km · 约 3.5 h · 轻',start:570,hardEnd:1320,drive:'3.5 h',
 pre:null,post:{mode:'walk',conn:'步行回古城住处 · 8 分',min:8,cost:0},
 stops:[
 {k:'mls-pickup',name:'丽江提车 · 验车',era:'租车站',dur:45,prio:0,cost:0,cat:'tix',indoor:true,
  vibe:'滇藏线第一段，SUV 稳一点。',must:['必做','绕车拍视频 · 查备胎防冻液'],chips:[['up','SUV 建议']],q:'丽江 租车'},
 {mode:'drive',conn:'丽江 → 香格里拉 · 180 km · 约 3 小时 30 分',min:210,km:180,cost:35,
  via:'沿途 · 金沙江河谷 · 小中甸花海随停（6-7 月）'},
 {k:'dukezong',name:'独克宗古城 · 转经筒',era:'月光之城',dur:120,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'世界最大转经筒要五六个人才推得动，黄昏的古城安静下来。',
  must:['必看','龟山公园大转经筒推三圈 · 四方街喝碗酥油茶'],chips:[['up','免票'],['down','海拔 3,300 m 慢走']],q:'独克宗古城'}]},
{tab:'D2',name:'香格里拉 → 飞来寺',sub:'190 km · 约 4 h · 中',start:540,hardEnd:1320,drive:'4 h',
 pre:{mode:'drive',conn:'香格里拉 → 飞来寺 · 190 km · 约 4 小时',min:240,km:190,cost:0,
   via:'沿途 · 金沙江大湾观景台 · 白马雪山垭口 4,292 m'},
 post:{mode:'walk',conn:'步行回观景住处 · 3 分',min:3,cost:0},
 stops:[
 {k:'jinsha-bend',name:'金沙江大湾',era:'月亮湾',dur:45,prio:1,cost:20,cat:'tix',indoor:false,
  vibe:'江水在这里拐了一个 180 度的弯，把山抱在怀里。',must:['必看','观景台最高层 · 全湾收进来'],chips:[['','门票¥20']],q:'金沙江大湾'},
 {mode:'drive',conn:'→ 白马雪山垭口 → 飞来寺 · 110 km · 约 2 小时 30 分',min:150,km:110,cost:0},
 {k:'feilai-dusk',name:'飞来寺 · 梅里十三峰全景',cng:'最美名山',era:'卡瓦格博 6,740 m',dur:0,openUntil:1230,openMin:60,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'十三座雪峰一字排开，卡瓦格博至今无人登顶。',
  must:['必看','日落后雪山剪影 · 明早在这里等日照金山'],chips:[['up','观景台免票']],q:'飞来寺观景台'}]},
{tab:'D3',name:'日照金山 · 徒步进雨崩',sub:'12 km 上坡徒步 · 重',start:420,hardEnd:1290,drive:'1 h',
 pre:null,post:{mode:'walk',conn:'步行进上村客栈 · 10 分',min:10,cost:0},
 stops:[
 {k:'golden-peak',name:'日照金山 · 飞来寺',cng:'最美名山',era:'黄金 20 分钟',dur:90,prio:0,cost:0,cat:'free',indoor:false,earliest:420,
  vibe:'太阳先点亮卡瓦格博的顶，然后金色一路淌下来。',
  must:['必看','日出前 30 分钟站好机位 · 雨季看到靠运气'],chips:[['up','免票'],['down','10-5 月晴率高 · 雨季难见']],q:'飞来寺日照金山'},
 {mode:'drive',conn:'飞来寺 → 西当村徒步起点 · 30 km · 约 1 小时',min:60,km:30,cost:0},
 {k:'yubeng-in',name:'徒步进雨崩 · 南宗垭口',era:'12 km · 爬升 1,100 m',dur:360,prio:0,cost:230,cat:'tix',indoor:false,
  vibe:'翻过 3,700 m 的南宗垭口，雪山脚下的村子就到了。',
  must:['必做','门票含生态车 · 骑骡子可省一半体力（另 ¥300）'],chips:[['down','6 小时徒步 · 量力'],['','票含接驳']],q:'雨崩村徒步'}]},
{tab:'D4',name:'雨崩 → 冰湖往返',sub:'14 km 高海拔徒步 · 重',start:480,hardEnd:1230,drive:'0 h',
 pre:null,post:{mode:'walk',conn:'回下村客栈 · 20 分',min:20,cost:0},
 stops:[
 {k:'ice-lake',name:'冰湖 · 卡瓦格博脚下',cng:'最美名山',era:'海拔 3,900 m',dur:300,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'冰川融水积成的湖，绿得像块玉，头顶就是主峰冰壁。',
  must:['必看','笑农大本营歇脚 · 湖边别久留（落石区）'],chips:[['up','免票'],['down','往返 6-7 小时']],q:'雨崩冰湖'},
 {k:'yubeng-night',name:'雨崩下村 · 星空',era:'无光污染',dur:60,prio:2,cost:0,cat:'free',indoor:false,
  vibe:'村里熄灯后，银河从雪山后面升起来。',must:['必看','裹紧点 · 十点后最清楚'],chips:[['up','免票']],q:'雨崩村'}]},
{tab:'D5',name:'徒步出山 → 香格里拉',sub:'尼农线 9 km + 车 4 h · 重',start:480,hardEnd:1320,drive:'4 h',
 pre:null,post:{mode:'walk',conn:'步行回住处 · 8 分',min:8,cost:0},
 stops:[
 {k:'ninong-out',name:'尼农大峡谷 · 徒步出山',era:'9 km 缓下坡',dur:240,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'沿着水渠走出峡谷，澜沧江在脚下越来越近。',
  must:['必做','靠山侧行走 · 峡谷段不要停留拍照'],chips:[['down','悬崖水渠路 · 恐高慎选（可原路西当出）']],q:'尼农大峡谷'},
 {mode:'drive',conn:'尼农 → 香格里拉 · 180 km · 约 4 小时',min:240,km:180,cost:0,
  via:'沿途 · 澜沧江峡谷 · 白马雪山二次翻越'}]},
{tab:'D6',name:'香格里拉 → 丽江还车',sub:'180 km · 约 3.5 h · 轻',start:540,hardEnd:1230,drive:'3.5 h',
 pre:{mode:'drive',conn:'香格里拉 → 丽江 · 180 km · 约 3 小时 30 分',min:210,km:180,cost:35,
   via:'沿途 · 虎跳峡镇可停 · 拉市海随停'},
 post:null,
 stops:[
 {k:'mls-return',name:'还车 · 丽江',era:'满油交车',dur:45,prio:0,cost:0,cat:'tix',indoor:true,
  vibe:'六天，雪山住进身体里了。',must:['必做','满油 · 对公里数 · 拍视频'],chips:[['','留足 45 分']],q:'丽江 租车还车'}]}];
const MLS6_LODGES=[
 {city:'香格里拉 · 独克宗',price:320,why:'古城里 · 转经筒步行 5 分',q:'独克宗古城客栈'},
 {opts:[{city:'飞来寺 · 金山景观房',price:460,why:'躺床上等日照金山',q:'飞来寺观景酒店'},
        {city:'飞来寺 · 普通标间',price:320,why:'省 ¥70/人 · 走 3 分到观景台',q:'飞来寺'}]},
 {city:'雨崩上村 · 客栈',price:280,why:'进村先到 · 明早往冰湖近',q:'雨崩上村客栈'},
 {city:'雨崩下村 · 客栈',price:280,why:'神瀑线和出山线都顺',q:'雨崩下村客栈'},
 {city:'香格里拉 · 独克宗',price:320,why:'出山落脚 · 好好洗个澡',q:'独克宗古城客栈'},
 null];

/* ── 呼伦贝尔 5 天（海拉尔进 · 满洲里出）──────────── */
const HLB_NODES=[
 {n:'海拉尔',x:420,y:260,lx:13,ly:4,a:'start'},
 {n:'额尔古纳',x:360,y:150,lx:13,ly:-8,a:'start'},
 {n:'室韦',x:400,y:60,lx:13,ly:4,a:'start'},
 {n:'莫尔道嘎',x:470,y:96,lx:13,ly:14,a:'middle'},
 {n:'黑山头',x:300,y:176,lx:-2,ly:16,a:'middle'},
 {n:'满洲里',x:180,y:230,lx:-2,ly:16,a:'end'}];
const HLB5_DAYS=[
{tab:'D1',name:'海拉尔 → 额尔古纳',sub:'130 km · 草原第一天 · 轻',start:570,hardEnd:1320,drive:'2.5 h',
 pre:null,post:{mode:'walk',conn:'步行回住处 · 5 分',min:5,cost:0},
 stops:[
 {k:'hlb-pickup',name:'海拉尔提车 · 验车',era:'租车站',dur:45,prio:0,cost:0,cat:'tix',indoor:true,
  vibe:'草原公路笔直到天边，油要满箱。',must:['必做','绕车拍视频 · 备防蚊液'],chips:[['','小车即可']],q:'海拉尔 租车'},
 {mode:'drive',conn:'海拉尔 → 金帐汗 · 40 km · 50 分',min:50,km:40,cost:0},
 {k:'mrgl-river',name:'莫日格勒河 · 九曲十八弯',cng:'最美草原',era:'天下第一曲水',dur:120,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'河在草原上随手画了几十个弯，老舍说它是天下第一曲水。',
  must:['必看','制高点俯瞰全弯 · 别开车碾草场'],chips:[['up','观景免票'],['down','景区内骑马另计']],q:'莫日格勒河'},
 {mode:'drive',conn:'→ 额尔古纳 · 90 km · 约 1 小时 40 分',min:100,km:90,cost:0},
 {k:'eegn-wet',name:'额尔古纳湿地 · 黄昏',cng:'最美湿地',era:'亚洲第一湿地',dur:0,openUntil:1200,openMin:75,prio:1,cost:65,cat:'tix',indoor:false,
  vibe:'根河在湿地里摊开成一面面镜子，落日一块块点亮它们。',
  must:['必看','木栈道走到最高观景台'],chips:[['','门票¥65']],q:'额尔古纳湿地'}]},
{tab:'D2',name:'额尔古纳 → 室韦',sub:'160 km · 白桦林+俄乡 · 轻',start:570,hardEnd:1320,drive:'3 h',
 pre:{mode:'drive',conn:'额尔古纳 → 白桦林 · 40 km · 50 分',min:50,km:40,cost:0},
 post:{mode:'walk',conn:'步行回木刻楞 · 5 分',min:5,cost:0},
 stops:[
 {k:'birch-forest',name:'白桦林景区',era:'姑娘一样的树',dur:90,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'一整片白桦，风一吹叶子哗哗响，随手一拍都是明信片。',
  must:['必看','栈道深处人少 · 别刻字'],chips:[['up','免票（小火车另计）']],q:'额尔古纳白桦林'},
 {mode:'drive',conn:'→ 恩和 → 室韦 · 120 km · 约 2 小时 10 分',min:130,km:120,cost:0,
  via:'沿途 · 恩和俄罗斯族村可停 · 哈乌尔河展望台'},
 {k:'shiwei',name:'室韦 · 中俄界河',era:'俄罗斯族民族乡',dur:150,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'额尔古纳河对岸就是俄罗斯村庄，晚上住木刻楞，吃列巴蘸蓝莓酱。',
  must:['必看','界河边走一段 · 木刻楞家庭旅馆的晚餐'],chips:[['up','村子免票'],['','界河游船¥50 自选']],q:'室韦'}]},
{tab:'D3',name:'室韦 → 莫尔道嘎',sub:'110 km · 大兴安岭 · 轻',start:570,hardEnd:1290,drive:'2.5 h',
 pre:{mode:'drive',conn:'室韦 → 莫尔道嘎 · 110 km · 约 2 小时 30 分',min:150,km:110,cost:0,
   via:'沿途 · 临江神仙坡日出可起早 · 老鹰嘴random停'},
 post:{mode:'walk',conn:'步行回住处 · 5 分',min:5,cost:0},
 stops:[
 {k:'medg-park',name:'莫尔道嘎森林公园 · 龙岩山',era:'大兴安岭腹地',dur:150,prio:0,cost:80,cat:'tix',indoor:false,
  vibe:'中国最后一片寒温带原始林，落叶松一直铺到天边。',
  must:['必看','龙岩山顶看林海 · 9 月中下旬变金色'],chips:[['','门票¥80'],['down','防蚊必备']],q:'莫尔道嘎森林公园'},
 {k:'medg-town',name:'莫尔道嘎镇 · 晚市',era:'林区小镇',dur:0,openUntil:1200,openMin:45,prio:2,cost:55,cat:'food',indoor:true,
  vibe:'林区人实在，铁锅炖江鱼分量吓人。',must:['必点','铁锅炖 · 蓝莓汁'],chips:[['','人均¥55']],q:'莫尔道嘎 铁锅炖'}]},
{tab:'D4',name:'莫尔道嘎 → 黑山头',sub:'230 km · 骑马与日落 · 中',start:540,hardEnd:1320,drive:'4 h',
 pre:{mode:'drive',conn:'莫尔道嘎 → 额尔古纳 → 黑山头 · 230 km · 约 4 小时',min:240,km:230,cost:0,
   via:'沿途 · 卡线草原段随停 · 额尔古纳加满油'},
 post:{mode:'walk',conn:'步行进蒙古包营地 · 5 分',min:5,cost:0},
 stops:[
 {k:'heishantou-horse',name:'黑山头 · 草原骑马',cng:'最美草原',era:'马背民族腹地',dur:120,prio:0,cost:150,cat:'tix',indoor:false,
  vibe:'跟着马倌小跑起来，草原才真正属于你。',
  must:['必做','选正规马场 · 头盔护具都要'],chips:[['','1 小时¥150'],['down','听马倌指挥']],q:'黑山头骑马'},
 {k:'heishantou-sunset',name:'黑山头 · 日落山',era:'草原落日标准机位',dur:90,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'太阳沉进草原尽头，整片天从金烧到紫。',must:['必看','提前 40 分钟占机位'],chips:[['up','免票']],q:'黑山头日落山'}]},
{tab:'D5',name:'黑山头 → 满洲里还车',sub:'190 km · 边境收官 · 轻',start:540,hardEnd:1230,drive:'3 h',
 pre:{mode:'drive',conn:'黑山头 → 呼伦湖 → 满洲里 · 190 km · 约 3 小时',min:180,km:190,cost:0,
   via:'沿途 · 边防公路草原段 · 呼伦湖金海岸'},
 post:null,
 stops:[
 {k:'hulun-lake',name:'呼伦湖 · 金海岸',cng:'最美湖泊',era:'内蒙第一大湖',dur:75,prio:1,cost:30,cat:'tix',indoor:false,
  vibe:'草原上的海，风大浪也大。',must:['必看','湖边走走就好 · 别下水'],chips:[['','门票¥30']],q:'呼伦湖'},
 {mode:'drive',conn:'→ 满洲里 · 40 km · 40 分',min:40,km:40,cost:0},
 {k:'hlb-return',name:'满洲里 · 还车',era:'国门边城',dur:45,prio:0,cost:0,cat:'tix',indoor:true,
  vibe:'套娃广场和国门就在城边，还完车打车去转一圈。',
  must:['必做','异地还车费提前确认 · 满油交车'],chips:[['down','异地还车费约¥400/车']],q:'满洲里 租车还车'}]}];
const HLB5_LODGES=[
 {city:'额尔古纳市区',price:360,why:'湿地公园 10 分钟 · 补给方便',q:'额尔古纳'},
 {city:'室韦 · 木刻楞',price:380,why:'俄式木屋 · 界河边',q:'室韦木刻楞'},
 {city:'莫尔道嘎镇',price:300,why:'林区小镇 · 明早进园近',q:'莫尔道嘎'},
 {opts:[{city:'黑山头 · 星空蒙古包',price:420,why:'躺着看银河',q:'黑山头蒙古包'},
        {city:'黑山头 · 标准间',price:300,why:'省 ¥60/人 · 怕冷选这个',q:'黑山头'}]},
 null];

/* ── 注册：梅里 + 呼伦贝尔 ───────────────────────── */
Object.assign(ROUTES,{
 mls6:{name:'梅里雪山·雨崩',dest:'云南 · 梅里雪山',fam:'mls',days:MLS6_DAYS,lodges:MLS6_LODGES,
  cluster:null,inserts:null,defSels:{},defSelsM:null,
  nights:5,rent:2600,roadfood:360,perCar:true,nav:'amap',strength:'重',
  dayVariants:[6],
  carLabel:'租车 · 油费 · 路桥',tixLabel:'门票与进山票',foodLabel:'餐饮 · 含路餐',
  overTip:'可换飞来寺普通标间',
  budgets:[{l:'宽松',v:3950},{l:'精打细算',v:3500}],
  thrift(){ lodge4=1; },
  tastes:[{id:'hike',apply(){ addP('走走走 · 雨崩全程徒步') }},{id:'photo',apply(){ addP('拍照控 · 日照金山蹲守') }}],
  defTasteIds:['hike','photo'],
  title:'🗻 梅里雪山·雨崩 6 天 · 神山脚下',meta:'云南梅里 · 6天5晚 · 08-25 出发',
  why:'滇西北的终极一站：D2 傍晚先看十三峰全景，D3 清晨蹲日照金山后徒步进雨崩，D4 冰湖往返，D5 尼农峡谷出山。两天徒步是体力活，但雪山会把它全还给你。',
  weather:'梅里 8 月 · 昼 12–20°C 夜 4–8°C · 雨季云多 · 金山看运气',
  seasons:[{in:true,name:'雨崩徒步季',why:'6-10 月路况最好 · 雨具必备',tag:'已排入 D3-D5',ver:1},
   {in:false,name:'日照金山高概率期',why:'10-5 月晴率高 · 雨季全靠缘分',pick:{key:'mls-winter',name:'金山季再来',ptext:'金山控'}}],
  extras:[{later:{key:'shenpu',name:'神瀑线',why:'雨崩另一条线 · 需多住一天',ptext:'徒步控'}}],
  extrasSub:'备着的还有 玩 14 · 吃 6 · 住 8',
  todos(){ return [
   {k:'yubeng',tag:['down','进山'],text:'雨崩门票实名 · 旺季提前 3 天线上购（含生态车）',v:'更新 08-03'},
   {k:'fit',tag:['down','体力'],text:'两天徒步 26 km · 出发前两周开始爬楼训练',v:''},
   {k:'alt',tag:['down','高反'],text:'垭口 3,700 m · 高反药备好 · 头痛就骑骡子',v:''},
   {k:'lodge2',tag:['up','确认'],text:'飞来寺金山景观房旺季紧俏 · 提前订',v:''},
   {k:'rain',tag:['','装备'],text:'雨衣+登山杖+防水鞋 · 雨季必备三件',v:''},
   {k:'fuel',tag:['','纪律'],text:'香格里拉满箱 · 飞来寺油贵且少',v:''}]; },
  map:{nodes:MLS_NODES,order:[0,1,2,3],loop:true,
   seg:[[0,1],[1,2],[2,3],null,[3,1],[1,0]],
   tonight:[1,2,3,3,1,-1]}},

 hlb5:{name:'呼伦贝尔',dest:'内蒙古 · 呼伦贝尔',fam:'hlb',days:HLB5_DAYS,lodges:HLB5_LODGES,
  cluster:null,inserts:null,defSels:{},defSelsM:null,
  nights:4,rent:2200,roadfood:300,perCar:true,nav:'amap',strength:'轻',
  dayVariants:[5],
  carLabel:'租车 · 油费（含异地还车费）',tixLabel:'门票与骑马',foodLabel:'餐饮 · 含路餐',
  overTip:'可换黑山头标准间',
  budgets:[{l:'宽松',v:3400},{l:'精打细算',v:3100}],
  thrift(){ lodge4=1; },
  tastes:[{id:'photo',apply(){ addP('拍照控 · 九曲与日落') }},{id:'chill',apply(){ addP('躺平型 · 草原发呆') }}],
  defTasteIds:['photo','chill'],
  title:'🌾 呼伦贝尔 5 天 · 草原到边城',meta:'内蒙呼伦贝尔 · 5天4晚 · 海拉尔进满洲里出',
  why:'不走回头路的草原线：D1 九曲十八弯和湿地，D2 白桦林到中俄界河，D3 钻进大兴安岭，D4 黑山头骑马看日落，D5 沿边防公路到满洲里收官。7-8 月草最绿。',
  weather:'呼伦贝尔 8 月 · 昼 18–26°C 夜 8–13°C · 昼夜温差大 · 午后偶阵雨',
  seasons:[{in:true,name:'草原盛季',why:'7-8 月草最绿 · 蚊虫也最多',tag:'防蚊液已列装备',ver:1},
   {in:false,name:'莫尔道嘎金秋',why:'9 月中下旬落叶松全金 · 本次未到季',pick:{key:'hlb-autumn',name:'大兴安岭秋色',ptext:'秋色控'}}],
  extras:[{later:{key:'aoluguya',name:'敖鲁古雅驯鹿部落',why:'根河方向 · 需绕 150 km',ptext:'民俗控'}}],
  extrasSub:'备着的还有 玩 16 · 吃 8 · 住 9',
  todos(){ return [
   {k:'car',tag:['down','还车'],text:'满洲里异地还车费约 ¥400/车 · 订车时确认',v:'更新 08-03'},
   {k:'horse',tag:['down','安全'],text:'骑马选正规马场 · 头盔护具缺一不可',v:''},
   {k:'bug',tag:['','装备'],text:'防蚊液+长袖 · 草原蚊子认真的',v:''},
   {k:'fuel',tag:['','纪律'],text:'额尔古纳、莫尔道嘎各加满一次 · 卡线加油站稀',v:''},
   {k:'cold',tag:['','装备'],text:'早晚 10°C 上下 · 抓绒带一件',v:''}]; },
  map:{nodes:HLB_NODES,order:[0,1,2,3,4,5],loop:false,
   seg:[[0,1],[1,2],[2,3],[3,4],[4,5]],
   tonight:[1,2,3,4,-1]}},
});


/* ── 桂林·阳朔 4 天（漓江峰林）───────────────────── */
const GL_NODES=[
 {n:'桂林',x:300,y:120,lx:13,ly:4,a:'start'},
 {n:'龙脊',x:220,y:56,lx:-2,ly:-10,a:'start'},
 {n:'兴坪',x:368,y:220,lx:13,ly:4,a:'middle'},
 {n:'阳朔',x:316,y:264,lx:-2,ly:16,a:'end'}];
const GL4_DAYS=[
{tab:'D1',name:'桂林 → 龙脊梯田',sub:'90 km 山路 · 轻',start:570,hardEnd:1320,drive:'2.5 h',
 pre:null,post:{mode:'walk',conn:'步行上山到梯田客栈 · 30 分',min:30,cost:0},
 stops:[
 {k:'gl-pickup',name:'桂林提车 · 验车',era:'租车站',dur:40,prio:0,cost:0,cat:'tix',indoor:true,
  vibe:'南方山路多弯，小车灵活。',must:['必做','绕车拍视频 · 山路备晕车药'],chips:[['','小车即可']],q:'桂林 租车'},
 {mode:'drive',conn:'桂林 → 龙脊大寨 · 90 km · 约 2 小时 30 分',min:150,km:90,cost:20,
  via:'沿途 · 最后 20 km 盘山 · 会车慢行'},
 {k:'longji',name:'龙脊梯田 · 金坑大寨',cng:'最美峰林',era:'壮族千年梯田',dur:180,prio:0,cost:80,cat:'tix',indoor:false,
  vibe:'梯田一层层盘到云里，灌水季是镜子，秋收季是金子。',
  must:['必看','西山韶乐观景点走上去 · 日落前光最斜'],chips:[['','门票¥80'],['down','上山 30-50 分 · 可坐缆车¥70']],q:'龙脊梯田大寨'}]},
{tab:'D2',name:'龙脊 → 兴坪 → 阳朔',sub:'170 km · 漓江精华 · 中',start:540,hardEnd:1320,drive:'3.5 h',
 pre:{mode:'drive',conn:'龙脊 → 兴坪古镇 · 150 km · 约 3 小时',min:180,km:150,cost:35,
   via:'沿途 · 桂林绕城 · 兴坪沿江路窄慢行'},
 post:{mode:'drive',conn:'兴坪 → 阳朔 · 25 km · 40 分',min:40,km:25,cost:0},
 stops:[
 {k:'xingping',name:'兴坪 · 20 元人民币机位',cng:'最美峰林',era:'漓江精华段',dur:120,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'掏出一张 20 块对着江面比一比，你就站在人民币里。',
  must:['必看','码头边比对机位 · 老寨山可登顶（往返 1.5 h）'],chips:[['up','江边免票'],['','竹筏漓江段¥118 自选']],q:'兴坪古镇'},
 {k:'xingping-food',name:'啤酒鱼 · 兴坪老店',era:'漓江活鱼',dur:75,prio:1,cost:60,cat:'food',indoor:true,
  vibe:'漓江剑骨鱼配啤酒焖，皮脆汁浓。',must:['必点','啤酒鱼 · 田螺酿'],chips:[['','人均¥60']],q:'兴坪 啤酒鱼'}]},
{tab:'D3',name:'阳朔 · 遇龙河一整天',sub:'骑行+竹筏 · 轻',start:540,hardEnd:1320,drive:'0.5 h',
 pre:{mode:'walk',conn:'租电动车出发 · 10 分',min:10,cost:30},
 post:{mode:'walk',conn:'骑回西街还车 · 20 分',min:20,cost:0},
 stops:[
 {k:'yulong-raft',name:'遇龙河 · 竹筏漂流',cng:'最美峰林',era:'小漓江',dur:120,prio:0,cost:120,cat:'tix',indoor:false,dep:{first:510,every:20,last:1020},
  vibe:'人工竹筏慢慢撑，两岸峰林倒在水里，比漓江更安静。',
  must:['必做','金龙桥-旧县段最美 · 早班人少'],chips:[['','双人筏¥240/筏'],['down','旺季提前一天订']],q:'遇龙河竹筏'},
 {mode:'walk',conn:'骑行十里画廊 · 40 分',min:40,cost:0},
 {k:'shili-gallery',name:'十里画廊 · 骑行',era:'峰林绿道',dur:120,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'电动车慢慢晃，大榕树、月亮山一路排开。',
  must:['必看','月亮山观景台 · 傍晚逆光最好'],chips:[['up','绿道免费'],['','景点门票自选']],q:'阳朔十里画廊'},
 {k:'westst-night',name:'西街 · 夜',era:'阳朔老街',dur:0,openUntil:1290,openMin:60,prio:2,cost:0,cat:'free',indoor:false,
  vibe:'酒吧声、糖画摊、背包客，热闹但不吵到江边。',must:['必逛','江边段安静 · 主街段热闹 · 各取所需'],chips:[['up','免票']],q:'阳朔西街'}]},
{tab:'D4',name:'阳朔 → 桂林还车',sub:'70 km · 收官 · 轻',start:570,hardEnd:1230,drive:'1.5 h',
 pre:{mode:'drive',conn:'阳朔 → 桂林 · 70 km · 约 1 小时 20 分',min:80,km:70,cost:20,
   via:'沿途 · 高速直达 · 雨天桥面慢行'},
 post:null,
 stops:[
 {k:'elephant',name:'象鼻山 · 江对岸机位',era:'桂林城徽',dur:45,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'不用进园，訾洲对岸就能拍到完整的象鼻。',must:['必看','滨江路对岸免费机位'],chips:[['up','外观免票']],q:'象鼻山'},
 {k:'gl-return',name:'还车 · 桂林',era:'满油交车',dur:40,prio:0,cost:0,cat:'tix',indoor:true,
  vibe:'四天山水，够回味半年。',must:['必做','满油 · 对公里数'],chips:[['','留足 40 分']],q:'桂林 租车还车'}]}];
const GL4_LODGES=[
 {city:'龙脊 · 梯田景观房',price:380,why:'推窗就是梯田 · 日出不用赶路',q:'龙脊梯田客栈'},
 {opts:[{city:'阳朔 · 江景房',price:400,why:'漓江边 · 阳台看峰林',q:'阳朔江景酒店'},
        {city:'阳朔 · 西街巷内',price:280,why:'省 ¥60/人 · 热闹就在楼下',q:'阳朔西街客栈'}]},
 {city:'阳朔 · 连住',price:280,why:'不挪窝 · 行李不动',q:'阳朔西街客栈'},
 null];

/* ═══ 桂林 3 天：砍龙脊，直奔漓江精华 ═══ */
const GL3_D1={tab:'D1',name:'桂林 → 兴坪 → 阳朔',sub:'135 km · 20 元机位 · 轻',start:540,hardEnd:1320,drive:'2.5 h',
 pre:null,post:{mode:'drive',conn:'兴坪 → 阳朔 · 25 km · 40 分',min:40,km:25,cost:0},
 stops:[
 {k:'gl-pickup',name:'桂林提车 · 验车',era:'租车站',dur:40,prio:0,cost:0,cat:'tix',indoor:true,
  vibe:'南方山路多弯，小车灵活。',must:['必做','绕车拍视频 · 山路备晕车药'],chips:[['','小车即可']],q:'桂林 租车'},
 {mode:'drive',conn:'桂林 → 兴坪古镇 · 110 km · 约 2 小时',min:120,km:110,cost:30,
  via:'沿途 · 高速转沿江路 · 兴坪路窄慢行'},
 {k:'xingping',name:'兴坪 · 20 元人民币机位',cng:'最美峰林',era:'漓江精华段',dur:120,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'掏出一张 20 块对着江面比一比，你就站在人民币里。',
  must:['必看','码头边比对机位 · 老寨山可登顶（往返 1.5 h）'],chips:[['up','江边免票'],['','竹筏漓江段¥118 自选']],q:'兴坪古镇'},
 {k:'xingping-food',name:'啤酒鱼 · 兴坪老店',era:'漓江活鱼',dur:75,prio:1,cost:60,cat:'food',indoor:true,
  vibe:'漓江剑骨鱼配啤酒焖，皮脆汁浓。',must:['必点','啤酒鱼 · 田螺酿'],chips:[['','人均¥60']],q:'兴坪 啤酒鱼'}]};
const GL3_DAYS=[GL3_D1,
 Object.assign({},GL4_DAYS[2],{tab:'D2'}),
 Object.assign({},GL4_DAYS[3],{tab:'D3'})];
const GL3_LODGES=[
 {opts:[{city:'阳朔 · 江景房',price:400,why:'漓江边 · 阳台看峰林',q:'阳朔江景酒店'},
        {city:'阳朔 · 西街巷内',price:280,why:'省 ¥60/人 · 热闹就在楼下',q:'阳朔西街客栈'}]},
 {city:'阳朔 · 连住',price:280,why:'不挪窝 · 行李不动',q:'阳朔西街客栈'},
 null];


/* ── 张家界·武陵源 4 天 ──────────────────────────── */
const ZJJ_NODES=[
 {n:'张家界市',x:300,y:240,lx:13,ly:4,a:'start'},
 {n:'天门山',x:322,y:298,lx:13,ly:14,a:'start'},
 {n:'武陵源',x:262,y:120,lx:-2,ly:-10,a:'end'},
 {n:'大峡谷',x:200,y:64,lx:-2,ly:-10,a:'middle'}];
const ZJJ4_DAYS=[
{tab:'D1',name:'张家界市 · 落脚',sub:'提车+老城暖场 · 极轻',start:600,hardEnd:1350,drive:'0.5 h',
 pre:null,post:{mode:'walk',conn:'步行回住处 · 8 分',min:8,cost:0},
 stops:[
 {k:'zjj-pickup',name:'张家界提车 · 验车',era:'租车站',dur:40,prio:0,cost:0,cat:'tix',indoor:true,
  vibe:'市内到两大景区都不远，车是腿。',must:['必做','绕车拍视频 · 确认山路险'],chips:[['','小车即可']],q:'张家界 租车'},
 {mode:'drive',conn:'→ 市区住处 · 8 km · 20 分',min:20,km:8,cost:0},
 {k:'dayong',name:'大庸古城 · 夜',era:'老张家界',dur:0,openUntil:1290,openMin:75,prio:2,cost:0,cat:'free',indoor:false,
  vibe:'第二天要爬山，今晚就在古城慢慢吃、早点睡。',
  must:['必吃','三下锅 · 人均¥50 管饱'],chips:[['up','古城免票']],q:'大庸古城'}]},
{tab:'D2',name:'天门山 · 全天',sub:'索道+玻璃栈道+天门洞 · 重',start:450,hardEnd:1290,drive:'0.5 h',
 pre:{mode:'drive',conn:'→ 天门山索道下站 · 5 km · 15 分',min:15,km:5,cost:0},
 post:{mode:'drive',conn:'索道下山取车回住处 · 20 分',min:20,km:5,cost:0},
 stops:[
 {k:'tianmen',name:'天门山 · 索道上山',cng:'最美峰林',era:'世界最长索道 7,455 m',dur:60,prio:0,cost:278,cat:'tix',indoor:false,dep:{first:420,every:10,last:960},
  vibe:'索道跨过整座城再钻进云里，28 分钟像一场电影。',
  must:['必做','A 线（索道上环保车下）· 7:00 首班避高峰'],chips:[['down','限流 · 提前 1 天官网购'],['','票含索道+环保车']],q:'天门山'},
 {mode:'walk',conn:'山顶西线步行 · 30 分',min:30,cost:0},
 {k:'glass-walk',name:'玻璃栈道 · 西线',era:'崖壁 1,430 m',dur:60,prio:1,cost:5,cat:'tix',indoor:false,
  vibe:'脚下就是垂直崖壁，鞋套一穿，走出去就赢了。',
  must:['必做','恐高就走鬼谷栈道平行段'],chips:[['','鞋套¥5']],q:'天门山玻璃栈道'},
 {mode:'walk',conn:'穿山扶梯到天门洞 · 25 分',min:25,cost:0},
 {k:'tianmen-cave',name:'天门洞 · 999 级天梯',era:'世界最高天然穿山溶洞',dur:90,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'山被凿开一扇门，云从洞里穿过去。',
  must:['必看','洞下仰拍 · 天梯量力（可扶梯替代）'],chips:[['up','已含在门票']],q:'天门洞'}]},
{tab:'D3',name:'武陵源 · 袁家界',sub:'阿凡达悬浮山 · 重',start:450,hardEnd:1290,drive:'1 h',
 pre:{mode:'drive',conn:'市区 → 武陵源标志门 · 32 km · 约 50 分',min:50,km:32,cost:0,
   via:'沿途 · 存行李到武陵源镇住处再进园'},
 post:{mode:'walk',conn:'景区出口步行回镇 · 15 分',min:15,cost:0},
 stops:[
 {k:'wly-in',name:'武陵源 · 购票进山',cng:'最美峰林',era:'世界自然遗产',dur:30,prio:0,cost:228,cat:'tix',indoor:false,dep:{first:420,every:15,last:990},
  vibe:'三千奇峰的家，票管四天，今天走精华。',
  must:['必做','刷身份证进 · 环保车全含'],chips:[['','门票¥228 四日有效'],['down','旺季 7:00 前到']],q:'武陵源'},
 {mode:'shuttle',conn:'环保车+百龙天梯上袁家界 · 40 分',min:40,cost:72},
 {k:'yuanjiajie',name:'袁家界 · 悬浮山',cng:'最美峰林',era:'阿凡达取景地',dur:150,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'乾坤柱就是哈利路亚山的原型，云一来，柱子真的浮起来。',
  must:['必看','迷魂台 · 天下第一桥 · 沿栈道走全'],chips:[['up','门票已含'],['','百龙天梯¥72 单程']],q:'袁家界'},
 {mode:'shuttle',conn:'环保车转天子山 · 30 分',min:30,cost:0},
 {k:'tianzishan',name:'天子山 · 御笔峰',era:'峰林之王视角',dur:90,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'御笔峰像几支插在云里的笔，黄昏侧光最立体。',
  must:['必看','贺龙公园观景台 · 索道下山¥72 自选'],chips:[['up','门票已含']],q:'天子山御笔峰'}]},
{tab:'D4',name:'十里画廊 → 还车',sub:'轻徒步+收官 · 轻',start:510,hardEnd:1230,drive:'1 h',
 pre:{mode:'walk',conn:'步行进十里画廊入口 · 15 分',min:15,cost:0},
 post:{mode:'drive',conn:'武陵源 → 张家界市还车 · 40 km · 约 1 小时',min:60,km:40,cost:0},
 stops:[
 {k:'shili-zjj',name:'十里画廊 · 徒步',cng:'最美峰林',era:'峡谷画卷',dur:120,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'沿着小火车轨道慢慢走，三姐妹峰在头顶排队。',
  must:['必看','徒步去小火车回（¥38）· 采药老人峰'],chips:[['up','门票已含'],['','小火车¥38 自选']],q:'十里画廊 张家界'},
 {k:'zjj-return',name:'还车 · 张家界市',era:'满油交车',dur:40,prio:0,cost:0,cat:'tix',indoor:true,
  vibe:'四天两座山，腿酸得值。',must:['必做','满油 · 对公里数'],chips:[['','留足 40 分']],q:'张家界 租车还车'}]}];
const ZJJ4_LODGES=[
 {city:'张家界市 · 古城边',price:280,why:'三下锅一条街 · 明早索道 15 分',q:'张家界市区酒店'},
 {city:'市区 · 连住',price:280,why:'不挪窝 · 天门山就在城边',q:'张家界市区酒店'},
 {opts:[{city:'武陵源镇 · 景区门口',price:340,why:'走路进园 · 多睡半小时',q:'武陵源镇酒店'},
        {city:'武陵源镇 · 巷内',price:260,why:'省 ¥40/人 · 步行 10 分进园',q:'武陵源'}]},
 null];

/* ═══ 张家界 5 天：在武陵源后加一天大峡谷玻璃桥 ═══ */
const ZJJ_CANYON_DAY={tab:'D4',name:'大峡谷 · 玻璃桥',sub:'30 km · 桥上走 + 谷底下行 · 中',start:480,hardEnd:1260,drive:'1 h',
 pre:{mode:'drive',conn:'武陵源 → 张家界大峡谷 · 30 km · 约 50 分',min:50,km:30,cost:0,
   via:'沿途 · 三官寺方向 · 景区停车场 ¥15'},
 post:{mode:'drive',conn:'大峡谷 → 武陵源镇 · 30 km · 约 50 分',min:50,km:30,cost:0},
 stops:[
 {k:'glass-bridge',name:'张家界大峡谷玻璃桥',cng:'最美峡谷',era:'跨谷 430 m · 高 300 m',dur:90,prio:0,cost:259,cat:'tix',indoor:false,
  vibe:'一脚踏空的错觉持续整座桥，桥中央往下看，溪水细成一条线。',
  must:['必做','分时预约进桥 · 鞋套现场发'],chips:[['','联票¥259'],['down','需提前网上预约时段'],['down','大风或雷雨封桥']],q:'张家界大峡谷玻璃桥'},
 {mode:'walk',conn:'桥头下切谷底栈道 · 20 分',min:20,cost:0},
 {k:'canyon-walk',name:'大峡谷 · 谷底栈道',era:'一线天到神泉湖',dur:150,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'谷底常年不见太阳，水声压过人声，一线天那段抬头只有一条缝。',
  must:['必走','下行为主省力 · 神泉湖可坐船（¥30 自选）'],chips:[['up','含在联票'],['down','雨天湿滑']],q:'张家界大峡谷'},
 {k:'canyon-lift',name:'出谷 · 垂直电梯',era:'省 400 级台阶',dur:30,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'从谷底直提到出口，回头看整条峡谷缩成一道绿痕。',
  must:['必做','含在联票 · 排队高峰 15 分'],chips:[['up','含票']],q:'张家界大峡谷电梯'}]};
const ZJJ5_DAYS=[ZJJ4_DAYS[0], ZJJ4_DAYS[1], ZJJ4_DAYS[2], ZJJ_CANYON_DAY,
  Object.assign({},ZJJ4_DAYS[3],{tab:'D5'})];
const ZJJ5_LODGES=[
 {city:'张家界市 · 古城边',price:280,why:'老城步行圈 · 明早去天门山近',q:'张家界市 古城'},
 {city:'市区 · 连住',price:280,why:'不挪窝 · 行李不动',q:'张家界市 酒店'},
 {opts:[{city:'武陵源镇 · 景区门口',price:360,why:'省下每天 50 分往返',q:'武陵源镇 酒店'},
        {city:'武陵源镇 · 巷内客栈',price:260,why:'省 ¥50/人 · 走 5 分钟到门口',q:'武陵源镇 客栈'}]},
 {city:'武陵源镇 · 连住',price:260,why:'不挪窝 · 明早直接进十里画廊',q:'武陵源镇 客栈'},
 null];


/* ── 注册：桂林 + 张家界 ─────────────────────────── */
Object.assign(ROUTES,{
 gl4:{name:'桂林·阳朔',dest:'广西 · 桂林阳朔',fam:'gl',days:GL4_DAYS,lodges:GL4_LODGES,
  cluster:null,inserts:null,defSels:{},defSelsM:null,
  nights:3,rent:800,roadfood:220,perCar:true,nav:'amap',strength:'轻',
  dayVariants:[3,4],
  carLabel:'租车 · 油费 · 路桥',tixLabel:'门票与竹筏',foodLabel:'餐饮 · 含路餐',
  overTip:'可换西街巷内房',
  budgets:[{l:'宽松',v:2150},{l:'精打细算',v:1900}],
  thrift(){ lodge4=1; },
  tastes:[{id:'photo',apply(){ addP('拍照控 · 20元机位') }},{id:'chill',apply(){ addP('躺平型 · 竹筏漂着') }}],
  defTasteIds:['photo','chill'],
  title:'🚢 桂林·阳朔 4 天 · 山水打底',meta:'广西桂林 · 4天3晚 · 08-16 出发',
  why:'龙脊先上山看梯田，兴坪站进 20 元人民币，阳朔一整天泡在遇龙河和十里画廊。四天不赶，山水都给足。',
  weather:'桂林 8 月 · 昼 27–35°C · 午后雷阵雨 · 防晒防雨都要',
  seasons:[{in:true,name:'漓江丰水期',why:'6-8 月水量足 · 竹筏全线开',tag:'已排入 D3',ver:1},
   {in:false,name:'龙脊灌水季',why:'5-6 月梯田注水如镜 · 本次已过',pick:{key:'gl-water',name:'灌水季再来',ptext:'梯田控'}}],
  inserts:{
   zhufa:{day:1, afterK:'xingping', label:'D2', brief:'兴坪码头 → 九马画山 · 竹筏往返约 120 分 · ¥118/人',
     profile:'坐船控',
     stop:{k:'zhufa',name:'漓江竹筏 · 兴坪—九马画山',era:'漓江精华 20 公里',dur:120,prio:2,cost:118,cat:'tix',indoor:false,
       vibe:'竹筏压着水走，黄布倒影和九马画山从两侧退过去，江面比岸上安静得多。',
       must:['必看','九马画山数马 · 船家会指给你看'],
       chips:[['','竹筏¥118/人'],['down','雨大停航']],
       q:'兴坪竹筏码头',pt:[380,236]},
     conns:[{mode:'',conn:'兴坪码头登筏 · 步行 5 分',min:5,km:0,cost:0},
            {mode:'',conn:'返兴坪码头 → 继续行程',min:5,km:0,cost:0}]}
  },
  extras:[{ins:'zhufa'}],
  extrasSub:'备着的还有 玩 15 · 吃 9 · 住 7',
  todos(){ return [
   {k:'raft',tag:['down','预订'],text:'遇龙河竹筏旺季提前 1 天订 · 早班人少',v:'更新 08-03'},
   {k:'heat',tag:['down','防暑'],text:'8 月桂林 35°C · 竹筏段备防晒和水',v:''},
   {k:'mount',tag:['','驾驶'],text:'龙脊最后 20 km 盘山 · 会车鸣笛慢行',v:''},
   {k:'ebike',tag:['','体验'],text:'阳朔租电动车押金身份证 · 选新车电足的',v:''}]; },
  map:{nodes:GL_NODES,order:[0,1,2,3],loop:true,
   seg:[[0,1],[1,2],null,[3,0]],
   tonight:[1,3,3,-1]}},

 zjj4:{name:'张家界·武陵源',dest:'湖南 · 张家界',fam:'zjj',days:ZJJ4_DAYS,lodges:ZJJ4_LODGES,
  cluster:null,inserts:null,defSels:{},defSelsM:null,
  nights:3,rent:800,roadfood:220,perCar:true,nav:'amap',strength:'中',
  dayVariants:[4],
  carLabel:'租车 · 油费',tixLabel:'门票与索道天梯',foodLabel:'餐饮 · 含路餐',
  overTip:'可换武陵源巷内房',
  budgets:[{l:'宽松',v:2300},{l:'精打细算',v:2050}],
  thrift(){ lodge4=1; },
  tastes:[{id:'hike',apply(){ addP('走走走 · 栈道走全') }},{id:'photo',apply(){ addP('拍照控 · 悬浮山等云') }}],
  defTasteIds:['hike','photo'],
  title:'🏞 张家界 4 天 · 两座山各给一天',meta:'湖南张家界 · 4天3晚 · 08-15 出发',
  why:'天门山和武陵源是两回事，各给一整天才不亏：D2 索道玻璃栈道天门洞，D3 袁家界悬浮山加天子山，D4 十里画廊轻徒步收官。门票四日有效，节奏刚好。',
  weather:'张家界 8 月 · 昼 26–34°C · 山顶凉 5°C · 午后雷阵雨',
  seasons:[{in:true,name:'雨后云海',why:'雨停次日出云海概率最高',tag:'D3 看预报机动',ver:0},
   {in:false,name:'冬季雾凇',why:'12-2 月天子山雾凇 · 本季未到',pick:{key:'zjj-winter',name:'雾凇季再来',ptext:'雪景控'}}],
  extras:[{later:{key:'grand-canyon',name:'大峡谷玻璃桥',why:'需加半天 · 另购票',ptext:'胆大控'}}],
  extrasSub:'备着的还有 玩 13 · 吃 7 · 住 6',
  todos(){ return [
   {k:'tianmen',tag:['down','预约'],text:'天门山限流 · 提前 1 天官网分时段购票',v:'更新 08-03',url:'https://www.zjjtms.com'},
   {k:'wly',tag:['','门票'],text:'武陵源 ¥228 四日有效 · 刷身份证进',v:''},
   {k:'shoes',tag:['','装备'],text:'两天爬山 · 抓地好的鞋 · 山顶带件外套',v:''},
   {k:'peak',tag:['down','避峰'],text:'两大景区都 7:00 前到 · 晚一小时排队翻倍',v:''}]; },
  map:{nodes:ZJJ_NODES,order:[0,1,2],loop:true,
   seg:[null,[0,1,0],[0,2],[2,0]],
   tonight:[0,0,2,-1]}},
});


/* ── 都江堰·青城山 1 日（成都出发 · 动车 · 单日打样）── */
const DJY_NODES=[
 {n:'成都',x:430,y:250,lx:13,ly:4,a:'start'},
 {n:'都江堰',x:230,y:140,lx:-2,ly:-10,a:'middle'},
 {n:'青城山',x:180,y:230,lx:-2,ly:16,a:'end'}];
const DJY1_DAYS=[
{tab:'D1',name:'都江堰 → 青城山 · 一日',sub:'动车往返 · 拜水问道 · 中',start:440,hardEnd:1220,drive:'— h',
 pre:{mode:'train',conn:'成都西 → 离堆公园站 · 动车 40 分',min:55,cost:17,
   dep:{first:420,every:40,last:1140},via:'犀浦/成都西均可上车 · 刷身份证进站'},
 post:{mode:'train',conn:'青城山站 → 成都西 · 动车 50 分',min:60,cost:17,
   dep:{first:600,every:40,last:1250}},
 stops:[
 {k:'dujiangyan',name:'都江堰 · 鱼嘴分水',cng:'最美古镇',era:'公元前 256 年',dur:180,prio:0,cost:80,cat:'tix',indoor:false,
  vibe:'两千多年前的水利工程今天还在上班，鱼嘴把岷江一分为二。',
  must:['必看','鱼嘴 → 飞沙堰 → 宝瓶口顺序走 · 安澜索桥来回'],
  chips:[['','门票¥80'],['down','景区摆渡¥10 自选']],q:'都江堰景区'},
 {mode:'walk',conn:'离堆公园 → 南桥午饭 · 步行 15 分',min:15,cost:0},
 {k:'nanqiao-lunch',name:'南桥 · 尤兔头或冷锅鱼',era:'廊桥边',dur:70,prio:1,cost:55,cat:'food',indoor:true,
  vibe:'桥下就是奔腾的岷江水，夏天坐桥边风都是凉的。',must:['必点','冷锅鱼 · 或麻辣兔头配冰粉'],chips:[['','人均¥55']],q:'都江堰南桥 美食'},
 {mode:'train',conn:'离堆公园 → 青城山站 · 动车 10 分 + 摆渡 20 分',min:45,cost:8,
  dep:{first:540,every:40,last:1080}},
 {k:'qingcheng',name:'青城山前山 · 问道',cng:'最美名山',era:'道教发源地',dur:210,prio:0,cost:80,cat:'tix',indoor:false,
  opts:[{name:'青城山前山 · 索道上步行下',cost:115,dur:180,vibe:'索道直上上清宫一线，省两小时脚程，把力气留给殿宇。'},
        {name:'青城山前山 · 全程步行',cost:80,dur:240,vibe:'从山门一步步走上去，青城天下幽是走出来的。'}],
  id:'qc-up',
  must:['必看','上清宫 · 老君阁登顶 · 天然图画牌坊'],
  chips:[['','前山门票¥80'],['down','索道单程¥35 自选']],q:'青城山前山'}]}];
const DJY1_LODGES=[null];

/* ═══ 都江堰·青城山 2 日：前山问道 + 后山徒步，住青城山镇 ═══ */
const DJY2_D1=Object.assign({},DJY1_DAYS[0],{
 tab:'D1',name:'都江堰 → 青城前山',sub:'动车进 · 拜水问道 · 中',
 post:{mode:'transit',conn:'青城山站 → 青城山镇住处 · 摆渡 15 分',min:15,cost:5}});
const DJY2_D2={tab:'D2',name:'青城后山 · 徒步一日',sub:'五龙沟栈道 · 中偏重',start:450,hardEnd:1140,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 后山山门 · 摆渡 20 分',min:20,cost:5},
 post:{mode:'transit',conn:'青城山站 → 成都西 · 动车 50 分',min:60,cost:17},
 stops:[
 {k:'taian',name:'泰安古镇 · 早茶',era:'后山门口老场镇',dur:60,prio:1,cost:25,cat:'food',indoor:false,
  vibe:'溪水穿镇过，铺子刚开门，豆花和油茶端上来还烫嘴。',
  must:['必吃','豆花 + 老鸭汤 · 带一份猪肉脯上山'],chips:[['up','古镇免票'],['','人均¥25']],q:'泰安古镇'},
 {k:'houshan-in',name:'青城后山 · 购票进山',era:'比前山野，比前山凉',dur:20,prio:0,cost:20,cat:'tix',indoor:false,
  vibe:'后山不讲道观讲水，一进门就是溪声。',
  must:['必做','现场扫码购票 · 山门取地图'],chips:[['','门票¥20']],q:'青城后山山门'},
 {k:'wulonggou',name:'五龙沟 · 溪边栈道',cng:'最美峡谷',era:'飞泉坊到幽一水',dur:150,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'栈道贴着水走，飞泉从头顶落下来，夏天比城里凉十度。',
  must:['必走','飞泉坊拍水帘 · 幽一水段最阴凉'],chips:[['up','含在门票'],['down','石阶湿滑穿防滑鞋']],q:'青城后山五龙沟'},
 {k:'youyicun',name:'又一村 · 半山农家午饭',era:'海拔 1000 m 的村子',dur:70,prio:1,cost:45,cat:'food',indoor:true,
  vibe:'走两小时到这儿，腊肉炒笋和一碗甜皮鸭最解乏。',
  must:['必点','腊肉炒春笋 · 山泉豆花'],chips:[['','人均¥45']],q:'青城后山又一村'},
 {k:'baiyun-down',name:'下山 · 白云索道或步行',era:'省两小时腿力',dur:60,prio:0,cost:45,cat:'tix',indoor:false,
  opts:[{name:'白云索道下山',cost:45,dur:60,vibe:'索道从又一村直落山门，膝盖谢谢你。'},
        {name:'原路步行下山',cost:0,dur:135,vibe:'再走一遍溪边栈道，下午的光斜着穿过水汽。'}],
  id:'hs-down',
  must:['必做','索道末班 17:00 · 步行需留足 2.5 小时'],
  chips:[['','索道¥45 自选'],['down','末班前 40 分到站']],q:'青城后山白云索道'}]};
const DJY2_DAYS=[DJY2_D1, DJY2_D2];
const DJY2_LODGES=[
 {opts:[{city:'青城山镇 · 溪边民宿',price:320,why:'推窗听水 · 明早直接进后山',q:'青城山镇 民宿'},
        {city:'青城山镇 · 快捷房',price:220,why:'省 ¥50/人 · 干净够睡',q:'青城山镇 酒店'}]},
 null];


/* ── 日本·关西 5 天（大阪进出 · 全公共交通 · 国外打样）── */
const KAN_NODES=[
 {n:'关西机场',x:220,y:300,lx:-2,ly:16,a:'start'},
 {n:'大阪',x:300,y:214,lx:13,ly:4,a:'start'},
 {n:'京都',x:330,y:100,lx:13,ly:-8,a:'middle'},
 {n:'奈良',x:396,y:196,lx:13,ly:14,a:'end'}];
const KAN5_DAYS=[
{tab:'D1',name:'关西机场 → 大阪',sub:'南海电车 · 道顿堀夜 · 轻',start:840,hardEnd:1380,drive:'— h',
 pre:{mode:'train',conn:'关西机场 → 难波 · 南海电车急行 45 分',min:60,cost:48,
   dep:{first:360,every:15,last:1380},via:'落地先领 eSIM 信号 · 南海线跟着蓝色指示走'},
 post:{mode:'walk',conn:'步行回难波住处 · 8 分',min:8,cost:0},
 stops:[
 {k:'kan-arrive',name:'难波 · 放行李',era:'大阪的胃',dur:40,prio:0,cost:0,cat:'free',indoor:true,
  vibe:'住难波，四天不挪窝，去哪都是电车直达。',must:['必做','ICOCA 卡充值 ¥2,000 起步（手机可开）'],chips:[['','ICOCA 通刷']],q:'Namba Osaka'},
 {mode:'walk',conn:'步行到道顿堀 · 6 分',min:6,cost:0},
 {k:'dotonbori',name:'道顿堀 · 格力高打卡',era:'大阪夜',dur:120,prio:0,cost:70,cat:'food',indoor:false,
  vibe:'霓虹倒在运河里，章鱼烧在铁板上翻面，大阪的夜从这里开始。',
  must:['必吃','章鱼烧 · 一兰拉面深夜场排队短'],chips:[['','人均¥70']],q:'Dotonbori'}]},
{tab:'D2',name:'大阪 · 城与市场',sub:'大阪城+黑门+梅田 · 轻',start:540,hardEnd:1350,drive:'— h',
 pre:{mode:'metro',conn:'地铁御堂筋线 → 谷町四丁目 · 20 分',min:25,cost:15,
   dep:{first:330,every:5,last:1430}},
 post:{mode:'metro',conn:'梅田 → 难波 · 地铁 15 分',min:20,cost:15},
 stops:[
 {k:'osaka-castle',name:'大阪城 · 天守阁',era:'丰臣秀吉 1583',dur:150,prio:0,cost:30,cat:'tix',indoor:false,
  vibe:'金鯱在天守顶上晒太阳，护城河一圈走下来就懂了什么叫城。',
  must:['必看','天守阁 8 层展望台 · 西之丸庭园看全景'],chips:[['','天守阁¥30'],['up','公园免费']],q:'Osaka Castle'},
 {mode:'metro',conn:'地铁 → 日本桥 · 15 分',min:20,cost:15},
 {k:'kuromon',name:'黑门市场 · 边走边吃',era:'大阪的厨房',dur:90,prio:1,cost:90,cat:'food',indoor:true,
  vibe:'现开的海胆、现烤的和牛串，这条街是用嘴逛的。',
  must:['必吃','金枪鱼中落 · 玉子烧 · 现切和牛串'],chips:[['','人均¥90'],['down','15:00 后陆续收摊']],q:'Kuromon Market'},
 {mode:'metro',conn:'地铁 → 梅田 · 20 分',min:25,cost:15},
 {k:'umeda-sky',name:'梅田蓝天大厦 · 空中庭园',era:'露天 360°',dur:90,prio:1,cost:75,cat:'tix',indoor:false,
  vibe:'日落时分上去，大阪的灯一盏盏亮起来，淀川像条光带。',
  must:['必看','日落前 40 分钟到 · 露天回廊走一整圈'],chips:[['','门票¥75']],q:'Umeda Sky Building'}]},
{tab:'D3',name:'京都 · 一日',sub:'伏见稻荷+清水寺+祇园 · 中',start:480,hardEnd:1350,drive:'— h',
 pre:{mode:'train',conn:'难波 → 京都 · 近铁/阪急换乘 · 约 1 小时',min:70,cost:40,
   dep:{first:330,every:10,last:1380}},
 post:{mode:'train',conn:'京都 → 难波 · 约 1 小时 10 分',min:75,cost:40,
   dep:{first:360,every:10,last:1370}},
 stops:[
 {k:'fushimi',name:'伏见稻荷 · 千本鸟居',era:'稻荷神总本宫',dur:150,prio:0,cost:0,cat:'free',indoor:false,earliest:480,
  vibe:'橙红色的鸟居一座接一座爬满山，越早来越安静。',
  must:['必看','走到四辻展望点即可折返 · 全山 2 小时'],chips:[['up','免票'],['down','8:00 前人最少']],q:'Fushimi Inari'},
 {mode:'train',conn:'京阪电车 → 清水五条 · 20 分',min:30,cost:15},
 {k:'kiyomizu',name:'清水寺 · 舞台',era:'公元 778 年',dur:120,prio:0,cost:20,cat:'tix',indoor:false,
  vibe:'悬空的木舞台伸向山谷，京都在脚下铺开。',
  must:['必看','清水舞台 · 音羽瀑布三选一 · 二三年坂顺路'],chips:[['','门票¥20']],q:'Kiyomizu-dera'},
 {mode:'walk',conn:'二年坂 → 祇园 · 步行 25 分',min:25,cost:0},
 {k:'gion',name:'祇园 · 花见小路',era:'艺伎之街',dur:90,prio:1,cost:80,cat:'food',indoor:false,
  vibe:'木格子门里透出暖光，运气好能遇见赶场的艺伎。',
  must:['必做','白川巽桥拍一张 · 晚饭在先斗町解决'],chips:[['','人均¥80'],['down','别追拍艺伎']],q:'Gion Kyoto'}]},
{tab:'D4',name:'奈良 · 半日 + 大阪',sub:'喂鹿+春日大社 · 轻',start:510,hardEnd:1350,drive:'— h',
 pre:{mode:'train',conn:'难波 → 近铁奈良 · 快速急行 40 分',min:50,cost:25,
   dep:{first:330,every:10,last:1380}},
 post:{mode:'train',conn:'近铁奈良 → 难波 · 40 分',min:50,cost:25,
   dep:{first:360,every:10,last:1390}},
 stops:[
 {k:'nara-deer',name:'奈良公园 · 鹿饼外交',era:'1,200 头野生鹿',dur:120,prio:0,cost:15,cat:'tix',indoor:false,
  vibe:'鹿会鞠躬讨吃的，饼一举高它们就排队。',
  must:['必做','鹿饼¥15/份 · 举高喂 · 藏好纸质物'],chips:[['','鹿饼¥15'],['down','空手摊开表示没了']],q:'Nara Park'},
 {mode:'walk',conn:'穿过公园到春日大社 · 20 分',min:20,cost:0},
 {k:'kasuga',name:'春日大社 · 石灯笼参道',era:'公元 768 年',dur:90,prio:1,cost:25,cat:'tix',indoor:false,
  vibe:'三千座石灯笼排到深林里，苔藓把时间都长满了。',
  must:['必看','本殿回廊 · 万灯笼再现室'],chips:[['','特别参拜¥25']],q:'Kasuga Taisha'},
 {mode:'walk',conn:'东向商店街 · 步行 15 分',min:15,cost:0},
 {k:'nara-mochi',name:'中谷堂 · 高速捣麻糬',era:'奈良名物',dur:40,prio:2,cost:15,cat:'food',indoor:false,
  vibe:'捣麻糬快到看不清手，刚出炉的艾草麻糬还烫着。',must:['必吃','现捣艾草麻糬 ¥15'],chips:[['','排队 10 分']],q:'Nakatanidou'}]},
{tab:'D5',name:'心斋桥 → 机场',sub:'扫货+返程 · 轻',start:570,hardEnd:1200,drive:'— h',
 pre:{mode:'walk',conn:'难波 → 心斋桥筋 · 步行 10 分',min:10,cost:0},
 post:{mode:'train',conn:'难波 → 关西机场 · 南海电车 45 分',min:60,cost:48,
   dep:{first:330,every:15,last:1320},via:'国际航班提前 3 小时到 · 退税柜台留 40 分'},
 stops:[
 {k:'shinsaibashi',name:'心斋桥筋 · 补货',era:'一条街扫完',dur:150,prio:0,cost:0,cat:'free',indoor:true,
  vibe:'药妆、球鞋、大丸百货一条直线，预算在这里蒸发。',
  must:['必做','药妆比价再下手 · 护照退税满 ¥250'],chips:[['up','逛街免票']],q:'Shinsaibashi'},
 {k:'kan-out',name:'关西机场 · 返程',era:'再见大阪',dur:60,prio:0,cost:0,cat:'free',indoor:true,
  vibe:'ICOCA 里剩的钱，留着下次来花。',must:['必做','eSIM 关漫游 · 保安检查液体'],chips:[['','提前 3 小时']],q:'Kansai Airport'}]}];
const KAN5_LODGES=[
 {opts:[{city:'难波 · 商务酒店',price:520,why:'电车枢纽楼上 · 四天不挪窝',q:'Namba hotel'},
        {city:'难波 · 胶囊旅馆',price:360,why:'省 ¥80/人 · 洗浴公用',q:'Namba capsule hotel'}]},
 {city:'难波 · 连住',price:520,why:'不挪窝 · 行李不动',q:'Namba hotel'},
 {city:'难波 · 连住',price:520,why:'京都当日往返 · 还住这',q:'Namba hotel'},
 {city:'难波 · 连住',price:520,why:'最后一晚 · 明早去机场顺',q:'Namba hotel'},
 null];

/* ── 注册：单日 + 国外（Schema v2 三件套写法）────── */
Object.assign(ROUTES,{
 djy1:{name:'都江堰·青城山',dest:'四川 · 成都周边',fam:'djy',days:DJY1_DAYS,lodges:DJY1_LODGES,
  cluster:null,inserts:null,defSels:{'qc-up':0},defSelsM:null,
  transport:{mode:'transit',rent:0,perCar:false,roadfood:0,label:'动车 · 摆渡（每人实付）'},
  locale:{region:'domestic',country:'中国',navApp:'amap',currencyNote:null},
  stay:{nights:0},
  strength:'中',dayVariants:[1],
  tixLabel:'门票与索道',foodLabel:'餐饮',
  hero1v:'1<small>日</small>',hero1k:'成都出发即走',
  overTip:'可换全程步行上山',
  budgets:[{l:'宽松',v:450},{l:'精打细算',v:400}],
  thrift(){ sels['qc-up']=1; },
  tastes:[{id:'hike',apply(){ addP('走走走 · 全程步行上山') }},{id:'folk',apply(){ addP('民俗控 · 问道青城') }}],
  defTasteIds:['hike'],
  title:'⛲ 都江堰·青城山 1 日 · 拜水问道',meta:'成都周边 · 一日往返 · 动车说走就走',
  why:'成都人的周末标配：早班动车 40 分钟到都江堰看两千年水利工程，午饭南桥边，下午青城山问道，晚饭前回城。不用请假的旅行。',
  weather:'成都平原 8 月 · 昼 26–34°C · 山中凉 4°C · 午后阵雨',
  seasons:[{in:true,name:'夏日避暑',why:'青城山比市区低 5°C · 雨后最幽',tag:'带把伞',ver:0},
   {in:false,name:'放水节',why:'清明节都江堰放水大典 · 本季未到',pick:{key:'djy-water',name:'放水节再来',ptext:'民俗控'}}],
  extras:[{later:{key:'houshan',name:'青城后山',why:'徒步一整天 · 需另安排',ptext:'徒步控'}}],
  extrasSub:'备着的还有 玩 8 · 吃 6',
  todos(){ return [
   {k:'train',tag:['down','车票'],text:'动车票 12306 提前 1 天买 · 节假日提前 3 天',v:'更新 08-03'},
   {k:'shoe',tag:['','装备'],text:'青城山石阶多 · 防滑鞋 · 带把伞',v:''},
   {k:'time',tag:['','节奏'],text:'18:30 前到青城山站 · 末班动车别赌',v:''}]; },
  map:{nodes:DJY_NODES,order:[0,1,2],loop:true,
   seg:[[0,1]],
   tonight:[-1]}},

 kansai5:{name:'日本·关西',dest:'日本 · 大阪京都奈良',fam:'kan',days:KAN5_DAYS,lodges:KAN5_LODGES,
  cluster:null,inserts:null,defSels:{},defSelsM:null,
  transport:{mode:'transit',rent:0,perCar:false,roadfood:0,label:'电车 · 地铁 · ICOCA（每人实付）'},
  locale:{region:'intl',country:'日本',navApp:'gmaps',currencyNote:'金额按人民币估 · 当地用 ICOCA+日元现金'},
  stay:{nights:4},
  strength:'轻',dayVariants:[5],
  tixLabel:'门票与体验',foodLabel:'餐饮',
  hero1v:'4<small>晚</small>',hero1k:'难波连住不挪窝',
  overTip:'可换胶囊旅馆',
  budgets:[{l:'宽松',v:3550},{l:'精打细算',v:3150}],
  thrift(){ lodge4=1; },
  tastes:[{id:'food',apply(){ addP('美食控 · 黑门市场用嘴逛') }},{id:'art',apply(){ addP('看展控 · 寺社巡礼') }}],
  defTasteIds:['food','photo'],
  title:'🇯🇵 日本·关西 5 天 · 大阪京都奈良',meta:'日本关西 · 5天4晚 · 不含机票 · 首次出境友好',
  i18n:{en:{name:'Kansai, Japan',dest:'Japan · Osaka Kyoto Nara',
   title:'🇯🇵 Kansai, Japan · 5 days · Osaka Kyoto Nara',
   meta:'Kansai · 5d 4n · flights excluded · first-trip friendly',
   hero1k:'4 nights in Namba, zero repacking',
   why:'Kansai is the easiest way into Japan: four nights in Namba, day-return trains to Kyoto and Nara. One ICOCA card taps through three cities. Prices shown are estimates in your currency; flights not included.'}},
  why:'关西是日本入门最优解：住大阪难波四晚不挪窝，京都奈良当天往返。电车把三座城串成一条线，ICOCA 一张卡刷到底。金额按人民币估算，不含往返机票。',
  weather:'关西 8 月 · 昼 28–36°C 湿热 · 午后雷阵雨 · 室内冷气足',
  seasons:[{in:true,name:'盛夏出行',why:'高温高湿 · 排队景点趁早',tag:'防暑入列',ver:0},
   {in:false,name:'红叶季',why:'11 月中下旬京都封神 · 本季未到',pick:{key:'kan-momiji',name:'红叶季再来',ptext:'红叶控'}}],
  extras:[{later:{key:'usj',name:'环球影城 USJ',why:'需整一天 · 门票另 ¥420',ptext:'乐园控'}},
   {later:{key:'kobe',name:'神户半日',why:'阪神电车 30 分 · 牛排+夜景',ptext:'美食控'}}],
  extrasSub:'备着的还有 玩 22 · 吃 15 · 住 6',
  todos(){ return [
   {k:'visa',tag:['down','签证'],text:'日本旅游签提前 2-3 周办 · 护照有效期 6 个月以上',v:'更新 08-03'},
   {k:'sim',tag:['down','网络'],text:'eSIM 出发前装好 · 或机场租随身 WiFi',v:''},
   {k:'icoca',tag:['','交通'],text:'ICOCA 卡手机可开（Apple Pay）· 充 ¥2,000 起',v:''},
   {k:'cash',tag:['','现金'],text:'备 2 万日元现金 · 小店和神社不刷卡',v:''},
   {k:'flight',tag:['','机票'],text:'往返机票另计 · 提前 1 个月订约 ¥2,500',v:''},
   {k:'tax',tag:['','退税'],text:'单店满 ¥250 可退税 · 护照随身带',v:''}]; },
  map:{nodes:KAN_NODES,order:[0,1,2,3],loop:true,
   seg:[[0,1],null,[1,2],[1,3],[1,0]],
   tonight:[1,1,1,1,-1]}},
});

/* ── 预置设计稿行程（榜单未收录目的地）───────── */








/* ═══════════ 厦门 3 天 · 鼓浪屿与环岛路（轮渡 + 公交 + 单车）═══════════ */
const XM_NODES=[
 {n:'中山路·轮渡',x:300,y:230,lx:13,ly:4,a:'start'},
 {n:'鼓浪屿',x:180,y:210,lx:-2,ly:-10,a:'middle'},
 {n:'环岛路·曾厝垵',x:400,y:320,lx:13,ly:12,a:'end'}];
const XM3_DAYS=[
{tab:'D1',name:'鼓浪屿一整天',sub:'轮渡进岛 · 全程步行 · 中',start:510,hardEnd:1260,drive:'0 h',
 pre:{mode:'transit',conn:'东渡邮轮码头 → 鼓浪屿 · 轮渡 20 分',min:20,cost:35,
   via:'游客须从东渡码头进岛 · 提前网上买票'},
 post:{mode:'transit',conn:'鼓浪屿 → 中山路住处 · 轮渡 + 步行 35 分',min:35,cost:35},
 stops:[
 {k:'xm-sunlight',name:'日光岩',cng:'最美海岸',era:'岛上制高点 92 m',dur:90,prio:0,cost:50,cat:'tix',indoor:false,
  vibe:'爬到顶能看见整座岛的红屋顶铺在海里，对岸就是厦门岛的高楼。',
  must:['必看','早上进岛先冲日光岩 · 十点后排队'],
  chips:[['','门票¥50'],['down','旺季需预约']],q:'鼓浪屿日光岩'},
 {mode:'walk',conn:'日光岩 → 菽庄花园 · 步行 15 分',min:15,cost:0},
 {k:'xm-shuzhuang',name:'菽庄花园 · 钢琴博物馆',era:'1913 年私家园林',dur:80,prio:1,cost:30,cat:'tix',indoor:false,
  vibe:'把海圈进园子里的四十四桥，涨潮时浪能拍到栏杆上。',
  must:['必看','四十四桥 · 钢琴博物馆含在票内'],
  chips:[['','门票¥30']],q:'厦门菽庄花园'},
 {k:'xm-laojie',name:'龙头路 · 老别墅巷',era:'万国建筑博览',dur:100,prio:0,cost:60,cat:'food',indoor:false,
  vibe:'钻进主街后面的小巷，殖民时期的老别墅一栋接一栋，人一下就少了。',
  must:['必逛','往泉州路笔山路走 · 沙茶面和土笋冻'],
  chips:[['up','街区免票'],['','人均¥60']],q:'鼓浪屿龙头路'}]},
{tab:'D2',name:'环岛路 · 曾厝垵 · 沙坡尾',sub:'骑行看海 · 轻',start:540,hardEnd:1290,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 环岛路起点 · 公交 29 路 30 分',min:30,cost:2},
 post:{mode:'transit',conn:'沙坡尾 → 住处 · 公交 25 分',min:25,cost:2},
 stops:[
 {k:'xm-huandao',name:'环岛路 · 骑行看海',cng:'最美海岸',era:'全长 31 km 滨海道',dur:150,prio:0,cost:30,cat:'tix',indoor:false,
  vibe:'一边是海一边是木棉，骑到椰风寨那段能看见对岸的金门。',
  must:['必骑','租单车 ¥30/天 · 骑到椰风寨折返'],
  chips:[['','单车¥30'],['up','路本身免费'],['down','正午晒']],q:'厦门环岛路'},
 {k:'xm-zengcuoan',name:'曾厝垵 · 渔村小巷',era:'渔村改造',dur:80,prio:1,cost:50,cat:'food',indoor:false,
  vibe:'巷子窄得只容两人过，海蛎煎和芒果沙冰的招牌一路挂到底。',
  must:['必吃','海蛎煎 · 芒果沙冰 · 往里巷走'],
  chips:[['up','免票'],['','人均¥50']],q:'厦门曾厝垵'},
 {k:'xm-shapowei',name:'沙坡尾 · 避风坞',era:'老厦门渔港',dur:70,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'退潮时渔船斜靠在坞里，旁边就是艺术西区的旧仓库。',
  must:['必看','避风坞看船 · 艺术西区逛店'],
  chips:[['up','免票']],q:'厦门沙坡尾'}]},
{tab:'D3',name:'南普陀 · 厦大收官',sub:'寺庙与校园 · 下午离开 · 轻',start:540,hardEnd:1170,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 南普陀 · 公交 1 路 25 分',min:25,cost:2},
 post:{mode:'transit',conn:'厦大 → 高崎机场/厦门北站 · 地铁 1 号线 约 45 分',min:45,cost:6},
 stops:[
 {k:'xm-nanputuo',name:'南普陀寺',cng:'最美古镇',era:'唐末始建',dur:100,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'背靠五老峰，殿前放生池的莲花开得满满当当，香火从早烧到晚。',
  must:['必看','大悲殿 · 后山五老峰可登顶'],
  chips:[['up','免票需预约'],['','素斋人均¥30']],q:'厦门南普陀寺'},
 {mode:'walk',conn:'南普陀 → 厦门大学 · 步行 8 分',min:8,cost:0},
 {k:'xm-university',name:'厦门大学 · 芙蓉隧道',era:'1921 年陈嘉庚创办',dur:80,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'嘉庚风格的红砖楼配棕榈树，芙蓉隧道两壁全是学生涂鸦。',
  must:['必看','需提前预约入校 · 芙蓉湖与隧道'],
  chips:[['up','免票'],['down','须提前 3 天官微预约']],q:'厦门大学'},
 {k:'xm-lunch',name:'走之前 · 沙茶面',era:'厦门早饭标配',dur:60,prio:0,cost:35,cat:'food',indoor:true,
  vibe:'花生酱和沙茶熬成的汤底浇在碱面上，加一份猪心和油条。',
  must:['必点','沙茶面加料 · 配一碗四果汤'],
  chips:[['','人均¥35']],q:'厦门 沙茶面'}]}];
const XM3_LODGES=[
 {opts:[{city:'中山路 · 轮渡旁',price:420,why:'走到轮渡码头 5 分 · 老城步行圈',q:'厦门中山路酒店'},
        {city:'曾厝垵 · 民宿',price:300,why:'省 ¥60/人 · 环岛路就在门口',q:'厦门曾厝垵民宿'}]},
 {city:'中山路 · 连住',price:420,why:'不挪窝 · 行李不动',q:'厦门中山路酒店'},
 null];

/* ═══════════ 三亚 4 天 · 海岛慢走（打车 + 景区专线）═══════════ */
const SY_NODES=[
 {n:'三亚湾·市区',x:280,y:250,lx:13,ly:4,a:'start'},
 {n:'蜈支洲岛',x:440,y:180,lx:13,ly:-8,a:'middle'},
 {n:'亚龙湾',x:400,y:300,lx:13,ly:12,a:'middle'},
 {n:'南山·天涯',x:160,y:290,lx:-6,ly:12,a:'end'}];
const SY4_DAYS=[
{tab:'D1',name:'抵达 · 大东海落日',sub:'不赶路 · 先下海 · 极轻',start:720,hardEnd:1260,drive:'0 h',
 pre:{mode:'transit',conn:'凤凰机场 → 市区住处 · 机场快线 40 分',min:40,cost:30},
 post:{mode:'walk',conn:'步行回住处 · 10 分',min:10,cost:0},
 stops:[
 {k:'sy-arrive',name:'放行李 · 换泳衣',era:'到了先别赶',dur:40,prio:0,cost:0,cat:'free',indoor:true,
  vibe:'海就在门口，行李一扔先去泡半小时。',
  must:['必做','防晒霜先涂 · 三亚紫外线全年最强'],
  chips:[['up','无门票']],q:'三亚市区'},
 {k:'sy-dadonghai',name:'大东海 · 落日',cng:'最美海岸',era:'市区最近的海湾',dur:120,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'沙子偏粗但胜在方便，太阳落进海里那十分钟整片沙滩都安静下来。',
  must:['必看','日落前 40 分到 · 沙滩免费'],
  chips:[['up','免票'],['down','水母季 6-9 月注意']],q:'三亚大东海'},
 {k:'sy-seafood',name:'第一市场 · 海鲜加工',era:'自己挑现场做',dur:100,prio:0,cost:150,cat:'food',indoor:true,
  vibe:'市场里挑好虾蟹，隔壁排档按斤收加工费，比酒店便宜一半。',
  must:['必点','和乐蟹 · 芒果螺 · 加工费问清楚'],
  chips:[['','人均¥150'],['down','认准明码标价摊位']],q:'三亚第一市场'}]},
{tab:'D2',name:'蜈支洲岛',sub:'跨海船 · 浮潜看珊瑚 · 中',start:450,hardEnd:1230,drive:'0 h',
 pre:{mode:'transit',conn:'市区 → 蜈支洲码头 · 打车 50 分',min:50,cost:60,
   via:'早班船 8:00 起 · 提前网上订票'},
 post:{mode:'transit',conn:'码头 → 亚龙湾住处 · 打车 40 分',min:40,cost:50},
 stops:[
 {k:'sy-wuzhizhou',name:'蜈支洲岛',cng:'最美海岸',era:'三亚能见度最好的海',dur:300,prio:0,cost:214,cat:'tix',indoor:false,
  vibe:'水下十几米还能看清珊瑚，环岛观光车绕一圈能停五六个观景台。',
  must:['必做','早班船进岛 · 情人桥 · 观日岩'],
  chips:[['','门票+船¥214'],['','浮潜¥380 自选'],['down','旺季提前 3 天订票']],q:'蜈支洲岛'}]},
{tab:'D3',name:'亚龙湾 · 天涯海角',sub:'白沙滩泡半天 · 轻',start:540,hardEnd:1260,drive:'0 h',
 pre:{mode:'walk',conn:'住处 → 亚龙湾沙滩 · 步行 8 分',min:8,cost:0},
 post:{mode:'transit',conn:'天涯海角 → 亚龙湾住处 · 打车 55 分',min:55,cost:70},
 stops:[
 {k:'sy-yalong',name:'亚龙湾 · 白沙滩',cng:'最美海岸',era:'三亚沙质最细的湾',dur:180,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'沙子白得晃眼，走上去像踩在面粉里，海水一层层从透明到深蓝。',
  must:['必做','上午光线最好 · 沙滩公共段免费'],
  chips:[['up','公共沙滩免票'],['down','正午晒 · 备遮阳伞']],q:'三亚亚龙湾'},
 {mode:'transit',conn:'亚龙湾 → 天涯海角 · 打车 50 分',min:50,cost:70},
 {k:'sy-tianya',name:'天涯海角',era:'清雍正年间摩崖石刻',dur:100,prio:1,cost:81,cat:'tix',indoor:false,
  vibe:'两块大石头立在海边刻着字，说实话是拍照打卡多过看景。',
  must:['必拍','天涯石 · 海角石 · 傍晚人少'],
  chips:[['','门票¥81'],['down','景区大 · 需坐观光车']],q:'三亚天涯海角'}]},
{tab:'D4',name:'南山寺 · 返程',sub:'海上观音 · 中午离开 · 轻',start:510,hardEnd:1140,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 南山寺 · 打车 60 分',min:60,cost:80},
 post:{mode:'transit',conn:'南山 → 凤凰机场 · 打车 50 分',min:50,cost:70},
 stops:[
 {k:'sy-nanshan',name:'南山寺 · 海上观音',cng:'最美海岸',era:'108 米三面观音立于海中',dur:180,prio:0,cost:129,cat:'tix',indoor:false,
  vibe:'观音像从海里立起来一百多米高，走到底座下面才知道有多大。',
  must:['必看','海上观音 · 三十三观音堂 · 园区有电瓶车'],
  chips:[['','门票¥129'],['','电瓶车¥25 自选'],['down','园区大 · 留足 3 小时']],q:'三亚南山文化旅游区'}]}];
const SY4_LODGES=[
 {opts:[{city:'三亚湾 · 海景房',price:460,why:'市区吃饭方便 · 落日就在窗外',q:'三亚湾酒店'},
        {city:'市区 · 商圈',price:300,why:'省 ¥80/人 · 第一市场走得到',q:'三亚市区酒店'}]},
 {city:'亚龙湾 · 沙滩边',price:680,why:'推门就是白沙滩 · 明早不用赶路',q:'三亚亚龙湾酒店'},
 {city:'亚龙湾 · 连住',price:680,why:'不挪窝 · 行李不动',q:'三亚亚龙湾酒店'},
 null];




/* ═══════════ 长沙 3 天 · 橘子洲与岳麓山（地铁 + 步行）═══════════ */
const CS_NODES=[
 {n:'五一广场·太平街',x:310,y:240,lx:13,ly:4,a:'start'},
 {n:'岳麓山·橘子洲',x:220,y:200,lx:-6,ly:-8,a:'middle'},
 {n:'马王堆·省博',x:400,y:190,lx:13,ly:-8,a:'end'}];
const CS3_DAYS=[
{tab:'D1',name:'橘子洲 · 岳麓山',sub:'江心洲与山顶 · 中',start:540,hardEnd:1290,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 橘子洲 · 地铁 2 号线 15 分',min:15,cost:3},
 post:{mode:'transit',conn:'岳麓山 → 住处 · 地铁 4 号线 25 分',min:25,cost:3},
 stops:[
 {k:'cs-juzizhou',name:'橘子洲 · 青年毛泽东像',era:'湘江江心洲',dur:100,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'五公里长的江心洲，站在头像下面往北看，湘江从两边流过去。',
  must:['必看','观光车¥20 绕全洲 · 周六烟花'],
  chips:[['up','免票'],['','观光车¥20 自选']],q:'长沙橘子洲'},
 {mode:'transit',conn:'橘子洲 → 岳麓山 · 地铁 4 号线 12 分',min:12,cost:3},
 {k:'cs-yuelu',name:'岳麓书院 · 爱晚亭',cng:'最美名山',era:'北宋开宝九年 · 千年学府',dur:140,prio:0,cost:60,cat:'tix',indoor:false,
  vibe:'书院讲堂那块"实事求是"的匾挂了一百年，后面上山就是爱晚亭。',
  must:['必看','岳麓书院 · 爱晚亭 · 山顶看湘江'],
  chips:[['','书院¥60'],['up','爬山免票'],['down','秋天枫叶最好']],q:'长沙岳麓书院'}]},
{tab:'D2',name:'太平街 · 文和友',sub:'老街与夜宵 · 轻',start:600,hardEnd:1320,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 太平街 · 步行 10 分',min:10,cost:0},
 post:{mode:'walk',conn:'步行回住处 · 12 分',min:12,cost:0},
 stops:[
 {k:'cs-taiping',name:'太平街 · 贾谊故居',era:'长沙唯一保存完整的老街',dur:90,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'青石板路两边全是小吃摊，贾谊故居夹在中间安静得像另一个世界。',
  must:['必吃','臭豆腐 · 糖油粑粑 · 贾谊故居免费'],
  chips:[['up','街区免票'],['','小吃人均¥40']],q:'长沙太平街'},
 {k:'cs-wenheyou',name:'超级文和友',era:'把八十年代整栋搬进商场',dur:100,prio:1,cost:90,cat:'food',indoor:true,
  vibe:'一整栋楼复刻了老长沙的筒子楼，霓虹招牌和晾衣杆全是真的。',
  must:['必点','小龙虾 · 臭豆腐 · 提前取号'],
  chips:[['','人均¥90'],['down','周末排队 2 小时']],q:'长沙超级文和友'},
 {k:'cs-night',name:'夜宵 · 小龙虾或糖油粑粑',era:'长沙的夜从十点开始',dur:80,prio:0,cost:80,cat:'food',indoor:true,
  opts:[{name:'口味虾大排档',cost:120,dur:90,vibe:'一盆口味虾配冰啤，长沙的夏夜标配。'},
        {name:'糖油粑粑 + 甜酒',cost:25,dur:40,vibe:'刚炸好的糖油粑粑外脆里糯，五块钱能吃饱。'}],
  id:'cs-food',
  must:['必点','口味虾 · 糖油粑粑 · 茶颜悦色'],
  chips:[['','人均¥25-120']],q:'长沙 夜宵'}]},
{tab:'D3',name:'湖南省博 · 收官',sub:'马王堆一上午 · 下午离开 · 轻',start:540,hardEnd:1170,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 省博 · 地铁 3 号线 20 分',min:20,cost:3},
 post:{mode:'transit',conn:'省博 → 长沙南站 · 地铁 3 号线转 4 号线 40 分',min:40,cost:5},
 stops:[
 {k:'cs-museum',name:'湖南省博物馆 · 马王堆',cng:'最美古镇',era:'西汉辛追墓 · 素纱襌衣',dur:160,prio:0,cost:0,cat:'free',indoor:true,
  vibe:'那件素纱襌衣只有 49 克，两千年前的织工水平至今复刻不出。',
  must:['必看','素纱襌衣 · T 形帛画 · 辛追墓复原'],
  chips:[['up','免票'],['down','提前 7 天预约 · 周一闭馆']],q:'湖南博物院'}]}];
const CS3_LODGES=[
 {opts:[{city:'五一广场 · 地铁枢纽',price:340,why:'三线换乘 · 走到太平街 10 分',q:'长沙五一广场酒店'},
        {city:'岳麓区 · 大学城',price:240,why:'省 ¥50/人 · 去岳麓山近',q:'长沙岳麓区酒店'}]},
 {city:'五一广场 · 连住',price:340,why:'不挪窝 · 行李不动',q:'长沙五一广场酒店'},
 null];

/* ═══════════ 贵州 5 天 · 苗寨与瀑布（包车 + 高铁）═══════════ */
const GZ_NODES=[
 {n:'贵阳',x:300,y:230,lx:13,ly:4,a:'start'},
 {n:'西江千户苗寨',x:410,y:190,lx:13,ly:-8,a:'middle'},
 {n:'荔波小七孔',x:360,y:320,lx:13,ly:12,a:'middle'},
 {n:'黄果树',x:190,y:270,lx:-6,ly:12,a:'end'}];
const GZ5_DAYS=[
{tab:'D1',name:'贵阳抵达 · 青岩古镇',sub:'落地不赶 · 半日古镇 · 极轻',start:660,hardEnd:1260,drive:'1 h',
 pre:{mode:'transit',conn:'龙洞堡机场 → 市区住处 · 地铁 2 号线 35 分',min:35,cost:5},
 post:{mode:'transit',conn:'青岩 → 贵阳住处 · 包车 50 分',min:50,cost:60},
 stops:[
 {k:'gz-arrive',name:'放行李 · 换鞋',era:'贵州多雨多山路',dur:30,prio:0,cost:0,cat:'free',indoor:true,
  vibe:'接下来几天都在山里走，先把防滑鞋和雨具备好。',
  must:['必做','贵州十天九雨 · 雨具随身'],
  chips:[['up','无门票']],q:'贵阳市区'},
 {k:'gz-qingyan',name:'青岩古镇',cng:'最美古镇',era:'明洪武十一年屯堡',dur:150,prio:0,cost:80,cat:'tix',indoor:false,
  vibe:'城墙用石头垒的，巷子也是石板，卖状元蹄的铺子排到街尾。',
  must:['必吃','状元蹄 · 玫瑰糖 · 北门城墙'],
  chips:[['','联票¥80'],['up','进古镇免票 · 景点联票']],q:'贵阳青岩古镇'}]},
{tab:'D2',name:'西江千户苗寨',sub:'包车进山 · 看夜景 · 中',start:480,hardEnd:1320,drive:'3 h',
 pre:{mode:'drive',conn:'贵阳 → 西江苗寨 · 200 km · 约 3 小时',min:180,km:200,cost:180,
   via:'沿途 · 凯里下高速 · 后半段盘山'},
 post:{mode:'walk',conn:'步行回寨内住处 · 15 分',min:15,cost:0},
 stops:[
 {k:'gz-xijiang',name:'西江千户苗寨',cng:'最美古镇',era:'一千多户吊脚楼依山而建',dur:300,prio:0,cost:110,cat:'tix',indoor:false,
  vibe:'天一黑，整面山坡的吊脚楼灯全亮，像把星空翻过来铺在山上。',
  must:['必看','观景台看全景 · 长桌宴 · 夜里灯全开'],
  chips:[['','门票¥110'],['','观光车¥20 自选'],['down','旺季寨内住宿贵']],q:'西江千户苗寨'}]},
{tab:'D3',name:'荔波小七孔',sub:'水上森林 · 长途转场 · 中',start:450,hardEnd:1290,drive:'4.5 h',
 pre:{mode:'drive',conn:'西江 → 荔波 · 280 km · 约 4 小时 30 分',min:270,km:280,cost:250,
   via:'沿途 · 山路多弯 · 中途服务区休整'},
 post:{mode:'drive',conn:'→ 荔波县城住处 · 30 km · 40 分',min:40,km:30,cost:0},
 stops:[
 {k:'gz-xiaoqikong',name:'小七孔 · 水上森林',cng:'最美峡谷',era:'道光十五年古桥',dur:240,prio:0,cost:130,cat:'tix',indoor:false,
  vibe:'水从树根之间流过去，人可以踩着石头在林子里蹚水走。',
  must:['必走','水上森林蹚水 · 68 级瀑布 · 卧龙潭'],
  chips:[['','门票¥110+车¥40'],['down','雨季水大封路']],q:'荔波小七孔'}]},
{tab:'D4',name:'黄果树瀑布',sub:'跨省转场 · 看大瀑布 · 中',start:450,hardEnd:1290,drive:'4 h',
 pre:{mode:'drive',conn:'荔波 → 黄果树 · 280 km · 约 4 小时',min:240,km:280,cost:240,
   via:'沿途 · 兰海高速 · 中途安顺午饭'},
 post:{mode:'drive',conn:'→ 安顺住处 · 45 km · 50 分',min:50,km:45,cost:0},
 stops:[
 {k:'gz-huangguoshu',name:'黄果树瀑布 · 水帘洞',cng:'最美峡谷',era:'亚洲第一大瀑布',dur:220,prio:0,cost:180,cat:'tix',indoor:false,
  vibe:'水从七十多米高砸下来，走进水帘洞能从瀑布背面看出去，浑身湿透。',
  must:['必走','水帘洞穿瀑布 · 备雨衣 · 陡坡电梯¥50'],
  chips:[['','联票¥180'],['down','夏季水量最大 · 必湿身']],q:'黄果树瀑布'}]},
{tab:'D5',name:'返程',sub:'安顺回贵阳 · 中午离开 · 轻',start:510,hardEnd:1140,drive:'1.5 h',
 pre:{mode:'drive',conn:'安顺 → 贵阳 · 110 km · 约 1 小时 30 分',min:90,km:110,cost:100},
 post:{mode:'transit',conn:'贵阳 → 机场/高铁站 · 地铁 30 分',min:30,cost:5},
 stops:[
 {k:'gz-lunch',name:'走之前 · 酸汤鱼',era:'苗家酸汤',dur:80,prio:0,cost:90,cat:'food',indoor:true,
  vibe:'红酸汤煮江团，酸得开胃，配一碟糊辣椒蘸水。',
  must:['必点','红酸汤鱼 · 折耳根蘸水 · 丝娃娃'],
  chips:[['','人均¥90']],q:'贵阳 酸汤鱼'}]}];
const GZ5_LODGES=[
 {city:'贵阳 · 市区',price:320,why:'机场地铁直达 · 明早出发方便',q:'贵阳市区酒店'},
 {opts:[{city:'西江苗寨 · 观景吊脚楼',price:520,why:'推窗看整面山的灯',q:'西江苗寨观景客栈'},
        {city:'西江 · 寨口民宿',price:300,why:'省 ¥110/人 · 走进寨子 10 分',q:'西江苗寨民宿'}]},
 {city:'荔波县城',price:300,why:'小七孔景区外 · 比景区内便宜',q:'荔波县城酒店'},
 {city:'安顺 · 黄果树附近',price:340,why:'明早第一批进瀑布',q:'安顺黄果树酒店'},
 null];





/* ═══════════ 福建土楼 3 天 · 客家围屋（高铁 + 包车）═══════════ */
const TL_NODES=[
 {n:'厦门·龙岩',x:300,y:250,lx:13,ly:4,a:'start'},
 {n:'南靖田螺坑',x:250,y:180,lx:-6,ly:-8,a:'middle'},
 {n:'永定洪坑',x:370,y:180,lx:13,ly:-8,a:'end'}];
const TL3_DAYS=[
{tab:'D1',name:'南靖 · 田螺坑四菜一汤',sub:'高铁转包车 · 中',start:480,hardEnd:1290,drive:'2 h',
 pre:{mode:'transit',conn:'厦门 → 南靖站 · 动车 50 分 + 包车 90 分',min:140,cost:160,
   via:'南靖站有直达土楼的旅游专线'},
 post:{mode:'drive',conn:'→ 云水谣住处 · 25 km · 40 分',min:40,km:25,cost:0},
 stops:[
 {k:'tl-tianluokeng',name:'田螺坑土楼群',cng:'最美古镇',era:'明清客家围屋 · 世界遗产',dur:150,prio:0,cost:100,cat:'tix',indoor:false,
  vibe:'四个圆楼围着一个方楼，从山上观景台看下去，当地人叫它四菜一汤。',
  must:['必看','上观景台看全景 · 下到楼里看天井'],
  chips:[['','联票¥100'],['down','需包车或专线 · 公交不便']],q:'南靖田螺坑土楼群'},
 {k:'tl-yunshuiyao',name:'云水谣古镇',era:'榕树与鹅卵石路',dur:120,prio:1,cost:90,cat:'tix',indoor:false,
  vibe:'一条溪穿过村子，岸边十几棵百年老榕，水车吱呀吱呀转。',
  must:['必逛','千年古榕 · 和贵楼 · 溪边走一圈'],
  chips:[['','门票¥90']],q:'云水谣古镇'}]},
{tab:'D2',name:'永定 · 洪坑土楼群',sub:'振成楼与客家生活 · 中',start:510,hardEnd:1260,drive:'2.5 h',
 pre:{mode:'drive',conn:'云水谣 → 永定洪坑 · 90 km · 约 2 小时',min:120,km:90,cost:180,
   via:'沿途 · 山路多弯 · 包车按天算'},
 post:{mode:'drive',conn:'→ 洪坑住处 · 3 km · 8 分',min:8,km:3,cost:0},
 stops:[
 {k:'tl-zhencheng',name:'振成楼 · 土楼王子',cng:'最美古镇',era:'1912 年建 · 中西合璧',dur:150,prio:0,cost:90,cat:'tix',indoor:false,
  vibe:'外圈是客家夯土，内圈却是西洋柱廊，一栋楼里住过四百多人。',
  must:['必看','振成楼 · 奎聚楼 · 福裕楼'],
  chips:[['','洪坑景区¥90']],q:'永定振成楼'},
 {k:'tl-hakka',name:'客家土楼人家 · 午饭',era:'楼里还住着人',dur:90,prio:0,cost:60,cat:'food',indoor:true,
  vibe:'在土楼的天井里吃饭，头顶是一圈天，桌上是芋子包和梅菜扣肉。',
  must:['必点','芋子包 · 梅菜扣肉 · 土楼米酒'],
  chips:[['','人均¥60']],q:'永定土楼农家菜'}]},
{tab:'D3',name:'初溪土楼群 · 返程',sub:'最原始的一片 · 下午回厦门 · 中',start:510,hardEnd:1200,drive:'4 h',
 pre:{mode:'drive',conn:'洪坑 → 初溪 · 50 km · 约 1 小时 20 分',min:80,km:50,cost:120},
 post:{mode:'transit',conn:'初溪 → 厦门 · 包车 + 动车 约 3 小时',min:180,cost:200},
 stops:[
 {k:'tl-chuxi',name:'初溪土楼群',cng:'最美古镇',era:'集庆楼建于 1419 年',dur:150,prio:0,cost:70,cat:'tix',indoor:false,
  vibe:'比田螺坑安静得多，集庆楼里 72 道楼梯各自独立，六百年没塌。',
  must:['必看','集庆楼 72 道楼梯 · 观景台看全群'],
  chips:[['','门票¥70'],['up','人比南靖少很多']],q:'永定初溪土楼群'}]}];
const TL3_LODGES=[
 {city:'云水谣 · 溪边客栈',price:280,why:'古榕就在门口 · 夜里安静',q:'云水谣客栈'},
 {city:'洪坑 · 土楼民宿',price:300,why:'住在土楼里 · 天井看星星',q:'永定洪坑土楼民宿'},
 null];

/* ═══════════ 泰山曲阜 3 天 · 登顶与孔府（高铁 + 步行）═══════════ */
const TS_NODES=[
 {n:'泰安·泰山',x:300,y:220,lx:13,ly:4,a:'start'},
 {n:'曲阜三孔',x:380,y:300,lx:13,ly:12,a:'end'}];
const TS3_DAYS=[
{tab:'D1',name:'泰山 · 红门登顶',sub:'七千级台阶 · 重',start:420,hardEnd:1290,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 红门登山口 · 公交 20 分',min:20,cost:2,
   via:'红门是传统登山道起点 · 全程约 6 小时'},
 post:{mode:'transit',conn:'南天门 → 山顶住处 · 步行 20 分',min:20,cost:0},
 stops:[
 {k:'ts-hongmen',name:'红门 · 中天门',cng:'最美名山',era:'历代帝王封禅之路',dur:210,prio:0,cost:115,cat:'tix',indoor:false,
  vibe:'一路都是石刻，从红门到中天门这段还算缓，真正的硬仗在后面。',
  must:['必走','红门起步 · 中天门可坐索道跳过'],
  chips:[['','门票¥115'],['','索道¥100 自选'],['down','全程 7000 级台阶']],q:'泰山红门'},
 {k:'ts-shibapan',name:'十八盘 · 南天门',cng:'最美名山',era:'最陡的 1600 级',dur:150,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'最后那段陡到要手脚并用，抬头就是南天门那道石门框着天。',
  must:['必爬','慢慢来 · 不赶时间'],
  chips:[['up','门票已含'],['down','最陡一段 · 量力而行']],q:'泰山十八盘'}]},
{tab:'D2',name:'日观峰日出 · 下山',sub:'四点起床 · 中',start:240,hardEnd:1260,drive:'0 h',
 pre:{mode:'walk',conn:'住处 → 日观峰 · 步行 25 分',min:25,cost:0,
   via:'日出前 40 分到位 · 山顶风大'},
 post:{mode:'transit',conn:'索道下山 → 泰安市区 · 约 90 分',min:90,cost:110},
 stops:[
 {k:'ts-sunrise',name:'日观峰日出',cng:'最美名山',era:'孔子登东山而小鲁',dur:120,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'云海在脚下，太阳从海那边爬出来，四周全是裹着军大衣等日出的人。',
  must:['必看','日出前 40 分到 · 山顶租军大衣¥30'],
  chips:[['up','门票已含'],['down','山顶 5–10℃ · 必备厚衣']],q:'泰山日观峰'},
 {k:'ts-daimiao',name:'岱庙',era:'历代帝王封禅前祭天处',dur:100,prio:1,cost:30,cat:'tix',indoor:false,
  vibe:'和故宫太和殿同规格的天贶殿，宋代壁画画的就是封禅仪仗。',
  must:['必看','天贶殿宋代壁画 · 汉柏'],
  chips:[['','门票¥30']],q:'泰安岱庙'}]},
{tab:'D3',name:'曲阜三孔 · 返程',sub:'孔庙孔府孔林 · 下午离开 · 轻',start:510,hardEnd:1200,drive:'0 h',
 pre:{mode:'transit',conn:'泰安 → 曲阜东 · 高铁 20 分 + 公交 25 分',min:45,cost:45},
 post:{mode:'transit',conn:'曲阜东站 → 返程 · 公交 25 分',min:25,cost:3},
 stops:[
 {k:'ts-kongmiao',name:'孔庙 · 大成殿',cng:'最美古镇',era:'公元前 478 年始建',dur:150,prio:0,cost:140,cat:'tix',indoor:false,
  vibe:'大成殿前那十根蟠龙石柱是明代雕的，据说皇帝来时要用红绸盖住。',
  must:['必看','大成殿蟠龙柱 · 杏坛 · 三孔联票'],
  chips:[['','三孔联票¥140'],['','孔林需坐车¥20']],q:'曲阜孔庙'},
 {k:'ts-konglin',name:'孔林 · 孔子墓',era:'延续两千五百年的家族墓地',dur:110,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'世界上延续时间最长的家族墓地，十万座坟散在两万棵古树之间。',
  must:['必看','孔子墓 · 子贡手植楷'],
  chips:[['up','联票已含'],['','园区大 · 可坐观光车']],q:'曲阜孔林'}]}];
const TS3_LODGES=[
 {city:'泰山山顶 · 神憩宾馆',price:680,why:'不用摸黑爬夜山 · 明早直接看日出',q:'泰山山顶宾馆'},
 {opts:[{city:'泰安 · 岱庙旁',price:320,why:'高铁站近 · 明早去曲阜方便',q:'泰安岱庙酒店'},
        {city:'泰安 · 火车站旁',price:240,why:'省 ¥40/人',q:'泰安火车站酒店'}]},
 null];

/* ═══════════ 九寨沟黄龙 4 天 · 彩林季（自驾）═══════════ */
const JZ_NODES=[
 {n:'成都',x:280,y:300,lx:-6,ly:12,a:'start'},
 {n:'九寨沟',x:360,y:170,lx:13,ly:-8,a:'middle'},
 {n:'黄龙',x:300,y:220,lx:-6,ly:4,a:'end'}];
const JZ4_DAYS=[
{tab:'D1',name:'成都 → 九寨沟',sub:'岷江河谷长途 · 中',start:420,hardEnd:1290,drive:'8 h',
 pre:{mode:'drive',conn:'成都 → 九寨沟 · 430 km · 约 8 小时',min:480,km:430,cost:400,
   via:'沿途 · 都汶高速转 G213 · 茂县午饭 · 后段沿岷江'},
 post:{mode:'drive',conn:'→ 沟口住处 · 5 km · 10 分',min:10,km:5,cost:0},
 stops:[
 {k:'jz-diexi',name:'叠溪海子 · 途中',era:'1933 年地震形成的堰塞湖',dur:40,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'湖水绿得发假，是一场地震把整座城压在了下面。',
  must:['必看','公路边观景台 · 停车 20 分'],
  chips:[['up','免票']],q:'叠溪海子'}]},
{tab:'D2',name:'九寨沟一整天',sub:'三条沟走全 · 中',start:390,hardEnd:1230,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 沟口 · 步行 15 分',min:15,cost:0,
   via:'7:00 前到闸机排队 · 观光车通票已含'},
 post:{mode:'transit',conn:'沟口 → 住处 · 步行 15 分',min:15,cost:0},
 stops:[
 {k:'jz-wuhuahai',name:'五花海 · 箭竹海',cng:'最美湖泊',era:'钙华堰塞湖群',dur:200,prio:0,cost:190,cat:'tix',indoor:false,
  vibe:'水底的枯树被钙华裹成白色，阳光一照，一个湖里能看出五种蓝。',
  must:['必看','先坐车到原始森林 · 一路往下走'],
  chips:[['','门票¥190+车¥90'],['down','旺季需提前 3 天预约']],q:'九寨沟五花海'},
 {k:'jz-nuorilang',name:'诺日朗瀑布 · 树正群海',cng:'最美峡谷',era:'中国最宽的钙华瀑布',dur:150,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'水从三百米宽的台地上整片跌下来，秋天两边全是黄红的树。',
  must:['必看','诺日朗观景台 · 树正栈道走一段'],
  chips:[['up','门票已含'],['','10 月下旬彩林最好']],q:'九寨沟诺日朗瀑布'}]},
{tab:'D3',name:'黄龙 · 五彩池',sub:'高原钙华梯池 · 中',start:450,hardEnd:1260,drive:'3 h',
 pre:{mode:'drive',conn:'九寨沟 → 黄龙 · 130 km · 约 2 小时 30 分',min:150,km:130,cost:130,
   via:'沿途 · 翻雪山梁 4000m · 备高反药'},
 post:{mode:'drive',conn:'黄龙 → 川主寺住处 · 55 km · 1 小时',min:60,km:55,cost:0},
 stops:[
 {k:'jz-huanglong',name:'黄龙 · 五彩池',cng:'最美湖泊',era:'世界最大钙华景观',dur:240,prio:0,cost:170,cat:'tix',indoor:false,
  vibe:'三千多个钙华池顺着山坡叠下来，池边是金黄的边，池水从蓝到绿。',
  must:['必走','索道上步行下 · 五彩池在最高处 3600m'],
  chips:[['','门票¥170'],['','索道¥80 自选'],['down','海拔 3600m · 慢走勿急']],q:'黄龙风景区'}]},
{tab:'D4',name:'川主寺 → 成都 · 返程',sub:'回程 · 中',start:480,hardEnd:1230,drive:'7 h',
 pre:{mode:'drive',conn:'川主寺 → 成都 · 380 km · 约 7 小时',min:420,km:380,cost:360,
   via:'沿途 · 松潘古城可停 40 分'},
 post:{mode:'transit',conn:'→ 还车点 · 打车 20 分',min:20,cost:30},
 stops:[
 {k:'jz-songpan',name:'松潘古城 · 途中',era:'明洪武十二年边城',dur:60,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'城墙还在，城门洞下面卖牦牛肉干的摊子一字排开。',
  must:['必看','古城墙 · 带牦牛肉干'],
  chips:[['up','免票']],q:'松潘古城'}]}];
const JZ4_LODGES=[
 {opts:[{city:'九寨沟口 · 观景',price:420,why:'明早步行进沟 · 不用赶车',q:'九寨沟口酒店'},
        {city:'漳扎镇',price:280,why:'省 ¥70/人 · 吃饭方便',q:'九寨沟漳扎镇酒店'}]},
 {city:'九寨沟口 · 连住',price:420,why:'不挪窝 · 行李不动',q:'九寨沟口酒店'},
 {city:'川主寺镇',price:300,why:'黄龙与成都之间 · 明早好走',q:'川主寺镇酒店'},
 null];

/* ═══════════ 伊犁 6 天 · 河谷深度（自驾）═══════════ */
const YL_NODES=[
 {n:'伊宁',x:230,y:230,lx:-6,ly:4,a:'start'},
 {n:'那拉提·巴音布鲁克',x:400,y:190,lx:13,ly:-8,a:'middle'},
 {n:'昭苏·特克斯',x:280,y:320,lx:-2,ly:16,a:'end'}];
const YL6_DAYS=[
{tab:'D1',name:'伊宁 · 六星街',sub:'落地慢逛 · 轻',start:660,hardEnd:1320,drive:'0 h',
 pre:{mode:'transit',conn:'伊宁机场 → 市区住处 · 打车 25 分',min:25,cost:35},
 post:{mode:'walk',conn:'步行回住处 · 10 分',min:10,cost:0},
 stops:[
 {k:'yl-liuxing',name:'六星街 · 手风琴博物馆',cng:'最美古镇',era:'1934 年规划的六芒星街区',dur:150,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'蓝色的窗框、俄式小楼、院子里种满花，随便推开一家门就是咖啡馆。',
  must:['必看','手风琴博物馆 · 亚历山大手风琴 · 冰淇淋'],
  chips:[['up','街区免票'],['','手风琴馆¥20 自选']],q:'伊宁六星街'}]},
{tab:'D2',name:'伊宁 → 那拉提',sub:'河谷草原 · 中',start:480,hardEnd:1290,drive:'4 h',
 pre:{mode:'drive',conn:'伊宁 → 那拉提 · 260 km · 约 4 小时',min:240,km:260,cost:230,
   via:'沿途 · 伊犁河谷 · 巩乃斯河一路相伴'},
 post:{mode:'drive',conn:'→ 那拉提镇住处 · 10 km · 20 分',min:20,km:10,cost:0},
 stops:[
 {k:'yl-nalati',name:'那拉提空中草原',cng:'最美草原',era:'世界四大高山河谷草原',dur:210,prio:0,cost:145,cat:'tix',indoor:false,
  vibe:'草原铺在半山腰上，云影从坡上滚过去，哈萨克毡房散在草里。',
  must:['必玩','空中草原区间车 · 骑马 1 小时'],
  chips:[['','门票+车¥145'],['','骑马¥100 自选']],q:'那拉提空中草原'}]},
{tab:'D3',name:'巴音布鲁克 · 九曲十八弯',sub:'看落日九个太阳 · 中',start:450,hardEnd:1320,drive:'3 h',
 pre:{mode:'drive',conn:'那拉提 → 巴音布鲁克 · 130 km · 约 2 小时 30 分',min:150,km:130,cost:130,
   via:'沿途 · 翻越那拉提达坂 · 独库北段起点'},
 post:{mode:'drive',conn:'→ 巴音镇住处 · 15 km · 25 分',min:25,km:15,cost:0},
 stops:[
 {k:'yl-jiuqu',name:'九曲十八弯 · 日落',cng:'最美湿地',era:'开都河在草原上绕出的曲流',dur:180,prio:0,cost:110,cat:'tix',indoor:false,
  vibe:'日落那十分钟，河的每一道弯里都嵌着一个太阳，最多能数到九个。',
  must:['必看','日落前 1.5 小时进 · 爬观景台'],
  chips:[['','门票+车¥110'],['down','海拔 2500m 风大 · 带厚衣']],q:'巴音布鲁克九曲十八弯'}]},
{tab:'D4',name:'巴音 → 特克斯八卦城',sub:'转场 · 八卦格局 · 中',start:480,hardEnd:1290,drive:'4 h',
 pre:{mode:'drive',conn:'巴音布鲁克 → 特克斯 · 250 km · 约 4 小时',min:240,km:250,cost:220,
   via:'沿途 · 返程翻达坂 · 经巩留'},
 post:{mode:'drive',conn:'→ 特克斯住处 · 5 km · 10 分',min:10,km:5,cost:0},
 stops:[
 {k:'yl-tekesi',name:'特克斯八卦城',cng:'最美古镇',era:'按易经八卦布局的城',dur:120,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'全城没有一个红绿灯，八条主街从中心呈放射状铺开，走着走着就绕回原地。',
  must:['必看','八卦文化城观景塔看全城格局'],
  chips:[['up','城区免票'],['','观景塔¥30 自选']],q:'特克斯八卦城'}]},
{tab:'D5',name:'昭苏 · 天马与油菜花',sub:'草原马场 · 轻',start:540,hardEnd:1290,drive:'2 h',
 pre:{mode:'drive',conn:'特克斯 → 昭苏 · 90 km · 约 1 小时 40 分',min:100,km:90,cost:90},
 post:{mode:'drive',conn:'→ 昭苏住处 · 12 km · 20 分',min:20,km:12,cost:0},
 stops:[
 {k:'yl-zhaosu',name:'昭苏草原 · 天马场',cng:'最美草原',era:'伊犁马原产地',dur:180,prio:0,cost:80,cat:'tix',indoor:false,
  vibe:'找一匹伊犁马跑起来，草原一直铺到天山脚下，七月还有大片油菜花。',
  must:['必做','骑马 1 小时 · 7 月油菜花期'],
  chips:[['','马场¥80'],['','7 月花期最好']],q:'昭苏天马旅游文化园'}]},
{tab:'D6',name:'昭苏 → 伊宁 · 返程',sub:'回程 · 轻',start:540,hardEnd:1200,drive:'3 h',
 pre:{mode:'drive',conn:'昭苏 → 伊宁 · 180 km · 约 3 小时',min:180,km:180,cost:160,
   via:'沿途 · 经察布查尔 · 锡伯族聚居地'},
 post:{mode:'transit',conn:'→ 伊宁机场 · 打车 25 分',min:25,cost:35},
 stops:[
 {k:'yl-lunch',name:'走之前 · 手抓饭与馕坑肉',era:'伊犁的最后一顿',dur:80,prio:0,cost:70,cat:'food',indoor:true,
  vibe:'羊肉手抓饭油润不腻，配一碗酸奶刚好解腻。',
  must:['必点','手抓饭 · 馕坑肉 · 卡瓦斯'],
  chips:[['','人均¥70']],q:'伊宁 手抓饭'}]}];
const YL6_LODGES=[
 {city:'伊宁 · 六星街旁',price:320,why:'夜里逛街走得到',q:'伊宁六星街酒店'},
 {city:'那拉提镇',price:360,why:'明早进草原近',q:'那拉提镇酒店'},
 {city:'巴音布鲁克镇',price:340,why:'看完日落不用赶夜路',q:'巴音布鲁克酒店'},
 {city:'特克斯 · 八卦城内',price:280,why:'城里步行即可',q:'特克斯县酒店'},
 {city:'昭苏县城',price:280,why:'马场附近 · 安静',q:'昭苏县城酒店'},
 null];

/* ═══════════ 南疆 8 天 · 喀什与帕米尔（自驾）═══════════ */
const NJG_NODES=[
 {n:'喀什',x:200,y:250,lx:-6,ly:4,a:'start'},
 {n:'塔县·帕米尔',x:230,y:340,lx:-2,ly:16,a:'middle'},
 {n:'和田',x:360,y:300,lx:13,ly:12,a:'middle'},
 {n:'库车·天山',x:380,y:170,lx:13,ly:-8,a:'end'}];
const NJG8_DAYS=[
{tab:'D1',name:'喀什老城 · 艾提尕尔',sub:'落地就是另一个国度 · 轻',start:660,hardEnd:1320,drive:'0 h',
 pre:{mode:'transit',conn:'喀什机场 → 老城住处 · 打车 30 分',min:30,cost:40},
 post:{mode:'walk',conn:'步行回住处 · 10 分',min:10,cost:0},
 stops:[
 {k:'nj-oldcity',name:'喀什噶尔老城',cng:'最美古镇',era:'两千年土陶城',dur:180,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'土黄色的巷子拐来拐去，门口坐着打馕的、修铜壶的，小孩在巷子里追着跑。',
  must:['必逛','早上 10 点开城仪式 · 往深巷走 · 百年老茶馆'],
  chips:[['up','免票'],['','开城仪式 10:00']],q:'喀什噶尔老城'},
 {k:'nj-idkah',name:'艾提尕尔清真寺',era:'1442 年建',dur:70,prio:1,cost:45,cat:'tix',indoor:false,
  vibe:'新疆最大的清真寺，黄砖拱门前的广场永远有人在晒太阳。',
  must:['必看','外观免费 · 入内需着装得体'],
  chips:[['','门票¥45'],['down','礼拜时段不开放']],q:'喀什艾提尕尔清真寺'}]},
{tab:'D2',name:'喀什 → 塔县',sub:'中巴公路 · 白沙湖 · 中',start:480,hardEnd:1290,drive:'5 h',
 pre:{mode:'drive',conn:'喀什 → 塔县 · 290 km · 约 5 小时',min:300,km:290,cost:260,
   via:'沿途 · 中巴公路 G314 · 需边境通行证'},
 post:{mode:'drive',conn:'→ 塔县住处 · 10 km · 15 分',min:15,km:10,cost:0},
 stops:[
 {k:'nj-baisha',name:'白沙湖 · 白沙山',cng:'最美湖泊',era:'帕米尔高原东缘',dur:90,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'一整座山是白沙堆的，湖水绿得发蓝，两个颜色贴在一起假得像画。',
  must:['必看','公路边观景台 · 逆光更蓝'],
  chips:[['up','免票'],['down','海拔 3300m 慢走']],q:'新疆白沙湖'},
 {k:'nj-karakul',name:'卡拉库里湖 · 慕士塔格',cng:'最美湖泊',era:'冰山之父倒影',dur:100,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'7546 米的慕士塔格峰整个倒在湖里，天气好的时候连雪线都照得清清楚楚。',
  must:['必看','湖边看倒影 · 柯尔克孜毡房喝奶茶'],
  chips:[['up','免票'],['down','海拔 3600m']],q:'卡拉库里湖'}]},
{tab:'D3',name:'塔县 · 石头城',sub:'金草滩与边境 · 轻',start:540,hardEnd:1260,drive:'1 h',
 pre:{mode:'drive',conn:'住处 → 石头城 · 5 km · 10 分',min:10,km:5,cost:0},
 post:{mode:'drive',conn:'→ 住处 · 8 km · 15 分',min:15,km:8,cost:0},
 stops:[
 {k:'nj-shitou',name:'石头城 · 金草滩',cng:'最美草原',era:'汉代蒲犁国都城',dur:150,prio:0,cost:30,cat:'tix',indoor:false,
  vibe:'土黄的城墙残垣立在高处，脚下是一整片金黄草滩，远处一圈全是雪山。',
  must:['必看','日落时草滩最金 · 城墙上看全景'],
  chips:[['','门票¥30'],['down','海拔 3100m 风大']],q:'塔什库尔干石头城'},
 {k:'nj-panlong',name:'盘龙古道',era:'六百多个弯',dur:120,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'柏油路在山上盘成一条龙，从高处看下去像有人用笔画上去的。',
  must:['必开','往返约 2 小时 · 山顶看全貌'],
  chips:[['up','免票'],['down','弯多路窄 · 新手慎入']],q:'新疆盘龙古道'}]},
{tab:'D4',name:'塔县 → 和田',sub:'长途转场 · 中',start:420,hardEnd:1320,drive:'8 h',
 pre:{mode:'drive',conn:'塔县 → 和田 · 590 km · 约 8 小时',min:480,km:590,cost:500,
   via:'沿途 · 经莎车叶城 · 全天赶路 · 备干粮'},
 post:{mode:'drive',conn:'→ 和田市区住处 · 8 km · 15 分',min:15,km:8,cost:0},
 stops:[
 {k:'nj-yecheng',name:'叶城 · 零公里碑',era:'新藏线起点',dur:40,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'新藏公路从这里往南一直通到阿里，碑前停满了要进藏的越野车。',
  must:['必拍','零公里碑 · 加满油'],
  chips:[['up','免票']],q:'叶城零公里'}]},
{tab:'D5',name:'和田 · 玉龙喀什河',sub:'夜市与捡玉 · 轻',start:600,hardEnd:1320,drive:'0 h',
 pre:{mode:'drive',conn:'住处 → 玉龙喀什河 · 6 km · 15 分',min:15,km:6,cost:0},
 post:{mode:'drive',conn:'→ 夜市 · 5 km · 12 分',min:12,km:5,cost:0},
 stops:[
 {k:'nj-yulong',name:'玉龙喀什河 · 捡玉',era:'和田玉主产区',dur:100,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'河滩上全是弯腰翻石头的人，捡到的概率极低，但那个氛围值得看一眼。',
  must:['必看','河滩看当地人捡玉 · 别买路边玉'],
  chips:[['up','免费'],['down','路边兜售多为假货']],q:'和田玉龙喀什河'},
 {k:'nj-nightmkt',name:'和田夜市',era:'南疆最大夜市',dur:120,prio:0,cost:70,cat:'food',indoor:false,
  vibe:'烤全羊在门口转，玫瑰花酱酸奶粽子甜得刚好，人多得挪不动。',
  must:['必吃','烤羊 · 玫瑰花酱酸奶 · 缸子肉'],
  chips:[['','人均¥70'],['','20:00 后最热闹']],q:'和田夜市'}]},
{tab:'D6',name:'和田 → 库车',sub:'穿塔克拉玛干 · 中',start:420,hardEnd:1320,drive:'8 h',
 pre:{mode:'drive',conn:'和田 → 库车 · 620 km · 约 8 小时',min:480,km:620,cost:520,
   via:'沿途 · 穿越沙漠公路 · 两侧全是草方格'},
 post:{mode:'drive',conn:'→ 库车住处 · 10 km · 20 分',min:20,km:10,cost:0},
 stops:[
 {k:'nj-desert',name:'塔克拉玛干沙漠公路',cng:'最美雅丹',era:'世界最长流动沙漠公路',dur:120,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'五百公里全是沙，路两边的草方格是人一格一格扎出来挡沙的。',
  must:['必看','中途观景台停车 · 加满油再进'],
  chips:[['up','免票'],['down','沿途无补给 · 备水与油']],q:'塔克拉玛干沙漠公路'}]},
{tab:'D7',name:'库车 · 天山神秘大峡谷',sub:'红色峡谷 · 中',start:510,hardEnd:1260,drive:'2 h',
 pre:{mode:'drive',conn:'库车 → 神秘大峡谷 · 70 km · 约 1 小时 20 分',min:80,km:70,cost:70},
 post:{mode:'drive',conn:'→ 库车住处 · 70 km · 1 小时 20 分',min:80,km:70,cost:70},
 stops:[
 {k:'nj-canyon',name:'天山神秘大峡谷',cng:'最美峡谷',era:'红色砂砾岩',dur:180,prio:0,cost:45,cat:'tix',indoor:false,
  vibe:'峡谷窄到两人并排走都费劲，抬头是一线天，岩壁红得像烧过。',
  must:['必走','走到底约 5 km · 阿艾石窟'],
  chips:[['','门票¥45'],['down','雨天禁入 · 有山洪风险']],q:'库车天山神秘大峡谷'}]},
{tab:'D8',name:'库车 → 乌鲁木齐 · 返程',sub:'独库南段收尾 · 中',start:450,hardEnd:1230,drive:'7 h',
 pre:{mode:'drive',conn:'库车 → 乌鲁木齐 · 750 km · 约 7 小时',min:420,km:750,cost:620,
   via:'沿途 · 走独库南段或吐和高速'},
 post:{mode:'transit',conn:'→ 地窝堡机场 · 打车 40 分',min:40,cost:60},
 stops:[
 {k:'nj-return',name:'还车 · 返程',era:'南疆环线收官',dur:60,prio:0,cost:0,cat:'free',indoor:true,
  vibe:'八天两千七百公里，从土城到雪山到沙漠，一趟走完南疆的骨架。',
  must:['必做','还车前加满油 · 检查车况'],
  chips:[['up','无门票']],q:'乌鲁木齐地窝堡机场'}]}];
const NJG8_LODGES=[
 {opts:[{city:'喀什老城 · 民宿',price:320,why:'走进老城 2 分 · 早上看开城仪式',q:'喀什老城民宿'},
        {city:'喀什市区 · 快捷',price:220,why:'省 ¥50/人 · 停车方便',q:'喀什市区酒店'}]},
 {city:'塔县 · 县城酒店',price:380,why:'海拔 3100m · 有供氧房',q:'塔什库尔干酒店'},
 {city:'塔县 · 连住',price:380,why:'不挪窝 · 明早走盘龙古道',q:'塔什库尔干酒店'},
 {city:'和田市区',price:300,why:'夜市走得到',q:'和田市区酒店'},
 {city:'和田 · 连住',price:300,why:'不挪窝 · 明早穿沙漠',q:'和田市区酒店'},
 {city:'库车 · 市区',price:280,why:'明早去大峡谷近',q:'库车市区酒店'},
 {city:'库车 · 连住',price:280,why:'不挪窝 · 明早返程',q:'库车市区酒店'},
 null];

/* ═══════════ 西双版纳 4 天 · 雨林与傣味（全程打车）═══════════ */
const BN_NODES=[
 {n:'景洪·告庄',x:310,y:250,lx:13,ly:4,a:'start'},
 {n:'野象谷·基诺山',x:330,y:170,lx:13,ly:-8,a:'middle'},
 {n:'橄榄坝·傣族园',x:390,y:310,lx:13,ly:12,a:'end'}];
const BN4_DAYS=[
{tab:'D1',name:'抵达 · 告庄西双景',sub:'落地就热 · 夜市开场 · 极轻',start:720,hardEnd:1320,drive:'0 h',
 pre:{mode:'transit',conn:'嘎洒机场 → 告庄住处 · 打车 30 分',min:30,cost:40},
 post:{mode:'walk',conn:'步行回住处 · 8 分',min:8,cost:0},
 stops:[
 {k:'bn-arrive',name:'放行李 · 换短袖',era:'版纳全年短袖',dur:30,prio:0,cost:0,cat:'free',indoor:true,
  vibe:'一下飞机就是热带的湿热，长袖收起来吧。',
  must:['必备','防蚊液 · 防晒 · 雨伞'],
  chips:[['up','无门票']],q:'景洪告庄西双景'},
 {k:'bn-dazhuang',name:'告庄 · 大金塔',cng:'最美古镇',era:'仿景洪古城',dur:90,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'金塔一亮，整片湄公河边的仿古建筑都镀了一层金。',
  must:['必看','日落后金塔亮灯 · 江边散步'],
  chips:[['up','免票'],['','夜里最好看']],q:'西双版纳告庄西双景'},
 {k:'bn-night',name:'星光夜市 · 傣味',era:'东南亚风夜市',dur:100,prio:0,cost:80,cat:'food',indoor:false,
  vibe:'烤五花肉、菠萝饭、舂鸡脚，配一杯手打柠檬茶。',
  must:['必吃','包烧 · 舂鸡脚 · 菠萝饭 · 手抓饭'],
  chips:[['','人均¥80'],['down','周末人多']],q:'西双版纳星光夜市'}]},
{tab:'D2',name:'野象谷 · 基诺山寨',sub:'雨林一整天 · 中',start:510,hardEnd:1260,drive:'0 h',
 pre:{mode:'transit',conn:'景洪 → 野象谷 · 打车 50 分',min:50,cost:80,
   via:'昆磨高速 · 或坐景区专线大巴'},
 post:{mode:'transit',conn:'基诺山 → 住处 · 打车 60 分',min:60,cost:90},
 stops:[
 {k:'bn-elephant',name:'野象谷 · 空中走廊',cng:'最美湿地',era:'亚洲象保护区',dur:180,prio:0,cost:65,cat:'tix',indoor:false,
  vibe:'走在树冠层的钢索桥上，运气好能看见野象群从下面的沟谷经过。',
  must:['必走','空中走廊 · 大象学校 · 索道¥50 自选'],
  chips:[['','门票¥65'],['down','野象随缘 · 不保证见到']],q:'西双版纳野象谷'},
 {k:'bn-jinuo',name:'基诺山寨',era:'中国最后确认的少数民族',dur:120,prio:1,cost:100,cat:'tix',indoor:false,
  vibe:'基诺族 1979 年才被确认为独立民族，寨子里还在用最老的方式做茶。',
  must:['必看','大鼓舞 · 手工制茶 · 卓巴长老家'],
  chips:[['','门票¥100']],q:'西双版纳基诺山寨'}]},
{tab:'D3',name:'橄榄坝 · 傣族园',sub:'泼水与佛寺 · 轻',start:540,hardEnd:1290,drive:'0 h',
 pre:{mode:'transit',conn:'景洪 → 橄榄坝 · 打车 45 分',min:45,cost:70},
 post:{mode:'transit',conn:'橄榄坝 → 住处 · 打车 45 分',min:45,cost:70},
 stops:[
 {k:'bn-daizu',name:'傣族园 · 天天泼水',era:'五个傣族自然村',dur:180,prio:0,cost:55,cat:'tix',indoor:false,
  vibe:'不用等四月，园里每天下午两场泼水，全身湿透是标配。',
  must:['必玩','14:00 与 16:00 泼水场 · 带换洗'],
  chips:[['','门票¥55'],['down','必湿身 · 手机装防水袋']],q:'西双版纳傣族园'},
 {k:'bn-manting',name:'曼听公园 · 总佛寺',era:'傣王御花园',dur:90,prio:1,cost:40,cat:'tix',indoor:false,
  vibe:'一千三百年的御花园，旁边就是南传佛教的总佛寺，僧人在树下诵经。',
  must:['必看','总佛寺 · 白塔 · 孔雀放飞'],
  chips:[['','门票¥40']],q:'西双版纳曼听公园'}]},
{tab:'D4',name:'中科院植物园 · 返程',sub:'热带植物园 · 下午飞走 · 轻',start:510,hardEnd:1170,drive:'0 h',
 pre:{mode:'transit',conn:'景洪 → 勐仑植物园 · 打车 80 分',min:80,cost:120},
 post:{mode:'transit',conn:'植物园 → 嘎洒机场 · 打车 90 分',min:90,cost:140},
 stops:[
 {k:'bn-garden',name:'中科院热带植物园',cng:'最美湿地',era:'亚洲最大热带植物园',dur:200,prio:0,cost:80,cat:'tix',indoor:false,
  vibe:'一万三千种热带植物，望天树高到要仰头看，绞杀榕把宿主整个吞掉。',
  must:['必看','望天树 · 绞杀榕 · 王莲 · 电瓶车¥40'],
  chips:[['','门票¥80'],['','电瓶车¥40 自选'],['down','园区巨大 · 留足 3 小时']],q:'中科院西双版纳热带植物园'}]}];
const BN4_LODGES=[
 {opts:[{city:'告庄 · 江景房',price:380,why:'夜市就在楼下 · 推窗看大金塔',q:'西双版纳告庄酒店'},
        {city:'景洪市区',price:260,why:'省 ¥60/人 · 打车哪都近',q:'景洪市区酒店'}]},
 {city:'告庄 · 连住',price:380,why:'不挪窝 · 行李不动',q:'西双版纳告庄酒店'},
 {city:'告庄 · 连住',price:380,why:'不挪窝 · 明早去植物园',q:'西双版纳告庄酒店'},
 null];

/* ═══════════ 元阳梯田 3 天 · 灌水期限定（自驾）═══════════ */
const YY_NODES=[
 {n:'昆明',x:250,y:200,lx:-6,ly:-8,a:'start'},
 {n:'元阳·多依树',x:360,y:290,lx:13,ly:12,a:'middle'},
 {n:'老虎嘴·坝达',x:400,y:250,lx:13,ly:4,a:'end'}];
const YY3_DAYS=[
{tab:'D1',name:'昆明 → 元阳',sub:'长途转场 · 傍晚看坝达 · 中',start:450,hardEnd:1290,drive:'5 h',
 pre:{mode:'drive',conn:'昆明 → 元阳新街 · 350 km · 约 5 小时',min:300,km:350,cost:280,
   via:'沿途 · 建水可停一小时吃烧豆腐 · 后段盘山'},
 post:{mode:'drive',conn:'→ 多依树住处 · 20 km · 30 分',min:30,km:20,cost:0},
 stops:[
 {k:'yy-bada',name:'坝达梯田 · 日落',cng:'最美梯田',era:'哈尼族开垦一千三百年',dur:120,prio:0,cost:100,cat:'tix',indoor:false,
  vibe:'三千七百级梯田从山顶铺到谷底，日落时每一块水田都是一面镜子。',
  must:['必看','日落前 1 小时到 · 联票含四个观景台'],
  chips:[['','联票¥100 三日有效'],['down','11–4 月灌水期才有镜面']],q:'元阳坝达梯田'}]},
{tab:'D2',name:'多依树日出 · 老虎嘴日落',sub:'追光一整天 · 中',start:330,hardEnd:1290,drive:'1 h',
 pre:{mode:'drive',conn:'住处 → 多依树观景台 · 3 km · 10 分',min:10,km:3,cost:0,
   via:'摸黑出发 · 日出前 40 分到位占机位'},
 post:{mode:'drive',conn:'老虎嘴 → 住处 · 25 km · 40 分',min:40,km:25,cost:0},
 stops:[
 {k:'yy-duoyishu',name:'多依树 · 日出云海',cng:'最美梯田',era:'元阳最著名的日出机位',dur:150,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'天没亮就有人架三脚架，太阳一出来，云海从谷底涌上梯田。',
  must:['必看','日出前 40 分到位 · 联票已含'],
  chips:[['up','联票已含'],['down','冬季 7:20 前到 · 要穿厚']],q:'元阳多依树梯田'},
 {k:'yy-village',name:'哈尼族蘑菇房村寨',era:'土掌房与茅草顶',dur:100,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'蘑菇房的茅草顶一层压一层，村里的水渠还在按老规矩分水。',
  must:['必逛','阿者科村 · 箐口村'],
  chips:[['up','免票']],q:'元阳阿者科村'},
 {k:'yy-laohuzui',name:'老虎嘴 · 日落',cng:'最美梯田',era:'元阳最壮阔的一片',dur:120,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'梯田顺着山势拧成漩涡，夕阳一斜，整片田由银变金再变红。',
  must:['必看','日落前 1 小时到 · 联票已含'],
  chips:[['up','联票已含'],['down','边缘无护栏 · 注意脚下']],q:'元阳老虎嘴梯田'}]},
{tab:'D3',name:'建水古城 · 返程',sub:'回程顺路一站 · 中',start:480,hardEnd:1200,drive:'5 h',
 pre:{mode:'drive',conn:'元阳 → 建水 · 140 km · 约 2 小时 30 分',min:150,km:140,cost:120},
 post:{mode:'drive',conn:'建水 → 昆明 · 220 km · 约 3 小时',min:180,km:220,cost:180},
 stops:[
 {k:'yy-jianshui',name:'建水古城 · 朱家花园',cng:'最美古镇',era:'元代建城 · 文献名邦',dur:150,prio:0,cost:50,cat:'tix',indoor:false,
  vibe:'朱家花园是滇南最大的私家园林，隔壁的文庙规模仅次于曲阜。',
  must:['必看','朱家花园 · 文庙 · 烧豆腐配米线'],
  chips:[['','朱家花园¥50'],['','文庙¥60 自选']],q:'建水朱家花园'}]}];
const YY3_LODGES=[
 {opts:[{city:'多依树 · 观景客栈',price:340,why:'出门就是日出机位 · 不用摸黑赶路',q:'元阳多依树客栈'},
        {city:'元阳新街镇',price:220,why:'省 ¥60/人 · 吃饭方便',q:'元阳新街酒店'}]},
 {city:'多依树 · 连住',price:340,why:'不挪窝 · 明早还看日出',q:'元阳多依树客栈'},
 null];

/* ═══════════ 青岛 3 天 · 红瓦绿树与啤酒（地铁 + 公交）═══════════ */
const QD_NODES=[
 {n:'栈桥·中山路',x:300,y:250,lx:13,ly:4,a:'start'},
 {n:'八大关·第二海水浴场',x:380,y:290,lx:13,ly:12,a:'middle'},
 {n:'崂山',x:470,y:200,lx:13,ly:-8,a:'end'}];
const QD3_DAYS=[
{tab:'D1',name:'栈桥 · 八大关',sub:'海边步行 · 老别墅 · 轻',start:570,hardEnd:1290,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 栈桥 · 地铁 3 号线 12 分',min:12,cost:3},
 post:{mode:'transit',conn:'八大关 → 住处 · 公交 26 路 25 分',min:25,cost:2},
 stops:[
 {k:'qd-zhanqiao',name:'栈桥 · 回澜阁',cng:'最美海岸',era:'1892 年清军码头',dur:70,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'四百米栈桥伸进海里，尽头那座八角亭就是青岛啤酒商标上那个。',
  must:['必看','退潮时能下到礁石 · 海鸥 11 月到次年 4 月'],
  chips:[['up','免票'],['down','旺季人多 · 早上最静']],q:'青岛栈桥'},
 {mode:'transit',conn:'栈桥 → 八大关 · 公交 26 路 20 分',min:20,cost:2},
 {k:'qd-badaguan',name:'八大关 · 花石楼',cng:'最美古镇',era:'二十国建筑博览',dur:120,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'十条以关隘命名的路，每条种一种树，房子是德俄英法各家的老别墅。',
  must:['必逛','居庸关路的银杏 · 花石楼登顶看海'],
  chips:[['up','街区免票'],['','花石楼¥8.5 自选']],q:'青岛八大关'},
 {k:'qd-beach',name:'第二海水浴场 · 落日',era:'八大关脚下',dur:80,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'沙滩不大但正对海湾，太阳落进海里的时候整片沙都是橘色的。',
  must:['必看','日落前 40 分到 · 婚纱照聚集地'],
  chips:[['up','免票']],q:'青岛第二海水浴场'}]},
{tab:'D2',name:'崂山 · 仰口',sub:'山海一整天 · 中',start:480,hardEnd:1260,drive:'0 h',
 pre:{mode:'transit',conn:'市区 → 崂山仰口 · 公交 618 路 90 分',min:90,cost:8,
   via:'李村站发车 · 沿海公路景色好'},
 post:{mode:'transit',conn:'崂山 → 住处 · 公交 90 分',min:90,cost:8},
 stops:[
 {k:'qd-laoshan',name:'崂山 · 仰口游览区',cng:'最美名山',era:'海上第一名山',dur:240,prio:0,cost:130,cat:'tix',indoor:false,
  vibe:'山直接扎进海里，爬到觅天洞那段要侧身钻石缝，出来就是整片黄海。',
  must:['必爬','仰口索道上 · 觅天洞 · 太平宫'],
  chips:[['','门票¥130'],['','索道¥45 自选'],['down','雨雾天封山']],q:'崂山仰口游览区'}]},
{tab:'D3',name:'啤酒博物馆 · 中山路收官',sub:'一杯原浆 · 下午离开 · 轻',start:570,hardEnd:1170,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 登州路 · 地铁 3 号线 15 分',min:15,cost:3},
 post:{mode:'transit',conn:'中山路 → 青岛站/机场 · 地铁直达 约 45 分',min:45,cost:8},
 stops:[
 {k:'qd-beer',name:'青岛啤酒博物馆',era:'1903 年德国工艺',dur:110,prio:0,cost:60,cat:'tix',indoor:true,
  vibe:'走完老厂房那条线，出口给一杯刚下线的原浆，跟瓶装的完全两回事。',
  must:['必喝','门票含原浆一杯 · 隔壁登州路啤酒街'],
  chips:[['','门票¥60'],['up','含原浆一杯']],q:'青岛啤酒博物馆'},
 {mode:'transit',conn:'登州路 → 中山路 · 地铁 3 号线 12 分',min:12,cost:3},
 {k:'qd-zhongshan',name:'中山路 · 天主教堂',era:'德占时期主街',dur:80,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'双塔哥特教堂立在坡顶，台阶上永远坐着拍照的人。',
  must:['必看','教堂外观免费 · 劈柴院吃点小海鲜'],
  chips:[['up','街区免票'],['','入内¥10 自选']],q:'青岛天主教堂'},
 {k:'qd-lunch',name:'走之前 · 海鲜与啤酒',era:'袋装啤酒配蛤蜊',dur:80,prio:0,cost:100,cat:'food',indoor:true,
  vibe:'塑料袋装的散啤，配一盘辣炒蛤蜊，这才是青岛的日常。',
  must:['必点','辣炒蛤蜊 · 鲅鱼水饺 · 袋装原浆'],
  chips:[['','人均¥100']],q:'青岛 海鲜大排档'}]}];
const QD3_LODGES=[
 {opts:[{city:'栈桥 · 老城区',price:380,why:'走到栈桥 5 分 · 老建筑环绕',q:'青岛栈桥酒店'},
        {city:'台东 · 地铁口',price:260,why:'省 ¥60/人 · 夜市就在楼下',q:'青岛台东酒店'}]},
 {city:'栈桥 · 连住',price:380,why:'不挪窝 · 行李不动',q:'青岛栈桥酒店'},
 null];

/* ═══════════ 武汉 3 天 · 江城与东湖（地铁 + 轮渡）═══════════ */
const WH_NODES=[
 {n:'黄鹤楼·户部巷',x:310,y:240,lx:13,ly:4,a:'start'},
 {n:'东湖·武大',x:420,y:190,lx:13,ly:-8,a:'middle'},
 {n:'汉口江滩',x:230,y:190,lx:-6,ly:-8,a:'end'}];
const WH3_DAYS=[
{tab:'D1',name:'黄鹤楼 · 户部巷',sub:'登楼看两江 · 轻',start:570,hardEnd:1290,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 黄鹤楼 · 地铁 4 号线 15 分',min:15,cost:3},
 post:{mode:'walk',conn:'步行回住处 · 15 分',min:15,cost:0},
 stops:[
 {k:'wh-huanghelou',name:'黄鹤楼',cng:'最美古镇',era:'始建三国 · 现楼 1985 年重建',dur:100,prio:0,cost:70,cat:'tix',indoor:false,
  vibe:'登到五层，长江大桥横在脚下，江对面是汉口的楼群。',
  must:['必看','登顶看两江交汇 · 崔颢题诗处'],
  chips:[['','门票¥70'],['down','旺季需预约']],q:'武汉黄鹤楼'},
 {mode:'walk',conn:'黄鹤楼 → 户部巷 · 步行 12 分',min:12,cost:0},
 {k:'wh-hubuxiang',name:'户部巷 · 过早',era:'汉味小吃第一巷',dur:80,prio:0,cost:55,cat:'food',indoor:false,
  vibe:'武汉人管吃早饭叫过早，这条巷子从早上五点热闹到中午。',
  must:['必吃','热干面 · 三鲜豆皮 · 面窝'],
  chips:[['','人均¥55'],['down','中午后大半收摊']],q:'武汉户部巷'},
 {k:'wh-jiangtan',name:'汉口江滩 · 夜景',era:'万里长江第一滩',dur:90,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'江风一吹，对岸的灯光秀打在楼上，江上的轮渡慢慢划过去。',
  must:['必做','坐一次轮渡过江 ¥1.5 · 灯光秀 20:00'],
  chips:[['up','免票'],['','轮渡¥1.5']],q:'武汉汉口江滩'}]},
{tab:'D2',name:'东湖绿道 · 武汉大学',sub:'骑行环湖 · 中',start:540,hardEnd:1260,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 东湖绿道 · 地铁 8 号线 30 分',min:30,cost:4},
 post:{mode:'transit',conn:'武大 → 住处 · 地铁 2 号线 25 分',min:25,cost:3},
 stops:[
 {k:'wh-donghu',name:'东湖绿道 · 骑行',cng:'最美湖泊',era:'中国最大城中湖',dur:180,prio:0,cost:30,cat:'tix',indoor:false,
  vibe:'湖面比西湖大六倍，绿道贴着水修了一百多公里，骑到磨山那段全是树荫。',
  must:['必骑','租车¥30/天 · 湖中道那段最好'],
  chips:[['','单车¥30'],['up','绿道免费'],['down','正午晒']],q:'武汉东湖绿道'},
 {mode:'transit',conn:'东湖 → 武汉大学 · 公交 20 分',min:20,cost:2},
 {k:'wh-wuda',name:'武汉大学 · 老斋舍',era:'1893 年建校 · 民国建筑群',dur:100,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'樱花大道两侧的老斋舍是绿瓦飞檐，樱花季要预约，平时随便进。',
  must:['必看','老斋舍 · 万林艺术博物馆'],
  chips:[['up','平时免票'],['down','樱花季需预约']],q:'武汉大学'}]},
{tab:'D3',name:'湖北省博 · 昙华林收官',sub:'看编钟 · 下午离开 · 轻',start:540,hardEnd:1170,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 省博 · 地铁 8 号线 25 分',min:25,cost:4},
 post:{mode:'transit',conn:'昙华林 → 武汉站 · 地铁 4 号线 35 分',min:35,cost:5},
 stops:[
 {k:'wh-museum',name:'湖北省博物馆 · 曾侯乙编钟',cng:'最美古镇',era:'战国早期 · 六十五件青铜编钟',dur:140,prio:0,cost:0,cat:'free',indoor:true,
  vibe:'那套编钟两千四百年了还能奏出五个八度，展厅每天有编钟演奏。',
  must:['必看','曾侯乙编钟 · 越王勾践剑 · 需预约'],
  chips:[['up','免票'],['down','提前 3 天预约 · 周一闭馆'],['','编钟演奏¥30 自选']],q:'湖北省博物馆'},
 {mode:'transit',conn:'省博 → 昙华林 · 地铁 2 号线 25 分',min:25,cost:3},
 {k:'wh-tanhualin',name:'昙华林 · 老街区',era:'近代教会与民居混居',dur:80,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'半山腰的老街，教堂、民居和小店挤在一起，比户部巷安静得多。',
  must:['必逛','往山上走 · 咖啡馆多'],
  chips:[['up','免票']],q:'武汉昙华林'}]}];
const WH3_LODGES=[
 {opts:[{city:'武昌 · 黄鹤楼旁',price:360,why:'走到黄鹤楼户部巷都近',q:'武汉武昌酒店'},
        {city:'汉口 · 江滩边',price:300,why:'省 ¥60/人 · 夜里看江景',q:'武汉汉口酒店'}]},
 {city:'武昌 · 连住',price:360,why:'不挪窝 · 行李不动',q:'武汉武昌酒店'},
 null];


/* ═══ +1 天变体：用备选点撑起多出来的那天 ═══
   22 个族原本只有一种天数，用户想多待一天却加不了。
   多出来的那天不是硬凑，用的是原来「路上还有」里没排下的地方。 */
const CD4_D4=[{tab:'D4',name:'三圣乡 · 白鹿镇',sub:'城郊花海与法式小镇 · 轻',start:540,hardEnd:1200,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 三圣乡 · 地铁 + 公交 50 分',min:50,cost:5},
 post:{mode:'transit',conn:'白鹿镇 → 成都东站 · 城际 70 分',min:70,cost:15},
 stops:[
 {k:'cd-sansheng',name:'三圣乡 · 花乡农居',era:'成都人的周末后花园',dur:120,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'一整片花田里散着茶铺，成都人一杯茶能坐一下午。',
  must:['必做','找家院子喝茶 · 花期三到五月最好'],
  chips:[['up','免票'],['','茶位¥30']],q:'成都三圣乡'},
 {mode:'transit',conn:'三圣乡 → 白鹿镇 · 城际 60 分',min:60,cost:12},
 {k:'cd-bailu',name:'白鹿镇 · 中法风情',era:'1908 年法国传教士建',dur:120,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'山谷里一座法式小镇，上书院的残墙是地震留下的。',
  must:['必看','中法桥 · 上书院遗址'],
  chips:[['up','免票']],q:'彭州白鹿镇'}]}];

const SH4_D4=[{tab:'D4',name:'朱家角水乡',sub:'地铁直达的江南 · 下午回市区 · 轻',start:540,hardEnd:1200,drive:'0 h',
 pre:{mode:'transit',conn:'市区 → 朱家角 · 地铁 17 号线 60 分',min:60,cost:8},
 post:{mode:'transit',conn:'朱家角 → 虹桥/浦东 · 地铁 70 分',min:70,cost:10},
 stops:[
 {k:'sh-zhujiajiao',name:'朱家角 · 放生桥',cng:'最美古镇',era:'明隆庆五年建桥',dur:150,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'五孔石桥横在漕港河上，桥下摇橹船一条接一条过。',
  must:['必看','放生桥 · 课植园 · 摇橹船¥150/船'],
  chips:[['up','古镇免票'],['','课植园¥30 自选']],q:'上海朱家角'},
 {k:'sh-zjj-food',name:'水乡午饭',era:'扎肉与阿婆粽',dur:80,prio:0,cost:60,cat:'food',indoor:true,
  vibe:'一块扎肉配一只阿婆粽，河边坐着吃完再走。',
  must:['必点','扎肉 · 阿婆粽 · 熏青豆'],
  chips:[['','人均¥60']],q:'朱家角 本地菜'}]}];

const HZ4_D4=[{tab:'D4',name:'西溪湿地',sub:'芦苇荡与摇橹船 · 轻',start:540,hardEnd:1200,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 西溪 · 地铁 5 号线 35 分',min:35,cost:4},
 post:{mode:'transit',conn:'西溪 → 杭州东站 · 地铁 45 分',min:45,cost:6},
 stops:[
 {k:'hz-xixi',name:'西溪湿地 · 摇橹船',cng:'最美湿地',era:'中国首个国家湿地公园',dur:180,prio:0,cost:80,cat:'tix',indoor:false,
  vibe:'船在芦苇丛里穿，两岸只有水声和鸟叫，跟西湖完全两个节奏。',
  must:['必做','摇橹船必坐 · 深潭口 · 秋天芦花最好'],
  chips:[['','门票¥80'],['','摇橹船¥100/船'],['down','园区大 · 走东区就够']],q:'杭州西溪湿地'}]}];

const SZ4_D4=[{tab:'D4',name:'同里古镇',sub:'退思园与三桥 · 轻',start:540,hardEnd:1200,drive:'0 h',
 pre:{mode:'transit',conn:'苏州 → 同里 · 公交 快线 60 分',min:60,cost:8},
 post:{mode:'transit',conn:'同里 → 苏州站 · 公交 70 分',min:70,cost:8},
 stops:[
 {k:'sz-tongli',name:'同里 · 退思园',cng:'最美古镇',era:'1885 年建 · 世界遗产',dur:160,prio:0,cost:100,cat:'tix',indoor:false,
  vibe:'贴水而建的园子，走廊几乎踩着水面，比拙政园小但更私密。',
  must:['必看','退思园 · 三桥（太平·吉利·长庆）'],
  chips:[['','联票¥100']],q:'同里退思园'},
 {k:'sz-tongli-food',name:'水乡午饭',era:'状元蹄与芡实糕',dur:80,prio:0,cost:55,cat:'food',indoor:true,
  vibe:'一只状元蹄配一碗银鱼羹，河边的桌子最好。',
  must:['必点','状元蹄 · 芡实糕 · 银鱼羹'],
  chips:[['','人均¥55']],q:'同里 本地菜'}]}];

/* ═══════════ 苏州 3 天 · 园林与平江路（地铁 + 步行）═══════════ */
const SZ_NODES=[
 {n:'平江路·观前',x:320,y:220,lx:13,ly:4,a:'start'},
 {n:'拙政园·狮子林',x:330,y:150,lx:13,ly:-8,a:'middle'},
 {n:'山塘街·虎丘',x:200,y:180,lx:-6,ly:-8,a:'end'}];
const SZ3_DAYS=[
{tab:'D1',name:'拙政园 · 平江路',sub:'园林一上午 · 老街一下午 · 轻',start:540,hardEnd:1290,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 拙政园 · 地铁 4 号线 15 分',min:15,cost:3},
 post:{mode:'walk',conn:'步行回住处 · 12 分',min:12,cost:0},
 stops:[
 {k:'sz-zhuozheng',name:'拙政园',cng:'最美古镇',era:'明正德年间 · 四大名园之首',dur:120,prio:0,cost:70,cat:'tix',indoor:false,
  vibe:'水面占了三分之一，走几步换一个框景，是园林的教科书。',
  must:['必看','远香堂 · 小飞虹廊桥 · 早上 8:30 开园就进'],
  chips:[['','旺季¥70 淡季¥50'],['down','需实名预约 · 十点后人挤人']],q:'苏州拙政园'},
 {mode:'walk',conn:'拙政园 → 狮子林 · 步行 8 分',min:8,cost:0},
 {k:'sz-shizilin',name:'狮子林 · 假山迷宫',era:'元至正二年',dur:70,prio:1,cost:40,cat:'tix',indoor:false,
  vibe:'一堆太湖石堆成的迷宫，钻进去能绕半天出不来。',
  must:['必玩','假山群钻一圈 · 燕誉堂'],
  chips:[['','门票¥40'],['','与拙政园相邻']],q:'苏州狮子林'},
 {mode:'walk',conn:'狮子林 → 平江路 · 步行 10 分',min:10,cost:0},
 {k:'sz-pingjiang',name:'平江路 · 河街并行',cng:'最美古镇',era:'宋代平江图上的老街',dur:100,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'一条水一条街并排走了八百年，摇橹船从桥洞里钻出来。',
  must:['必逛','往小巷钻 · 猫的天空之城 · 评弹馆听一段'],
  chips:[['up','免票'],['','摇橹船¥120/船']],q:'苏州平江路'}]},
{tab:'D2',name:'虎丘 · 山塘街',sub:'斜塔与七里山塘 · 轻',start:540,hardEnd:1290,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 虎丘 · 公交 游1路 30 分',min:30,cost:2},
 post:{mode:'transit',conn:'山塘街 → 住处 · 地铁 2 号线 20 分',min:20,cost:3},
 stops:[
 {k:'sz-huqiu',name:'虎丘 · 云岩寺塔',cng:'最美古镇',era:'东晋 · 塔建于五代',dur:120,prio:0,cost:60,cat:'tix',indoor:false,
  vibe:'中国的比萨斜塔，倾斜了一千年还立着，苏东坡说到苏州不游虎丘乃憾事。',
  must:['必看','云岩寺塔 · 剑池 · 千人石'],
  chips:[['','旺季¥60 淡季¥45']],q:'苏州虎丘'},
 {mode:'walk',conn:'虎丘 → 山塘街 · 步行 20 分',min:20,cost:0},
 {k:'sz-shantang',name:'山塘街 · 七里山塘',era:'白居易任苏州刺史时开凿',dur:100,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'从虎丘一直通到阊门，晚上灯笼亮起来，船在河里慢慢划。',
  must:['必逛','往西段走人少 · 夜里坐一次船'],
  chips:[['up','街区免票'],['','游船¥55/人']],q:'苏州山塘街'},
 {k:'sz-dinner',name:'苏帮菜 · 晚饭',era:'甜口江南',dur:80,prio:0,cost:110,cat:'food',indoor:true,
  opts:[{name:'老字号松鹤楼',cost:150,dur:90,vibe:'松鼠鳜鱼摆上来还在滋滋响，甜口是正宗苏帮味。'},
        {name:'巷子里的面馆',cost:45,dur:50,vibe:'一碗焖肉面配一碟爆鱼，苏州人的日常。'}],
  id:'sz-food',
  must:['必点','松鼠鳜鱼 · 响油鳝糊 · 头汤面'],
  chips:[['','人均¥45-150']],q:'苏州 苏帮菜'}]},
{tab:'D3',name:'苏州博物馆 · 观前街收官',sub:'看展与老街 · 下午离开 · 轻',start:540,hardEnd:1170,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 苏博 · 地铁 4 号线 15 分',min:15,cost:3},
 post:{mode:'transit',conn:'观前街 → 苏州站 · 地铁 4 号线 12 分',min:12,cost:3},
 stops:[
 {k:'sz-museum',name:'苏州博物馆 · 贝聿铭设计',cng:'最美古镇',era:'2006 年建成',dur:120,prio:0,cost:0,cat:'free',indoor:true,
  vibe:'白墙灰瓦的现代版园林，主庭院那面片石假山是照着米芾的画堆的。',
  must:['必看','片石假山 · 秘色瓷莲花碗 · 提前 3 天预约'],
  chips:[['up','免票'],['down','需提前 3 天官网预约 · 周一闭馆']],q:'苏州博物馆'},
 {mode:'walk',conn:'苏博 → 观前街 · 步行 15 分',min:15,cost:0},
 {k:'sz-guanqian',name:'观前街 · 玄妙观',era:'苏州最老的商业街',dur:70,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'玄妙观的三清殿是南宋的，殿前就是热闹的小吃摊。',
  must:['必吃','采芝斋买糖 · 黄天源糕团'],
  chips:[['up','街区免票']],q:'苏州观前街'}]}];
const SZ3_LODGES=[
 {opts:[{city:'平江路 · 河边客栈',price:400,why:'推窗见河 · 走到拙政园 10 分',q:'苏州平江路客栈'},
        {city:'观前街 · 地铁口',price:280,why:'省 ¥60/人 · 两站到各景点',q:'苏州观前街酒店'}]},
 {city:'平江路 · 连住',price:400,why:'不挪窝 · 行李不动',q:'苏州平江路客栈'},
 null];

/* ═══════════ 南京 3 天 · 六朝与民国（地铁 + 步行）═══════════ */
const NJ_NODES=[
 {n:'新街口·夫子庙',x:320,y:240,lx:13,ly:4,a:'start'},
 {n:'钟山·中山陵',x:430,y:180,lx:13,ly:-8,a:'middle'},
 {n:'颐和路·鼓楼',x:250,y:170,lx:-6,ly:-8,a:'end'}];
const NJ3_DAYS=[
{tab:'D1',name:'中山陵 · 明孝陵',sub:'钟山一整天 · 台阶多 · 中',start:510,hardEnd:1260,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 中山陵 · 地铁 2 号线 + 观光车 40 分',min:40,cost:8},
 post:{mode:'transit',conn:'钟山 → 住处 · 地铁 2 号线 35 分',min:35,cost:4},
 stops:[
 {k:'nj-zhongshan',name:'中山陵',cng:'最美名山',era:'1929 年落成',dur:120,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'392 级台阶一路往上，走到顶回头看，整个钟山铺在脚下。',
  must:['必做','需提前预约 · 台阶陡量力而行'],
  chips:[['up','免票需预约'],['down','周一维护闭馆']],q:'南京中山陵'},
 {mode:'transit',conn:'中山陵 → 明孝陵 · 景区观光车 15 分',min:15,cost:10},
 {k:'nj-xiaoling',name:'明孝陵 · 石象路',cng:'最美古镇',era:'明洪武十四年',dur:120,prio:0,cost:70,cat:'tix',indoor:false,
  vibe:'石象路那段神道两侧全是六百年的石兽，秋天满地梧桐叶。',
  must:['必看','石象路神道 · 十一月落叶最美'],
  chips:[['','门票¥70'],['','秋天最佳']],q:'南京明孝陵'}]},
{tab:'D2',name:'夫子庙 · 老门东',sub:'秦淮河与老城南 · 轻',start:570,hardEnd:1320,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 夫子庙 · 地铁 3 号线 15 分',min:15,cost:3},
 post:{mode:'transit',conn:'老门东 → 住处 · 地铁 3 号线 20 分',min:20,cost:3},
 stops:[
 {k:'nj-fuzimiao',name:'夫子庙 · 秦淮河',cng:'最美古镇',era:'东晋建康学宫',dur:100,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'画舫在秦淮河上划过，两岸的灯把水面照得发红。',
  must:['必看','夜里灯亮最好 · 乌衣巷 · 江南贡院'],
  chips:[['up','街区免票'],['','游船¥80/人'],['down','节假日限流']],q:'南京夫子庙'},
 {mode:'walk',conn:'夫子庙 → 老门东 · 步行 12 分',min:12,cost:0},
 {k:'nj-laomendong',name:'老门东 · 城墙根',era:'明城墙内侧老城南',dur:90,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'比夫子庙安静，青砖巷子里有先锋书店和评话馆。',
  must:['必逛','先锋书店 · 城墙上走一段'],
  chips:[['up','免票'],['','登城墙¥50 自选']],q:'南京老门东'},
 {k:'nj-dinner',name:'盐水鸭 · 晚饭',era:'南京的规定动作',dur:80,prio:0,cost:90,cat:'food',indoor:true,
  vibe:'皮白肉嫩，配一碗鸭血粉丝汤，这一顿才算到过南京。',
  must:['必点','盐水鸭 · 鸭血粉丝汤 · 皮肚面'],
  chips:[['','人均¥90']],q:'南京 盐水鸭'}]},
{tab:'D3',name:'颐和路 · 总统府收官',sub:'民国建筑群 · 下午离开 · 轻',start:540,hardEnd:1170,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 颐和路 · 地铁 4 号线 18 分',min:18,cost:3},
 post:{mode:'transit',conn:'总统府 → 南京南站 · 地铁 3 号线 30 分',min:30,cost:4},
 stops:[
 {k:'nj-yihe',name:'颐和路 · 民国公馆区',era:'1930 年代使馆区',dur:80,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'梧桐树盖住整条路，两边全是爬满藤蔓的民国小楼。',
  must:['必走','颐和路到宁海路那段 · 大多不对外开放'],
  chips:[['up','街区免票'],['','秋天梧桐最美']],q:'南京颐和路'},
 {mode:'transit',conn:'颐和路 → 总统府 · 地铁 2 号线 15 分',min:15,cost:3},
 {k:'nj-presidential',name:'总统府',cng:'最美古镇',era:'明汉王府 · 民国总统府',dur:110,prio:0,cost:40,cat:'tix',indoor:false,
  vibe:'一座院子装了六百年：明代王府、太平天国王宫、民国总统府叠在一起。',
  must:['必看','大堂 · 煦园水榭 · 孙中山办公室'],
  chips:[['','门票¥40'],['down','周一闭馆']],q:'南京总统府'}]}];
const NJ3_LODGES=[
 {opts:[{city:'新街口 · 地铁枢纽',price:420,why:'四线换乘 · 去哪都两站',q:'南京新街口酒店'},
        {city:'夫子庙 · 老城南',price:300,why:'省 ¥60/人 · 夜里逛秦淮河',q:'南京夫子庙酒店'}]},
 {city:'新街口 · 连住',price:420,why:'不挪窝 · 行李不动',q:'南京新街口酒店'},
 null];

/* ═══════════ 杭州 3 天 · 西湖与龙井（地铁 + 环湖公交）═══════════ */
const HZ_NODES=[
 {n:'西湖 · 湖滨',x:320,y:220,lx:13,ly:4,a:'start'},
 {n:'灵隐 · 龙井',x:190,y:170,lx:-2,ly:-10,a:'middle'},
 {n:'河坊街',x:350,y:310,lx:13,ly:12,a:'end'}];
const HZ3_DAYS=[
{tab:'D1',name:'西湖环湖 · 雷峰塔',sub:'断桥到苏堤 · 走一圈 · 中',start:540,hardEnd:1290,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 断桥 · 地铁 1 号线 15 分',min:15,cost:3},
 post:{mode:'walk',conn:'步行回湖滨住处 · 15 分',min:15,cost:0},
 stops:[
 {k:'hz-baidi',name:'断桥 · 白堤',cng:'最美湖泊',era:'白居易筑堤',dur:90,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'一条堤把湖分成里外两片，早上八点前几乎只有本地人在遛弯。',
  must:['必走','断桥 → 平湖秋月 → 孤山，全程 1.5 km'],
  chips:[['up','免票'],['down','节假日人挤人 · 早去']],q:'杭州断桥'},
 {mode:'walk',conn:'孤山 → 苏堤 · 步行 20 分',min:20,cost:0},
 {k:'hz-sudi',name:'苏堤春晓',era:'苏轼疏浚西湖所筑',dur:100,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'两侧全是水，六座拱桥一座接一座，走完腿酸但值。',
  must:['必走','全长 2.8 km · 可租共享单车'],
  chips:[['up','免票'],['','单车¥2/30分']],q:'杭州苏堤'},
 {k:'hz-leifeng',name:'雷峰塔 · 夕照',era:'吴越国王钱俶建',dur:80,prio:1,cost:40,cat:'tix',indoor:false,
  vibe:'登顶看整片西湖铺开，日落时湖面全是金的。',
  must:['必看','日落前 40 分上塔 · 塔下有旧塔遗址'],
  chips:[['','门票¥40'],['','日落最佳']],q:'杭州雷峰塔'}]},
{tab:'D2',name:'灵隐寺 · 龙井村',sub:'山里一整天 · 茶园 · 中',start:510,hardEnd:1260,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 灵隐 · 公交 7 路 35 分',min:35,cost:3},
 post:{mode:'transit',conn:'龙井村 → 住处 · 公交 27 路 40 分',min:40,cost:3},
 stops:[
 {k:'hz-lingyin',name:'灵隐寺 · 飞来峰',cng:'最美古镇',era:'东晋咸和元年',dur:150,prio:0,cost:75,cat:'tix',indoor:false,
  vibe:'飞来峰的宋代石窟就贴在山壁上，走进寺里香火气盖过人声。',
  must:['必看','飞来峰造像 · 大雄宝殿 · 需买两道票'],
  chips:[['','景区¥45+寺院¥30'],['down','旺季提前预约']],q:'杭州灵隐寺'},
 {mode:'transit',conn:'灵隐 → 龙井村 · 公交 15 分',min:15,cost:2},
 {k:'hz-longjing',name:'龙井村 · 茶园',era:'狮峰龙井核心产区',dur:120,prio:0,cost:60,cat:'food',indoor:false,
  vibe:'茶山一层层铺到山顶，找家农户坐下来，一杯明前泡三回。',
  must:['必做','茶农家喝一杯 · 十八棵御茶树'],
  chips:[['','茶位¥60'],['up','茶园免票']],q:'杭州龙井村'}]},
{tab:'D3',name:'河坊街 · 运河收官',sub:'老街与漕运 · 下午离开 · 轻',start:540,hardEnd:1170,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 河坊街 · 地铁 7 号线 12 分',min:12,cost:3},
 post:{mode:'transit',conn:'拱宸桥 → 东站/萧山机场 · 地铁直达 约 50 分',min:50,cost:8},
 stops:[
 {k:'hz-hefang',name:'河坊街 · 南宋御街',era:'南宋临安御道',dur:90,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'青石板路两边全是老铺子，胡庆余堂的药香飘半条街。',
  must:['必逛','胡庆余堂 · 定胜糕 · 王星记扇子'],
  chips:[['up','免票'],['','买特产方便']],q:'杭州河坊街'},
 {mode:'transit',conn:'河坊街 → 拱宸桥 · 地铁 1 号线转 5 号线 30 分',min:30,cost:4},
 {k:'hz-canal',name:'京杭大运河 · 拱宸桥',cng:'最美古镇',era:'明崇祯四年重建',dur:80,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'三孔石拱桥横在运河上，桥边的桥西直街还住着人。',
  must:['必看','拱宸桥 · 运河博物馆免费'],
  chips:[['up','免票']],q:'杭州拱宸桥'},
 {k:'hz-lunch',name:'走之前 · 片儿川或东坡肉',era:'杭帮菜',dur:70,prio:0,cost:60,cat:'food',indoor:true,
  opts:[{name:'老字号杭帮菜',cost:90,dur:80,vibe:'东坡肉炖到筷子一夹就断，西湖醋鱼看手艺。'},
        {name:'面馆片儿川',cost:35,dur:50,vibe:'雪菜笋片配腰花，一碗就饱，赶车前刚好。'}],
  id:'hz-food',
  must:['必点','东坡肉 · 片儿川 · 龙井虾仁'],
  chips:[['','人均¥35-90']],q:'杭州 杭帮菜'}]}];
const HZ3_LODGES=[
 {opts:[{city:'湖滨 · 西湖边',price:480,why:'走到断桥 10 分 · 地铁枢纽',q:'杭州湖滨酒店'},
        {city:'武林广场 · 地铁口',price:340,why:'省 ¥70/人 · 两站到西湖',q:'杭州武林广场酒店'}]},
 {city:'湖滨 · 连住',price:480,why:'不挪窝 · 行李不动',q:'杭州湖滨酒店'},
 null];

/* ═══════════ 重庆 3 天 · 山城立体（轻轨 + 索道 + 步行）═══════════ */
const CQ_NODES=[
 {n:'解放碑·洪崖洞',x:330,y:230,lx:13,ly:4,a:'start'},
 {n:'磁器口',x:190,y:170,lx:-2,ly:-10,a:'middle'},
 {n:'李子坝',x:270,y:300,lx:-2,ly:14,a:'end'}];
const CQ3_DAYS=[
{tab:'D1',name:'解放碑 · 洪崖洞夜景',sub:'市中心 · 过江索道 · 轻',start:600,hardEnd:1320,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 解放碑 · 轻轨 2 号线 15 分',min:15,cost:4},
 post:{mode:'walk',conn:'步行回住处 · 12 分',min:12,cost:0},
 stops:[
 {k:'cq-jiefang',name:'解放碑 · 八一路',era:'1947 年抗战胜利纪功碑',dur:70,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'一座碑被玻璃楼围在中间，好吃街的酸辣粉香气飘出两条街。',
  must:['必吃','八一路好吃街 · 山城小汤圆'],
  chips:[['up','免票'],['','小吃人均¥40']],q:'重庆解放碑'},
 {k:'cq-suodao',name:'长江索道',era:'1987 年通车 · 空中公交',dur:50,prio:0,cost:30,cat:'tix',indoor:false,
  vibe:'缆车贴着江面过去，两岸的楼像从水里长出来。',
  must:['必坐','单程¥30 · 建议下午过江傍晚回'],
  chips:[['','单程¥30'],['down','旺季排队 40 分']],q:'重庆长江索道'},
 {k:'cq-hongya',name:'洪崖洞 · 夜景',cng:'最美古镇',era:'吊脚楼群',dur:90,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'十一层吊脚楼从江边一路堆到马路上，灯全亮的时候像动画里那座城。',
  must:['必看','19:00 后灯全开 · 千厮门大桥上拍全景'],
  chips:[['up','免票'],['down','周末人流管制']],q:'重庆洪崖洞'},
 {k:'cq-hotpot',name:'火锅 · 晚饭',era:'牛油九宫格',dur:100,prio:0,cost:130,cat:'food',indoor:true,
  opts:[{name:'老牌牛油火锅',cost:160,dur:110,vibe:'九宫格中间烫毛肚，边格炖脑花，辣得过瘾。'},
        {name:'本地连锁 · 不排队',cost:100,dur:80,vibe:'味道稳定不用等位，微辣也能调。'}],
  id:'cq-hg',
  must:['必点','毛肚 · 鸭肠 · 黄喉 · 冰粉解辣'],
  chips:[['','人均¥100-160'],['down','热门店排队 1 小时']],q:'重庆火锅'}]},
{tab:'D2',name:'磁器口 · 鹅岭二厂',sub:'古镇加旧厂房 · 轻',start:540,hardEnd:1290,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 磁器口 · 轻轨 1 号线 30 分',min:30,cost:5},
 post:{mode:'transit',conn:'鹅岭二厂 → 住处 · 轻轨 2 号线 25 分',min:25,cost:4},
 stops:[
 {k:'cq-ciqikou',name:'磁器口古镇',cng:'最美古镇',era:'明建文年间码头',dur:120,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'石板路从山门一直斜到嘉陵江边，陈麻花的队伍能排出半条街。',
  must:['必吃','陈麻花 · 毛血旺 · 往江边走人少'],
  chips:[['up','免票'],['down','主街人多 · 往支巷钻']],q:'重庆磁器口'},
 {mode:'transit',conn:'磁器口 → 鹅岭二厂 · 轻轨 25 分',min:25,cost:4},
 {k:'cq-erchang',name:'鹅岭二厂 · 天台',era:'民国印钞厂改造',dur:90,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'旧厂房里塞满小店，天台正对渝中半岛，日落时整片楼群染成橘色。',
  must:['必看','天台看渝中半岛 · 日落前到'],
  chips:[['up','免票'],['','天台咖啡¥40']],q:'重庆鹅岭二厂'}]},
{tab:'D3',name:'李子坝 · 山城步道收官',sub:'轻轨穿楼 · 下午离开 · 轻',start:570,hardEnd:1170,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 李子坝 · 轻轨 2 号线 12 分',min:12,cost:3},
 post:{mode:'transit',conn:'两路口 → 江北机场/重庆北站 · 轻轨直达 约 45 分',min:45,cost:8},
 stops:[
 {k:'cq-liziba',name:'李子坝 · 轻轨穿楼',era:'2005 年建成',dur:60,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'列车从八楼直接钻进居民楼，站在观景台上等两分钟就来一趟。',
  must:['必拍','观景台在马路对面 · 高峰期每 3 分一趟'],
  chips:[['up','免票'],['','观景台免费']],q:'重庆李子坝轻轨站'},
 {mode:'walk',conn:'李子坝 → 山城步道 · 步行 15 分',min:15,cost:0},
 {k:'cq-budao',name:'山城第三步道',era:'老重庆的垂直生活',dur:90,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'一条挂在崖壁上的老街，防空洞、吊脚楼和晾衣绳全在一条道上。',
  must:['必走','从领事巷进 · 看得见长江'],
  chips:[['up','免票'],['down','台阶多 · 穿好鞋']],q:'重庆山城第三步道'}]}];
const CQ3_LODGES=[
 {opts:[{city:'解放碑 · 江景房',price:460,why:'走到洪崖洞 10 分 · 轻轨枢纽',q:'重庆解放碑酒店'},
        {city:'观音桥 · 地铁口',price:320,why:'省 ¥70/人 · 三站到解放碑',q:'重庆观音桥酒店'}]},
 {city:'解放碑 · 连住',price:460,why:'不挪窝 · 行李不动',q:'重庆解放碑酒店'},
 null];

/* ═══════════════════════════════════════════════════
   上海 3 天 · 外滩到梧桐区（全程地铁 · 城市漫步第四条）
   ═══════════════════════════════════════════════════ */
const SH_NODES=[
 {n:'外滩·南京路',x:340,y:210,lx:13,ly:4,a:'start'},
 {n:'武康路',x:200,y:300,lx:-2,ly:16,a:'middle'},
 {n:'陆家嘴',x:470,y:190,lx:13,ly:-8,a:'end'}];

const SH3_DAYS=[
{tab:'D1',name:'外滩 · 南京路 · 豫园',sub:'市中心步行 · 看夜景 · 轻',start:570,hardEnd:1320,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 南京东路 · 地铁 2 号线 12 分',min:12,cost:3},
 post:{mode:'walk',conn:'步行回住处 · 10 分',min:10,cost:0},
 stops:[
 {k:'sh-yuyuan',name:'豫园 · 城隍庙',cng:'最美古镇',era:'明嘉靖三十八年',dur:100,prio:0,cost:40,cat:'tix',indoor:false,
  vibe:'四百年的江南园林嵌在高楼中间，出园就是城隍庙的小笼和梨膏糖。',
  must:['必看','玉玲珑太湖石 · 九曲桥喂鱼'],
  chips:[['','门票¥40'],['down','周末人多 · 早上 9 点前最静']],q:'上海豫园'},
 {mode:'walk',conn:'豫园 → 南京东路 · 步行 15 分',min:15,cost:0},
 {k:'sh-nanjing',name:'南京路步行街',era:'1851 年起的商业街',dur:70,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'霓虹一路铺到外滩，老字号招牌和新店挤在一条街上。',
  must:['必逛','沈大成青团 · 第一食品商店带特产'],
  chips:[['up','免票'],['','有观光车¥5']],q:'上海南京路步行街'},
 {k:'sh-bund',name:'外滩 · 万国建筑群',cng:'最美古镇',era:'1844 年开埠',dur:90,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'一边是百年石砌外墙，一边是江对岸的玻璃塔尖，一条江隔开一百年。',
  must:['必看','18:30 后灯全开 · 走到外白渡桥回望'],
  chips:[['up','免票'],['','夜景最佳']],q:'上海外滩'},
 {k:'sh-dinner',name:'本帮菜 · 晚饭',era:'浓油赤酱',dur:80,prio:0,cost:130,cat:'food',indoor:true,
  opts:[{name:'老字号本帮馆',cost:160,dur:90,vibe:'红烧肉油亮，草头圈子是硬菜，价格也硬。'},
        {name:'弄堂小馆 · 不排队',cost:100,dur:70,vibe:'一样的浓油赤酱，人均便宜三分之一。'}],
  id:'sh-food',
  must:['必点','红烧肉 · 油爆虾 · 八宝辣酱'],
  chips:[['','人均¥100-160'],['down','老字号需排队']],q:'上海 本帮菜'}]},

{tab:'D2',name:'武康路 · 安福路 · 田子坊',sub:'梧桐区一整天 · 咖啡与老洋房 · 轻',start:600,hardEnd:1290,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 武康路 · 地铁 10/11 号线 25 分',min:25,cost:4},
 post:{mode:'transit',conn:'田子坊 → 住处 · 地铁 9 号线 25 分',min:25,cost:4},
 stops:[
 {k:'sh-wukang',name:'武康路 · 武康大楼',era:'1924 年诺曼底公寓',dur:110,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'船头一样的楼尖立在五岔路口，梧桐荫下全是举着手机找角度的人。',
  must:['必拍','武康大楼斜对角人行道 · 巴金故居可进'],
  chips:[['up','街区免票'],['down','周末路口人挤人']],q:'上海武康大楼'},
 {mode:'walk',conn:'武康路 → 安福路 · 步行 12 分',min:12,cost:0},
 {k:'sh-anfu',name:'安福路 · 咖啡与小店',era:'上海最会喝咖啡的街',dur:90,prio:1,cost:60,cat:'food',indoor:true,
  vibe:'一条街十几家咖啡馆，话剧艺术中心门口坐满了人，下午最好泡在这儿。',
  must:['必做','找一家坐下来 · 街角面包店带可颂'],
  chips:[['','人均¥60'],['up','逛街免费']],q:'上海安福路'},
 {mode:'transit',conn:'安福路 → 田子坊 · 地铁 9 号线 20 分',min:20,cost:3},
 {k:'sh-tianzifang',name:'田子坊 · 石库门弄堂',era:'1930 年代里弄工厂',dur:80,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'窄得只容两人并行的弄堂里，头顶还晾着居民的衣服，两边全是小店。',
  must:['必逛','往深处走 · 天台咖啡看弄堂顶'],
  chips:[['up','免票'],['down','巷子窄 · 避开饭点']],q:'上海田子坊'}]},

{tab:'D3',name:'上海博物馆 · 陆家嘴收官',sub:'看展加天际线 · 下午离开 · 轻',start:540,hardEnd:1200,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 人民广场 · 地铁 1/2/8 号线 15 分',min:15,cost:3},
 post:{mode:'transit',conn:'陆家嘴 → 虹桥/浦东机场 · 地铁直达 约 55 分',min:55,cost:8},
 stops:[
 {k:'sh-museum',name:'上海博物馆',cng:'最美古镇',era:'青铜器与书画冠绝江南',dur:140,prio:0,cost:0,cat:'free',indoor:true,
  vibe:'四层看下来，从商周青铜走到明清家具，空调还足。',
  must:['必看','青铜馆 · 书法馆 · 提前官微预约'],
  chips:[['up','免票'],['down','提前 1 天预约 · 周一闭馆']],q:'上海博物馆'},
 {mode:'transit',conn:'人民广场 → 陆家嘴 · 地铁 2 号线 12 分',min:12,cost:3},
 {k:'sh-lujiazui',name:'陆家嘴 · 天际线',era:'三件套：金茂 · 环球 · 上海中心',dur:90,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'站在环形天桥中间转一圈，三座塔把天空切成几块。',
  must:['必拍','陆家嘴环形天桥 · 上海中心登顶¥180 自选'],
  chips:[['up','天桥免票'],['','登顶¥180 自选']],q:'上海陆家嘴环形天桥'},
 {k:'sh-lunch',name:'走之前 · 生煎或小笼',era:'碳水收尾',dur:60,prio:0,cost:45,cat:'food',indoor:true,
  vibe:'底脆汁多的生煎配一碗咖喱牛肉汤，是上海人的日常开场。',
  must:['必点','生煎四只起 · 小笼配姜丝'],
  chips:[['','人均¥45']],q:'上海 生煎'}]}];

const SH3_LODGES=[
 {opts:[{city:'人民广场 · 地铁枢纽',price:520,why:'三线换乘 · 走到外滩 15 分',q:'上海人民广场酒店'},
        {city:'徐家汇 · 地铁口',price:380,why:'省 ¥70/人 · 去武康路两站',q:'上海徐家汇酒店'}]},
 {city:'人民广场 · 连住',price:520,why:'不挪窝 · 行李不动',q:'上海人民广场酒店'},
 null];

/* ═══════════════════════════════════════════════════
   北京 4 天 · 中轴线与长城（全程地铁 + 一趟公交）
   ═══════════════════════════════════════════════════ */
const BJ_NODES=[
 {n:'前门·天安门',x:320,y:260,lx:13,ly:4,a:'start'},
 {n:'景山·北海',x:310,y:190,lx:-2,ly:-10,a:'middle'},
 {n:'慕田峪长城',x:400,y:80,lx:13,ly:-8,a:'middle'},
 {n:'颐和园',x:190,y:180,lx:-6,ly:-10,a:'end'}];

const BJ4_DAYS=[
{tab:'D1',name:'故宫中轴线 · 景山',sub:'一天走完六百年 · 中',start:480,hardEnd:1290,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 天安门东 · 地铁 1 号线 15 分',min:15,cost:4},
 post:{mode:'transit',conn:'景山 → 住处 · 地铁 8 号线 25 分',min:25,cost:4},
 stops:[
 {k:'bj-tiananmen',name:'天安门广场 · 正阳门',era:'明清中轴线起点',dur:60,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'从正阳门往北望过去，一条中轴线笔直插进城市中心，六百年没歪过。',
  must:['必做','需提前预约进广场 · 带身份证'],
  chips:[['up','免票'],['down','须提前一天预约']],q:'天安门广场'},
 {k:'bj-gugong',name:'故宫 · 中轴线',cng:'最美古镇',era:'明永乐十八年',dur:210,prio:0,cost:60,cat:'tix',indoor:false,
  vibe:'三大殿一路往北，越走越安静，走到御花园时腿已经不是自己的了。',
  must:['必看','午门进神武门出 · 珍宝馆钟表馆各 ¥10 值得加'],
  chips:[['','门票¥60'],['down','官网提前 7 天放票 · 秒光'],['','珍宝馆¥10 自选']],q:'故宫博物院'},
 {mode:'walk',conn:'神武门 → 景山公园 · 步行 5 分',min:5,cost:0},
 {k:'bj-jingshan',name:'景山 · 万春亭俯瞰',era:'紫禁城最佳机位',dur:70,prio:0,cost:2,cat:'tix',indoor:false,
  vibe:'爬十分钟上万春亭，整座紫禁城的金顶铺在脚下，日落时全是金的。',
  must:['必看','日落前 40 分上山占位'],
  chips:[['','门票¥2'],['up','故宫全景唯一机位']],q:'景山公园'}]},

{tab:'D2',name:'慕田峪长城',sub:'北郊往返 · 缆车上滑道下 · 中',start:420,hardEnd:1290,drive:'0 h',
 pre:{mode:'transit',conn:'市区 → 慕田峪 · 916 快 + 接驳 约 2 小时',min:120,cost:26,
   via:'东直门枢纽发车 · 或坐旅游专线直达'},
 post:{mode:'transit',conn:'慕田峪 → 市区 · 约 2 小时',min:120,cost:26},
 stops:[
 {k:'bj-greatwall',name:'慕田峪长城',cng:'最美名山',era:'明代边墙 · 敌楼 22 座',dur:210,prio:0,cost:100,cat:'tix',indoor:false,
  vibe:'比八达岭安静得多，从 14 号敌楼往西那段没修过，砖缝里长着草。',
  must:['必走','缆车上 → 走到 20 号敌楼 → 滑道下山'],
  chips:[['','门票¥45+缆车¥100'],['up','人比八达岭少一半'],['down','冬季滑道停运']],q:'慕田峪长城'}]},

{tab:'D3',name:'颐和园 · 什刹海',sub:'皇家园林 + 胡同 · 轻',start:510,hardEnd:1290,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 北宫门 · 地铁 4 号线 40 分',min:40,cost:5},
 post:{mode:'transit',conn:'什刹海 → 住处 · 地铁 8 号线 20 分',min:20,cost:3},
 stops:[
 {k:'bj-yiheyuan',name:'颐和园 · 长廊昆明湖',cng:'最美湖泊',era:'乾隆十五年清漪园',dur:180,prio:0,cost:60,cat:'tix',indoor:false,
  vibe:'长廊七百多米，每根梁上都有画，走到尽头昆明湖一下子铺开。',
  must:['必看','北宫门进 · 佛香阁登高 · 十七孔桥'],
  chips:[['','联票¥60'],['up','湖边可租船']],q:'颐和园'},
 {mode:'transit',conn:'颐和园 → 什刹海 · 地铁 4 号线转 6 号线 45 分',min:45,cost:5},
 {k:'bj-shichahai',name:'什刹海 · 胡同',era:'元代漕运终点',dur:100,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'银锭桥边坐着钓鱼的大爷，后海的酒吧还没开门，胡同里飘着炸酱面味。',
  must:['必逛','银锭桥观景 · 烟袋斜街 · 钟鼓楼'],
  chips:[['up','免票'],['','可租自行车穿胡同']],q:'北京什刹海'},
 {k:'bj-duck',name:'烤鸭 · 晚饭',era:'来北京的规定动作',dur:90,prio:0,cost:160,cat:'food',indoor:true,
  opts:[{name:'老字号挂炉烤鸭',cost:200,dur:100,vibe:'果木挂炉，片鸭师傅在桌边现片，108 片一只。'},
        {name:'本地馆子 · 不排队',cost:130,dur:80,vibe:'胡同里的小店，鸭子一样酥，价格便宜三分之一。'}],
  id:'bj-yakao',
  must:['必点','片皮蘸白糖 · 荷叶饼卷葱丝甜面酱'],
  chips:[['','人均¥130-200'],['down','老字号需提前订位']],q:'北京烤鸭'}]},

{tab:'D4',name:'天坛 · 前门收官',sub:'祈年殿与老街 · 下午离开 · 轻',start:510,hardEnd:1170,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 天坛东门 · 地铁 5 号线 20 分',min:20,cost:4},
 post:{mode:'transit',conn:'前门 → 首都机场/北京站 · 地铁直达 约 60 分',min:60,cost:10},
 stops:[
 {k:'bj-tiantan',name:'天坛 · 祈年殿',cng:'最美古镇',era:'明永乐十八年 · 皇帝祭天处',dur:120,prio:0,cost:34,cat:'tix',indoor:false,
  vibe:'三层蓝琉璃圆顶立在汉白玉台基上，回音壁贴着墙说话对面能听见。',
  must:['必看','祈年殿 · 回音壁 · 圜丘'],
  chips:[['','联票¥34'],['up','早上有大爷在园里唱戏']],q:'天坛公园'},
 {mode:'transit',conn:'天坛 → 前门大街 · 地铁 7 号线 15 分',min:15,cost:3},
 {k:'bj-qianmen',name:'前门大街 · 大栅栏',era:'明清商业街',dur:80,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'铛铛车在青石路上开过，两边老字号招牌一块挨一块。',
  must:['必逛','大栅栏老字号 · 带茯苓饼与稻香村'],
  chips:[['up','免票'],['','买特产方便']],q:'北京前门大街'}]}];

const BJ4_LODGES=[
 {opts:[{city:'前门 · 胡同酒店',price:480,why:'地铁枢纽 · 步行到天安门',q:'北京前门酒店'},
        {city:'南锣鼓巷 · 青旅',price:280,why:'省 ¥100/人 · 胡同里',q:'北京南锣鼓巷客栈'}]},
 {city:'前门 · 连住',price:480,why:'不挪窝 · 行李不动',q:'北京前门酒店'},
 {city:'前门 · 连住',price:480,why:'不挪窝 · 明早去天坛近',q:'北京前门酒店'},
 null];

/* ═══════════════════════════════════════════════════
   西安 3 天 · 城墙兵马俑（全程地铁 · 第二条城市漫步线）
   ═══════════════════════════════════════════════════ */
const XA_NODES=[
 {n:'钟楼·回民街',x:300,y:230,lx:13,ly:4,a:'start'},
 {n:'兵马俑',x:520,y:180,lx:13,ly:-8,a:'middle'},
 {n:'大雁塔',x:330,y:340,lx:-2,ly:16,a:'end'}];

const XA3_DAYS=[
{tab:'D1',name:'城墙骑行 · 回民街',sub:'市中心 · 骑一圈城墙 · 轻',start:570,hardEnd:1320,drive:'0 h',
 pre:null,post:{mode:'walk',conn:'步行回住处 · 10 分',min:10,cost:0},
 stops:[
 {k:'xa-wall',name:'西安城墙 · 骑行一圈',cng:'最美古镇',era:'明洪武年间 · 周长 13.7 km',dur:150,prio:0,cost:99,cat:'tix',indoor:false,
  vibe:'骑上城墙那一刻，脚下是六百年的砖，两边是活着的城市。',
  must:['必做','南门上墙租车 · 顺时针一圈约 100 分钟'],
  chips:[['','门票¥54 + 单车¥45'],['down','正午晒 · 傍晚最舒服'],['up','城墙上有补给点']],q:'西安城墙南门'},
 {mode:'walk',conn:'南门 → 回民街 · 步行 15 分',min:15,cost:0},
 {k:'xa-huimin',name:'回民街 · 北院门',era:'一条街全是碳水',dur:90,prio:0,cost:65,cat:'food',indoor:false,
  vibe:'羊肉泡馍要自己掰，肉夹馍的腊汁流下来，甑糕的枣泥堆得冒尖。',
  must:['必吃','老孙家泡馍 · 贾三灌汤包 · 红红酸菜炒米'],
  chips:[['','人均¥65'],['down','主街贵 · 往巷子里走'],['up','24 小时不打烊']],q:'西安回民街'},
 {mode:'walk',conn:'回民街 → 钟鼓楼广场 · 步行 5 分',min:5,cost:0},
 {k:'xa-bell',name:'钟鼓楼 · 夜灯',era:'明代报时中心',dur:60,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'灯一亮，钟楼整个浮在车流上面，绕一圈广场就能拍够。',
  must:['必看','夜里外观免费 · 登楼需另购票'],
  chips:[['up','广场免票'],['','登楼¥50 自选']],q:'西安钟鼓楼'}]},

{tab:'D2',name:'兵马俑 · 大唐不夜城',sub:'东郊往返 · 夜游长街 · 中',start:480,hardEnd:1320,drive:'0 h',
 pre:{mode:'transit',conn:'市区 → 兵马俑 · 地铁 9 号线 + 公交 约 80 分',min:80,cost:12,
   via:'华清池站换 613 路 · 或坐游 5 专线直达'},
 post:{mode:'transit',conn:'兵马俑 → 大唐不夜城 · 地铁 + 换乘 约 75 分',min:75,cost:10},
 stops:[
 {k:'xa-terracotta',name:'秦始皇兵马俑',cng:'最美古镇',era:'公元前 246 年起建',dur:180,prio:0,cost:120,cat:'tix',indoor:true,
  vibe:'一号坑门一推开，几千个真人大小的兵俑列在土沟里，两千两百年没散过队。',
  must:['必看','按 一号坑 → 三号坑 → 二号坑 顺序 · 请讲解或租语音'],
  chips:[['','门票¥120'],['down','旺季提前 3 天预约'],['','讲解¥100/团 自选']],q:'秦始皇兵马俑博物馆'},
 {k:'xa-tang',name:'大唐不夜城 · 夜游',era:'仿唐步行街',dur:120,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'整条街的唐风建筑亮起来，不倒翁小姐姐和飞天在人群里穿，热闹得不像博物馆城市。',
  must:['必看','19:30 后灯全开 · 大雁塔北广场喷泉'],
  chips:[['up','街区免票'],['down','周末人挤人']],q:'西安大唐不夜城'},
 {k:'xa-yongxing',name:'永兴坊 · 摔碗酒',era:'陕西非遗小吃街',dur:70,prio:1,cost:55,cat:'food',indoor:false,
  vibe:'一碗稠酒五块钱，喝完把碗往地上摔，一晚上碎碗堆成小山。',
  must:['必做','摔碗酒 ¥5 · 子长煎饼 · 蓼花糖'],
  chips:[['','人均¥55'],['up','街区免票']],q:'西安永兴坊'}]},

{tab:'D3',name:'陕历博 · 大雁塔收官',sub:'博物馆一上午 · 下午离开 · 轻',start:510,hardEnd:1200,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 陕西历史博物馆 · 地铁 2 号线 20 分',min:20,cost:3},
 post:{mode:'transit',conn:'大雁塔 → 火车北站/机场 · 地铁直达 约 50 分',min:50,cost:8},
 stops:[
 {k:'xa-museum',name:'陕西历史博物馆',cng:'最美古镇',era:'十八件国宝级文物',dur:150,prio:0,cost:0,cat:'free',indoor:true,
  vibe:'一层走完就是从周到唐，何家村那批金银器隔着玻璃还在发光。',
  must:['必看','基本陈列免费需预约 · 何家村特展¥30 值得加'],
  chips:[['up','基本陈列免票'],['down','提前 3 天官微预约 · 秒光'],['','特展¥30 自选']],q:'陕西历史博物馆'},
 {mode:'walk',conn:'陕历博 → 大慈恩寺 · 步行 15 分',min:15,cost:0},
 {k:'xa-pagoda',name:'大雁塔 · 大慈恩寺',era:'玄奘译经处 · 唐永徽三年',dur:90,prio:0,cost:40,cat:'tix',indoor:false,
  vibe:'玄奘从印度带回来的经书就存在这座塔里，塔身一千三百年没倒。',
  must:['必看','大慈恩寺¥40 · 登塔另¥20 可俯瞰南城'],
  chips:[['','门票¥40'],['','登塔¥20 自选']],q:'西安大雁塔'},
 {k:'xa-lunch',name:'走之前 · 葫芦头或裤带面',era:'碳水收尾',dur:70,prio:0,cost:45,cat:'food',indoor:true,
  opts:[{name:'春发生葫芦头泡馍',cost:55,dur:75,vibe:'猪大肠处理得一点腥味没有，汤浓馍筋道。'},
        {name:'裤带面 · 油泼辣子',cost:35,dur:60,vibe:'一根面裤带宽，热油往辣子面上一泼，香得整条街都知道。'}],
  id:'xa-food',
  must:['必点','葫芦头配糖蒜 · 或裤带面加荷包蛋'],
  chips:[['','人均¥35-55']],q:'西安 葫芦头'}]}];

const XA3_LODGES=[
 {opts:[{city:'钟楼 · 回民街旁',price:380,why:'地铁枢纽 · 夜里逛街走回来',q:'西安钟楼酒店'},
        {city:'小寨 · 地铁口',price:260,why:'省 ¥60/人 · 去陕历博两站',q:'西安小寨酒店'}]},
 {city:'钟楼 · 连住',price:380,why:'不挪窝 · 行李不动',q:'西安钟楼酒店'},
 null];

/* ═══════════════════════════════════════════════════
   成都 3 天 · 城市漫步（全程地铁 · 第一条纯步行城市线）
   补两个形态缺口：公共交通、城市漫步
   ═══════════════════════════════════════════════════ */
const CD_NODES=[
 {n:'市中心',x:330,y:230,lx:13,ly:4,a:'start'},
 {n:'熊猫基地',x:360,y:110,lx:13,ly:-8,a:'middle'},
 {n:'武侯祠',x:280,y:300,lx:-2,ly:16,a:'middle'},
 {n:'杜甫草堂',x:222,y:214,lx:-6,ly:-10,a:'end'}];

const CD3_DAYS=[
{tab:'D1',name:'宽窄巷子 · 人民公园',sub:'市中心步行 · 茶馆一下午 · 极轻',start:570,hardEnd:1320,drive:'0 h',
 pre:null,post:{mode:'walk',conn:'步行回住处 · 12 分',min:12,cost:0},
 stops:[
 {k:'cd-kuanzhai',name:'宽窄巷子',cng:'最美古镇',era:'清代少城胡同',dur:90,prio:0,cost:0,cat:'free',indoor:false,
  vibe:'青砖巷子里全是掏耳朵的、盖碗茶的、卖冰粉的，游客多但成都的样子就在这儿。',
  must:['必看','窄巷子看老院门 · 井巷子砖雕影壁墙'],
  chips:[['up','免票'],['down','人多 · 早上 9 点前最静']],q:'成都宽窄巷子'},
 {mode:'walk',conn:'宽窄巷子 → 奎星楼街 · 步行 8 分',min:8,cost:0},
 {k:'cd-kuixing',name:'奎星楼街 · 小吃街',era:'本地人的苍蝇馆子街',dur:75,prio:1,cost:60,cat:'food',indoor:true,
  vibe:'一条街全是排队的小店，冒椒火辣的冷锅串串和马路边儿的锅盔，油碟一蘸就停不下来。',
  must:['必点','冷锅串串 · 军屯锅盔 · 三大炮'],chips:[['','人均¥60'],['down','饭点排队 30 分']],q:'成都奎星楼街'},
 {mode:'walk',conn:'奎星楼街 → 人民公园 · 步行 12 分',min:12,cost:0},
 {k:'cd-heming',name:'人民公园 · 鹤鸣茶社',era:'1923 年老茶馆',dur:120,prio:0,cost:35,cat:'free',indoor:false,
  vibe:'竹椅一躺，盖碗茶续水到天黑，隔壁桌在打牌，采耳师傅的音叉在耳边嗡。',
  must:['必做','盖碗茶 ¥25 无限续 · 采耳 ¥50 体验一次'],
  chips:[['','茶位¥25 起'],['up','公园免票'],['','采耳¥50 自选']],q:'成都人民公园鹤鸣茶社'},
 {mode:'walk',conn:'人民公园 → 太古里 · 地铁 2 号线 15 分',min:15,cost:3},
 {k:'cd-taikoo',name:'太古里 · 大慈寺',era:'古寺与快闪店并排',dur:90,prio:1,cost:0,cat:'free',indoor:false,
  vibe:'一边是唐代大慈寺的红墙，一边是玻璃橱窗，成都把新旧摞在一起也不违和。',
  must:['必看','大慈寺红墙拍照 · 晚上太古里灯亮起来'],
  chips:[['up','免票'],['','晚上更好看']],q:'成都太古里'}]},

{tab:'D2',name:'熊猫基地 · 武侯祠锦里',sub:'早起看熊猫 · 地铁往返 · 中',start:420,hardEnd:1320,drive:'0 h',
 pre:{mode:'transit',conn:'市中心 → 熊猫基地 · 地铁 3 号线 + 接驳 约 50 分',min:50,cost:5,
   via:'熊猫大道站换观光车 · 早班地铁 6:20 首发'},
 post:{mode:'transit',conn:'锦里 → 住处 · 地铁 3 号线 20 分',min:20,cost:3},
 stops:[
 {k:'cd-panda',name:'大熊猫繁育研究基地',cng:'最美湿地',era:'全球最大熊猫种群',dur:180,prio:0,cost:55,cat:'tix',indoor:false,
  vibe:'八点半的月亮产房里全是滚来滚去的幼崽，晚一小时它们就睡了。',
  must:['必做','7:30 开园就进 · 先冲月亮产房和幼年园'],
  chips:[['','门票¥55'],['down','10 点后熊猫全睡'],['','观光车¥10 自选']],q:'成都大熊猫繁育研究基地'},
 {mode:'transit',conn:'熊猫基地 → 武侯祠 · 地铁 3 号线 约 55 分',min:55,cost:5},
 {k:'cd-wuhou',name:'武侯祠 · 三义庙',cng:'最美古镇',era:'唐碑宋刻 · 蜀汉君臣合祀',dur:100,prio:0,cost:50,cat:'tix',indoor:false,
  vibe:'红墙夹道的那条竹影小径，几乎每个来成都的人都拍过。',
  must:['必看','红墙竹影甬道 · 唐碑「三绝碑」 · 惠陵'],
  chips:[['','门票¥50'],['','与锦里连着']],q:'成都武侯祠'},
 {mode:'walk',conn:'武侯祠 → 锦里 · 步行 5 分',min:5,cost:0},
 {k:'cd-jinli',name:'锦里 · 夜市',era:'仿古商业街',dur:80,prio:1,cost:55,cat:'food',indoor:false,
  vibe:'灯笼一串串挂到街尾，三大炮的糖锣敲得响，热闹但不难吃。',
  must:['必吃','伤心凉粉 · 三大炮 · 张飞牛肉'],
  chips:[['up','免票'],['','人均¥55'],['','晚上灯笼最好看']],q:'成都锦里'}]},

{tab:'D3',name:'杜甫草堂 · 春熙路收官',sub:'诗与街 · 下午离开 · 轻',start:540,hardEnd:1200,drive:'0 h',
 pre:{mode:'transit',conn:'住处 → 杜甫草堂 · 地铁 4 号线 18 分',min:18,cost:3},
 post:{mode:'transit',conn:'春熙路 → 火车东站/机场 · 地铁直达 约 40 分',min:40,cost:6},
 stops:[
 {k:'cd-dufu',name:'杜甫草堂',cng:'最美古镇',era:'诗圣避乱居所 · 唐',dur:120,prio:0,cost:50,cat:'tix',indoor:false,
  vibe:'茅屋前的溪水和竹林，一千两百年前那句「安得广厦千万间」就写在这儿。',
  must:['必看','茅屋故居 · 大雅堂 · 浣花溪连着走'],
  chips:[['','门票¥50'],['up','浣花溪公园免票']],q:'成都杜甫草堂'},
 {mode:'transit',conn:'草堂 → 春熙路 · 地铁 4 号线转 2 号线 25 分',min:25,cost:4},
 {k:'cd-chunxi',name:'春熙路 · IFS 熊猫',era:'成都最旺的街',dur:80,prio:1,cost:0,cat:'free',indoor:true,
  vibe:'爬墙熊猫屁股对着街，楼下人来人往，走之前买点特产刚好。',
  must:['必做','IFS 楼顶熊猫合影 · 带牛肉干与蜀绣'],
  chips:[['up','免票'],['','买特产方便']],q:'成都春熙路IFS'},
 {k:'cd-hotpot',name:'火锅 · 走之前那顿',era:'成都的仪式感',dur:90,prio:0,cost:120,cat:'food',indoor:true,
  opts:[{name:'老牌牛油火锅 · 排队店',cost:140,dur:110,vibe:'牛油锅底翻滚，毛肚七上八下，走之前必须再来一顿。'},
        {name:'本地连锁 · 不排队',cost:100,dur:80,vibe:'味道稳定不用等位，赶车前吃刚好。'}],
  id:'cd-hg',
  must:['必点','毛肚 · 鸭肠 · 老肉片 · 冰粉解辣'],
  chips:[['','人均¥100-140'],['down','热门店排队 1 小时']],q:'成都火锅'}]}];

const CD3_LODGES=[
 {opts:[{city:'春熙路 · 太古里旁',price:420,why:'地铁枢纽 · 夜里逛街不用打车',q:'成都春熙路酒店'},
        {city:'宽窄巷子 · 巷内客栈',price:280,why:'省 ¥70/人 · 早上第一个进巷子',q:'成都宽窄巷子客栈'}]},
 {city:'春熙路 · 连住',price:420,why:'不挪窝 · 行李不动',q:'成都春熙路酒店'},
 null];

/* ═══ 天数变体（批次一收尾）：额济纳 3 / 关西 4 / 香港 2 / 梅里 5 / 滇西北 5 ═══ */
const NM3_DAYS=[NM4_DAYS[0], _cd(NM4_DAYS[1],{tab:'D2'}), _cd(NM4_DAYS[3],{tab:'D3'})];
const NM3_LODGES=[NM4_LODGES[0], NM4_LODGES[1], null];

const KAN4_DAYS=[KAN5_DAYS[0], _cd(KAN5_DAYS[1],{tab:'D2'}), _cd(KAN5_DAYS[2],{tab:'D3'}), _cd(KAN5_DAYS[4],{tab:'D4'})];
const KAN4_LODGES=[KAN5_LODGES[0], KAN5_LODGES[1], KAN5_LODGES[2], null];

const HK2_DAYS=[HK_DAYS[0], _cd(HK_DAYS[2],{tab:'D2'})];
const HK2_LODGES=[HK_LODGES[0], null];

const MLS5_DAYS=[MLS6_DAYS[0], _cd(MLS6_DAYS[1],{tab:'D2'}), _cd(MLS6_DAYS[2],{tab:'D3'}),
                 _cd(MLS6_DAYS[4],{tab:'D4'}), _cd(MLS6_DAYS[5],{tab:'D5'})];
const MLS5_LODGES=[MLS6_LODGES[0], MLS6_LODGES[1], MLS6_LODGES[2], MLS6_LODGES[4], null];

const DXB5_DAYS=[DXB_DAYS[0], _cd(DXB_DAYS[1],{tab:'D2'}), _cd(DXB_DAYS[2],{tab:'D3'}),
                 _cd(DXB_DAYS[3],{tab:'D4'}), _cd(DXB_DAYS[5],{tab:'D5'})];
const DXB5_LODGES=[DXB_LODGES[0], DXB_LODGES[1], DXB_LODGES[2], DXB_LODGES[3], null];

/* ── 天数变体追加区（gl3 / hs2 / djy2 / zjj5 / xz10）· 必须在 ROUTES 字面量之后 ── */
ROUTES.gl4.dayVariants=[3,4];
ROUTES.hs3.dayVariants=[2,3];
ROUTES.djy1.dayVariants=[1,2];
ROUTES.xz7.dayVariants=[7,10];
ROUTES.nm4.dayVariants=[3,4];
ROUTES.kansai5.dayVariants=[4,5];
ROUTES.hk3.dayVariants=[2,3];
ROUTES.mls6.dayVariants=[5,6];
ROUTES.dxb6.dayVariants=[5,6];
ROUTES.zjj4.dayVariants=[4,5];
Object.assign(ROUTES,{
 jz4:normRoute({
  name:'九寨沟 · 黄龙',dest:'四川 · 阿坝',fam:'jz',
  days:JZ4_DAYS,lodges:JZ4_LODGES,
  transport:{mode:'drive',rent:2400,perCar:true,roadfood:280,label:'租车 · 油费路桥（按车均摊）'},
  locale:{region:'domestic',country:'中国',navApp:'amap',currencyNote:null},
  stay:{nights:3},dayVariants:[4],
  budgets:[{l:'宽松',v:4000},{l:'精打细算',v:3550}],
  title:'🍁 九寨沟黄龙 4 天 · 彩林季',meta:'四川阿坝 · 4天3晚 · 成都出发',
  why:'九寨的水一年四季都在，但十月下旬彩林一上来才是巅峰——五花海周围整片黄红，倒影里的颜色比水面还多。D1 沿岷江开八小时进沟；D2 一整天走三条沟，七点前到闸机；D3 黄龙的三千个钙华池叠在 3600 米的坡上；D4 松潘古城顺路收尾。',
  hero1v:'940<small>km</small>',hero1k:'成都往返',
  strength:'中',overTip:'可换漳扎镇',
  weather:'九寨 10 月 · 昼 8–18℃ · 早晚冷 · 黄龙 3600m 更冷',
  tixLabel:'门票与观光车',foodLabel:'餐饮 · 含路餐',carLabel:'租车 · 油费路桥（按车均摊）',
  tastes:[
   {id:'nature',label:'山水控',apply(){ addP('海子控'); }},
   {id:'geo',   label:'山水控',apply(){ addP('钙华地貌控'); }},
   {id:'photo', label:'拍照控',apply(){ addP('倒影机位'); }},
   {id:'hike',  label:'走走走',apply(){ addP('栈道走全程'); }},
   {id:'chill', label:'躺平型',apply(){ addP('海子边多坐'); }}],
  defSels:{}, defSelsM:[],
  seasons:[{in:true,name:'九寨预约',why:'旺季需提前 3 天官网实名预约',tag:'已排入 D2',ver:1},
   {in:false,name:'十月彩林',why:'10 月下旬至 11 月初 · 一年最好的两周',pick:{key:'jz-autumn',name:'九寨彩林',ptext:'秋色控'}}],
  extras:[{later:{key:'jz-ruoergai',name:'若尔盖草原',why:'川主寺往北 · 需另一天',ptext:'草原控'}}],
  extrasSub:'备着的还有 玩 17 · 吃 21 · 住 13',
  todos(){ return [
   {k:'book',tag:['down','预约'],text:'九寨沟旺季提前 3 天官网实名预约 · 每日限流',v:'',url:'https://www.jiuzhai.com'},
   {k:'early',tag:['down','排队'],text:'7:00 前到沟口闸机 · 晚了排队一小时',v:''},
   {k:'alt',tag:['','高反'],text:'黄龙五彩池 3600m · 慢走勿急 · 可租氧气',v:''},
   {k:'warm',tag:['','装备'],text:'九寨早晚 8℃ · 黄龙更冷 · 带厚外套',v:''}]; },
  map:{nodes:JZ_NODES,order:[0,1,2],loop:true,
   seg:[[0,1],null,[1,2],[2,0]],tonight:[1,1,2,-1]}}),

 yl6:normRoute({
  name:'伊犁 · 河谷深度',dest:'新疆 · 伊犁河谷',fam:'yl',
  days:YL6_DAYS,lodges:YL6_LODGES,
  transport:{mode:'drive',rent:3600,perCar:true,roadfood:380,label:'租车 · 油费路桥（按车均摊）'},
  locale:{region:'domestic',country:'中国',navApp:'amap',currencyNote:null},
  stay:{nights:5},dayVariants:[6],
  budgets:[{l:'宽松',v:5000},{l:'精打细算',v:4450}],
  title:'🐎 伊犁 6 天 · 河谷深度',meta:'新疆伊犁 · 6天5晚 · 伊宁进出',
  why:'北疆环线只在伊犁待两天就走，这条把河谷走透：D1 伊宁六星街的蓝窗俄式小楼；D2 那拉提空中草原骑马；D3 巴音布鲁克等日落——那十分钟河的每道弯里都嵌一个太阳；D4 特克斯八卦城全城没有红绿灯；D5 昭苏骑伊犁马；D6 手抓饭收尾。',
  hero1v:'910<small>km</small>',hero1k:'伊宁进出',
  strength:'中',overTip:'可换那拉提镇',
  weather:'伊犁 7 月 · 昼 18–30℃ · 草原昼夜温差大 · 巴音 2500m 夜冷',
  tixLabel:'门票与区间车',foodLabel:'餐饮 · 含手抓饭',carLabel:'租车 · 油费路桥（按车均摊）',
  tastes:[
   {id:'nature',label:'山水控',apply(){ addP('草原控'); }},
   {id:'geo',   label:'山水控',apply(){ addP('草原控'); }},
   {id:'folk',  label:'人文控',apply(){ addP('哈萨克与锡伯'); }},
   {id:'photo', label:'拍照控',apply(){ addP('九曲日落机位'); }},
   {id:'chill', label:'躺平型',apply(){ addP('草原多躺一会儿'); }},
   {id:'food',  label:'美食控',apply(){ addP('手抓饭不将就'); }}],
  defSels:{}, defSelsM:[],
  seasons:[{in:true,name:'九曲日落',why:'日落前 1.5 小时进 · 那十分钟才有九个太阳',tag:'已排入 D3',ver:1},
   {in:false,name:'昭苏油菜花',why:'7 月中下旬万亩花海 · 其余月份是绿草',pick:{key:'yl-rape',name:'昭苏油菜花',ptext:'花海控'}},
   {in:false,name:'霍城薰衣草',why:'6 月中下旬 · 需另半天',pick:{key:'yl-lavender',name:'霍城薰衣草',ptext:'花海控'}}],
  extras:[{later:{key:'yl-kalajun',name:'喀拉峻草原',why:'特克斯旁 · 需另一天',ptext:'草原控'}}],
  extrasSub:'备着的还有 玩 22 · 吃 26 · 住 17',
  todos(){ return [
   {k:'sunset',tag:['down','时间'],text:'九曲十八弯日落前 1.5 小时进景区 · 区间车要时间',v:''},
   {k:'warm',tag:['','装备'],text:'巴音布鲁克 2500m 夜里接近 0℃ · 带厚衣',v:''},
   {k:'fuel',tag:['','补给'],text:'巴音至特克斯段加油站少 · 提前加满',v:''},
   {k:'horse',tag:['','提示'],text:'骑马前谈好价格与时长 · 认准正规马场',v:''}]; },
  map:{nodes:YL_NODES,order:[0,1,2],loop:true,
   seg:[null,[0,1],null,[1,2],null,[2,0]],tonight:[0,1,1,2,2,-1]}}),

 tl3:normRoute({
  name:'福建土楼 · 客家围屋',dest:'福建 · 龙岩漳州',fam:'tl',
  days:TL3_DAYS,lodges:TL3_LODGES,
  transport:{mode:'transit',rent:0,perCar:false,roadfood:0,label:'动车 · 包车（每人实付）'},
  locale:{region:'domestic',country:'中国',navApp:'amap',currencyNote:null},
  stay:{nights:2},dayVariants:[3],
  budgets:[{l:'宽松',v:1950},{l:'精打细算',v:1700}],
  title:'🏘 福建土楼 3 天 · 客家围屋',meta:'福建龙岩漳州 · 3天2晚 · 厦门进出',
  why:'土楼不是一个景点是一片文明：D1 南靖田螺坑的四菜一汤，云水谣的百年老榕；D2 永定振成楼外圈夯土内圈西洋柱廊，一栋住过四百人；D3 初溪的集庆楼六百年没塌，72 道楼梯各自独立，而且人比南靖少得多。住在土楼里，天井看星星。',
  hero1v:'3<small>片</small>',hero1k:'南靖 · 永定 · 初溪',
  strength:'轻',overTip:'土楼间需包车',
  weather:'闽西 8 月 · 昼 26–34℃ · 山区午后有雨',
  tixLabel:'门票与包车',foodLabel:'餐饮 · 含客家菜',carLabel:'动车 · 包车（每人实付）',
  tastes:[
   {id:'art',   label:'历史控',apply(){ addP('围屋细看派'); }},
   {id:'folk',  label:'人文控',apply(){ addP('客家生活'); }},
   {id:'photo', label:'拍照控',apply(){ addP('土楼俯拍机位'); }},
   {id:'food',  label:'美食控',apply(){ addP('客家菜不将就'); }},
   {id:'chill', label:'躺平型',apply(){ addP('溪边多坐一会儿'); }}],
  defSels:{}, defSelsM:[],
  seasons:[{in:true,name:'土楼间需包车',why:'南靖永定之间公交不便 · 建议整段包车',tag:'已排入全程',ver:1},
   {in:false,name:'土楼夜景灯',why:'部分景区周末开灯 · 需当地确认',pick:{key:'tl-night',name:'土楼夜景',ptext:'夜景控'}}],
  extras:[{later:{key:'tl-hekeng',name:'河坑土楼群',why:'南靖境内 · 需另半天',ptext:'土楼控'}}],
  extrasSub:'备着的还有 玩 15 · 吃 19 · 住 12',
  todos(){ return [
   {k:'car',tag:['down','交通'],text:'土楼之间公交不便 · 建议包车按天算 · 提前谈价',v:''},
   {k:'train',tag:['','订票'],text:'厦门至南靖动车 50 分 · 提前订往返',v:''},
   {k:'stay',tag:['','住宿'],text:'土楼民宿条件简单 · 图的是体验不是舒适',v:''},
   {k:'rain',tag:['','天气'],text:'闽西山区午后有雨 · 带伞',v:''}]; },
  map:{nodes:TL_NODES,order:[0,1,2],loop:true,
   seg:[[0,1],[1,2],[2,0]],tonight:[1,2,-1]}}),

 ts3:normRoute({
  name:'泰山曲阜 · 登顶与三孔',dest:'山东 · 泰安曲阜',fam:'ts',
  days:TS3_DAYS,lodges:TS3_LODGES,
  transport:{mode:'transit',rent:0,perCar:false,roadfood:0,label:'高铁 · 公交 · 索道（每人实付）'},
  locale:{region:'domestic',country:'中国',navApp:'amap',currencyNote:null},
  stay:{nights:2},dayVariants:[3],
  budgets:[{l:'宽松',v:1900},{l:'精打细算',v:1700}],
  title:'⛰ 泰山曲阜 3 天 · 登顶与三孔',meta:'山东泰安曲阜 · 3天2晚 · 高铁直达',
  why:'这条是「爬上去」和「看回去」两件事：D1 从红门一路爬七千级台阶到南天门，最后的十八盘陡到手脚并用；D2 四点起床在日观峰等日出，裹着租来的军大衣；D3 高铁二十分钟到曲阜，孔庙大成殿那十根蟠龙柱是明代雕的，孔林里十万座坟散在两万棵古树间。住山顶就不用摸黑爬夜山。',
  hero1v:'7,000<small>级</small>',hero1k:'红门到南天门',
  strength:'重',overTip:'可换泰安火车站旁',
  weather:'泰山 8 月 · 山下 26–33℃ · 山顶 15–22℃ · 日出时 10℃ 以下',
  tixLabel:'门票与索道',foodLabel:'餐饮 · 含山顶餐',carLabel:'高铁 · 公交（每人实付）',
  tastes:[
   {id:'hike',  label:'走走走',apply(){ addP('台阶爬全程'); }},
   {id:'art',   label:'历史控',apply(){ addP('三孔细看派'); }},
   {id:'photo', label:'拍照控',apply(){ addP('日出机位'); }},
   {id:'nature',label:'山水控',apply(){ addP('云海控'); }},
   {id:'geo',   label:'山水控',apply(){ addP('云海控'); }}],
  defSels:{}, defSelsM:[],
  seasons:[{in:true,name:'日观峰日出',why:'日出前 40 分到位 · 山顶 10℃ 以下',tag:'已排入 D2',ver:1},
   {in:false,name:'泰山云海',why:'雨后初晴概率最高 · 看天吃饭',pick:{key:'ts-cloud',name:'泰山云海',ptext:'云海控'}}],
  extras:[{later:{key:'ts-zoucheng',name:'邹城孟庙',why:'曲阜旁 · 需另半天',ptext:'历史控'}}],
  extrasSub:'备着的还有 玩 16 · 吃 20 · 住 14',
  todos(){ return [
   {k:'coat',tag:['down','装备'],text:'山顶日出时 10℃ 以下 · 可租军大衣¥30',v:''},
   {k:'stay',tag:['down','订房'],text:'山顶宾馆旺季需提前 1 周订 · 房少价高',v:''},
   {k:'shoe',tag:['','装备'],text:'7000 级台阶 · 护膝与好走的鞋',v:''},
   {k:'sankong',tag:['','购票'],text:'曲阜三孔联票¥140 · 孔林需另坐观光车',v:'',url:'https://www.sanks.cn'}]; },
  map:{nodes:TS_NODES,order:[0,1],loop:true,
   seg:[null,null,[0,1]],tonight:[0,0,-1]}}),
 njg8:normRoute({
  name:'南疆 · 喀什与帕米尔',dest:'新疆 · 南疆环线',fam:'njg',
  days:NJG8_DAYS,lodges:NJG8_LODGES,
  transport:{mode:'drive',rent:5600,perCar:true,roadfood:560,label:'租车 · 油费路桥（按车均摊）'},
  locale:{region:'domestic',country:'中国',navApp:'amap',currencyNote:null},
  stay:{nights:7},dayVariants:[8],
  budgets:[{l:'宽松',v:7750},{l:'精打细算',v:6900}],
  title:'🕌 南疆 8 天 · 喀什与帕米尔',meta:'新疆南疆 · 8天7晚 · 自驾环线',
  why:'南疆和北疆是两个新疆：那边是雪山湖泊草原，这边是土城、清真寺、帕米尔高原和塔克拉玛干。D1-3 喀什老城接帕米尔（卡拉库里湖里倒着 7546 米的慕士塔格）；D4-5 转和田捡玉逛夜市；D6 穿五百公里沙漠公路；D7 天山神秘大峡谷；D8 走独库南段回乌市。',
  hero1v:'2,700<small>km</small>',hero1k:'南疆大环线',
  strength:'重',overTip:'可换喀什市区快捷',
  weather:'南疆 8 月 · 昼 25–38℃ · 干热 · 帕米尔昼夜温差 20℃',
  tixLabel:'门票与通行证',foodLabel:'餐饮 · 含夜市',carLabel:'租车 · 油费路桥（按车均摊）',
  tastes:[
   {id:'folk',  label:'人文控',apply(){ addP('维吾尔与塔吉克'); }},
   {id:'nature',label:'山水控',apply(){ addP('帕米尔控'); }},
   {id:'geo',   label:'山水控',apply(){ addP('帕米尔控'); }},
   {id:'photo', label:'拍照控',apply(){ addP('慕士塔格倒影'); }},
   {id:'food',  label:'美食控',apply(){ addP('夜市不将就'); }},
   {id:'hike',  label:'走走走',apply(){ addP('峡谷走到底'); }}],
  defSels:{}, defSelsM:[],
  seasons:[{in:true,name:'边境通行证',why:'去塔县需办理 · 喀什边防支队当天可出',tag:'已排入 D2 前',ver:1},
   {in:true,name:'金草滩秋色',why:'9-10 月草滩最金 · 其余月份偏绿',tag:'已排入 D3',ver:0},
   {in:false,name:'红其拉甫口岸',why:'需另办证件 · 海拔 4700m',pick:{key:'njg-khunjerab',name:'红其拉甫',ptext:'口岸控'}}],
  extras:[{later:{key:'njg-karghilik',name:'莎车老城',why:'和田路上 · 需另半天',ptext:'老城控'}}],
  extrasSub:'备着的还有 玩 24 · 吃 31 · 住 19',
  todos(){ return [
   {k:'permit',tag:['down','办证'],text:'去塔县需边境通行证 · 喀什边防支队当天可办 · 带身份证',v:''},
   {k:'altitude',tag:['down','高反'],text:'帕米尔海拔 3100–3600m · 备高反药与红景天',v:''},
   {k:'fuel',tag:['down','补给'],text:'沙漠公路五百公里无补给 · 进沙漠前加满油备足水',v:''},
   {k:'car',tag:['','租车'],text:'长途建议 SUV · 确认异地还车与备胎',v:''},
   {k:'canyon',tag:['down','天气'],text:'大峡谷雨天禁入 · 有山洪风险',v:''}]; },
  map:{nodes:NJG_NODES,order:[0,1,2,3],loop:true,
   seg:[null,[0,1],null,[1,2],null,[2,3],null,[3,0]],tonight:[0,1,1,2,2,3,3,-1]}}),
 bn4:normRoute({
  name:'西双版纳 · 雨林与傣味',dest:'云南 · 西双版纳',fam:'bn',
  days:BN4_DAYS,lodges:BN4_LODGES,
  transport:{mode:'transit',rent:0,perCar:false,roadfood:0,label:'打车 · 景区专线（每人实付）'},
  locale:{region:'domestic',country:'中国',navApp:'amap',currencyNote:null},
  stay:{nights:3},dayVariants:[4],
  budgets:[{l:'宽松',v:2300},{l:'精打细算',v:2050}],
  title:'🌴 西双版纳 4 天 · 雨林与傣味',meta:'云南西双版纳 · 4天3晚 · 不含机票',
  why:'版纳跟滇西北是两个云南：这边全年短袖，热带雨林、南传佛教、傣族村寨。D1 落地逛告庄夜市；D2 野象谷走树冠层的空中走廊，接基诺山寨；D3 傣族园天天泼水不用等四月；D4 中科院植物园看一万三千种热带植物再飞走。',
  hero1v:'3<small>片</small>',hero1k:'雨林 · 傣寨 · 植物园',
  strength:'轻',overTip:'可换景洪市区',
  weather:'版纳 8 月 · 昼 24–32℃ · 雨季闷热 · 全年短袖',
  tixLabel:'门票与索道',foodLabel:'餐饮 · 含傣味',carLabel:'打车 · 机场线（每人实付）',
  tastes:[
   {id:'nature',label:'山水控',apply(){ addP('雨林控'); }},
   {id:'geo',   label:'山水控',apply(){ addP('雨林控'); }},
   {id:'folk',  label:'人文控',apply(){ addP('傣族与基诺'); }},
   {id:'food',  label:'美食控',apply(){ addP('傣味不将就'); }},
   {id:'photo', label:'拍照控',apply(){ addP('金塔夜景机位'); }},
   {id:'chill', label:'躺平型',apply(){ addP('江边多坐一会儿'); }}],
  defSels:{}, defSelsM:[],
  seasons:[{in:true,name:'傣族园泼水',why:'每天 14:00 与 16:00 两场 · 不用等四月',tag:'已排入 D3',ver:1},
   {in:false,name:'泼水节',why:'4 月 13–15 日全城泼水 · 需提前半年订房',pick:{key:'bn-songkran',name:'泼水节',ptext:'节庆控'}}],
  extras:[{later:{key:'bn-mengla',name:'望天树空中走廊',why:'勐腊方向 · 需另一天',ptext:'雨林控'}}],
  extrasSub:'备着的还有 玩 19 · 吃 28 · 住 16',
  todos(){ return [
   {k:'mosquito',tag:['down','装备'],text:'雨林蚊虫多 · 防蚊液与长裤必备',v:''},
   {k:'water',tag:['','装备'],text:'傣族园泼水必湿身 · 带换洗与手机防水袋',v:''},
   {k:'taxi',tag:['','交通'],text:'景点分散建议打车 · 高德叫车比景区车便宜',v:''},
   {k:'rain',tag:['down','天气'],text:'5–10 月雨季 · 午后阵雨随身带伞',v:''}]; },
  map:{nodes:BN_NODES,order:[0,1,2],loop:true,
   seg:[null,[0,1,0],[0,2,0],null],tonight:[0,0,0,-1]}}),

 yy3:normRoute({
  name:'元阳梯田 · 灌水期限定',dest:'云南 · 红河元阳',fam:'yy',
  days:YY3_DAYS,lodges:YY3_LODGES,
  transport:{mode:'drive',rent:1500,perCar:true,roadfood:180,label:'租车 · 油费路桥（按车均摊）'},
  locale:{region:'domestic',country:'中国',navApp:'amap',currencyNote:null},
  stay:{nights:2},dayVariants:[3],
  budgets:[{l:'宽松',v:2400},{l:'精打细算',v:2200}],
  title:'🌾 元阳梯田 3 天 · 灌水期限定',meta:'云南红河 · 3天2晚 · 昆明出发自驾',
  why:'元阳只在 11 月到 4 月灌水期才是那副样子——三千七百级梯田灌满水，日出日落时每块田都是镜子，其余月份是绿油油的稻田，完全两回事。D1 昆明开五小时到坝达看日落；D2 摸黑起来蹲多依树日出，傍晚老虎嘴看夕阳把梯田染红；D3 回程顺路建水古城。',
  hero1v:'710<small>km</small>',hero1k:'昆明往返自驾',
  strength:'中',overTip:'可换元阳新街镇',
  weather:'元阳 1 月 · 昼 10–20℃ · 早晚冷 · 日出前山顶接近 0℃',
  tixLabel:'梯田联票',foodLabel:'餐饮 · 含建水烧豆腐',carLabel:'租车 · 油费路桥（按车均摊）',
  tastes:[
   {id:'photo', label:'拍照控',apply(){ addP('日出日落机位'); }},
   {id:'nature',label:'山水控',apply(){ addP('梯田控'); }},
   {id:'geo',   label:'山水控',apply(){ addP('梯田控'); }},
   {id:'folk',  label:'人文控',apply(){ addP('哈尼村寨'); }},
   {id:'art',   label:'历史控',apply(){ addP('建水古城细看'); }}],
  defSels:{}, defSelsM:[],
  seasons:[{in:true,name:'灌水期镜面',why:'11 月至次年 4 月才有水镜 · 其余月份是绿田',tag:'已排入全程',ver:1},
   {in:true,name:'多依树日出',why:'日出前 40 分到位占机位 · 冬季 7:20 前',tag:'已排入 D2',ver:0},
   {in:false,name:'哈尼长街宴',why:'农历十月年 · 一年一次',pick:{key:'yy-feast',name:'长街宴',ptext:'节庆控'}}],
  extras:[{later:{key:'yy-shadian',name:'沙甸大清真寺',why:'个旧方向 · 需另半天',ptext:'建筑控'}}],
  extrasSub:'备着的还有 玩 14 · 吃 18 · 住 11',
  todos(){ return [
   {k:'season',tag:['down','季节'],text:'11–4 月才是灌水期 · 其余月份没有水镜',v:''},
   {k:'sunrise',tag:['down','早起'],text:'多依树日出需 6:30 起床 · 住多依树可少赶路',v:''},
   {k:'cold',tag:['','装备'],text:'日出前山顶接近 0℃ · 羽绒服与手套',v:''},
   {k:'road',tag:['down','路况'],text:'后段全是盘山弯道 · 夜间不建议开',v:''}]; },
  map:{nodes:YY_NODES,order:[0,1,2],loop:true,
   seg:[[0,1],[1,2,1],[1,0]],tonight:[1,1,-1]}}),
 qd3:normRoute({
  name:'青岛 · 红瓦绿树',dest:'山东 · 青岛',fam:'qd',
  days:QD3_DAYS,lodges:QD3_LODGES,
  transport:{mode:'transit',rent:0,perCar:false,roadfood:0,label:'地铁 · 公交（每人实付）'},
  locale:{region:'domestic',country:'中国',navApp:'amap',currencyNote:null},
  stay:{nights:2},dayVariants:[3],
  budgets:[{l:'宽松',v:1500},{l:'精打细算',v:1350}],
  title:'🌊 青岛 3 天 · 红瓦绿树与啤酒',meta:'山东青岛 · 3天2晚 · 地铁公交',
  why:'青岛把德国人留下的老城和海摞在一起：D1 栈桥看完往八大关走，十条路各种一种树，傍晚第二海水浴场看日落；D2 一整天给崂山，山直接扎进海里；D3 啤酒博物馆喝一杯刚下线的原浆，中山路的教堂收尾。',
  hero1v:'0<small>km</small>',hero1k:'地铁公交步行',
  strength:'中',overTip:'可换台东地铁口',
  weather:'青岛 8 月 · 昼 24–29℃ · 海风凉爽 · 崂山雾大',
  tixLabel:'门票与索道',foodLabel:'餐饮 · 含海鲜',carLabel:'地铁 · 公交（每人实付）',
  tastes:[
   {id:'nature',label:'山水控',apply(){ addP('海岸线控'); }},
   {id:'geo',   label:'山水控',apply(){ addP('海岸线控'); }},
   {id:'food',  label:'美食控',apply(){ addP('海鲜与原浆'); }},
   {id:'photo', label:'拍照控',apply(){ addP('老别墅机位'); }},
   {id:'art',   label:'历史控',apply(){ addP('德式建筑细看'); }},
   {id:'hike',  label:'走走走',apply(){ addP('崂山走全程'); }}],
  defSels:{}, defSelsM:[],
  seasons:[{in:true,name:'崂山天气',why:'雨雾天封山 · 出发前查景区公告',tag:'已排入 D2',ver:1},
   {in:false,name:'海鸥季',why:'11 月至次年 4 月栈桥有海鸥 · 本次未到季',pick:{key:'qd-gull',name:'栈桥海鸥',ptext:'观鸟控'}}],
  extras:[{later:{key:'qd-xiaoyushan',name:'小鱼山看红瓦',why:'老城制高点 · 需另半天',ptext:'拍照控'}}],
  extrasSub:'备着的还有 玩 19 · 吃 26 · 住 14',
  todos(){ return [
   {k:'laoshan',tag:['down','天气'],text:'崂山雨雾天封山 · 出发前查景区公告',v:''},
   {k:'metro',tag:['','支付'],text:'琴岛通或支付宝乘车码 · 地铁公交通用',v:''},
   {k:'beer',tag:['','提示'],text:'啤酒博物馆门票含原浆一杯 · 隔壁啤酒街可续',v:''},
   {k:'shoe',tag:['','装备'],text:'崂山台阶多且湿滑 · 穿防滑鞋',v:''}]; },
  map:{nodes:QD_NODES,order:[0,1,2],loop:true,
   seg:[[0,1],[0,2,0],null],tonight:[0,0,-1]}}),

 wh3:normRoute({
  name:'武汉 · 江城与东湖',dest:'湖北 · 武汉',fam:'wh',
  days:WH3_DAYS,lodges:WH3_LODGES,
  transport:{mode:'transit',rent:0,perCar:false,roadfood:0,label:'地铁 · 轮渡（每人实付）'},
  locale:{region:'domestic',country:'中国',navApp:'amap',currencyNote:null},
  stay:{nights:2},dayVariants:[3],
  budgets:[{l:'宽松',v:1300},{l:'精打细算',v:1180}],
  title:'🌉 武汉 3 天 · 江城与东湖',meta:'湖北武汉 · 3天2晚 · 地铁轮渡',
  why:'武汉是被两条江切成三块的城：D1 黄鹤楼登顶看长江大桥，户部巷过早，夜里坐 1.5 元的轮渡过江；D2 东湖绿道租车骑一段（湖面比西湖大六倍），拐去武大看老斋舍；D3 省博看曾侯乙编钟，昙华林收尾。',
  hero1v:'0<small>km</small>',hero1k:'地铁轮渡单车',
  strength:'中',overTip:'可换汉口江滩边',
  weather:'武汉 8 月 · 昼 30–37℃ · 火炉之首 · 江边有风',
  tixLabel:'门票与单车',foodLabel:'餐饮 · 含过早',carLabel:'地铁 · 轮渡（每人实付）',
  tastes:[
   {id:'nature',label:'山水控',apply(){ addP('江湖控'); }},
   {id:'geo',   label:'山水控',apply(){ addP('江湖控'); }},
   {id:'art',   label:'历史控',apply(){ addP('编钟细看派'); }},
   {id:'food',  label:'美食控',apply(){ addP('过早不将就'); }},
   {id:'photo', label:'拍照控',apply(){ addP('两江机位'); }},
   {id:'chill', label:'躺平型',apply(){ addP('江滩多坐一会儿'); }}],
  defSels:{}, defSelsM:[],
  seasons:[{in:true,name:'省博预约',why:'免费但需提前 3 天预约 · 周一闭馆',tag:'已排入 D3',ver:1},
   {in:false,name:'武大樱花',why:'3 月中下旬 · 需专门预约 · 本次未到季',pick:{key:'wh-sakura',name:'武大樱花',ptext:'花季控'}}],
  extras:[{later:{key:'wh-hanjie',name:'楚河汉街',why:'城中 · 需另半天',ptext:'逛街控'}}],
  extrasSub:'备着的还有 玩 22 · 吃 30 · 住 15',
  todos(){ return [
   {k:'museum',tag:['down','预约'],text:'湖北省博提前 3 天预约 · 周一闭馆',v:'',url:'https://www.hbww.org'},
   {k:'ferry',tag:['','体验'],text:'武汉关轮渡 ¥1.5 · 夜里过江看灯光秀',v:''},
   {k:'metro',tag:['','支付'],text:'武汉地铁支付宝乘车码 · 全线通用',v:''},
   {k:'heat',tag:['down','天气'],text:'夏天酷热 · 东湖骑行避开正午',v:''}]; },
  map:{nodes:WH_NODES,order:[0,1,2],loop:true,
   seg:[[0,2,0],[0,1,0],null],tonight:[0,0,-1]}}),

 cs3:normRoute({
  name:'长沙 · 橘子洲与夜宵',dest:'湖南 · 长沙',fam:'cs',
  days:CS3_DAYS,lodges:CS3_LODGES,
  transport:{mode:'transit',rent:0,perCar:false,roadfood:0,label:'地铁 · 步行（每人实付）'},
  locale:{region:'domestic',country:'中国',navApp:'amap',currencyNote:null},
  stay:{nights:2},dayVariants:[3],
  budgets:[{l:'宽松',v:1200},{l:'精打细算',v:1080}],
  title:'🌶 长沙 3 天 · 橘子洲与夜宵',meta:'湖南长沙 · 3天2晚 · 地铁步行',
  why:'长沙的白天在山上，夜里在街上：D1 橘子洲看完过江上岳麓山，书院那块「实事求是」的匾挂了一百年；D2 太平街吃到文和友，夜里再来一盆口味虾；D3 省博看马王堆那件 49 克的素纱襌衣，中午走人。',
  hero1v:'0<small>km</small>',hero1k:'地铁步行',
  strength:'轻',overTip:'可换岳麓区大学城',
  weather:'长沙 8 月 · 昼 30–37℃ · 闷热 · 夜里街上凉快',
  tixLabel:'门票与观光车',foodLabel:'餐饮 · 含夜宵',carLabel:'地铁 · 步行（每人实付）',
  tastes:[
   {id:'food',  label:'美食控',apply(){ sels['cs-food']=0; addP('夜宵不将就'); }},
   {id:'art',   label:'历史控',apply(){ addP('马王堆细看派'); }},
   {id:'folk',  label:'人文控',apply(){ addP('市井夜生活'); }},
   {id:'photo', label:'拍照控',apply(){ addP('江洲机位'); }},
   {id:'hike',  label:'走走走',apply(){ addP('岳麓山走上去'); }}],
  defSels:{'cs-food':1}, defSelsM:[],
  seasons:[{in:true,name:'省博预约',why:'免费但需提前 7 天预约 · 周一闭馆',tag:'已排入 D3',ver:1},
   {in:false,name:'岳麓山红叶',why:'11 月中下旬爱晚亭最好 · 本次未到季',pick:{key:'cs-maple',name:'爱晚亭红叶',ptext:'秋色控'}}],
  extras:[{later:{key:'cs-tongguan',name:'铜官窑古镇',why:'城北 · 需另一天',ptext:'古镇控'}}],
  extrasSub:'备着的还有 玩 18 · 吃 34 · 住 13',
  todos(){ return [
   {k:'museum',tag:['down','预约'],text:'湖南博物院提前 7 天预约 · 周一闭馆',v:'',url:'https://www.hnmuseum.com'},
   {k:'wenheyou',tag:['down','排队'],text:'文和友周末排队 2 小时 · 提前线上取号',v:''},
   {k:'metro',tag:['','支付'],text:'长沙地铁支付宝乘车码 · 全线通用',v:''},
   {k:'spicy',tag:['','提示'],text:'长沙的微辣≈别处的中辣 · 点单说清楚',v:''}]; },
  map:{nodes:CS_NODES,order:[0,1,2],loop:true,
   seg:[[0,1,0],null,[0,2,0]],tonight:[0,0,-1]}}),

 gz5:normRoute({
  name:'贵州 · 苗寨与瀑布',dest:'贵州 · 黔东南环线',fam:'gz',
  days:GZ5_DAYS,lodges:GZ5_LODGES,
  transport:{mode:'drive',rent:2800,perCar:true,roadfood:320,label:'包车 · 油费路桥（按车均摊）'},
  locale:{region:'domestic',country:'中国',navApp:'amap',currencyNote:null},
  stay:{nights:4},dayVariants:[5],
  budgets:[{l:'宽松',v:4550},{l:'精打细算',v:4050}],
  title:'🪘 贵州 5 天 · 苗寨与瀑布',meta:'贵州 · 5天4晚 · 包车环线',
  why:'贵州的好东西都在山里，得包车：D1 落地先去青岩古镇吃只状元蹄；D2 进西江千户苗寨，天黑后整面山坡的吊脚楼灯全亮；D3 转场荔波，小七孔的水上森林能踩着石头蹚水走；D4 黄果树穿水帘洞，从瀑布背面看出去；D5 一碗酸汤鱼收尾。',
  hero1v:'870<small>km</small>',hero1k:'包车环线',
  strength:'中',overTip:'可换西江寨口民宿',
  weather:'贵州 8 月 · 昼 22–30℃ · 十天九雨 · 山路多弯',
  tixLabel:'门票与观光车',foodLabel:'餐饮 · 含长桌宴',carLabel:'包车 · 油费路桥（按车均摊）',
  tastes:[
   {id:'folk',  label:'人文控',apply(){ addP('苗寨生活控'); }},
   {id:'nature',label:'山水控',apply(){ addP('瀑布与水森林'); }},
   {id:'geo',   label:'山水控',apply(){ addP('瀑布与水森林'); }},
   {id:'photo', label:'拍照控',apply(){ addP('苗寨夜景机位'); }},
   {id:'food',  label:'美食控',apply(){ addP('酸汤不将就'); }},
   {id:'hike',  label:'走走走',apply(){ addP('小七孔走全程'); }}],
  defSels:{}, defSelsM:[],
  seasons:[{in:true,name:'苗寨夜景',why:'天黑后吊脚楼灯全开 · 需住寨内或晚走',tag:'已排入 D2',ver:1},
   {in:true,name:'黄果树丰水期',why:'6-9 月水量最大 · 水帘洞必湿身',tag:'已排入 D4',ver:0},
   {in:false,name:'加榜梯田',why:'从江方向 · 需另加两天',pick:{key:'gz-jiabang',name:'加榜梯田',ptext:'梯田控'}}],
  extras:[{later:{key:'gz-zhaoxing',name:'肇兴侗寨',why:'黎平方向 · 需另一天',ptext:'侗寨控'}}],
  extrasSub:'备着的还有 玩 21 · 吃 27 · 住 18',
  todos(){ return [
   {k:'car',tag:['down','包车'],text:'山路多弯建议包车 · 提前谈好每日里程上限',v:''},
   {k:'rain',tag:['down','天气'],text:'贵州十天九雨 · 雨衣防滑鞋必备',v:''},
   {k:'xijiang',tag:['','住宿'],text:'想看夜景须住寨内或晚走 · 观景房提前订',v:''},
   {k:'waterfall',tag:['','装备'],text:'黄果树水帘洞必湿身 · 备换洗与防水袋',v:''}]; },
  map:{nodes:GZ_NODES,order:[0,1,2,3],loop:true,
   seg:[null,[0,1],[1,2],[2,3],[3,0]],tonight:[0,1,2,3,-1]}}),
 sz3:normRoute({
  name:'苏州 · 园林与老街',dest:'江苏 · 苏州',fam:'sz',
  days:SZ3_DAYS,lodges:SZ3_LODGES,
  transport:{mode:'transit',rent:0,perCar:false,roadfood:0,label:'地铁 · 步行（每人实付）'},
  locale:{region:'domestic',country:'中国',navApp:'amap',currencyNote:null},
  stay:{nights:2},dayVariants:[3],
  budgets:[{l:'宽松',v:1400},{l:'精打细算',v:1250}],
  title:'🏯 苏州 3 天 · 园林与平江路',meta:'江苏苏州 · 3天2晚 · 地铁步行',
  why:'苏州的节奏本来就慢：D1 八点半开园就进拙政园（十点后人挤人），下午泡平江路听段评弹；D2 虎丘看斜了一千年的塔，晚上山塘街坐船；D3 苏博看贝聿铭那面片石假山，观前街买点糖走人。',
  hero1v:'0<small>km</small>',hero1k:'地铁步行',
  strength:'轻',overTip:'可换观前街地铁口',
  weather:'苏州 8 月 · 昼 28–35℃ · 闷热多雨 · 园林里阴凉',
  tixLabel:'门票与船票',foodLabel:'餐饮 · 含苏帮菜',carLabel:'地铁 · 公交（每人实付）',
  tastes:[
   {id:'art',   label:'历史控',apply(){ addP('园林细看派'); }},
   {id:'photo', label:'拍照控',apply(){ addP('框景机位'); }},
   {id:'food',  label:'美食控',apply(){ sels['sz-food']=0; addP('苏帮菜不将就'); }},
   {id:'chill', label:'躺平型',apply(){ addP('园中多坐一会儿'); }},
   {id:'folk',  label:'人文控',apply(){ addP('评弹与老街'); }}],
  defSels:{'sz-food':1}, defSelsM:[],
  seasons:[{in:true,name:'苏博预约',why:'免费但需提前 3 天官网预约 · 周一闭馆',tag:'已排入 D3',ver:1},
   {in:true,name:'拙政园早场',why:'8:30 开园就进 · 十点后人挤人',tag:'已排入 D1',ver:0},
   {in:false,name:'留园与网师园夜花园',why:'需另半天 · 夜花园 3-11 月开放',pick:{key:'sz-liuyuan',name:'留园',ptext:'园林控'}}],
  extras:[{later:{key:'sz-tongli',name:'同里古镇',why:'城南 · 需另一天',ptext:'水乡控'}}],
  extrasSub:'备着的还有 玩 23 · 吃 31 · 住 16',
  todos(){ return [
   {k:'museum',tag:['down','预约'],text:'苏州博物馆提前 3 天官网预约 · 周一闭馆',v:'',url:'https://www.szmuseum.com'},
   {k:'garden',tag:['down','预约'],text:'拙政园需实名预约 · 建议订 8:30 首场',v:'',url:'https://www.szzzy.cn'},
   {k:'metro',tag:['','支付'],text:'苏 e 行或支付宝乘车码 · 地铁公交通用',v:''},
   {k:'rain',tag:['','装备'],text:'江南夏天午后雷阵雨 · 折伞随身',v:''}]; },
  map:{nodes:SZ_NODES,order:[0,1,2],loop:true,
   seg:[[0,1,0],[0,2,0],null],tonight:[0,0,-1]}}),

 nj3:normRoute({
  name:'南京 · 六朝与民国',dest:'江苏 · 南京',fam:'nj',
  days:NJ3_DAYS,lodges:NJ3_LODGES,
  transport:{mode:'transit',rent:0,perCar:false,roadfood:0,label:'地铁 · 观光车（每人实付）'},
  locale:{region:'domestic',country:'中国',navApp:'amap',currencyNote:null},
  stay:{nights:2},dayVariants:[3],
  budgets:[{l:'宽松',v:1400},{l:'精打细算',v:1250}],
  title:'🏛 南京 3 天 · 六朝与民国',meta:'江苏南京 · 3天2晚 · 地铁直达',
  why:'南京把六百年摞在一座城里：D1 钟山上走完中山陵 392 级台阶，接明孝陵的石象路神道；D2 夫子庙看秦淮河的夜灯，转去老门东的城墙根；D3 颐和路的梧桐和民国小楼，总统府一座院子装了三个朝代。',
  hero1v:'0<small>km</small>',hero1k:'地铁观光车',
  strength:'中',overTip:'可换夫子庙老城南',
  weather:'南京 8 月 · 昼 29–36℃ · 火炉之一 · 钟山有荫',
  tixLabel:'门票与观光车',foodLabel:'餐饮 · 含盐水鸭',carLabel:'地铁 · 观光车（每人实付）',
  tastes:[
   {id:'art',   label:'历史控',apply(){ addP('六朝细看派'); }},
   {id:'photo', label:'拍照控',apply(){ addP('梧桐与神道机位'); }},
   {id:'food',  label:'美食控',apply(){ addP('鸭子不将就'); }},
   {id:'hike',  label:'走走走',apply(){ addP('钟山走全程'); }},
   {id:'folk',  label:'人文控',apply(){ addP('老城南生活'); }}],
  defSels:{}, defSelsM:[],
  seasons:[{in:true,name:'中山陵预约',why:'免费但需提前预约 · 周一维护闭馆',tag:'已排入 D1',ver:1},
   {in:false,name:'石象路落叶季',why:'11 月中下旬满地梧桐叶 · 本次未到季',pick:{key:'nj-leaf',name:'石象路秋色',ptext:'秋色控'}}],
  extras:[{later:{key:'nj-qixia',name:'栖霞山红叶',why:'城东北 · 需另半天',ptext:'秋色控'}}],
  extrasSub:'备着的还有 玩 21 · 吃 28 · 住 15',
  todos(){ return [
   {k:'zhongshan',tag:['down','预约'],text:'中山陵需提前预约 · 周一维护闭馆',v:'',url:'https://www.zschina.org.cn'},
   {k:'palace',tag:['down','闭馆'],text:'总统府周一闭馆 · 提前查开放时间',v:'',url:'https://www.njztf.cn'},
   {k:'metro',tag:['','支付'],text:'南京地铁支付宝乘车码 · 全线通用',v:''},
   {k:'walk',tag:['','装备'],text:'中山陵 392 级台阶 · 穿好走的鞋',v:'',url:'https://www.zschina.org.cn'}]; },
  map:{nodes:NJ_NODES,order:[0,1,2],loop:true,
   seg:[[0,1,0],null,[0,2,0]],tonight:[0,0,-1]}}),
 hz3:normRoute({
  name:'杭州 · 西湖与龙井',dest:'浙江 · 杭州',fam:'hz',
  days:HZ3_DAYS,lodges:HZ3_LODGES,
  transport:{mode:'transit',rent:0,perCar:false,roadfood:0,label:'地铁 · 公交（每人实付）'},
  locale:{region:'domestic',country:'中国',navApp:'amap',currencyNote:null},
  stay:{nights:2},dayVariants:[3],
  budgets:[{l:'宽松',v:1400},{l:'精打细算',v:1250}],
  title:'🌿 杭州 3 天 · 西湖与龙井',meta:'浙江杭州 · 3天2晚 · 地铁公交',
  why:'杭州三天不用赶：D1 沿断桥白堤走到苏堤，傍晚上雷峰塔看日落；D2 整天在山里，灵隐寺的宋代石窟接龙井村的茶园；D3 河坊街买特产、拱宸桥看运河，中午吃碗片儿川走人。',
  hero1v:'0<small>km</small>',hero1k:'地铁公交步行',
  strength:'中',overTip:'可换武林广场地铁口',
  weather:'杭州 8 月 · 昼 29–36℃ · 闷热多雨 · 环湖遮阴少',
  tixLabel:'门票与茶位',foodLabel:'餐饮 · 含杭帮菜',carLabel:'地铁 · 公交（每人实付）',
  tastes:[
   {id:'nature',label:'山水控',apply(){ addP('湖山慢走派'); }},
   {id:'geo',   label:'山水控',apply(){ addP('湖山慢走派'); }},
   {id:'art',   label:'历史控',apply(){ addP('古寺细看派'); }},
   {id:'food',  label:'美食控',apply(){ sels['hz-food']=0; addP('杭帮菜不将就'); }},
   {id:'photo', label:'拍照控',apply(){ addP('断桥晨光机位'); }},
   {id:'chill', label:'躺平型',apply(){ addP('茶园多坐一会儿'); }}],
  defSels:{'hz-food':1}, defSelsM:[],
  seasons:[{in:true,name:'荷花季',why:'6-8 月曲院风荷开满',tag:'沿苏堤可见',ver:0},
   {in:false,name:'桂花与秋茶',why:'9 月下旬满城桂香 · 本次未到季',pick:{key:'hz-osmanthus',name:'满觉陇赏桂',ptext:'花香控'}}],
  extras:[{later:{key:'hz-xixi',name:'西溪湿地',why:'城西 · 需另半天',ptext:'湿地控'}}],
  extrasSub:'备着的还有 玩 21 · 吃 29 · 住 14',
  todos(){ return [
   {k:'lingyin',tag:['down','预约'],text:'灵隐寺旺季需提前预约 · 景区与寺院两道票',v:'',url:'https://www.lingyinsi.org'},
   {k:'metro',tag:['','支付'],text:'杭州地铁支付宝乘车码 · 公交同样可扫',v:''},
   {k:'bike',tag:['','装备'],text:'环湖建议租共享单车 · 苏堤全长 2.8 km',v:''},
   {k:'sun',tag:['','装备'],text:'夏天环湖遮阴少 · 帽子和水必备',v:''}]; },
  map:{nodes:HZ_NODES,order:[0,1,2],loop:true,
   seg:[null,[0,1,0],[0,2]],tonight:[0,0,-1]}}),

 cq3:normRoute({
  name:'重庆 · 山城立体',dest:'重庆',fam:'cq',
  days:CQ3_DAYS,lodges:CQ3_LODGES,
  transport:{mode:'transit',rent:0,perCar:false,roadfood:0,label:'轻轨 · 索道 · 步行（每人实付）'},
  locale:{region:'domestic',country:'中国',navApp:'amap',currencyNote:null},
  stay:{nights:2},dayVariants:[3],
  budgets:[{l:'宽松',v:1400},{l:'精打细算',v:1250}],
  title:'🌉 重庆 3 天 · 山城立体',meta:'重庆 · 3天2晚 · 轻轨索道',
  why:'重庆要按立体走：D1 解放碑逛完坐长江索道过江，天黑回洪崖洞看灯全开；D2 磁器口的石板路接鹅岭二厂的天台日落；D3 李子坝看轻轨钻楼，山城步道从崖壁上走一段。三天全靠轻轨，别开车——这里的导航会骗人。',
  hero1v:'0<small>km</small>',hero1k:'轻轨索道步行',
  strength:'中',overTip:'可换观音桥地铁口',
  weather:'重庆 8 月 · 昼 30–38℃ · 火炉城市 · 夜里才凉',
  tixLabel:'索道与门票',foodLabel:'餐饮 · 含火锅',carLabel:'轻轨 · 索道（每人实付）',
  tastes:[
   {id:'food',  label:'美食控',apply(){ sels['cq-hg']=0; addP('火锅不将就'); }},
   {id:'photo', label:'拍照控',apply(){ addP('洪崖洞夜景机位'); }},
   {id:'folk',  label:'人文控',apply(){ addP('山城生活控'); }},
   {id:'hike',  label:'走走走',apply(){ addP('步道走全程'); }},
   {id:'art',   label:'历史控',apply(){ addP('古镇细看派'); }}],
  defSels:{'cq-hg':1}, defSelsM:[],
  seasons:[{in:true,name:'洪崖洞灯光',why:'19:00 后全开 · 周末人流管制',tag:'已排入 D1',ver:1},
   {in:false,name:'武隆天生三桥',why:'需另加两天 · 车程 3 小时',pick:{key:'cq-wulong',name:'武隆喀斯特',ptext:'地质控'}}],
  extras:[{later:{key:'cq-baigongguan',name:'白公馆渣滓洞',why:'歌乐山 · 需另半天',ptext:'历史控'}}],
  extrasSub:'备着的还有 玩 24 · 吃 35 · 住 16',
  todos(){ return [
   {k:'suodao',tag:['down','排队'],text:'长江索道旺季排队 40 分 · 网上买票走快速通道',v:''},
   {k:'metro',tag:['','支付'],text:'渝畅行或云闪付扫码 · 轻轨全线通用',v:''},
   {k:'nav',tag:['down','避坑'],text:'重庆导航会骗人 · 认楼层不认平面距离',v:''},
   {k:'shoe',tag:['','装备'],text:'台阶多坡度大 · 穿好走的鞋',v:''}]; },
  map:{nodes:CQ_NODES,order:[0,1,2],loop:true,
   seg:[null,[0,1,0],[0,2]],tonight:[0,0,-1]}}),

 xm3:normRoute({
  name:'厦门 · 鼓浪屿与环岛路',dest:'福建 · 厦门',fam:'xm',
  days:XM3_DAYS,lodges:XM3_LODGES,
  transport:{mode:'transit',rent:0,perCar:false,roadfood:0,label:'轮渡 · 公交 · 单车（每人实付）'},
  locale:{region:'domestic',country:'中国',navApp:'amap',currencyNote:null},
  stay:{nights:2},dayVariants:[3],
  budgets:[{l:'宽松',v:1500},{l:'精打细算',v:1350}],
  title:'🏝 厦门 3 天 · 鼓浪屿与环岛路',meta:'福建厦门 · 3天2晚 · 轮渡公交',
  why:'厦门三天分三块：D1 一整天给鼓浪屿，早班船进岛先冲日光岩，之后往小巷里钻看老别墅；D2 环岛路租车骑到椰风寨，傍晚曾厝垵吃海蛎煎、沙坡尾看渔船；D3 南普陀接厦大芙蓉隧道，走之前一碗沙茶面。',
  hero1v:'0<small>km</small>',hero1k:'轮渡公交单车',
  strength:'中',overTip:'可换曾厝垵民宿',
  weather:'厦门 8 月 · 昼 28–34℃ · 海风大 · 需防台风',
  tixLabel:'门票与轮渡',foodLabel:'餐饮 · 含海鲜',carLabel:'轮渡 · 公交（每人实付）',
  tastes:[
   {id:'nature',label:'山水控',apply(){ addP('海岸线控'); }},
   {id:'geo',   label:'山水控',apply(){ addP('海岸线控'); }},
   {id:'food',  label:'美食控',apply(){ addP('海鲜不将就'); }},
   {id:'photo', label:'拍照控',apply(){ addP('红顶老别墅机位'); }},
   {id:'chill', label:'躺平型',apply(){ addP('海边多坐一会儿'); }},
   {id:'art',   label:'历史控',apply(){ addP('万国建筑细看'); }}],
  defSels:{}, defSelsM:[],
  seasons:[{in:true,name:'厦大预约',why:'需提前 3 天官微预约入校',tag:'已排入 D3',ver:1},
   {in:false,name:'台风季',why:'7-9 月轮渡可能停航 · 出发前查公告',pick:{key:'xm-typhoon',name:'避开台风',ptext:'稳妥派'}}],
  extras:[{later:{key:'xm-yundang',name:'筼筜湖白鹭',why:'市中心 · 需另半天',ptext:'观鸟控'}}],
  extrasSub:'备着的还有 玩 20 · 吃 27 · 住 13',
  todos(){ return [
   {k:'ferry',tag:['down','订票'],text:'游客须从东渡码头进岛 · 提前网上订轮渡票',v:''},
   {k:'xmu',tag:['down','预约'],text:'厦门大学提前 3 天官微预约入校',v:'',url:'https://www.xmu.edu.cn'},
   {k:'typhoon',tag:['down','天气'],text:'7-9 月台风季 · 出发前查轮渡停航公告',v:''},
   {k:'sun',tag:['','装备'],text:'环岛路无遮阴 · 防晒和水必备',v:''}]; },
  map:{nodes:XM_NODES,order:[0,1,2],loop:true,
   seg:[[0,1,0],[0,2],null],tonight:[0,0,-1]}}),

 sy4:normRoute({
  name:'三亚 · 海岛慢走',dest:'海南 · 三亚',fam:'sy',
  days:SY4_DAYS,lodges:SY4_LODGES,
  transport:{mode:'transit',rent:0,perCar:false,roadfood:0,label:'打车 · 景区专线（每人实付）'},
  locale:{region:'domestic',country:'中国',navApp:'amap',currencyNote:null},
  stay:{nights:3},dayVariants:[4],
  budgets:[{l:'宽松',v:2700},{l:'精打细算',v:2400}],
  title:'🏖 三亚 4 天 · 海岛慢走',meta:'海南三亚 · 4天3晚 · 不含机票',
  why:'三亚不用赶景点：D1 落地先下海，第一市场挑海鲜现做；D2 一整天蜈支洲岛，这里的水下能见度是三亚最好的；D3 上午泡亚龙湾的白沙滩，下午天涯海角打个卡；D4 南山看海上观音，中午飞走。住宿前两晚在市区吃饭方便，后两晚换到亚龙湾推门就是沙滩。',
  hero1v:'3<small>片海</small>',hero1k:'两湾一岛',
  strength:'轻',overTip:'可换市区商圈',
  weather:'三亚 8 月 · 昼 28–33℃ · 紫外线全年最强 · 注意台风',
  tixLabel:'门票与船票',foodLabel:'餐饮 · 含海鲜',carLabel:'打车 · 机场线（每人实付）',
  tastes:[
   {id:'nature',label:'山水控',apply(){ addP('海岛控'); }},
   {id:'geo',   label:'山水控',apply(){ addP('海岛控'); }},
   {id:'chill', label:'躺平型',apply(){ addP('沙滩躺平派'); }},
   {id:'food',  label:'美食控',apply(){ addP('海鲜不将就'); }},
   {id:'photo', label:'拍照控',apply(){ addP('白沙滩机位'); }},
   {id:'art',   label:'历史控',apply(){ addP('南山细看派'); }}],
  defSels:{}, defSelsM:[],
  seasons:[{in:true,name:'蜈支洲订票',why:'旺季提前 3 天 · 早班船进岛人少',tag:'已排入 D2',ver:1},
   {in:false,name:'避开水母季',why:'6-9 月大东海偶有水母 · 下水前问救生员',pick:{key:'sy-jelly',name:'水母季提醒',ptext:'稳妥派'}}],
  extras:[{later:{key:'sy-yanoda',name:'呀诺达雨林',why:'保亭方向 · 需另一天',ptext:'雨林控'}}],
  extrasSub:'备着的还有 玩 18 · 吃 24 · 住 21',
  todos(){ return [
   {k:'wuzhi',tag:['down','订票'],text:'蜈支洲岛旺季提前 3 天订票 · 订早班船',v:'',url:'https://www.wuzhizhou.com'},
   {k:'seafood',tag:['down','避坑'],text:'第一市场认明码标价摊位 · 加工费先问清',v:''},
   {k:'sun',tag:['','装备'],text:'紫外线全年最强 · 防晒霜每两小时补一次',v:''},
   {k:'typhoon',tag:['down','天气'],text:'8-10 月台风季 · 出发前查航班与船班',v:''}]; },
  map:{nodes:SY_NODES,order:[0,1,2,3],loop:true,
   seg:[null,[0,1,2],[2,3,2],[2,0]],tonight:[0,2,2,-1]}}),
 sh3:normRoute({
  name:'上海 · 外滩到梧桐区',dest:'上海',fam:'sh',
  days:SH3_DAYS,lodges:SH3_LODGES,
  transport:{mode:'transit',rent:0,perCar:false,roadfood:0,label:'地铁 · 步行（每人实付）'},
  locale:{region:'domestic',country:'中国',navApp:'amap',currencyNote:null},
  stay:{nights:2},
  dayVariants:[3],
  budgets:[{l:'宽松',v:1500},{l:'精打细算',v:1350}],
  title:'🌆 上海 3 天 · 外滩到梧桐区',meta:'上海 · 3天2晚 · 全程地铁',
  why:'上海分两面走：D1 豫园老园林接南京路，天黑前站上外滩看对岸亮灯；D2 一整天泡在梧桐区，武康大楼、安福路咖啡、田子坊弄堂；D3 上海博物馆看青铜器，陆家嘴天桥收尾。三天全靠地铁，不用打车。',
  hero1v:'0<small>km</small>',hero1k:'全程地铁步行',
  strength:'轻',overTip:'可换徐家汇地铁口',
  weather:'上海 8 月 · 昼 28–35℃ · 湿度大体感闷 · 午后雷阵雨',
  tixLabel:'门票与登顶',foodLabel:'餐饮 · 含本帮菜',carLabel:'地铁 · 机场线（每人实付）',
  tastes:[
   {id:'photo', label:'拍照控',apply(){ addP('武康大楼机位'); }},
   {id:'food',  label:'美食控',apply(){ sels['sh-food']=0; addP('本帮菜不将就'); }},
   {id:'art',   label:'历史控',apply(){ addP('博物馆细看派'); }},
   {id:'folk',  label:'人文控',apply(){ addP('弄堂生活控'); }},
   {id:'chill', label:'躺平型',apply(){ addP('咖啡馆多坐一会儿'); }}],
  defSels:{'sh-food':1}, defSelsM:[],
  seasons:[{in:true,name:'外滩灯光',why:'18:30 后全开 · 天气好才亮',tag:'已排入 D1',ver:0},
   {in:true,name:'上博预约',why:'免费但需提前 1 天官微预约 · 周一闭馆',tag:'已排入 D3',ver:1},
   {in:false,name:'梧桐区落叶季',why:'11 月中下旬不扫落叶 · 本次未到季',pick:{key:'sh-leaf',name:'落叶不扫',ptext:'秋色控'}}],
  extras:[{later:{key:'sh-zhujiajiao',name:'朱家角水乡',why:'地铁 17 号线终点 · 需另半天',ptext:'水乡控'}}],
  extrasSub:'备着的还有 玩 26 · 吃 38 · 住 19',
  todos(){ return [
   {k:'museum',tag:['down','预约'],text:'上海博物馆提前 1 天官微预约 · 周一闭馆',v:'',url:'https://www.shanghaimuseum.net'},
   {k:'metro',tag:['','支付'],text:'Metro 大都会或云闪付扫码 · 地铁全线通用',v:''},
   {k:'wukang',tag:['','避峰'],text:'武康大楼周末路口人挤人 · 工作日或早上去',v:''},
   {k:'rain',tag:['','装备'],text:'上海夏天午后雷阵雨 · 折伞随身',v:''}]; },
  map:{nodes:SH_NODES,order:[0,1,2],loop:true,
   seg:[null,[0,1],[0,2]],tonight:[0,0,-1]}}),
 bj4:normRoute({
  name:'北京 · 中轴线与长城',dest:'北京',fam:'bj',
  days:BJ4_DAYS,lodges:BJ4_LODGES,
  transport:{mode:'transit',rent:0,perCar:false,roadfood:0,label:'地铁 · 公交（每人实付）'},
  locale:{region:'domestic',country:'中国',navApp:'amap',currencyNote:null},
  stay:{nights:3},
  dayVariants:[4],
  budgets:[{l:'宽松',v:2200},{l:'精打细算',v:1950}],
  title:'🏛 北京 4 天 · 中轴线与长城',meta:'北京 · 4天3晚 · 全程地铁公交',
  why:'四天按中轴线铺开：D1 故宫走到底再上景山看日落全景，D2 一整天给慕田峪长城（比八达岭安静一半），D3 颐和园长廊接什刹海胡同和烤鸭，D4 天坛祈年殿收尾。故宫和长城都不用包车，地铁公交直达。',
  hero1v:'0<small>km</small>',hero1k:'全程地铁公交',
  strength:'中',overTip:'可换南锣鼓巷青旅',
  weather:'北京 8 月 · 昼 26–33℃ · 午后偶雷阵雨 · 长城段风大',
  tixLabel:'门票与缆车',foodLabel:'餐饮 · 含烤鸭',carLabel:'地铁 · 长城专线（每人实付）',
  tastes:[
   {id:'art',   label:'历史控',apply(){ addP('中轴线细看派'); }},
   {id:'photo', label:'拍照控',apply(){ addP('景山日落机位'); }},
   {id:'food',  label:'美食控',apply(){ sels['bj-yakao']=0; addP('烤鸭不将就'); }},
   {id:'folk',  label:'人文控',apply(){ addP('胡同生活控'); }},
   {id:'hike',  label:'走走走',apply(){ addP('长城走远段'); }}],
  defSels:{'bj-yakao':1}, defSelsM:[],
  seasons:[{in:true,name:'故宫放票',why:'官网提前 7 天 20:00 放票 · 秒光',tag:'已排入 D1',ver:1},
   {in:true,name:'景山日落',why:'紫禁城全景唯一机位 · 日落前占位',tag:'已排入 D1',ver:0},
   {in:false,name:'香山红叶',why:'10 月下旬至 11 月中 · 本次未到季',pick:{key:'bj-xiangshan',name:'香山红叶',ptext:'秋色控'}}],
  extras:[{later:{key:'bj-798',name:'798 艺术区',why:'东北四环 · 需另半天',ptext:'看展控'}}],
  extrasSub:'备着的还有 玩 34 · 吃 41 · 住 22',
  todos(){ return [
   {k:'gugong',tag:['down','抢票'],text:'故宫官网提前 7 天 20:00 放票 · 定闹钟',v:'',url:'https://gugong.ktmtech.cn'},
   {k:'tam',tag:['down','预约'],text:'天安门广场需提前一天预约 · 带身份证',v:''},
   {k:'metro',tag:['','支付'],text:'亿通行或云闪付扫码 · 地铁公交通用',v:''},
   {k:'wall',tag:['','装备'],text:'长城段风大 · 防晒和外套都要',v:''}]; },
  map:{nodes:BJ_NODES,order:[0,1,2,3],loop:true,
   seg:[[0,1],[0,2,0],[0,3,0],null],tonight:[0,0,0,-1]}}),
 xa3:normRoute({
  name:'西安 · 城墙兵马俑',dest:'陕西 · 西安',fam:'xa',
  days:XA3_DAYS,lodges:XA3_LODGES,
  transport:{mode:'transit',rent:0,perCar:false,roadfood:0,label:'地铁 · 公交（每人实付）'},
  locale:{region:'domestic',country:'中国',navApp:'amap',currencyNote:null},
  stay:{nights:2},
  dayVariants:[3],
  budgets:[{l:'宽松',v:1400},{l:'精打细算',v:1250}],
  title:'🏯 西安 3 天 · 城墙兵马俑与碳水',meta:'陕西西安 · 3天2晚 · 全程地铁',
  why:'西安把两千年摞在一条地铁线上：D1 傍晚骑一圈城墙再钻回民街，D2 上午兵马俑、晚上大唐不夜城，D3 陕历博看完何家村的金银器，大雁塔收尾。全程地铁，兵马俑也不用包车。',
  hero1v:'0<small>km</small>',hero1k:'全程地铁公交',
  strength:'轻',overTip:'可换小寨地铁口',
  weather:'西安 8 月 · 昼 27–36℃ · 干热少雨 · 城墙上无遮阳',
  tixLabel:'门票与单车',foodLabel:'餐饮 · 碳水三顿',carLabel:'地铁 · 公交（每人实付）',
  tastes:[
   {id:'history',label:'历史控',apply(){ addP('博物馆细看派'); }},
   {id:'art',   label:'历史控',apply(){ addP('博物馆细看派'); }},
   {id:'food',  label:'美食控',apply(){ sels['xa-food']=0; addP('碳水不将就'); }},
   {id:'folk',  label:'人文控',apply(){ addP('市井小吃控'); }},
   {id:'photo', label:'拍照控',apply(){ addP('城墙落日机位'); }}],
  defSels:{'xa-food':1}, defSelsM:[],
  seasons:[{in:true,name:'陕历博预约',why:'基本陈列免费 · 提前 3 天官微放票',tag:'已排入 D3',ver:1},
   {in:true,name:'城墙落日',why:'傍晚骑行不晒 · 日落打在砖上',tag:'已排入 D1',ver:0},
   {in:false,name:'华清池·长恨歌',why:'需另加半天与夜场票',pick:{key:'xa-huaqing',name:'华清池长恨歌',ptext:'演出控'}}],
  extras:[{later:{key:'xa-hanyang',name:'汉阳陵',why:'城北 · 需另半天',ptext:'考古控'}}],
  extrasSub:'备着的还有 玩 19 · 吃 26 · 住 11',
  todos(){ return [
   {k:'museum',tag:['down','预约'],text:'陕历博提前 3 天官微抢票 · 放票即秒光',v:'',url:'https://www.sxhm.com'},
   {k:'bmy',tag:['down','预约'],text:'兵马俑旺季提前 3 天实名预约',v:'',url:'https://www.bmy.com.cn'},
   {k:'metro',tag:['','支付'],text:'长安通乘车码或云闪付 · 地铁全线通用',v:''},
   {k:'sun',tag:['','装备'],text:'城墙上无遮阳 · 帽子和水必备',v:''}]; },
  map:{nodes:XA_NODES,order:[0,1,2],loop:true,
   seg:[null,[0,1,2],[0,2]],tonight:[0,0,-1]}}),
 cd3:normRoute({
  name:'成都 · 城市漫步',dest:'四川 · 成都',fam:'cd',
  days:CD3_DAYS,lodges:CD3_LODGES,
  transport:{mode:'transit',rent:0,perCar:false,roadfood:0,label:'地铁 · 步行（每人实付）'},
  locale:{region:'domestic',country:'中国',navApp:'amap',currencyNote:null},
  stay:{nights:2},
  dayVariants:[3],
  budgets:[{l:'宽松',v:1300},{l:'精打细算',v:1150}],
  title:'🐼 成都 3 天 · 茶馆熊猫和火锅',meta:'四川成都 · 3天2晚 · 全程地铁步行',
  why:'成都不用赶路：D1 宽窄巷子逛完在鹤鸣茶社躺一下午，D2 七点半冲熊猫基地（十点后它们就睡了）再看武侯祠红墙，D3 杜甫草堂收个尾，走之前一顿火锅。全程地铁，不用租车。',
  hero1v:'0<small>km</small>',hero1k:'全程地铁步行',
  strength:'轻',overTip:'可换宽窄巷子客栈',
  weather:'成都 8 月 · 昼 26–34℃ · 湿度大体感闷 · 阵雨随身伞',
  tixLabel:'门票与茶位',foodLabel:'餐饮 · 含火锅',carLabel:'地铁 · 接驳（每人实付）',
  tastes:[
   {id:'food',  label:'美食控',apply(){ sels['cd-hg']=0; addP('火锅不将就'); }},
   {id:'chill', label:'躺平型',apply(){ addP('茶馆多坐一会儿'); }},
   {id:'folk',  label:'人文控',apply(){ addP('市井生活控'); }},
   {id:'photo', label:'拍照控',apply(){ addP('红墙竹影机位'); }}],
  defSels:{'cd-hg':1}, defSelsM:[],
  seasons:[{in:true,name:'熊猫活跃时段',why:'早 7:30–10:00 最活跃 · 之后基本在睡',tag:'已排入 D2',ver:1},
   {in:false,name:'都江堰·青城山',why:'需另加一天 · 见「都江堰」线',pick:{key:'cd-djy',name:'都江堰一日',ptext:'古迹控'}}],
  extras:[{later:{key:'cd-yulin',name:'玉林路 · 小酒馆',why:'夜生活 · 本次排到太古里为止',ptext:'夜生活控'}}],
  extrasSub:'备着的还有 玩 22 · 吃 31 · 住 14',
  todos(){ return [
   {k:'panda',tag:['down','抢票'],text:'熊猫基地官微提前 7 天放票 · 旺季秒光',v:'',url:'https://www.panda.org.cn'},
   {k:'metro',tag:['','支付'],text:'天府通乘车码或云闪付 · 地铁全线通用',v:''},
   {k:'hotpot',tag:['','排队'],text:'热门火锅店提前 2 小时线上取号',v:''},
   {k:'umbrella',tag:['','装备'],text:'成都夏天阵雨多 · 折伞随身',v:''}]; },
  map:{nodes:CD_NODES,order:[0,1,2,3],loop:true,
   seg:[null,[0,1,2],[0,3]],tonight:[0,0,-1]}}),
 nm3:Object.assign({},ROUTES.nm4,{
  days:NM3_DAYS,lodges:NM3_LODGES,nights:2,rent:1600,roadfood:180,
  dayVariants:[3,4],
  budgets:[{l:'宽松',v:2200},{l:'精打细算',v:1950}],
  title:'🌾 额济纳 3 天 · 胡杨速通',meta:'内蒙古额济纳 · 3天2晚 · 10 月最佳',
  why:'三天版砍掉怪树林那天，把时间全给一二三道桥的金色胡杨和黑城的落日。周末加一天调休就能走完，金黄期只有一周，速通版更适合抢时间。',
  seasons:[{in:true,name:'胡杨金黄期',why:'10 月上旬约一周 · 过期只剩枯枝',tag:'已排入 D2',ver:1},
   {in:false,name:'怪树林日落',why:'需多住一晚 · 4 天版才排得下',pick:{key:'nm-ghost',name:'怪树林',ptext:'枯木控'},needDays:4}],
  map:{nodes:NM_NODES,order:[0,1],loop:true,seg:[[0,1],null,[1,0]],tonight:[1,1,-1]}}),

 kansai4:Object.assign({},ROUTES.kansai5,{
  days:KAN4_DAYS,lodges:KAN4_LODGES,nights:3,
  stay:{nights:3},
  dayVariants:[4,5],
  budgets:[{l:'宽松',v:2750},{l:'精打细算',v:2450}],
  title:'🇯🇵 日本·关西 4 天 · 大阪京都',meta:'日本关西 · 4天3晚 · 不含机票 · 周末加两天',
  why:'四天版不去奈良，大阪京都各给足一天：难波连住三晚不挪窝，电车往返最省心。第一次去关西、假期只有四天的话，这个密度刚好不赶。',
  i18n:{en:{name:'Kansai 4 Days',dest:'Japan · Osaka & Kyoto',
   title:'🇯🇵 Kansai, Japan · 4 days · Osaka & Kyoto',
   meta:'Kansai · 4d 3n · flights excluded',
   hero1k:'3 nights in Namba, zero repacking',
   why:'Four days, no Nara: a full day each for Osaka and Kyoto, three nights in Namba, trains both ways. The right density for a first Kansai trip on a short break.'}},
  seasons:[{in:true,name:'京都红叶',why:'11 月中下旬 · 清水寺夜间特别拜观',tag:'看当期',ver:0},
   {in:false,name:'奈良喂鹿',why:'需多半天 · 5 天版才排得下',pick:{key:'kan-nara',name:'奈良公园',ptext:'动物控'},needDays:5}],
  map:{nodes:KAN_NODES,order:[0,1,2,3],loop:false,
   seg:[[0,1],null,[1,2],[1,0]],tonight:[1,1,1,-1]}}),

 hk2:Object.assign({},ROUTES.hk3,{
  days:HK2_DAYS,lodges:HK2_LODGES,nights:1,
  stay:{nights:1},
  dayVariants:[2,3],
  budgets:[{l:'宽松',v:1150},{l:'精打细算',v:1000}],
  title:'🚢 香港周末 2 天 · 中环与山顶',meta:'香港 · 2天1晚 · 全程地铁渡轮',
  why:'两天版不进西九，周六泡在中环上环的老街和大馆，周日上太平山看完维港就走。适合周五晚出发、周日晚回的短周末。',
  i18n:{en:{name:'Hong Kong 2 Days',dest:'Hong Kong · Short weekend',
   title:'🚢 Hong Kong · 2 days · Central & the Peak',
   meta:'Hong Kong · 2d 1n · all by MTR & ferry',
   hero1k:'1 night in Jordan',
   why:'Two days: Central and Sheung Wan on Saturday, the Peak and the harbour on Sunday. Built for a Friday-night arrival.'}},
  seasons:[{in:true,name:'维港夜景',why:'幻彩咏香江 20:00 · 天气好才开',tag:'已排入 D1',ver:0},
   {in:false,name:'M+ 与西九',why:'需多一天 · 3 天版才排得下',pick:{key:'hk-mplus',name:'M+ 博物馆',ptext:'看展控'},needDays:3}],
  map:{nodes:HK_NODES,order:[0,1],loop:true,seg:[null,[0,1]],tonight:[0,-1]}}),

 mls5:Object.assign({},ROUTES.mls6,{
  days:MLS5_DAYS,lodges:MLS5_LODGES,nights:4,rent:3000,roadfood:380,
  dayVariants:[5,6],
  budgets:[{l:'宽松',v:3900},{l:'精打细算',v:3450}],
  title:'🗻 梅里雪山·雨崩 5 天 · 轻装进出',meta:'云南迪庆 · 5天4晚 · 雨崩住一晚',
  why:'五天版雨崩只住一晚：D3 徒步进上村，第二天原路出山回香格里拉。省下冰湖往返那天，体力要求降一档，日照金山和雨崩村的夜色一样不少。',
  seasons:[{in:true,name:'日照金山',why:'秋冬清晨概率最高 · 飞来寺守候',tag:'已排入 D2',ver:0},
   {in:false,name:'冰湖徒步',why:'往返一整天 · 6 天版才排得下',pick:{key:'mls-ice',name:'雨崩冰湖',ptext:'徒步控'},needDays:6}],
  map:{nodes:MLS_NODES,order:[0,1,2,3],loop:true,
   seg:[[0,1],[1,2],[2,3],[3,1],[1,0]],tonight:[1,2,3,1,-1]}}),

 dxb5:Object.assign({},ROUTES.dxb6,{
  days:DXB5_DAYS,lodges:DXB5_LODGES,nights:4,rent:2600,roadfood:340,
  dayVariants:[5,6],
  budgets:[{l:'宽松',v:3500},{l:'精打细算',v:3100}],
  title:'🚗 滇西北 5 天 · 大理丽江到香格里拉',meta:'云南 · 5天4晚 · 08-16 出发',
  why:'五天版不进普达措：大理躺两天、丽江一天、虎跳峡上香格里拉住独克宗，第五天直接回丽江还车。少一个高原景区，路上更松，也省下一张 258 的门票。',
  seasons:[{in:true,name:'洱海骑行季',why:'3-11 月环海路全线开放',tag:'已排入 D2',ver:0},
   {in:false,name:'普达措高山湖',why:'需多一天 · 6 天版才排得下',pick:{key:'dxb-pds',name:'普达措',ptext:'高原湖控'},needDays:6}],
  map:{nodes:DXB_NODES,order:[0,1,2,3],loop:false,
   seg:[null,[0,1],[1,2],[2,3],[3,2]],tonight:[0,1,2,3,-1]}}),
 xz10:Object.assign({},ROUTES.xz7,{
  days:XZ10_DAYS,lodges:XZ10_LODGES,nights:9,rent:6000,roadfood:580,
  dayVariants:[7,10],strength:'中',
  budgets:[{l:'宽松',v:9500},{l:'精打细算',v:8500}],
  title:'🏔 西藏 10 天 · 拉萨 + 林芝 + 纳木错',meta:'西藏 · 10天9晚 · 08-16 出发',
  why:'比 7 天版多出林芝三天，而且顺序有讲究：先从拉萨 3650 m 下到林芝 3000 m 缓两天（巴松措、雅鲁藏布大峡谷、索松村等日照金山），身体适应了再上羊湖、日喀则，最后住两晚纳木错 4718 m 看银河。高原反应最怕一上来就冲高海拔。',
  hero1v:'2,600<small>km</small>',hero1k:'全程包车',
  seasons:[{in:true,name:'布达拉宫限流',why:'旺季每日限流 · 提前 3 天预约',tag:'已排入 D2',ver:1},
   {in:true,name:'南迦巴瓦露脸',why:'秋季晴天概率最高 · 清晨最清',tag:'已排入 D4',ver:0},
   {in:false,name:'林芝桃花',why:'花期 3 月下旬至 4 月中 · 本次未到季',pick:{key:'lz-peach',name:'林芝桃花',ptext:'花海控'}}],
  extras:[{later:{key:'ebc',name:'珠峰大本营',why:'需多住定日两晚 · 本次不排',ptext:'登山控'}}],
  map:{nodes:XZ_NODES,order:[1,0,4,5,6,0,2,3],loop:false,
   seg:[null,null,[0,5],[5,6],[6,0],[0,1],[0,2],[2,3],null,[3,0]],
   tonight:[0,0,5,6,0,0,2,3,3,-1]}}),
 djy2:Object.assign({},ROUTES.djy1,{
  days:DJY2_DAYS,lodges:DJY2_LODGES,
  transport:{mode:'transit',rent:0,perCar:false,roadfood:0,label:'动车 · 摆渡（每人实付）'},
  stay:{nights:1},nights:1,
  dayVariants:[1,2],strength:'中',
  budgets:[{l:'宽松',v:850},{l:'精打细算',v:750}],
  title:'⛲ 都江堰·青城山 2 日 · 前山问道后山听水',meta:'成都周边 · 2天1晚 · 动车往返',
  why:'一日版只够拜水问道；两日版住进青城山镇，第二天整天泡在后山五龙沟的溪水栈道里，比前山凉十度，也比前山野。',
  hero1v:'8<small>km</small>',hero1k:'后山徒步',
  weather:'成都平原 8 月 · 昼 26–34°C · 后山谷内低 8–10°C · 午后阵雨',
  overTip:'可换镇上快捷房',
  seasons:[{in:true,name:'后山避暑季',why:'6-9 月谷内比市区低 8-10℃',tag:'已排入 D2',ver:1},
   {in:false,name:'青城山雪后',why:'12-1 月上清宫雾凇 · 本季未到',pick:{key:'qc-snow',name:'青城雪后',ptext:'雪景控'}}],
  inserts:null,extras:[],
  map:{nodes:DJY_NODES,order:[0,1,2],loop:true,
   seg:[[0,1],[2,0]],tonight:[2,-1]}}),
 zjj5:Object.assign({},ROUTES.zjj4,{
  days:ZJJ5_DAYS,lodges:ZJJ5_LODGES,nights:4,rent:1000,roadfood:275,
  dayVariants:[4,5],strength:'重',
  budgets:[{l:'宽松',v:3050},{l:'精打细算',v:2700}],
  title:'🏞 张家界 5 天 · 三山一桥全收',meta:'湖南张家界 · 5天4晚 · 08-16 出发',
  why:'四天版走完三座山，第五天补上大峡谷玻璃桥：上午桥上走一遍，下午顺谷底栈道下行到神泉湖，垂直电梯出谷。武陵源连住两晚不挪窝。',
  seasons:[{in:true,name:'武陵源云雾',why:'雨后清晨悬浮山概率最高',tag:'D3 早进山',ver:0},
   {in:true,name:'玻璃桥开放',why:'大风雷雨会临时封桥 · 出发前查公告',tag:'已排入 D4',ver:1}],
  inserts:null,extras:[],
  map:{nodes:ZJJ_NODES,order:[0,1,2,3],loop:false,
   seg:[null,[0,1,0],[0,2],[2,3,2],[2,0]],tonight:[0,0,2,2,-1]}}),
 gl3:Object.assign({},ROUTES.gl4,{
  days:GL3_DAYS,lodges:GL3_LODGES,nights:2,rent:600,roadfood:165,
  dayVariants:[3,4],
  budgets:[{l:'宽松',v:1550},{l:'精打细算',v:1350}],
  title:'🚢 桂林·阳朔 3 天 · 漓江精华',meta:'广西桂林 · 3天2晚 · 08-16 出发',
  why:'三天不上龙脊，全部给漓江：D1 直奔兴坪站进 20 元人民币，D2 遇龙河竹筏加十里画廊骑一整天，D3 象鼻山收官还车。周末加一天就能走完。',
  hero1v:'205<small>km</small>',hero1k:'全程自驾',
  seasons:[{in:true,name:'漓江丰水期',why:'6-8 月水量足 · 竹筏全线开',tag:'已排入 D2',ver:1},
   {in:false,name:'龙脊灌水季',why:'需多一天上山 · 4 天版才排得下',pick:{key:'gl-water',name:'龙脊梯田',ptext:'梯田控'},needDays:4}],
  inserts:{
   zhufa:Object.assign({},ROUTES.gl4.inserts.zhufa,{day:0,label:'D1'})},
  extras:[{ins:'zhufa'}],
  map:{nodes:GL_NODES,order:[0,2,3],loop:true,
   seg:[[0,2],null,[3,0]],tonight:[3,3,-1]}}),
 hs2:Object.assign({},ROUTES.hs3,{
  days:HS2_DAYS,lodges:HS2_LODGES,nights:1,rent:600,roadfood:110,
  dayVariants:[2,3],strength:'中',
  budgets:[{l:'宽松',v:2050},{l:'精打细算',v:1800}],
  title:'🏔 黄山·宏村 2 天 · 直接上山',meta:'安徽黄山 · 2天1晚 · 周六早出发',
  why:'两天版不进徽州古城：周六早八点出杭州，中午到山脚直接索道上山，西海大峡谷走一环、光明顶看日落、山顶过夜等日出；周日下山收宏村返杭。山上住宿必须提前订。',
  hero1v:'640<small>km</small>',hero1k:'全程自驾',
  seasons:[{in:true,name:'黄山云海',why:'雨后第二天出现概率最高',tag:'进山时查预报',ver:0},
   {in:false,name:'徽州古城 · 屯溪老街',why:'需多住一晚山下 · 3 天版才排得下',pick:{key:'hs-huizhou',name:'徽州古城',ptext:'古城控'},needDays:3}],
  inserts:{
   xidi:Object.assign({},ROUTES.hs3.inserts.xidi,{day:1,label:'D2'})},
  extras:[{ins:'xidi'}],
  map:{nodes:HS_NODES,order:[0,1,2],loop:false,
   seg:[[0,1],[1,2]],tonight:[1,-1]}}),
});

/* ═══ +1 天变体 ═══
   放在主追加区之后：它们要引用 cd3/sh3/hz3/sz3，那几条在上面才刚挂进 ROUTES。 */
Object.assign(ROUTES,{
 /* ═══ +1 天变体：同族多一天，用备选点补上 ═══ */
 cd4:normRoute(Object.assign({},ROUTES.cd3,{
   name:'成都 · 茶馆熊猫与郊野',dest:'四川 · 成都',fam:'cd',
   days:CD3_DAYS.concat(CD4_D4),
   lodges:CD3_LODGES.slice(0,-1).concat([{city:'宽窄巷子 · 连住',price:420,why:'不挪窝 · 明早去三圣乡',q:'成都宽窄巷子酒店'},null]),
   stay:{nights:3}, nights:3, dayVariants:[4],
   budgets:[{l:'宽松',v:1600},{l:'精打细算',v:1450}],
   title:'🐼 成都 4 天 · 加一天郊野',meta:'四川成都 · 4天3晚 · 全程地铁公交',
   why:'在三天版基础上多留一天给郊野：三圣乡的花田里泡个茶铺，转去白鹿镇看山谷里那座法式小镇。城里逛够了，正好换个节奏。',
   hero1v:'2<small>片</small>',hero1k:'城里加郊野',
   tastes:ROUTES.cd3.tastes, defSels:ROUTES.cd3.defSels, defSelsM:ROUTES.cd3.defSelsM,
   seasons:ROUTES.cd3.seasons, extras:ROUTES.cd3.extras, extrasSub:ROUTES.cd3.extrasSub,
   todos:ROUTES.cd3.todos, transport:ROUTES.cd3.transport, locale:ROUTES.cd3.locale,
   weather:ROUTES.cd3.weather, strength:ROUTES.cd3.strength, overTip:ROUTES.cd3.overTip,
   tixLabel:ROUTES.cd3.tixLabel, foodLabel:ROUTES.cd3.foodLabel, carLabel:ROUTES.cd3.carLabel,
   map:Object.assign({},ROUTES.cd3.map,{seg:ROUTES.cd3.map.seg.concat([null]),tonight:ROUTES.cd3.map.tonight.slice(0,-1).concat([ROUTES.cd3.map.tonight[0],-1])})})),

 sh4:normRoute(Object.assign({},ROUTES.sh3,{
   name:'上海 · 外滩梧桐与水乡',dest:'上海',fam:'sh',
   days:SH3_DAYS.concat(SH4_D4),
   lodges:SH3_LODGES.slice(0,-1).concat([{city:'人民广场 · 连住',price:520,why:'不挪窝 · 明早坐 17 号线去朱家角',q:'上海人民广场酒店'},null]),
   stay:{nights:3}, nights:3, dayVariants:[4],
   budgets:[{l:'宽松',v:1800},{l:'精打细算',v:1650}],
   title:'🌆 上海 4 天 · 加一天水乡',meta:'上海 · 4天3晚 · 全程地铁',
   why:'三天走完外滩与梧桐区后，第四天坐 17 号线到底去朱家角——放生桥下摇橹船一条接一条，扎肉配阿婆粽，地铁直达的江南。',
   hero1v:'2<small>片</small>',hero1k:'城里加水乡',
   tastes:ROUTES.sh3.tastes, defSels:ROUTES.sh3.defSels, defSelsM:ROUTES.sh3.defSelsM,
   seasons:ROUTES.sh3.seasons, extras:ROUTES.sh3.extras, extrasSub:ROUTES.sh3.extrasSub,
   todos:ROUTES.sh3.todos, transport:ROUTES.sh3.transport, locale:ROUTES.sh3.locale,
   weather:ROUTES.sh3.weather, strength:ROUTES.sh3.strength, overTip:ROUTES.sh3.overTip,
   tixLabel:ROUTES.sh3.tixLabel, foodLabel:ROUTES.sh3.foodLabel, carLabel:ROUTES.sh3.carLabel,
   map:Object.assign({},ROUTES.sh3.map,{seg:ROUTES.sh3.map.seg.concat([null]),tonight:ROUTES.sh3.map.tonight.slice(0,-1).concat([ROUTES.sh3.map.tonight[0],-1])})})),

 hz4:normRoute(Object.assign({},ROUTES.hz3,{
   name:'杭州 · 西湖龙井与湿地',dest:'浙江 · 杭州',fam:'hz',
   days:HZ3_DAYS.concat(HZ4_D4),
   lodges:HZ3_LODGES.slice(0,-1).concat([{city:'湖滨 · 连住',price:480,why:'不挪窝 · 明早去西溪',q:'杭州湖滨酒店'},null]),
   stay:{nights:3}, nights:3, dayVariants:[4],
   budgets:[{l:'宽松',v:1700},{l:'精打细算',v:1550}],
   title:'🌿 杭州 4 天 · 加一天湿地',meta:'浙江杭州 · 4天3晚 · 地铁公交',
   why:'西湖与龙井走完，第四天去西溪坐摇橹船——船在芦苇丛里穿，只有水声和鸟叫，跟西湖完全两个节奏。',
   hero1v:'2<small>片</small>',hero1k:'湖山加湿地',
   tastes:ROUTES.hz3.tastes, defSels:ROUTES.hz3.defSels, defSelsM:ROUTES.hz3.defSelsM,
   seasons:ROUTES.hz3.seasons, extras:ROUTES.hz3.extras, extrasSub:ROUTES.hz3.extrasSub,
   todos:ROUTES.hz3.todos, transport:ROUTES.hz3.transport, locale:ROUTES.hz3.locale,
   weather:ROUTES.hz3.weather, strength:ROUTES.hz3.strength, overTip:ROUTES.hz3.overTip,
   tixLabel:ROUTES.hz3.tixLabel, foodLabel:ROUTES.hz3.foodLabel, carLabel:ROUTES.hz3.carLabel,
   map:Object.assign({},ROUTES.hz3.map,{seg:ROUTES.hz3.map.seg.concat([null]),tonight:ROUTES.hz3.map.tonight.slice(0,-1).concat([ROUTES.hz3.map.tonight[0],-1])})})),

 sz4:normRoute(Object.assign({},ROUTES.sz3,{
   name:'苏州 · 园林老街与水乡',dest:'江苏 · 苏州',fam:'sz',
   days:SZ3_DAYS.concat(SZ4_D4),
   lodges:SZ3_LODGES.slice(0,-1).concat([{city:'平江路 · 连住',price:400,why:'不挪窝 · 明早去同里',q:'苏州平江路客栈'},null]),
   stay:{nights:3}, nights:3, dayVariants:[4],
   budgets:[{l:'宽松',v:1600},{l:'精打细算',v:1450}],
   title:'🎐 苏州 4 天 · 加一天水乡',meta:'江苏苏州 · 4天3晚 · 地铁步行',
   why:'园林与老街走完，第四天去同里——退思园贴水而建，走廊几乎踩着水面，比拙政园小但更私密，三桥走一圈就是一下午。',
   hero1v:'2<small>片</small>',hero1k:'园林加水乡',
   tastes:ROUTES.sz3.tastes, defSels:ROUTES.sz3.defSels, defSelsM:ROUTES.sz3.defSelsM,
   seasons:ROUTES.sz3.seasons, extras:ROUTES.sz3.extras, extrasSub:ROUTES.sz3.extrasSub,
   todos:ROUTES.sz3.todos, transport:ROUTES.sz3.transport, locale:ROUTES.sz3.locale,
   weather:ROUTES.sz3.weather, strength:ROUTES.sz3.strength, overTip:ROUTES.sz3.overTip,
   tixLabel:ROUTES.sz3.tixLabel, foodLabel:ROUTES.sz3.foodLabel, carLabel:ROUTES.sz3.carLabel,
   map:Object.assign({},ROUTES.sz3.map,{seg:ROUTES.sz3.map.seg.concat([null]),tonight:ROUTES.sz3.map.tonight.slice(0,-1).concat([ROUTES.sz3.map.tonight[0],-1])})}))
});


/* 设计稿已移除：行程页只放用户自己的行程 */
const DRAFT_TRIPS=[];

/* ── Schema v2 归一层 ─────────────────────────────────
   新线路只写语义三件套，旧线路自动折算，双向兼容：
   transport:{ mode:'drive'|'transit'|'walk'|'mixed',
               rent, perCar, roadfood, label }
   locale:   { region:'domestic'|'intl', country,
               navApp:'amap'|'gmaps', currencyNote }
   stay:     { nights }        ← 0 = 一日往返
   行程粒度天然支持单日/多日：days.length===1 即单日。
   交通花费入桶规则：自驾=rent+km×FUEL+tolls；
   公交/步行=各段 conn.cost 汇入 tolls（每人实付）。 */
function normRoute(R){
  if(R._norm) return R;
  R.transport = R.transport || {
    mode: R.perCar===false ? 'transit' : 'drive',
    rent: R.rent||0, perCar: R.perCar!==false,
    roadfood: R.roadfood||0, label: R.carLabel||'交通' };
  R.locale = R.locale || {
    region:'domestic', country:'中国',
    navApp: R.nav==='google' ? 'gmaps' : 'amap', currencyNote:null };
  R.stay = R.stay || { nights: (R.nights!=null?R.nights:Math.max(0,R.days.length-1)) };
  /* 反写旧字段：引擎与既有 UI 零改动直接读 */
  R.perCar=R.transport.perCar; R.rent=R.transport.rent;
  R.roadfood=R.transport.roadfood; R.carLabel=R.transport.label;
  R.nav = R.locale.navApp==='gmaps' ? 'google' : 'amap';
  R.nights=R.stay.nights;
  R._norm=1; return R;
}
function loadRoute(id){
  RT=ROUTES[id];
  if(!RT){                                   /* 兼容老内核：不用可选链 */
    var mNum=String(id).match(/\d+$/);
    var famKey=String(id).replace(/\d+$/,''), wantD=mNum?+mNum[0]:0;
    var alt=Object.keys(ROUTES).find(function(k){
      return ROUTES[k].fam===famKey && ROUTES[k].dayVariants && ROUTES[k].dayVariants.indexOf(wantD)>-1;
    });
    RT=alt?ROUTES[alt]:null;
  }
  if(!RT) return;
  normRoute(RT);
  DAYS=RT.days; LODGES=RT.lodges; CLUSTER=RT.cluster; INSERTS=RT.inserts||{};
  RENT=RT.rent; ROADFOOD=RT.roadfood;
  sels=Object.assign({},RT.defSels);
  selsM=new Set(RT.defSelsM||[]);
  lodge4=0; inserted.clear();          /* 口味是用户资产：跨线路保留，勿清 */
  mods=DAYS.map(()=>newMods());
  active=0; resolveAll();
}


/* ---------- 引擎 ---------- */
function variantOf(s){ return s.opts ? {...s, ...s.opts[sels[s.id]||0], k:s.k} : s; }
function dayMaterial(di){
  let rs=[], cs=[];
  const src=DAYS[di].stops;
  src.forEach(item=>{
    if(item.conn){ cs.push({...item}); return; }
    if(item.clusterRef){
      const sel=[...selsM].sort((a,b)=>a-b);
      if(sel.length===0){
        if(cs.length) cs.pop();
        if(CLUSTER.emptyConn) cs.push({...CLUSTER.emptyConn});
        rs.push({k:'cluster-empty',empty:true});
        src.slice(src.indexOf(item)+1).some(n=>{ if(n.conn){ n._skipOnce=true; } return true; });
      }else{
        sel.forEach((idx,j)=>{
          if(j>0) cs.push({...CLUSTER.opts[idx].join});
          rs.push({...CLUSTER.opts[idx], prio:j===0?1:2, _cluster:true, _cFirst:j===0});
        });
      }
      return;
    }
    if(item._skipOnce){ delete item._skipOnce; return; }
    rs.push(item);
  });
  for(const id of inserted){ const ins=INSERTS[id];
    if(ins.day!==di) continue;
    const at=rs.findIndex(s=>s.k===ins.afterK);
    if(at<0) continue;
    rs.splice(at+1,0,ins.stop);
    cs.splice(at,1,{...ins.conns[0]},{...ins.conns[1]});
  }
  return {rs,cs};
}
/* 班次吸附：区间车/火车/轮渡同机制 */

