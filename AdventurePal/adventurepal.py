from redbot.core import commands, checks, Config
from .story import Story, StoryEncoder
import discord
import aiohttp
import json

CONFIG_IDENTIFIER = 2389284938

ERROR = "An error has occured."
FAILED_BOOKMARK_RESET = "The bookmark you entered does not match any bookmark you've reached yet."
BAD_END_MESSAGE = "You did not choose wisely. This was not the way it was meant to end."
VICTORY_MESSAGE = "You have found a true ending of the story."
NO_VALID_STORY = "You must pass your story as an attachment for this to work."
FAILED_TO_OPEN_FILE = "Failed to read your story file."
INVALID_OPTION = "{} is not a valid option. Pick one of the numbers shown."
RESET_MESSAGE = """
You may choose to return to any bookmark you have already reached.
Check the list of bookmarks you have already reached by typing:
[p]advpal bookmarks list
Return to one of your choosing by typing:
[p]advpal bookmarks reset [bookmark index]
(Note: [p] is your bot command prefix)
"""

class AdventurePal(commands.Cog):
    def __init__(self):
        self.config = Config.get_conf(self, identifier=CONFIG_IDENTIFIER)
        #sample_story = Story()
        #sample_story.load_sample()
        default_global = { "channels": [] }
        default_channel = { "story": None }
        self.config.register_global(**default_global)
        self.config.register_channel(**default_channel)

    def with_story(func):
        async def get_and_save_story(self, ctx, *args, **kwargs):
            channel_config = self.config.channel(ctx.channel)
            story_json = await channel_config.story()
            story = StoryEncoder.from_json(story_json)
            story = await func(self, ctx, story, *args, **kwargs)
            if story:
                await channel_config.story.set(StoryEncoder.to_json(story))
        return get_and_save_story

    def zero_index_input(func):
        async def reduce_input(self, ctx, story, option, *args, **kwargs):
            if option.isdigit():
                option = str(int(option) - 1)
            return await func(self, ctx, story, option, *args, **kwargs)
        return reduce_input

    def build_state_embed(self, story):
        state_data = story.get_state_data()
        options = story.options_string()
        imgsrc = state_data.get("imgsrc", None)
        em = discord.Embed()
        em.add_field(name="Bookmark", value=state_data["bookmark"])
        em.add_field(name="Description", value=state_data["text"])
        if options:
            em.add_field(name="Options", value=options)
        if imgsrc:
            em.set_image(url=imgsrc)
        return em

    async def load_attachment(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                if r.status != 200:
                    return False
                try:
                  contents = await r.json()
                except (aiohttp.client_exceptions.ContentTypeError, json.decoder.JSONDecodeError):
                  return False
                return contents

    async def communicate_state(self, ctx, story):
        await ctx.send(embed=self.build_state_embed(story))
        await self.maybe_end_message(ctx, story)

    async def error_message(self, ctx, error):
        await ctx.send(embed=discord.Embed(title=ERROR, description=error))

    async def maybe_end_message(self, ctx, story):
        ending = story.get_ending()
        message = None
        if ending:
          if ending == "good":
            em = discord.Embed(description=RESET_MESSAGE, title=VICTORY_MESSAGE)
          if ending == "bad":
            em = discord.Embed(description=RESET_MESSAGE, title=BAD_END_MESSAGE)
          await ctx.send(embed=em)

    async def on_message(self, message):
        print("on message")
        channel = message.channel
        channels = await self.config.channels()
        if message.channel in channels and not message.bot:
            self.choose(self, message, message.text)


    @commands.group()
    async def advpal(self, ctx: commands.Context):
        pass

    @advpal.command(name="choose")
    @with_story
    @zero_index_input
    async def choose(self, ctx, story, option):
        print("time to choose")
        if not option.isdigit() or story.choose_option(int(option)) is None:
            await self.error_message(ctx, INVALID_OPTION.format(option))
            return
        await self.communicate_state(ctx, story)
        return story


    @advpal.command(name="reset_sample")
    @with_story
    async def reset_sample(self, ctx, story):
        story.load_sample()
        story.set_initial_state()
        return story

    @advpal.command(name="load")
    @with_story
    async def load(self, ctx, story):
        if len(ctx.message.attachments) == 0:
            await self.error_message(ctx, NO_VALID_STORY)
            return
        story_attachment = ctx.message.attachments[0]
        attachment_json = await self.load_attachment(story_attachment.url)
        if attachment_json and story.load_from_json(attachment_json):
            await self.communicate_state(ctx, story)
            return story
        await self.error_message(ctx, FAILED_TO_OPEN_FILE)

    @advpal.command(name="start")
    @with_story
    async def start(self, ctx, story):
        story.set_initial_state()
        await self.communicate_state(ctx, story)
        return story

    @advpal.group()
    async def bookmarks(self, ctx: commands.Context):
        pass

    @bookmarks.command(name = "list")
    @with_story
    async def list(self, ctx, story):
        em = discord.Embed(title="Bookmarks", description=story.bookmarks_string())
        await ctx.send(embed=em)

    @bookmarks.command(name = "reset")
    @with_story
    @zero_index_input
    async def reset(self, ctx, story, bookmark):
        if bookmark.isdigit() and story.bookmark_reset(int(bookmark)):
            await self.communicate_state(ctx, story)
            return story
        await self.error_message(ctx, FAILED_BOOKMARK_RESET)
        await self.list(ctx, story)
