from redbot.core import commands, checks, Config
from redbot.core.i18n import Translator, cog_i18n
from jsonschema.exceptions import ValidationError
from .story import Story, StoryStateError
import discord
import aiohttp
import json

CONFIG_IDENTIFIER = "769f6635-f604-4e47-ac20-a12e981474fb"
_ = Translator("AdventurePal", __file__)

COMMAND_PREFIX = "advpal"
CHOOSE_CMD = _("choose")
BOOKMARKS_CMD = _("bookmarks")
RESET_CMD = _("reset")
LOAD_CMD = _("load")
UNLOAD_CMD = _("unload")
ERROR = _("An error has occured.")
FAILED_BOOKMARK_RESET = _("The bookmark you entered does not match any bookmark you've reached yet.")
BOOKMARKS_LIST_TITLE = _("Bookmarks")
BOOKMARK_FIELD = _("Bookmark")
DESCRIPTION_FIELD = _("Description")
OPTIONS_FIELD = _("Options")
BAD_END_MESSAGE = _("You did not choose wisely. This was not the way it was meant to end.")
VICTORY_MESSAGE = _("You have found a true ending of the story.")
NO_VALID_STORY = _("You must pass your story as an attachment for this to work.")
FAILED_TO_OPEN_FILE = _("Failed to read your story file.")
INVALID_OPTION = _("{} is not a valid option. Pick one of the options listed.")
INVALID_START_STATE = _("Loaded story has invalid starting state.")
INVALID_STORY_LOADED = _("Loaded story is invalid. Check your '{}' field.")
INVALID_STORY_STATES = _("""
Loaded story references a bookmark '{}' that is undefined. Check to make sure you defined this state in the 'states' bracket and that both are typed the same way including letter case. Additionally, ensure that none of your options
include the word 'advpal'.
""")
NO_STORY_LOADED = _("You cannot enter this command until this channel has a story loaded.")
RESET_MESSAGE = _("""
You may choose to return to a bookmark.
Check the list of bookmarks you have already reached by typing:
[p]advpal bookmarks
Return to one of your choosing by typing:
[p]advpal bookmarks reset [bookmark name]
(Note: [p] is your bot command prefix)
""")

@cog_i18n(_)
class AdventurePal(commands.Cog):
    def __init__(self):
        self.config = Config.get_conf(self, identifier=CONFIG_IDENTIFIER)
        default_global = { "channels": [] }
        default_channel = { "story": {} }
        default_guild = { "stories": {} }
        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)
        self.config.register_channel(**default_channel)

    def collapse_args(func):
        async def collapsed_args(self, ctx, story, *args):
            return await func(self, ctx, story, ' '.join(args))
        return collapsed_args

    def with_story(must_exist=True):
        def load_story_into_func(func):
            async def get_and_save_story(self, ctx, *args, **kwargs):
                channel_config = self.config.channel(ctx.channel)
                story_hash = await channel_config.story()
                if story_hash:
                    story = await self.try_load(ctx, story_hash, channel_config)
                    if not story:
                        return
                elif must_exist:
                    await self.error_message(ctx, NO_STORY_LOADED)
                    return
                else:
                    story = Story()
                await self.maybe_update_story(channel_config, await func(self, ctx, story, *args, **kwargs))
            return get_and_save_story
        return load_story_into_func


    async def on_message(self, message):
        if message.author.bot or COMMAND_PREFIX in message.content:
            return
        channel_config = self.config.channel(message.channel)
        story_hash = await channel_config.story()
        if story_hash:
            story = await self.try_load(message.channel, story_hash, channel_config)
            if story:
                story_changes = story.choose_option(message.content)
                await self.maybe_update_story(channel_config, story_changes)
                if story_changes:
                    await self.communicate_state(message.channel, story)

    @commands.group()
    async def advpal(self, ctx: commands.Context):
        pass

    @advpal.command(name=LOAD_CMD)
    @with_story(must_exist=False)
    async def load(self, ctx, story):
        if len(ctx.message.attachments) == 0:
            await self.error_message(ctx, NO_VALID_STORY)
            return
        attachment_hash = await self.load_json_attachment(ctx.message)
        if not attachment_hash:
            await self.error_message(ctx, FAILED_TO_OPEN_FILE)
            return
        story = await self.try_load(ctx, attachment_hash, self.config.channel(ctx.channel))
        if story:
            initial_state = story.set_initial_state()
            attachment_hash.update(initial_state)
            await self.communicate_state(ctx, story)
            return attachment_hash

    @advpal.command(name=UNLOAD_CMD)
    async def unload(self, ctx):
        async with self.config.channel(ctx.channel).story() as story:
            story.clear()

    @advpal.command(name=CHOOSE_CMD)
    @with_story()
    @collapse_args
    async def choose(self, ctx, story, option):
        return await self.try_story_operation(ctx, story, option, story.choose_option, INVALID_OPTION)

    @advpal.command(name=RESET_CMD)
    @with_story()
    @collapse_args
    async def reset(self, ctx, story, bookmark):
        return await self.try_story_operation(ctx, story, option, story.bookmark_reset, FAILED_BOOKMARK_RESET)

    @advpal.command(name=BOOKMARKS_CMD)
    @with_story()
    async def bookmarks(self, ctx, story):
        em = discord.Embed(title=BOOKMARKS_LIST_TITLE, description=story.bookmarks_string())
        await ctx.send(embed=em)

    async def try_story_operation(self, ctx, story, arg, func, error_msg):
        story_changes = func(arg)
        if story_changes:
            await self.communicate_state(ctx, story)
            return story_changes
        await self.error_message(ctx, error_msg.format(arg))

    async def try_load(self, ctx, story_hash, channel_config):
        try:
            story = Story()
            return story.load_from_hash(story_hash)
        except ValidationError as e:
            await self.error_message(ctx, INVALID_STORY_LOADED.format(e.path.pop()))
        except StoryStateError as e:
            await self.error_message(ctx, INVALID_STORY_STATES.format(e.state))
        async with channel_config.story() as story:
            story.clear()
        return None

    async def maybe_update_story(self, channel_config, story_changes):
        if story_changes:
            async with channel_config.story() as story:
                story.update(story_changes)


    def build_state_embed(self, story):
        em = discord.Embed()
        em.add_field(name=BOOKMARK_FIELD, value=story.bookmark())
        em.add_field(name=DESCRIPTION_FIELD, value=story.text())
        options = story.options()
        if options: em.add_field(name=OPTIONS_FIELD, value=options)
        imgsrc = story.image()
        if imgsrc: em.set_image(url=imgsrc)
        return em

    async def load_json_attachment(self, message):
        story_attachment = message.attachments[0]
        async with aiohttp.ClientSession() as session:
            async with session.get(story_attachment.url) as r:
                if r.status != 200: return False
                try: contents = await r.json()
                except (aiohttp.client_exceptions.ContentTypeError, json.decoder.JSONDecodeError):
                  return False
                return contents

    async def error_message(self, ctx, error):
        await ctx.send(embed=discord.Embed(title=ERROR, description=error))

    async def communicate_state(self, ctx, story):
        await ctx.send(embed=self.build_state_embed(story))
        ending = story.get_ending()
        message = None
        if ending:
          if ending == "good":
            em = discord.Embed(description=RESET_MESSAGE, title=VICTORY_MESSAGE)
          if ending == "bad":
            em = discord.Embed(description=RESET_MESSAGE, title=BAD_END_MESSAGE)
          await ctx.send(embed=em)
