# -*- coding: utf-8 -*-
"""
菜单编辑工具 - 本地小网站服务器（阶段5）
职责：
1. 打开网页时，把 menu_editor.html 页面"端"给浏览器看
2. 你在网页点【保存】时，把新的菜单内容写进 menu.json 菜谱文件
3. 你在网页上传图片时，把图片存进 images 文件夹（图片仓库）
4. 浏览器要显示图片缩略图时，把图片"端"给它看

这个服务器只在你自己电脑上运行（localhost），别人进不来。
运行命令：.venv\\Scripts\\python.exe menu_server.py
"""
import json
import os
import random
import threading
import time
import urllib.parse
import webbrowser  # 自动打开浏览器用的
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ---- 文件家目录 ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MENU_PATH = os.path.join(BASE_DIR, "menu.json")          # 菜谱文件
HTML_PATH = os.path.join(BASE_DIR, "menu_editor.html")   # 编辑页面文件
IMAGES_DIR = os.path.join(BASE_DIR, "images")            # 图片仓库文件夹

# 保存时先写"草稿文件"，全部写成功后再替换正式文件。
# 这样即使中途断电/出错，也不会把 menu.json 写坏（半截文件）。
TMP_PATH = os.path.join(BASE_DIR, "menu.json.tmp")

PORT = 1002  # 端口号（1002=菜单编辑器专属；1001 留给机器人做标识）

# ---- 图片的规矩 ----
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}  # 只准这几种格式
MIME_MAP = {                                              # 端图给浏览器时"报名"用
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif",
}
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 单张图最多 10MB（Telegram 的规矩）


def read_menu():
    """读出菜单内容，返回一个字典；文件坏了就返回空结构"""
    try:
        with open(MENU_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {"welcome_text": "", "menu": [], "replies": {}}


class Handler(BaseHTTPRequestHandler):
    # ---- 让浏览器正常识别中文 ----
    def _send(self, code, body, content_type="application/json; charset=utf-8"):
        body = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ---- 浏览器要东西时走的档口 ----
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        # 档口1：把当前菜单内容发给网页（填输入框用）
        if parsed.path == "/api/menu":
            self._send(200, json.dumps(read_menu(), ensure_ascii=False))
            return
        # 档口2：把图片仓库里的图端给浏览器（显示缩略图用）
        if parsed.path.startswith("/api/image/"):
            filename = urllib.parse.unquote(parsed.path.split("/api/image/", 1)[1])
            filename = os.path.basename(filename)  # 只认文件名本身，防止跑到别的文件夹
            if not filename:
                self._send(404, "没给图片名", "text/plain; charset=utf-8")
                return
            file_path = os.path.join(IMAGES_DIR, filename)
            if not os.path.isfile(file_path):
                self._send(404, "图片不存在", "text/plain; charset=utf-8")
                return
            content_type = MIME_MAP.get(os.path.splitext(filename)[1].lower(), "application/octet-stream")
            with open(file_path, "rb") as f:
                self._send(200, f.read(), content_type)
            return
        # 其他请求：把编辑页面端给浏览器
        try:
            with open(HTML_PATH, "rb") as f:
                html = f.read()
            self._send(200, html, "text/html; charset=utf-8")
        except FileNotFoundError:
            self._send(500, "未找到 menu_editor.html 文件", "text/plain; charset=utf-8")

    # ---- 浏览器"送货上门"时走的档口 ----
    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        # 档口A：收图片（网页上传图片用）
        if parsed.path == "/api/upload":
            self._handle_upload(parsed)
            return
        # 档口B：保存菜单
        if parsed.path == "/api/menu":
            self._handle_save_menu()
            return
        self._send(404, "未知路径", "text/plain; charset=utf-8")

    # ---- 收图片：检查格式、大小，存进图片仓库 ----
    def _handle_upload(self, parsed):
        query = urllib.parse.parse_qs(parsed.query)
        original_name = query.get("name", [""])[0]
        ext = os.path.splitext(original_name)[1].lower()
        if ext not in ALLOWED_EXT:
            self._send(400, "只支持 jpg / jpeg / png / webp / gif 格式的图片", "text/plain; charset=utf-8")
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            self._send(400, "上传内容有误", "text/plain; charset=utf-8")
            return
        if length <= 0:
            self._send(400, "没有收到图片内容", "text/plain; charset=utf-8")
            return
        if length > MAX_IMAGE_BYTES:
            self._send(413, "图片超过 10MB，请换一张小一点的", "text/plain; charset=utf-8")
            return
        data = self.rfile.read(length)
        os.makedirs(IMAGES_DIR, exist_ok=True)  # 仓库不存在就建一个
        # 自动起不重名的文件名：时间戳 + 随机数（不用原文件名，防止中文名和重名出乱子）
        filename = "img_{}_{}{}".format(int(time.time()), random.randint(1000, 9999), ext)
        with open(os.path.join(IMAGES_DIR, filename), "wb") as f:
            f.write(data)
        self._send(200, json.dumps({"filename": filename}, ensure_ascii=False))

    # ---- 保存菜单：检查格式对不对劲，然后写进菜谱文件 ----
    def _handle_save_menu(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            new_menu = json.loads(self.rfile.read(length).decode("utf-8"))
            # 只认这几个字段，防止塞进乱七八糟的东西
            assert isinstance(new_menu.get("welcome_text"), str)
            assert isinstance(new_menu.get("welcome_image", ""), str)
            assert isinstance(new_menu.get("menu"), list)
            replies = new_menu.get("replies")
            assert isinstance(replies, dict)
            for value in replies.values():
                if isinstance(value, str):
                    continue  # 老格式（纯文字）也放行
                assert isinstance(value, dict)
                assert isinstance(value.get("text", ""), str)
                assert isinstance(value.get("image", ""), str)
        except Exception:
            self._send(400, "保存失败：菜单数据格式不对", "text/plain; charset=utf-8")
            return
        # 先写草稿，再替换正式文件（防止写坏）
        with open(TMP_PATH, "w", encoding="utf-8") as f:
            json.dump(new_menu, f, ensure_ascii=False, indent=4)
        os.replace(TMP_PATH, MENU_PATH)
        self._send(200, "ok")

    def log_message(self, *args):
        pass  # 不刷屏，保持安静


def main():
    os.makedirs(IMAGES_DIR, exist_ok=True)  # 启动时确保图片仓库存在
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    # 用一个小线程守护服务器，主线程就开着（这样关闭窗口=停止）
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"菜单编辑器已启动: http://127.0.0.1:{PORT}/")
    # 服务器就绪后，自动帮用户打开浏览器
    try:
        webbrowser.open(f"http://127.0.0.1:{PORT}/")
    except Exception:
        print("自动打开浏览器失败，请手动复制上面的网址到浏览器访问")
    print("按 Ctrl+C 停止本工具")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()