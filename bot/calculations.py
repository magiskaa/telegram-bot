import math
import time
from telegram import Update
from telegram.ext import ContextTypes
from bot.save_and_load import save_profiles, user_profiles

# Calculate the number of servings in a drink
def calculate_alcohol(vol, perc):
    pure_alcohol = vol * (perc / 100) * 789
    servings = pure_alcohol / 12
    return round(servings, 2)

# Calculate the users BAC
async def calculate_bac(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, noSaving=False):
    profile = user_profiles[user_id]

    profile["elapsed_time"] = time.time() - profile["start_time"]
    drinking_time = profile["elapsed_time"] / 3600
    
    weight = profile["weight"]
    gender = profile["gender"]
    age = profile["age"]
    height = profile["height"]

    if gender == "mies":
        TBW = 2.447 - 0.09516 * age + 0.1074 * height + 0.3362 * weight
    else:
        TBW = -2.097 + 0.1069 * height + 0.2466 * weight

    r = TBW / weight

    absorbed_grams = await calculate_absorption(update, context, user_id)
    
    if drinking_time < 0.6:
        elimination_factor = drinking_time / 0.6
        elimination_time = drinking_time * elimination_factor
    else:
        elimination_time = drinking_time

    bac = absorbed_grams / (weight*1000 * r) * 100

    if gender == "mies":
        grams = 0.11 if weight < 70 else 0.10
    else:
        grams = 0.13 if weight < 60 else 0.12 
    
    grams_per_kg = grams * weight
    bac_elim = grams_per_kg / (weight*1000 * r) * 100

    bac -= bac_elim * elimination_time
    bac = max(0, bac)

    if noSaving:
        profile["BAC"] = bac
        context.user_data["max_BAC"] = profile["drink_count"] * 12 / (weight*1000 * r) * 100
        return bac_elim
    else:
        profile["BAC"] = bac * 10
        save_profiles()

# Calculate the total amount of alcohol absorbed
async def calculate_absorption(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    profile = user_profiles[user_id]
    current_time = time.time()
    weight = profile["weight"]
    gender_factor = 1.0 if profile["gender"] == "mies" else 1.15

    total_absorbed = 0

    for drink in profile["drink_history"]:
        drink_elapsed_time = (current_time - drink["timestamp"]) / 3600

        if drink_elapsed_time < 0:
            continue
        
        k = 3 * (64/weight)**0.25 * gender_factor

        c = drink["percentage"]
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

        k *= concentration_factor

        drink_grams = drink["servings"] * 12
        absorbed_grams = drink_grams * (1 - math.e**(-k * drink_elapsed_time**1.1))

        if drink_elapsed_time > 2:
            absorbed_grams = drink_grams
        
        total_absorbed += absorbed_grams

    return total_absorbed
