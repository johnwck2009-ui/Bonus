import ast
import logging
import operator
import os
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_NAME = "BonusSpecialistaBot"

MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("🧮 Basic Calculator", callback_data="tool:basic")],
    [InlineKeyboardButton("📊 Percentage Calculator", callback_data="tool:percentage"),
     InlineKeyboardButton("🏷 Discount Calculator", callback_data="tool:discount")],
    [InlineKeyboardButton("📈 Commission Calculator", callback_data="tool:commission"),
     InlineKeyboardButton("🎁 Bonus Calculator", callback_data="tool:bonus")],
    [InlineKeyboardButton("💵 Salary Calculator", callback_data="tool:salary")],
    [InlineKeyboardButton("🔄 Unit Converter", callback_data="units")],
    [InlineKeyboardButton("ℹ️ Help", callback_data="help")],
])

UNIT_MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("Kilometres → Miles", callback_data="unit:km_mi"),
     InlineKeyboardButton("Miles → Kilometres", callback_data="unit:mi_km")],
    [InlineKeyboardButton("Kilograms → Pounds", callback_data="unit:kg_lb"),
     InlineKeyboardButton("Pounds → Kilograms", callback_data="unit:lb_kg")],
    [InlineKeyboardButton("Celsius → Fahrenheit", callback_data="unit:c_f"),
     InlineKeyboardButton("Fahrenheit → Celsius", callback_data="unit:f_c")],
    [InlineKeyboardButton("Litres → US Gallons", callback_data="unit:l_gal"),
     InlineKeyboardButton("US Gallons → Litres", callback_data="unit:gal_l")],
    [InlineKeyboardButton("⬅️ Main menu", callback_data="menu")],
])

# A deliberately small arithmetic grammar; eval() is never used.
_ALLOWED_BINARY = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_ALLOWED_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def safe_calculate(expression: str) -> float:
    expression = expression.replace("×", "*").replace("÷", "/").replace(",", ".").strip()
    if len(expression) > 100:
        raise ValueError("Expression is too long.")
    tree = ast.parse(expression, mode="eval")

    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINARY:
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 8:
                raise ValueError("The exponent is too large.")
            result = _ALLOWED_BINARY[type(node.op)](left, right)
            if abs(result) > 1e15:
                raise ValueError("The result is too large.")
            return result
        if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARY:
            return _ALLOWED_UNARY[type(node.op)](visit(node.operand))
        raise ValueError("Use numbers and +, -, *, /, %, **, and parentheses only.")

    result = visit(tree)
    if isinstance(result, complex):
        raise ValueError("Complex results are not supported.")
    return result


def fmt(value: float) -> str:
    if abs(value) < 1e-10:
        value = 0
    return f"{value:,.6f}".rstrip("0").rstrip(".")


