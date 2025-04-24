# Telegram BAC Bot

This telegram bot calculates the user's BAC using gender, age, height and weight.

## Table of Contents

- [Installation](#installation)
- [Features](#features)
- [Configuration](#configuration)
- [LICENSE](#LICENSE)
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

5. Add your OpenAI and telegram bot API keys to `config/config.py`

## Features

- Calculates users BAC using their gender, age, height and weight
- Users can input drinks and setup a favorite drink
- Users can check their own drinking stats or the group's stats
- Top 3 list for highest BACs
- The bot sends messages when someones BAC goes over certain limits
- The bot sends a recap message at 12 o'clock of the previous night
- An AI chatbot with which users can have conversations with
- Admin commands such as: reset_top3, announcement and saved_announcement

## Configuration

Edit `config/config.py` to set your:
- API keys
- Group ID
- Admin IDs
- Announcement text
- Gifs list
- Top 3 gifs list

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

Valtteri Antikainen, vantikaine@gmail.com