import os.path
import re

import pandas as pd
from ltp import LTP
from thulac import thulac

from src.xfd_solution.constants.constants import DATA_PATH
from src.xfd_solution.utils.common_utils import read_json_line, get_stopwords

TIME_POS = 't'  # 'ntppl'
PUNC_POS = 'w'  # 'wp'
"""n/名词 np/人名 ns/地名 ni/机构名 nz/其它专名
m/数词 q/量词 mq/数量词 t/时间词 f/方位词 s/处所词
v/动词 vm/能愿动词 vd/趋向动词 a/形容词 d/副词
h/前接成分 k/后接成分 i/习语 j/简称
r/代词 c/连词 p/介词 u/助词 y/语气助词
e/叹词 o/拟声词 g/语素 w/标点 x/其它 """


class PreProcessor(object):
    def __init__(self, tokenizer='ltp'):
        stopwords = get_stopwords('zh')
        stopwords.extend(
            ['?', '2', '两', '位', '年报', '报告', '公司', '内', '后', '年报数据', '介绍', '提供', '报告期',
             '介绍报告期', '保留', '简要', '进行', '分析', '一下', '根据', '能否', '元', '请简', '单位'])
        self.stopwords = stopwords
        all_info = pd.read_csv(os.path.join(DATA_PATH, 'alltxt_info.csv'), dtype=str)
        self.abbreviation = all_info['abbreviation'].tolist()
        self.full_name = all_info['full_name'].tolist()
        self.company_codes = all_info['company_code'].tolist()
        self.company_names = list(set(self.abbreviation))
        self.company_names.extend(list(set(self.full_name)))
        self.finance_terms = ['三费比重', '期末现金']
        if tokenizer == 'ltp':
            self.tokenizer = LTP('/home/model_weight/ltp')
            self.tokenizer.to("cuda")
            self.tokenizer.add_words(self.company_names, freq=2)
            self.tokenizer.add_words(self.finance_terms, freq=2)
        else:
            self.tokenizer = thulac(seg_only=False,
                                    model_path='/home/model_weight/THULACmodels/',
                                    user_dict=os.path.join(DATA_PATH, 'user_dict.txt'))

    def tokenize(self, question):
        if 'ltp' in str(type(self.tokenizer)):
            cws, pos = self.tokenizer.pipeline([question], tasks=["cws", "pos"]).to_tuple()
            return cws[0], pos[0]
        else:
            seg_res = self.tokenizer.fast_cut(question)
            return [s[0] for s in seg_res], [s[1] for s in seg_res]

    def concat_vn(self, cws, pos):
        N = len(cws)
        for i in range(N):
            if cws[i].strip() in self.company_names:
                pos[i] = 'ncn'
            if pos[i] == TIME_POS:
                continue
            elif '小数' in cws[i] or cws[i] in self.stopwords or pos[i] == PUNC_POS:
                # 只保留名词，去掉停用词(弃用) | 停用词扩充，不限定词性(√)
                cws[i], pos[i] = '', ''
            # 拼动名词
            elif pos[i] in ['v'] and i + 1 < N and cws[i + 1] not in self.company_names and 'n' in pos[i + 1]:
                cws[i], cws[i + 1] = '', cws[i] + cws[i + 1]
                pos[i], pos[i + 1] = '', 'n'
            # 拼名词
            elif (pos[i] == 'n' or pos[i] == 'nz') and i + 1 < N and cws[i + 1] not in self.company_names and pos[
                i + 1] == 'n':
                cws[i], cws[i + 1] = '', cws[i] + cws[i + 1]
                pos[i], pos[i + 1] = '', 'n'
        pos = [p for p in pos if p]
        cws = [w for w in cws if w]
        return cws, pos

    def process_question(self, question: str):
        """
        :param question:
        :return:
        """
        question = question.replace('(', '').replace(')', '').replace('（', '').replace('）', '').replace('A', 'A,')
        cws, pos = self.tokenize(question)
        cws, pos = self.concat_vn(cws, pos)
        report_date = [w for w, p in zip(cws, pos) if p == TIME_POS]
        report_date = [re.sub(u"([^\u0030-\u0039])", "", d) for d in report_date] if report_date else None
        company_name = [w for w, p in zip(cws, pos) if 'n' in p]
        company_code = [
            self.company_codes[self.abbreviation.index(n)] if n in self.abbreviation else self.company_codes[
                self.full_name.index(n)] for n in company_name if n in self.company_names]
        company_code = company_code[0] if company_code else None
        kws = [w for w, p in zip(cws, pos) if
               p != TIME_POS and w not in self.company_names] if company_code and report_date else []
        return report_date, company_code, kws


if __name__ == '__main__':
    questions = read_json_line('../data/test_questions.jsonl')
    bad_case = ['清研环境2021年每股经营现金流量是多少元?',
                '2019年征和的工业技术人员数是多少？',
                '中兰环保科技股份有限公司2021年无形资产是多少元?',
                ]

    pp = PreProcessor(tokenizer='thulac')
    # ppl = PreProcessor(tokenizer='ltp')
    for line in bad_case:
        result = pp.process_question(line)
        print(result)
    result = pp.process_question('请提供深天马A2021年的法定代表人是否相同。')
    print(result)
