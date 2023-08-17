# -*- coding: utf-8 -*-
# @Desc   : Description of File
# @Licence: (C) Copyright for ValueOnline
# @Author : chen.long
# @Date   : 2023/8/1
import json
import os
import re
import sys
import time

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.xfd_solution.utils.chatgpt_utils import ChatGPT_35
from src.xfd_solution.utils.common_utils import get_company_info
from src.xfd_solution.utils.embedding_utils import SimilarityModel
from src.xfd_solution.utils.chatglm_utils import ChatGlm2
from src.xfd_solution.constants.constants import GLM_PATH, DATA_PATH, M3E_PATH, INDEX_PATTERNS, ROOT_PATH, CALC_INDEX
from src.xfd_solution.utils.dataset_utils import save_answers, load_jsonl_data, save_analysis

if __name__ == '__main__':
    # 当前时间
    ts = int(time.time())

    # 选择大模型引擎：ChatGLM、ChatGPT
    llm = ['ChatGLM', 'ChatGPT'][1]

    if llm == 'ChatGPT':
        model = ChatGPT_35()
    else:
        model = ChatGlm2(GLM_PATH, device='0')

    # 加载模型
    s_model = SimilarityModel(M3E_PATH)

    # 指标列表
    index_list = list(INDEX_PATTERNS.keys())
    # 指标向量化数组
    index_vecs = s_model.encode(index_list)

    # 加载测试数据集
    dt = load_jsonl_data(os.path.join(DATA_PATH, 'test_questions.jsonl'))
    # pp = PreProcessor(tokenizer='thulac')

    # 加载处理后的测试数据集
    extract_info = pd.read_csv(os.path.join(ROOT_PATH, 'results/question_info.csv'),
                               dtype={'公司': str, '包关键词': str, '年份': str, '鑫鑫关键词': str})
    extract_info = [t[1] for t in extract_info.iterrows()]

    # 保存中间结果用于分析
    analysis = []

    # 遍历回答问题
    for data, info in zip(dt, extract_info):
        question = data.get('question')
        if not re.search('国联股份|常宝股份|航新科技|海鸥股份|雅化集团|清研环境|东方金钰|盛航海运|均胜电子|众源新材|星光农机', question):
            continue

        # 公司名称、年份和关键词识别
        # year, code, _ = pp.process_question(question)
        year, code, bao_key_info, xx_key_info = info['年份'], info['公司'], info['包关键词'], info['鑫鑫关键词']

        if pd.notna(bao_key_info):
            key_info = bao_key_info
        else:
            key_info = xx_key_info

        # NOTE: 因为向量匹配可能存在问题，因此去掉后缀。
        if isinstance(key_info, str):
            key_info = key_info.replace('增长率', '')

        year = year.split('|') if pd.notna(year) else None
        key_info = key_info.split('|') if pd.notna(key_info) else None

        refine_key_info = []
        if year and code:
            # 基于规则+语义相似度检索年报中基本信息
            if key_info:
                key_info = list(set(key_info))
                # 基于向量匹配用户问题抽取关键信息与预设指标
                key_info_vec = s_model.encode(key_info)
                for key_vec in key_info_vec:
                    similarities = cosine_similarity(np.reshape(key_vec, (1, -1)),
                                                     index_vecs)
                    top_1_similarity = np.max(similarities)
                    if top_1_similarity > 0.8:
                        top_1_index = np.argmax(similarities)
                        refine_key_info.append(index_list[top_1_index])
                refine_key_info = list(set(refine_key_info))
                # 如果抽取指标中包含计算指标，则抽取指标以计算指标为准，用于过滤计算指标外的指标信息
                calc_key = [k for k in refine_key_info if k in CALC_INDEX.keys()]
                if calc_key:
                    refine_key_info = calc_key

            info = {}
            # 基于不同年份抽取年报信息
            for y in year:
                try:
                    _info = get_company_info(f'{code}_{y}', refine_key_info, s_model, y)
                    info.update(_info)
                except FileNotFoundError:
                    y = str(int(y) + 1)
                    if y not in year:
                        try:
                            _info = get_company_info(f'{code}_{y}', refine_key_info, s_model, y)
                            info.update(_info)
                        except FileNotFoundError:
                            print('无文件%s.txt。' % f'{code}_{y}')
                            continue
                    else:
                        continue

            answer = model.get_answer_base_info(question, info, refine_key_info)
        else:
            info = {}
            answer = model.get_answer(question)

        if answer:
            data.update({'answer': answer.replace(',', '')})
            info_str = json.dumps(info, ensure_ascii=False, indent=2)
            print('年报文件：%s' % ([f'{code}_{y}.txt' for y in year] if year and code else None))
            print('回答结果%s' % data)
            print('公司信息：%s' % info_str)
            print('抽取指标：%s\n--------------------分割线-----------------' % refine_key_info)

            analysis.append({'年报文件': [f'{code}_{y}.txt' for y in year] if year and code else None,
                             '问题': question,
                             '公司信息': info_str,
                             '答案': answer})

    # 保存文件
    save_answers(dt, f'价值在线小分队_result_{ts}.json')

    # 保存中间结果
    save_analysis(analysis, f'价值在线小分队_中间结果_{ts}.json')
