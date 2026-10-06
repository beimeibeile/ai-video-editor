"""
P23: 剧本结构化解析器（Script Parser）
导演引擎的第一模块：把人类自然语言剧本翻译成标准分镜JSON

核心能力：
1. 角色识别（名称、形象、情绪、关系）
2. 动作解析（谁在什么时间做什么）
3. 情绪标注（每个角色每个时刻的情绪状态）
4. 音效点识别（动作音效、环境音、转场音效）
5. 节奏分析（每个镜头时长、转场类型）
6. 场景识别（地点、时间、氛围）

输出标准：scene_schema.json（见director_engine_architecture.md）
"""

import json
import re
import os
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict


# ============ 情绪词典 ============
EMOTION_KEYWORDS = {
    "开心": ["开心", "高兴", "快乐", "兴奋", "比耶", "笑", "得意", "蹦跶", "哈哈", "嘿嘿"],
    "委屈": ["委屈", "难过", "伤心", "哭", "摸头", "低头", "失落", "沮丧", "呜呜", "可怜"],
    "愤怒": ["愤怒", "生气", "怒吼", "拍桌", "瞪眼", "火大", "暴怒", "暴跳如雷", "气"],
    "惊恐": ["惊恐", "害怕", "尖叫", "躲闪", "颤抖", "惊慌", "吓", "惶恐", "慌张"],
    "得意": ["得意", "炫耀", "傲娇", "挑眉", "嘚瑟", "嚣张", "洋洋得意", "得意洋洋"],
    "平静": ["平静", "淡定", "冷静", "面无表情", "冷漠", "淡然", "从容"],
    "惊讶": ["惊讶", "吃惊", "瞪眼", "张嘴", "意外", "震惊", "愕然", "诧异"],
    "害羞": ["害羞", "脸红", "扭捏", "不好意思", "羞涩"],
    "质问": ["质问", "质疑", "反问", "责问", "逼问", "追问"],
    "尴尬": ["尴尬", "窘迫", "难堪", "为难", "语塞", "支吾"],
    "冷笑": ["冷笑", "嘲讽", "讥讽", "挖苦", "嗤笑", "嘲笑"],
    "不紧不慢": ["不紧不慢", "慢条斯理", "从容不迫", "不慌不忙", "缓缓"],
    "结结巴巴": ["结结巴巴", "支支吾吾", "吞吞吐吐", "语无伦次", "磕巴"],
    "心慌意乱": ["心慌意乱", "慌张", "慌乱", "心急如焚", "忐忑", "不安"],
    "低声下气": ["低声下气", "卑微", "讨好", "谄媚", "小心翼翼", "恭敬"],
    "严肃": ["严肃", "严厉", "庄重", "郑重", "认真"],
    "无奈": ["无奈", "叹气", "叹息", "无可奈何", "苦笑"],
    "坚定": ["坚定", "坚决", "果断", "毅然", "笃定"],
    "悲伤": ["悲伤", "哀伤", "悲痛", "凄凉", "伤感"],
    "紧张": ["紧张", "焦虑", "担忧", "忧心", "不安"],
}

# ============ 动作词典 ============
ACTION_KEYWORDS = {
    "比耶": ["比耶", "剪刀手", "耶", "v字手"],
    "被打": ["被打", "挨打", "揍", "一拳", "一巴掌", "踢", "击中", "打飞", "扇"],
    "摸头": ["摸头", "捂头", "抱头", "头好痛", "扶额"],
    "掉下": ["掉下", "掉出", "摔下", "跌出", "滚出", "摔倒"],
    "爬上": ["爬上", "爬回", "钻回", "探出头", "探出"],
    "说话": ["说", "道", "喊", "叫", "问", "答", "念", "讲", "读", "唱"],
    "转身": ["转身", "回头", "扭过头", "转过头"],
    "挥手": ["挥手", "招手", "摆手", "打招呼", "招手"],
    "弹弓": ["弹弓", "打弹弓", "射", "拉弓"],
    "站立": ["站", "站立", "站着", "挺立", "伫立"],
    "坐下": ["坐", "坐下", "坐着", "端坐", "瘫坐"],
    "走路": ["走", "走路", "步行", "踱步", "走来"],
    "跑步": ["跑", "跑步", "奔跑", "冲", "飞奔"],
    "看": ["看", "盯着", "注视", "凝视", "望", "瞅", "瞥"],
    "指": ["指", "指着", "指向", "指点", "手指"],
    "拿": ["拿", "拿着", "举起", "端起", "抓起"],
    "放下": ["放", "放下", "搁下", "丢下", "扔下"],
    "推": ["推", "推开", "推搡", "推进"],
    "拉": ["拉", "拉开", "拉扯", "拽"],
    "点头": ["点头", "颔首", "认可"],
    "摇头": ["摇头", "摆手拒绝", "否认"],
    "鼓掌": ["鼓掌", "拍手", "叫好"],
    "抱": ["抱", "拥抱", "搂住", "抱住"],
    "踢": ["踢", "踹", "踢脚"],
    "跳": ["跳", "跳跃", "蹦", "跃起"],
    "哭": ["哭", "流泪", "落泪", "抽泣"],
    "笑": ["笑", "微笑", "大笑", "狂笑", "偷笑"],
    "叹气": ["叹气", "叹息", "唉声叹气"],
    "打电话": ["打电话", "接电话", "通话", "手机"],
    "吃东西": ["吃", "喝", "咀嚼", "吞咽", "品尝"],
    "写字": ["写", "写字", "打字", "记录", "画"],
    "开门": ["开门", "关门", "推门", "敲门"],
}

