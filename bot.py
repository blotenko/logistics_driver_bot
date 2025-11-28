from datetime import datetime, date, timedelta

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN
from db import init_db, get_session
from models import Vehicle, Driver
from crud import (
    list_drivers,
    list_vehicles,
    create_driver,
    get_assignments_for_date,
    get_assignments_for_driver,
    create_assignment,
)


# --------------------- FORMATTER ---------------------

def fmt(assignments):
    if not assignments:
        return "На эту дату задач нет."

    lines = []
    for a in assignments:
        d = a.driver.full_name if a.driver else "—"
        v = a.vehicle.plate if a.vehicle else "без машины"
        line = f"{d}: {a.task_type} ({a.description}, {v})"
        lines.append(line)

    return "\n".join(lines)


# --------------------- MAIN MENU ---------------------

def main_menu():
    keyboard = [
        [KeyboardButton("📋 Расписание на сегодня"), KeyboardButton("📅 Расписание на завтра")],
        [KeyboardButton("📆 Расписание на дату")],
        [KeyboardButton("👥 Водители"), KeyboardButton("🚚 Машины")],
        [KeyboardButton("➕ Добавить задачу")],
        [KeyboardButton("➕ Добавить водителя")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# --------------------- /START ---------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Выберите действие:",
        reply_markup=main_menu(),
    )


# --------------------- ВОДИТЕЛИ ---------------------

async def drivers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dr = list_drivers()
    if not dr:
        await update.message.reply_text("Водителей пока нет.")
        return

    kb = [
        [InlineKeyboardButton(d.full_name, callback_data=f"driver_select:{d.id}")]
        for d in dr
    ]

    await update.message.reply_text(
        "Выберите водителя:",
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def driver_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    driver_id = int(query.data.split(":")[1])

    with get_session() as s:
        dr = s.query(Driver).get(driver_id)

    assigns_today = get_assignments_for_driver(dr.full_name, date.today())
    assigns_tom = get_assignments_for_driver(dr.full_name, date.today() + timedelta(days=1))

    text = f"👤 *{dr.full_name}*\n\n" \
           f"📋 Сегодня:\n{fmt(assigns_today)}\n\n" \
           f"📅 Завтра:\n{fmt(assigns_tom)}"

    await query.edit_message_text(text, parse_mode="Markdown")


# --------------------- МАШИНЫ ---------------------

async def vehicles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    v = list_vehicles()
    if not v:
        await update.message.reply_text("Машин пока нет.")
        return

    out = "\n".join(f"• {x.plate}" for x in v)
    await update.message.reply_text(f"🚚 Машины:\n{out}")


# --------------------- /DAY ---------------------

async def day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: /day YYYY-MM-DD")
        return

    try:
        d = datetime.strptime(context.args[0], "%Y-%m-%d").date()
    except:
        await update.message.reply_text("Неверная дата.")
        return

    assigns = get_assignments_for_date(d)
    await update.message.reply_text(fmt(assigns))


# --------------------- ДОБАВИТЬ ВОДИТЕЛЯ ---------------------

async def handle_add_driver_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    d = create_driver(name)
    await update.message.reply_text(f"✔ Водитель {d.full_name} добавлен.")
    context.user_data["await_add_driver"] = False


# --------------------- ДОБАВИТЬ ЗАДАЧУ — ДИАЛОГ ---------------------

async def add_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dr = list_drivers()

    kb = [
        [InlineKeyboardButton(d.full_name, callback_data=f"addtask_driver:{d.id}")]
        for d in dr
    ]

    await update.message.reply_text(
        "Выберите водителя:",
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def addtask_driver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    driver_id = int(query.data.split(":")[1])
    context.user_data["task_driver"] = driver_id

    await query.edit_message_text("Введите дату (YYYY-MM-DD):")
    context.user_data["await_task_date"] = True


async def addtask_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        d = date.fromisoformat(update.message.text)
    except:
        await update.message.reply_text("Неверный формат даты. Попробуйте так: 2025-11-28")
        return

    context.user_data["task_date"] = d
    context.user_data["await_task_date"] = False

    vehicles = list_vehicles()
    kb = [
        [InlineKeyboardButton(v.plate, callback_data=f"addtask_vehicle:{v.id}")]
        for v in vehicles
    ]
    kb.append([InlineKeyboardButton("Без машины", callback_data="addtask_vehicle:none")])

    await update.message.reply_text(
        "Выберите машину:",
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def addtask_vehicle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    vehicle_id_raw = query.data.split(":")[1]
    vehicle_id = None if vehicle_id_raw == "none" else int(vehicle_id_raw)

    context.user_data["task_vehicle"] = vehicle_id

    await query.edit_message_text("Введите описание задачи:")
    context.user_data["await_task_desc"] = True


async def addtask_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc = update.message.text.strip()

    driver_id = context.user_data["task_driver"]
    work_date = context.user_data["task_date"]
    vehicle_id = context.user_data["task_vehicle"]

    create_assignment(
        work_date=work_date,
        driver_id=driver_id,
        vehicle_id=vehicle_id,
        task_type="задача",
        description=desc,
        manager="Диспетчер",
    )

    await update.message.reply_text("✔ Задача добавлена.")
    context.user_data.clear()


# --------------------- ОБРАБОТЧИК КНОПОК МЕНЮ ---------------------

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "📋 Расписание на сегодня":
        d = date.today()
        assigns = get_assignments_for_date(d)
        await update.message.reply_text(fmt(assigns))

    elif text == "📅 Расписание на завтра":
        d = date.today() + timedelta(days=1)
        assigns = get_assignments_for_date(d)
        await update.message.reply_text(fmt(assigns))

    elif text == "📆 Расписание на дату":
        await update.message.reply_text("Введите дату YYYY-MM-DD:")
        context.user_data["await_date_for_show"] = True

    elif text == "👥 Водители":
        await drivers(update, context)

    elif text == "🚚 Машины":
        await vehicles(update, context)

    elif text == "➕ Добавить задачу":
        await add_task_start(update, context)

    elif text == "➕ Добавить водителя":
        await update.message.reply_text("Введите ФИО:")
        context.user_data["await_add_driver"] = True

    elif context.user_data.get("await_date_for_show"):
        try:
            d = date.fromisoformat(text)
            assigns = get_assignments_for_date(d)
            await update.message.reply_text(fmt(assigns))
        except:
            await update.message.reply_text("Неверная дата.")
        finally:
            context.user_data["await_date_for_show"] = False

    elif context.user_data.get("await_add_driver"):
        await handle_add_driver_input(update, context)

    elif context.user_data.get("await_task_date"):
        await addtask_date(update, context)

    elif context.user_data.get("await_task_desc"):
        await addtask_desc(update, context)

    else:
        await update.message.reply_text("Не понял команду.")


# --------------------- CALLBACK HANDLER ---------------------

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data

    if data.startswith("driver_select"):
        return await driver_selected(update, context)

    if data.startswith("addtask_driver"):
        return await addtask_driver(update, context)

    if data.startswith("addtask_vehicle"):
        return await addtask_vehicle(update, context)


# --------------------- STARTUP ---------------------

async def on_startup(app):
    await app.bot.delete_webhook(drop_pending_updates=True)


# --------------------- MAIN ---------------------

def main():
    init_db()

    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(on_startup)
        .build()
    )

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("drivers", drivers))
    app.add_handler(CommandHandler("day", day))

    # Кнопки меню
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))

    # Inline-кнопки
    app.add_handler(CallbackQueryHandler(callback_router))

    app.run_polling()


if __name__ == "__main__":
    main()
