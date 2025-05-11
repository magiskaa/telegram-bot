from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.ext import ContextTypes
from bot.save_and_load import user_profiles
from config.config import ADMIN_ID

def name_conjugation(name, ending):
    name = name.strip()
    if name == "Matleena":
        name = "Matti"
    if ending == "lle":
        if name.endswith("kko"):
            return name[:-2] + "olle"
        elif name.endswith("tti"):
            return name[:-2] + "ille"
        else:
            return name + "lle"
    elif ending == "lla":
        if name.endswith("kko"):
            return name[:-2] + "olla"
        elif name.endswith("tti"):
            return name[:-2] + "illa"
        elif name.endswith("ti") or name.endswith("ni"):
            return name + "llä"
        else:
            return name + "lla"
    elif ending == "lta":
        if name.endswith("kko"):
            return name[:-2] + "olta"
        elif name.endswith("tti"):
            return name[:-2] + "ilta"
        elif name.endswith("ti") or name.endswith("ni"):
            return name + "ltä"
        else:
            return name + "lta"
    elif ending == "n":
        if name.endswith("kko"):
            return name[:-2] + "on"
        elif name.endswith("tti"):
            return name[:-2] + "in"
        else:
            return name + "n"
    else:
        return name + ending

def get_group_id():
    with open("data/group_id.txt", "r") as f:
        group_id = int(f.read().strip())
    return group_id

async def validate_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in user_profiles:
        await update.message.reply_text("Et ole vielä määrittänyt profiiliasi. Käytä /setup komentoa ensin.")
        return True
    else:
        return False

async def validate_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("Sinulla ei ole oikeuksia tähän komentoon.")
        return True
    else:
        return False

def get_timezone():
    return datetime.now(ZoneInfo("Europe/Helsinki")).timestamp()

def time_adjustment(size):
    if size <= 0.06:
        time_adjustment = 1 * 60
    elif size < 0.12:
        time_adjustment = 5 * 60
    elif size <= 0.33:
        time_adjustment = 10 * 60
    elif size <= 0.5:
        time_adjustment = 15 * 60
    else:
        time_adjustment = 20 * 60
    return time_adjustment
