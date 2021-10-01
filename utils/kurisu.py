import asyncio
import logging
import os

from aiohttp import ClientSession
from databases import Database
from discord.ext import commands
import discord
import lavalink
import toml

from .context import KurisuContext
from .log import LoggingHandler


class KurisuBot(commands.AutoShardedBot):
    """Idk"""

    def __init__(self, *args, **kwargs):
        for logger in [
            "kurisu",
            "discord.client",
            "discord.gateway",
            "discord.http",
            "discord.ext.commands.core",
            "listeners",
            "main",
        ]:
            logging.getLogger(logger).setLevel(
                logging.DEBUG if logger == "kurisu" else logging.INFO
            )
            logging.getLogger(logger).addHandler(LoggingHandler())
        self.logger = logging.getLogger("kurisu")
        super().__init__(
            help_command=None,
            intents=discord.Intents.all(),
            allowed_mentions=discord.AllowedMentions(roles=False, everyone=False),
            *args,
            **kwargs,
        )
        self.config = toml.load("config.toml")
        self.configoptions = toml.load("configoptions.toml")
        self.owner_ids: set = {000000000000}  # The 0's are a placeholder
        self.ok_color = int(
            str(self.get_config("configoptions", "options", "ok_color")).replace("#", "0x"),
            base=16,
        )
        self.error_color = int(
            str(self.get_config("configoptions", "options", "error_color")).replace("#", "0x"),
            base=16,
        )
        self.uptime = None
        self._session = None
        self.startup_time = discord.utils.utcnow()
        self.version = "3.2.2"
        self.db = Database("sqlite:///data/kurisu.db")
        self.executed_commands = 0
        self.prefixes = {}

    @property
    def database(self) -> Database:
        return self.db

    @property
    def session(self) -> ClientSession:
        if self._session is None:
            self._session = ClientSession(loop=self.loop)
        return self._session

    def get_config(self, file: str, group: str, config: str = None):
        if file == "configoptions":
            if not config:
                return self.configoptions[group]
            return self.configoptions[group][config]

        if file == "config":
            if not config:
                return self.config[group]
            return self.config[group][config]

    async def on_connect(self):
        self.logger.info(f"Logged in as {self.user.name}(ID: {self.user.id})")
        try:
            await self.db.connect()
        except AssertionError:
            pass
        self.logger.info("Connected to the database: `kurisu.db`")

    async def on_ready(self):
        if self.uptime is not None:
            return
        self.uptime = discord.utils.utcnow()
        self.logger.info(
            f"FINISHED CHUNKING {len(self.guilds)} GUILDS AND CACHING {len(self.users)} USERS",
        )
        self.logger.info(f"Registered Shard Count: {len(self.shards)}")
        owners = [
            await self.fetch_user(o) for o in self.get_config("config", "config", "owner_ids")
        ]
        self.logger.info(f"Recognized Owner(s): {', '.join(map(str, owners))}")
        self.logger.info(
            f"NO_PRIVLIEDGED_OWNERS config was set to {self.get_config('configoptions', 'options', 'no_priviledged_owners')}"
        )
        self.logger.info("ATTEMPTING TO MOUNT COG EXTENSIONS!")
        loaded_cogs = 0
        unloaded_cogs = 0
        for cog in os.listdir("./cogs"):
            if cog.endswith(".py"):
                try:
                    self.load_extension(f"cogs.{cog[:-3]}")
                    self.logger.info(f"Loaded {cog}")
                    loaded_cogs += 1
                except Exception as e:
                    unloaded_cogs += 1
                    self.logger.warning(f"Failed to load the cog: {cog}")
                    self.logger.warning(f"{e}")
        self.logger.info("DONE")
        self.logger.info(f"Total mounted cogs: {loaded_cogs}")
        msg = f"Total unmounted cogs: {unloaded_cogs}"
        self.logger.info(msg) if unloaded_cogs == 0 else self.logger.warning(msg)
        time_difference = ((self.startup_time - discord.utils.utcnow()) * 1000).total_seconds()
        formatted_time_difference = str(time_difference).replace("-", "")
        self.logger.info(f"Elapsed Time Since Startup: {formatted_time_difference} Ms")
        self.logger.info("STARTUP COMPLETE. READY!")

    # noinspection PyMethodMayBeStatic
    async def on_shard_disconnect(self, shard_id):
        self.logger.warning(f"SHARD {shard_id} IS NOW IN A DISCONNECTED STATE FROM DISCORD")

    async def on_message(self, message: discord.Message):
        ctx: KurisuContext = await self.get_context(message, cls=KurisuContext)
        await self.invoke(ctx)

    async def close(self):
        """Logs out bot and closes any active connections. Method is used to restart bot."""
        await super().close()
        await lavalink.close(self)
        self.logger.info("Severed LL Connections.")
        if self._session:
            await self._session.close()
            self.logger.info("HTTP Client Session(s) closed")
        await self.db.disconnect()
        self.logger.info("Database Connection Closed")
        await asyncio.sleep(1)

    async def full_exit(self):
        """Completely kills the process and closes all connections. However, it will continue to restart if being ran with PM2"""
        await lavalink.close(self)
        if self._session:
            await self._session.close()
            self.logger.info("HTTP Client Session Closed.")
        await self.db.disconnect()
        self.logger.info("Database Connection Closed")
        exit(code=26)

    async def reload_all_extensions(self, ctx: commands.Context = None):
        self.logger.info("Signal recieved to reload all bot extensions")
        success = 0
        failed = 0
        for cog in os.listdir("./cogs"):
            if cog.endswith(".py"):
                try:
                    self.reload_extension(f"cogs.{cog[:-3]}")
                    self.logger.info(f"Reloaded {cog}")
                    success += 1
                except Exception as e:
                    self.logger.warning(f"Failed reloading {cog}\n{e}")
                    failed += 1
        if ctx:
            await ctx.send(
                embed=discord.Embed(
                    description=f"Successfully reloaded {success} cog(s)\n Failed reloading {failed} cog(s)",
                    color=self.ok_color,
                ).set_footer(text="If any cogs failed to reload, check console for feedback.")
            )