# ============ 音效词典 ============
SFX_KEYWORDS = {
    "击打声": ["被打", "一拳", "一巴掌", "踢", "击中", "揍", "啪", "扇"],
    "闪白": ["被打", "击中", "一拳", "一巴掌"],
    "脚步声": ["走", "跑", "脚步", "踏", "踱步", "飞奔"],
    "风声": ["风", "吹", "飘", "呼啸"],
    "笑声": ["笑", "哈哈", "嘿嘿", "鼓掌", "叫好"],
    "哭声": ["哭", "呜呜", "委屈", "抽泣", "流泪"],
    "弹弓声": ["弹弓", "射", "嗖", "拉弓"],
    "玻璃碎": ["碎", "哗啦", "砰", "打碎"],
    "开门声": ["开门", "关门", "推门", "敲门", "吱呀"],
    "电话声": ["打电话", "接电话", "铃声", "嘟嘟"],
    "吃东西声": ["吃", "喝", "咀嚼", "吞咽", "吧唧"],
    "写字声": ["写", "打字", "键盘", "沙沙"],
    "叹气声": ["叹气", "叹息", "唉"],
    "掌声": ["鼓掌", "拍手", "叫好"],
    "碰撞声": ["撞", "碰", "磕", "咚"],
    "水流声": ["水", "流", "哗哗", "滴答"],
    "警报声": ["警报", "警笛", "呜哇"],
    "爆炸声": ["爆炸", "轰", "砰", "炸裂"],
}

# ============ 场景词典 ============
SCENE_KEYWORDS = {
    "头像框内": ["头像框", "头像", "框里", "框内", "圆形"],
    "抖音主页": ["抖音", "主页", "个人主页", "作品列表"],
    "商品橱窗": ["橱窗", "商品", "购物"],
    "室外": ["室外", "户外", "外面", "街", "路", "广场", "公园"],
    "室内": ["室内", "屋里", "房间", "办公室"],
    "酒店": ["酒店", "宾馆", "大堂", "前台", "客房", "走廊"],
    "餐厅": ["餐厅", "饭店", "食堂", "厨房", "餐桌", "菜单"],
    "办公室": ["办公室", "公司", "工位", "会议室", "老板桌"],
    "家里": ["家里", "家中", "客厅", "卧室", "书房", "阳台"],
    "街道": ["街道", "马路", "人行道", "路口", "红绿灯"],
    "学校": ["学校", "教室", "操场", "图书馆", "宿舍"],
    "医院": ["医院", "病房", "诊室", "护士站", "急诊"],
    "商场": ["商场", "超市", "店铺", "柜台", "收银台"],
    "车站": ["车站", "机场", "地铁站", "站台", "候车室"],
    "森林": ["森林", "树林", "丛林", "野外", "山"],
    "海边": ["海边", "海滩", "沙滩", "海浪", "码头"],
    "夜晚": ["夜晚", "深夜", "晚上", "黑夜", "月光"],
    "白天": ["白天", "清晨", "早晨", "正午", "下午"],
}

# ============ 转场词典 ============
TRANSITION_KEYWORDS = {
    "硬切": ["切", "切换", "转到", "画面一转"],
    "叠化": ["叠化", "淡入淡出", "渐渐", "慢慢"],
    "闪白": ["闪", "白屏", "刺眼"],
    "缩放": ["放大", "缩小", "推近", "拉远"],
}

# ============ 情绪→默认微动作映射（纯对话场景用）============
EMOTION_DEFAULT_ACTION = {
    "愤怒": "拍桌",
    "开心": "微笑",
    "委屈": "低头",
    "惊恐": "躲闪",
    "得意": "挑眉",
    "平静": "站立",
    "惊讶": "张嘴",
    "害羞": "低头",
    "质问": "指",
    "尴尬": "挠头",
    "冷笑": "抱臂",
    "不紧不慢": "整理衣服",
    "结结巴巴": "搓手",
    "心慌意乱": "踱步",
    "低声下气": "鞠躬",
    "严肃": "挺立",
    "无奈": "叹气",
    "坚定": "握拳",
    "悲伤": "低头",
    "紧张": "搓手",
}

# ============ 镜头语言自动选择 ============
def _auto_camera(actions: list, emotions: list, is_attack: bool = False) -> str:
    """根据动作和情绪自动选择镜头语言"""
    if is_attack:
        return "手持"
    if any(e in emotions for e in ["愤怒", "质问", "坚定"]):
        return "缓推"
    if any(e in emotions for e in ["惊恐", "惊讶", "心慌意乱"]):
        return "快推"
    if any(a in actions for a in ["走路", "跑步", "转身", "挥手"]):
        return "跟拍"
    if any(e in emotions for e in ["开心", "得意", "冷笑"]):
        return "固定"
    return "固定"


