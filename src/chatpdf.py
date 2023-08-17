# -*- coding: utf-8 -*-
from typing import Union, List
import os
import torch
from loguru import logger
from peft import PeftModel
from similarities import Similarity
from transformers import AutoModelForCausalLM, AutoTokenizer, AutoModel

PROMPT_TEMPLATE = """基于以下已知信息，简洁和专业地来回答用户的问题。
如果无法从中得到答案，请说 "根据已知信息无法回答该问题" 或 "没有提供足够的相关信息"，不允许在答案中添加编造成分，答案请使用中文。

已知信息:
{context_str}

问题:
{query_str}
"""


class SMP:
    def __init__(
            self,
            sim_model_name_or_path: str = "/root/brx/m3e-base",
            gen_model_type: str = "chatglm",
            gen_model_name_or_path: str = "/root/.cache/modelscope/hub/ZhipuAI/chatglm2-6b",
            lora_model_name_or_path: str = None,
            device: str = 'cuda',
            int8: bool = False,
            int4: bool = False,
    ):
        default_device = 'cpu'
        if torch.cuda.is_available():
            default_device = 'cuda'
        elif torch.backends.mps.is_available():
            default_device = 'mps'
        self.device = device or default_device
        self.sim_model = Similarity(model_name_or_path=sim_model_name_or_path, device=self.device)
        self.gen_model, self.tokenizer = self._init_gen_model(
            gen_model_type,
            gen_model_name_or_path,
            peft_name=lora_model_name_or_path,
            int8=int8,
            int4=int4,
        )
        self.history = None
        self.txt_files = None

    def _init_gen_model(
            self,
            gen_model_type: str,
            gen_model_name_or_path: str,
            peft_name: str = None,
            int8: bool = False,
            int4: bool = False,
    ):
        """Init generate model."""
        if int8 or int4:
            device_map = None
        else:
            device_map = "auto"
        if gen_model_type == "chatglm":
            model = AutoModel.from_pretrained(
                gen_model_name_or_path,
                torch_dtype=torch.float16,
                device_map=device_map,
                trust_remote_code=True
            )
        else:
            model = AutoModelForCausalLM.from_pretrained(
                gen_model_name_or_path,
                torch_dtype=torch.float16,
                device_map=device_map,
                trust_remote_code=True
            )
        if int4:
            model = model.quantize(4).cuda()
        elif int8:
            model = model.quantize(8).cuda()
        # model.generation_config = GenerationConfig.from_pretrained(gen_model_name_or_path)
        tokenizer = AutoTokenizer.from_pretrained(
            gen_model_name_or_path,
            use_fast=False,
            trust_remote_code=True
        )
        if peft_name:
            model = PeftModel.from_pretrained(
                model,
                peft_name,
                torch_dtype=torch.float16,
            )
            logger.info(f"Loaded peft model from {peft_name}")
        return model, tokenizer

    def chat_only(self, question, history=[]):
        model = self.gen_model.eval()
        response, history = model.chat(self.tokenizer, question, history=history, temperature=0.1)
        return response

    @torch.inference_mode()
    def generate_answer(
            self,
            prompt,
            max_new_tokens=512,
            temperature=0.7,
            top_k=40,
            top_p=0.9,
            do_sample=True,
            repetition_penalty=1.0,
            context_len=2048
    ):
        generation_config = dict(
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            do_sample=do_sample,
            repetition_penalty=repetition_penalty,
        )
        input_ids = self.tokenizer(prompt).input_ids
        max_src_len = context_len - max_new_tokens - 8
        input_ids = input_ids[-max_src_len:]
        generation_output = self.gen_model.generate(
            input_ids=torch.as_tensor([input_ids]).to(self.device),
            **generation_config,
        )
        output_ids = generation_output[0]
        output = self.tokenizer.decode(output_ids, skip_special_tokens=False)
        stop_str = self.tokenizer.eos_token
        l_prompt = len(self.tokenizer.decode(input_ids, skip_special_tokens=False))
        pos = output.rfind(stop_str, l_prompt)
        if pos != -1:
            output = output[l_prompt:pos]
        else:
            output = output[l_prompt:]
        return output.strip()

    def load_txt_files(self, txt_files: Union[str, List[str]]):
        """Load document files."""
        if isinstance(txt_files, str):
            txt_files = [txt_files]
        for txt_file in txt_files:
            corpus = self.extract_text_from_txt(txt_file)
            self.sim_model.add_corpus(corpus)
        self.txt_files = txt_files

    @staticmethod
    def extract_text_from_txt(file_path: str):
        """Extract text content from a TXT file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            contents = [text.strip() for text in f.readlines() if text.strip()]
        return contents


    @staticmethod
    def _add_source_numbers(lst):
        """Add source numbers to a list of strings."""
        return [f'[{idx + 1}]\t "{item}"' for idx, item in enumerate(lst)]

    def query(
            self,
            query: str,
            topn: int = 5,
            max_length: int = 512,
            max_input_size: int = 1024,
    ):
        """Query from corpus."""

        sim_contents = self.sim_model.most_similar(query, topn=topn)

        reference_results = []
        for query_id, id_score_dict in sim_contents.items():
            for corpus_id, s in id_score_dict.items():
                reference_results.append(self.sim_model.corpus[corpus_id])
        if not reference_results:
            return '没有提供足够的相关信息', reference_results
        reference_results = self._add_source_numbers(reference_results)
        context_str = '\n'.join(reference_results)[:(max_input_size - len(PROMPT_TEMPLATE))]

        prompt = PROMPT_TEMPLATE.format(context_str=context_str, query_str=query)
        response = self.generate_answer(prompt, max_new_tokens=max_length)
        return response, reference_results

    def save_index(self, index_path):
        """Save model."""
        index_path = os.path.join("./index", index_path.split('.')[0] + '_index.json')
        self.sim_model.save_index(index_path)

    def load_index(self, index_path):
        """Load model."""
        index_path = os.path.join("./index", index_path.split('.')[0] + '_index.json')
        self.sim_model.load_index(index_path)


def save_declare_index(m, declare_path):
    """
    将年报数据解析后的结果存储为向量索引
    :param m:
    :param declare_path: 年报txt文件存储的路径
    :return:
    """
    for file in os.listdir(declare_path):
        print(file)
        m.load_txt_files(os.path.join(declare_path, file))
        m.save_index(file)

if __name__ == "__main__":
    m = SMP()

    save_declare_index(m, "./declare_files")
    m.load_index("000056_2020.txt")
    #
    response = m.query('公司的董事长是谁？')
    print(response)
    # print(response[0])
    # response = m.query('本文作者是谁？')
    # print(response)
