import uuid

import cltl.chatbackend.reverse as backend
from cltl.chatui.api import Utterance


if __name__ == '__main__':
    agent = "Agent"
    other = input(f"Agent> Who are you?\n> ").strip()

    processor = backend.ReverseChatProcessor(agent)
    chat_id = str(uuid.uuid4())

    response = Utterance(chat_id, "agent", "Hi!")
    while True:
        text = input(f"{response.speaker}> {response.text}\n{other}> ")
        response = processor.process(Utterance(chat_id, other, text))