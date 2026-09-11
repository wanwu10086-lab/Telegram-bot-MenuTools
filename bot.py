# -*- coding: utf-8 -*-
"""
量化助手 - 机器人大脑（阶段3）
会做的事：
1. 有人发 /start，回复欢迎语 + 菜单按钮
2. 有人按了按钮（等于发来一句按钮文字），根据按钮查"话术表"来回复
3. 菜单和话术不再写死在代码里，而是每次启动时从"菜谱文件" menu.json 读取
   —— 以后改菜单 = 改 menu.json，不用碰代码。
"""
import os
import json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ---- 1. 找到"文件家目录"（程序自己所在的那个文件夹）----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---- 2. 从钥匙盒(.env)里读出 Token ----
def read_token():
    """打开 .env 文件，找到 BOT_TOKEN= 那一行，把钥匙取出来"""
    env_path = os.path.join(BASE_DIR, ".env")
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("BOT_TOKEN="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("没在 .env 里找到 BOT_TOKEN，请检查钥匙盒文件")

# ---- 3. 读"菜谱文件" menu.json ----
def load_menu():
    """把菜单、欢迎语、话术表从 menu.json 读进来，装进一个大箱子里（字典）"""
    menu_path = os.path.join(BASE_DIR, "menu.json")
    with open(menu_path, "r", encoding="utf-8") as f:
        return json.load(f)

# ---- 4. 处理 /start 命令的函数 ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """有人发 /start 时执行：摆出欢迎语 + 菜单按钮"""
    menu = load_menu()  # 开饭前先翻菜谱
    keyboard = ReplyKeyboardMarkup(menu["menu"], resize_keyboard=True)
    await update.message.reply_text(menu["welcome_text"], reply_markup=keyboard)

# ---- 5. 处理普通文字消息的函数 ----
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """有人发来普通文字（包括按菜单按钮）时执行"""
    text = update.message.text
    menu = load_menu()  # 有人点菜，先翻菜谱，看这道菜（按钮）有没有对应的"话术"
    replies = menu["replies"]
    if text in replies:
        await update.message.reply_text(replies[text])
    else:
        # 不在话术表里：礼貌回复，引导去看菜单
        await update.message.reply_text("这条指令我还不认识。请点聊天框下方的菜单按钮试试。")

# ---- 6. 启动机器人的入口 ----
def main():
    app = (
        Application.builder()
        .token(read_token())                    # 出示钥匙
        .proxy("http://127.0.0.1:7890")         # 走 Clash 特殊通道上网
        .build()
    )
    app.add_handler(CommandHandler("start", start))  # 登记：/start 命令交给 start 函数处理
    # 登记：所有"普通文字消息"（不是命令、不是按钮之外的东西）交给 handle_text 处理
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("量化助手已启动，等待消息中...（按 Ctrl+C 停止）")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()