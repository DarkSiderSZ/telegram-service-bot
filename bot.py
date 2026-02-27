import time
import json
import os
from typing import Dict, Any, List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

# ========== CONFIG ==========
DATA_FILE = "/data/service_status.json"
PIN_ENV = "BOT_PIN"
AUTH_FILE = "/data/auth.json"
AUTH_TTL_SECONDS = 24 * 60 * 60  # 8 hours

# Put your Telegram numeric user id(s) here to enable tap-to-toggle.
# Get it by messaging @userinfobot on Telegram.
ADMIN_USER_IDS = {123456789}  # <-- change this (or set() to disable toggling)

ICON_ALL_IN = "✅"
ICON_ALL_OUT = "❌"
ICON_MIXED = "➖"
ICON_IN = "✅"
ICON_OUT = "❌"

CB_CAT = "cat:"       # cat:<category_id>
CB_BACK = "back"      # back to categories
CB_TOGGLE = "tog:"    # tog:<category_id>:<item_id>


# ========== DEFAULT DATA (YOUR CATEGORIES) ==========
# Edit the items later, or the bot will create service_status.json you can edit.
DEFAULT_DATA = {
    "categories": [
        {"id": "deserts", "name": "Deserts", "items": [
            {"id": "cheesecake", "name": "Cheesecake", "in_service": True},
            {"id": "brownie", "name": "Brownie", "in_service": True},
        ]},
        {"id": "speciality_coffee", "name": "Speciality Coffee", "items": [
            {"id": "v60", "name": "V60", "in_service": True},
            {"id": "aeropress", "name": "AeroPress", "in_service": True},
        ]},
        {"id": "hot_drinks", "name": "Hot Drinks", "items": [
            {"id": "americano", "name": "Americano", "in_service": True},
            {"id": "hot_chocolate", "name": "Hot Chocolate", "in_service": True},
        ]},
        {"id": "iced_coffee", "name": "Iced Coffee", "items": [
            {"id": "iced_americano", "name": "Iced Americano", "in_service": True},
            {"id": "iced_latte", "name": "Iced Latte", "in_service": True},
        ]},
        {"id": "iced_tea", "name": "Iced Tea", "items": [
            {"id": "lemon_iced_tea", "name": "Lemon Iced Tea", "in_service": True},
            {"id": "peach_iced_tea", "name": "Peach Iced Tea", "in_service": True},
        ]},
        {"id": "frappuccino", "name": "Frappuccino", "items": [
            {"id": "coffee_frappe", "name": "Coffee Frappe", "in_service": True},
            {"id": "caramel_frappe", "name": "Caramel Frappe", "in_service": True},
        ]},
        {"id": "matcha", "name": "Matcha", "items": [
            {"id": "matcha_latte", "name": "Matcha Latte", "in_service": True},
            {"id": "iced_matcha", "name": "Iced Matcha", "in_service": True},
        ]},
        {"id": "milkshake", "name": "Milkshake", "items": [
            {"id": "vanilla_milkshake", "name": "Vanilla", "in_service": True},
            {"id": "oreo_milkshake", "name": "Oreo", "in_service": True},
        ]},
        {"id": "mojito", "name": "Mojito", "items": [
            {"id": "classic_mojito", "name": "Classic", "in_service": True},
            {"id": "strawberry_mojito", "name": "Strawberry", "in_service": True},
        ]},
        {"id": "mojito_mixes", "name": "Mojito Mixes", "items": [
            {"id": "mint_mix", "name": "Mint Mix", "in_service": True},
            {"id": "berry_mix", "name": "Berry Mix", "in_service": True},
        ]},
        {"id": "yogurt", "name": "Yogurt", "items": [
            {"id": "yogurt_berry", "name": "Berry Yogurt", "in_service": True},
            {"id": "yogurt_mango", "name": "Mango Yogurt", "in_service": True},
        ]},
        {"id": "cold_drinks", "name": "Cold Drinks", "items": [
            {"id": "water", "name": "Water", "in_service": True},
            {"id": "soft_drink", "name": "Soft Drink", "in_service": True},
        ]},
        {"id": "smoothie", "name": "Smoothie", "items": [
            {"id": "strawberry_smoothie", "name": "Strawberry Smoothie", "in_service": True},
            {"id": "mango_smoothie", "name": "Mango Smoothie", "in_service": True},
        ]},
    ]
}


# ========== STORAGE ==========
def load_data() -> Dict[str, Any]:
    if not os.path.exists(DATA_FILE):
        save_data(DEFAULT_DATA)
        return DEFAULT_DATA
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data: Dict[str, Any]) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ========== HELPERS ==========
def category_status_icon(items: List[Dict[str, Any]]) -> str:
    if not items:
        return ICON_ALL_OUT
    ins = sum(1 for it in items if it.get("in_service"))
    if ins == len(items):
        return ICON_ALL_IN
    if ins == 0:
        return ICON_ALL_OUT
    return ICON_MIXED

def find_category(data: Dict[str, Any], category_id: str):
    for cat in data.get("categories", []):
        if cat.get("id") == category_id:
            return cat
    return None

