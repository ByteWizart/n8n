#!/usr/bin/env python3
"""Gerador de video curto 2D (bonequinho de graveto + icones), 100% gratuito.
Uso: python3 render.py <pasta>   (a pasta precisa ter voice.mp3 e cenas.json)
Saida: <pasta>/video.mp4  (1080x1920, 30 fps, do tamanho da narracao)
"""
import json, math, os, re, subprocess, sys, wave, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
SS = int(os.environ.get("SS", "2"))
SR = 44100

INK = (30, 34, 51)
WHITE = (255, 253, 246)
PINK = (244, 166, 190)
PINK_D = (230, 138, 168)
CAV0 = (252, 218, 230)
CAV1 = (190, 222, 255)
RED = (229, 56, 79)
GREY = (150, 156, 172)
BLUE = (45, 127, 249)
PURP = (155, 111, 208)

def ss(a, b, t):
    x = min(1, max(0, (t - a) / (b - a)))
    return x * x * (3 - 2 * x)

def back(x, s=1.7):
    x = min(1, max(0, x))
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2

def lerp(a, b, k):
    return a + (b - a) * k

def lerpc(c1, c2, k):
    return tuple(lerp(c1[i], c2[i], k) for i in range(3))


# ---------- canvas ----------
def ci(col):
    return None if col is None else tuple(int(round(v)) for v in col)

class Cv:
    def __init__(s, bg):
        s.im = Image.new('RGB', (W * SS, H * SS), tuple(int(v) for v in bg))
        s.d = ImageDraw.Draw(s.im)

    def circ(s, x, y, r, fill=None, outline=None, w=0):
        s.d.ellipse([(x - r) * SS, (y - r) * SS, (x + r) * SS, (y + r) * SS], fill=ci(fill), outline=ci(outline), width=max(1, int(w * SS)) if outline else 0)

    def ell(s, x, y, rx, ry, fill):
        s.d.ellipse([(x - rx) * SS, (y - ry) * SS, (x + rx) * SS, (y + ry) * SS], fill=ci(fill))

    def ello(s, x, y, rx, ry, fill, w=8):
        s.ell(x, y, rx + w / 2, ry + w / 2, INK)
        s.ell(x, y, rx - w / 2, ry - w / 2, fill)

    def line(s, pts, w, col=INK):
        P = [(x * SS, y * SS) for x, y in pts]
        s.d.line(P, fill=ci(col), width=max(1, int(w * SS)))
        r = w / 2
        for x, y in pts:
            s.circ(x, y, r, fill=col)

    def poly(s, pts, fill):
        s.d.polygon([(x * SS, y * SS) for x, y in pts], fill=ci(fill))

def heart_pts(x, y, size):
    pts = []
    for i in range(48):
        t = i / 48 * 2 * math.pi
        hx = 16 * math.sin(t) ** 3
        hy = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((x + hx * size / 17, y + (hy + 2) * size / 17))
    return pts

def heart(c, x, y, size, fill):
    if size < 1:
        return
    c.poly(heart_pts(x, y, size * 1.22), INK)
    c.poly(heart_pts(x, y, size), fill)
    # brilho
    c.circ(x - size * 0.45, y - size * 0.35, size * 0.13, fill=(255, 255, 255))

def sparkle(c, x, y, r, col=(255, 200, 40)):
    if r < 1:
        return
    pts = []
    for i in range(8):
        a = i * math.pi / 4
        rr = r if i % 2 == 0 else r * 0.28
        pts.append((x + rr * math.sin(a), y - rr * math.cos(a)))
    c.poly(pts, col)

def qmark(c, x, y, k):
    if k < 0.02:
        return
    r = 50 * k
    pts = []
    for i in range(0, 17):
        a = math.radians(200 + i * (250 / 16))
        pts.append((x + r * math.cos(a), y - r * 0.2 + r * math.sin(a)))
    pts += [(x + r * 0.05, y + r * 1.15)]
    c.line(pts, 15 * k, INK)
    c.circ(x + r * 0.05, y + r * 1.95, 9 * k, fill=INK)

# ---------- stick figure ----------
def rot(px, py, a):
    return px * math.cos(a) - py * math.sin(a), px * math.sin(a) + py * math.cos(a)

