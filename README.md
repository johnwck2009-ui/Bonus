# BonusSpecialistaBot

An all-in-one mathematical and calculation utility that works directly in Telegram chat.

## Features

- Basic arithmetic calculator with safe expression parsing
- Percentage calculator
- Discount calculator
- Commission calculator
- Bonus/additional earnings calculator
- Salary total calculator
- Unit conversions: distance, weight, temperature, and volume
- Telegram inline keyboard navigation

## Requirements

- Python 3.10+
- A Telegram bot token from [@BotFather](https://t.me/BotFather)

## Run locally

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Set your bot token as an environment variable:

   Linux/macOS:
   ```bash
   export BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
   ```

   Windows PowerShell:
   ```powershell
   $env:BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
   ```

3. Start the bot:

   ```bash
   python main.py
   ```

## Deploy on Render

Create a **Background Worker** connected to this repository.

- Build command: `pip install -r requirements.txt`
- Start command: `python main.py`
- Environment variable: `BOT_TOKEN` = your token from BotFather

Keep the token in Render's environment settings. Never commit it to GitHub.

## Notes

- The bot uses Telegram's Bot API through python-telegram-bot.
- No external data APIs or web app are required.
- Calculations are performed locally by the bot.
- This project provides calculation tools and does not offer financial, investment, or gambling services.
