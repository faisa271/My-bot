import telebot
import sqlite3
import os
import time
import sys
from telebot import types

# --- Config ---
TOKEN = '8031810027:AAE0w8qFFRXFT1AjCEfw9xII-H2x8roRalM'
ADMIN = 7859342477
SUPPORT_URL = "https://t.me/NepalGmailsupport"

bot = telebot.TeleBot(TOKEN)

# --- Database ---
def init_db():
    conn = sqlite3.connect('final_v11.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, name TEXT, main REAL DEFAULT 0, 
        app INTEGER DEFAULT 0, rej INTEGER DEFAULT 0, ref_by INTEGER)''')
    c.execute('CREATE TABLE IF NOT EXISTS stock (id INTEGER PRIMARY KEY AUTOINCREMENT, info TEXT, status TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS config (id TEXT PRIMARY KEY, val REAL)')
    c.execute("INSERT OR IGNORE INTO config VALUES ('per', 1.0), ('ref', 0.5), ('min', 10.0)")
    conn.commit()
    return conn

db = init_db()

def get_conf(key):
    c = db.cursor()
    c.execute("SELECT val FROM config WHERE id=?", (key,))
    res = c.fetchone()
    return float(res[0]) if res else 0.0

# --- Keyboards ---
def main_menu(uid):
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("📧 Register a New Account", "💰 Balance")
    m.add("👥 Refer & Earn", "💳 Withdraw")
    m.add("🎧 Support")
    if uid == ADMIN:
        m.add("🎮 Admin Panel")
    return m

def admin_panel_kb():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("📊 Stats", "📦 View Stock")
    m.add("💰 Set Per Task", "🎁 Set Refer Bonus")
    m.add("💸 Set Min Withdraw", "📢 Broadcast")
    m.add("🏠 Back to Home")
    return m

# --- START ---
@bot.message_handler(commands=['start'])
def start(message):
    uid, fname = message.from_user.id, message.from_user.first_name
    c = db.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (uid,))
    if not c.fetchone():
        args = message.text.split()
        ref_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
        bonus = get_conf('ref')
        if ref_id and ref_id != uid:
            c.execute("UPDATE users SET main = main + ? WHERE id=?", (bonus, ref_id))
            try: bot.send_message(ref_id, f"🎁 रेफरल बोनस प्राप्त भयो: +{bonus} NRP")
            except: pass
            c.execute("INSERT INTO users VALUES (?, ?, 0, 0, 0, ?)", (uid, fname, ref_id))
        else:
            c.execute("INSERT INTO users VALUES (?, ?, 0, 0, 0, NULL)", (uid, fname))
        db.commit()
    bot.send_message(uid, f"नमस्ते {fname}! स्वागत छ।", reply_markup=main_menu(uid))

# --- ADMIN PANEL LOGIC ---
@bot.message_handler(func=lambda m: m.from_user.id == ADMIN)
def admin_handler(message):
    uid, text = message.chat.id, message.text
    c = db.cursor()

    if text == "🎮 Admin Panel":
        bot.send_message(uid, "🕹 एडमिन प्यानलमा स्वागत छ। कार्य छनोट गर्नुहोस्:", reply_markup=admin_panel_kb())
    
    elif text == "📊 Stats":
        c.execute("SELECT COUNT(*) FROM users")
        total = c.fetchone()[0]
        bot.send_message(uid, f"📊 **Status:**\nTotal Users: {total}\nPer Task: {get_conf('per')} NRP\nMin Withdraw: {get_conf('min')} NRP")

    elif text == "📦 View Stock":
        c.execute("SELECT id, info FROM stock WHERE status='available'")
        rows = c.fetchall()
        if not rows: return bot.send_message(uid, "स्टक खाली छ। `/add [data]` बाट थप्नुहोस्।")
        for r in rows:
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Delete 🗑", callback_data=f"del_{r[0]}"))
            bot.send_message(uid, f"🆔 ID: {r[0]}\n📝 Info: `{r[1]}`", reply_markup=kb)

    elif text == "💰 Set Per Task":
        msg = bot.send_message(uid, "नयाँ टास्क रेट पठाउनुहोस् (Example: 2.5):")
        bot.register_next_step_handler(msg, lambda m: update_conf(m, 'per'))

    elif text == "🎁 Set Refer Bonus":
        msg = bot.send_message(uid, "नयाँ रेफरल बोनस पठाउनुहोस्:")
        bot.register_next_step_handler(msg, lambda m: update_conf(m, 'ref'))

    elif text == "💸 Set Min Withdraw":
        msg = bot.send_message(uid, "न्यूनतम विड्रअल लिमिट पठाउनुहोस्:")
        bot.register_next_step_handler(msg, lambda m: update_conf(m, 'min'))

    elif text == "📢 Broadcast":
        msg = bot.send_message(uid, "सबैलाई पठाउने मेसेज लेख्नुहोस्:")
        bot.register_next_step_handler(msg, process_broadcast)

    elif text == "🏠 Back to Home":
        bot.send_message(uid, "User Menu मा फर्कियो।", reply_markup=main_menu(uid))

    # SLASH COMMANDS SUPPORT
    elif text.startswith("/addbal"):
        try:
            cmd = text.split()
            c.execute("UPDATE users SET main = main + ? WHERE id=?", (float(cmd[2]), int(cmd[1])))
            db.commit(); bot.reply_to(message, "✅ Success!")
        except: bot.reply_to(message, "Usage: `/addbal ID Amt`")

    elif text.startswith("/add "):
        data = text.replace("/add ", "")
        c.execute("INSERT INTO stock (info, status) VALUES (?, 'available')", (data,))
        db.commit(); bot.reply_to(message, "✅ Stock Added!")

def update_conf(message, key):
    try:
        val = float(message.text)
        c = db.cursor()
        c.execute("UPDATE config SET val=? WHERE id=?", (val, key))
        db.commit()
        bot.send_message(ADMIN, f"✅ {key} सफलतापूर्वक अपडेट भयो: {val}")
    except: bot.send_message(ADMIN, "❌ कृपया नम्बर मात्र पठाउनुहोस्।")

def process_broadcast(message):
    c = db.cursor()
    c.execute("SELECT id FROM users")
    users = c.fetchall()
    for u in users:
        try: bot.send_message(u[0], f"📢 **ब्रोडकास्ट:**\n{message.text}")
        except: pass
    bot.send_message(ADMIN, "✅ ब्रोडकास्ट सम्पन्न भयो।")

# --- USER ACTIONS ---
@bot.message_handler(func=lambda m: m.text == "📧 Register a New Account")
def get_task(message):
    uid = message.from_user.id
    c = db.cursor()
    c.execute("SELECT id, info FROM stock WHERE status='available' LIMIT 1")
    row = c.fetchone()
    if row:
        # Task लिने बित्तिकै 'locked' हुन्छ (One-time Use)
        c.execute("UPDATE stock SET status='locked' WHERE id=?", (row[0],))
        db.commit()
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Done ✅", callback_data=f"done_{row[0]}_{uid}"))
        kb.add(types.InlineKeyboardButton("Cancel ❌", callback_data=f"can_{row[0]}_{uid}"))
        bot.send_message(uid, f"📝 **तपाईंको टास्क:**\n\n`{row[1]}`\n\n**नोट:** यो टास्क एक पटक मात्र प्रयोग गर्न सकिन्छ।", reply_markup=kb, parse_mode="Markdown")
    else: bot.send_message(uid, "❌ अहिले स्टक खाली छ।")

@bot.message_handler(func=lambda m: m.text == "💰 Balance")
def show_bal(message):
    c = db.cursor(); c.execute("SELECT main FROM users WHERE id=?", (message.from_user.id,))
    res = c.fetchone()
    bot.reply_to(message, f"💰 तपाइँको ब्यालेन्स: **{res[0]} NRP**", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "💳 Withdraw")
def withdraw_req(message):
    uid = message.from_user.id
    c = db.cursor(); c.execute("SELECT main FROM users WHERE id=?", (uid,))
    bal = float(c.fetchone()[0])
    min_w = get_conf('min')
    
    if bal < min_w:
        bot.reply_to(message, f"❌ न्यूनतम विड्रअल {min_w} NRP हुनुपर्छ।\nतपाईँको ब्यालेन्स: {bal} NRP")
    else:
        msg = bot.send_message(uid, "विड्रअलको लागि (रकम, eSewa ID) पठाउनुहोस्:\nउदाहरण: `50, 98XXXXXXXX`")
        bot.register_next_step_handler(msg, process_withdraw_fixed)

def process_withdraw_fixed(message):
    try:
        parts = message.text.split(',')
        amt = float(parts[0].strip())
        uid = message.from_user.id
        c = db.cursor(); c.execute("SELECT main FROM users WHERE id=?", (uid,))
        current_bal = float(c.fetchone()[0])
        min_w = get_conf('min')

        if amt >= min_w and amt <= current_bal:
            c.execute("UPDATE users SET main = main - ? WHERE id=?", (amt, uid))
            db.commit()
            bot.send_message(uid, f"✅ {amt} NRP विड्रअल अनुरोध सफल भयो। एडमिनले छिट्टै पैसा पठाउनुहुनेछ।")
            bot.send_message(ADMIN, f"💳 **Withdraw Request:**\nUser ID: `{uid}`\nAmount: `{amt}`\nInfo: `{message.text}`")
        else:
            bot.send_message(uid, f"❌ ब्यालेन्स पुगेन वा लिमिट मिलेन। (ब्यालेन्स: {current_bal})")
    except: bot.send_message(message.chat.id, "❌ फॉर्मेट मिलेन। कृपया (रकम, विवरण) लेख्नुहोस्।")

@bot.message_handler(func=lambda m: m.text == "👥 Refer & Earn")
def refer_link(message):
    uid = message.from_user.id
    bot.send_message(uid, f"🔗 तपाइँको लिंक: https://t.me/{bot.get_me().username}?start={uid}")

@bot.message_handler(func=lambda m: m.text == "🎧 Support")
def contact_admin(message):
    bot.send_message(message.chat.id, f"सहयोगको लागि यहाँ जानुहोस्: {SUPPORT_URL}")

# --- CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def calls_handler(call):
    c = db.cursor(); data = call.data.split('_')
    if data[0] == "done":
        kb = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("Approve ✅", callback_data=f"app_{data[1]}_{data[2]}"),
            types.InlineKeyboardButton("Reject ❌", callback_data=f"rej_{data[1]}_{data[2]}")
        )
        bot.send_message(ADMIN, f"🧐 कार्य जाँच (User: {data[2]}):", reply_markup=kb)
        bot.edit_message_text("⏳ एडमिनले चेक गर्दै हुनुहुन्छ...", call.message.chat.id, call.message.message_id)
    
    elif data[0] == "can":
        # क्यान्सिल गरे पनि यो 'locked' नै रहन्छ (One-time policy)। यदि उपलब्ध गराउने हो भने DELETE को साटो UPDATE status='available' राख्नुहोस्।
        c.execute("DELETE FROM stock WHERE id=?", (data[1],))
        db.commit()
        bot.edit_message_text("❌ कार्य रद्द गरियो र स्टकबाट हटाइयो।", call.message.chat.id, call.message.message_id)

    elif data[0] == "app":
        p = get_conf('per')
        c.execute("UPDATE users SET main = main + ?, app = app + 1 WHERE id=?", (p, data[2]))
        c.execute("DELETE FROM stock WHERE id=?", (data[1],))
        db.commit()
        bot.send_message(data[2], f"✅ कार्य स्वीकृत! +{p} NRP ब्यालेन्समा थपियो।")
        bot.edit_message_text("Approved ✅", ADMIN, call.message.message_id)

    elif data[0] == "rej":
        c.execute("DELETE FROM stock WHERE id=?", (data[1],))
        db.commit()
        bot.send_message(data[2], "❌ कार्य अस्वीकृत गरियो।")
        bot.edit_message_text("Rejected & Deleted ❌", ADMIN, call.message.message_id)

    elif data[0] == "del":
        c.execute("DELETE FROM stock WHERE id=?", (data[1],))
        db.commit(); bot.delete_message(ADMIN, call.message.message_id)

# --- RUN ---
print("==============================")
print("🤖 Banking Bot is RUNNING...")
print("Admin ID:", ADMIN)
print("Status: Success - Errors Fixed")
print("==============================")

bot.infinity_polling(none_stop=True)
