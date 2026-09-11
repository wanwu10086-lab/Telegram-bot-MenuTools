# -*- coding: utf-8 -*-
"""
菜单编辑工具 - 本地小网站服务器（阶段4）
职责：
1. 打开网页时，把 menu_editor.html 页面"端"给浏览器看
2. 你在网页点【保存】时，把新的菜单内容写进 menu.json 菜谱文件

这个服务器只在你自己电脑上运行（localhost），别人进不来。
运行命令：.venv\\Scripts\\python.exe menu_server.py
"""
import json
import os
import threading
import webbrowser  # 自动打开浏览器用的
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ---- 文件家目录 ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MENU_PATH = os.path.join(BASE_DIR, "menu.json")          # 菜谱文件
HTML_PATH = os.path.join(BASE_DIR, "menu_editor.html")   # 编辑页面文件

# 保存时先写"草稿文件"，全部写成功后再替换正式文件。
# 这样即使中途断电/出错，也不会把 menu.json 写坏（半截文件）。
TMP_PATH = os.path.join(BASE_DIR, "menu.json.tmp")

PORT = 1002  # 端口号（1002=菜单编辑器专属；1001 留给机器人做标识）


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

    # ---- 浏览器打开时调用的档口 ----
    def do_GET(self):
        if self.path == "/api/menu":
            # 前端进来时：把当前菜单内容发给它，用来"填"到输入框里
            self._send(200, json.dumps(read_menu(), ensure_ascii=False))
        else:
            # 其他请求：把编辑页面端给浏览器
            try:
                with open(HTML_PATH, "rb") as f:
                    html = f.read()
                self._send(200, html, "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(500, "未找到 menu_editor.html 文件", "text/plain; charset=utf-8")

    # ---- 点【保存】时调用的档口 ----
    def do_POST(self):
        if self.path != "/api/menu":
            self._send(404, "未知路径", "text/plain; charset=utf-8")
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            new_menu = json.loads(self.rfile.read(length).decode("utf-8"))
            # 只认这几个字段，防止塞进乱七八糟的东西
            assert isinstance(new_menu.get("welcome_text"), str)
            assert isinstance(new_menu.get("menu"), list)
            assert isinstance(new_menu.get("replies"), dict)
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
            import time
            time.sleep(60)
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()