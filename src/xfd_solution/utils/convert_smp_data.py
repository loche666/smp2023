# -*- coding: utf-8 -*-
# @Desc   : Description of File
# @Licence: (C) Copyright for ValueOnline
# @Author : chen.long
# @Date   : 2023/8/6
import os
import re
import sys
import traceback

from src.xfd_solution.constants.constants import SPECIAL_TABLE_PATTERN, INDEX_PATTERNS, THEAD_PATTERN, \
    ANNUAL_REPORT_PATH
from src.xfd_solution.utils.common_utils import remove_multi_chars

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.xfd_solution.utils.dataset_utils import load_jsonl_data

smp_data_path = '/home/data/alltxt'
tar_data_path = ANNUAL_REPORT_PATH


def extract_txt_patterns():
    """ 生成需要抽取文本类内容的正则
    :return:
    """
    keys = ['主要业务', '社会责任', '主要销售客户', '竞争优势', '供应商', '证券代码', '注册地址', '办公地址',
            '证券简称/中文简称', '法定代表人', '英文名称', '环境信息', '股权激励', '公司地位', '经营情况']
    patterns = '|'.join(['|'.join(val) for key, val in INDEX_PATTERNS.items() if key in keys])
    return patterns


TXT_PATTERNS = extract_txt_patterns()


def refine_row_str(raw_row):
    """优化表格行显示内容，去掉提取无用的信息
    :param raw_row:
    :return:
    """
    row_str = raw_row if not raw_row.endswith('；') else raw_row[:-1]
    row_str = row_str if not row_str.startswith(('：', '；')) else row_str[1:]
    col_list = [c for c in row_str.split('；') if not c.endswith('：')]
    row_str = '；'.join(col_list)
    if '：' not in row_str:
        return ''
    return row_str


def str_2_list(string: str):
    """将表格中行字符串转成列表
    :param string:
    :return:
    """
    string = string.strip('[').strip(']').replace('\'', '')
    return string.split(', ')


def process_table(_table, table_head):
    """将表格处理成“项目：单元格值”形式
    :param table_head:
    :param _table:
    :return:
    """
    # 处理table_head
    table_head = re.sub('|'.join(
        [
            '[(（]?[一二三四五六七八九十][）)]?',
            '[一二三四五六七八九十](、)? ',
            '[(（]\d[)）]([.、])?', '\d、', '20(19|2[01])年1—12月', '20(19|2[01])年12月31日',
            '\d\.\d(\.\d)?', '.*?20(19|2[01])年度报告(（.*?股）)?'
        ]
    ), '', table_head)
    table_head = table_head[1:] if len(table_head) > 1 and table_head[0].isdigit() else table_head
    table_head = table_head[1:] if len(table_head) > 1 and table_head[0].startswith(('、', '.')) else table_head
    table_head = f'{table_head} | ' if table_head != '' else ''

    table_list = []

    # 用于判断表格是否需要特殊处理
    _table_str = '\n'.join(_table)
    if re.search(SPECIAL_TABLE_PATTERN, _table_str) and len([e for e in str_2_list(_table[0]) if e != '']) < 5:
        for row in _table:
            row = [e for e in str_2_list(row) if e != '']
            if len(row) % 2 == 0:
                # 如果表列数为双数，隔列格式化
                for col_index in range(0, len(row), 2):
                    table_list.append(f'{table_head}{row[col_index]}：{row[col_index + 1]}')
            else:
                # 释义项表格
                if re.search('常用词语释义|释义项', _table_str):
                    row = [e for e in row if e != '指']
                    if len(row) == 2:
                        table_list.append(f'{row[0]}：{row[1]}')
    else:
        # 处理表头
        header = str_2_list(_table[0])
        data_row_index = 1

        if '' in header:
            if header.index('') == 0 and len([h for h in header if h != '']) == len(
                    [v for v in str_2_list(_table[1]) if v != '']) - 1:
                # 如果表头比表内容少一列，将原表头作为前缀，与表每行的第一列拼接，作为表头
                header_prefix = [h for h in header if h != '']
                for row in _table[1:]:
                    row = [col for col in str_2_list(row) if col != '']
                    if len(row) - 1 == len(header_prefix):
                        row_str = ''
                        for h, val in zip(header_prefix, row[1:]):
                            row_str += f'{h + row[0]}：{val}；'
                        refine_str = refine_row_str(row_str)
                        if refine_str != '':
                            table_list.append(f'{table_head}{refine_str}')
                return table_list
            else:
                # 表头有两行以上，先填充第一行空列，然后将第一行表头和第二行表头拼接
                rheader = list(reversed(header))
                header = []
                for i, elem in enumerate(rheader[:-1]):
                    if rheader[i] == '' and rheader[i + 1] != '':
                        rheader[i] = rheader[i + 1]
                header_1 = list(reversed(rheader))
                header_2 = str_2_list(_table[1])
                for h1, h2 in zip(header_1, header_2):
                    header.append(f'{h1}{h2}')
                data_row_index = 2

        if len(_table) > data_row_index:
            # 将表头和表内容进行格式化
            for row in _table[data_row_index:]:
                row = str_2_list(row)
                row_str = ''
                for col, c in zip(header, row):
                    row_str += f'{col}：{c}；'
                refine_str = refine_row_str(row_str)
                if refine_str != '':
                    table_list.append(f'{table_head}{refine_str}')
    return table_list


