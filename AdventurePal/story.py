from enum import Enum
from jsonschema import validate
from jsonschema.exceptions import ValidationError
import json

COMMAND_PREFIX = "advpal"

story_schema = {
    "type": "object",
    "properties": {
        "title": {"type" : "string"},
        "author": {"type" : "string"},
        "start": {"type" : "string"},
        "states": {"type": "object"}
    }
}

state_schema = {
    "type": "object",
    "properties": {
        "bookmark": {"type": "string"},
        "text": {"type": "string"},
        "imgsrc": {"type": "string"},
        "ending": {"type": "string"},
        "options": {"type": "object"}
    }
}

options_schema = {
    "type": "object",
    "patternproperties": {
        ".*": {"type": "string"}
    }
}

class StoryStateError(Exception):
    def __init__(self, state):
        self.state = state

class Story:
    def set_initial_state(self):
        self.bookmarks = []
        return self.__maybe_transfer_state(self.start)

    def validate(self):
        validate(self.__hash(), story_schema)
        if self.start not in self.states.keys():
            raise StoryStateError(self.start)
        self.validate_states()

    def validate_states(self):
        for bookmark, state in self.states.items():
            validate(state, state_schema)
            self.validate_options(state)

    def validate_options(self, state):
        validate(state["options"], options_schema)
        for option, bookmark in state["options"].items():
            if COMMAND_PREFIX in bookmark or not bookmark in self.states:
                raise StoryStateError(bookmark)

    def load_from_hash(self, story_hash):
        self.states = story_hash.get("states", None)
        self.title = story_hash.get("title", None)
        self.author = story_hash.get("author", None)
        self.start = story_hash.get("start", None)
        self.state = story_hash.get("state", None)
        self.bookmarks = story_hash.get("bookmarks", [])
        self.validate()
        return self


    def bookmarks_string(self):
        return "\n".join(self.bookmarks)

    def get_ending(self):
        return self.__get_state_data().get("ending", None)

    def choose_option(self, option):
        next_state = self.__get_state_data()["options"].get(option, None)
        return self.__maybe_transfer_state(next_state)

    def bookmark_reset(self, bookmark):
        bookmark = (bookmark if bookmark in self.bookmarks else None)
        return self.__maybe_transfer_state(bookmark)

    def bookmark(self):
        return self.__get_state_data()["bookmark"]

    def text(self):
        return self.__get_state_data()["text"]

    def image(self):
        return self.__get_state_data().get("imgsrc", None)

    def options(self):
        options = self.__get_state_data()["options"]
        if options:
            return "\n".join(options.keys())
        return None

    def __hash(self):
        story_hash = {
            "states": self.states,
            "title": self.title,
            "author": self.author,
            "start": self.start
        }
        story_hash.update(self.__state_hash())
        return story_hash

    def __state_hash(self):
        return {
            "state": self.state,
            "bookmarks": list(self.bookmarks),
        }

    def __maybe_transfer_state(self, state):
        if state:
            self.state = state
            self.__add_bookmark(state)
            return self.__state_hash()
        return {}

    def __add_bookmark(self, bookmark):
        if not bookmark in self.bookmarks:
            self.bookmarks.append(bookmark)

    def __get_state_data(self):
        return self.states[self.state]
