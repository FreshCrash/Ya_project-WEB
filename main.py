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
db_session = db_session.create_session()
all_reminds = db_session.query(Remind).all()

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)
week_days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
launched = False

id_to_job = {}
repeats_count = {}


def load_remind(remind_type, remind_id, hour_minute, author_id, remind_text, channel, weekday):
    global id_to_job
    if remind_type == "weekly":

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

    elif remind_type == "daily":
        day_of_week = schedule.every().day
    if remind_type != "custom":
        try:
            id_to_job[remind_id] = day_of_week.at(hour_minute).do(send_message, channel,
                                                                  f"Remind for <@{author_id}>: {remind_text}! (id = {remind_id})",
                                                                  remind_id)
            logger.debug(f"Loaded remind {remind_id}")
        except Exception:
            db_session.query(Remind).filter(Remind.id == remind_id).delete()
            db_session.commit()
            logger.error(f"Invalid time format of remind {remind_id}. Remind removed")
    else:
        id_to_job[remind_id] = schedule.every(int(hour_minute)).seconds.do(send_message, channel,
                                                                           f"Remind for <@{author_id}>: {remind_text}! (id = {remind_id})",
                                                                           remind_id)
        logger.debug("Loaded custom remind")


def send_message(ctx, message, remind_id):
    if repeats_count[remind_id] != 0:
        asyncio.ensure_future(ctx.send(message))
        if repeats_count[remind_id] > 0:
            repeats_count[remind_id] -= 1
    else:
        db_session.query(Remind).filter(Remind.id == remind_id).delete()
        db_session.commit()
        id_to_job.pop(remind_id)
        repeats_count.pop(remind_id)
        return schedule.CancelJob


@bot.event
async def on_ready():
    global all_reminds
    all_reminds = db_session.query(Remind).all()
    for remind in all_reminds:
        weekday = remind.day
        repeats_count[remind.id] = remind.reps
        remind_text = remind.text
        channel = discord.utils.get(bot.get_all_channels(), guild__name=remind.guild, name=remind.channel)
        load_remind(remind.r_type, remind.id, remind.time, remind.userid, remind_text, channel, weekday)
    all_reminds = db_session.query(Remind).all()
    logger.info("Reminds loaded!")
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)


@bot.command(name='remind')
async def new_remind(ctx, day_month, hour_minute, *var_args):
    remind_text = " ".join(var_args)
    remind_time = datetime.datetime.strptime(str(datetime.datetime.now().year) + " " + day_month + hour_minute,
                                             "%Y %d.%m%H:%M")
    now = datetime.datetime.now()
    dtime = (remind_time - now).total_seconds()
    logger.info(f"New single remind")
    await ctx.send(f"Remind for <@{ctx.message.author.id}> set: {remind_text} in {day_month}, {hour_minute}.")
    await asyncio.sleep(round(dtime))
    await ctx.send(f"Remind for <@{ctx.message.author.id}>: {remind_text}!")


@bot.command(name="weekly")
async def weekly_remind(ctx, weekday, hour_minute, *var_args):
    global all_reminds
    global repeats_count
    rep = -1
    for word in var_args:
        if word[:4:] == "rep=":
            try:
                rep = int(word[4::])
            except Exception:
                pass
    remind_text = " ".join(var_args)
    remind = Remind()
    remind.r_type = "weekly"
    remind.day = weekday
    remind.userid = ctx.message.author.id
    remind.time = hour_minute
    remind.text = remind_text
    remind.channel = ctx.channel.name
    remind.guild = ctx.guild.name
    remind.reps = rep
    db_session.add(remind)
    db_session.commit()
    all_reminds = db_session.query(Remind).all()
    remind = db_session.query(Remind).filter(
        Remind.text == remind_text and Remind.userid == ctx.message.author.id).first()
    load_remind(remind.r_type, remind.id, remind.time, remind.userid, remind_text, ctx.channel, weekday)
    repeats_count[remind.id] = rep
    logger.info(f"New weekly remind {remind.id}")
    await ctx.send(
        f"Remind for <@{ctx.message.author.id}> set: {remind_text} everyday at {hour_minute}. (id = {remind.id})")


