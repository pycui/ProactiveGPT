import discord
import os
import openai
import questionary
from questionary import ValidationError
from gpt_gpt import GptBot

intents = discord.Intents.default()
intents.message_content = True

default_task_prompt = ("You are a personal fitness trainer now. I want to have a 7 day workout "
                       "plan, using the time in the morning (9-10AM) and evening (7PM-10PM) for "
                       "exercises and activities. The workout should be not be too heavy. "
                       "I will start the plan tomorrow (04/06/2023). Can you help me make a plan? "
                       "The plan should be detailed, with the date and time of each activities. ")
loop_prompt_template = (
    "Now, I will start following your plan and would like you to remind on what to do at current time. "
    "A scheduler will help provide current time info to you. He will always start his words with "
    "\"SCHEDULER: \", followed by a date and time, by roughly once per every {cadence} hour. "
    "If I should be doing an activity at that time, you should answer with: \"Exercise Time!\", "
    "followed by the activity. Otherwise, reply with \"Nothing to do now\". If you understand, "
    "please say OK.")


def cadence_validator(value: str):
    try:
        value_int = int(value)
    except ValueError:
        raise ValidationError(message="Please enter a valid integer.")

    if value_int <= 0:
        raise ValidationError(message="Please enter a positive integer.")

    return True


def main():
    # Select model.
    choices = [
        "gpt-4",
        "gpt-3.5-turbo",
    ]

    model = questionary.select(
        "Please choose your GPT model:", choices=choices).ask()

    if model:
        print(f"You selected: {model}")
    else:
        print("No model was selected. Exiting.")
        return

    # Enter API key.
    api_token = questionary.text("Please enter your OpenAI API token. \n"
                                 "If empty, I will use the OPENAI_API_KEY "
                                 "environment variable:").ask()

    if api_token:
        print("Using user-provided API key.")
        openai.api_key = api_token
    else:
        print("Using environment variable OPENAI_API_KEY.")
        openai.api_key = os.environ.get("GPT_KEY")

    # Enter discord bot token.
    discord_token = questionary.text("Please enter your Discord bot token. \n"
                                     "If empty, I will use the DISCORD_BOT_TOKEN "
                                     "environment variable:").ask()
    if discord_token:
        print("Using user-provided Discord bot token.")
    else:
        print("Using environment variable DISCORD_BOT_TOKEN.")
        discord_token = os.environ.get("DISCORD_BOT_TOKEN")

    # Enter cadence.
    cadence = questionary.text("Please enter the cadence of your GPT's proactiveness\n"
                               "(in hours, cron format will be supported soon):",
                               validate=cadence_validator, default="1").ask()

    # Enter task prompt.
    task_prompt = questionary.text("Please enter your task prompt to GPT:",
                                   default=default_task_prompt).ask()
    loop_prompt = loop_prompt_template.format(cadence=cadence)

    # Enter loop prompt.
    loop_prompt = questionary.text("Please enter your loop prompt to GPT:",
                                   default=loop_prompt).ask()

    # Enter user ID.
    user_id = questionary.text(
        "Please enter the discord user ID to send the message to:").ask()

    # Replace "!" with the desired prefix for your bot commands.
    bot = GptBot(model, task_prompt, loop_prompt, cadence, user_id,
                 command_prefix="!", intents=intents, heartbeat_timeout=10000)

    bot.run(discord_token)


if __name__ == "__main__":
    main()
