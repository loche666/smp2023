# -*- coding: utf-8 -*-
# @Desc   : Description of File
# @Licence: (C) Copyright for ValueOnline
# @Author : chen.long
# @Date   : 2023/5/8
import json
import logging
import re
from typing import List

from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch
from collections import defaultdict
from tqdm import tqdm

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

console = logging.StreamHandler()
logger.addHandler(console)

# es_index = 'regular_report_smp_192021'
es_index = 'regular_report_split_cxc'
# es_index_add = 'regular_report_split_cxc05~08'

es = Elasticsearch(hosts='172.16.20.220', http_auth=('llm_qa', 'jzzx@123'))
unused_chapter = ['相关公告摘要', '摘要数据报送']
num2char = {"1": "一", '2': '二', '3': '三', '4': '四', '5': '五', '6': '六', '7': '七', '8': '八', '9': '九', '10': '十'}
char2num = {'一': '1', '二': '2', '三': '3', '四': '4', '五': '5', '六': '6', '七': '7', '八': '8', '九': '9', '十': '10'}


class Declare:
    def __init__(self, level_1, level_2, level_3, content, content_id=None, level_0=None):
        self.level_0 = level_0
        self.level_1 = level_1
        self.level_2 = level_2
        self.level_3 = level_3
        self.content = content
        # self.report_id = report_id
        self.content_id = content_id