def figure(c, x, y, h, t, pose, eyes, mouth_open, sweat=False, hop=0.0):
    s = h / 410.0
    bob = 3 * math.sin(t * 5) * s
    ox, oy = x, y - hop * s

    def T(px, py, bobbed=True):
        return ox + px * s, oy + py * s + (bob if bobbed else 0)

    lw = 12 * s
    hip = T(0, -150)
    sh = T(0, -290)
    # legs
    c.line([hip, T(-20, -78), T(-42, 0, False)], lw)
    c.line([hip, T(20, -78), T(42, 0, False)], lw)
    c.line([T(-42, 0, False), T(-62, 0, False)], lw)
    c.line([T(42, 0, False), T(62, 0, False)], lw)
    # corpo
    c.line([hip, sh], lw)
    # braços
    Ra1, Ra2, La1, La2, tilt = pose
    for a1, a2 in ((Ra1, Ra2), (La1, La2)):
        a1r, a2r = math.radians(a1), math.radians(a2)
        e = (sh[0] + math.sin(a1r) * 78 * s, sh[1] + math.cos(a1r) * 78 * s)
        hnd = (e[0] + math.sin(a2r) * 72 * s, e[1] + math.cos(a2r) * 72 * s)
        c.line([sh, e, hnd], lw)
        c.circ(hnd[0], hnd[1], 7 * s, fill=INK)
    # cabeça
    neck = T(0, -298)
    hc_local = rot(0, -62, tilt)
    hc = (neck[0] + hc_local[0] * s, neck[1] + hc_local[1] * s)
    R = 56 * s

    def HP(dx, dy):
        px, py = rot(dx, dy, tilt)
        return hc[0] + px * s, hc[1] + py * s

    c.circ(hc[0], hc[1], R + 5 * s, fill=INK)
    c.circ(hc[0], hc[1], R - 2 * s, fill=WHITE)
    # olhos
    for sx in (-1, 1):
        ex, ey = HP(sx * 21, -6)
        if eyes == 'dot':
            c.circ(ex, ey, 6.5 * s, fill=INK)
        elif eyes == 'wide':
            c.circ(ex, ey, 14 * s, fill=INK)
            c.circ(ex, ey, 11 * s, fill=WHITE)
            c.circ(ex, ey, 4.5 * s, fill=INK)
            b0 = HP(sx * 21 - 13, -30)
            b1 = HP(sx * 21 + 13, -34 if sx > 0 else -34)
            c.line([b0, b1], 5 * s)
        elif eyes == 'happy':
            pts = [HP(sx * 21 + k, -4 - 9 * math.sin(math.pi * (k + 11) / 22)) for k in range(-11, 12, 4)]
            c.line(pts, 5 * s)
        elif eyes == 'blink':
            c.line([HP(sx * 21 - 9, -6), HP(sx * 21 + 9, -6)], 5 * s)
        elif eyes == 'wink':
            if sx < 0:
                c.circ(ex, ey, 6.5 * s, fill=INK)
            else:
                pts = [HP(sx * 21 + k, -4 - 9 * math.sin(math.pi * (k + 11) / 22)) for k in range(-11, 12, 4)]
                c.line(pts, 5 * s)
    # bochechas
    for sx in (-1, 1):
        bx, by = HP(sx * 36, 12)
        c.circ(bx, by, 8 * s, fill=(246, 190, 190))
    # boca
    mx, my = HP(0, 24)
    if mouth_open > 0.12:
        c.ell(mx, my, (11 + 5 * mouth_open) * s, (4 + 15 * mouth_open) * s, INK)
        c.ell(mx, my + (5 + 6 * mouth_open) * s, 7 * s, (3 + 5 * mouth_open) * s, (232, 110, 120))
    else:
        pts = [HP(k, 22 + 6 * (1 - (k / 16) ** 2)) for k in range(-16, 17, 4)]
        c.line(pts, 5 * s)
    if sweat:
        sx_, sy_ = HP(52, -34)
        c.circ(sx_, sy_ + 6 * s, 9 * s, fill=(120, 190, 255))
        c.poly([(sx_, sy_ - 20 * s), (sx_ - 8 * s, sy_ + 2 * s), (sx_ + 8 * s, sy_ + 2 * s)], (120, 190, 255))
    return hc