# ============ 角色默认描述映射 ============
CHARACTER_DEFAULTS = {
    "顾客": {"description": "普通顾客", "voice": "年轻女性/中性"},
    "客户": {"description": "普通客户", "voice": "年轻女性/中性"},
    "客人": {"description": "来访客人", "voice": "年轻女性/中性"},
    "前台": {"description": "酒店前台服务人员", "voice": "年轻女性/礼貌"},
    "服务员": {"description": "餐厅服务员", "voice": "年轻女性/热情"},
    "店员": {"description": "店铺店员", "voice": "年轻女性/礼貌"},
    "老板": {"description": "店铺老板", "voice": "中年男性/沉稳"},
    "经理": {"description": "公司经理", "voice": "中年男性/威严"},
    "主管": {"description": "部门主管", "voice": "中年男性/沉稳"},
    "员工": {"description": "普通员工", "voice": "年轻/中性"},
    "同事": {"description": "公司同事", "voice": "年轻/中性"},
    "职员": {"description": "公司职员", "voice": "年轻/中性"},
    "妈妈": {"description": "中年母亲", "voice": "中年女性/温柔"},
    "母亲": {"description": "中年母亲", "voice": "中年女性/温柔"},
    "爸爸": {"description": "中年父亲", "voice": "中年男性/沉稳"},
    "父亲": {"description": "中年父亲", "voice": "中年男性/沉稳"},
    "孩子": {"description": "儿童", "voice": "童声/活泼"},
    "小孩": {"description": "儿童", "voice": "童声/活泼"},
    "宝宝": {"description": "婴幼儿", "voice": "童声/可爱"},
    "老师": {"description": "学校老师", "voice": "中年女性/温和"},
    "教师": {"description": "学校教师", "voice": "中年女性/温和"},
    "学生": {"description": "在校学生", "voice": "年轻/活泼"},
    "医生": {"description": "医院医生", "voice": "中年/专业冷静"},
    "护士": {"description": "医院护士", "voice": "年轻女性/温柔"},
    "警察": {"description": "执法警察", "voice": "中年男性/威严"},
    "保安": {"description": "安保人员", "voice": "中年男性/低沉"},
    "外卖员": {"description": "外卖配送员", "voice": "年轻男性/急促"},
    "快递员": {"description": "快递配送员", "voice": "年轻男性/急促"},
    "旁白": {"description": "旁白解说", "voice": "沉稳/磁性"},
    "解说": {"description": "解说员", "voice": "沉稳/磁性"},
    "主持人": {"description": "节目主持人", "voice": "专业/洪亮"},
    "主播": {"description": "网络主播", "voice": "年轻/活泼"},
    "网红": {"description": "网络红人", "voice": "年轻/时尚"},
    "杀手": {"description": "职业杀手", "voice": "冷艳/低沉"},
    "特工": {"description": "特工人员", "voice": "冷静/低沉"},
    "侦探": {"description": "私家侦探", "voice": "中年男性/沉稳"},
    "律师": {"description": "执业律师", "voice": "中年/专业严谨"},
    "记者": {"description": "新闻记者", "voice": "年轻/干练"},
    "司机": {"description": "司机", "voice": "中年男性/朴实"},
    "厨师": {"description": "厨师", "voice": "中年男性/豪爽"},
    "保安": {"description": "安保人员", "voice": "中年男性/低沉"},
}


@dataclass
class Character:
    id: str
    name: str
    description: str = ""
    voice: str = ""
    emotion_default: str = "平静"


@dataclass
class CharacterAction:
    character_id: str
    action: str
    emotion: str = "平静"
    position: str = ""
    dialogue: str = ""


@dataclass
class Shot:
    id: str
    start: float
    duration: float
    camera: str = "固定"
    characters: List[CharacterAction] = field(default_factory=list)
    sfx: List[str] = field(default_factory=list)
    environment: str = ""


@dataclass
class Scene:
    id: str
    start: float
    duration: float
    location: str = ""
    atmosphere: str = ""
    shots: List[Shot] = field(default_factory=list)
    transition: str = "硬切"


@dataclass
class AudioMix:
    bgm: str = ""
    ambient: List[str] = field(default_factory=list)
    sfx_timeline: List[Dict] = field(default_factory=list)


@dataclass
class TextLayout:
    logo: Dict = field(default_factory=dict)
    subtitles: List[Dict] = field(default_factory=list)


@dataclass
class ScriptProject:
    title: str
    duration: float = 20.0
    fps: int = 30
    resolution: List[int] = field(default_factory=lambda: [1080, 1920])
    style: str = ""
    characters: List[Character] = field(default_factory=list)
    scenes: List[Scene] = field(default_factory=list)
    audio_mix: AudioMix = field(default_factory=AudioMix)
    text_layout: TextLayout = field(default_factory=TextLayout)


