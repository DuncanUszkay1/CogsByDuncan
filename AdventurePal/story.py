from enum import Enum
import json
START_STATE = 0

class MODIFICATION_LEVEL(Enum):
    CLEAN = 0
    STATE_ONLY = 1
    FULL = 2

class Story:
    def set_initial_state(self):
        self.bookmarks = []
        return self.__maybe_transfer_state(self.start)

    def load_from_hash(self, story_hash):
        try:
            self.states = story_hash["states"]
            self.title = story_hash["title"]
            self.author = story_hash["author"]
            self.start = story_hash["start"]
        except KeyError:
            return {}
        self.state = story_hash.get("state", None)
        self.bookmarks = story_hash.get("bookmarks", [])
        self.modification_level = MODIFICATION_LEVEL.CLEAN
        return self.__hash()

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
