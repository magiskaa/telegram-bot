import random
import math
import time
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from bot.save_and_load import save_profiles, user_profiles
from config.config import TOP_3_GIFS
from bot.calculations import calculate_bac
from bot.utils import name_conjugation, get_timezone


# Own stats command
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    profile = user_profiles[user_id]
    if user_id not in user_profiles:
        await update.message.reply_text("Profiilia ei löydy. Käytä /setup komentoa ensin.")
        return
    if profile["start_time"] == 0:
        await update.message.reply_text("Et ole vielä aloittanut juomista.")
        return
    
    bac_elim = await calculate_bac(update, context, user_id, noSaving=True)

    bac = profile["BAC"] * 10
    if bac > profile["highest_BAC"]:
        profile["highest_BAC"] = bac
        
    drinking_time = profile["elapsed_time"] / 3600
    drinks = profile["drink_count"]
    
    if bac > 0:
        context.user_data["max_BAC"] -= bac_elim * drinking_time
        hours_until_sober = context.user_data["max_BAC"] / bac_elim
        sober_timestamp = get_timezone() + (hours_until_sober * 3600)
        sober_time_str = time.strftime("%H:%M", time.gmtime(sober_timestamp))
        sober_text = f"Selvinpäin olet noin klo {sober_time_str}."
    else:
        sober_text = "Olet jo selvinpäin."

    drinking_time_h = math.floor(drinking_time)
    drinking_time_m = int(drinking_time % 1 * 60)
    stats_text = (
        f"{name_conjugation(profile['name'], 'n')} statsit\n"
        f"==========================\n"
        f"Alkoholin määrä: {drinks:.2f} annosta.\n"
        f"Aloitus: {time.strftime('%H:%M:%S', time.gmtime(profile['start_time']))}.\n"
        f"Olet juonut {drinking_time_h}h {drinking_time_m}min.\n"
        f"Arvioitu BAC: {bac:.3f}‰.\n"
        f"Korkein BAC: {profile['highest_BAC']:.3f}‰.\n"
        f"{sober_text}"
    )
    
    save_profiles()

    await update.message.reply_text(stats_text)

# Own stats reset command
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in user_profiles:
        await update.message.reply_text("Et ole vielä määrittänyt profiiliasi. Käytä /setup komentoa ensin.")
        return

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

    await update.message.reply_text("Tilastot nollattu.")

# Personal best command
async def personal_best(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    profile = user_profiles[user_id]
    if user_id not in user_profiles:
        await update.message.reply_text("Profiilia ei löydy. Käytä /setup komentoa ensin.")
        return

    if profile["PB_BAC"] == 0:
        await update.message.reply_text("Ei henkilökohtaista ennätystä.")
        return
    else:
        pb_text = (
            f"{name_conjugation(profile['name'], 'n')} henkilökohtainen ennätys\n"
            f"=============================\n"
            f"BAC: {profile['PB_BAC']:.2f}‰ ({profile['PB_dc']:.2f} annosta)\n"
            f"Päivä: {profile['PB_day']}"
        )
        await update.message.reply_text(pb_text)

# Group stats command
async def group_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    drinkers = []
    for user in user_profiles:
        if user == "top_3":
            continue
        profile = user_profiles[user]
        if profile["drink_count"] == 0:
            continue
        else:
            await calculate_bac(update, context, user)
            drinkers.append(profile)

    leaderboard = ""
    sorted_drinkers = sorted(drinkers, key=lambda x: x["BAC"], reverse=True)
    for i, profile in enumerate(sorted_drinkers, 1):
        leaderboard += f"{i}. {profile['name']} {profile['BAC']:.2f}‰ ({profile['drink_count']:.2f} annosta)\n"

    if len(drinkers) != 0:
        await context.bot.send_animation(
            chat_id=update.effective_chat.id,
            animation=random.choice(TOP_3_GIFS),
            caption=
            "Ryhmän tilastot\n"
            "==========================\n"
            f"Juojia: {len(drinkers)}\n"
            f"Alkoholia juotu: {sum([profile['drink_count'] for profile in drinkers]):.2f} annosta.\n"
            "\nLeaderboard tällä hetkellä:\n"
            f"{leaderboard}"
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Ei juojia tällä hetkellä."
        )

# Top 3 command
async def top_3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    first = user_profiles["top_3"]["1"]
    second = user_profiles["top_3"]["2"]
    third = user_profiles["top_3"]["3"]

    text = (
        "Top 3 kännit\n"
        "=============================\n"
        f"1. {first['name'].capitalize()} {first['BAC']:.2f}‰ ({first['drinks']:.2f} annosta) {first['day']}\n"
        f"2. {second['name'].capitalize()} {second['BAC']:.2f}‰ ({second['drinks']:.2f} annosta) {second['day']}\n"
        f"3. {third['name'].capitalize()} {third['BAC']:.2f}‰ ({third['drinks']:.2f} annosta) {third['day']}\n"
    )

    await context.bot.send_animation(
        chat_id=update.effective_chat.id,
        animation=random.choice(TOP_3_GIFS),
        caption=text
    )
