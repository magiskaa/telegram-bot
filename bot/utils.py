import math
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
        elif name.endswith("an"):
            return name + "ille"
        else:
            return name + "lle"
    elif ending == "lla":
        if name.endswith("kko"):
            return name[:-2] + "olla"
        elif name.endswith("tti"):
            return name[:-2] + "illa"
        elif name.endswith("ti") or name.endswith("ni"):
            return name + "llä"
        elif name.endswith("an"):
            return name + "illa"
        else:
            return name + "lla"
    elif ending == "lta":
        if name.endswith("kko"):
            return name[:-2] + "olta"
        elif name.endswith("tti"):
            return name[:-2] + "ilta"
        elif name.endswith("ti") or name.endswith("ni"):
            return name + "ltä"
        elif name.endswith("an"):
            return name + "ilta"
        else:
            return name + "lta"
    elif ending == "n":
        if name.endswith("kko"):
            return name[:-2] + "on"
        elif name.endswith("tti"):
            return name[:-2] + "in"
        elif name.endswith("an"):
            return name + "in"
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

def get_TBW(user_id):
    profile = user_profiles[user_id]
    weight = profile["weight"]
    gender = profile["gender"]
    age = profile["age"]
    height = profile["height"]

    if gender == "mies":
        TBW = 2.447 - 0.09516 * age + 0.1074 * height + 0.3362 * weight
    else:
        TBW = -2.097 + 0.1069 * height + 0.2466 * weight

    return TBW / weight

def get_elim_rate(user_id):
    profile = user_profiles[user_id]
    weight = profile["weight"]
    gender = profile["gender"]

    if gender == "mies":
        min_w, max_w = 60, 100
        min_g, max_g = 0.12, 0.1
        if weight <= min_w:
            grams = min_g
        elif weight >= max_w:
            grams = max_g
        else:
            grams = min_g + (max_g - min_g) * ((weight - min_w) / (max_w - min_w))
    else:
        min_w, max_w = 50, 90
        min_g, max_g = 0.15, 0.125
        if weight <= min_w:
            grams = min_g
        elif weight >= max_w:
            grams = max_g
        else:
            grams = min_g + (max_g - min_g) * ((weight - min_w) / (max_w - min_w))

    return grams

def get_concentration_factor(c):
    if c <= 4:
        concentration_factor = 0.9
    elif 4 < c < 20:
        concentration_factor = 0.9 + (c - 4) * (1.2 - 0.9) / (20 - 4)
    elif 20 <= c <= 30:
        concentration_factor = 1.2
    elif 30 < c <= 60:
        concentration_factor = 1.2 - (c - 30) * (1.2 - 0.9) / (60 - 30)
    else:
        concentration_factor = 0.9

    return concentration_factor

def get_BAC(user_id, grams, r):
    profile = user_profiles[user_id]
    weight = profile["weight"]

    return grams / (weight*1000 * r) * 100

def get_absorbed_grams(user_id, bac, r):
    profile = user_profiles[user_id]
    weight = profile["weight"]

    return bac * weight * r

def get_elim_time(hours_since_start):
    if hours_since_start < 0.6:
        elimination_factor = hours_since_start / 0.6
        elimination_time = hours_since_start * elimination_factor
    else:
        elimination_time = hours_since_start

    return elimination_time

def get_absorption(user_id, drink, drink_elapsed_time):
    profile = user_profiles[user_id]
    weight = profile["weight"]
    gender = profile["gender"]

    gender_factor = 1.0 if gender == "mies" else 1.1

    k = 3.1 * (64/weight)**0.25 * gender_factor

    c = drink["percentage"]
    concentration_factor = get_concentration_factor(c)
    k *= concentration_factor

    drink_grams = drink["servings"] * 12
    if drink_elapsed_time > 2:
        absorbed = drink_grams
    else:
        absorbed = drink_grams * (1 - math.e**(-k * drink_elapsed_time**1.1))

    return absorbed
