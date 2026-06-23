
import os, json
from datetime import datetime
import httpx
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN     = "8603036898:AAH5aTd6ui9FmNU6zOvemenJlz5sfCkatI0"
SUPABASE_URL  = "https://cbfztoaeyvepxnwvayyk.supabase.co"
SUPABASE_KEY  = "sb_publishable_Rnhs6OvSqHsQsn14nsRekg_ouO-32fl"
ANTHROPIC_KEY = "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"
ALLOWED_USER  = "6138343624"

HEADERS_SB = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

async def sb_insert(table, data):
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{SUPABASE_URL}/rest/v1/{table}", headers=HEADERS_SB, json=data)
        return r.status_code in (200, 201)

async def sb_select(table, params=""):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{SUPABASE_URL}/rest/v1/{table}?{params}", headers=HEADERS_SB)
        return r.json() if r.status_code == 200 else []

async def ask_claude(system, user, max_tokens=400):
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": max_tokens, "system": system, "messages": [{"role": "user", "content": user}]},
        )
        data = r.json()
        return data["content"][0]["text"] if r.status_code == 200 else "AI недоступен"

def allowed(update):
    return not ALLOWED_USER or str(update.effective_user.id) == ALLOWED_USER

MAIN_KB = ReplyKeyboardMarkup([
    ["💰 Доход", "💸 Расход"],
    ["⚖️ Вес", "✅ Задача"],
    ["🔥 Привычка", "📊 Сводка"],
    ["💡 Идея", "🤖 AI"],
], resize_keyboard=True)

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not allowed(update): return
    await update.message.reply_text(
        f"👋 Привет, {update.effective_user.first_name}!\n\n🦁 SANS LAB Life OS Bot\n\nПиши что хочешь записать:",
        reply_markup=MAIN_KB
    )

