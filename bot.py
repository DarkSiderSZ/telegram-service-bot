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
DATA_FILE = "/data/service_status.json"   # persisted via Railway volume mounted at /data
AUDIT_FILE = "/data/audit.log"

PIN_ENV = "BOT_PIN"
AUTH_FILE = "/data/auth.json"
AUTH_TTL_SECONDS = 24 * 60 * 60  # 24 hours (change if you want)

ICON_ALL_IN = "✅"
ICON_ALL_OUT = "❌"
ICON_MIXED = "➖"
ICON_IN = "✅"
ICON_OUT = "❌"

CB_CAT = "cat:"       # cat:<category_id>
CB_BACK = "back"      # back to categories
CB_TOGGLE = "tog:"    # tog:<category_id>:<item_id>

# ========== DEFAULT DATA ==========
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
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    if not os.path.exists(DATA_FILE):
        save_data(DEFAULT_DATA)
        return DEFAULT_DATA
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ========== AUTH (PIN unlock) ==========
def load_auth() -> Dict[str, float]:
    os.makedirs(os.path.dirname(AUTH_FILE), exist_ok=True)
    if not os.path.exists(AUTH_FILE):
        return {}
    try:
        with open(AUTH_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {str(k): float(v) for k, v in data.items()}
    except Exception:
        return {}

def save_auth(auth: Dict[str, float]) -> None:
    os.makedirs(os.path.dirname(AUTH_FILE), exist_ok=True)
    with open(AUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(auth, f, ensure_ascii=False, indent=2)

def cleanup_and_get_until(user_id: int) -> float:
    """Returns unlock-until timestamp (epoch seconds) for user_id, after cleaning expired."""
    auth = load_auth()
    now = time.time()

    expired = [uid for uid, until in auth.items() if until <= now]
    for uid in expired:
        auth.pop(uid, None)
    if expired:
        save_auth(auth)

    return float(auth.get(str(user_id), 0.0))

def is_unlocked(user_id: int) -> bool:
    return time.time() < cleanup_and_get_until(user_id)

def set_unlocked(user_id: int, unlocked: bool) -> None:
    auth = load_auth()
    if unlocked:
        auth[str(user_id)] = time.time() + AUTH_TTL_SECONDS
    else:
        auth.pop(str(user_id), None)
    save_auth(auth)

def format_remaining(until_ts: float) -> str:
    remaining = int(until_ts - time.time())
    if remaining <= 0:
        return ""
    hours = remaining // 3600
    minutes = (remaining % 3600) // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"

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
        cb = f"{CB_TOGGLE}{cat['id']}:{item['id']}" if allow_toggle else "noop"
        rows.append([InlineKeyboardButton(text=label, callback_data=cb)])

    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data=CB_BACK)])
    return InlineKeyboardMarkup(rows)


def log_action(user, category_name: str, item_name: str, new_status: bool) -> None:
    os.makedirs(os.path.dirname(AUDIT_FILE), exist_ok=True)

    username = user.username or "no_username"
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    status_text = "IN" if new_status else "OUT"

    line = (
        f"{time.strftime('%Y-%m-%d %H:%M:%S')} | "
        f"{full_name} (@{username}, id:{user.id}) | "
        f"{category_name} -> {item_name} -> {status_text}\n"
    )

    with open(AUDIT_FILE, "a", encoding="utf-8") as f:
        f.write(line)

    username = user.username or "no_username"
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    status_text = "IN" if new_status else "OUT"

    line = (
        f"{time.strftime('%Y-%m-%d %H:%M:%S')} | "
        f"{full_name} (@{username}, id:{user.id}) | "
        f"{category_name} -> {item_name} -> {status_text}\n"
    )

    with open(AUDIT_FILE, "a", encoding="utf-8") as f:
        f.write(line)
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data=CB_BACK)])
    return InlineKeyboardMarkup(rows)

