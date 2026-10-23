# -*- coding: utf-8 -*-
"""AMAZON RIVER · DISK (Android) — interface no estilo Zeta Division."""
import os, time, shutil, threading
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, Ellipse, Quad
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.utils import platform, get_color_from_hex as hx
import core

BG, FG, MUTED, BORDER = hx("#FFFFFF"), hx("#111111"), hx("#777777"), hx("#E5E5E5")
Window.clearcolor = BG


class TL(Label):  # rótulo alinhado à esquerda, altura automática
    def __init__(s, text, size=12, bold=False, color=FG, **kw):
        super().__init__(text=text, markup=True, font_size=sp(size), bold=bold, color=color, halign="left",
                         valign="middle", size_hint_y=None, **kw)
        s.bind(width=lambda *_: setattr(s, "text_size", (s.width, None)))
        s.bind(texture_size=lambda *_: setattr(s, "height", max(s.texture_size[1], dp(14))))


class Flag(Widget):
    def __init__(s, kind, **kw):
        super().__init__(size_hint=(None, None), size=(dp(30), dp(21)), **kw)
        s.kind = kind
        s.bind(pos=s.draw, size=s.draw)

    def draw(s, *_):
        s.canvas.clear()
        x, y, w, h = *s.pos, *s.size
        with s.canvas:
            if s.kind == "am":  # Amazonas (simplificada)
                for i in range(7):
                    Color(*hx("#D5202C" if i % 2 == 0 else "#FFFFFF"))
                    Rectangle(pos=(x, y + h - (i + 1) * h / 7), size=(w, h / 7))
                Color(*hx("#0A2A8A")); Rectangle(pos=(x, y + h - 4 * h / 7), size=(w * .47, 4 * h / 7))
                Color(1, 1, 1, 1)
                for r in range(3):
                    for k in range(4):
                        Ellipse(pos=(x + dp(2) + k * dp(3.3), y + h - dp(4.2) - r * dp(3.6)), size=(dp(1.6), dp(1.6)))
                Ellipse(pos=(x + w * .2, y + h * .5), size=(dp(3.4), dp(3.4)))
            else:  # Brasil
                Color(*hx("#009C3B")); Rectangle(pos=s.pos, size=s.size)
                Color(*hx("#FFDF00")); Quad(points=[x + w / 2, y + h * .9, x + w * .93, y + h / 2, x + w / 2, y + h * .1, x + w * .07, y + h / 2])
                Color(*hx("#002776")); Ellipse(pos=(x + w * .33, y + h * .27), size=(w * .34, h * .46))


def hline():
    w = Widget(size_hint_y=None, height=1)
    with w.canvas:
        Color(*BORDER); r = Rectangle(pos=w.pos, size=w.size)
    w.bind(pos=lambda *_: setattr(r, "pos", w.pos), size=lambda *_: setattr(r, "size", w.size))
    return w


def button(text, cb, primary=True):
    b = Button(text=text.upper(), font_size=sp(11), bold=True, size_hint_y=None, height=dp(44), background_normal="",
               background_color=FG if primary else BG, color=BG if primary else FG)
    b.bind(on_release=lambda *_: cb())
    return b


def scroll():
    sv = ScrollView(do_scroll_x=False)
    g = GridLayout(cols=1, size_hint_y=None, spacing=dp(4))
    g.bind(minimum_height=g.setter("height"))
    sv.add_widget(g)
    return sv, g


