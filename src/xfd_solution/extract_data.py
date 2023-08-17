# # -*- coding: utf-8 -*-
# # @Desc   : Description of File
# # @Licence: (C) Copyright for ValueOnline
# # @Author : chen.long
# # @Date   : 2023/8/1
# import json
# import os
# import re
# import sys
# import traceback
# from threading import Thread, current_thread
# from typing import List
#
# import math
#
# from src.xfd_solution.utils.embedding_utils import SimilarityModel
#
# sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
#
# from src.xfd_solution.constants.constants import DATA_PATH, INDEX_PATTERNS, GLM_PATH, M3E_PATH, THREAD_NUM
# from src.xfd_solution.utils.chatglm_utils import ChatGlm2
# from src.xfd_solution.utils.common_utils import refine_index
#
# model = ChatGlm2(GLM_PATH, device='1')
#
# s_model = SimilarityModel(M3E_PATH)
#
#
# def extract_index(fnames: List):
#     # 抽取结果文件
#     with open(os.path.join(DATA_PATH, f'extract_data_0803_{current_thread().name}.jsonl'), 'w',
#               encoding='utf-8') as output_file:
#         for fname in fnames:
#             try:
#                 dict_key = fname.split('.')[0]
#                 year = dict_key.split('_')[1]
#                 # 读取年报文本文件
#                 with open(os.path.join(report_data_path, fname), 'r', encoding='utf-8') as report_file:
#                     if not fname.endswith('.txt'):
#                         continue
#                     lines = report_file.readlines()
#
#                 info_dict = {}
#
#                 # 抽取年报相关指标候选
#                 for key, pattern in INDEX_PATTERNS.items():
#                     for line in lines:
#                         res = re.search('|'.join(pattern), line)
#                         if res:
#                             if info_dict.get(key):
#                                 info_dict.get(key).append(line)
#                             else:
#                                 info_dict[key] = [line]
#                     if not info_dict.get(key):
#                         info_dict[key] = []
#
#                 # 基于chatglm抽取相关指标
#                 index_dict = {}
#                 for key, info in info_dict.items():
#                     info = [i for i in info if len(i) < 1000]
#                     if info:
#                         # 基于Embedding精排序
#                         info = s_model.range(f'本公司{key}是×××。', info, 3)
#
#                     # 财务指标
#                     if key in {'注册资本', '总资产', '净资产', '营业收入', '营业利润', '净利润', '营业外支出',
#                                '证券代码', '利息支出', '研发费用', '财务费用'}:
#                         res = model.extract_index(key, '\n\n'.join([e.strip()[:200] for e in info]),
#                                                   'decimal', year=year).get('response')
#                         if re.search('抱歉|无法.*?(回答|确定)', res):
#                             refine_res = ''
#                         else:
#                             refine_res = re.search(f'{key}[为是：](.*?)[。，；]', res)
#                             if refine_res:
#                                 refine_res = refine_res.group(1)
#                                 index_dict[key] = refine_res
#                             else:
#                                 index_dict[key] = ''
#                     else:
#                         # 文字类指标
#                         res = model.extract_index(key, '\n\n'.join([e.strip()[:200] for e in info]), 'text').get(
#                             'response')
#                         refine_res = re.sub('根据提供的(基本)?信息(，)?|\n|公司.*?？', '', res)
#                         if key in {'注册地址', '办公地址', '证券简称', '法定代表人', '英文名称', '电子邮箱',
#                                    '公司网址'}:
#                             # 如果无法回答，指标值为空
#                             if re.search('抱歉|无法.*?(回答|确定)', refine_res):
#                                 refine_res = ''
#                             else:
#                                 refine_pattern = re.search(f'{key}(应该)?(为|是|：|位于)(.*?)[。，；]', refine_res)
#                                 if refine_pattern:
#                                     refine_res = refine_pattern.group(3)
#                         refine_res = refine_index(refine_res)
#                         index_dict[key] = refine_res
#
#                 # 写入输出文件
#                 output_str = json.dumps({'key': dict_key, 'val': index_dict}, ensure_ascii=False)
#                 print(current_thread().name, fname, output_str)
#                 output_file.write(f'{output_str}\n')
#             except Exception:
#                 print('处理文件%s出错。%s' % (fname, traceback.format_exc()))
#                 continue
#
#
# if __name__ == '__main__':
#     report_data_path = os.path.join('/root/liudi/SMP2023/data/report_data')
#     files = os.listdir(report_data_path)
#     batch_size = math.ceil(len(files) / THREAD_NUM)
#
#     # 启动的线程池
#     thread_pool = []
#     for i in range(THREAD_NUM):
#         if i < THREAD_NUM - 1:
#             process_data = files[i * batch_size: (i + 1) * batch_size]
#         else:
#             process_data = files[i * batch_size:]
#         thread_name = f'thread-{i}'
#         thread = Thread(target=extract_index, args=[process_data], name=thread_name)
#         thread.start()
#         print('启动线程%s' % thread_name)
#         thread_pool.append(thread)
#
#     for t in thread_pool:
#         t.join()