# ---------- fonte ----------
def get_font(px):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/Library/Fonts/Arial Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, int(px))
    return ImageFont.load_default()

YEL = (255, 205, 60)
ORG = (255, 140, 60)
GREEN = (96, 190, 120)
LBLUE = (110, 175, 245)

# ---------- icones (todos desenhados em codigo) ----------
def blob_outline(c, pts, fill, w=9):
    c.poly(pts, fill)
    c.line(pts + [pts[0]], w, INK)

def ic_coracao(c, x, y, r, t, bg, k):
    pulse = 1 + 0.10 * max(0, math.sin(t * 7)) ** 2
    heart(c, x, y, r * 0.95 * pulse, RED)

def ic_estrela(c, x, y, r, t, bg, k):
    pts = []
    for i in range(10):
        a = math.radians(i * 36 + t * 40)
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((x + rr * math.sin(a), y - rr * math.cos(a)))
    blob_outline(c, pts, YEL)

def ic_sol(c, x, y, r, t, bg, k):
    for i in range(12):
        a = math.radians(i * 30 + t * 25)
        c.line([(x + math.cos(a) * r * 0.78, y + math.sin(a) * r * 0.78), (x + math.cos(a) * r * 1.1, y + math.sin(a) * r * 1.1)], 16, ORG)
    c.circ(x, y, r * 0.7 + 5, fill=INK)
    c.circ(x, y, r * 0.7, fill=YEL)
    for sx in (-1, 1):
        c.circ(x + sx * r * 0.22, y - r * 0.08, r * 0.06, fill=INK)
    c.line([(x + k_ * r * 0.3, y + r * 0.2 + (1 - (k_ / 1.0) ** 2) * r * 0.1) for k_ in (-1, -0.5, 0, 0.5, 1)], 7, INK)

def ic_lua(c, x, y, r, t, bg, k):
    R, rr, d = r * 0.95, r * 0.78, r * 0.55
    xi = (R * R - rr * rr + d * d) / (2 * d)
    yi = math.sqrt(max(0, R * R - xi * xi))
    a1 = math.atan2(yi, xi)
    b1 = math.atan2(yi, xi - d)
    pts = []
    for i in range(0, 41):
        a = a1 + (2 * math.pi - 2 * a1) * i / 40
        pts.append((x + R * math.cos(a) - d * 0.3, y + R * math.sin(a)))
    for i in range(0, 41):
        a = (2 * math.pi - b1) - (2 * math.pi - 2 * b1) * i / 40
        pts.append((x + d + rr * math.cos(a) - d * 0.3, y + rr * math.sin(a)))
    blob_outline(c, pts, (255, 232, 140))
    for j in range(3):
        sparkle(c, x + r * (0.9 + 0.2 * j), y - r * (0.7 - 0.5 * j), 22 + 8 * math.sin(t * 5 + j), YEL)

def ic_terra(c, x, y, r, t, bg, k):
    c.circ(x, y, r * 0.9 + 6, fill=INK)
    c.circ(x, y, r * 0.9, fill=LBLUE)
    for i, (ox, oy, rx, ry) in enumerate([(-0.35, -0.25, 0.32, 0.22), (0.3, 0.1, 0.28, 0.34), (-0.15, 0.45, 0.22, 0.15)]):
        sh = math.sin(t * 0.8 + i * 2) * 0.12
        px, py = ox + sh, oy
        if math.hypot(px, py) < 0.55:
            c.ell(x + px * r, y + py * r, rx * r, ry * r, GREEN)

def ic_gota(c, x, y, r, t, bg, k):
    rr = r * 0.62
    cy = y + r * 0.18
    c.poly([(x, cy - rr * 2.0), (x - rr * 0.86, cy - rr * 0.35), (x + rr * 0.86, cy - rr * 0.35)], INK)
    c.circ(x, cy, rr * 1.08, fill=INK)
    c.poly([(x, cy - rr * 1.8), (x - rr * 0.76, cy - rr * 0.35), (x + rr * 0.76, cy - rr * 0.35)], BLUE)
    c.circ(x, cy, rr, fill=BLUE)
    c.circ(x - rr * 0.38, cy - rr * 0.1, rr * 0.18, fill=(255, 255, 255))

