from openai_config import get_openai_client
import json

client = get_openai_client()

class Agent:
    def __init__(self, instructions, tools, tool_choice="auto"):
        self.instructions = instructions
        self.tools = tools
        self.tool_choice = tool_choice
        
    async def chat(self, message):
        messages = [{"role": "system","content": self.instructions},{"role": "user","content": message}]
        try:
            print(message)
            completion = await client.chat.completions.create(model="gpt-4-1106-preview", messages=messages, tools=self.tools, tool_choice=self.tool_choice, temperature=0.0)
            print(f'\n\n{completion}')
        except Exception as e:
            print(f"Exception occurred: {e}")
            return
        return self.get_tool_output(completion)

    def get_tool_output(self, completion):
        tool_output = {}
        for tool_call in completion.choices[0].message.tool_calls:
            tool_output['function_name'] = tool_call.function.name
            tool_output['arguments'] = json.loads(tool_call.function.arguments)
        print(tool_output)
        return tool_output