# ========== COMMANDS ==========
async def unlock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pin = os.getenv(PIN_ENV, "").strip()
    if not pin:
        await update.message.reply_text("PIN not set on server.")
        return

    if not context.args:
        await update.message.reply_text("Use: /unlock <PIN>")
        return

    if context.args[0].strip() == pin:
        user = update.effective_user
        if not user:
            await update.message.reply_text("Could not identify user.")
            return
        set_unlocked(user.id, True)
        until_ts = cleanup_and_get_until(user.id)
        rem = format_remaining(until_ts)
        await update.message.reply_text(f"Unlocked ✅ ({rem} remaining)")
    else:
        await update.message.reply_text("Wrong PIN ❌")

async def lock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user:
        set_unlocked(user.id, False)
    await update.message.reply_text("Locked 🔒")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = load_data()
    await update.message.reply_text("Choose a category:", reply_markup=build_categories_keyboard(data))

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "/start - categories\n"
        "/unlock <PIN> - enable editing\n"
        "/lock - disable editing\n"
        "/help - help\n"
    )

# ========== BUTTON HANDLER ==========
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

        user = update.effective_user
        locked = True
        remaining_line = ""

        if user:
            until_ts = cleanup_and_get_until(user.id)
            if time.time() < until_ts:
                locked = False
                rem = format_remaining(until_ts)
                if rem:
                    remaining_line = f"\n🕒 {rem} remaining"

        lock_icon = " 🔒" if locked else ""
        text = f"{icon} *{cat.get('name','Category')}*{lock_icon}{remaining_line}"

        await query.edit_message_text(
            text,
            reply_markup=build_items_keyboard(cat, allow_toggle=True),
            parse_mode="Markdown",
        )
        return

    if d.startswith(CB_TOGGLE):
        pin = os.getenv(PIN_ENV, "").strip()
        user = update.effective_user

        # Hard lock if no PIN is set
        if not pin:
            await query.answer("Editing disabled (no PIN set).", show_alert=True)
            return

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
                log_action(user, cat.get("name", ""), it.get("name", ""), it["in_service"])
                break

        # Re-load fresh data and re-render same category so keyboard updates immediately
        data = load_data()
        cat = find_category(data, cat_id)
        if not cat:
            await query.answer("Category not found after update.", show_alert=True)
            return

        icon = category_status_icon(cat.get("items", []))

        locked = True
        remaining_line = ""
        if user:
            until_ts = cleanup_and_get_until(user.id)
            if time.time() < until_ts:
                locked = False
                rem = format_remaining(until_ts)
                if rem:
                    remaining_line = f"\n🕒 {rem} remaining"

        lock_icon = " 🔒" if locked else ""
        text = f"{icon} *{cat.get('name','Category')}*{lock_icon}{remaining_line}"

        await query.edit_message_text(
            text=text,
            reply_markup=build_items_keyboard(cat, allow_toggle=True),
            parse_mode="Markdown",
        )
        return
async def audit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not os.path.exists(AUDIT_FILE):
        await update.message.reply_text("No audit logs yet.")
        return

    # default = 10 lines
    limit = 10
    if context.args:
        try:
            limit = max(1, min(100, int(context.args[0])))
        except ValueError:
            pass

    with open(AUDIT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if not lines:
        await update.message.reply_text("No audit logs yet.")
        return

    last_lines = lines[-limit:]
    text = "".join(last_lines)

    # Telegram max message length safety
    if len(text) > 4000:
        text = text[-4000:]

    await update.message.reply_text(f"📜 Last {len(last_lines)} changes:\n\n{text}")
def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Missing BOT_TOKEN environment variable.")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("unlock", unlock_cmd))
    app.add_handler(CommandHandler("lock", lock_cmd))
    app.add_handler(CommandHandler("audit", audit_cmd))
    app.add_handler(CallbackQueryHandler(on_button))

    print("Bot running... Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()