if __name__ == '__main__':
    # 创建目标文件夹
    if not os.path.exists(tar_data_path):
        os.mkdir(tar_data_path)

    fnames = os.listdir(smp_data_path)
    for f_num, fname in enumerate(fnames):
        theader_list = []
        try:
            outlines = []
            lines = load_jsonl_data(os.path.join(smp_data_path, fname))
            lines = [l for l in lines if all([
                l.get('type') in ['text', 'excel'],
                l.get('inside') != ''
            ])]

            # 记录表格内容
            _table = []
            theader = ''
            _content = ''

            # 遍历行处理
            for i, line in enumerate(lines):
                content, _type = line.get('inside'), line.get('type')
                if _type == 'text':
                    if _table:
                        # 如果是子公司相关表格，不进行处理
                        if re.search(THEAD_PATTERN, theader):
                            theader_list.append(theader)
                            outlines.extend(process_table(_table, theader))
                        _table = []
                        theader = ''
                    # NOTE: 文本类目前只保留TXT_PATTERNS包含的信息
                    content = remove_multi_chars(content)
                    if re.search(TXT_PATTERNS, content):
                        outlines.append(content.strip())
                else:
                    # 如果是第一次添加表格，搜索表头信息
                    if not _table:
                        trial = 6
                        for j in range(1, trial + 1):
                            if lines[i - j].get('type') == 'text':
                                theader = lines[i - j].get('inside')
                                if any({
                                    re.search('单位：|[□√]适用[□√]不适用|[□√]是[□√]否|是否|\d{4}年\d月\d日',
                                              theader),
                                    not re.search(THEAD_PATTERN, theader),
                                    theader.endswith('。'),
                                    theader.isdigit()
                                }):
                                    theader = ''
                                    continue
                                else:
                                    # 为了解决类似：”法定代表人：杨炯洋主管会计工作负责人：李斌会计机构负责人：胡小莉3、合并利润表“的问题
                                    if len(theader) > 30 and re.search(THEAD_PATTERN, theader):
                                        spos, epos = re.search(THEAD_PATTERN, theader).span()
                                        theader = theader[spos: epos]
                                    break
                    _table.append(line.get('inside'))

            with open(os.path.join(tar_data_path, fname), 'w', encoding='utf-8') as tar_file:
                tar_file.writelines([f'{line}\n' for line in outlines])
        except Exception:
            print('处理文件%s失败。%s' % (fname, traceback.format_exc()))

        table_num = len(theader_list)
        # 打印抽取可能存在异常的信息
        if table_num < 4:
            print(fname, theader_list, f'【{table_num}】')