def parse_pair(text: str):
    parts = [p for p in re.split(r"[,;\s]+", text.strip()) if p]
    if len(parts) != 2:
        raise ValueError("Please enter exactly two numbers separated by a comma. Example: 2500, 10")
    values = [float(p.replace("%", "")) for p in parts]
    return values[0], values[1]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("pending", None)
    await update.message.reply_text(
        f"Welcome to {BOT_NAME}!\n\n"
        "Your everyday calculation assistant. Calculate percentages, discounts, "
        "commissions, additional earnings, salary totals, and more.\n\n"
        "Choose a tool below to get started.",
        reply_markup=MENU,
    )


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("pending", None)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "Choose a calculator to continue:", reply_markup=MENU
        )
    else:
        await update.message.reply_text("Choose a calculator to continue:", reply_markup=MENU)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "How to use BonusSpecialistaBot\n\n"
        "1. Choose a calculator from the menu.\n"
        "2. Enter the requested number or values.\n"
        "3. The bot will calculate and show your result.\n\n"
        "For two-value tools, enter the values separated by a comma, for example: 2500, 10.\n"
        "For the basic calculator, use an expression such as (120 + 30) * 2.\n\n"
        "Use /start to return to the main menu."
    )


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu":
        context.user_data.pop("pending", None)
        await query.edit_message_text("Choose a calculator to continue:", reply_markup=MENU)
        return
    if data == "help":
        await query.edit_message_text(
            "Choose a tool, enter the requested values, and receive your calculation.\n\n"
            "For two-value tools, enter values separated by a comma (example: 2500, 10).\n"
            "For the basic calculator, enter an expression (example: (120 + 30) * 2).",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main menu", callback_data="menu")]])
        )
        return
    if data == "units":
        context.user_data.pop("pending", None)
        await query.edit_message_text("Choose a conversion:", reply_markup=UNIT_MENU)
        return
    if data.startswith("unit:"):
        unit = data.split(":", 1)[1]
        context.user_data["pending"] = {"type": "unit", "unit": unit}
        prompts = {
            "km_mi": "Enter the distance in kilometres:",
            "mi_km": "Enter the distance in miles:",
            "kg_lb": "Enter the weight in kilograms:",
            "lb_kg": "Enter the weight in pounds:",
            "c_f": "Enter the temperature in Celsius:",
            "f_c": "Enter the temperature in Fahrenheit:",
            "l_gal": "Enter the volume in litres:",
            "gal_l": "Enter the volume in US gallons:",
        }
        await query.edit_message_text(
            prompts[unit],
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main menu", callback_data="menu")]])
        )
        return

    if data.startswith("tool:"):
        tool = data.split(":", 1)[1]
        context.user_data["pending"] = {"type": tool}
        prompts = {
            "basic": "Enter a maths expression. Example: (120 + 30) * 2",
            "percentage": "Enter the amount and percentage, separated by a comma. Example: 2500, 10",
            "discount": "Enter the original price and discount percentage. Example: 2500, 15",
            "commission": "Enter the sales amount and commission percentage. Example: 50000, 5",
            "bonus": "Enter the base amount and bonus percentage. Example: 40000, 12",
            "salary": "Enter your base salary and additional earnings, separated by a comma. Example: 50000, 7500",
        }
        await query.edit_message_text(
            prompts.get(tool, "Choose a calculator from the menu."),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main menu", callback_data="menu")]])
        )


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pending = context.user_data.get("pending")
    if not pending:
        await update.message.reply_text("Please choose a tool from the menu first.", reply_markup=MENU)
        return

    raw = update.message.text.strip()
    kind = pending["type"]
    try:
        if kind == "basic":
            result = safe_calculate(raw)
            response = f"🧮 Result: {fmt(result)}"
        elif kind == "percentage":
            amount, percent = parse_pair(raw)
            result = amount * percent / 100
            response = f"📊 {fmt(percent)}% of {fmt(amount)} = {fmt(result)}"
        elif kind == "discount":
            price, percent = parse_pair(raw)
            if price < 0 or not 0 <= percent <= 100:
                raise ValueError("Price must be non-negative and discount must be between 0 and 100.")
            saved = price * percent / 100
            response = (
                f"🏷 Discount: {fmt(saved)}\n"
                f"Final price: {fmt(price - saved)}"
            )
        elif kind in ("commission", "bonus"):
            amount, percent = parse_pair(raw)
            if amount < 0 or percent < 0:
                raise ValueError("Both values must be non-negative.")
            extra = amount * percent / 100
            label = "Commission" if kind == "commission" else "Bonus"
            response = f"📈 {label}: {fmt(extra)}\nTotal with {label.lower()}: {fmt(amount + extra)}"
        elif kind == "salary":
            base, extra = parse_pair(raw)
            if base < 0 or extra < 0:
                raise ValueError("Both values must be non-negative.")
            response = f"💵 Total earnings: {fmt(base + extra)}\nBase salary: {fmt(base)}\nAdditional earnings: {fmt(extra)}"
        elif kind == "unit":
            value = float(raw.replace(",", "."))
            unit = pending["unit"]
            conversions = {
                "km_mi": (value * 0.621371, "miles"),
                "mi_km": (value * 1.609344, "kilometres"),
                "kg_lb": (value * 2.2046226218, "pounds"),
                "lb_kg": (value / 2.2046226218, "kilograms"),
                "c_f": (value * 9 / 5 + 32, "°F"),
                "f_c": ((value - 32) * 5 / 9, "°C"),
                "l_gal": (value * 0.2641720524, "US gallons"),
                "gal_l": (value * 3.785411784, "litres"),
            }
            converted, label = conversions[unit]
            response = f"🔄 Result: {fmt(converted)} {label}"
        else:
            raise ValueError("Unknown calculator. Please choose a tool again.")
        context.user_data.pop("pending", None)
        await update.message.reply_text(
            response,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔁 Calculate again", callback_data=f"tool:{kind}" if kind != "unit" else f"unit:{pending['unit']}")],
                [InlineKeyboardButton("⬅️ Main menu", callback_data="menu")],
            ]),
        )
    except (ValueError, SyntaxError, ZeroDivisionError, OverflowError) as exc:
        await update.message.reply_text(
            f"Couldn't calculate that: {exc}\n\nPlease try again, or use /start to return to the menu."
        )


def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Set the BOT_TOKEN environment variable before starting the bot.")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    logger.info("%s is starting", BOT_NAME)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