@bot.command(name="daily")
async def daily_remind(ctx, hour_minute, *var_args):
    global all_reminds
    global repeats_count
    rep = -1
    rttext = []
    for word in var_args:
        if word[:4:] == "rep=":
            try:
                rep = int(word[4::])
            except Exception:
                rttext.append(word)
        else:
            rttext.append(word)
    remind_text = " ".join(rttext)
    remind = Remind()
    remind.r_type = "daily"
    remind.day = "every"
    remind.userid = ctx.message.author.id
    remind.time = hour_minute
    remind.text = remind_text
    remind.channel = ctx.channel.name
    remind.guild = ctx.guild.name
    remind.reps = rep
    db_session.add(remind)
    db_session.commit()
    all_reminds = db_session.query(Remind).all()
    remind = db_session.query(Remind).filter(
        Remind.text == remind_text and Remind.userid == ctx.message.author.id).first()
    repeats_count[remind.id] = rep
    logger.info(f"New daily remind {remind.id}")
    id_to_job[remind.id] = schedule.every().day.at(hour_minute).do(send_message, ctx,
                                                                   f"Reminder for <@{ctx.message.author.id}>: {remind_text}!",
                                                                   remind.id)
    await ctx.send(
        f"Remind for <@{ctx.message.author.id}> set: {remind_text} everyday at {hour_minute}. (id = {remind.id})")


@bot.command(name="custom")
async def custom_remind(ctx, *var_args):
    global all_reminds
    rttext = []
    days = 0
    hours = 0
    minutes = 0
    seconds = 0
    rep = -1
    for arg in var_args:
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
    remind_text = " ".join(rttext)
    total_seconds = (days * 86400) + (hours * 3600) + (minutes * 60) + seconds
    remind = Remind()
    remind.r_type = "custom"
    remind.day = None
    remind.userid = ctx.message.author.id
    remind.time = total_seconds
    remind.text = remind_text
    remind.channel = ctx.channel.name
    remind.guild = ctx.guild.name
    remind.reps = rep
    db_session.add(remind)
    db_session.commit()
    all_reminds = db_session.query(Remind).all()
    remind = db_session.query(Remind).filter(
        Remind.text == remind_text and Remind.userid == ctx.message.author.id).first()
    repeats_count[remind.id] = rep
    logger.info(f"New custom remind {remind.id}")
    load_remind("custom", remind.id, total_seconds, remind.userid, remind_text, ctx, None)
    await ctx.send(
        f"New custom remind for <@{remind.userid}>: {remind_text}, every {days} days, {hours} hours, {minutes} minutes and {seconds} seconds. (id = {remind.id})")


@bot.command(name="delete")
async def delete_rem(ctx, remind_id):
    try:
        job = id_to_job[int(remind_id)]
        remind = db_session.query(Remind).filter(Remind.id == remind_id).first()
        if ctx.message.author.id == remind.userid:
            schedule.cancel_job(job)
            db_session.query(Remind).filter(Remind.id == remind_id).delete()
            db_session.commit()
            await ctx.send("Remind successfully deleted")
            logger.info(f"Remind {remind_id} deleted")
        else:
            await ctx.send("Error: you are not a creator of this remind!")
            logger.info(f"Remind {remind_id} was not deleted")
    except KeyError:
        await ctx.send("Error: Invalid id!")
        logger.info(f"No remind with id {remind_id} found")


@bot.command(name="my_reminds")
async def list_reminds(ctx):
    reminds = db_session.query(Remind).filter(Remind.userid == ctx.message.author.id).all()
    if len(reminds) == 0:
        await ctx.send(f"You have no reminds.")
    for remind in reminds:
        if remind.r_type == "weekly":
            await ctx.send(f"{remind.text} every {remind.day} at {remind.time}. ID = {remind.id}")
        elif remind.r_type == "daily":
            await ctx.send(f"{remind.text} everyday at {remind.time}. ID = {remind.id}")
        elif remind.r_type == "custom":
            string_time = time.strftime('%dd, %H:%M:%S', time.gmtime(int(remind.time)))
            await ctx.send(
                f"{remind.text} every {str(int(string_time[:2:]) - 1) + string_time[2::]}. ID = {remind.id}")


@bot.command(name="bot_help")
async def help_command(ctx):
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
