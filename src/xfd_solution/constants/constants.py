# -*- coding: utf-8 -*-
# @Desc   : Description of File
# @Licence: (C) Copyright for ValueOnline
# @Author : chen.long
# @Date   : 2023/8/1
import os

# ChatGLM2模型路径
GLM_PATH = '/home/ubuntu/chenl/chatglm2-6b'

# 抽取年报数据路径
ANNUAL_REPORT_PATH = '/home/ubuntu/chenl/smp_processed_data'

# m3e模型路径
M3E_PATH = '/root/brx/m3e-base'

# 项目根目录
ROOT_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# 数据路径
DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'data')

# 无参考资料问题prompt
ANSWER_PROMPT = "请准确、简短地回答下列问题，不得有编造和杜撰成分，字数不超过200字。\n\n{}"

# 基于公司基本信息回答问题prompt
ANSWER_BASE_INFO_PROMPT = ("以下三引号内是公司信息，请基于公司信息准确、简短回答问题“{}”。回答不得有编造和杜撰成分，不得重复问题，不得包含问题以外的信息，字数不得超过200字。\n\n"
                           "\"\"\"{}\"\"\"")

# 计算类指标的prompt
CALCULATE_TYPE_PROMPT = (
    "已知公式：{}\n以下三引号内是公司信息，请基于上面公式及公司信息，计算并回答问题：“{}”。问题中除带“比值”、“比例”外，其余指标需要转换为百分制表示。\n\n"
    "\"\"\"{}\"\"\"")

# 抽取数字指标prompt
EXTRACT_DECIMAL_PROMPT = ('请基于以下5个原则用中文回答问题：\"{}年，公司的{}是多少？\"。\n\n '
                          '1、以下三个引号内为基本信息，基于基本信息回答问题，不得有编造和杜撰成分。\n'
                          '2、回答中不能包含问题内容。\n'
                          '3、如果答案是数字，只需回答数字即可。\n'
                          '4、回答需专业、简短、准确。\n'
                          '5、如果基于基本信息无法回答该问题，只回答\"NULL\"，不得回答其他内容。\n\n'
                          '\"\"\"{}\"\"\"')

# 抽取文本指标prompt
EXTRACT_TEXT_PROMPT = ('请基于以下4个原则用中文回答问题：\"公司的{}是什么？\"。\n\n '
                       '1、以下三个引号内为基本信息，基于基本信息回答问题，不得有编造和杜撰成分。\n'
                       '2、回答中不得包含问题内容。'
                       '3、回答需专业、简短、准确，字数不得超过50个字。\n'
                       '4、如果基于基本信息无法回答该问题，只回答\"NULL\"，不得回答其他内容。\n\n'
                       '\"\"\"{}\"\"\"')

