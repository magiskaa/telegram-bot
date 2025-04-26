import time
import random
import math
from bot.save_and_load import save_profiles, user_profiles
from config.config import GIFS, GROUP_ID, ADMIN_ID
from telegram import Update
import telegram
from telegram.ext import ContextTypes, ConversationHandler, CallbackContext

SIZE, PERCENTAGE = range(2)
FAVORITE = 1

async def drink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in user_profiles:
        await update.message.reply_text("Et ole vielä määrittänyt profiiliasi. Käytä /setup komentoa ensin.")
        return

    await update.message.reply_text("Minkä kokoinen juoma? Voit vähentää juoman asettamalla koon negatiiviseksi.")
    return SIZE

async def get_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        size = float(update.message.text)
        if size == 0:
            raise ValueError("Koko ei voi olla nolla.")
        context.user_data["size"] = size
        await update.message.reply_text("Kuinka monta prosenttia juomassa on alkoholia?")
        return PERCENTAGE
    except ValueError:
        await update.message.reply_text("Virheellinen syöte. Kirjoita juomasi tilavuus litroina. (esim. 0.33)")
        return SIZE

async def get_percentage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        percentage = float(update.message.text)
        if percentage <= 0 or percentage > 100:
            raise ValueError("Prosentti ei voi olla negatiivinen tai yli sata.")
        
        context.user_data["percentage"] = percentage
        
        user_id = str(update.message.from_user.id)
        profile = user_profiles[user_id]

        servings = calculate_alcohol(context.user_data["size"], context.user_data["percentage"])
        profile["drink_count"] += servings

        if context.user_data["size"] < 0:
            if profile["highest_BAC"] > 0.1:
                profile["highest_BAC"] -= 0.1
            else:
                profile["highest_BAC"] = 0.0 
            for drink in reversed(profile["drink_history"]):
                if drink["size"] == abs(context.user_data["size"]) and drink["percentage"] == context.user_data["percentage"]:
                    profile["drink_history"].remove(drink)
                    profile["BAC"] = await calculate_bac(update, context, user_id)
                    break

            await update.message.reply_text(
                f"Poistettu juoma: {abs(context.user_data['size'])}l {context.user_data['percentage']}% "
                f"({abs(servings)} annosta).\nBAC: {profile['BAC']:.3f}‰"
            )
            return ConversationHandler.END

        current_time = time.time()
        size = context.user_data["size"]
        if size <= 0.06:
            time_adjustment = 1 * 60
        elif size <= 0.33:
            time_adjustment = 10 * 60
        elif size <= 0.5:
            time_adjustment = 15 * 60
        else:
            time_adjustment = 20 * 60

        profile["drink_history"].append({
            "size": context.user_data["size"],
            "percentage": context.user_data["percentage"],
            "servings": servings,
            "timestamp": current_time - time_adjustment
        })
        save_profiles()

        if profile["start_time"] == 0:
            profile["start_time"] = current_time - time_adjustment

        await calculate_bac(update, context, user_id)
        
        await update.message.reply_text(f"Lisätty {servings} annosta.\nBAC: {profile['BAC']:.3f}‰")
        
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Virheellinen syöte. Kirjoita prosentti desimaalilukuna. (esim. 4.2)")
        return PERCENTAGE
    
async def favorite_drink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in user_profiles:
        await update.message.reply_text("Et ole vielä määrittänyt profiiliasi. Käytä /setup komentoa ensin.")
        return

    await update.message.reply_text("Anna lempijuomasi koko, prosentit ja nimi (esim. 0.33 4.2 kupari):")
    return FAVORITE

async def get_favorite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    favorite = update.message.text
    favorite_size, favorite_percentage, favorite_name = favorite.split()

    user_id = str(update.message.from_user.id)
    profile = user_profiles[user_id]

    profile["favorite_drink_size"] = favorite_size
    profile["favorite_drink_percentage"] = favorite_percentage
    profile["favorite_drink_name"] = favorite_name

    save_profiles()

    await update.message.reply_text(f"Lempijuomasi on nyt {favorite_name}.")
    return ConversationHandler.END

