import asyncio
import discord
import schedule
from discord.ext import commands
from discord.ext.commands import Context
import logging
import datetime
from data import db_session
from data.reminds import Remind

db_session.global_init("db/reminds.db")
db_sess = db_session.create_session()
all_rems = db_sess.query(Remind).all()
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

rdict = {}
def send_ctx(ctx, message):
    asyncio.ensure_future(ctx.send(message))


@bot.event
async def on_ready():
    all_rems = db_sess.query(Remind).all()
    for remind in all_rems:
        weekday = remind.day
        hour_minute = remind.time
        rtext = remind.text
        channel = discord.utils.get(bot.get_all_channels(), guild__name=remind.guild, name=remind.channel)
        authorid = remind.userid
        if remind.r_type == "weekly":

            if weekday == "mon":
                rdict[remind.id] = schedule.every().monday.at(hour_minute).do(send_ctx, channel,
                                                           f"Reminder for <@{authorid}>: {rtext}!")
            elif weekday == "tue":
                rdict[remind.id] = schedule.every().tuesday.at(hour_minute).do(send_ctx, channel,
                                                           f"Reminder for <@{authorid}>: {rtext}!")
            elif weekday == "wed":
                rdict[remind.id] = schedule.every().wednesday.at(hour_minute).do(send_ctx, channel,
                                                           f"Reminder for <@{authorid}>: {rtext}!")
            elif weekday == "thu":
                rdict[remind.id] = schedule.every().thursday.at(hour_minute).do(send_ctx, channel,
                                                           f"Reminder for <@{authorid}>: {rtext}!")
            elif weekday == "fri":
                rdict[remind.id] = schedule.every().friday.at(hour_minute).do(send_ctx, channel,
                                                           f"Reminder for <@{authorid}>: {rtext}!")
            elif weekday == "sat":
                rdict[remind.id] = schedule.every().saturday.at(hour_minute).do(send_ctx, channel,
                                                           f"Reminder for <@{authorid}>: {rtext}!")
            elif weekday == "sun":
                rdict[remind.id] = schedule.every().sunday.at(hour_minute).do(send_ctx, channel,
                                                           f"Reminder for <@{authorid}>: {rtext}!")
        elif remind.r_type == "daily":
            rtext = remind.text
            rdict[remind.id] = schedule.every().day.at(hour_minute).do(send_ctx, channel, f"Reminder for <@{remind.userid}>: {rtext}!")
    all_rems = db_sess.query(Remind).all()
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
    rem = Remind()
    rem.r_type = "weekly"
    rem.day = weekday
    rem.userid = ctx.message.author.id
    rem.time = hour_minute
    rem.text = rtext
    rem.channel = ctx.channel.name
    rem.guild = ctx.guild.name
    db_sess.add(rem)
    db_sess.commit()
    all_rems = db_sess.query(Remind).all()
    remind = db_sess.query(Remind).filter(Remind.text == rtext and Remind.userid == ctx.message.author.id)
    if weekday == "mon":
        rdict[remind.id] = schedule.every().monday.at(hour_minute).do(send_ctx, ctx, f"Reminder for <@{ctx.message.author.id}>: {rtext}!")
    elif weekday == "tue":
        rdict[remind.id] = schedule.every().tuesday.at(hour_minute).do(send_ctx, ctx, f"Reminder for <@{ctx.message.author.id}>: {rtext}!")
    elif weekday == "wed":
        rdict[remind.id] = schedule.every().wednesday.at(hour_minute).do(send_ctx, ctx, f"Reminder for <@{ctx.message.author.id}>: {rtext}!")
    elif weekday == "thu":
        rdict[remind.id] = schedule.every().thursday.at(hour_minute).do(send_ctx, ctx, f"Reminder for <@{ctx.message.author.id}>: {rtext}!")
    elif weekday == "fri":
        rdict[remind.id] = schedule.every().friday.at(hour_minute).do(send_ctx, ctx, f"Reminder for <@{ctx.message.author.id}>: {rtext}!")
    elif weekday == "sat":
        rdict[remind.id] = schedule.every().saturday.at(hour_minute).do(send_ctx, ctx, f"Reminder for <@{ctx.message.author.id}>: {rtext}!")
    elif weekday == "sun":
        rdict[remind.id] = schedule.every().sunday.at(hour_minute).do(send_ctx, ctx, f"Reminder for <@{ctx.message.author.id}>: {rtext}!")
    await ctx.send(f"Reminder for <@{ctx.message.author.id}> set: {rtext} every {weekday} at {hour_minute}.")

@bot.command(name="daily")
async def daily_remind(ctx, hour_minute, *rltext):
    rtext = " ".join(rltext)
    rem = Remind()
    rem.r_type = "daily"
    rem.day = "every"
    rem.userid = ctx.message.author.id
    rem.time = hour_minute
    rem.text = rtext
    rem.channel = ctx.channel.name
    rem.guild = ctx.guild.name
    db_sess.add(rem)
    db_sess.commit()
    all_rems = db_sess.query(Remind).all()
    remind = db_sess.query(Remind).filter(Remind.text == rtext and Remind.userid == ctx.message.author.id)
    rdict[remind.id] = schedule.every().day.at(hour_minute).do(send_ctx, ctx, f"Reminder for <@{ctx.message.author.id}>: {rtext}!")
    await ctx.send(f"Reminder for <@{ctx.message.author.id}> set: {rtext} everyday at {hour_minute}.")




TOKEN = open("token.txt").readline()
bot.run(TOKEN)