# 抽取指标正则
INDEX_PATTERNS = {
    '主要业务': ['主[要营]业务(形态)?[为是]', '主要从事', '公司(是一家)?致力于'],
    '注册资本': ['注册资本[为：:]?.*?元'],
    '总资产': ['总资产[为：:]?.*?元', '总资产.*?(合计)?；', '^主要会计数据.*总资产', '^主要会计数据.*总资产'],
    '净资产': ['^合并资产负债表.*负债[合总]计', '^合并资产负债表.*资产[合总]计'],
    '营业收入': [
        '营业收入[为：:]?.*?元', '实现营业收入.*?元', '营业收入.*?(合计)?；', '营业收入增长率', '^主要会计数据.*营业收入'
    ],
    '营业利润': [
        '营业利润[为：:]?.*?元', '实现营业利润.*?元', '营业利润.*?(合计)?；', '营业利润增长率', '^(合并利润|项目利润|利润表).*营业利润'
    ],
    '净利润': [
        '净利润[为：:]?.*?元', '实现净利润.*?元', '净利润.*?(合计)?；', '^(合并利润|项目利润|利润表).*净利润'
    ],  # 主要财务指标中也有两个净利润如何选择
    '证券代码': ['(证券|公司|股票)代码'],
    '注册地址': ['^(公司信息|基本情况).*?(公司)?注册地址：'],
    '办公地址': ['^(公司信息|基本情况).*?(公司)?办公地址：'],
    '公司地位': ['(公司|社会|行业|技术)(地位|优势)'],
    '证券简称/中文简称': ['^公司信息.*中文简称'],
    '法定代表人': ['^公司信息.*法定代表人'],
    '英文名称': ['^公司信息.*外文名称'],
    '营业外支出': [
        '营业外支出本期发生额', '营业外支出 金额：', '营业外支出.*?(合计)?；(2019|2020|2021)年(度)?',
        '^(合并利润|项目利润|利润表).*营业外支出'
    ],
    '营业外收入': [
        '营业外收入本期发生额', '营业外收入 金额：', '营业外收入.*?(合计)?；(2019|2020|2021)年(度)?',
        '^(合并利润|项目利润|利润表).*营业外收入'
    ],
    '利息支出': [
        '利息((净)?支出|费用).*?(合计)?；本期发生额', '利息(净)?支出.*?(合计)?；(2019|2020|2021)年(度)?', '^(合并利润|项目利润|利润表).*利息费用'
    ],
    '利息收入': [
        '利息(净)?收入.*?(合计)?；本期发生额', '利息(净)?收入.*?(合计)?；(2019|2020|2021)年(度)?', '^(合并利润|项目利润|利润表).*利息(净)?收入'
    ],
    '研发费用': [
        '研发(费用|经费).*?(合计)?；本期发生额', '研发(费用|经费).*?(合计)?；(2019|2020|2021)年(度)?',
        '^(合并利润|项目利润|利润表).*研发费用'
    ],
    '财务费用': [
        '财务费用.*?(合计)；本期发生额', '财务费用.*?(合计)?；(2019|2020|2021)年(度)?', '^(合并利润|项目利润|利润表).*财务费用'
    ],
    '电子邮箱': ['^[公司信息|基本情况].*电子信箱'],
    '公司网址': ['^[公司信息|基本情况].*中国证监会指定网站的网址', '^[公司信息|基本情况].*公司(国际)?(互联网)?网址'],
    '社会责任': ['社会责任'],
    '衍生金融资产': ['^(合并)?资产负债|资产及负债状况.*衍生金融资产'],
    '其他非流动金融资产': ['^((合并)?资产负债|资产及负债状况).*其他非流动金融资产'],
    '营业成本': ['营业成本.*?(合计)?；(2019|2020|2021)年(度)?', '^(合并利润|项目利润|利润表).*营业成本'],
    '无形资产': ['^((合并)?资产负债|资产及负债状况).*无形资产'],
    '货币资金': ['货币资金', '^((合并)?资产负债|资产及负债状况).*货币资金'],
    '会计师事务': ['^(其他[有|相]关资料|(聘请)?的?会计师事务所).*会计师事务'],
    '现金流量': ['现金流(量)?', '现金流(量)?.*?(合计)?；(2019|2020|2021)年(度)?'],
    '研发人员数': ['^员工[数量|情况].*(研发|技术)人员'],
    '技术人员数': ['^员工[数量|情况].*(研发|技术)人员'],
    '管理费用': [
        '管理费用.*?(合计)?；本期发生额', '管理费用.*?(合计)?；(2019|2020|2021)年(度)?',
        '^(合并利润|项目利润|利润表).*管理费用'
    ],
    '资产负债': ['资产(及)?负债.*?总计', '^((合并)?资产负债|资产及负债状况).*负债合计'],
    '职工薪酬': ['(应付)?职工薪酬', '^((合并)?资产负债|资产及负债状况).*职工薪酬'],
    '毛利率': [
        '毛利率', '实现营业收入.*?元|营业收入[：；]', '营业成本.*?(合计)?；', '^(合并利润|项目利润|利润表).*营业成本',
        '^主要会计数据.*营业收入'
    ],
    '固定资产': ['^((合并)?资产负债|资产及负债状况).*固定资产'],
    '投资收益': ['投资收益.*?；', '^(合并利润|项目利润|利润表).*投资(收益|损失)（'],
    '博士人数': ['^(员工[数量|情况]|研发).*(博士|研究生)'],
    '硕士人数': ['^(员工[数量|情况]|研发).*(硕士|研究生)'],
    '速动比率': [
        '^((合并)?资产负债|资产及负债状况).*流动资产合计', '^((合并)?资产负债|资产及负债状况).*存货；',
        '^((合并)?资产负债|资产及负债状况).*流动负债合计'
    ],
    '应收款项融资': ['^((合并)?资产负债|资产及负债状况).*应收款项(融资)?'],
    '收回投资': ['^合并现金流量.*收回投资'],
    '公允价值变动收益': ['^(合并利润|项目利润|利润表).*公允价值变动收益'],
    '三费比重': [
        '销售费用.*?(合计)?；', '管理费用.*?(合计)?；', '财务费用.*?(合计)?；', '实现营业收入.*?元|营业收入[：；]',
        '^(合并利润|项目利润|利润表).*销售费用', '^(合并利润|项目利润|利润表).*管理费用',
        '^(合并利润|项目利润|利润表).*财务费用',
        '^(合并利润|项目利润|利润表).*营业总收入'
    ],
    '销售费用': ['销售费用.*?(合计)?；', '^(合并利润|项目利润|利润表).*销售费用'],
    '主要销售客户': ['(主要)?(销售)?客户', '前.*?名客户', '主要销售客户.*', '前.大客户'],
    '竞争优势': ['(竞争)?优势'],
    '企业名称': ['公司(的)?中文名称', '公司、本公司', '^公司信息.*中文名称'],
    '现金比率': [
        '库存现金.*?(合计)?；', '流动负债合计.*?(合计)?；', '^货币资金.*库存现金', '^((合并)?资产负债|资产及负债状况).*流动负债合计'
    ],
    '职工总数': ['职工总数', '在职员工', '^员工[数量|情况].*员工.*合计'],
    '重大关联交易': ['关联交易', '关联方(销售|采购)'],  # 这个是一整个章节关联交易情况
    '营业税金及附加': ['^(合并利润|项目利润|利润表).*税金及附加'],
    # '费用': ['销售费用.*?(合计)?；', '财务费用.*?(合计)?；', '管理费用.*?(合计)?；', '研发费用.*?(合计)?；']
    '所得税费用': ['^(合并利润|项目利润|利润表).*所得税费用'],
    '股权激励': ['股权激励', '员工持股', '员工激励'],  # 属于正文内容 公司股权激励计划、员工持股计划或其他员工激励措施的实施情况
    '环境信息': ['工作环境'],  # 属于正文内容 环境保护相关的情况|环境信息情况
    '供应商': ['(主要(的)?)?供应商', '前.*?名供应商', '前.大供应商'],
    '每股净资产': [
        '(基本)?每股(净)?资产', '^((合并)?资产负债|资产及负债状况).*归属于母公司所有者权益',
        '^((合并)?资产负债|资产及负债状况).*少数股东权益',
        '^((合并)?资产负债|资产及负债状况).*股本'
    ],
    '每股收益': ['(基本)?每股(净)?收益', '^(合并利润|项目利润|利润表).*基本每股(净)?收益'],
    '每股经营现金流量': [
        '(基本)?每股(净)?收益', '^(合并)?现金流(量)?.*经营活动产生的现金流量净额', '^((合并)?资产负债|资产及负债状况).*股本'
    ],
    '归属母公司所有者净利润': ['^(合并利润|项目利润|利润表).*归属于母公司股东的净利润'],
    '风险情况': ['面临.*?风险'],
    '研发经费占费用比例': [
        '研发(费用|经费).*?(合计)?；', '销售费用.*?(合计)?；', '财务费用.*?(合计)?；', '管理费用.*?(合计)?；'
    ],
    '研发人员占职工人数比例': ['^研发.*研发人员', '^员工[数量|情况].*员工.*合计'],
    '企业硕士及以上人员占职工人数比例': [
        '^员工[数量|情况].*硕士', '^员工[数量|情况].*博士', '^员工[数量|情况].*员工.*合计'
    ],
    '营业利润率': [
        '营业利润.*?(合计)?；', '营业收入.*?(合计)?；', '^(合并利润|项目利润|利润表).*营业利润', '^(合并利润|项目利润|利润表).*营业总收入'
    ],
    '资产负债比率': [
        '负债.*?[总合]计；', '资产.*?[总合]计；', '^((合并)?资产负债|资产及负债状况).*负债[合总]计',
        '^((合并)?资产负债|资产及负债状况).*资产[合总]计'
    ],
    '非流动负债比率': [
        '非流动负债.*?(合计)?；', '负债.*?[总合]计；', '^((合并)?资产负债|资产及负债状况).*负债[合总]计',
        '^((合并)?资产负债|资产及负债状况).*非流动负债.*?(合计)?'
    ],
    '流动负债比率': [
        '^((合并)?资产负债|资产及负债状况).*流动负债.*?(合计)?；', '^((合并)?资产负债|资产及负债状况).*负债.*?[总合]计；'
    ],
    '净资产收益率': [
        '^(合并利润|项目利润|利润表).*净利润.*?(合计)?；', '^((合并)?资产负债|资产及负债状况).*负债[合总]计',
        '^((合并)?资产负债|资产及负债状况).*资产[合总]计'
    ],
    '净利润率': [
        '^(合并利润|项目利润|利润表).*净利润.*?(合计)?；', '^(合并利润|项目利润|利润表).*营业(总)?收入.*?(合计)?；'
    ],
    '营业成本率': [
        '^(合并利润|项目利润|利润表).*营业成本.*?(合计)?；', '^(合并利润|项目利润|利润表).*营业收入.*?(合计)?；'
    ],
    '管理费用率': [
        '^(合并利润|项目利润|利润表).*管理费用.*?(合计)?；', '^(合并利润|项目利润|利润表).*营业收入.*?(合计)?；'
    ],
    '财务费用率': [
        '^(合并利润|项目利润|利润表).*财务费用.*?(合计)?；', '^(合并利润|项目利润|利润表).*营业收入.*?(合计)?；'
    ],
    '投资收益占营业收入比率': [
        '^(合并利润|项目利润|利润表).*投资收益（', '^(合并利润|项目利润|利润表).*营业收入.*?(合计)?；'
    ],
    '研发经费与利润比值': ['研发(费用|经费).*?(合计)?；', '^(合并利润|项目利润|利润表).*净利润'],
    '现金及现金等价物': ['现金及现金等价物余额'],
    '经营情况': ['经营情况'],
    '综合收益总额': ['^(合并利润|项目利润|利润表).*综合收益总额；']
}