def is_admin(update: Update) -> bool:
    user = update.effective_user
    return bool(user and user.id in ADMIN_USER_IDS)

def build_categories_keyboard(data: Dict[str, Any]) -> InlineKeyboardMarkup:
    rows = []
    for cat in data.get("categories", []):
        icon = category_status_icon(cat.get("items", []))
        text = f"{icon} {cat.get('name','Unnamed')}"
        rows.append([InlineKeyboardButton(text=text, callback_data=f"{CB_CAT}{cat['id']}")])
    return InlineKeyboardMarkup(rows)

def build_items_keyboard(cat: Dict[str, Any], allow_toggle: bool) -> InlineKeyboardMarkup:
    rows = []
    for item in cat.get("items", []):
        icon = ICON_IN if item.get("in_service") else ICON_OUT
        label = f"{icon} {item.get('name','Item')}"
        if allow_toggle:
            cb = f"{CB_TOGGLE}{cat['id']}:{item['id']}"
        else:
            cb = "noop"
        rows.append([InlineKeyboardButton(text=label, callback_data=cb)])

    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data=CB_BACK)])
    return InlineKeyboardMarkup(rows)
def load_auth() -> Dict[str, float]:
    if not os.path.exists(AUTH_FILE):
        return {}
    try:
        with open(AUTH_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # ensure floats
            return {str(k): float(v) for k, v in data.items()}
    except Exception:
        return {}

def save_auth(auth: Dict[str, float]) -> None:
    os.makedirs(os.path.dirname(AUTH_FILE), exist_ok=True)
    with open(AUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(auth, f, ensure_ascii=False, indent=2)

def is_unlocked(user_id: int) -> bool:
    auth = load_auth()
    now = time.time()
    # cleanup expired
    expired = [uid for uid, until in auth.items() if until <= now]
    for uid in expired:
        auth.pop(uid, None)
    if expired:
        save_auth(auth)
    return now < auth.get(str(user_id), 0.0)

def set_unlocked(user_id: int, unlocked: bool) -> None:
    auth = load_auth()
    if unlocked:
        auth[str(user_id)] = time.time() + AUTH_TTL_SECONDS
    else:
        auth.pop(str(user_id), None)
    save_auth(auth)    

# ========== HANDLERS ==========
async def unlock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pin = os.getenv(PIN_ENV, "")
    if not pin:
        await update.message.reply_text("PIN not set on server.")
        return

    if not context.args:
        await update.message.reply_text("Use: /unlock <PIN>")
        return

    if context.args[0] == pin:
        set_unlocked(update.effective_user.id, True)
        await update.message.reply_text("Unlocked ✅ You can toggle items now.")
    else:
        await update.message.reply_text("Wrong PIN ❌")

async def lock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    set_unlocked(update.effective_user.id, False)
    await update.message.reply_text("Locked 🔒")
    
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = load_data()
    await update.message.reply_text("Choose a category:", reply_markup=build_categories_keyboard(data))

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = load_data()
    d = query.data or ""

    if d == CB_BACK:
        await query.edit_message_text("Choose a category:", reply_markup=build_categories_keyboard(data))
        return

    if d == "noop":
        return

    if d.startswith(CB_CAT):
        cat_id = d[len(CB_CAT):]
        cat = find_category(data, cat_id)
        if not cat:
            await query.edit_message_text("Category not found.")
            return
        icon = category_status_icon(cat.get("items", []))
        text = f"{icon} *{cat.get('name','Category')}*"
        if is_admin(update):
            text += "\nTap an item to toggle."
        await query.edit_message_text(
            text,
            reply_markup=build_items_keyboard(cat, allow_toggle=True),
            parse_mode="Markdown",
        )
        return

if d.startswith(CB_TOGGLE):
    user = update.effective_user
    if not user or not is_unlocked(user.id):
        await query.answer("Locked. Use /unlock <PIN> to edit.", show_alert=True)
        return
        payload = d[len(CB_TOGGLE):]  # <cat_id>:<item_id>
        if ":" not in payload:
            await query.answer("Bad data.", show_alert=True)
            return
        cat_id, item_id = payload.split(":", 1)

        cat = find_category(data, cat_id)
        if not cat:
            await query.answer("Category not found.", show_alert=True)
            return

        for it in cat.get("items", []):
            if it.get("id") == item_id:
                it["in_service"] = not bool(it.get("in_service"))
                save_data(data)
                break

        # refresh
        icon = category_status_icon(cat.get("items", []))
        text = f"{icon} *{cat.get('name','Category')}*\nTap an item to toggle."
        await query.edit_message_text(
            text,
            reply_markup=build_items_keyboard(cat, allow_toggle=True),
            parse_mode="Markdown",
        )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("/start - categories\n/help - help\n")

def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Missing BOT_TOKEN environment variable.")

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("unlock", unlock_cmd))
    app.add_handler(CommandHandler("lock", lock_cmd))
    app.add_handler(CallbackQueryHandler(on_button))

    print("Bot running... Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":

    main()



