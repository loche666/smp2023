# -*- coding: utf-8 -*-
# @Desc   : Description of File
# @Licence: (C) Copyright for ValueOnline
# @Author : chen.long
# @Date   : 2023/8/1
import json
import os.path
import re
from typing import List, Dict

from src.xfd_solution.constants.constants import DATA_PATH, INDEX_PATTERNS, CALC_INDEX, ANNUAL_REPORT_PATH
from src.xfd_solution.utils.embedding_utils import SimilarityModel


def is_float(string: str) -> bool:
    """判断字符串是否为浮点数
    :param string:
    :return:
    """
    try:
        float(string)
        return True
    except ValueError:
        return False


def str_2_float(form: str) -> float:
    """基于给定的公式字符串，计算结果
    :param form:
    :return:
    """
    form = form.split('=')[1]
    fenzi, fenmu = form.split('/')

    def _sum(tmp_num):
        sum_num = 0
        # 如果分子是相加形式
        if tmp_num.startswith('('):
            tmp_num = tmp_num.strip('(').strip(')')
            tmp_num = [e for e in tmp_num.split('+')]
            sum_num += sum([float(e) for e in tmp_num if '-' not in e])
            tmp_num = [e for e in tmp_num if '-' in e]
            if len(tmp_num) == 1:
                tmp_num = ([float(e) for e in tmp_num[0].split('-') if e != ''])
                _tmp_sum = tmp_num[0]
                for i in range(1, len(tmp_num)):
                    _tmp_sum -= tmp_num[i]
                sum_num += _tmp_sum
                return sum_num
            elif len(tmp_num) == 0:
                return sum_num
            else:
                print('无法处理加减混合运算')
                raise ValueError
        else:
            try:
                return float(tmp_num)
            except ValueError:
                return -1

    fenzi = _sum(fenzi)
    fenmu = _sum(fenmu)
    return fenzi / fenmu


def extract_index_for_calculation(model, index_name: str, year: str, info: List) -> List:
    """基于抽取文本，进一步抽取指标，用于计算
    :param model:
    :param index_name:
    :param year:
    :param info:
    :return:
    """

    content = list(set(model.range(f'{year}年{index_name}合计：×××。', info, 1)))
    year = int(year)

    join_str = ''
    # 用于计算增长率
    current_val = None
    last_val = None

    contents = content[0].split('；') if content else []
    # 基本信息，或员工人数相关
    if len(contents) == 1 and re.search('(基本)?(信息|情况)|人员|[职员]工|[博硕]士', contents[0]) and '：' in contents[
        0]:
        return [f"{year}年{index_name}：{contents[0].split('：')[1].strip()}；"]

    if contents:
        for c in contents:
            # TODO: 未考虑问题年份与year不同；抽取存在错误问题
            if re.search(f'{year}(\s)?年|本期.*?：|期末', c):
                try:
                    val = c.split('：')[1].replace(',', '').strip()
                    join_str += f'{year}年{index_name}：{val}；'
                    current_val = val
                except Exception:
                    continue

            if re.search(f'{year - 1}(\s)?年|上[期年].*?：|期初', c):
                try:
                    val = c.split('：')[1].replace(',', '').strip()
                    join_str += f'{year - 1}年{index_name}：{val}；'
                    last_val = val
                except Exception:
                    continue

            if re.search(f'{year - 2}(\s)?年', c):
                try:
                    val = c.split('：')[1].replace(',', '').strip()
                    join_str += f'{year - 2}年{index_name}：{val}；'
                except Exception:
                    continue

        if join_str != '':
            if current_val and last_val and is_float(last_val) and float(last_val) != 0:
                try:
                    ratio = round(((float(current_val) - float(last_val)) / float(last_val)) * 100, 2)
                    join_str += f'{index_name}增长率：{ratio}%；'
                    return [join_str]
                except ValueError:
                    return [join_str]
            return [join_str]
        else:
            return content
    else:
        return content


def read_json_line(path):
    data = open(path, 'r', encoding='utf-8').readlines()
    if data:
        data = [json.loads(line.strip())['question'] for line in data]
    return data


def get_stopwords(lang_id):
    multi_stopwords = json.load(open(os.path.join(DATA_PATH, 'multi_stopwords.json')))
    return multi_stopwords[lang_id]


def refine_index(raw_index: str) -> str:
    """对glm返回的结果进行进一步处理
    :param raw_index:
    :return:
    """
    raw_index = raw_index.strip()
    if raw_index.startswith(('：', '\"')):
        raw_index = raw_index[1:]
    if raw_index.endswith(('。', '\"')):
        raw_index = raw_index[:-1]
    if 'NULL' in raw_index or re.search('抱歉|提供答案|无法回答', raw_index):
        raw_index = ''
    return raw_index