SPECIAL_TABLE_PATTERN = '|'.join([
    '股票简称', '中文名称', '中文简称', '办公地址', '释义项', '公司披露年度报告的(证券交易所网站|媒体名称及网址)',
    '常用词语释义', '教育程度类别', '员工(的)?数量', '研发投入', '前五名(客户|供应商)'
])

THEAD_PATTERN = '|'.join([
    '合并利润|项目利润',
    '公司(信息|简介)',
    '[)）、]基本情况',
    '其他[有相]关资料|聘请(的)?会计师事务所'
    '研发(投入|人员情况)',  # 用于查询研发人员的数量
    '货币资金',  # 查询库存现金
    '(?<!母公司)(合并)?现金流(量)?',
    '(?<!母公司)(合并)?资产负债|资产及负债状况',
    '[)）、][职员]工(信息|情况|数量)',
    '(?<!季度)(的)?主要(会计数据|财务指标)',
    '(主要(的)?)?供应商',
    '前.[名大]供应商',
    '前.[大名]客户',
    '主要(销售)?客户',
    '关键审计事项'
])

# 需要计算的指标
CALC_INDEX = {
    '三费比重': '三费比重=(销售费用+管理费用+财务费用)/营业收入',
    '现金比率': '现金比率=货币资金/流动负债',
    '速动比率': '速动比率=(流动资产-存货)/流动负债',
    '流动比率': '流动比率=流动资产/流动负债',
    '研发经费占费用比例': '企业研发经费占费用比例=研发费用/(销售费用+财务费用+管理费用+研发费用)',
    '营业利润率': '营业利润率=营业利润/营业收入',
    '资产负债比率': '资产负债比率=总负债/资产总额',
    '非流动负债比率': '非流动负债比率=非流动负债/总负债',
    '流动负债比率': '流动负债比率=流动负债/总负债',
    '净资产收益率': '净资产收益率=净利润/净资产',
    '净利润率': '净利润率=净利润/营业收入',
    '营业成本率': '营业成本率=营业成本/营业收入',
    '管理费用率': '管理费用率=管理费用/营业收入',
    '财务费用率': '财务费用率=财务费用/营业收入',
    '毛利率': '毛利率=(营业收入-营业成本)/营业收入',
    '投资收益占营业收入比率': '投资收益占营业收入比率=投资收益/营业收入',
    '研发人员占职工人数比例': '研发人员占职工人数比例=研发人数/职工总数',
    '企业硕士及以上人员占职工人数比例': '企业硕士及以上人员占职工人数比例=(硕士人数+博士人数)/职工总数',
    '研发经费与利润比值': '研发经费与利润比值=研发经费/净利润',
    '每股净资产': '(归属于母公司所有者权益-少数股东权益)/股本',
    '每股经营现金流量': '经营活动产生的现金流量净额/股本'
}
