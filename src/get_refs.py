# -*- coding: utf-8 -*-
# @File    : dev.py
# @Time    : 2023/8/3 上午10:03
# @Author  : xinxin.wang@valueonline
import json

# from src.utils import rename_files
# rename_files('/home/data/alltxt')
import multiprocessing
import os.path
import re
import time
from typing import List

import pandas as pd
from tqdm import tqdm

data_path = ['/root/liudi/SMP2023/data/report_data', '/home/data/alltxt']


def is_title(text):
    if re.match('[一二三四五六七八九十]{1,2}、', text):
        return 1
    elif re.match('[0-9]{1,2}、', text):
        return 2
    elif re.match('（[0-9]{1,2}）', text):
        return 3
    elif re.match('\([一二三四五六七八九十]{1,2}\)|[0-9]{1,2}）|[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]', text):
        return 4
    else:
        return 0


def rm_title_ordinal(text):
    text = re.sub('[一二三四五六七八九十]{1,2}、|[0-9]{1,2}、|（[0-9]{1,2}）|\([一二三四五六七八九十]{1,2}\)', '', text)
    text = re.sub('[0-9]{1,2}）|[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]|[0-9]{1,2}\.', '', text)
    return text


# report_data
def get_refs_with_kw_0(company_code, report_date, kw):
    try:
        data = open(os.path.join(data_path[0], f"{company_code}_{report_date}.txt")).readlines()
        data = [l.strip() for l in data]
        res = ['|'.join([data[i], data[i + 1]]) if i + 1 < len(data) else data[i] for i, l in
               enumerate(data) if kw in l]
    except FileNotFoundError:
        res = [f'###{company_code}_{report_date}###']
    return res


# 官方给的
def rm_not_applicable(lines):
    for i in range(len(lines)):
        if lines[i]['inside'] in ['□适用√不适用', '□是√否']:
            lines[i - 1]['inside'] = ''
            lines[i]['inside'] = ''
        elif lines[i]['inside'] in ['√适用□不适用', '√是□否']:
            lines[i]['inside'] = ''
        elif lines[i]['inside'] == '否':
            lines[i - 1]['inside'] = lines[i - 1]['inside'].replace('是否', '不')
            lines[i]['inside'] = ''
        # elif lines[i]['inside'] == '单位：元':
        #     lines[i]['inside'] = ''
    lines = [l for l in lines if l['inside'] != '']
    return lines


# 官方给的
def format_string(line):
    if isinstance(line, str) and '[\'' in line:
        line = eval(line)
    if isinstance(line, List):
        return ','.join([element for element in line if element])
    else:
        return line


# 官方给的
def get_refs_with_kw_1(company_code, report_date, kw):
    try:
        data = open(os.path.join(data_path[1], f"{company_code}_{report_date}.txt"), 'r').readlines()
        data = [json.loads(l) for l in data]
        data = [l for l in data if l and l['type'] not in ['页眉', '页脚']]
        data = rm_not_applicable(data)
        res = ['|'.join([format_string(data[i]['inside']), format_string(data[i + 1]['inside'])]) if i + 1 < len(
            data) else data[i]['inside'] for
               i, l in enumerate(data) if kw in l['inside']]
    except FileNotFoundError:
        res = [f'###{company_code}_{report_date}###']
    return res


def gef_refs_of_line(line):
    idx, line = line
    print(idx)
    if pd.isna(line['年份']) or pd.isna(line['公司']):
        return ''
    if pd.notna(line['包关键词']):
        kw = line['包关键词'].split('|')
    elif pd.notna(line['鑫鑫关键词']):
        kw = line['鑫鑫关键词'].split('|')
    date = line['年份'].split('|')
    ref_texts = []
    for d in date:
        for w in kw:
            ref_texts.extend([f'{d}年 ' + l for l in get_refs_with_kw_0(line['公司'], d, w)])
    return '\n'.join(ref_texts)


def get_finance_indicator(f):
    data = open(os.path.join(data_path[1], f), 'r').readlines()
    data = [json.loads(l) for l in data]
    data = [l for l in data if l and l['type'] not in ['页眉', '页脚']]
    data = rm_not_applicable(data)
    fin_indicators = {}
    flag = 0  # 没遇到excel
    for i, l in enumerate(data):
        if l['type'] == 'excel':
            # 找表的标题
            if flag == 0:
                bias = 1
                if '单位：' in data[i - bias]['inside'] and data[i - bias - 1]['type'] == 'text':
                    bias += 1
                if (is_title(data[i - bias]['inside']) == 0 and len(data[i - bias]['inside']) > 35 or 'http:' in
                    data[i - bias]['inside']) and data[i - bias - 1]['type'] == 'text':
                    bias += 1
                title = data[i - bias]['inside']
                if is_title(title):
                    title = rm_title_ordinal(title)
                fin_indicators.update({title: []})
                flag = 1
            # 找指标
            if isinstance(l['inside'], str) and '[\'' in l['inside']:
                ind = eval(l['inside'])
                ind = ind[1] if (ind[0].isdigit() or ind[0] == '序号') and len(ind) > 1 else ind[0]
                ind = '' if len(ind) > 32 else ind
            else:
                ind = ''
            if ind and title:
                fin_indicators[title].append(ind)
        elif l['inside'] != '(续上表)' and flag == 1:
            flag = 0
    return fin_indicators


if __name__ == '__main__':
    files = os.listdir(data_path[1])
    for f in files:
        finance_indicators = get_finance_indicator(f)
        json.dump(finance_indicators,
                  open(os.path.join('../data/indicator', f.replace('.txt', '.json')), 'w+', encoding='utf-8'),
                  ensure_ascii=False)
# if __name__ == '__main__':
#     question_info = pd.read_csv('../results/question_info_ref1.csv', dtype=str)
#     no_data = []
#     # results = []
#     # question_info['ref_train_data'] = [gef_refs_of_line([idx, l]) for idx, l in tqdm(question_info.iterrows())]
#     # print(no_data)
#
#     process_list = [[id_, c_line] for id_, c_line in question_info.iterrows()]
#     # # insert_a_company(process_list[0])
#     st = time.time()
#     pool = multiprocessing.Pool(processes=15)
#     result = pool.map(gef_refs_of_line, process_list)
#     pool.close()  # 关闭进程池，不再接受新的进程
#     pool.join()
#     print("耗时：", time.time() - st)
#     question_info['ref_report_data_es'] = result
#     question_info.to_csv('../results/question_info_ref1_.csv', index=False)
#     print('ok')