class ScriptParser:
    """剧本结构化解析器"""

    def __init__(self):
        self.characters = {}
        self.scenes = []
        self.project = None
        self.current_location = ""  # 当前场景位置（由"场景：XXX"声明设置）
        self.current_emotions = {}  # 角色当前情绪（叙述体情绪继承：动作描述句的情绪延续到后续台词）

    def parse(self, script_text: str, title: str = "未命名项目",
              duration: float = 20.0, style: str = "") -> Dict[str, Any]:
        """
        解析自然语言剧本，输出标准分镜JSON

        Args:
            script_text: 自然语言剧本
            title: 项目标题
            duration: 总时长（秒）
            style: 视频风格

        Returns:
            标准分镜JSON字典
        """
        self.project = ScriptProject(
            title=title,
            duration=duration,
            style=style,
        )

        # 1. 识别角色
        self._extract_characters(script_text)

        # 2. 分句/分段
        sentences = self._split_sentences(script_text)

        # 3. 逐句解析动作、情绪、音效
        parsed_shots = []
        current_time = 0.0
        for i, sent in enumerate(sentences):
            shot = self._parse_sentence(sent, i, current_time)
            if shot:
                parsed_shots.append(shot)
                current_time += shot.duration

        # 4. 聚合为场景
        self._group_into_scenes(parsed_shots)

        # 4.5 时长归一化（确保总时长接近目标）
        self._normalize_duration(parsed_shots)

        # 5. 生成音轨混合
        self._generate_audio_mix(parsed_shots)

        # 6. 生成文字排版
        self._generate_text_layout(script_text)

        # 7. 输出JSON
        return self._to_json()

    def _extract_characters(self, text: str):
        """从文本中识别角色"""
        # 已知角色映射（优先匹配）
        known_chars = {
            "豆包": {"name": "豆包", "description": "短发红围巾黑西装女性", "voice": "年轻女性/活泼"},
            "机器人": {"name": "机器人", "description": "银灰钢铁侠风格机器人", "voice": "机械音/低沉"},
            "女杀手": {"name": "女杀手", "description": "全身黑西装高跟鞋女性", "voice": "冷艳女性"},
        }

        # 非角色名黑名单（常见的动词/副词/量词/连接词/短语）
        blacklist = {
            "一脚", "一拳", "一巴掌", "一下", "一次", "结果", "然后", "突然",
            "这时", "接着", "最后", "终于", "于是", "所以", "因为",
            "如果", "虽然", "但是", "而且", "并且", "或者", "还是", "不是",
            "结果又", "然后又", "突然又", "这时又", "接着又",
            "委屈地", "开心地", "愤怒地", "惊恐地", "得意地", "平静地",
            "惊讶地", "害羞地", "难过地", "高兴地", "兴奋地", "激动地",
            "家打招呼", "打招呼", "大家好", "你们好", "大家", "你们",
            "我们", "他们", "她们", "它们", "这个", "那个", "这些", "那些",
            "什么", "怎么", "为什么", "哪里", "哪个", "谁", "怎么回事",
            "向大家", "对大家", "跟大家", "和大家", "给大家",
            "手一脚", "手一拳", "手一巴掌", "头一撞", "脚一踢",
            # 常见动词短语（避免被误识别为角色）
            "帮我", "帮你", "帮他", "帮她", "露出", "露出微", "露出笑",
            "深吸", "深吸一", "当场", "当场石化", "突然回", "突然回头",
            # 方位短语
            "在旁边", "在那里", "在这里", "在后面", "在前面", "在上面", "在下面",
            "在左边", "在右边", "在中间", "在外面", "在里面", "在远处", "在近处",
            "站在旁", "坐在旁", "躺在地", "跑过来", "走过来", "飞过来",
            # 场景标记
            "场景", "地点", "背景", "环境",
            # LLM文本常见标签性词汇（非角色名）
            "动作", "问题", "结束语", "开场白", "正文", "内容", "描述", "说明",
            "注释", "备注", "标题", "副标题", "摘要", "总结", "结论", "要点",
            "重点", "亮点", "彩蛋", "花絮", "幕后", "预告", "片头", "片尾",
            "转场", "过渡", "衔接", "呼应", "铺垫", "伏笔", "悬念", "冲突",
            "高潮", "结局", "结尾", "开头", "开场", "引入", "切入", "展开",
            "发展", "推进", "转折", "反转", "升华", "点题", "扣题", "收尾",
            # 常见短语截断（避免被误识别）
            "现反转", "心价值", "时抛出", "出邀请", "员慌张", "客明明",
            "地躲闪", "地逃跑", "地后退", "地前进", "地攻击", "地防御",
            "地微笑", "地哭泣", "地大笑", "地怒吼", "地低语", "地沉默",
            # 常见名词（非角色）
            "时间", "地点", "人物", "事件", "原因", "结果", "过程", "方法",
            "方式", "手段", "工具", "道具", "服装", "化妆", "造型", "设计",
            "画面", "镜头", "景别", "角度", "构图", "光影", "色彩", "音效",
            "音乐", "配乐", "配音", "台词", "对白", "独白", "旁白", "解说",
            # 常见动词（非角色）
            "提问", "回答", "解释", "说明", "描述", "介绍", "分析", "总结",
            "讨论", "商量", "协商", "谈判", "沟通", "交流", "对话", "聊天",
            # 动作短语（LLM输出常见）
            "上前", "后退", "转身", "点头", "摇头", "挥手", "拍手", "跺脚",
            "坐下", "站起", "蹲下", "趴下", "躺下", "靠在", "倚在", "趴在",
            "拿起", "放下", "推开", "拉开", "关上", "打开", "摔门", "踢门",
            "微笑", "大笑", "苦笑", "冷笑", "偷笑", "狂笑", "傻笑", "假笑",
            "皱眉", "瞪眼", "眯眼", "闭眼", "睁眼", "眨眼", "流泪", "哭泣",
            "温暖", "温柔", "冷漠", "热情", "激动", "平静", "紧张", "害怕",
            # 短语截断（LLM输出常见的不完整词）
            "暖的微", "留下微", "露出微", "带着微", "含着微", "挂着微",
            "的微笑", "的笑容", "的表情", "的眼神", "的动作", "的声音",
            "地微笑", "地大笑", "地点头", "地摇头", "地转身", "地后退",
            "上前一", "后退一", "转身一", "点头一", "摇头一",
            "务员微", "员微笑", "员慌张", "员尴尬", "员无奈", "员惊讶",
            "客惊讶", "客愤怒", "客疑惑", "客无奈", "客微笑", "客大笑",
            # 常见非角色名词
            "外卖", "快递", "菜单", "账单", "发票", "收据", "订单", "合同",
            "手机", "电话", "电脑", "电视", "空调", "冰箱", "洗衣机", "微波炉",
        }

        # 介词开头过滤（这些词通常不是角色名）
        preposition_prefixes = set("在从向对跟和给被把将由为以于")

        found_names = set()
        # 先匹配已知角色
        for name in known_chars:
            if name in text:
                found_names.add(name)

        # 收集所有情绪词和动作词（用于从候选角色名中去除）
        all_emotion_words = set()
        for keywords in EMOTION_KEYWORDS.values():
            all_emotion_words.update(keywords)
        all_action_words = set()
        for keywords in ACTION_KEYWORDS.values():
            all_action_words.update(keywords)
        # 常见的"地+动词"后缀
        speech_verbs = {"说", "道", "喊", "问", "答", "笑", "哭", "叫", "讲", "念", "读", "唱"}

        def _extract_speaker_name(line_text: str, has_emotion_marker: bool = False) -> Optional[str]:
            """从句首文本中提取角色名（去掉情绪词、动作词、地说后缀）
            Args:
                line_text: 行首文本
                has_emotion_marker: 是否有情绪标注（括号内情绪或"地+动词"后缀）
            """
            # 去掉冒号及后面的内容
            text = line_text.split("：")[0].split(":")[0].strip()
            if not text:
                return None
            # 去掉括号内的情绪标注
            text = re.sub(r'[（(][^）)]*[）)]', '', text).strip()
            # 去掉"地+动词"后缀（如"愤怒地说"→"愤怒"）
            for verb in speech_verbs:
                suffix = "地" + verb
                if text.endswith(suffix):
                    text = text[:-len(suffix)]
                    break
            # 从结尾逐步去掉"地"+情绪词/动作词（长词优先）
            all_words = sorted(all_emotion_words | all_action_words, key=len, reverse=True)
            changed = True
            while changed and len(text) > 2:
                changed = False
                # 先去掉结尾的"地"（副词后缀）
                if text.endswith("地") and len(text) > 2:
                    text = text[:-1]
                    changed = True
                # 再去掉结尾的情绪词/动作词
                for word in all_words:
                    if text.endswith(word) and len(text) - len(word) >= 2:
                        text = text[:-len(word)]
                        changed = True
                        break
            # 最终检查：2-4个中文字，不以"地/的/了/着/过"结尾，不以"地"开头
            if 2 <= len(text) <= 4 and text[-1] not in "地的了着过" and text[0] != "地":
                if text[0] not in preposition_prefixes and text not in blacklist:
                    return text
            return None

        # 匹配行首"角色（情绪）："或"角色："或"角色+情绪地说："格式
        line_pattern = re.compile(r'^[\s]*([\u4e00-\u9fa5]{2,8}(?:[（(][^）)]*[）)])?\s*(?:地?[说道喊问答笑哭叫讲念读唱]?)?)\s*[：:]', re.MULTILINE)
        for match in line_pattern.finditer(text):
            raw_match = match.group(1)
            # 检测是否有情绪标注（括号内情绪或"地+动词"后缀）
            has_marker = bool(re.search(r'[（(][^）)]*[）)]', raw_match)) or bool(re.search(r'地[说道喊问答笑哭叫讲念读唱]$', raw_match))
            name = _extract_speaker_name(raw_match, has_emotion_marker=has_marker)
            if name and name not in known_chars:
                found_names.add(name)

        # 再尝试识别其他角色名（2-3个中文字，后面跟着说/道/喊/问/答/笑/哭/被/把/将/：/:等，且不在黑名单）
        other_matches = re.findall(r'([\u4e00-\u9fa5]{2,3})(?=说|道|喊|问|答|笑|哭|被|把|将|：|:)', text)
        for m in other_matches:
            if m not in blacklist and m not in known_chars and len(m) >= 2:
                # 额外过滤：不以"地/的/了/着/过"结尾，不以"地"开头（地+动词是副词短语，不是角色名）
                if m[-1] not in "地的了着过" and m[0] != "地":
                    # 不以介词开头
                    if m[0] not in preposition_prefixes:
                        found_names.add(m)

        char_id = 0
        for name in found_names:
            if name in known_chars:
                info = known_chars[name]
                char = Character(
                    id=f"char_{char_id}",
                    name=info["name"],
                    description=info["description"],
                    voice=info["voice"],
                )
            else:
                # 从默认描述映射表查找，找不到则用通用描述
                default = CHARACTER_DEFAULTS.get(name, {"description": "未指定角色", "voice": "中性"})
                char = Character(
                    id=f"char_{char_id}",
                    name=name,
                    description=default["description"],
                    voice=default["voice"],
                )
            self.characters[name] = char
            self.project.characters.append(char)
            char_id += 1

    def _split_sentences(self, text: str) -> List[str]:
        """按行+标点分句（优先按行，避免台词中标点被拆断）"""
        # 先按换行分句（剧本通常每行一句台词）
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        sentences = []
        for line in lines:
            # 每行内再按句号/分号分句（问号/感叹号保留在台词中不拆）
            parts = re.split(r'[。；]+', line)
            for p in parts:
                p = p.strip()
                if p:
                    sentences.append(p)
        return sentences

    def _parse_sentence(self, sentence: str, index: int, start_time: float) -> Optional[Shot]:
        """解析单句，识别角色、动作、情绪、音效"""
        if not sentence:
            return None

        # 识别"场景：XXX"/"场景1：XXX"/"场景一：XXX"声明——不生成shot，只设置当前场景
        scene_decl = re.match(r'^[\s]*场景[0-9一二三四五六七八九十]*[：:]\s*(.+)$', sentence)
        if scene_decl:
            self.current_location = scene_decl.group(1).strip()
            return None

        # 识别角色：优先提取句首说话人（"角色（情绪）："或"角色："格式）
        chars_in_sentence = []
        speaker_match = re.match(r'^[\s]*([\u4e00-\u9fa5]{2,4})(?:[（(][^）)]*[）)])?\s*[：:]', sentence)
        if speaker_match:
            speaker_name = speaker_match.group(1)
            if speaker_name in self.characters:
                chars_in_sentence.append(self.characters[speaker_name])
        else:
            # 回退：角色名出现在句子中（动作描述类句子）
            # 非攻击场景：只取句首第一个角色作为动作执行者（避免"前台桌子"中的"前台"被误识别）
            # 攻击场景：需要两个角色（施动者+受动者）
            is_attack = any(kw in sentence for kw in ["打", "踢", "揍", "扇", "捶", "砸", "撞", "推", "被"])
            if is_attack:
                for name, char in self.characters.items():
                    if name in sentence:
                        chars_in_sentence.append(char)
            else:
                # 找句首第一个出现的角色
                first_char = None
                first_pos = len(sentence)
                for name, char in self.characters.items():
                    pos = sentence.find(name)
                    if pos != -1 and pos < first_pos:
                        first_pos = pos
                        first_char = char
                if first_char:
                    chars_in_sentence.append(first_char)

        # 识别动作
        actions = []
        for action, keywords in ACTION_KEYWORDS.items():
            for kw in keywords:
                if kw in sentence:
                    actions.append(action)
                    break

        # 识别情绪（长关键词优先，避免"冷笑"被"开心"的"笑"抢先匹配）
        emotions = []
        emotion_matches = []  # (关键词长度, 情绪名)
        for emotion, keywords in EMOTION_KEYWORDS.items():
            for kw in keywords:
                if kw in sentence:
                    emotion_matches.append((len(kw), emotion))
                    break
        # 按关键词长度降序排列，长关键词优先
        emotion_matches.sort(key=lambda x: -x[0])
        emotions = [e for _, e in emotion_matches]

        # 识别音效
        sfx = []
        for sfx_type, keywords in SFX_KEYWORDS.items():
            for kw in keywords:
                if kw in sentence:
                    sfx.append(sfx_type)
                    break

        # 识别场景（优先使用"场景：XXX"声明的位置）
        location = self.current_location
        if not location:
            for scene, keywords in SCENE_KEYWORDS.items():
                for kw in keywords:
                    if kw in sentence:
                        location = scene
                        break
                if location:
                    break
        # 仍无法识别时，根据内容智能推断
        if not location:
            location = self._infer_location_from_content(sentence)

        # 识别转场
        transition = "硬切"
        for trans, keywords in TRANSITION_KEYWORDS.items():
            for kw in keywords:
                if kw in sentence:
                    transition = trans
                    break
            if transition != "硬切":
                break

        # 识别台词（引号内的内容）
        dialogue = ""
        dialogue_match = re.search(r'[「『"](.+?)[」』"]', sentence)
        if dialogue_match:
            dialogue = dialogue_match.group(1)
        else:
            # 检查句子是否以角色名开头（支持"角色："、"角色（情绪）："、"角色+情绪地说："、"角色+情绪地+动作："格式）
            sentence_starts_with_char = False
            for c in chars_in_sentence:
                if sentence.lstrip().startswith(c.name):
                    sentence_starts_with_char = True
                    break
            # 支持"角色名：台词"、"角色（情绪）：台词"、"角色+情绪地说：台词"格式
            colon_match = re.search(
                r'[\u4e00-\u9fa5]{2,4}(?:[（(][^）)]*[）)])?(?:\s*[\u4e00-\u9fa5]{0,4}地)?(?:说|道|喊|问|答|笑|哭|叫|讲|念|读|唱)?\s*[：:]\s*(.+?)(?:[。！？!?]|$)',
                sentence
            )
            if colon_match:
                candidate = colon_match.group(1).strip()
                # 以角色名开头时，冒号后内容直接作为台词（不过滤"了/着/地/过"）
                if sentence_starts_with_char:
                    if len(candidate) >= 2:
                        dialogue = candidate
                else:
                    # 无明确角色前缀时，用过滤条件区分动作描述和台词
                    if len(candidate) >= 2 and not any(kw in candidate for kw in ["地", "着", "了", "过"]):
                        dialogue = candidate

        # 构建角色动作（施动者/受动者区分）
        char_actions = []

        # 判断是否有被动/主动结构
        has_passive = "被" in sentence
        has_active = "把" in sentence or "将" in sentence

        # 攻击类动作关键词
        attack_keywords = ["打", "踢", "揍", "扇", "捶", "砸", "撞", "推"]
        is_attack_scene = any(kw in sentence for kw in attack_keywords)

        # 预计算所有角色位置（按位置排序）
        char_positions = [(c.name, sentence.find(c.name)) for c in chars_in_sentence]
        char_positions.sort(key=lambda x: x[1])

        # 确定受动者和施动者
        patient_name = None  # 受动者（被打）
        agent_name = None    # 施动者（攻击）

        if is_attack_scene and len(chars_in_sentence) >= 2:
            if has_passive:
                # "A被B打" 或 "..., A被打得..." → A是受动者
                bei_pos = sentence.find("被")
                # 找"被"字前面最近的角色
                for name, pos in reversed(char_positions):
                    if pos < bei_pos:
                        patient_name = name
                        break
                # 找"被"字后面的角色（如果有）作为施动者
                for name, pos in char_positions:
                    if pos > bei_pos:
                        agent_name = name
                        break
                # 如果"被"字后面没有角色，第一个出现的角色（非受动者）是施动者
                if not agent_name:
                    for name, _ in char_positions:
                        if name != patient_name:
                            agent_name = name
                            break
            elif has_active:
                # "A把B打" → A是施动者，B是受动者
                ba_pos = sentence.find("把")
                if ba_pos == -1:
                    ba_pos = sentence.find("将")
                for name, pos in char_positions:
                    if pos < ba_pos:
                        agent_name = name
                    elif pos > ba_pos and not patient_name:
                        patient_name = name
            else:
                # "A打B" → 第一个是施动者，后面的是受动者
                agent_name = char_positions[0][0]
                if len(char_positions) > 1:
                    patient_name = char_positions[1][0]

        for char in chars_in_sentence:
            # 动作：优先匹配动作关键词，否则根据情绪选默认微动作
            if actions:
                action = actions[0]
            else:
                action = EMOTION_DEFAULT_ACTION.get(emotions[0] if emotions else char.emotion_default, "站立")

            # 情绪：优先匹配到的情绪；台词句无情绪时继承动作描述句的情绪
            if emotions:
                emotion = emotions[0]
            elif dialogue and char.name in self.current_emotions:
                emotion = self.current_emotions[char.name]
            else:
                emotion = char.emotion_default

            # 情绪继承：动作描述句（无台词）更新角色当前情绪，供后续台词继承
            if not dialogue and emotions:
                self.current_emotions[char.name] = emotions[0]

            # 应用动作归属
            if is_attack_scene and len(chars_in_sentence) >= 2:
                if char.name == patient_name:
                    action = "被打"
                elif char.name == agent_name:
                    action = "攻击"

            char_actions.append(CharacterAction(
                character_id=char.id,
                action=action,
                emotion=emotion,
                dialogue=dialogue if dialogue else "",
            ))

        # 估算时长（基于动作数量和台词长度）
        base_duration = 2.0
        if dialogue:
            base_duration += len(dialogue) * 0.15
        if "被打" in actions:
            base_duration = 1.0
        if "比耶" in actions:
            base_duration = 3.0

        # 镜头语言自动选择
        camera = _auto_camera(actions, emotions, is_attack_scene)

        shot = Shot(
            id=f"shot_{index:03d}",
            start=start_time,
            duration=round(base_duration, 1),
            camera=camera,
            characters=char_actions,
            sfx=sfx,
            environment=location,
        )
        return shot

    def _group_into_scenes(self, shots: List[Shot]):
        """把镜头聚合为场景（按位置/环境分组）"""
        if not shots:
            return

        current_scene = None
        scene_id = 0

        for shot in shots:
            location = shot.environment or "未指定"

            if current_scene is None or current_scene.location != location:
                # 新场景
                if current_scene:
                    current_scene.duration = round(
                        shot.start - current_scene.start, 1
                    )
                    self.project.scenes.append(current_scene)

                current_scene = Scene(
                    id=f"scene_{scene_id:02d}",
                    start=shot.start,
                    duration=0,
                    location=location,
                    atmosphere=self._infer_atmosphere(location),
                    transition="硬切",
                )
                scene_id += 1

            current_scene.shots.append(shot)

        if current_scene:
            last_shot = shots[-1]
            current_scene.duration = round(
                last_shot.start + last_shot.duration - current_scene.start, 1
            )
            self.project.scenes.append(current_scene)

    def _normalize_duration(self, shots: List[Shot]):
        """
        时长归一化：确保所有镜头总时长接近目标时长

        策略：
        - 偏差≤10%：不调整
        - 偏差>10%：按比例压缩/扩展，保持每个镜头最小时长1.0秒
        - 重新分配start时间，更新场景时长
        """
        if not shots:
            return

        target = self.project.duration
        total = sum(s.duration for s in shots)

        if total <= 0:
            return

        deviation = abs(total - target) / target
        if deviation <= 0.10:
            return  # 偏差在10%以内，不调整

        # 计算缩放比例
        scale = target / total

        # 按比例调整每个镜头时长，保持最小时长1.0秒
        new_durations = []
        for shot in shots:
            new_dur = max(1.0, round(shot.duration * scale, 1))
            new_durations.append(new_dur)

        # 如果调整后总时长仍偏差较大，微调最后一个镜头
        new_total = sum(new_durations)
        if abs(new_total - target) > 0.5 and new_durations:
            diff = round(target - new_total, 1)
            new_durations[-1] = max(1.0, new_durations[-1] + diff)

        # 重新分配start时间
        current_time = 0.0
        for i, shot in enumerate(shots):
            shot.start = round(current_time, 1)
            shot.duration = new_durations[i]
            current_time += shot.duration

        # 更新场景时长
        for scene in self.project.scenes:
            if scene.shots:
                first = scene.shots[0]
                last = scene.shots[-1]
                scene.start = first.start
                scene.duration = round(last.start + last.duration - first.start, 1)

        print(f"  ⏱️  时长归一化: {total:.1f}s → {sum(new_durations):.1f}s (目标{target}s, 缩放{scale:.2f})")

    def _infer_location_from_content(self, sentence: str) -> str:
        """
        根据句子内容智能推断场景位置（当场景词典未匹配时）

        规则：
        - 提到菜/饭/服务员/顾客/点菜/买单 → 餐厅
        - 提到老板/工位/会议/同事/上班 → 办公室
        - 提到老师/同学/上课/教室/考试 → 学校
        - 提到医生/护士/病房/挂号 → 医院
        - 提到妈妈/爸爸/家/客厅/卧室 → 家里
        - 其他 → 室内（默认）
        """
        content_rules = [
            ("餐厅", ["菜", "饭", "服务员", "顾客", "点菜", "买单", "菜单", "米饭", "咸", "好吃", "难吃"]),
            ("办公室", ["老板", "工位", "会议", "同事", "上班", "加班", "汇报", "项目", "KPI"]),
            ("学校", ["老师", "同学", "上课", "教室", "考试", "作业", "学生", "校长", "班主任"]),
            ("医院", ["医生", "护士", "病房", "挂号", "看病", "手术", "药", "体检"]),
            ("家里", ["妈妈", "爸爸", "家", "客厅", "卧室", "孩子", "老婆", "老公"]),
            ("商场", ["买", "购物", "打折", "促销", "收银", "店员"]),
            ("街道", ["街", "路", "走", "跑", "车", "红绿灯", "路口"]),
        ]

        for location, keywords in content_rules:
            for kw in keywords:
                if kw in sentence:
                    return location

        return "室内"  # 默认场景

    def _infer_atmosphere(self, location: str) -> str:
        """根据场景推断氛围"""
        atmosphere_map = {
            "头像框内": "轻松/搞笑",
            "抖音主页": "日常",
            "商品橱窗": "商业",
            "室外": "开阔",
            "室内": "温馨",
        }
        return atmosphere_map.get(location, "中性")

    def _generate_audio_mix(self, shots: List[Shot]):
        """生成音轨混合方案"""
        # 收集所有音效点
        sfx_timeline = []
        for shot in shots:
            for sfx in shot.sfx:
                sfx_timeline.append({
                    "time": shot.start,
                    "type": sfx,
                    "intensity": 0.7,
                })

        # 根据风格推断BGM
        bgm_map = {
            "旅拍": "轻松旅拍BGM",
            "短剧": "剧情向BGM",
            "搞笑": "欢快搞笑BGM",
            "广告": "商业宣传BGM",
        }
        bgm = bgm_map.get(self.project.style, "通用BGM")

        # 根据场景推断环境音
        ambient = []
        for scene in self.project.scenes:
            if scene.location == "室外":
                ambient.append("户外环境音")
            elif scene.location == "室内":
                ambient.append("室内环境音")
            elif "头像框" in scene.location:
                ambient.append("轻微室内音")

        self.project.audio_mix = AudioMix(
            bgm=bgm,
            ambient=list(set(ambient)),
            sfx_timeline=sfx_timeline,
        )

    def _generate_text_layout(self, script_text: str):
        """生成文字排版方案"""
        # 根据风格推断排版
        if self.project.style == "旅拍":
            self.project.text_layout = TextLayout(
                logo={"text": self.project.title, "position": "左上", "style": "手写体"},
                subtitles=[],
            )
        elif self.project.style == "短剧":
            self.project.text_layout = TextLayout(
                logo={},
                subtitles=[],
            )
        else:
            self.project.text_layout = TextLayout(
                logo={},
                subtitles=[],
            )

    def _to_json(self) -> Dict[str, Any]:
        """转换为标准JSON"""
        return {
            "project": {
                "title": self.project.title,
                "duration": self.project.duration,
                "fps": self.project.fps,
                "resolution": self.project.resolution,
                "style": self.project.style,
            },
            "characters": [asdict(c) for c in self.project.characters],
            "scenes": [
                {
                    "id": s.id,
                    "start": s.start,
                    "duration": s.duration,
                    "location": s.location,
                    "atmosphere": s.atmosphere,
                    "shots": [
                        {
                            "id": sh.id,
                            "start": sh.start,
                            "duration": sh.duration,
                            "camera": sh.camera,
                            "characters": [asdict(ca) for ca in sh.characters],
                            "sfx": sh.sfx,
                            "environment": sh.environment,
                        }
                        for sh in s.shots
                    ],
                    "transition": s.transition,
                }
                for s in self.project.scenes
            ],
            "audio_mix": asdict(self.project.audio_mix),
            "text_layout": asdict(self.project.text_layout),
        }

    def save_json(self, output_path: str):
        """保存解析结果到JSON文件"""
        result = self._to_json()
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"✅ 分镜JSON已保存: {output_path}")
        return output_path

    def print_summary(self):
        """打印解析摘要"""
        result = self._to_json()
        print(f"\n{'='*60}")
        print(f"剧本解析摘要")
        print(f"{'='*60}")
        print(f"项目: {result['project']['title']}")
        print(f"时长: {result['project']['duration']}秒")
        print(f"风格: {result['project']['style']}")
        print(f"\n角色 ({len(result['characters'])}):")
        for c in result['characters']:
            print(f"  - {c['name']}: {c['description']}")
        print(f"\n场景 ({len(result['scenes'])}):")
        for s in result['scenes']:
            print(f"  {s['id']}: {s['location']} ({s['start']}s-{s['start']+s['duration']}s) "
                  f"[{s['atmosphere']}] {len(s['shots'])}镜头")
            for sh in s['shots']:
                chars = ", ".join([f"{ca['character_id']}:{ca['action']}({ca['emotion']})"
                                   for ca in sh['characters']])
                print(f"    {sh['id']}: {sh['duration']}s | {chars} | SFX:{sh['sfx']}")
        print(f"\n音效点: {len(result['audio_mix']['sfx_timeline'])}个")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    # 测试：豆包被打案例
    test_script = """
    豆包在抖音主页的头像框里开心地比耶，向大家打招呼。
    突然机器人一拳打在豆包脸上，豆包被打得飞出去，委屈地摸头。
    豆包从头像框里掉出来，摔在作品列表上。
    女杀手出现，一脚把豆包踢回头像框里。
    豆包爬回头像框，得意地比耶，结果又被机器人打了一拳。
    """

    parser = ScriptParser()
    result = parser.parse(
        script_text=test_script,
        title="豆包被打",
        duration=20.0,
        style="搞笑短剧",
    )
    parser.print_summary()

    # 保存
    out = r"C:\Users\Administrator\Videos\剪映导出\Doubao_Jianying-editor\director_engine_test\parsed_script.json"
    parser.save_json(out)