def ic_raio(c, x, y, r, t, bg, k):
    P = [(0.12, -1.0), (-0.55, 0.12), (-0.06, 0.12), (-0.28, 1.0), (0.55, -0.22), (0.06, -0.22), (0.12, -1.0)]
    pts = [(x + px * r, y + py * r) for px, py in P]
    blob_outline(c, pts, YEL if int(t * 6) % 2 == 0 else (255, 235, 120))

def ic_relogio(c, x, y, r, t, bg, k):
    c.circ(x, y, r * 0.85 + 7, fill=INK)
    c.circ(x, y, r * 0.85, fill=WHITE)
    for i in range(12):
        a = math.radians(i * 30)
        c.line([(x + math.sin(a) * r * 0.68, y - math.cos(a) * r * 0.68), (x + math.sin(a) * r * 0.78, y - math.cos(a) * r * 0.78)], 8, INK)
    am = t * 2.0
    ah = am / 12
    c.line([(x, y), (x + math.sin(am) * r * 0.62, y - math.cos(am) * r * 0.62)], 9, INK)
    c.line([(x, y), (x + math.sin(ah) * r * 0.42, y - math.cos(ah) * r * 0.42)], 13, INK)
    c.circ(x, y, 10, fill=RED)

def ic_cerebro(c, x, y, r, t, bg, k):
    spots = [(-0.45, -0.1, 0.42), (0.0, -0.3, 0.48), (0.45, -0.1, 0.42), (-0.25, 0.25, 0.4), (0.25, 0.25, 0.4)]
    for sx, sy, sr in spots:
        c.circ(x + sx * r, y + sy * r, (sr * r) + 6, fill=INK)
    for sx, sy, sr in spots:
        c.circ(x + sx * r, y + sy * r, sr * r, fill=(247, 170, 195))
    pts = [(x + math.sin(i * 0.9 + t * 3) * r * 0.08 + (i - 4) * r * 0.1, y - r * 0.3 + i * r * 0.09) for i in range(8)]
    c.line(pts, 6, (205, 110, 140))
    for sx in (-1, 1):
        c.line([(x + sx * r * 0.45, y - r * 0.3), (x + sx * r * 0.3, y + r * 0.1)], 6, (205, 110, 140))

def ic_olho(c, x, y, r, t, bg, k):
    top = [(x + math.cos(a) * r, y - math.sin(a) * r * 0.55 * math.sin(a / 1.0 + 0.0001) ** 0) for a in []]
    pts = []
    for i in range(0, 25):
        u = i / 24
        pts.append((x - r + 2 * r * u, y - math.sin(math.pi * u) * r * 0.62))
    for i in range(24, -1, -1):
        u = i / 24
        pts.append((x - r + 2 * r * u, y + math.sin(math.pi * u) * r * 0.62))
    blob_outline(c, pts, WHITE)
    px = x + math.sin(t * 1.7) * r * 0.25
    py = y + math.cos(t * 1.3) * r * 0.08
    c.circ(px, py, r * 0.38 + 5, fill=INK)
    c.circ(px, py, r * 0.38, fill=LBLUE)
    c.circ(px, py, r * 0.17, fill=INK)
    c.circ(px - r * 0.1, py - r * 0.1, r * 0.06, fill=WHITE)

def ic_lampada(c, x, y, r, t, bg, k):
    for i in range(9):
        a = math.radians(-160 + i * 40)
        c.line([(x + math.cos(a) * r * 0.85, y - r * 0.2 + math.sin(a) * r * 0.85), (x + math.cos(a) * r * 1.1, y - r * 0.2 + math.sin(a) * r * 1.1)], 12, YEL)
    c.circ(x, y - r * 0.2, r * 0.62 + 6, fill=INK)
    c.circ(x, y - r * 0.2, r * 0.62, fill=(255, 232, 110))
    c.poly([(x - r * 0.28, y + r * 0.25), (x + r * 0.28, y + r * 0.25), (x + r * 0.22, y + r * 0.55), (x - r * 0.22, y + r * 0.55)], INK)
    c.poly([(x - r * 0.22, y + r * 0.3), (x + r * 0.22, y + r * 0.3), (x + r * 0.17, y + r * 0.5), (x - r * 0.17, y + r * 0.5)], GREY)
    c.line([(x - r * 0.15, y + r * 0.1), (x - r * 0.05, y - r * 0.2), (x + r * 0.05, y), (x + r * 0.15, y - r * 0.25)], 6, ORG)

