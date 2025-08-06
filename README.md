# Telegram BAC Bot

A comprehensive Telegram bot that calculates and tracks Blood Alcohol Content (BAC) for individuals and groups in real-time. The bot uses scientifically-based calculations considering user-specific factors like gender, age, height, and weight to provide accurate BAC estimates and personalized drinking statistics.

## Table of Contents

- [Installation](#installation)
- [Features](#features)
- [Available Commands](#available-commands)
- [Configuration](#configuration)
- [Scientific Accuracy](#scientific-accuracy)
- [Safety Notice](#safety-notice)
- [License](#license)
- [Contact](#contact)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/magiskaa/telegram-bot.git
cd telegram-bot
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Create a config file:
```bash
cp config/config.example.py config/config.py
```

5. Add your OpenAI and Telegram bot API keys to `config/config.py`

## Available Commands

### User Commands
- `/start` - Welcome message and basic information
- `/setup` - Configure your profile (gender, age, height, weight)
- `/profile` - View and edit your profile information
- `/drink` - Log a drink from the list or input a custom drink
- `/favorite` - Quickly log one of your preset favorite drinks
- `/favorite_setup` - Configure your favorite drinks
- `/add_last` - Repeat your most recent drink entry
- `/forgotten` - Add a drink you forgot to log earlier (with custom time)
- `/stats` - View your current statistics
- `/group_stats` - View group drinking statistics
- `/drinks` - See your complete drink history for the night
- `/pb` - View your personal best BAC record
- `/top3` - See the groups all-time Top 3 highest BACs
- `/delete` - Remove a specific drink entry
- `/reset` - Reset your current statistics
- `/friend` - Chat with the AI companion (say "heippa" to exit)
- `/help` - Display all available commands
- `/cancel` - Cancel any ongoing command interaction

### Admin Commands
- `/admin` - Display admin command list
- `/announcement` - Send announcements to the group
- `/saved_announcement` - Send a pre-configured announcement
- `/group_id` - Get the current group's chat ID
- `/get_stats` - View any user's statistics
- `/get_drinks` - View any user's drink history
- `/reset_top3` - Reset the Top 3 leaderboard
- `/group_pb` - Display the whole group's PBs in a leaderboard

## Features

### Drink Management
- **Custom Drinks**: Input any drink with volume (liters) and alcohol percentage
- **Forgotten Drinks**: Add drinks retroactively with custom timestamps
- **Drink History**: View complete chronological list of consumed drinks
- **Latest Drink**: Quickly repeat your most recent drink entry

### Statistics & Analytics
- **Real-time BAC**: Live blood alcohol content updates every 30 seconds
- **Personal Stats**: Current session statistics including drink count and peak BAC
- **Top 3 Leaderboard**: All-time highest BAC records of the group
- **Daily Recaps**: Automated morning summaries of previous night's statistics

### Other Features
- **AI Chatbot**: OpenAI-powered conversational companion
- **Safety Alerts**: Automatic warnings at BAC thresholds with entertaining messages
- **Error Logging**: Comprehensive error tracking and admin notifications

## Configuration

Edit `config/config.py` to set your:
- **BOT_TOKEN**: Your Telegram bot token from @BotFather
- **OPENAI_API**: Your OpenAI API key for the AI chatbot feature
- **GROUP_ID**: Target group chat ID for notifications and recaps
- **ADMIN_ID**: Your Telegram user ID for admin commands and error notifications
- **GIFS**: List of GIF URLs for BAC level notifications
- **TOP3_GIFS**: List of GIF URLs for Top 3 list
- **ANNOUNCEMENT_TEXT**: Pre-configured instructions for the AI

## Scientific Accuracy

- **BAC calculation**: BAC calculation is done using the Widmark formula
- **Gender-specific TBW**: Different Total Body Water percentages for men and women, which are calculated with the Watson formula
- **Absorption Rates**: Time and gender-based alcohol absorption
- **Elimination Rates**: Weight and gender-adjusted alcohol elimination
- **Real-time Updates**: Continuous recalculation every 30 seconds for accuracy

## Safety Notice

**This bot is for entertainment and educational purposes only.** 
- BAC calculations are estimates and may not reflect actual blood alcohol levels
- Individual metabolism varies significantly
- Never rely solely on this bot for decisions about driving or safety
- Always drink responsibly and know your limits
- Seek medical attention if experiencing alcohol poisoning symptoms

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

**Valtteri Antikainen**  
vantikaine@gmail.com