def calculate_index(key, year, need_info: List, need_index: int, form: str):
    """基于抽取指标，计算问题中的指标
    :param year:
    :param key:
    :param need_info:
    :param need_index:
    :param form:
    :return:
    """
    indexes = {}
    if not len(list(set(need_info))) == need_index:
        return '\n'.join(need_info)

    # 抽取指标
    for i in need_info:
        res = re.findall(f'{year}年(.*?)：(.*?)；', i)
        if res:
            indexes[res[0][0]] = res[0][1].replace(',', '')

    # 替换公式的文字
    for k, v in indexes.items():
        form = form.replace(k, v)

    # 带入公式计算
    try:
        res = str_2_float(form)
        if not re.search('比[值例]|速动比率|流动比率|每股净资产|每股经营现金流量', key):
            return f'{round(res * 100, 2)}%'
        elif key == '每股经营现金流量':
            return str(round(res, 3))
        elif key == '每股净资产':
            return str(round(res, 4))
        else:
            return str(round(res, 2))
    except Exception:
        return '\n'.join(need_info)


def get_company_info(fname: str, index_key: List, s_model: SimilarityModel, year: str) -> Dict:
    """ 基于公司年报解析文件、关键词召回年报内容，和向量模型，对候选内容进行精排序
    :param year:
    :param fname:
    :param index_key:
    :param s_model:
    :return:
    """
    info_dict = {}
    with open(os.path.join(ANNUAL_REPORT_PATH, f'{fname}.txt'), 'r',
              encoding='utf-8') as report:
        lines = report.readlines()

    # 抽取年报相关指标候选
    for key in index_key:
        pattern = INDEX_PATTERNS.get(key)
        for line in lines:
            res = re.search('|'.join(pattern), line)
            if res:
                if info_dict.get(key):
                    info_dict.get(key).append(line)
                else:
                    info_dict[key] = [line]
        if not info_dict.get(key):
            info_dict[key] = []

    # 基于chatglm抽取相关指标
    index_dict = {}
    for key, info in info_dict.items():
        info = [i for i in info if len(i) < 1000]
        if info:
            # 基于Embedding精排序
            if key in CALC_INDEX.keys():
                if key == '现金比率':
                    _info = extract_index_for_calculation(s_model, '货币资金', year, info)
                    _info.extend(extract_index_for_calculation(s_model, '流动负债', year, info))
                    index_dict[f'{year}年{key}'] = calculate_index(key, year, _info, 2, CALC_INDEX.get(key))
                elif key == '三费比重':
                    _info = extract_index_for_calculation(s_model, '销售费用', year, info)
                    _info.extend(extract_index_for_calculation(s_model, '管理费用', year, info))
                    _info.extend(extract_index_for_calculation(s_model, '财务费用', year, info))
                    _info.extend(extract_index_for_calculation(s_model, '营业收入', year, info))
                    index_dict[f'{year}年{key}'] = calculate_index(key, year, _info, 4, CALC_INDEX.get(key))
                elif key == '速动比率':
                    _info = extract_index_for_calculation(s_model, '流动资产', year, info)
                    _info.extend(extract_index_for_calculation(s_model, '存货', year, info))
                    _info.extend(extract_index_for_calculation(s_model, '流动负债', year, info))
                    index_dict[f'{year}年{key}'] = calculate_index(key, year, _info, 3, CALC_INDEX.get(key))
                elif key == '流动比率':
                    _info = extract_index_for_calculation(s_model, '流动资产', year, info)
                    _info.extend(extract_index_for_calculation(s_model, '流动负债', year, info))
                    index_dict[f'{year}年{key}'] = calculate_index(key, year, _info, 2, CALC_INDEX.get(key))
                elif key == '研发经费占费用比例':
                    _info = extract_index_for_calculation(s_model, '研发费用', year, info)
                    _info.extend(extract_index_for_calculation(s_model, '销售费用', year, info))
                    _info.extend(extract_index_for_calculation(s_model, '财务费用', year, info))
                    _info.extend(extract_index_for_calculation(s_model, '管理费用', year, info))
                    index_dict[f'{year}年{key}'] = calculate_index(key, year, _info, 4, CALC_INDEX.get(key))
                elif key == '营业利润率':
                    _info = extract_index_for_calculation(s_model, '营业利润', year, info)
                    _info.extend(extract_index_for_calculation(s_model, '营业收入', year, info))
                    index_dict[f'{year}年{key}'] = calculate_index(key, year, _info, 2, CALC_INDEX.get(key))
                elif key == '资产负债比率':
                    _info = extract_index_for_calculation(s_model, '总负债', year, info)
                    _info.extend(extract_index_for_calculation(s_model, '资产总额', year, info))
                    index_dict[f'{year}年{key}'] = calculate_index(key, year, _info, 2, CALC_INDEX.get(key))
                elif key == '非流动负债比率':
                    _info = extract_index_for_calculation(s_model, '非流动负债', year, info)
                    _info.extend(extract_index_for_calculation(s_model, '总负债', year, info))
                    index_dict[f'{year}年{key}'] = calculate_index(key, year, _info, 2, CALC_INDEX.get(key))
                elif key == '流动负债比率':
                    _info = extract_index_for_calculation(s_model, '流动负债', year, info)
                    _info.extend(extract_index_for_calculation(s_model, '总负债', year, info))
                    index_dict[f'{year}年{key}'] = calculate_index(key, year, _info, 2, CALC_INDEX.get(key))
                elif key == '净资产收益率':
                    _info = extract_index_for_calculation(s_model, '净利润', year, info)
                    _info.extend(extract_index_for_calculation(s_model, '净资产', year, info))
                    index_dict[f'{year}年{key}'] = calculate_index(key, year, _info, 2, CALC_INDEX.get(key))
                elif key == '净利润率':
                    _info = extract_index_for_calculation(s_model, '净利润', year, info)
                    _info.extend(extract_index_for_calculation(s_model, '营业收入', year, info))
                    index_dict[f'{year}年{key}'] = calculate_index(key, year, _info, 2, CALC_INDEX.get(key))
                elif key == '营业成本率':
                    _info = extract_index_for_calculation(s_model, '营业成本', year, info)
                    _info.extend(extract_index_for_calculation(s_model, '营业收入', year, info))
                    index_dict[f'{year}年{key}'] = calculate_index(key, year, _info, 2, CALC_INDEX.get(key))
                elif key == '管理费用率':
                    _info = extract_index_for_calculation(s_model, '管理费用', year, info)
                    _info.extend(extract_index_for_calculation(s_model, '营业收入', year, info))
                    index_dict[f'{year}年{key}'] = calculate_index(key, year, _info, 2, CALC_INDEX.get(key))
                elif key == '财务费用率':
                    _info = extract_index_for_calculation(s_model, '财务费用', year, info)
                    _info.extend(extract_index_for_calculation(s_model, '营业收入', year, info))
                    index_dict[f'{year}年{key}'] = calculate_index(key, year, _info, 2, CALC_INDEX.get(key))
                elif key == '毛利率':
                    _info = extract_index_for_calculation(s_model, '营业收入', year, info)
                    _info.extend(extract_index_for_calculation(s_model, '营业成本', year, info))
                    index_dict[f'{year}年{key}'] = calculate_index(key, year, _info, 2, CALC_INDEX.get(key))
                elif key == '投资收益占营业收入比率':
                    _info = extract_index_for_calculation(s_model, '投资收益', year, info)
                    _info.extend(extract_index_for_calculation(s_model, '营业收入', year, info))
                    index_dict[f'{year}年{key}'] = calculate_index(key, year, _info, 2, CALC_INDEX.get(key))
                elif key == '研发人员占职工人数比例':
                    _info = extract_index_for_calculation(s_model, '研发人数', year, info)
                    _info.extend(extract_index_for_calculation(s_model, '职工总数', year, info))
                    index_dict[f'{year}年{key}'] = calculate_index(key, year, _info, 2, CALC_INDEX.get(key))
                elif key == '企业硕士及以上人员占职工人数比例':
                    _info = extract_index_for_calculation(s_model, '硕士人数', year, info)
                    _info.extend(extract_index_for_calculation(s_model, '博士人数', year, info))
                    _info.extend(extract_index_for_calculation(s_model, '职工总数', year, info))
                    index_dict[f'{year}年{key}'] = calculate_index(key, year, _info, 3, CALC_INDEX.get(key))
                elif key == '研发经费与利润比值':
                    _info = extract_index_for_calculation(s_model, '研发经费', year, info)
                    _info.extend(extract_index_for_calculation(s_model, '净利润', year, info))
                    index_dict[f'{year}年{key}'] = calculate_index(key, year, _info, 2, CALC_INDEX.get(key))
                elif key == '每股净资产':
                    _info = extract_index_for_calculation(s_model, '归属于母公司所有者权益', year, info)
                    _info.extend(extract_index_for_calculation(s_model, '少数股东权益', year, info))
                    _info.extend(extract_index_for_calculation(s_model, '股本', year, info))
                    index_dict[f'{year}年{key}'] = calculate_index(key, year, _info, 3, CALC_INDEX.get(key))
                elif key == '每股经营现金流量':
                    _info = extract_index_for_calculation(s_model, '经营活动产生的现金流量净额', year, info)
                    _info.extend(extract_index_for_calculation(s_model, '股本', year, info))
                    index_dict[f'{year}年{key}'] = calculate_index(key, year, _info, 2, CALC_INDEX.get(key))
                else:
                    pass
            else:
                info = extract_index_for_calculation(s_model, key, year, info)
                info = list(set([i[:200] for i in info]))
                index_dict[f'{year}年{key}'] = info[0] if info else '-'
    return index_dict


def remove_multi_chars(string):
    """ 公司基础数据解析需要过滤的内容
    :param string:
    :return:
    """
    if string.endswith(','):
        string = string[:-1]
    while '  ' in string:
        string = string.replace('  ', ' ')
    while '||' in string:
        string = string.replace('||', '|')
    while '\n\n' in string:
        string = string.replace('\n\n', '\n')

    if re.fullmatch('\d{1,3}|(不)?适用(。)?|[有无]|[□√]适用[□√]不适用|[□√]是[□√]否|单位：元', string):
        return ''
    if re.match('([（(])?(一|二|三|四|五|六|七|八|九|十|十一|十二|十三|十四)[)）]?(、)?|第.*?[章节]|\(\d\)\.', string):
        return ''
    if re.match('\d{1,3}[、\.]|（\d{1,3}）', string):
        return ''
    return string.strip()