class DiskApp(App):
    title = "Amazon River Disk"

    def build(s):
        s.root_dir = "/storage/emulated/0" if platform == "android" else os.path.expanduser("~")
        s.sc, s.waste, s.files, s.stack, s.scanning = None, [], [], [], False
        s.pkgs, s.labels = set(), set()
        L = BoxLayout(orientation="vertical", padding=(dp(16), dp(30), dp(16), dp(10)), spacing=dp(8))
        h = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        h.add_widget(Widget())
        h.add_widget(Image(source="logo.png", size_hint_x=None, width=dp(38)))
        h.add_widget(Label(text="AMAZON RIVER", font_size=sp(17), color=FG, size_hint_x=None, width=dp(140)))
        h.add_widget(Flag("am")); h.add_widget(Flag("br")); h.add_widget(Widget())
        L.add_widget(h)
        nav = BoxLayout(size_hint_y=None, height=dp(34))
        s.nav = {}
        for k, t in (("home", "VISÃO"), ("types", "TIPOS"), ("waste", "RESÍDUOS"), ("files", "MAIORES")):
            b = Button(text=t, font_size=sp(10), bold=True, background_normal="", background_color=BG, color=MUTED)
            b.bind(on_release=lambda _, k=k: s.show(k)); s.nav[k] = b; nav.add_widget(b)
        L.add_widget(nav); L.add_widget(hline())
        s.body = BoxLayout(orientation="vertical", spacing=dp(8))
        L.add_widget(s.body)
        s.show("home")
        Clock.schedule_once(lambda _: s.ensure_access(), 0.5)
        return L

    # ── permissões / apps instalados ────────────────────────────────────
    def ensure_access(s):
        if platform != "android":
            return True
        from jnius import autoclass
        Env, Ver = autoclass("android.os.Environment"), autoclass("android.os.Build$VERSION")
        if Ver.SDK_INT >= 30 and not Env.isExternalStorageManager():
            I, St, U = autoclass("android.content.Intent"), autoclass("android.provider.Settings"), autoclass("android.net.Uri")
            act = autoclass("org.kivy.android.PythonActivity").mActivity
            act.startActivity(I(St.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION, U.parse("package:" + act.getPackageName())))
            return False
        if Ver.SDK_INT < 30:
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])
        return True

    def load_apps(s):
        if platform != "android":
            return
        from jnius import autoclass
        pm = autoclass("org.kivy.android.PythonActivity").mActivity.getPackageManager()
        lst = pm.getInstalledPackages(0)
        for i in range(lst.size()):
            p = lst.get(i)
            s.pkgs.add(str(p.packageName))
            try:
                s.labels.add(str(pm.getApplicationLabel(p.applicationInfo)))
            except Exception:
                pass

    # ── páginas ─────────────────────────────────────────────────────────
    def show(s, k):
        s.page = k
        for n, b in s.nav.items():
            b.color = FG if n == k else MUTED
            b.text = ("[u]" + b.text.replace("[u]", "").replace("[/u]", "") + "[/u]") if n == k else b.text.replace("[u]", "").replace("[/u]", "")
            b.markup = True
        s.body.clear_widgets()
        getattr(s, "pg_" + k)()

    def pg_home(s):
        b = s.body
        b.add_widget(TL("DISCO", 9, color=MUTED))
        u = shutil.disk_usage(s.root_dir)
        b.add_widget(TL(f"[b]{core.fmt(u.total)}[/b]", 26))
        g = GridLayout(cols=2, size_hint_y=None, height=dp(120), spacing=dp(4))
        s.stat = {}
        for k, t, v in (("used", "USADO", core.fmt(u.used)), ("free", "LIVRE", core.fmt(u.free)),
                        ("safe", "LIMPEZA SEGURA", s.sum("SEGURO")), ("rev", "A REVISAR", s.sum("REVISAR"))):
            c = BoxLayout(orientation="vertical"); lb = TL(f"[b]{v}[/b]", 17); s.stat[k] = lb
            c.add_widget(lb); c.add_widget(TL(t, 8, color=MUTED)); g.add_widget(c)
        b.add_widget(g)
        bar = Widget(size_hint_y=None, height=dp(6))
        with bar.canvas:
            Color(*BORDER); r1 = Rectangle(pos=bar.pos, size=bar.size)
            Color(*FG); r2 = Rectangle(pos=bar.pos, size=(0, 0))

        def lay(*_):
            r1.pos = r2.pos = bar.pos; r1.size = bar.size; r2.size = (bar.width * u.used / u.total, bar.height)
        bar.bind(pos=lay, size=lay); b.add_widget(bar)
        s.btn_scan = button("Analisar armazenamento", s.start); b.add_widget(s.btn_scan)
        s.status = TL(getattr(s, "msg", ""), 9, color=MUTED); b.add_widget(s.status)
        s.nav_lbl = TL("ONDE ESTÁ O ESPAÇO", 9, color=MUTED); b.add_widget(s.nav_lbl)
        sv, s.grid = scroll(); b.add_widget(sv)
        if s.sc and hasattr(s.sc, "tot"):
            s.folder(s.stack[-1] if s.stack else s.sc.root)

    def sum(s, risk):
        return core.fmt(sum(i["size"] for i in s.waste if i["risk"] == risk))

    def folder(s, path):
        c, g = s.sc, s.grid
        g.clear_widgets()
        tot = max(c.tot.get(c.root, 1), 1)
        if path != c.root:
            bk = button("‹ voltar", s.up, False); g.add_widget(bk)
        for k in sorted(c.kids.get(path, []), key=lambda x: -c.tot[x])[:80]:
            r = Button(text=f"{os.path.basename(k)}\n[size=10sp][color=777777]{core.fmt(c.tot[k])} · {c.tot[k] * 100 / tot:.1f}%[/color][/size]",
                       markup=True, size_hint_y=None, height=dp(56), halign="left", background_normal="",
                       background_color=BG, color=FG, font_size=sp(13))
            r.bind(size=lambda w, _: setattr(w, "text_size", (w.width - dp(8), None)))
            r.bind(on_release=lambda _, k=k: s.enter(k)); g.add_widget(r)

    def enter(s, k):
        s.stack.append(k); s.folder(k)

    def up(s):
        if s.stack:
            s.stack.pop()
        s.folder(s.stack[-1] if s.stack else s.sc.root)

    def pg_types(s):
        sv, g = scroll(); s.body.add_widget(TL("DISTRIBUIÇÃO", 9, color=MUTED)); s.body.add_widget(sv)
        if not (s.sc and hasattr(s.sc, "tot")):
            return g.add_widget(TL("Analise o armazenamento primeiro.", 12, color=MUTED))
        rows = sorted(s.sc.cat.items(), key=lambda x: -x[1][0]); mx = max([v[0] for _, v in rows] or [1])
        for k, (sz, n) in rows:
            g.add_widget(TL(f"[b]{k.upper()}[/b]   {core.fmt(sz)} · {n:,} arq.".replace(",", "."), 11))
            bar = Widget(size_hint_y=None, height=dp(6))
            with bar.canvas:
                Color(*BORDER); a = Rectangle(pos=bar.pos, size=bar.size); Color(*FG); b2 = Rectangle(pos=bar.pos, size=(0, 0))
            bar.bind(pos=lambda w, _, a=a, b2=b2: (setattr(a, "pos", w.pos), setattr(b2, "pos", w.pos)),
                     size=lambda w, _, a=a, b2=b2, f=sz / mx: (setattr(a, "size", w.size), setattr(b2, "size", (w.width * f, w.height))))
            g.add_widget(bar); g.add_widget(Widget(size_hint_y=None, height=dp(8)))

    def pg_waste(s):
        s.body.add_widget(TL("LIMPEZA", 9, color=MUTED)); s.body.add_widget(TL("[b]Resíduos e itens inúteis[/b]", 20))
        sv, g = scroll(); s.body.add_widget(sv)
        s.sumlb = TL("", 10, color=MUTED); s.body.add_widget(s.sumlb)
        s.body.add_widget(button("Excluir selecionados", lambda: s.confirm(s.waste)))
        s.rows(g, s.waste, "Analise o armazenamento para listar resíduos.")

    def pg_files(s):
        s.body.add_widget(TL("ARQUIVOS", 9, color=MUTED)); s.body.add_widget(TL("[b]Maiores arquivos[/b]", 20))
        sv, g = scroll(); s.body.add_widget(sv)
        s.sumlb = TL("", 10, color=MUTED); s.body.add_widget(s.sumlb)
        s.body.add_widget(button("Excluir selecionados", lambda: s.confirm(s.files)))
        s.rows(g, s.files, "Analise o armazenamento para listar arquivos.")

    def rows(s, g, items, empty):
        if not items:
            g.add_widget(TL(empty, 12, color=MUTED))
        for it in items:
            r = BoxLayout(size_hint_y=None, height=dp(64), spacing=dp(6))
            cb = CheckBox(active=it.get("on", False), size_hint_x=None, width=dp(36), color=FG)
            cb.bind(active=lambda w, v, it=it: (it.__setitem__("on", v), s.sumw()))
            mid = BoxLayout(orientation="vertical")
            mid.add_widget(TL(f"[b]{os.path.basename(it['path'])}[/b]", 12))
            mid.add_widget(TL(it["why"], 9, color=MUTED))
            r.add_widget(cb); r.add_widget(mid)
            r.add_widget(Label(text=core.fmt(it["size"]), font_size=sp(11), color=FG, size_hint_x=None, width=dp(70)))
            g.add_widget(r)
        s.cur_items = items; s.sumw()

    def sumw(s):
        if hasattr(s, "sumlb") and s.sumlb.parent:
            s.sumlb.text = "Selecionado: " + core.fmt(sum(i["size"] for i in s.cur_items if i.get("on")))

    # ── análise ─────────────────────────────────────────────────────────
    def start(s):
        if s.scanning:
            return
        if not s.ensure_access():
            s.status.text = "Autorize “Acesso a todos os arquivos” e toque em analisar de novo."
            return
        s.scanning, s.t0, s.stack = True, time.time(), []
        s.sc = core.Scanner(s.root_dir, workers=8); s.sc.DEPTH = 6
        s.waste, s.files = [], []
        s.tick = Clock.schedule_interval(s.progress, 0.4)
        threading.Thread(target=s.job, daemon=True).start()

    def progress(s, *_):
        if s.page == "home" and s.scanning:
            s.status.text = f"{s.sc.files:,} arquivos · {core.fmt(s.sc.bytes)} · {time.time() - s.t0:.0f}s".replace(",", ".")

    def job(s):
        sc = s.sc
        sc.run()
        s.load_apps()
        w = core.find_waste(s.root_dir, s.pkgs, s.labels)
        f = [dict(path=p, size=z, risk="REVISAR", why=time.strftime("Modificado em %d/%m/%Y", time.localtime(m)), mode="file", on=False)
             for z, p, m in sc.top]
        Clock.schedule_once(lambda _: s.finish(w, f))

    def finish(s, w, f):
        s.tick.cancel(); s.scanning = False; s.waste, s.files = w, f
        s.msg = f"Concluído em {time.time() - s.t0:.0f}s · {s.sc.files:,} arquivos · {s.sc.errors:,} sem acesso".replace(",", ".")
        s.show("home")

    # ── exclusão ────────────────────────────────────────────────────────
    def confirm(s, items):
        sel = [i for i in items if i.get("on")]
        if not sel:
            return
        tot = core.fmt(sum(i["size"] for i in sel))
        box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        box.add_widget(TL(f"Excluir {len(sel)} item(ns) — até {tot}?\n\nNo Android não existe Lixeira: a exclusão é DEFINITIVA.", 12))
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        pop = Popup(title="Confirmar", content=box, size_hint=(.9, .45), auto_dismiss=False)
        row.add_widget(button("Cancelar", pop.dismiss, False))
        row.add_widget(button("Excluir", lambda: (pop.dismiss(), s.run_delete(items, sel))))
        box.add_widget(row); pop.open()

    def run_delete(s, items, sel):
        def job():
            freed = 0
            for i in sel:
                if core.remove(i, s.root_dir):
                    freed += i["size"]; i["size"] = 0; i["gone"] = True
            for lst in (s.waste, s.files):
                lst[:] = [x for x in lst if not x.get("gone")]
            Clock.schedule_once(lambda _: (setattr(s, "msg", "Liberado: " + core.fmt(freed)), s.show(s.page)))
        threading.Thread(target=job, daemon=True).start()


if __name__ == "__main__":
    DiskApp().run()
