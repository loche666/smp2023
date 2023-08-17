import re
import json

from flask import Flask, request

import pandas as pd

from src.utils import read_json_line, get_stopwords

"""n/名词 np/人名 ns/地名 ni/机构名 nz/其它专名
m/数词 q/量词 mq/数量词 t/时间词 f/方位词 s/处所词
v/动词 vm/能愿动词 vd/趋向动词 a/形容词 d/副词
h/前接成分 k/后接成分 i/习语 j/简称
r/代词 c/连词 p/介词 u/助词 y/语气助词
e/叹词 o/拟声词 g/语素 w/标点 x/其它 """
app = Flask(__name__)


class PreProcessor(object):
    def __init__(self, tokenizer='thulac'):
        stopwords = get_stopwords('zh')
        stopwords.extend(['?', '2', '两', '位', '年报', '报告', '公司', '内', '后', '年报数据', '数据', '显示', '介绍', '提供',
                          '报告期', '请问', '介绍报告期', '保留', '是否', '简要', '进行', '分析', '一下', '根据', '能否', '元',
                          '请简', '单位'])
        self.stopwords = stopwords
        all_info = pd.read_csv('../data/alltxt_info.csv', dtype=str)
        self.abbreviation = all_info['abbreviation'].tolist()
        self.full_name = all_info['full_name'].tolist()
        self.company_codes = all_info['company_code'].tolist()
        self.company_names = list(set(self.abbreviation))
        self.company_names.extend(list(set(self.full_name)))
        self.finance_terms = ['三费比重', '期末现金']
        if tokenizer == 'ltp':
            from ltp import LTP
            self.tokenizer = LTP('/home/model_weight/ltp')
            self.tokenizer.to("cuda")
            self.tokenizer.add_words(self.company_names, freq=2)
            self.tokenizer.add_words(self.finance_terms, freq=2)
            self.time_pos = 'nt'  # 'ntppl'
            self.punc_pos = 'wp'  # 'wp'
        else:
            from thulac import thulac
            self.tokenizer = thulac(seg_only=False,
                                    model_path='/home/model_weight/THULACmodels/',
                                    user_dict='../data/user_dict.txt')
            self.time_pos = 't'  # 'ntppl'
            self.punc_pos = 'w'  # 'wp'

    def tokenize(self, question):
        if 'ltp' in str(type(self.tokenizer)):
            cws, pos = self.tokenizer.pipeline([question], tasks=["cws", "pos"]).to_tuple()
            return cws[0], pos[0]
        else:
            seg_res = self.tokenizer.fast_cut(question)
            return [s[0] for s in seg_res], [s[1] for s in seg_res]

    def concat_vn(self, cws, pos):
        N = len(cws)
        print(cws)
        for i in range(N):
            if cws[i].strip() in self.company_names:
                pos[i] = 'ncn'
            if pos[i] == self.time_pos:
                continue
            elif '小数' in cws[i] or cws[i] in self.stopwords or pos[i] == self.punc_pos:
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
        print(cws, pos)
        return cws, pos

    def process_question(self, question: str):
        """
        :param question:
        :return:
        """
        question = question.replace('(', '').replace(')', '').replace('（', '').replace('）', '').replace('A', 'A,')
        cws, pos = self.tokenize(question)
        cws, pos = self.concat_vn(cws, pos)
        report_date = [w for w, p in zip(cws, pos) if p == self.time_pos]
        report_date = [re.sub(u"([^\u0030-\u0039])", "", d) for d in report_date] if report_date else None
        company_name = [w for w, p in zip(cws, pos) if p == 'ncn']
        company_code = [
            self.company_codes[self.abbreviation.index(n)] if n in self.abbreviation else self.company_codes[
                self.full_name.index(n)] for n in company_name if n in self.company_names]
        company_code = company_code[0] if company_code else None
        kws = [w for w, p in zip(cws, pos) if p != self.time_pos and p not in
               ['v', 'a'] and w not in self.company_names] if company_code and report_date else []
        return report_date, company_code, kws


@app.route('/process_question', methods=['POST'])
def test():
    if request.method == 'POST':
        data = json.loads(request.data)
        text = data['input']
        result = pp.process_question(text)
        result = {'result': result}
        result.update({'code': 0, 'msg': 'ok'})
    return json.dumps(result)


if __name__ == '__main__':
    pp = PreProcessor(tokenizer='thulac')
    print(pp.process_question('能否根据2020年金宇生物技术股份有限公司的年报，给我简要介绍一下报告期内公司的社会责任工作情况？'))
    app.config['MAX_CONTENT_LENGTH'] = pow(1024, 3)
    app.run(host='0.0.0.0', port='8001')

# if __name__ == '__main__':
#     questions = read_json_line('../data/test_questions.jsonl')
#     bad_case = ['清研环境2021年每股经营现金流量是多少元?',
#                 '2019年征和工业的技术人员数是多少？',
#                 '中兰环保科技股份有限公司2021年无形资产是多少元?',
#                 ]
#
#     pp = PreProcessor(tokenizer='thulac')
#     # ppl = PreProcessor(tokenizer='ltp')
#     for line in bad_case:
#         result = pp.process_question(line)
#         print(result)
#     result = pp.process_question('请提供深天马A2021年的法定代表人是否相同。')
#     print(result)
