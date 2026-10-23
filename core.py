# -*- coding: utf-8 -*-
"""Núcleo (sem interface): scanner multi-thread + detecção de resíduos no Android."""
import os, re, time, heapq, shutil, queue, threading
from concurrent.futures import ThreadPoolExecutor

MB, GB = 1 << 20, 1 << 30


def fmt(n):
    for u, d in (("TB", 1 << 40), ("GB", GB), ("MB", MB), ("KB", 1024)):
        if n >= d:
            return f"{n / d:.1f} {u}".replace(".", ",")
    return f"{n} B"


def T(s):  # tracking editorial (letter-spacing) simulado
    return "\u2009".join(s.upper())


def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


# ───────────────────────── SCANNER (multi-thread, memória constante) ─────────────────────────
CATS = {
    "Vídeos": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".flv", ".m4v", ".ts"},
    "Imagens": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic", ".raw", ".psd", ".tif", ".tiff"},
    "Áudio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"},
    "Documentos": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".csv", ".epub"},
    "Compactados": {".zip", ".rar", ".7z", ".gz", ".tar", ".bz2", ".xz", ".cab"},
    "Discos e instaladores": {".iso", ".img", ".vhd", ".vhdx", ".vmdk", ".msi", ".msix", ".bin"},
    "Programas e bibliotecas": {".exe", ".dll", ".sys", ".so", ".pak", ".dat", ".bundle", ".asset", ".pck"},
    "Logs, dumps e temporários": {".tmp", ".log", ".dmp", ".etl", ".bak", ".old", ".chk", ".mdmp"},
}
EXT = {x: c for c, xs in CATS.items() for x in xs}


class Scanner:
    DEPTH = 5  # profundidade em que as pastas são registradas individualmente

    def __init__(s, root, workers=24):
        s.root, s.workers = root, workers
        s.q = queue.Queue()
        s.lock = threading.Lock()
        s.files = s.bytes = s.errors = 0
        s.cur, s.cancel = root, False
        s.direct, s.cat, s.top = {}, {}, []

    def work(s):
        direct, cat, top = {}, {}, []
        n = b = err = 0
        while True:
            it = s.q.get()
            try:
                if it is None:
                    break
                if s.cancel:
                    continue
                path, depth, bucket = it
                s.cur = path
                try:
                    es = os.scandir(path)
                except OSError:
                    err += 1
                    continue
                with es:
                    for e in es:
                        try:
                            st = e.stat(follow_symlinks=False)
                            a = getattr(st, "st_file_attributes", 0)
                            if e.is_dir(follow_symlinks=False):
                                if a & 0x400:  # junction/symlink: não seguir
                                    continue
                                d = depth + 1
                                s.q.put((e.path, d, e.path if d <= s.DEPTH else bucket))
                            elif e.is_file(follow_symlinks=False):
                                if a & 0x441000:  # arquivo só na nuvem/offline
                                    continue
                                sz = st.st_size
                                n += 1
                                b += sz
                                direct[bucket] = direct.get(bucket, 0) + sz
                                c = EXT.get(os.path.splitext(e.name)[1].lower(), "Outros")
                                v = cat.get(c, (0, 0))
                                cat[c] = (v[0] + sz, v[1] + 1)
                                if sz >= MB:
                                    if len(top) < 400:
                                        heapq.heappush(top, (sz, e.path, st.st_mtime))
                                    elif sz > top[0][0]:
                                        heapq.heapreplace(top, (sz, e.path, st.st_mtime))
                        except OSError:
                            err += 1
                with s.lock:
                    s.files += n; s.bytes += b; s.errors += err
                n = b = err = 0
            finally:
                s.q.task_done()
        with s.lock:
            for k, v in direct.items():
                s.direct[k] = s.direct.get(k, 0) + v
            for k, v in cat.items():
                o = s.cat.get(k, (0, 0))
                s.cat[k] = (o[0] + v[0], o[1] + v[1])
            s.top += top

    def run(s):
        ths = [threading.Thread(target=s.work, daemon=True) for _ in range(s.workers)]
        s.q.put((s.root, 0, s.root))
        for t in ths:
            t.start()
        s.q.join()
        for _ in ths:
            s.q.put(None)
        for t in ths:
            t.join()
        s.tot, s.kids = {}, {}
        for b, sz in s.direct.items():
            p = b
            while True:
                s.tot[p] = s.tot.get(p, 0) + sz
                par = os.path.dirname(p.rstrip("\\/")) or p
                if p == s.root or par == p:
                    break
                p = par
        for p in s.tot:
            if p != s.root:
                s.kids.setdefault(os.path.dirname(p.rstrip("\\/")) or s.root, []).append(p)
        s.top.sort(reverse=True)


