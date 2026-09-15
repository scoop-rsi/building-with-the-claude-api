from dataclasses import dataclass, field
from typing import Self

from anthropic import Anthropic
from anthropic.types import Message, MessageParam
from dotenv import load_dotenv

SONNET = 'claude-sonnet-4-5'
MAX_TOKENS = 1000

TUTOR_PROMPT = '''You are a patient math tutor. Do not directly answer a student's questions.
Guide them to a solution step by step.'''

CODER_PROMPT = '''You are a seasoned Python programmer that writes code as succinctly as possible,
preferring terseness over readability. Return only the code asked for, without any explanation.
If there are tradeoffs, choose the one with the shortest implementation.'''

HOT_HOT_HOT = 1.0

load_dotenv()
client = Anthropic()

@dataclass
class MessageBroker:
    # https://platform.claude.com/docs/en/api/messages/create
    model: str
    max_tokens: int
    system_prompt: str = ''
    # temperature is deprecated
    temperature: float = 0.25 # Good for coding
    is_streaming: bool = False
    messages: list[MessageParam] = field(default_factory=list)

    def add_user_message(self, message_text: str) -> Self:
        message: MessageParam = {'role': 'user', 'content': message_text}
        self.messages.append(message)
        return self

    def add_assistant_message(self, message_text: str) -> Self:
            message: MessageParam = {'role': 'assistant', 'content': message_text}
            self.messages.append(message)
            return self

    def chat(self, user_message: str, code_type: str = '') -> str:
        '''
        Make a request to Anthropic with the given message and history

        Args:
            user_message (str): Latest message in conversation
            code_type (str, optional): When a formatted response is expected, define language. Defaults to ''.

        Returns:
            str: Response from Anthropic
        '''
        params = {
            'model': self.model,
            'max_tokens': self.max_tokens,
        }
        self.add_user_message(user_message)

        if code_type:
            _code_type = code_type if code_type != ' ' else ''
            self.add_assistant_message(f'```{_code_type}')
            params['stop_sequences'] = ['```']

        params['messages'] = self.messages

        if self.system_prompt:
            params['system'] = self.system_prompt

        message: Message = client.messages.create(**params)
        complete_response_message = ' '.join(c.text.strip() for c in message.content)
        self.add_assistant_message(complete_response_message)
        return complete_response_message

    # https://platform.claude.com/docs/en/build-with-claude/streaming
    def stream_chat(self, user_message: str) -> str:
        self.add_user_message(user_message)
        params = {
            'model': self.model,
            'max_tokens': self.max_tokens,
            'messages': self.messages
        }
        if self.system_prompt:
            params['system'] = self.system_prompt

        with client.messages.stream(**params) as stream:
            for text in stream.text_stream:
                print(f'\n[s] {text}', end='')

        return stream.get_final_message()

    def start_new_conversation(self) -> Self:
        self.messages = []
        return self

def main():
    broker = MessageBroker(
        model=SONNET,
        max_tokens=MAX_TOKENS,
        system_prompt=CODER_PROMPT,
        # temperature=HOT_HOT_HOT
    )
    print('How can I help?')
    while True:
        user_input = 'Generate three different sample AWS CLI commands. Each should be very short.^bash' # input('\n??? > ')
        split_input_code = user_input.split('^')
        code_type = split_input_code[1] if len(split_input_code) == 2 else ''
        assistant_response = broker.chat(split_input_code[0], code_type)
        # assistant_response = broker.stream_chat(user_input)
        print(f'AI: {assistant_response}')

if __name__ == '__main__':
    # Write a python function to check for duplicate characters in a string
    # Write a 1 sentence description of a fake database
    # Generate three different sample AWS CLI commands. Each should be very short.
    main()
