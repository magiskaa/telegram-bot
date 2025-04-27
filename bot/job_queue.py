import telegram
import time
import random
from telegram import Update
from telegram.ext import ContextTypes, CallbackContext
from bot.save_and_load import save_profiles, user_profiles
from config.config import GROUP_ID, ADMIN_ID, GIFS
from bot.calculations import calculate_bac
from bot.utils import name_conjugation

# Job queue functions
async def recap(context: CallbackContext):
    drinkers = []
    for user in user_profiles:
        if user != "top_3":
            profile = user_profiles[user]
            if profile["drink_count"] > 0:
                drinkers.append(profile)
    
    if len(drinkers) == 0:
        return
    
    first = user_profiles["top_3"]["1"]
    second = user_profiles["top_3"]["2"]
    third = user_profiles["top_3"]["3"]

    leaderboard = ""
    sorted_drinkers = sorted(drinkers, key=lambda x: x["highest_BAC"], reverse=True)
    for i, profile in enumerate(sorted_drinkers, 1):
        if profile["name"] == first["name"] and profile["highest_BAC"] == first["BAC"]:
            text = "Top 1!"
        elif profile["name"] == second["name"] and profile["highest_BAC"] == second["BAC"]:
            text = "Top 2!"
        elif profile["name"] == third["name"] and profile["highest_BAC"] == third["BAC"]:
            text = "Top 3!"
        else:
            text = ""
        leaderboard += f"{i}. {profile['name']} {profile['highest_BAC']:.2f}‰ ({profile['drink_count']:.2f} annosta) {text}\n"

    text = (
        "Eilisen juomatilastot:\n"
        "==========================\n"
        f"Juojia: {len(drinkers)}\n"
        f"Alkoholia juotu: {sum([profile['drink_count'] for profile in drinkers]):.2f} annosta.\n"
        "\nLeaderboard:\n"
        f"{leaderboard}"
    )
    try:
        await context.bot.send_message(chat_id=GROUP_ID, text=text)
    except telegram.error.TimedOut:
        await context.bot.send_message(chat_id=ADMIN_ID, text="Recap viestin lähetys epäonnistui aikakatkaisun vuoksi.")

async def reset_drink_stats(context: CallbackContext):
    for user_id in user_profiles:
        if user_id == "top_3":
            continue
        profile = user_profiles[user_id]
        profile["drink_count"] = 0
        profile["start_time"] = 0
        profile["elapsed_time"] = 0
        profile["BAC"] = 0
        profile["highest_BAC"] = 0
        profile["BAC_1_7"] = 0
        profile["BAC_2_0"] = 0
        profile["BAC_2_3"] = 0
        profile["BAC_2_7"] = 0
        profile["drink_history"] = []
    
    save_profiles()

async def bac_update(context: CallbackContext):
    for user_id in user_profiles:
        if user_id == "top_3" or user_profiles[user_id]["start_time"] == 0:
            continue
        else:
            profile = user_profiles[user_id]
            await calculate_bac(None, context, user_id)
            if profile["BAC"] > profile["highest_BAC"]:
                profile["highest_BAC"] = profile["BAC"]
            if profile["BAC"] > profile["PB_BAC"]:
                profile["PB_BAC"] = profile["BAC"]
                profile["PB_dc"] = profile["drink_count"]
                profile["PB_day"] = time.strftime("%d.%m.%Y")
            await top_3_update(None, context, user_id)
            if profile["BAC"] > 1.7:
                await message(None, context, user_id)

# Top 3 update and message functions for bac_update
async def top_3_update(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    profile = user_profiles[user_id]

    bac = profile["BAC"]
    name = profile["name"].capitalize()
    drinks = profile["drink_count"]
    day = time.strftime("%d.%m.%Y")
    
    top_3_candidates = []
    for pos in ["1", "2", "3"]:
        current_user = user_profiles["top_3"][pos]
        if current_user["name"] == name and current_user["BAC"] > bac:
            return
        elif current_user["name"] != "ei kukaan" and current_user["name"] != name:
            top_3_candidates.append(current_user)

    top_3_candidates.append({
        "name": name,
        "BAC": bac,
        "drinks": drinks,
        "day": day,
    })

    top_3_candidates.sort(key=lambda x: x["BAC"], reverse=True)

    for i, pos in enumerate(["1", "2", "3"]):
        if i < len(top_3_candidates):
            user_profiles["top_3"][pos] = top_3_candidates[i]
        else:
            user_profiles["top_3"][pos] = {
                "name": "ei kukaan",
                "BAC": 0,
                "drinks": 0,
                "day": "ei milloinkaan",
            }
    save_profiles()

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    profile = user_profiles[user_id]

    name = profile["name"].capitalize()
    bac = profile["BAC"]

    MESSAGES_1_7 = [
        f"{name_conjugation(name, 'lla')} menee nyt lujaa.",
        f"{name} ottaa nyt väliveden.",
    ]

    MESSAGES_2_0 = [
        f"{name_conjugation(name, 'lle')} tulee kohta hissiefekti, ottakaa bileämpäri hollille.",
        f"Onkohan tuo {name} kiskonu jo ihan tarpeeks?",
        f"{name} selvästi tähtää top 3 känneihin.",
        f"{name_conjugation(name, 'lla')} on ollu jano.",
        f"{name_conjugation(name, 'lla')} on selkeästi nestetasapaino kohillaan.",
        f"Onkohan {name_conjugation(name, 'lla')} vielä huomen sama mp tästä juomatahdista?",
        f"{name_conjugation(name, 'lla')} on huomenna rapsakat tunnelmat.",
        f"{name} ottaa nyt väliveden.",
    ]

    MESSAGES_2_3 = [
        f"{name_conjugation(name, 'lta')} pullo pois!",
        f"{name_conjugation(name, 'lle')} ei enää tarjoilla.",
        f"{name_conjugation(name, 'lle')} tulee kohta väsyväsy.",
        f"{name_conjugation(name, 'lle')} tulee morkkis.",
        f"{name} ei välttämättä muista koko iltaa, mutta me muistetaan.",
        f"{name} ei kohta enää muista omaa nimee.",
        f"{name_conjugation(name, 'lle')} nyt bileämpäri kätösiin!",
        f"{name} ottaa nyt väliveden.",
    ]

    MESSAGES_2_7 = [
        f"{name} kuolee.",
    ]

    if bac >= 1.7 and bac < 2.0 and profile["BAC_1_7"] == 0:
        profile["BAC_1_7"] = 1
        MESSAGES = MESSAGES_1_7
    elif bac >= 2.0 and bac < 2.3 and profile["BAC_2_0"] == 0:
        profile["BAC_2_0"] = 1
        MESSAGES = MESSAGES_2_0
    elif bac >= 2.3 and bac < 2.7 and profile["BAC_2_3"] == 0:
        profile["BAC_2_3"] = 1
        MESSAGES = MESSAGES_2_3
    elif bac >= 2.7 and profile["BAC_2_7"] == 0:
        profile["BAC_2_7"] = 1
        MESSAGES = MESSAGES_2_7
    else:
        return
    
    try:
        await context.bot.send_animation(
            chat_id=GROUP_ID, 
            animation=random.choice(GIFS),
            caption=random.choice(MESSAGES) + f" {profile['BAC']:.2f}‰")
    except telegram.error.TimedOut:
        await context.bot.send_message(chat_id=ADMIN_ID, text="Viestin lähetys epäonnistui aikakatkaisun vuoksi.")