def dirsize(p):
    try:
        if os.path.isfile(p):
            return os.path.getsize(p)
    except OSError:
        return 0
    t, st = 0, [p]
    while st:
        d = st.pop()
        try:
            with os.scandir(d) as es:
                for e in es:
                    try:
                        s_ = e.stat(follow_symlinks=False)
                        if e.is_dir(follow_symlinks=False):
                            if not getattr(s_, "st_file_attributes", 0) & 0x400:
                                st.append(e.path)
                        else:
                            t += s_.st_size
                    except OSError:
                        pass
        except OSError:
            pass
    return t


# ───────────────────────── RESÍDUOS (Android) ─────────────────────────
STD = {"dcim", "download", "downloads", "pictures", "movies", "music", "documents", "android", "alarms",
       "notifications", "ringtones", "podcasts", "audiobooks", "recordings", "screenshots", "data", "obb", "media",
       "lost.dir", "backups", "fonts", "themes"}
CACHEY = {"cache", ".cache", "temp", "tmp", ".temp", "logs", "log", ".trash", ".trashed", ".recycle", ".thumbnails", ".thumbs"}


def find_waste(root, pkgs, labels):
    items = []

    def add(path, risk, why, mode="dir", minsize=0, keep0=False):
        items.append(dict(path=path, risk=risk, why=why, mode=mode, size=0, min=minsize, keep0=keep0))

    names = {norm(x) for x in labels} | {norm(p) for p in pkgs} | {norm(p.split(".")[-1]) for p in pkgs}
    names.discard("")

    def known(d):
        n = norm(d)
        return len(n) < 3 or any(n in x or (len(x) >= 4 and x in n) for x in names)

    J = os.path.join
    try:
        for d in os.listdir(root):
            p = J(root, d)
            if not os.path.isdir(p):
                continue
            dl = d.lower()
            if dl in CACHEY:
                add(p, "SEGURO", "Cache / temporários na raiz do armazenamento")
            elif dl not in STD and not known(d):
                add(p, "REVISAR", "Pasta de app que não está mais instalado", minsize=1)
    except OSError:
        pass
    for sub in ("DCIM/.thumbnails", "Pictures/.thumbnails", "Android/.thumbnails", "Download/.thumbnails"):
        if os.path.isdir(J(root, sub)):
            add(J(root, sub), "SEGURO", "Miniaturas da galeria (recriadas sozinhas)")
    for base in ("Android/data", "Android/obb", "Android/media"):
        try:
            for d in os.listdir(J(root, base)):
                if "." in d and d not in pkgs:
                    add(J(root, base, d), "REVISAR", f"Resíduo de app desinstalado ({base})", minsize=1)
        except OSError:
            pass
    for d in ("Download", "Downloads"):
        try:
            for f in os.listdir(J(root, d)):
                if f.lower().endswith((".apk", ".apks", ".xapk")):
                    add(J(root, d, f), "REVISAR", "Instalador APK já baixado", "file")
        except OSError:
            pass
    st, n = [(root, 0)], 0  # pastas vazias (até 3 níveis)
    while st and n < 200:
        d, lv = st.pop()
        try:
            es = os.listdir(d)
        except OSError:
            continue
        if not es and lv > 0:
            add(d, "SEGURO", "Pasta vazia", keep0=True); n += 1
        if lv < 3:
            st += [(J(d, e), lv + 1) for e in es if os.path.isdir(J(d, e)) and not (lv == 0 and e.lower() == "android")]
    with ThreadPoolExecutor(8) as ex:
        for it, sz in zip(items, ex.map(lambda i: dirsize(i["path"]), items)):
            it["size"] = sz
    items = [i for i in items if i["size"] >= max(i["min"], 1) or i["keep0"]]
    items.sort(key=lambda i: ({"SEGURO": 0, "REVISAR": 1}[i["risk"]], -i["size"]))
    for i in items:
        i["on"] = i["risk"] == "SEGURO"
    return items


def remove(it, root):
    p = os.path.abspath(it["path"])
    if not p.startswith(os.path.abspath(root) + os.sep) or os.path.basename(p).lower() in STD:
        return False
    try:
        if os.path.isdir(p) and not os.path.islink(p):
            shutil.rmtree(p, ignore_errors=True)
        else:
            os.remove(p)
        return not os.path.exists(p)
    except OSError:
        return False
