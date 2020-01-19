import asyncio
import websockets
import random
import json
import time

class MessageType:
    ANSWER = "answer"
    QUESTION = "question"
    MESSAGE = "message"
    USERS = "users"
    MY_NAME = "my_name"

class User:
    def __init__(self, ws, name):
        self.ws = ws
        self.name = name
    
    def __eq__(self, other):
        return self.name == other.name
    
    def __hash__(self):
        return hash(self.name)

class UserCollection:
    def __init__(self, name_generator):
        self.name_generator = name_generator
        self.ws2user = {}
    
    def _get_names(self):
        return list(map(lambda user: user.name, self.ws2user.values()))

    async def add(self, websocket):
        new_name = name_generator.make_new()
        new_user = User(websocket, new_name)
        await websocket.send(json.dumps({"type": MessageType.MY_NAME, "content": new_name}))
        self.ws2user[websocket] = new_user
        names = self._get_names()
        await self.broadcast(type=MessageType.USERS, content=names)

    async def remove(self, websocket):
        user = self.ws2user[websocket]
        self.ws2user.pop(websocket)
        self.name_generator.remove(user.name)
        names = self._get_names()
        await self.broadcast(type=MessageType.USERS, content=names)

    async def broadcast(self, type, content):
        for ws in self.ws2user:
            await ws.send(json.dumps({
                "type": type,
                "content": content
            }))

    def __len__(self):
        return len(self.ws2user)

class NameGenerator:
    def __init__(self, adjectives, nouns):
        self.adjectives = adjectives
        self.nouns = nouns
        self.used_names = set()
    
    def make_new(self):
        while True:
            adjective = random.choice(self.adjectives)
            noun = random.choice(self.nouns)
            name = f"{adjective} {noun}"
            if name not in self.used_names:
                break
    
        self.used_names.add(name)
        return name
    
    def remove(self, name):
        self.used_names.remove(name)


class QuestionEngine:
    def __init__(self, source):
        self.source = source
        self._load()
        self.last_time = time.time()
        self.active_question = None
        self.active_answer = None

    def _load(self):
        self.questions = []
        self.answers = []
        with open(self.source, encoding="utf-8") as f:
            for line in f.readlines():
                question, answer = line.strip().split("\t")
                self.questions.append(question)
                self.answers.append(answer)
        assert len(self.questions) == len(self.answers)
    
    def start_new(self):
        index = random.randint(0, len(self.questions)-1)
        self.active_question = self.questions[index]
        self.active_answer = self.answers[index]
        self.last_time = time.time()
    
    async def pause_and_start_new(self, users):
        current_question_time = self.last_time
        self.start_new()
        for _ in range(1000):
            await asyncio.sleep(0.1)
        
        users.broadcast(type=MessageType.QUESTION, content=self.active_question)
        for _ in range(1000):
            await asyncio.sleep(0.1)
            if self.last_time != current_question_time:
                break

    def attempt(self, guess):
        if self.active_answer is None:
            return False
        
        if guess == self.active_answer.lower():
            self.active_question = None
            self.active_answer = None
            self.last_time = time.time()
            return True

name_generator = NameGenerator(
    adjectives = ["black", "brown", "red", "blue", "big", "little", "hard", "soft", "white", "orange", "strong", "weak", "iron", "copper", "gold", "silver"],
    nouns = ["cat", "dog", "mouse", "spider", "lion", "hero", "peasant", "knight", "warrior", "soldier", "gardener", "policeman", "fireman", "wizard", "tree", "mine", "bullet"]
)
users = UserCollection(name_generator)
question_engine = QuestionEngine("qa.txt")

async def main(websocket, path):
    await users.add(websocket)
    try:
        async for msg in websocket:
            await users.broadcast(type=MessageType.MESSAGE, content=msg)
            msg = msg.strip().lower()
            guessed = question_engine.attempt(msg)
            if guessed:
                await users.broadcast(type=MessageType.ANSWER, content=question_engine.active_answer)
                asyncio.get_event_loop().create_task(question_engine.pause_and_start_new(users))

    finally:
        await users.remove(websocket)

start_server = websockets.serve(main, "localhost", 8765)
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    # loop.create_task(question_engine.start_new())
    loop.run_until_complete(start_server) # TODO try create_task even for this
    loop.run_forever()