async def favorite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in user_profiles:
        await update.message.reply_text("Et ole vielä määrittänyt profiiliasi. Käytä /setup komentoa ensin.")
        return
    if user_profiles[user_id]["favorite_drink_size"] == "ei määritetty":
        await update.message.reply_text("Et ole vielä määrittänyt lempijuomaasi. Käytä /favorite_setup komentoa ensin.")
        return

    profile = user_profiles[user_id]
    size = float(profile["favorite_drink_size"])
    percentage = float(profile["favorite_drink_percentage"])
    servings = calculate_alcohol(size, percentage)
    profile["drink_count"] += servings

    current_time = time.time()
    if size <= 0.06:
        time_adjustment = 1 * 60
    elif size <= 0.33:
        time_adjustment = 10 * 60
    elif size <= 0.5:
        time_adjustment = 15 * 60
    else:
        time_adjustment = 20 * 60

    profile["drink_history"].append({
        "size": size,
        "percentage": percentage,
        "servings": servings,
        "timestamp": current_time - time_adjustment
    })
    save_profiles()

    if profile["start_time"] == 0:
        profile["start_time"] = current_time - time_adjustment

    await calculate_bac(update, context, user_id)

    await update.message.reply_text(
        f"{user_profiles[user_id]['favorite_drink_name'].capitalize()} +1 "
        f"({servings} annosta).\n BAC: {profile['BAC']:.3f}‰"
    )

async def delete_last_drink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in user_profiles:
        await update.message.reply_text("Et ole vielä määrittänyt profiiliasi. Käytä /setup komentoa ensin.")
        return

    profile = user_profiles[user_id]
    if len(profile["drink_history"]) == 0:
        await update.message.reply_text("Ei juomia poistettavaksi.")
        return

    profile["drink_count"] -= profile["drink_history"][-1]["servings"]

    profile["drink_history"].pop()

    if len(profile["drink_history"]) == 0:
        profile["drink_count"] = 0
        profile["start_time"] = 0
        profile["elapsed_time"] = 0
        profile["BAC"] = 0
        profile["highest_BAC"] = 0
    else:
        profile["BAC"] = await calculate_bac(update, context, user_id)

    await update.message.reply_text("Viimeisin juoma poistettu.")

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

async def top_3_update(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    profile = user_profiles[user_id]

    BAC = profile["BAC"]
    name = profile["name"].capitalize()
    drinks = profile["drink_count"]
    day = time.strftime("%d.%m.%Y")
    
    top_3_candidates = []
    for pos in ["1", "2", "3"]:
        current_user = user_profiles["top_3"][pos]
        if current_user["name"] == name and current_user["BAC"] > BAC:
            return
        elif current_user["name"] != "ei kukaan" and current_user["name"] != name:
            top_3_candidates.append(current_user)

    top_3_candidates.append({
        "name": name,
        "BAC": BAC,
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

async def recap(context: CallbackContext):
    drinkers = []
    for user in user_profiles:
        if user != "top_3":
            profile = user_profiles[user]
            if profile["drink_count"] > 0:
                drinkers.append(profile)
    
    if len(drinkers) == 0:
        return
    
    leaderboard = ""
    sorted_drinkers = sorted(drinkers, key=lambda x: x["highest_BAC"], reverse=True)
    for i, profile in enumerate(sorted_drinkers, 1):
        if profile["name"] == user_profiles["top_3"]["1"]["name"] and profile["highest_BAC"] == user_profiles["top_3"]["1"]["BAC"]:
            text = "Top 1!"
        elif profile["name"] == user_profiles["top_3"]["2"]["name"] and profile["highest_BAC"] == user_profiles["top_3"]["2"]["BAC"]:
            text = "Top 2!"
        elif profile["name"] == user_profiles["top_3"]["3"]["name"] and profile["highest_BAC"] == user_profiles["top_3"]["3"]["BAC"]:
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

def name_conjugation(name, ending):
    name = name.strip()
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

def calculate_alcohol(vol, perc):
    pure_alcohol = vol * (perc / 100) * 789
    servings = pure_alcohol / 12
    return round(servings, 2)

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
    
    if drinking_time < 0.75:
        elimination_factor = drinking_time / 0.25
        elimination_time = drinking_time * elimination_factor
    else:
        elimination_time = drinking_time

    bac = absorbed_grams / (weight*1000 * r) * 100
    grams_per_kg = 0.1 * weight
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

async def calculate_absorption(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    profile = user_profiles[user_id]
    current_time = time.time()
    weight = profile["weight"]
    gender_factor = 1.0 if profile["gender"] == "mies" else 1.15

    total_absorbed = 0

    for drink in profile["drink_history"]:
        drink_elapsed_time = (current_time - drink["timestamp"]) / 3600
        
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
        else:  # c > 60
            concentration_factor = 0.9

        k *= concentration_factor

        drink_grams = drink["servings"] * 12
        absorbed_grams = drink_grams * (1 - math.e**(-k * drink_elapsed_time**1.1))

        if drink_elapsed_time > 2:
            absorbed_grams = drink_grams
        
        total_absorbed += absorbed_grams

    return total_absorbed

def get_group_id():
    with open("data/group_id.txt", "r") as f:
        group_id = int(f.read().strip())
    return group_id