import discord
import os
from discord.ext import commands
import asyncio
import datetime
import openai

# Set your API key
openai.api_key = os.environ.get("GPT_KEY")

intents = discord.Intents.default()
intents.message_content = True

# Replace "!" with the desired prefix for your bot commands.
bot = commands.Bot(command_prefix="!", intents=intents,
                   heartbeat_timeout=10000)

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

messages = []

initial_message = ("You are a personal fitness trainer now. I'm an asian male, 32 years ago, "
                   "with 5'7\" height and 160 lbs weight. I want to have a 7 day workout plan, using the time in the morning "
                   "(9-10AM) and evening (7PM-10PM) for exercises and activities. The workout should be not be too heavy. "
                   "I will start the plan tomorrow (04/06/2023). Can you help me make a plan? The plan should be detailed, with the date and time of each activities. ")
loop_message = ("Now, I will start following your plan and would like you to remind on what to do at current time. A scheduler will help provide current time info to you. He will always start his words with \"SCHEDULER: \", followed by a date and time, by roughly once per every hour.  If I should be doing an activity at that time, you should answer with: \"Exercise Time!\", followed by the activity. Otherwise, reply with \"Nothing to do now\". If you understand, please say OK.")


def send_message_to_chatgpt(message: str):
    """
    send message to OpenAI chat API, get response from OpenAI chat API, and send response to user.
    """
    global messages
    messages.append({"content": message, "role": "user"})
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages,
        max_tokens=2048,  # Adjust the number of tokens as needed
        temperature=0.8,  # Adjust the creativity level
    )

    gpt_response = response.choices[0].message.content
    messages.append({"content": gpt_response, "role": "system"})
    return gpt_response


def split_long_string(text, max_length=2000):
    """Split a long string into a list of strings with a maximum length."""
    words = text.split()
    result = []
    current_line = ""

    for word in words:
        if len(current_line + " " + word) <= max_length:
            current_line += " " + word
        else:
            result.append(current_line.strip())
            current_line = word

    if current_line:
        result.append(current_line.strip())

    return result


async def send_daily_message(user_id):
    loop = asyncio.get_event_loop()

    user = await bot.fetch_user(user_id)
    if user is not None:
        await user.send(f"Your initial instruction to ChatGPT: {initial_message}")
        gpt_response = await loop.run_in_executor(None, send_message_to_chatgpt, initial_message)
        if (len(gpt_response) > 2000):
            for line in split_long_string(gpt_response):
                await user.send(line)
        else:
            await user.send(gpt_response)
        _ = await loop.run_in_executor(None, send_message_to_chatgpt, loop_message)

        while True:
            now = datetime.datetime.now()
            seconds_till_next_hour = 3600 - now.minute * \
                60 - now.second - now.microsecond / 1_000_000
            await asyncio.sleep(seconds_till_next_hour)

            time = datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")
            gpt_response = await loop.run_in_executor(None, send_message_to_chatgpt, f"SCHEDULER: {time}")
            if "nothing to do now" in gpt_response.lower():
                continue
            await user.send(gpt_response)


@bot.event
async def on_ready():
    print(f"{bot.user.name} has connected to Discord!")
    # Replace 'user_id' with the user's ID you want to send a message to
    user_id = '740804964913250344'
    # await send_message_to_user(user_id)
    asyncio.create_task(send_daily_message(user_id))


@bot.command(name="hello", help="Says hello to the user.")
async def hello(ctx):
    await ctx.send(f"Hello, {ctx.author.mention}!")


@bot.command(name="echo", help="Repeats the message back to the user.")
async def echo(ctx, *, message: str):
    await ctx.send(message)


@bot.command(name="g", help="Say something to chatgpt.")
async def g(ctx, *, message: str):
    loop = asyncio.get_event_loop()
    gpt_response = await loop.run_in_executor(None, send_message_to_chatgpt, message)
    await ctx.send(gpt_response)


bot.run(TOKEN)
