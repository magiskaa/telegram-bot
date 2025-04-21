import time
import random
from bot.save_and_load import save_profiles, user_profiles
from config.config import GIFS, EMOJIS
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

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
        servings = calculate_alcohol(context.user_data["size"], context.user_data["percentage"])
        user_profiles[user_id]["drink_count"] += servings
        if user_profiles[user_id]["start_time"] == 0:
            user_profiles[user_id]["start_time"] = time.time()
        calculate_bac(user_id)
        await update.message.reply_text(f"Lisätty {servings} annosta.")
        if user_profiles[user_id]["BAC"] > 1.7:
            await message(update, context)
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
    user_profiles[user_id]["favorite_drink_size"] = favorite_size
    user_profiles[user_id]["favorite_drink_percentage"] = favorite_percentage
    user_profiles[user_id]["favorite_drink_name"] = favorite_name
    save_profiles()
    await update.message.reply_text(f"Lempijuomasi on nyt {favorite_name}.")
    return ConversationHandler.END

async def favorite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in user_profiles:
        await update.message.reply_text("Et ole vielä määrittänyt profiiliasi. Käytä /setup komentoa ensin.")
        return
    if user_profiles[user_id]["favorite_drink_size"] == 0:
        await update.message.reply_text("Et ole vielä määrittänyt lempijuomaasi. Käytä /favorite_drink komentoa ensin.")
        return

    size = user_profiles[user_id]["favorite_drink_size"]
    percentage = user_profiles[user_id]["favorite_drink_percentage"]
    servings = calculate_alcohol(float(size), float(percentage))
    user_profiles[user_id]["drink_count"] += servings
    if user_profiles[user_id]["start_time"] == 0:
        user_profiles[user_id]["start_time"] = time.time()
    calculate_bac(user_id)
    await update.message.reply_text(f"{user_profiles[user_id]['favorite_drink_name']} +1.")
    if user_profiles[user_id]["BAC"] > 1.7:
        await message(update, context)

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    profile = user_profiles.get(user_id)

    group_id = get_group_id()

    name = profile["name"].capitalize()

    MESSAGES = [
        f"{name_conjugation(name, "lle")} tulee kohta hissiefekti, ottakaa bileämpäri hollille.",
        f"{name_conjugation(name, "lla")} menee nyt lujaa.",
        f"Ottakaa {name_conjugation(name, "lta")} pullo pois!",
        f"{name_conjugation(name, "lle")} ei enää tarjoilla.",
        f"{name_conjugation(name, "lla")} on huomenna rapsakat tunnelmat.",
        f"{name} ottaa nyt väliveden.",
        f"Onkohan tuo {name} kiskonut jo ihan tarpeeksi?",
        f"{name_conjugation(name, "lle")} tulee kohta väsyväsy.",
        f"{name} selvästi tähtää top 3 känneihin.",
        f"{name_conjugation(name, 'lle')} tulee morkkis.",
        f"{name} ei välttämättä muista koko iltaa, mutta me muistetaan.",
        f"{name} on valittu tämän illan vastuuttomimmaksi jannuksi.",
        f"{name_conjugation(name, 'lla')} on ollu jano.",
    ]

    await context.bot.send_animation(
        chat_id=group_id, 
        animation=random.choice(GIFS),
        caption=random.choice(MESSAGES) + f" {profile['BAC']:.2f}‰ {random.choice(EMOJIS)}")
    return ConversationHandler.END

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



def calculate_alcohol(vol, perc):
    pure_alcohol = vol * (perc / 100) * 789
    servings = pure_alcohol / 12
    return round(servings, 2)

def calculate_bac(user_id):
    profile = user_profiles[user_id]

    profile["elapsed_time"] = time.time() - profile["start_time"]
    drinking_time = profile["elapsed_time"] / 3600
    
    drinks = profile["drink_count"]
    weight = profile["weight"]
    gender = profile["gender"]
    age = profile["age"]
    height = profile["height"]
    if gender == "mies":
        TBW = 2.447 - 0.09516 * age + 0.1074 * height + 0.3362 * weight
    else:
        TBW = -2.097 + 0.1069 * height + 0.2466 * weight
    r = TBW / weight
    total_grams_of_alcohol = drinks * 12
    
    bac = total_grams_of_alcohol / (weight*1000 * r) * 100
    grams_per_kg = 0.1 * weight
    bac_elim = grams_per_kg / (weight*1000 * r) * 100
    bac -= bac_elim * drinking_time
    bac = max(0, bac)

    profile["BAC"] = bac * 10
    save_profiles()

def reset_drink_stats():
    for user_id in user_profiles:
        user_profiles[user_id]["drink_count"] = 0
        user_profiles[user_id]["start_time"] = 0
        user_profiles[user_id]["elapsed_time"] = 0
        user_profiles[user_id]["BAC"] = 0
    save_profiles()

def get_group_id():
    with open("config/group_id.txt", "r") as f:
        group_id = int(f.read().strip())
    return group_id