from redbot.core import commands, checks, Config
from .story import Story
import discord
import aiohttp
import json

CONFIG_IDENTIFIER = 2389284938

ERROR = "An error has occured."
FAILED_BOOKMARK_RESET = "The bookmark you entered does not match any bookmark you've reached yet."
BOOKMARKS_LIST_TITLE = "Bookmarks"
BOOKMARK_FIELD = "Bookmark"
DESCRIPTION_FIELD = "Description"
OPTIONS_FIELD = "Options"
BAD_END_MESSAGE = "You did not choose wisely. This was not the way it was meant to end."
VICTORY_MESSAGE = "You have found a true ending of the story."
NO_VALID_STORY = "You must pass your story as an attachment for this to work."
FAILED_TO_OPEN_FILE = "Failed to read your story file."
INVALID_OPTION = "{} is not a valid option. Pick one of the numbers shown."
INVALID_START_STATE = "Loaded story has invalid starting state."
RESET_MESSAGE = """
You may choose to return to a bookmark.
Check the list of bookmarks you have already reached by typing:
[p]advpal bookmarks
Return to one of your choosing by typing:
[p]advpal bookmarks reset [bookmark name]
(Note: [p] is your bot command prefix)
"""

class AdventurePal(commands.Cog):
    def __init__(self):
        self.config = Config.get_conf(self, identifier=CONFIG_IDENTIFIER)
        default_global = { "channels": [] }
        default_channel = { "story": {} }
        self.config.register_global(**default_global)
        self.config.register_channel(**default_channel)

    def __with_story(func):
        async def get_and_save_story(self, ctx, *args, **kwargs):
            channel_config = self.config.channel(ctx.channel)
            story_hash = await channel_config.story()
            story = Story()
            story.load_from_hash(story_hash)
            story_changes = await func(self, ctx, story, *args, **kwargs)
            if story_changes:
                async with channel_config.story() as story:
                    story.update(story_changes)
        return get_and_save_story

    def __collapse_args(func):
        async def collapsed_args(self, ctx, story, *args):
            return await func(self, ctx, story, ' '.join(args))
        return collapsed_args

    async def on_message(self, message):
        channel_config = self.config.channel(message.channel)
        story_hash = await channel_config.story()
        story = Story()
        story.load_from_hash(story_hash)
        story_changes = story.choose_option(message.content)
        if story_changes:
            await self.communicate_state(message.channel, story)
            async with channel_config.story() as story:
                story.update(story_changes)

    @commands.group()
    async def advpal(self, ctx: commands.Context):
        pass

    @advpal.command(name="load")
    @__with_story
    async def load(self, ctx, story):
        if len(ctx.message.attachments) == 0:
            await self.__error_message(ctx, NO_VALID_STORY)
            return
        attachment_hash = await self.load_attachment(ctx.message)
        if attachment_hash and story.load_from_hash(attachment_hash):
            initial_state = story.set_initial_state()
            if initial_state == {}:
                await self.__error_message(ctx, INVALID_START_STATE)
                return
            attachment_hash.update(initial_state)
            await self.communicate_state(ctx, story)
            return attachment_hash
        await self.__error_message(ctx, FAILED_TO_OPEN_FILE)

    @advpal.command(name="choose")
    @__with_story
    @__collapse_args
    async def choose(self, ctx, story, option):
        changes = story.choose_option(option)
        if changes:
            await self.communicate_state(ctx, story)
            return changes
        await self.__error_message(ctx, INVALID_OPTION.format(option))

    @advpal.command(name = "reset")
    @__with_story
    @__collapse_args
    async def reset(self, ctx, story, bookmark):
        changes = story.bookmark_reset(bookmark)
        if changes:
            await self.communicate_state(ctx, story)
            return changes
        await self.__error_message(ctx, FAILED_BOOKMARK_RESET)

    @advpal.command(name="bookmarks")
    @__with_story
    async def bookmarks(self, ctx, story):
        em = discord.Embed(title=BOOKMARKS_LIST_TITLE, description=story.bookmarks_string())
        await channel.send(embed=em)

    def build_state_embed(self, story):
        em = discord.Embed()
        em.add_field(name=BOOKMARK_FIELD, value=story.bookmark())
        em.add_field(name=DESCRIPTION_FIELD, value=story.text())
        options = story.options()
        if options: em.add_field(name=OPTIONS_FIELD, value=options)
        imgsrc = story.image()
        if imgsrc: em.set_image(url=imgsrc)
        return em

    async def load_attachment(self, message):
        story_attachment = message.attachments[0]
        async with aiohttp.ClientSession() as session:
            async with session.get(story_attachment.url) as r:
                if r.status != 200: return False
                try: contents = await r.json()
                except (aiohttp.client_exceptions.ContentTypeError, json.decoder.JSONDecodeError):
                  return False
                return contents

    async def communicate_state(self, ctx, story):
        await ctx.send(embed=self.build_state_embed(story))
        await self.__maybe_end_message(ctx, story)

    async def __error_message(self, ctx, error):
        await ctx.send(embed=discord.Embed(title=ERROR, description=error))

    async def __maybe_end_message(self, ctx, story):
        ending = story.get_ending()
        message = None
        if ending:
          if ending == "good":
            em = discord.Embed(description=RESET_MESSAGE, title=VICTORY_MESSAGE)
          if ending == "bad":
            em = discord.Embed(description=RESET_MESSAGE, title=BAD_END_MESSAGE)
          await ctx.send(embed=em)