def ic_foguete(c, x, y, r, t, bg, k):
    sh = math.sin(t * 30) * 3
    x += sh
    fl = 0.8 + 0.3 * math.sin(t * 25)
    c.poly([(x - r * 0.22, y + r * 0.7), (x + r * 0.22, y + r * 0.7), (x, y + r * (0.7 + 0.6 * fl))], ORG)
    body = [(x, y - r), (x + r * 0.34, y - r * 0.3), (x + r * 0.34, y + r * 0.7), (x - r * 0.34, y + r * 0.7), (x - r * 0.34, y - r * 0.3)]
    blob_outline(c, body, WHITE)
    for sx in (-1, 1):
        blob_outline(c, [(x + sx * r * 0.34, y + r * 0.2), (x + sx * r * 0.7, y + r * 0.75), (x + sx * r * 0.34, y + r * 0.7)], RED)
    c.poly([(x, y - r), (x + r * 0.34, y - r * 0.3), (x - r * 0.34, y - r * 0.3)], RED)
    c.line([(x, y - r), (x + r * 0.34, y - r * 0.3), (x - r * 0.34, y - r * 0.3), (x, y - r)], 9, INK)
    c.circ(x, y - r * 0.05, r * 0.19 + 5, fill=INK)
    c.circ(x, y - r * 0.05, r * 0.19, fill=LBLUE)

def ic_polvo(c, x, y, r, t, bg, k):
    sc = r / 230.0
    def T(px, py):
        return x + px * sc, y + py * sc
    for i in range(8):
        bx = -140 + i * 40
        ang = (i - 3.5) * 0.17
        ph = t * 3 + i * 0.9
        pts = []
        for j in range(33):
            u = j / 32
            px_ = bx + math.sin(ang) * 285 * u * 1.15 + math.sin(ph - u * 5.5) * 34 * u
            py_ = 150 + math.cos(ang) * 285 * u * 0.98
            pts.append((px_, py_, 20 * (1 - u) + 5.5))
        for px_, py_, rr in pts:
            X, Y = T(px_, py_)
            c.circ(X, Y, (rr + 5) * sc, fill=INK)
        for px_, py_, rr in pts:
            X, Y = T(px_, py_)
            c.circ(X, Y, rr * sc, fill=PINK)
    c.ello(*T(0, 0), 172 * sc, 205 * sc, PINK, w=10 * sc)
    for sx in (-1, 1):
        X, Y = T(sx * 66, 70)
        c.circ(X, Y, 29 * sc, fill=INK)
        c.circ(X, Y, 25 * sc, fill=WHITE)
        c.circ(X + 4 * sc, Y + 3 * sc, 12 * sc, fill=INK)
        c.circ(X, Y - 4 * sc, 3.5 * sc, fill=WHITE)
        bx, by = T(sx * 112, 105)
        c.circ(bx, by, 14 * sc, fill=(240, 128, 160))
    mx, my = T(0, 115)
    c.line([(mx + kk * sc, my + (6 - 6 * (kk / 18) ** 2) * sc) for kk in range(-18, 19, 6)], 5 * sc)

def ic_pergunta(c, x, y, r, t, bg, k):
    qmark(c, x, y - r * 0.55, r / 60.0)

def ic_exclamacao(c, x, y, r, t, bg, k):
    c.line([(x, y - r * 0.9), (x, y + r * 0.25)], r * 0.26, INK)
    c.circ(x, y + r * 0.72, r * 0.15, fill=INK)

def ic_numero(c, x, y, r, t, bg, k, text="?"):
    pass

