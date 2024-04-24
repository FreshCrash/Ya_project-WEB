import asyncio
import discord
import schedule
from discord.ext import commands
import logging
import datetime
from data import db_session
from data.reminds import Remind
import time

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
rep_count = {}


def load_rem(r_type, rid, hour_minute, authorid, rtext, channel, weekday):
    global rdict
    if r_type == "weekly":

        if weekday == "mon":
            day_of_week = schedule.every().monday
        elif weekday == "tue":
            day_of_week = schedule.every().tuesday

        elif weekday == "wed":
            day_of_week = schedule.every().wednesday

        elif weekday == "thu":
            day_of_week = schedule.every().thursday

        elif weekday == "fri":
            day_of_week = schedule.every().friday

        elif weekday == "sat":
            day_of_week = schedule.every().saturday

        elif weekday == "sun":
            day_of_week = schedule.every().sunday

    elif r_type == "daily":
        day_of_week = schedule.every().day
    if r_type != "custom":
        try:
            rdict[rid] = day_of_week.at(hour_minute).do(send_ctx, channel,
                                                        f"Remind for <@{authorid}>: {rtext}! (id = {rid})", rid)
            logger.debug(f"Loaded remind {rid}")
        except Exception:
            db_sess.query(Remind).filter(Remind.id == rid).delete()
            db_sess.commit()
            logger.error(f"Invalid time format of remind {rid}. Remind removed")
    else:
        rdict[rid] = schedule.every(int(hour_minute)).seconds.do(send_ctx, channel,
                                                                 f"Remind for <@{authorid}>: {rtext}! (id = {rid})",
                                                                 rid)
        logger.debug("Loaded custom remind")


def send_ctx(ctx, message, rid):
    if rep_count[rid] != 0:
        asyncio.ensure_future(ctx.send(message))
        if rep_count[rid] > 0:
            rep_count[rid] -= 1
    else:
        db_sess.query(Remind).filter(Remind.id == rid).delete()
        db_sess.commit()
        rdict.pop(rid)
        rep_count.pop(rid)
        return schedule.CancelJob


@bot.event
async def on_ready():
    global all_rems
    all_rems = db_sess.query(Remind).all()
    for remind in all_rems:
        weekday = remind.day
        rep_count[remind.id] = remind.reps
        rtext = remind.text
        channel = discord.utils.get(bot.get_all_channels(), guild__name=remind.guild, name=remind.channel)
        load_rem(remind.r_type, remind.id, remind.time, remind.userid, rtext, channel, weekday)
    all_rems = db_sess.query(Remind).all()
    logger.info("Reminds loaded!")
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
    logger.info(f"New single remind")
    await ctx.send(f"Remind for <@{ctx.message.author.id}> set: {rtext} in {day_month}, {hour_minute}.")
    await asyncio.sleep(round(dtime))
    await ctx.send(f"Remind for <@{ctx.message.author.id}>: {rtext}!")


@bot.command(name="weekly")
async def weekly_remind(ctx, weekday, hour_minute, *rltext):
    global all_rems
    global rep_count
    rep = -1
    for word in rltext:
        if word[:4:] == "rep=":
            try:
                rep = int(word[4::])
            except Exception:
                pass
    rtext = " ".join(rltext)
    rem = Remind()
    rem.r_type = "weekly"
    rem.day = weekday
    rem.userid = ctx.message.author.id
    rem.time = hour_minute
    rem.text = rtext
    rem.channel = ctx.channel.name
    rem.guild = ctx.guild.name
    rem.reps = rep
    db_sess.add(rem)
    db_sess.commit()
    all_rems = db_sess.query(Remind).all()
    remind = db_sess.query(Remind).filter(Remind.text == rtext and Remind.userid == ctx.message.author.id).first()
    load_rem(remind.r_type, remind.id, remind.time, remind.userid, rtext, ctx.channel, weekday)
    rep_count[remind.id] = rep
    logger.info(f"New weekly remind {remind.id}")
    await ctx.send(f"Remind for <@{ctx.message.author.id}> set: {rtext} everyday at {hour_minute}. (id = {remind.id})")


@bot.command(name="daily")
async def daily_remind(ctx, hour_minute, *rltext):
    global all_rems
    global rep_count
    rep = -1
    rttext = []
    for word in rltext:
        if word[:4:] == "rep=":
            try:
                rep = int(word[4::])
            except Exception:
                rttext.append(word)
        else:
            rttext.append(word)
    rtext = " ".join(rttext)
    rem = Remind()
    rem.r_type = "daily"
    rem.day = "every"
    rem.userid = ctx.message.author.id
    rem.time = hour_minute
    rem.text = rtext
    rem.channel = ctx.channel.name
    rem.guild = ctx.guild.name
    rem.reps = rep
    db_sess.add(rem)
    db_sess.commit()
    all_rems = db_sess.query(Remind).all()
    remind = db_sess.query(Remind).filter(Remind.text == rtext and Remind.userid == ctx.message.author.id).first()
    rep_count[remind.id] = rep
    logger.info(f"New daily remind {remind.id}")
    rdict[remind.id] = schedule.every().day.at(hour_minute).do(send_ctx, ctx,
                                                               f"Reminder for <@{ctx.message.author.id}>: {rtext}!",
                                                               remind.id)
    await ctx.send(f"Remind for <@{ctx.message.author.id}> set: {rtext} everyday at {hour_minute}. (id = {remind.id})")


