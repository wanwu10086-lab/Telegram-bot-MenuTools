# -*- coding: utf-8 -*-
"""
量化助手 - 机器人大脑（阶段5）
会做的事：
1. 有人发 /start，回复欢迎语 + 菜单按钮（欢迎语可配图）
2. 有人按了按钮（等于发来一句按钮文字），根据按钮查"话术表"来回复（话术可配图）
3. 配图和话合在一条消息里发（话变成图片下方的小字说明）
4. 菜单和话术不再写死在代码里，而是每次启动时从"菜谱文件" menu.json 读取
   —— 以后改菜单 = 改 menu.json，不用碰代码。
"""
import os
import json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ---- 1. 找到"文件家目录"（程序自己所在的那个文件夹）----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(BASE_DIR, "images")  # 图片仓库文件夹

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

# ---- 4. 小工具：把话术统一成两件套 {文字, 图片} ----
def normalize_reply(value):
    """
    老格式的话术只是一句文字，新格式带图片。
    这个函数负责把两种格式都"翻译"成统一格式，后面统一处理。
    """
    if isinstance(value, str):
        return {"text": value, "image": ""}
    if isinstance(value, dict):
        return {
            "text": value.get("text") or "",
            "image": value.get("image") or "",
        }
    return {"text": "", "image": ""}


def image_file(filename):
    """如果图片在仓库里真实存在，返回它的完整路径；否则返回 None"""
    if not filename:
        return None
    # 只认文件名本身，防止奇怪路径跳出图片仓库
    path = os.path.join(IMAGES_DIR, os.path.basename(filename))
    return path if os.path.isfile(path) else None

# ---- 5. 发"话 + 图"的核心函数（欢迎语和按钮回复都靠它）----
async def send_text_and_image(update, text, image, reply_markup=None):
    """
    图和话合在一条消息里发出去：
      有图 = 图片 + 图下方的小字说明（一条消息，一次推送）
      没图 = 只发文字（一条消息）
    图片丢了就自动退回只发文字，不会死机。
    """
    path = image_file(image)
    if path:
        with open(path, "rb") as f:
            await update.message.reply_photo(photo=f, caption=text or None, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

# ---- 6. 处理 /start 命令的函数 ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """有人发 /start 时执行：摆出欢迎语（可配图） + 菜单按钮"""
    menu = load_menu()  # 开饭前先翻菜谱
    keyboard = ReplyKeyboardMarkup(menu["menu"], resize_keyboard=True)
    text = menu.get("welcome_text", "")
    image = menu.get("welcome_image", "")
    # 保险：欢迎语和图片都空了，就补一句默认话，防止菜单按钮发不出去
    if not text and not image_file(image):
        text = "你好，我是量化助手。"
    await send_text_and_image(update, text, image, reply_markup=keyboard)

# ---- 7. 处理普通文字消息的函数 ----
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """有人发来普通文字（包括按菜单按钮）时执行"""
    text = update.message.text
    menu = load_menu()  # 有人点菜，先翻菜谱，看这道菜（按钮）有没有对应的"话术"
    replies = menu.get("replies", {})
    if text in replies:
        reply = normalize_reply(replies[text])
        if not reply["text"] and not reply["image"]:
            # 两件套全是空的：提醒去编辑器补内容
            await update.message.reply_text("这个按钮还没填内容，请在菜单编辑器里补上。")
            return
        await send_text_and_image(update, reply["text"], reply["image"])
    else:
        # 不在话术表里：礼貌回复，引导去看菜单
        await update.message.reply_text("这条指令我还不认识。请点聊天框下方的菜单按钮试试。")

# ---- 8. 启动机器人的入口 ----
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