# -*- coding: utf-8 -*-
# @Desc   : Description of File
# @Licence: (C) Copyright for ValueOnline
# @Author : chen.long
# @Date   : 2023/7/31
import os
from typing import Dict, List

from modelscope import Model
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks

from src.xfd_solution.constants.constants import ANSWER_PROMPT, EXTRACT_DECIMAL_PROMPT, EXTRACT_TEXT_PROMPT, \
    ANSWER_BASE_INFO_PROMPT, CALC_INDEX, CALCULATE_TYPE_PROMPT


# 加载抽取公司基本信息文件
# company_info = load_jsonl_data(os.path.join(DATA_PATH, 'extract_data.jsonl'))
# info_dict = dict(zip([e.get('key') for e in company_info],
#                      [e.get('val') for e in company_info]))


class ChatGlm2:
    def __init__(self, model_path: str, device='0'):
        """初始化chatglm模型
        :param model_path:
        :param device:
        """
        os.environ['CUDA_VISIBLE_DEVICES'] = device
        model = Model.from_pretrained(model_name_or_path=model_path, revision='v1.0.6')
        self.pipe = pipeline(task=Tasks.chat, model=model)

    def get_answer(self, question):
        """回答问题
        :param question:
        :return:
        """
        prompt = ANSWER_PROMPT.format(question)
        inputs = {'text': prompt, 'history': [], 'temperature': 0.1}
        result = self.pipe(inputs)
        return result.get('response')

    # def extract_key_info(self, keys, base_info):
    #     """
    #     :param keys:
    #     :param base_info:
    #     :return:
    #     """
    #     prompt_template = "基于以下三引号内的信息，总结一段关于“{}”的文本，要求简洁、准确，不得有编造和杜撰的成分。\n\n{}"
    #     prompt = prompt_template.format('、'.join(keys), base_info)
    #     inputs = {'text': prompt, 'history': [], 'temperature': 0.1}
    #     result = self.pipe(inputs)
    #     return result.get('response')

    def get_answer_base_info(self, question: str, info_dict: Dict, key_info: List):
        """基于年报指标回答问题
        :param key_info:
        :param info_dict:
        :param question:
        :return:
        """
        if info_dict:
            base_info = ''
            for key, val in info_dict.items():
                base_info += '{}信息如下：\n{}\n'.format(key, ''.join(val))

            # 基于抽取的信息，基于chatglm总结成文本
            # base_info = self.extract_key_info(list(info_dict.keys()), base_info)

            # if len(key_info) == 1 and key_info[0] in CALC_INDEX.keys():
            #     # 如果是计算类问题
            #     prompt = CALCULATE_TYPE_PROMPT.format(CALC_INDEX.get(key_info[0]), question, base_info)
            # else:
            #     # 如果是指标类问题
            prompt = ANSWER_BASE_INFO_PROMPT.format(question, base_info.strip())
        else:
            prompt = ANSWER_PROMPT.format(question)
        inputs = {'text': prompt, 'history': [], 'temperature': 0.1}
        result = self.pipe(inputs)
        return result.get('response')

    def extract_index(self, index: str, info: str, index_type: str, year=''):
        """抽取公司基本指标
        :param year: 用于指定抽取特定年份的指标
        :param index_type:
        :param index:
        :param info:
        :return:
        """

        if index_type == 'decimal':
            prompt = EXTRACT_DECIMAL_PROMPT.format(year, index, info)[:2048]
        elif index_type == 'text':
            prompt = EXTRACT_TEXT_PROMPT.format(index, info)[:2048]
        else:
            raise Exception
        inputs = {'text': prompt, 'history': [], 'temperature': 0.1}
        result = self.pipe(inputs)
        return result