ICONS = {"coracao": ic_coracao, "estrela": ic_estrela, "sol": ic_sol, "lua": ic_lua, "terra": ic_terra, "gota": ic_gota,
         "raio": ic_raio, "relogio": ic_relogio, "cerebro": ic_cerebro, "olho": ic_olho, "lampada": ic_lampada,
         "foguete": ic_foguete, "polvo": ic_polvo, "pergunta": ic_pergunta, "exclamacao": ic_exclamacao}

def draw_number(c, x, y, r, text):
    f = get_font(r * (1.5 if len(text) <= 2 else 1.0 if len(text) <= 5 else 0.6) * SS)
    d = c.d
    bb = d.textbbox((0, 0), text, font=f)
    w_, h_ = bb[2] - bb[0], bb[3] - bb[1]
    px, py = x * SS - w_ / 2 - bb[0], y * SS - h_ / 2 - bb[1]
    for dx, dy in ((-6, -6), (6, -6), (-6, 6), (6, 6), (0, 8), (0, -8), (8, 0), (-8, 0)):
        d.text((px + dx, py + dy), text, font=f, fill=INK)
    d.text((px, py), text, font=f, fill=(255, 90, 90))

# ---------- poses por emocao ----------
POSES = {
    "curioso": ((115, 125, -55, 5, 0.0), "dot"),
    "surpreso": ((165, 178, -165, -178, 0.0), "wide"),
    "feliz": ((30, 125, -30, -125, -0.08), "happy"),
    "pensativo": ((20, 10, -25, -165, 0.08), "dot"),
}

PALETTE = [(247, 242, 230), (214, 238, 226), (206, 232, 250), (253, 226, 210), (232, 222, 250), (252, 240, 200)]

# ---------- audio / tempos ----------
def load_voice(path):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "work_voice.wav"], check=True)
    w = wave.open("work_voice.wav")
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
    return a

def analyze(a):
    spf = SR // 50
    n = len(a) // spf
    rms = np.sqrt(np.mean(a[:n * spf].reshape(n, spf) ** 2, axis=1))
    voiced = rms > rms.max() * 0.05
    idx = np.where(voiced)[0]
    gaps = []
    if len(idx):
        for i in range(len(idx) - 1):
            if idx[i + 1] - idx[i] > 6:
                gaps.append(((idx[i] + 1) * 0.02, idx[i + 1] * 0.02))
    return rms, voiced, gaps

def scene_bounds(texts, a, dur):
    rms, voiced, gaps = analyze(a)
    vt = np.cumsum(voiced * 0.02)
    total = vt[-1]
    cnt = [max(1, len(re.sub(r"[^0-9A-Za-zÀ-ÿ]", "", t))) for t in texts]
    cum = np.cumsum(cnt) / sum(cnt)
    b = [0.0]
    for k in range(len(texts) - 1):
        est = int(np.searchsorted(vt, cum[k] * total)) * 0.02
        best, bs = None, 1e9
        fim = bool(re.search(r"[.!?…][\"'”)]*\s*$", texts[k].strip()))
        peso = 6.0 if fim else 2.0          # fim de frase costuma ter a pausa mais longa
        for g0, g1 in gaps:
            cen = (g0 + g1) / 2
            if g1 - g0 >= 0.15 and abs(cen - est) < 2.0:
                score = abs(cen - est) - peso * (g1 - g0)
                if score < bs:
                    best, bs = cen, score
        b.append(float(best if best is not None else est))
    b.append(dur)
    for i in range(1, len(b)):
        b[i] = max(b[i], b[i - 1] + 0.4)
    b[-1] = dur
    return b, rms

# ---------- sons ----------
def tt(d):
    return np.arange(int(d * SR)) / SR

def add(buf, t0, sig, g=1.0):
    i = int(t0 * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[:j - i] * g

def lpf(x, k):
    cs = np.cumsum(np.insert(x, 0, 0))
    y = (cs[k:] - cs[:-k]) / k
    return np.concatenate([y, np.zeros(k - 1)])

def pluck(f, d=0.4):
    t = tt(d)
    return (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(4 * np.pi * f * t) * np.exp(-t * 18)) * np.exp(-t * 11)

def marimba(f, d=0.4):
    t = tt(d)
    return np.sin(2 * np.pi * f * t) * np.exp(-t * 9) + 0.35 * np.sin(8 * np.pi * f * t) * np.exp(-t * 30)

def popf(d=0.14, f0=800, f1=220):
    t = tt(d)
    f = f0 * (f1 / f0) ** (t / d)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 26)

