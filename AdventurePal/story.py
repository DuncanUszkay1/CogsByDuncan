import json
sample_states = [
  {
    "bookmark": "Dark Room",
    "text": "You are in a dark room. To your left is a door, to your right is a hole. Do you go left or right?",
    "imgsrc": "https://www.escapeall.gr/Images/ServicesPhotos/d0d9794b-573a-4a56-80e1-7015acc2ae7f/e1585535-c825-48c6-b5ea-6f181155e528.jpg",
    "options": [
        {
            "text": "go left",
            "state": 1
        },
        {
            "text": "go right",
            "state": 2
        }
    ]
  },
  {
    "bookmark": "Sweet Victory",
    "text": "Behind the doors lies an enourmous stash of sealed blue ray copies of madagascar. Congradulations",
    "imgsrc": "https://images-na.ssl-images-amazon.com/images/I/91EPpEmV-qL._SX425_.jpg",
    "options": [],
    "ending": "good"
  },
  {
    "bookmark": "Endless Shaft",
    "text": "You are now tumbling down an endless shaft into the bowels of the earth. You may now do a flip if you wish.",
    "imgsrc": "https://i.ytimg.com/vi/E4flwk5rp8I/hqdefault.jpg",
    "options": [
        {
            "text": "do a flip",
            "state": 3
        }
    ]
  },
  {
    "bookmark": "Death",
    "text": "The hole goes down for hundreds of miles. You die instantly on impact with the ground. RIP",
    "imgsrc": "https://new-img.patrika.com/upload/2017/08/28/demo_pic_-_patrika_chhattisgarh__1756429_835x547-m.jpeg",
    "options": [],
    "ending": "bad"
  }
]

START_STATE = 0

class StoryEncoder:
    @staticmethod
    def to_json(story):
        return{
            "states": story.states,
            "title": story.title,
            "author": story.author,
            "state": story.state,
            "bookmarks": story.bookmarks
        }

    @staticmethod
    def from_json(json):
        story = Story()
        story.states = json["states"]
        story.title = json["title"]
        story.author = json["author"]
        story.state = json["state"]
        story.bookmarks = json["bookmarks"]
        return story


class Story:
    def __init__(self):
        self.states = []
        self.title = "NO STORY LOADED"
        self.author = ""
        self.set_initial_state()

    def load_sample(self):
        self.states = sample_states
        self.title = "Sample Story"
        self.author = "Kilgore Trout"

    def load_from_json(self, json):
        try:
            self.states = json["states"]
            self.title = json["title"]
            self.author = json["author"]
        except KeyError:
            return False
        self.set_initial_state()
        return True

    def set_initial_state(self):
        self.state = START_STATE
        self.bookmarks = [START_STATE]

    def get_state_data(self):
        return self.states[self.state]

    def numbered_list(self, array, represent_func):
        return "\n".join([str(i+1) + ": " + represent_func(a) for i,a in enumerate(array)])

    def options_string(self):
        options = self.get_state_data()["options"]
        if options:
            return self.numbered_list(options, lambda o: o["text"])
        return None

    def bookmarks_string(self):
        return self.numbered_list(self.bookmarks, lambda b: self.states[b]["bookmark"])

    def get_ending(self):
        return self.get_state_data().get("ending", None)

    def transfer_state(self, state):
        self.state = state
        self.bookmarks.append(state)

    def choose_option(self, index):
        options = self.get_state_data()["options"]
        if index < 0 or index >= len(options):
            return False
        self.transfer_state(options[index]["state"])
        return True

    def bookmark_reset(self, index):
        if index < 0 or index >= len(self.bookmarks):
            return False
        self.state = self.bookmarks[index]
        return True


