from dashscope import Generation
from config import DASHSCOPE_API_KEY, LLM_MODEL, SYSTEM_PROMPT_COT, SYSTEM_PROMPT_REACT, MAX_HISTORY_TURNS
import dashscope


class LLMService:
    """LLM问答服务：支持CoT和ReAct两种Agent模式"""

    def __init__(self):
        dashscope.api_key = DASHSCOPE_API_KEY
        # 多轮对话历史
        self.conversation_history = []

    def generate(self, query: str, context: str, mode: str = "cot") -> dict:
        """生成回答，返回答案+思考过程"""
        if mode == "cot":
            return self._generate_cot(query, context)
        elif mode == "react":
            return self._generate_react(query, context)
        else:
            raise ValueError(f"不支持的模式：{mode}")

    def _generate_cot(self, query: str, context: str) -> dict:
        """CoT模式：让模型先分析再回答"""
        # 1. 构建system prompt，注入参考资料
        system_prompt = SYSTEM_PROMPT_COT.format(context=context)

        # 2. 构建消息列表
        messages = [{"role": "system", "content": system_prompt}]

        # 3. 加入最近的历史对话（最多MAX_HISTORY_TURNS轮）
        recent_history = self.conversation_history[-(MAX_HISTORY_TURNS * 2):]
        messages.extend(recent_history)

        # 4. 加入当前问题
        messages.append({"role": "user", "content": query})

        # 5. 调用LLM API
        response = Generation.call(
            model=LLM_MODEL,
            messages=messages,
            result_format="message",
        )

        if response.status_code != 200:
            raise Exception(f"LLM API调用失败：{response.message}")

        answer = response.output.choices[0].message.content

        # 6. 记录到对话历史
        self.conversation_history.append({"role": "user", "content": query})
        self.conversation_history.append({"role": "assistant", "content": answer})

        return {
            "answer": answer,
            "thinking": "CoT模式：模型已根据参考资料进行分析",
        }

    def _generate_react(self, query: str, context: str) -> dict:
        """ReAct模式：模型循环推理，最多3步"""
        max_steps = 3
        system_prompt = SYSTEM_PROMPT_REACT.format(context=context)
        trace = []

        for step in range(max_steps):
            # 构建消息
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(self.conversation_history[-(MAX_HISTORY_TURNS * 2):])
            messages.append({"role": "user", "content": query})

            # 如果有之前的trace，也放进去让模型参考
            if trace:
                messages.append({
                    "role": "assistant",
                    "content": "\n".join(trace),
                })

            # 调用LLM
            response = Generation.call(
                model=LLM_MODEL,
                messages=messages,
                result_format="message",
            )

            if response.status_code != 200:
                raise Exception(f"LLM API调用失败：{response.message}")

            step_output = response.output.choices[0].message.content
            trace.append(f"Step {step + 1}: {step_output}")

            # 检查是否包含最终答案
            if "Action: answer" in step_output or "最终答案" in step_output:
                break

        # 提取最终答案（取最后一步的输出）
        final_answer = step_output

        # 记录到对话历史
        self.conversation_history.append({"role": "user", "content": query})
        self.conversation_history.append({"role": "assistant", "content": final_answer})

        return {
            "answer": final_answer,
            "thinking": "\n".join(trace),
        }

    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []

    def get_history(self) -> list:
        """获取对话历史"""
        return self.conversation_history.copy()