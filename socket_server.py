import asyncio
import websockets
import random
import json
import time

INTERMEZZO_SECONDS = 5
ANSWERING_SECONDS = 10

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
        self.score = 0
    
    def __eq__(self, other):
        return self.name == other.name
    
    def __hash__(self):
        return hash(self.name)
    
    def inc(self):
        self.score += 1
    
    def to_dict(self):
        return {"name": self.name, "score": self.score}

class UserCollection:
    def __init__(self, name_generator):
        self.name_generator = name_generator
        self.ws2user = {}
    
    def get_user_list(self):
        return list(map(lambda user: user.to_dict(), self.ws2user.values()))

    async def add(self, websocket):
        new_name = name_generator.make_new()
        new_user = User(websocket, new_name)
        await websocket.send(json.dumps({"type": MessageType.MY_NAME, "content": new_name}))
        self.ws2user[websocket] = new_user
        user_list = self.get_user_list()
        await self.broadcast(type=MessageType.USERS, content=user_list)
        return new_user

    async def remove(self, websocket):
        user = self.ws2user[websocket]
        self.ws2user.pop(websocket)
        self.name_generator.remove(user.name)
        user_list = self.get_user_list()
        await self.broadcast(type=MessageType.USERS, content=user_list)

    async def broadcast(self, type, **kwargs):
        for ws in self.ws2user:
            await ws.send(json.dumps({
                "type": type,
                **kwargs
            }))

    async def send(self, to, type, **kwargs):
        await to.send(json.dumps({
            "type": type,
            **kwargs
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
        self.last_question = None

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
        while True:
            index = random.randint(0, len(self.questions)-1)
            if self.last_question != self.questions[index]:
                break
        
        self.last_question = self.active_question = self.questions[index]
        self.active_answer = self.answers[index]
        self.last_time = time.time()
    
    async def pause_and_start_new(self, users):
        self.restart_active()
        print("pause and start new")
        for _ in range(INTERMEZZO_SECONDS*10):
            await asyncio.sleep(0.1)
        
        self.start_new()
        current_question_time = self.last_time
        
        await users.broadcast(type=MessageType.QUESTION, content=self.active_question)
        print("broadcasted question")
        for _ in range(ANSWERING_SECONDS*10):
            await asyncio.sleep(0.1)
            if self.last_time != current_question_time:
                break
        
        msg = ("not " if self.last_time == current_question_time else "") + "answered"
        print("sleeping done", msg)
        if self.last_time == current_question_time:
            await users.broadcast(type=MessageType.ANSWER, content=self.active_answer, author=None)
            print("restarting")
            self.restart_active()
            asyncio.get_event_loop().create_task(self.pause_and_start_new(users))

    def restart_active(self):
        self.active_question = None
        self.active_answer = None
        self.last_time = time.time()

    def attempt(self, guess):
        passed_time = time.time() - self.last_time
        if self.active_answer is None:
            return False, passed_time
        
        if guess == self.active_answer.lower():
            passed_time = time.time() - self.last_time
            self.restart_active()
            return True, passed_time
        
        return False, passed_time

name_generator = NameGenerator(
    adjectives = ["crni", "smeđi", "crveni", "plavi", "veliki", "mali", "čvrsti", "meki", "jaki", "slabi"],
    nouns = ["mačak", "pas", "miš", "pauk", "lav", "junak", "seljak", "vitez", "ratnik", "vojnik", "vrtlar", "čarobnjak", "političar", "policajac", "vatrogasac"]
    # adjectives = ["black", "brown", "red", "blue", "big", "little", "hard", "soft", "white", "orange", "strong", "weak", "iron", "copper", "gold", "silver"],
    # nouns = ["cat", "dog", "mouse", "spider", "lion", "hero", "peasant", "knight", "warrior", "soldier", "gardener", "policeman", "fireman", "wizard", "tree", "mine", "bullet"]
)
users = UserCollection(name_generator)
question_engine = QuestionEngine("qa.txt")

async def main(websocket, path):
    user = await users.add(websocket)
    content = question_engine.active_question if question_engine.active_question else "Smišljam pitanje."
    await users.send(to=websocket, type=MessageType.QUESTION, content=content)
    try:
        async for msg in websocket:
            print("new msg:", msg)
            msg = msg.strip().lower()
            guessed, passed_time = question_engine.attempt(msg)
            if guessed:
                print(msg, "is correct!")
                await users.broadcast(type=MessageType.ANSWER, content=msg, author=user.name, time=passed_time)
                user.inc()
                await users.broadcast(type=MessageType.USERS, content=users.get_user_list())
                print("broadcasted that q answered")
                asyncio.get_event_loop().create_task(question_engine.pause_and_start_new(users))
            else:
                await users.broadcast(type=MessageType.MESSAGE, content=msg, author=user.name)
                print(msg, "is not correct")

    finally:
        await users.remove(websocket)

start_server = websockets.serve(main, "localhost", 8765)
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(question_engine.pause_and_start_new(users))
    loop.run_until_complete(start_server) # TODO try create_task even for this
    loop.run_forever()