def remove_multi_chars(string):
    """
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

    if re.fullmatch('\d{1,3}|(不)?适用(。)?|[有无]|[□√]适用 [□√]不适用|[□√] 适用 [□√] 不适用', string):
        return ''
    return string.strip()


def query_from_es(declare_id):
    """
    :param declare_id:
    :return:
    """
    query_body = {
        "track_total_hits": "true",
        "_source": {
            "excludes": [
                "content_full_t",
                "special_industries_name_k",
                "sw_industries_name_k",
                "achievement_type_n",
                "announcement_date_dt",
                "audit_type_k",
                "capital_info_name_k",
                "industries_code_k",
                "industries_name_k",
                "index_create_time_dt",
                "routing",
                "parent_child_t",
                "index_update_time_dt",
                "net_profit_d",
                "operating_income_d",
                "new_flag_k",
                "capitalisation_type_d",
                "display_type_k",
                "profile_content_t"
            ]
        },
        "size": "10000",
        "query": {
            "bool": {
                "must": [
                    {
                        "match_all": {}
                    }
                ],
                "must_not": [],
                "should": [],
                "filter": [
                    {
                        "bool": {
                            "must": [
                                {
                                    "match_all": {}
                                },
                                {
                                    "term": {
                                        "parent_id_k": {
                                            "value": declare_id
                                        }
                                    }
                                },
                                {
                                    "has_parent": {
                                        "parent_type": "parent",
                                        "query": {
                                            "bool": {
                                                "filter": [
                                                    {
                                                        "term": {
                                                            "id": {
                                                                "value": declare_id
                                                            }
                                                        }
                                                    }
                                                ]
                                            }
                                        },
                                        "inner_hits": {
                                            "_source": "report_type_k"
                                        }
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        },
        "sort": [
            "order_i"
        ]
    }

    res = es.search(index=es_index, body=query_body, request_timeout=30)
    res = [r['_source'] for r in res['hits']['hits']]
    # res_add = es.search(index=es_index_add, body=query_body, request_timeout=30)
    # res_add = [r['_source'] for r in res_add['hits']['hits']]
    # res += res_add
    return res


def get_level_id(res, level_1_dict, level_2_dict, level_3_dict):
    """
    :param res:
    :param level_1_dict:
    :param level_2_dict:
    :return:
    """
    for r in res:
        if r["level_k"] == "1":
            level_1_dict[r["id"]] = get_title_text(r)
        elif r["level_k"] == "2":
            level_2_dict[r["id"]] = get_title_text(r)
        elif r["level_k"] == "3":
            level_3_dict[r["id"]] = get_title_text(r)


def get_title_text(r):
    return BeautifulSoup(r["title_t"], features="lxml").text


def delete_invalid_tag(r):
    patterns = [
        # '.*?\.\.\.\.\.\.\.\.\..*',
        '[□√](\\s{1,})?适用(\\s{1,})?[□√](\\s{1,})?不适用',
        '(□||√)(\\s{1,})?是(\\s{1,})?(□||√)(\\s{1,})?否',
        '(□||√)(\\s{1,})?法人(\\s{1,})?(□||√)(\\s{1,})?自然人',
        '(□||√).{1,15}(□||√)',
        '单位[：:](.*)?(([千万])?[元股])',
        '说明：无',
        '币种[：:].{1,5}币',
        '^[0-9]*$', '^如下$',
        '.*?的方框图',
        '审计报告正文|审 计 报 告|.*?[（([]20\d{2}[）)]].*?号',
        '财务附注中报表的单位为：元',
        '概括如下。',
        '其他说明',
        '^(是|否)$',
        '^无$',
        '^说明$',
        '其他变动的内容',
        '\d{1,3}.{0,2}/.{0,2}\d{1,3}',
        '^图\d',
        '.{0,15}情况的说明$',
        '净敞口套期收益：无$',
        '所得税费用$',
        '其他综合收益$',
        '现金流量表项目$',
        '现金流量表补充资料$',
        '所有者权益变动表项目注释$',
        '外币货币性项目$',
        '套期$',
        '政府补助$',
        '其他：无',
        '2022.*(年度报告|年报)-?(正文|全文|修订(版|后)?)?([\(（](?!英文|摘要).*[\)）])?$'

    ]
    patterns_pre = [
        '[□√](\\s{1,})?适用(\\s{1,})?[□√](\\s{1,})?不适用',
        '(□||√)(\\s{1,})?是(\\s{1,})?(□||√)(\\s{1,})?否',
        '(□||√)(\\s{1,})?法人(\\s{1,})?(□||√)(\\s{1,})?自然人',
        '(□||√).{1,10}(□||√)',
        # '单位[：:](.*)?(([千万])?[元股])',
        '^(是|否)$',
        '^无$'
    ]

    for p in r.find_all('p'):
        if re.search('|'.join(patterns_pre), p.text.strip()):
            try:
                pre = p.previous_sibling
                # # 直接将是否等选项加入拼接到句子中
                # pre.string = pre.text + '：' + re.search('((|√)(.{0,10})□)', p.text).group(3)
                # print()
                pre.extract()
            except:
                pass
                # logger.warning('无previous标签')
        if re.search('|'.join(patterns), p.text.strip()):
            p.extract()
        # elif len(p.text) <= 3 and re.search('^[0-9]*$', p.text):
        #     p.extract()


def p_in_table(p):
    if p.attrs.get('id'):
        if 'table' in p.attrs.get('id'):
            return True
        else:
            return False
    else:
        return False


def get_html_content(soup):
    """
    bs4解析html中的文本
    :return:
    """

    def concatenate_sentences_endswith_colon(content_lst):
        """合并不以句号结尾的文本
        :param content_lst:
        :return:
        """
        tmp_contents = []
        tmp_str = ''
        for c in content_lst:
            c = c.strip()
            if c.endswith(('：', ':')) and not c.endswith('。'):
                tmp_str += c
            elif tmp_str != '' and c.endswith('。'):
                tmp_str += c
                tmp_contents.append(tmp_str)
                tmp_str = ''
            else:
                tmp_contents.append(c)
        return tmp_contents

    def concatenate_sentences_startswith_level2_number(content_lst):
        """合并以（1）形式开头的文本
        :param content_lst:
        :return:
        """
        tmp_contents = []
        tmp_str = ''
        num = 0
        for c in content_lst:
            if re.match('[（(][0-9]{1,2}[)）]', c):
                # if re.match('[（(][0-9]{1,2}[)）]|（[一二三四五六七八九十]）|[一二三四五六七八九十]、', c):
                if tmp_str != '':
                    if not re.search('情况$', tmp_str.strip()) and num > 1:
                        tmp_contents.append(tmp_str.strip())
                        tmp_str = ''
                        num = 0
                    else:
                        tmp_str = ''
                        num = 0
                        continue
                tmp_str = c + ' '
                num += 1
            elif tmp_str != '':
                if re.match('[0-9]{1,2}[、.]|（[一二三四五六七八九十]）|[一二三四五六七八九十]、', c):
                    tmp_contents.append(tmp_str.strip())
                    tmp_contents.append(c)
                    tmp_str = ''
                else:
                    tmp_str += c + ' '
            else:
                tmp_contents.append(c)
        else:
            if tmp_str != '' and len(content_lst) > 1 and not re.search('(情况|说明)$', tmp_str):  # 防止只有一个标题的情况被保留
                tmp_contents.append(tmp_str)

        return tmp_contents

    def concatenate_sentences_startswith_level1_number(content_lst):
        """合并以1、形式开头的文本
        :param content_lst:
        :return:
        """
        tmp_contents = []
        tmp_str = ''
        for c in content_lst:
            if re.match('[0-9]{1,2}[、.]', c):
                if tmp_str != '':
                    if not re.search('情况$', tmp_str):
                        tmp_contents.append(tmp_str.strip())
                tmp_str = c + ' '
            elif tmp_str != '':
                if re.match('（[一二三四五六七八九十]）|[一二三四五六七八九十]、', c):
                    tmp_contents.append(tmp_str.strip())
                    tmp_contents.append(c)
                    tmp_str = ''
                else:
                    tmp_str += c + ' '
            else:
                tmp_contents.append(c)
        else:
            if tmp_str != '':
                tmp_contents.append(tmp_str)
        return tmp_contents

    def concatenate_sentences_startswith_level3_number(content_lst):
        """
        合并①这种类型的数据以中远海科2022年报为例
        :param content_lst:
        :return:
        """
        tmp_contents = []
        tmp_str = ''
        for c in content_lst:
            if re.search('①|②|③|④|⑤|⑥|⑦|⑧|⑨|⑩', c):
                if tmp_str != '':
                    tmp_contents.append(tmp_str)
                    tmp_str = ''
                    tmp_str += c + " "
                else:
                    tmp_str += c + " "

            else:
                if tmp_str == '':
                    tmp_contents.append(c)
                else:
                    tmp_str += c + " "
        else:
            if tmp_str != '':
                tmp_contents.append(tmp_str)
        return tmp_contents

    content_p = []
    ps = soup.find_all('p')
    for p in ps:
        if not p_in_table(p):
            content_p.append(p)

    contents = [p.text for p in content_p]

    # 后处理：根据结尾为冒号的规则合并句子
    contents = concatenate_sentences_endswith_colon(contents)

    # 后处理：开头为数字的规则合并句子
    contents = concatenate_sentences_startswith_level2_number(contents)
    contents = concatenate_sentences_startswith_level1_number(contents)
    contents = concatenate_sentences_startswith_level3_number(contents)
    # for c in contents:
    #     if len(c) > 512:
    #         tmp_contents = [f'{c}。' for c in c.split('。') if c != '']
    #         flatten_contents.extend(tmp_contents)
    #     else:
    #         flatten_contents.append(c)

    return [remove_multi_chars(c) for c in contents if len(remove_multi_chars(c)) > 5]


def tables2texts(soup, flag):
    """
   :param soup:
   :return:
   """
    content_table = []
    # 删除页码标签
    for p in soup.find_all("p", attrs={"class": "pageNumber"}):
        p.extract()
    soup = BeautifulSoup(str(soup).replace('</table><br/><table>', ''), features='lxml')
    delete_invalid_tag(soup)
    _tables = soup.find_all('table')
    # 如果不进行表格解析，只需要删除表格上方的描述信息
    if not flag:
        for _table in _tables:
            if _table.previous_sibling and _table.previous_sibling.name == 'p':
                if len(_table.previous_sibling.text) < 30:
                    p_tag = _table.previous_sibling
                    p_tag.extract()
        return content_table, soup

    def row_split(_table):
        """
        合并行拆分
        :param _table:
        :return:
        """
        max_rowspan = 0
        merge_flag = False  # 表头是否需要merge
        for idx_tr, tr in enumerate(_table.contents):
            for idx_td, td in enumerate(tr.find_all('td')):
                cur_rowspan = td.get('rowspan')
                if cur_rowspan:
                    try:
                        cur_rowspan = int(cur_rowspan)
                    except:
                        logger.error('rowspan标签有问题')
                        continue
                    if idx_tr == 0:
                        merge_flag = True
                    if cur_rowspan > max_rowspan:
                        max_rowspan = cur_rowspan

                    for i in range(1, cur_rowspan):
                        # todo 有可能会超range
                        new_tag = BeautifulSoup("", 'lxml').new_tag("td")
                        if td.string is not None:
                            new_tag.string = td.string
                        else:
                            new_tag.string = ''
                        try:
                            if idx_td < len(_table.contents[idx_tr + i].find_all('td')):
                                td1 = _table.contents[idx_tr + i].find_all('td')[idx_td]
                                td1.insert_before(new_tag)
                            else:
                                td1 = _table.contents[idx_tr + i].find_all('td')[-1]
                                td1.insert_after(new_tag)
                        except:
                            logger.error('表格行拆分出错')
                            continue
        return merge_flag, max_rowspan

    def col_split(_table):
        """
        合并列拆分
        :param _table:
        :return:
        """
        # 拆分列
        for idx_tr, tr in enumerate(_table.contents):
            for idx_td, td in enumerate(tr.find_all('td')):
                if td.get('colspan'):
                    for i in range(1, int(td.get('colspan'))):
                        new_tag = BeautifulSoup("", 'lxml').new_tag("td")
                        if td.string is not None:
                            new_tag.string = td.string
                        else:
                            new_tag.string = ''
                        td.insert_after(new_tag)

    def head_merge(merge_flag, max_rowspan):
        """
        多表头合并
        :param merge_flag:
        :param rowspan:
        :return:
        """
        if merge_flag:
            for i in range(1, max_rowspan):
                for j, row in enumerate(_table.contents[i].find_all('td')):
                    try:
                        if row.string != _table.contents[i - 1].find_all('td')[j].string:
                            row.string = _table.contents[i - 1].find_all('td')[j].text + row.text
                    except:
                        print('表头合并出问题：{}'.format(row.string))
            _table.contents = _table.contents[max_rowspan - 1:]

    for _table in _tables:
        try:
            if not _table.contents[0].find_all('td'):
                continue
        except:
            logger.error('表格解析存在问题')
            continue
        if re.search('释义项', _table.contents[0].find_all('td')[0].text):
            continue
        if _table.previous_sibling and _table.previous_sibling.name == 'p':
            if len(_table.previous_sibling.text) < 30 and not re.search('图.\d', _table.previous_sibling.text):
                joint_text = _table.previous_sibling.text
                p_tag = _table.previous_sibling
                p_tag.extract()
            else:
                joint_text = ''
        else:
            joint_text = ''
        if len(_table.contents) > 1:
            head_td = _table.contents[0].find_all('td')
            line_td = _table.contents[1].find_all('td')
            if re.search('报告期末普通股股东总数|公司及其子公司对外担保情况|主营业务分行业情况|公司股票简况|母公司在职员工|研发人员学历结构|^基本情况$|公司研发人员的数量',
                         _table.contents[0].find_all('td')[0].text.strip()):
                while len(_table.contents) > 0:
                    ls_td = []
                    try:
                        row = _table.contents[0]
                    except:
                        logger.warning('表已清空')
                        continue
                    if len(row.find_all('td')) > 1:
                        for td in row.find_all('td'):
                            ls_td.append(td.text)
                        table_txt = joint_text + '，'.join(ls_td)
                        content_table.append(remove_multi_chars(table_txt))
                        row.extract()
                    else:
                        break
                if len(_table.contents) > 1:
                    joint_text = _table.contents[0].find_all('td')[0].text
                    _table.contents = _table.contents[1:]
                    while len(_table.contents) > 1:
                        for row in _table.contents[1:]:
                            if len(row.find_all('td')) > 1:
                                if row.text.strip() == '':
                                    row.extract()
                                    continue
                                table_txt_sub = joint_text
                                for idx, row_sub in enumerate(_table.contents[0].find_all('td')):
                                    try:
                                        key_name = row_sub.text.strip()
                                        val = row.find_all('td')[idx].text.strip()
                                        if val != '' and key_name not in ['序号']:
                                            if idx == len(_table.contents[0].find_all('td')) - 1:
                                                table_txt_sub += '{}：{}'.format(key_name, val)
                                            else:
                                                if key_name == '':
                                                    table_txt_sub += '{} '.format(val)
                                                else:
                                                    table_txt_sub += '{}：{}；'.format(key_name, val)
                                    except:
                                        pass
                                        # logger.error('表格抽取出问题：{}'.format(row_sub.text))
                                content_table.append(remove_multi_chars(table_txt_sub))
                                row.extract()
                            else:
                                joint_text = row.find_all('td')[0].text
                                _table.contents[0].extract()
                                row.extract()
                                break

            elif head_td[0].text.strip() in ['股票简称'] or len(
                    head_td) == 2 and not re.search(
                '账.{0,3}龄|事项概述|项.{0,5}目|销售模式|其他关联方名称|授予日权益工具公允价值的确定方法|专门委员会类别|纳税主体名称|合营或联营企业名称|时期',
                head_td[0].text.strip()) and len(head_td) == len(line_td):
                for row in _table.contents:
                    ls_td = []
                    for td in row.find_all('td'):
                        ls_td.append(td.text)
                    table_txt = joint_text + '，'.join(ls_td)
                    content_table.append(remove_multi_chars(table_txt))
            else:
                if len(_table.contents) < 2:
                    continue
                if _table.contents[0].find_all('td') == 1:
                    joint_text = _table.contents[0].find_all('td')[0].text
                    _table.contents = _table.contents[1:]
                merge_flag, max_rowspan = row_split(_table)
                col_split(_table)
                head_merge(merge_flag, max_rowspan)
                for row in _table.contents[1:]:
                    # if len(row.find_all('td')) == 1:
                    #     continue
                    if re.search('分行业.*分行业|分产品.*分产品|分地区.*分地区|分销售模式.*分销售模式', row.text):
                        continue
                    # 表中一行只有表头有文本的去除
                    try:
                        if row.find_all('td')[0].text.strip() == row.text.strip():
                            continue
                    except:
                        logger.error('表格有问题')
                        continue
                    table_txt_sub = joint_text
                    for idx, row_sub in enumerate(_table.contents[0].find_all('td')):
                        try:
                            key_name = row_sub.text.strip()
                            val = row.find_all('td')[idx].text.strip()
                            if val != '' and key_name not in ['序号']:
                                if idx == len(_table.contents[0].find_all('td')) - 1:
                                    table_txt_sub += '{}：{}'.format(key_name, val)
                                else:
                                    if key_name == '':
                                        table_txt_sub += '{} '.format(val)
                                    else:
                                        table_txt_sub += '{}：{}；'.format(key_name, val)
                        except:
                            pass
                            # logger.error('表格抽取出问题：{}'.format(row_sub.text))
                    content_table.append(remove_multi_chars(table_txt_sub))

    return content_table, soup


def get_level_all(res, level_1_dict, level_2_dict):
    """
    :param res:
    :param level_1_dict:
    :param level_2_dict:
    :return:
    """
    table_list = []
    declare_list = []
    chapter_num = "一"
    flag = 1  # 用于区分是否需要章节的表
    flag_content = 1  # 用于去除第一章的数据，第一章文本无用

    for idx, r in enumerate(res):

        level_1_title = ""
        level_2_title = ""
        if r["level_k"] == "0":
            # 标题0默认没有表格
            content_list, soup = tables2texts(BeautifulSoup(r["content_t"], features="lxml"), flag)
            content_list = get_html_content(soup)
            declare_list.append(Declare(None, None, None, content_list))

        if r["level_k"] == "1":
            content_list, soup = tables2texts(BeautifulSoup(r["content_t"], features="lxml"), flag)
            content_list = get_html_content(soup)
            declare_list.append(Declare(get_title_text(r), None, None, content_list))

        if r["level_k"] == "2":
            content_list, soup = tables2texts(BeautifulSoup(r["content_t"], features="lxml"), flag)
            for id in r["parent_id_k"]:
                if id in level_1_dict:
                    level_1_title = level_1_dict[id]
            if flag == 1:
                table_list.append(Declare(level_1_title, get_title_text(r), None, content_list, r.get('id')))

            content_list = get_html_content(soup)
            for id in r["parent_id_k"]:
                if id in level_1_dict:
                    level_1_title = level_1_dict[id]
            declare_list.append(Declare(level_1_title, get_title_text(r), None, content_list, r.get('id')))

        elif r["level_k"] == "3":
            content_list, soup = tables2texts(BeautifulSoup(r["content_t"], features="lxml"), flag)
            for id in r["parent_id_k"]:
                if id in level_1_dict:
                    level_1_title = level_1_dict[id]
                if id in level_2_dict:
                    level_2_title = level_2_dict[id]
            if flag == 1:
                table_list.append(Declare(level_1_title, level_2_title, get_title_text(r), content_list, r.get('id')))

            content_list = get_html_content(soup)
            for id in r["parent_id_k"]:
                if id in level_1_dict:
                    level_1_title = level_1_dict[id]
                if id in level_2_dict:
                    level_2_title = level_2_dict[id]
            declare_list.append(Declare(level_1_title, level_2_title, get_title_text(r), content_list, r.get('id')))
    table_list = [t for t in table_list if len(t.content) > 0]
    declare_list = [d for d in declare_list if len(d.content) > 0]

    return [d for d in table_list if not d.level_1 or not re.search('|'.join(unused_chapter), d.level_1)], \
           [d for d in declare_list if not d.level_1 or not re.search('|'.join(unused_chapter), d.level_1)]


def convert_to_text(declare_objs):
    """根据_type（段落、表格）将对象转换为文本列表
    :param declare_objs:
    :param _type:
    :param title_2_contents:
    :return:
    """
    # text_list = []
    content_list, title_list, content_id_list = [], [], []
    # title_2_contents = {} if title_2_contents is None else title_2_contents
    for declare_obj in declare_objs:
        level1_title = re.sub('.*?[章节]', '', declare_obj.level_1) if declare_obj.level_1 else ''
        level2_title = re.sub('(([1-9])?[0-9]|(一|二|三|四|五|六|七|八|九|十|十一|十二|十三|十四|十五))、|（.*?）', '',
                              declare_obj.level_2) if declare_obj.level_2 else ''
        level3_title = re.sub('(([1-9])?[0-9]|(一|二|三|四|五|六|七|八|九|十|十一|十二|十三|十四|十五))、|（.*?）', '',
                              declare_obj.level_3) if declare_obj.level_3 else ''
        if level3_title != '':
            # title = remove_multi_chars(f'{level1_title} {level2_title} {level3_title}')
            title = remove_multi_chars(level3_title)
        elif level2_title != '':
            title = remove_multi_chars(level2_title)
        elif level1_title != '':
            title = remove_multi_chars(level1_title)
        else:
            continue
        content_list.extend([c for c in declare_obj.content])
        title_list.extend([title for _ in declare_obj.content])
        content_id_list.extend(declare_obj.content_id for _ in declare_obj.content)
        # if title in title_2_contents:
        #     title_2_contents[title].extend([c for c in declare_obj.content])
        # else:
        #     title_2_contents.update({title: [c for c in declare_obj.content]})
        # if _type == 'paragraph':
        #     if title in title2contents.keys():
        #         # title2contents[title].append('\n'.join([c for c in declare_obj.content]))
        #         title2contents[title].extend([c for c in declare_obj.content])
        #     else:
        #         # title2contents[title] = ['\n'.join([c for c in declare_obj.content])]
        #         title2contents[title] = [c for c in declare_obj.content]
        # elif _type == 'table':
        #     if title in title2contents.keys():
        #         title2contents[title].extend([c for c in declare_obj.content])
        #     else:
        #         title2contents[title] = [c for c in declare_obj.content]
    return content_list, title_list, content_id_list


def query_declare_ids(company_codes=None):
    """查询最新一年的年报数据id
    :return:
    """
    query_body = {
        # "_source": ["company_name_t", "id", "report_title_name_k", "announcement_date_dt", "company_code_k"],
        "size": 10000,
        "query": {
            "bool": {
                "must": [
                    {"bool": {"should": [{
                        "term": {
                            "report_type_k": {
                                "value": "0"
                            }
                        }
                    }, {
                        "term": {
                            "report_type_k": {
                                "value": "0"
                            }
                        }
                    }]}},
                    {
                        "term": {
                            "level_k": {
                                "value": "-1"
                            }
                        }
                    }
                ]
            }
        }
    }

    if company_codes:
        _body = {
            "bool": {
                "should": []
            }
        }
        for code in company_codes:
            _body.get('bool').get('should').append({
                "term": {
                    "company_code_k": {
                        "value": code
                    }
                }
            })
        query_body['query']['bool']['must'] = _body
    try:
        res = es.search(index=es_index, body=query_body, request_timeout=30)
        res = [r['_source'] for r in res['hits']['hits']]
        # res_add = es.search(index=es_index_add, body=query_body, request_timeout=30)
        # res_add = [r['_source'] for r in res_add['hits']['hits']]
        # res += res_add
        return res
    except Exception as e:
        print(e)
        return []


def query_report_data(report_id, save_map_id=False):
    """ 基于公司代码文本化年报数据
    :param save_map_id:
    :param report_id:年报id AN开头的唯一标识
    :return:
    """
    res = query_from_es(report_id)

    # 分别存储一级和二级的id和标题
    level_1_dict = {}
    level_2_dict = {}
    level_3_dict = {}
    ls_map_id = []  # 用于保存东财表对应年报id
    get_level_id(res, level_1_dict, level_2_dict, level_3_dict)
    # 获取表格和文本内容
    declare_tables, declare_paragraphs = get_level_all(res, level_1_dict, level_2_dict)

    # 将列表转换为文本
    declare_paragraphs.extend(declare_tables)
    content_list, title_list, content_id_list = convert_to_text(declare_paragraphs)
    return content_list, title_list, content_id_list, ls_map_id


if __name__ == '__main__':
    # 查询公告id
    # data = query_declare_ids(['001219'])
    ids = query_declare_ids()

    for obj in tqdm(ids):
        # print(json.dumps(obj, ensure_ascii=False))
        # 查询并解析公告内容
        title2contents = defaultdict(list)
        _id, company_name, company_code, report_title = obj.get('id'), obj.get('company_name_t'), \
                                                        obj.get('company_code_k'), obj.get('report_title_name_k')
        if re.search('.*(2019|2020|2021).*年度报(告)?$', report_title):
            announce_year = re.search('.*(2019|2020|2021).*年度报(告)?$', report_title).group(1)
        else:
            continue
        # 根据查询的公司代码文本化年报数据
        content_list, title_list, content_id_list, ls_map_id = query_report_data(_id)

        # 将结果转成文件格式
        with open(f'../../data/report_data/{company_code}_{announce_year}.txt', 'w',
                  encoding='utf-8') as output:
            for row in content_list:
                output.write(row + '\n')