@bot.command(name="custom")
async def custom_remind(ctx, *args):
    global all_rems
    rttext = []
    days = 0
    hours = 0
    minutes = 0
    seconds = 0
    rep = -1
    for arg in args:
        if arg[-1] == "d":
            try:
                days = int(arg[:-1:])
            except Exception:
                rttext.append(arg)
        elif arg[-1] == "h":
            try:
                hours = int(arg[:-1:])
            except Exception:
                rttext.append(arg)
        elif arg[-1] == "m":
            try:
                minutes = int(arg[:-1:])
            except Exception:
                rttext.append(arg)
        elif arg[-1] == "s":
            try:
                seconds = int(arg[:-1:])
            except Exception:
                rttext.append(arg)
        elif arg[:4:] == "rep=":
            try:
                rep = int(arg[4::])
            except Exception:
                rttext.append(arg)
        else:
            rttext.append(arg)
    rtext = " ".join(rttext)
    total_seconds = (days * 86400) + (hours * 3600) + (minutes * 60) + seconds
    rem = Remind()
    rem.r_type = "custom"
    rem.day = None
    rem.userid = ctx.message.author.id
    rem.time = total_seconds
    rem.text = rtext
    rem.channel = ctx.channel.name
    rem.guild = ctx.guild.name
    rem.reps = rep
    db_sess.add(rem)
    db_sess.commit()
    all_rems = db_sess.query(Remind).all()
    remind = db_sess.query(Remind).filter(Remind.text == rtext and Remind.userid == ctx.message.author.id).first()
    rep_count[remind.id] = rep
    logger.info(f"New custom remind {remind.id}")
    load_rem("custom", remind.id, total_seconds, remind.userid, rtext, ctx, None)
    await ctx.send(
        f"New custom remind for <@{remind.userid}>: {rtext}, every {days} days, {hours} hours, {minutes} minutes and {seconds} seconds. (id = {remind.id})")


@bot.command(name="delete")
async def delete_rem(ctx, rem_id):
    try:
        job = rdict[int(rem_id)]
        rem = db_sess.query(Remind).filter(Remind.id == rem_id).first()
        if ctx.message.author.id == rem.userid:
            schedule.cancel_job(job)
            db_sess.query(Remind).filter(Remind.id == rem_id).delete()
            db_sess.commit()
            await ctx.send("Remind successfully deleted")
            logger.info(f"Remind {rem_id} deleted")
        else:
            await ctx.send("Error: you are not a creator of this remind!")
            logger.info(f"Remind {rem_id} was not deleted")
    except KeyError:
        await ctx.send("Error: Invalid id!")
        logger.info(f"No remind with id {rem_id} found")


@bot.command(name="my_reminds")
async def listrems(ctx):
    rems = db_sess.query(Remind).filter(Remind.userid == ctx.message.author.id).all()
    if len(rems) == 0:
        await ctx.send(f"You have no reminds.")
    for remind in rems:
        if remind.r_type == "weekly":
            await ctx.send(f"{remind.text} every {remind.day} at {remind.time}. ID = {remind.id}")
        elif remind.r_type == "daily":
            await ctx.send(f"{remind.text} everyday at {remind.time}. ID = {remind.id}")
        elif remind.r_type == "custom":
            await ctx.send(
                f"{remind.text} every {time.strftime('%dd, %H:%M:%S', time.gmtime(int(remind.time)))}. ID = {remind.id}")


@bot.command(name="bot_help")
async def c_help(ctx):
    await ctx.send(f"This is a reminder bot."
                   f"\nCommands:\n1. Remind. It reminds you about something once. "
                   f"Format: !remind [day].[month] [hour]:[minute] [text]"
                   f". Example: !remind 12.04 19:20 feed my cat.\n"
                   f"2. Weekly. Sets a weekly remind. Format: !weekly [day(3-letter)] [hour]:[minute] [text]. "
                   f"Example: !weekly fri 12:33 feed my cat.\n"
                   f"3. Daily. Sets a daily remind. Format: !daily [hour]:[minute] [text]. "
                   f"Example: !daily 15:30 say hi\n"
                   f"4. Custom. Sets a remind with custom interval. "
                   f"This command has no exact format, you can insert your interval anywhere in the command. "
                   f"Examples: !custom 10s test, !custom 15m test2, !custom 3d 12 h test3\n"
                   f"5. Delete. Deletes a remind Format: !delete id. Example: !delete 1.\n"
                   f"6. My reminds. This command returns you list of your reminds. Format: !my_reminds.\n"
                   f"Also you can insert rep=[repeats] to repeat your remind as many times as you want.")


TOKEN = open("token.txt").readline()
bot.run(TOKEN)
