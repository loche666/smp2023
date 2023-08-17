"""
问题预处理
"""
import re
import csv
import json

from src.chatpdf import SMP
from src.preprocess import PreProcessor

chat_history = [["""“2021年西宁特殊钢股份有限公司的货币资金增长率为多少?保留2位小数。”
        从上述问题中抽取出提及的年报披露指标。""", "货币资金增长率"], ["""“2021年东方电气利息支出和利息收入分别是多少元?”
        从上述问题中抽取出提及的年报披露指标。""", "电气利息支出和利息收入"], ["""“请问，2021年江苏张家港农村商业银行股份有限公司的利息支出和利息收入分别为多少元?”
        从上述问题中抽取出提及的年报披露指标。""", "利息支出和利息收入"], ["""“根据2019年中科云网的年报，请简要分析报告期内公司费用情况及产生重大变化的原因。”
        从上述问题中抽取出提及的年报披露指标。""", "公司费用情况及产生重大变化"], ["""“根据2020年浙江东方的年报，请简要介绍报告期内公司防治污染设施的建设和运行情况。”
        从上述问题中抽取出提及的年报披露指标。""", "防治污染设施的建设和运行"], ["""“江铃汽车股份有限公司2019年外文名称是什么?”
        从上述问题中抽取出提及的年报披露指标。""", "外文名称"]]


class Company:
    def __init__(
            self,
            company_code,
            security_name,
            company_name
    ):
        self.company_code = company_code
        # 公司简称
        self.security_name = security_name
        # 公司全称
        self.company_name = company_name
        self.company_name_re = security_name + "|" + company_name
        self.company_info = "证券简称：{}\n证券代码:{}\n企业名称:{}".format(security_name, company_code, company_name)


def get_train_data():
    """
    获取训练数据中的公司名称、简称、公司代码
    :return:
    """
    company_list = []
    # 记录已转换的公司代码，用于去重
    code_list = []
    with open("../data/train.csv") as f:
        csv_reader = csv.reader(f)
        for i_c, c in enumerate(csv_reader):
            if i_c > 0:
                pdf_name = c[0]
                pdf_name_list = pdf_name.split("__")
                pdf_name_list = [p for p in pdf_name_list if len(p) > 0]
                if pdf_name_list[2] not in code_list:
                    company_list.append(Company(pdf_name_list[2], pdf_name_list[3], pdf_name_list[1]))
                    code_list.append(pdf_name_list[2])
    return company_list


company_list = get_train_data()
# 所有公司的全称及简称正则
all_company_name_re = "|".join([c.security_name + "的?|" + c.company_name + "的?" for c in company_list]) + "|^.*有限公司的?"
year_sub_re = "在?2019年?度?的?|在?2020年?度?的?|在?2021年?度?的?"

# 占...的?比例
# 与...的?(比值|比率)
# 和
# 、
# 以及
key_word_split = "占|与|和|、|以及"
key_word_sub_re = "与.*的?(比值|比率|比例)"
key_word_sub = "的?(比值|比率|比例)"


def get_year(question):
    """
    提取问题中所有提及的年份
    :return:
    """
    year_re = "2019|2020|2021"
    years = re.findall(year_re, question)
    return years


def get_company(question):
    """
    提取问题中的公司名称
    :return:
    """
    companys = []
    for c in company_list:
        if re.search(c.company_name_re, question):
            companys.append(c.company_code)
    return companys


def get_clear_question(question):
    """
    去除问题中的年份公司名称等无关信息
    :param question:
    :return:
    """


def get_question():
    questions = []
    with open('../data/test_questions.jsonl', 'r') as f:
        for line in f:
            json_line = json.loads(line)
            questions.append(json_line['question'])
    return questions


def main():
    m = SMP()
    pp = PreProcessor(tokenizer='thulac')
    questions = get_question()
    with open("../results/question_info.csv", "w") as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(["问题", "年份", "公司", "鑫鑫关键词", "包关键词"])
        for i_q, question in enumerate(questions):
            print(i_q)
            result = pp.process_question(question)
            years = get_year(question)
            if len(years) > 0:
                key_word = m.chat_only("""\“{}\”
                                从上述问题中抽取出提及的年报披露指标。""".format(question), chat_history)
                # 替换年份和公司名称
                key_word = re.sub(year_sub_re, "", key_word)
                key_word = re.sub(all_company_name_re, "", key_word)
                key_word_list = re.split(key_word_split, key_word)
                # 有与...的比值时，替换字符串
                if re.search(key_word_sub_re, key_word):
                    key_word_list = [re.sub(key_word_sub, "", k) for k in key_word_list]
                key_word_list = list(set([k for k in key_word_list + [key_word] if len(k.strip()) > 0]))
                key_word_temp = "|".join(key_word_list)
                csv_writer.writerow(
                    [question, "|".join(years), result[1], "|".join(result[2]), key_word_temp])
            else:
                csv_writer.writerow([question, "|".join(years), result[1], "|".join(result[2]), ""])


if __name__ == "__main__":
    main()

    # for question in questions:
    #     years = get_year(question)
    #     companys = get_company(question)
    #     if len(companys) > 1:
    #         print(question)
    #         print(companys)
