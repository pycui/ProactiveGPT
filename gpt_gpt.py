import asyncio
import datetime
import openai
from typing import List
from discord.ext import commands


# Discord max message length.
MAX_MESSAGE_LENGTH = 2000


def split_long_string(text, max_length=MAX_MESSAGE_LENGTH):
    """
    Split a long string into a list of strings with a maximum length.
    Useful for sending message to discord which has character limit."""
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


def send_message_to_chatgpt(messages: List[str], message: str, model: str):
    """
    Send message to OpenAI chat API, get response, and send response to user.
    """
    messages.append({"content": message, "role": "user"})
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        max_tokens=2048,  # Adjust the number of tokens as needed
        temperature=0.8,  # Adjust the creativity level
    )

    gpt_response = response.choices[0].message.content
    messages.append({"content": gpt_response, "role": "system"})
    return gpt_response


class GptBot(commands.Bot):
    """
    A discord bot that can interact with GPT.
    """
    def __init__(self, model, task_prompt, loop_prompt, cadence, user_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model
        self.task_prompt = task_prompt
        self.loop_prompt = loop_prompt
        self.cadence = cadence
        self.user_id = user_id
        self.messages = []
        self._commands()

    async def send_periodic_message(self):
        loop = asyncio.get_event_loop()

        user = await self.fetch_user(self.user_id)
        if user is not None:
            await user.send(f"Your initial instruction to ChatGPT: {self.task_prompt}")
            await user.send(f"ChatGPT is now generating the plan for you...")
            gpt_response = await loop.run_in_executor(
                None, send_message_to_chatgpt, self.messages, self.task_prompt, self.model)
            if (len(gpt_response) > MAX_MESSAGE_LENGTH):
                for line in split_long_string(gpt_response):
                    await user.send(line)
            else:
                await user.send(gpt_response)
            _ = await loop.run_in_executor(
                None, send_message_to_chatgpt, self.messages, self.loop_prompt, self.model)

            while True:
                now = datetime.datetime.now()
                seconds_till_next_hour = 3600 - now.minute * \
                    60 - now.second - now.microsecond / 1_000_000
                # Add more hours to make up cadence hours.
                more_hours = (now.hour + 1) % int(self.cadence)
                seconds_till_next_run = seconds_till_next_hour + more_hours * 3600
                await asyncio.sleep(seconds_till_next_run)

                time = datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")
                gpt_response = await loop.run_in_executor(
                    None, send_message_to_chatgpt, self.messages, f"SCHEDULER: {time}", self.model)
                if "nothing to do now" in gpt_response.lower():
                    continue
                await user.send(gpt_response)

    async def on_ready(self):
        print(f"Using task_prompt: {self.task_prompt}")
        print(f"Using loop_prompt: {self.loop_prompt}")
        print(f"{self.user.name} has connected to Discord!")
        asyncio.create_task(self.send_periodic_message())

    def _commands(self):
        @self.command(name="hello", help="Says hello to the user.")
        async def hello(ctx):
            await ctx.send(f"Hello, {ctx.author.mention}!")

        @self.command(name="echo", help="Repeats the message back to the user.")
        async def echo(ctx, *, message: str):
            await ctx.send(message)

        @self.command(name="g", help="Say something to chatgpt.")
        async def g(ctx, *, message: str):
            loop = asyncio.get_event_loop()
            gpt_response = await loop.run_in_executor(
                None, send_message_to_chatgpt, ctx.bot.messages, message, ctx.bot.model)
            await ctx.send(gpt_response)
