import numpy as np
from telegram import Update
from telegram.ext import ContextTypes
from bot.save_and_load import save_profiles, user_profiles
from bot.utils import get_timezone, get_TBW, get_elim_rate, get_BAC, get_elim_time, get_absorption

# Calculate the number of servings in a drink
def calculate_alcohol(vol, perc):
    pure_alcohol = vol * (perc / 100) * 789
    servings = pure_alcohol / 12
    return round(servings, 2)

# Calculate the users BAC
async def calculate_bac(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, noSaving=False):
    profile = user_profiles[user_id]

    if profile["second_start"] != 0:
        start_time = profile["second_start"]
    else:
        start_time = profile["start_time"]

    profile["elapsed_time"] = get_timezone() - start_time
    drinking_time = profile["elapsed_time"] / 3600
    
    weight = profile["weight"]

    r = get_TBW(user_id)

    absorbed_grams = await calculate_absorption(update, context, user_id)
    
    elimination_time = get_elim_time(drinking_time)

    bac = get_BAC(user_id, absorbed_grams, r)

    grams = get_elim_rate(user_id)
    
    grams_per_kg = grams * weight
    bac_elim = get_BAC(user_id, grams_per_kg, r)

    bac -= bac_elim * elimination_time
    bac = max(0, bac)

    if noSaving:
        profile["BAC"] = bac
        context.user_data["max_BAC"] = profile["drink_count"] * get_BAC(user_id, 12, r)
        return bac_elim
    else:
        profile["BAC"] = bac * 10
        save_profiles()

# Calculate the total amount of alcohol absorbed
async def calculate_absorption(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    profile = user_profiles[user_id]
    current_time = get_timezone()

    total_absorbed = 0

    for drink in profile["drink_history"]:
        drink_elapsed_time = (current_time - drink["timestamp"]) / 3600

        if drink_elapsed_time < 0:
            print(f"Drink elapsed time is negative, skipping {profile['name']}'s drink. ({drink['size']}l {drink['percentage']}%)")
            continue
        elif profile["second_start"] != 0 and drink["timestamp"] < profile["second_start"]:
            continue

        absorbed_grams = get_absorption(user_id, drink, drink_elapsed_time)
        total_absorbed += absorbed_grams

    return total_absorbed

# Recalculate the highest BAC after a drink is deleted
def recalculate_highest_bac(user_id, drink):
    profile = user_profiles[user_id]

    current_time = get_timezone()
    if profile["second_start"] != 0:
        profile["elapsed_time"] = current_time - profile["second_start"]
    else:
        profile["elapsed_time"] = current_time - profile["start_time"]

    r = get_TBW(user_id)

    drink_elapsed_time = (current_time - drink["timestamp"]) / 3600
    
    absorbed_grams = get_absorption(user_id, drink, drink_elapsed_time)    

    drink_bac = get_BAC(user_id, absorbed_grams, r)

    profile["highest_BAC"] -= drink_bac * 10

# Calculate the peak BAC that the user will reach
def calculate_peak_bac(user_id):
    profile = user_profiles[user_id]
    weight = profile["weight"]

    r = get_TBW(user_id)

    grams = get_elim_rate(user_id)

    drinks = profile["drink_history"]
    if not drinks:
        return 0

    start_time = min(drink["timestamp"] for drink in drinks)
    end_time = max(drink["timestamp"] for drink in drinks) + 2 * 3600

    times = np.arange(start_time, end_time, 150)
    bac_values = []

    for t in times:
        total_absorbed = 0
        for drink in drinks:
            drink_elapsed_time = (t - drink["timestamp"]) / 3600
            if drink_elapsed_time < 0:
                continue

            absorbed = get_absorption(user_id, drink, drink_elapsed_time)
            total_absorbed += absorbed

        hours_since_start = (t - start_time) / 3600

        elimination_time = get_elim_time(hours_since_start)

        bac = get_BAC(user_id, total_absorbed, r)

        grams_per_kg = grams * weight
        bac_elim = get_BAC(user_id, grams_per_kg, r)

        bac -= bac_elim * elimination_time
        bac = max(0, bac)

        bac_values.append(bac * 10)

    peak_bac = max(bac_values)
    return peak_bac