def ting(f, d=0.8):
    t = tt(d)
    return (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * 2.76 * f * t)) * np.exp(-t * 6)

def whoosh(d=0.5, rng=np.random.default_rng(4)):
    n = lpf(rng.standard_normal(int(d * SR)), 40) * 6
    return n * np.sin(np.pi * tt(d) / d) ** 2

def gated(x, win=0.05, db=-40):
    n = int(win * SR)
    k = len(x) // n
    r = np.sqrt(np.mean(x[:k * n].reshape(k, n) ** 2, axis=1))
    s = r[r > r.max() * 10 ** (db / 20)]
    return float(np.sqrt(np.mean(s ** 2)))

def build_audio(voice, bounds, dur):
    N = len(voice)
    music = np.zeros(N)
    sfx = np.zeros(N)
    beat = 60 / 112
    notes = {"C3": 130.8, "A2": 110.0, "F2": 87.3, "G2": 98.0, "E4": 329.6, "G4": 392.0, "C5": 523.3, "A4": 440.0, "D4": 293.7, "D5": 587.3}
    bass = ["C3", "A2", "F2", "G2"]
    mel = [["E4", "G4", "C5", "G4"], ["E4", "A4", "C5", "A4"], ["D4", "A4", "D5", "A4"], ["D4", "G4", "D5", "G4"]]
    t, bar = 0.0, 0
    while t < dur:
        b = notes[bass[bar % 4]]
        add(music, t, pluck(b), 0.9)
        add(music, t + 2 * beat, pluck(b * 1.5), 0.7)
        for k, nn in enumerate(mel[bar % 4]):
            add(music, t + k * beat, marimba(notes[nn]), 0.5)
            add(music, t + k * beat + beat / 2, marimba(notes[nn] * (1 if k % 2 == 0 else 1.5)), 0.25)
        t += 4 * beat
        bar += 1
    fade = np.ones(N)
    i0 = max(0, int((dur - 0.6) * SR))
    fade[i0:] = np.linspace(1, 0, N - i0)
    music *= fade
    for i, tb in enumerate(bounds[:-1]):
        add(sfx, max(0, tb - 0.12), whoosh(0.4), 0.5)
        add(sfx, tb, popf(), 0.8)
    add(sfx, bounds[-2] + 0.25, ting(1046), 0.5)
    add(sfx, bounds[-2] + 0.7, ting(1568), 0.4)
    vr, vp = gated(voice), np.abs(voice).max()
    music *= 0.5 * vr / gated(music)
    sfx *= min(0.5 * vr / gated(sfx), 0.7 * vp / np.abs(sfx).max())
    return np.clip(voice + music + sfx, -1, 1)

# ---------- quadro ----------
STATE = {}

