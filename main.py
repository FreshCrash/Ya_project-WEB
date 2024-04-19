import asyncio
import discord
import schedule
from discord.ext import commands
import logging
import datetime
from data import db_session
from data.reminds import Remind

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)
wdays = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
launched = False

def send_ctx(ctx, message):
    asyncio.ensure_future(ctx.send(message))
@bot.event
async def on_ready():
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)

@bot.command(name='remind')
async def new_remind(ctx, day_month, hour_minute, *rltext):
    rtext = " ".join(rltext)
    rtime = datetime.datetime.strptime(str(datetime.datetime.now().year) + " " + day_month + hour_minute,
                                       "%Y %d.%m%H:%M")
    now = datetime.datetime.now()
    dtime = (rtime - now).total_seconds()
    await ctx.send(round(dtime))
    await ctx.send(f"Reminder for <@{ctx.message.author.id}> set: {rtext} in {day_month}, {hour_minute}.")
    await asyncio.sleep(round(dtime))
    await ctx.send(f"Reminder for <@{ctx.message.author.id}>: {rtext}!")


@bot.command(name="weekly")
async def weekly_remind(ctx, weekday, hour_minute, *rltext):
    rtext = " ".join(rltext)
    if weekday == "mon":
        schedule.every().monday.at(hour_minute).do(send_ctx, ctx, f"Reminder for <@{ctx.message.author.id}>: {rtext}!")
    elif weekday == "tue":
        schedule.every().tuesday.at(hour_minute).do(send_ctx, ctx, f"Reminder for <@{ctx.message.author.id}>: {rtext}!")
    elif weekday == "wed":
        schedule.every().wednesday.at(hour_minute).do(send_ctx, ctx, f"Reminder for <@{ctx.message.author.id}>: {rtext}!")
    elif weekday == "thu":
        schedule.every().thursday.at(hour_minute).do(send_ctx, ctx, f"Reminder for <@{ctx.message.author.id}>: {rtext}!")
    elif weekday == "fri":
        schedule.every().friday.at(hour_minute).do(send_ctx, ctx, f"Reminder for <@{ctx.message.author.id}>: {rtext}!")
    elif weekday == "sat":
        schedule.every().saturday.at(hour_minute).do(send_ctx, ctx, f"Reminder for <@{ctx.message.author.id}>: {rtext}!")
    elif weekday == "sun":
        schedule.every().sunday.at(hour_minute).do(send_ctx, ctx, f"Reminder for <@{ctx.message.author.id}>: {rtext}!")
    await ctx.send(f"Reminder for <@{ctx.message.author.id}> set: {rtext} every {weekday} at {hour_minute}.")
    rem = Remind()
    rem.type = "weekly"
    rem.day = weekday
    rem.userid = ctx.message.author.id
    rem.time = hour_minute
    rem.text = rtext
    db_sess = db_session.create_session()
    db_sess.add(rem)
    db_sess.commit()

db_session.global_init("db/reminds.db")
TOKEN = open("token.txt").readline()
bot.run(TOKEN)