async def cmd_income(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not allowed(update): return
    if not ctx.args:
        await update.message.reply_text("Пример: /income 5000 продажи Nike")
        return
    amount = float(ctx.args[0])
    category = " ".join(ctx.args[1:]) if len(ctx.args) > 1 else "Прочее"
    ok = await sb_insert("finances", {"type": "income", "amount": amount, "category": category, "date": datetime.now().isoformat()})
    await update.message.reply_text(f"{'✅' if ok else '⚠️'} Доход записан!\n\n💰 +₽{amount:,.0f} · {category}", reply_markup=MAIN_KB)

async def cmd_expense(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not allowed(update): return
    if not ctx.args:
        await update.message.reply_text("Пример: /expense 2500 еда")
        return
    amount = float(ctx.args[0])
    category = " ".join(ctx.args[1:]) if len(ctx.args) > 1 else "Прочее"
    ok = await sb_insert("finances", {"type": "expense", "amount": amount, "category": category, "date": datetime.now().isoformat()})
    await update.message.reply_text(f"{'✅' if ok else '⚠️'} Расход записан!\n\n💸 -₽{amount:,.0f} · {category}", reply_markup=MAIN_KB)

async def cmd_weight(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not allowed(update): return
    if not ctx.args:
        await update.message.reply_text("Пример: /weight 69.5")
        return
    w = float(ctx.args[0])
    await sb_insert("weight_log", {"weight": w, "date": datetime.now().isoformat()})
    left = round(80 - w, 1)
    weeks = round(left / 0.8, 1)
    await update.message.reply_text(f"⚖️ Вес записан!\n\nСейчас: *{w} кг*\nЦель: 80 кг\nОсталось: {left} кг (~{weeks} нед)", parse_mode="Markdown", reply_markup=MAIN_KB)

async def cmd_task(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not allowed(update): return
    if not ctx.args:
        await update.message.reply_text("Пример: /task Позвонить поставщику")
        return
    text = " ".join(ctx.args)
    await sb_insert("tasks", {"text": text, "status": "todo", "date": datetime.now().isoformat(), "priority": "medium"})
    await update.message.reply_text(f"✅ Задача добавлена!\n\n📌 {text}", reply_markup=MAIN_KB)

async def cmd_idea(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not allowed(update): return
    if not ctx.args:
        await update.message.reply_text("Пример: /idea Выйти на Wildberries")
        return
    text = " ".join(ctx.args)
    await sb_insert("notes", {"title": text[:50], "text": text, "type": "idea", "date": datetime.now().isoformat()})
    await update.message.reply_text(f"💡 Идея сохранена!\n\n{text}", reply_markup=MAIN_KB)

async def cmd_habit(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not allowed(update): return
    if not ctx.args:
        await update.message.reply_text("Пример: /habit зал")
        return
    habit = " ".join(ctx.args)
    await sb_insert("habits_log", {"habit": habit, "date": datetime.now().date().isoformat()})
    await update.message.reply_text(f"🔥 Привычка отмечена!\n\n✓ {habit.title()}", reply_markup=MAIN_KB)

async def cmd_summary(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not allowed(update): return
    await update.message.reply_text("⏳ Собираю сводку...")
    today = datetime.now().date().isoformat()
    fins = await sb_select("finances", f"date=gte.{today}")
    income = sum(f["amount"] for f in fins if f.get("type") == "income")
    expense = sum(f["amount"] for f in fins if f.get("type") == "expense")
    habits = await sb_select("habits_log", f"date=eq.{today}")
    tasks = await sb_select("tasks", f"status=eq.todo")
    await update.message.reply_text(
        f"📊 *Сводка за сегодня*\n\n💰 Доход: ₽{income:,.0f}\n💸 Расход: ₽{expense:,.0f}\n💵 Баланс: ₽{income-expense:,.0f}\n\n📌 Задач: {len(tasks)}\n🔥 Привычек: {len(habits)}",
        parse_mode="Markdown", reply_markup=MAIN_KB
    )

SYSTEM_PARSE = 'Ты помощник Life OS. Верни ТОЛЬКО JSON без markdown: {"action":"income|expense|weight|task|idea|habit|question|unknown","amount":null,"category":null,"text":null,"weight":null,"reply":"ответ на русском"}'

async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not allowed(update): return
    msg = update.message.text
    btns = {"💰 Доход": "/income СУММА КАТЕГОРИЯ", "💸 Расход": "/expense СУММА КАТЕГОРИЯ",
            "⚖️ Вес": "/weight ВЕС", "✅ Задача": "/task ТЕКСТ",
            "💡 Идея": "/idea ТЕКСТ", "🔥 Привычка": "/habit НАЗВАНИЕ"}
    if msg in btns:
        await update.message.reply_text(f"Введи: {btns[msg]}", reply_markup=MAIN_KB); return
    if msg == "📊 Сводка":
        await cmd_summary(update, ctx); return
    if msg == "🤖 AI":
        await update.message.reply_text("Задай любой вопрос!", reply_markup=MAIN_KB); return

    await update.message.reply_text("🤔 Разбираю...")
    result = await ask_claude(SYSTEM_PARSE, msg)
    try:
        data = json.loads(result.strip().replace("```json","").replace("```","").strip())
        action = data.get("action")
        if action == "income" and data.get("amount"):
            await sb_insert("finances", {"type": "income", "amount": float(data["amount"]), "category": data.get("category","Прочее"), "date": datetime.now().isoformat()})
        elif action == "expense" and data.get("amount"):
            await sb_insert("finances", {"type": "expense", "amount": float(data["amount"]), "category": data.get("category","Прочее"), "date": datetime.now().isoformat()})
        elif action == "weight" and data.get("weight"):
            await sb_insert("weight_log", {"weight": float(data["weight"]), "date": datetime.now().isoformat()})
        elif action == "task" and data.get("text"):
            await sb_insert("tasks", {"text": data["text"], "status": "todo", "date": datetime.now().isoformat(), "priority": "medium"})
        elif action == "idea" and data.get("text"):
            await sb_insert("notes", {"title": data["text"][:50], "text": data["text"], "type": "idea", "date": datetime.now().isoformat()})
        elif action == "question":
            answer = await ask_claude("Ты AI-ассистент Life OS для Андреевича. Отвечай кратко на русском.", msg, 300)
            await update.message.reply_text(answer, reply_markup=MAIN_KB); return
        await update.message.reply_text(data.get("reply", "✅ Записал!"), reply_markup=MAIN_KB)
    except Exception:
        answer = await ask_claude("Ты AI Life OS. Отвечай кратко на русском.", msg, 200)
        await update.message.reply_text(answer, reply_markup=MAIN_KB)

async def handle_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎤 Напиши текстом — я пойму!", reply_markup=MAIN_KB)

if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("income",  cmd_income))
    app.add_handler(CommandHandler("expense", cmd_expense))
    app.add_handler(CommandHandler("weight",  cmd_weight))
    app.add_handler(CommandHandler("task",    cmd_task))
    app.add_handler(CommandHandler("idea",    cmd_idea))
    app.add_handler(CommandHandler("habit",   cmd_habit))
    app.add_handler(CommandHandler("summary", cmd_summary))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("🦁 SANS LAB Bot запущен!")
    app.run_polling(drop_pending_updates=True)