def render(i):
    S = STATE
    t = i / FPS
    bounds, scenes, ENV = S["bounds"], S["scenes"], S["env"]
    k = max(j for j in range(len(scenes)) if t >= bounds[j])
    u = t - bounds[k]
    sc = scenes[k]
    bg_c = PALETTE[k % len(PALETTE)]
    bg_p = PALETTE[(k - 1) % len(PALETTE)] if k > 0 else bg_c
    bg = lerpc(bg_p, bg_c, ss(0, 0.4, u))
    c = Cv(bg)
    rnd = random.Random(5)
    for _ in range(22):
        bx, by, br, sp = rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(6, 20), rnd.uniform(20, 60)
        c.circ(bx + 10 * math.sin(t + by), (by - t * sp) % H, br, fill=lerpc(bg, (255, 255, 255), 0.5))
    # visual principal
    vis = sc.get("visual", "pergunta")
    pop = back(u / 0.45, 1.8)
    R = 250 * max(0.001, pop)
    vx, vy = 620, 760 + 12 * math.sin(t * 2.2)
    if vis == "numero" or sc.get("numero"):
        draw_number(c, vx, vy, R, str(sc.get("numero", "?")))
    else:
        ICONS.get(vis, ic_pergunta)(c, vx, vy, R, t, bg, pop)
    # brilhos na entrada
    if u < 0.6:
        for j in range(5):
            a_ = j * 1.26 + 0.4
            kk = max(0, back((u - j * 0.05) / 0.3)) * (1 - ss(0.35, 0.6, u))
            sparkle(c, vx + math.cos(a_) * R * 1.25, vy + math.sin(a_) * R * 1.1, 26 * kk)
    # narrador
    em = sc.get("emocao", "curioso")
    pc, ec = POSES.get(em, POSES["curioso"])
    pp, _ = POSES.get(scenes[k - 1].get("emocao", "curioso") if k > 0 else em, POSES["curioso"])
    w = ss(0, 0.35, u)
    pose = [lerp(pp[q], pc[q], w) for q in range(5)]
    pose[0] += 6 * math.sin(t * 5)
    pose[2] -= 6 * math.sin(t * 5 + 1)
    eyes = ec if (t % 3.1) > 0.1 else "blink"
    hop = 80 * math.sin(min(1, u / 0.4) * math.pi) if em == "surpreso" else (18 * abs(math.sin(u * 6)) if em == "feliz" and u < 1.0 else 0)
    mo = min(1, float(ENV[min(len(ENV) - 1, int(t * FPS))]) * 1.5)
    figure(c, 300, 1780, 520, t, tuple(pose), eyes, mo, hop=hop)
    # camera
    dur_s = bounds[k + 1] - bounds[k]
    z = 1.0 + 0.06 * ss(0, dur_s, u) + 0.05 * (1 - ss(0, 0.3, u))
    cx = 540 + (35 if k % 2 == 0 else -35) * ss(0, dur_s, u)
    cy = 1000
    bw, bh = W / z, H / z
    l = min(max(cx - bw / 2, 0), W - bw)
    tp = min(max(cy - bh / 2, 0), H - bh)
    im = c.im.resize((W, H), Image.LANCZOS, box=(l * SS, tp * SS, (l + bw) * SS, (tp + bh) * SS))
    fl = max(0, 1 - u / 0.12) * 0.45 if k > 0 else 0
    if fl > 0:
        im = Image.blend(im, Image.new("RGB", (W, H), (255, 255, 255)), fl)
    return im

def main():
    folder = sys.argv[1]
    os.chdir(folder)
    cfg = json.load(open("cenas.json", encoding="utf-8"))
    scenes = cfg["cenas"]
    voice = load_voice("voice.mp3")
    dur = len(voice) / SR
    nf = round(dur * FPS)
    bounds, rms = scene_bounds([s["texto"] for s in scenes], voice, dur)
    print("limites das cenas (s):", [round(b, 2) for b in bounds], flush=True)
    spf = SR // FPS
    env = np.array([np.sqrt(np.mean(voice[q * spf:(q + 1) * spf] ** 2)) if q * spf < len(voice) else 0 for q in range(nf + 2)])
    env = np.clip(env / (np.percentile(env, 95) + 1e-9), 0, 1)
    env = np.convolve(env, [0.25, 0.5, 0.25], mode="same")
    STATE.update(bounds=bounds, scenes=scenes, env=env)
    mix = build_audio(voice, bounds, dur)
    w = wave.open("work_mix.wav", "wb")
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
    w.close()
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", "work_mix.wav", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "work_mix_n.wav"], check=True)
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-i", "work_mix_n.wav", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                          "-shortest", "-movflags", "+faststart", "video.mp4"], stdin=subprocess.PIPE)
    from multiprocessing import Pool
    with Pool(os.cpu_count() or 1) as pool:
        for n_, im in enumerate(pool.imap(render, range(nf), chunksize=2)):
            p.stdin.write(im.tobytes())
            if n_ % 60 == 0:
                print("quadro", n_, "/", nf, flush=True)
    p.stdin.close()
    p.wait()
    print("pronto: video.mp4")

if __name__ == "__main__":
    main()
