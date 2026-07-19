import pygame
import sys
import math
import random
from collections import deque

# ──────────────────── التهيئة ────────────────────
pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

# الحصول على دقة الشاشة الحقيقية
disp_info = pygame.display.Info()
SCREEN_W = disp_info.current_w
SCREEN_H = disp_info.current_h

# وضع ملء الشاشة
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.FULLSCREEN)
pygame.display.set_caption("⚡ Space Wars ⚡")
clock = pygame.time.Clock()

# الأبعاد الافتراضية للعبة (التصميم عليه)
VW, VH = 400, 700
FPS = 60

# حساب التحجيم والحفاظ على نسبة العرض
scale_x = SCREEN_W / VW
scale_y = SCREEN_H / VH
GAME_SCALE = min(scale_x, scale_y)
# توسيط اللعبة إذا كانت الشاشة أعرض
OFFSET_X = (SCREEN_W - VW * GAME_SCALE) / 2
OFFSET_Y = (SCREEN_H - VH * GAME_SCALE) / 2

# ──────────────────── دالّة تحويل إحداثيات اللمس ────────────────────
def touch_to_game(tx, ty):
    """تحويل إحداثيات شاشة الهاتف إلى إحداثيات اللعبة"""
    gx = (tx - OFFSET_X) / GAME_SCALE
    gy = (ty - OFFSET_Y) / GAME_SCALE
    return gx, gy

def game_to_screen(gx, gy):
    """تحويل إحداثيات اللعبة إلى إحداثيات الشاشة"""
    sx = gx * GAME_SCALE + OFFSET_X
    sy = gy * GAME_SCALE + OFFSET_Y
    return sx, sy

# ──────────────────── الألوان ────────────────────
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
YELLOW = (255, 255, 0)
RED = (255, 50, 50)
GREEN = (50, 255, 50)
BLUE = (50, 100, 255)
ORANGE = (255, 165, 0)
DARK_BLUE = (5, 5, 30)
PURPLE = (150, 50, 255)
PINK = (255, 100, 200)
GOLD = (255, 215, 0)
DARK_BG = (2, 2, 15)

# ──────────────────── توليد الأصوات بالكود ────────────────────
import array

def make_sound(frequency=440, duration=0.1, volume=0.3, wave='square'):
    sample_rate = 22050
    n_samples = int(sample_rate * duration)
    buf = array.array('h', [0] * n_samples)
    max_amp = int(32767 * volume)
    for i in range(n_samples):
        t = i / sample_rate
        decay = max(0, 1 - t / duration)
        if wave == 'square':
            val = max_amp if math.sin(2 * math.pi * frequency * t) >= 0 else -max_amp
        elif wave == 'saw':
            val = int(max_amp * (2 * (t * frequency - int(t * frequency)) - 1))
        elif wave == 'noise':
            val = int(random.uniform(-max_amp, max_amp))
        else:
            val = int(max_amp * math.sin(2 * math.pi * frequency * t))
        buf[i] = int(val * decay)
    sound = pygame.mixer.Sound(buffer=buf)
    return sound

snd_shoot = make_sound(880, 0.08, 0.2, 'square')
snd_shoot2 = make_sound(660, 0.1, 0.2, 'saw')
snd_explode = make_sound(120, 0.3, 0.4, 'noise')
snd_explode_big = make_sound(80, 0.5, 0.5, 'noise')
snd_powerup = make_sound(1200, 0.2, 0.25, 'sine')
snd_hit = make_sound(200, 0.1, 0.3, 'noise')
snd_levelup = make_sound(600, 0.15, 0.2, 'sine')
snd_levelup2 = make_sound(900, 0.15, 0.2, 'sine')
snd_menu = make_sound(440, 0.08, 0.15, 'sine')
snd_boss = make_sound(60, 0.6, 0.4, 'saw')

# ──────────────────── الخطوط ────────────────────
def get_font(size, bold=False):
    fonts = ['arial', 'helvetica', 'freesans', 'dejavusans', None]
    for f in fonts:
        try:
            font = pygame.font.SysFont(f, size, bold=bold)
            return font
        except:
            continue
    return pygame.font.Font(None, size)

font_xl = get_font(48, True)
font_lg = get_font(36, True)
font_md = get_font(24, True)
font_sm = get_font(18)
font_xs = get_font(14)

# ──────────────────── نظام الجسيمات ────────────────────
class Particle:
    __slots__ = ['x', 'y', 'color', 'vx', 'vy', 'life', 'max_life', 'size', 'gravity', 'shrink']
    def __init__(self, x, y, color, vx=0, vy=0, life=30, size=3, gravity=0, shrink=True):
        self.x, self.y = x, y
        self.color = color
        self.vx = vx + random.uniform(-1, 1)
        self.vy = vy + random.uniform(-1, 1)
        self.life = self.max_life = life
        self.size = size
        self.gravity = gravity
        self.shrink = shrink

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.life -= 1
        return self.life > 0

    def draw(self, surf):
        alpha = self.life / self.max_life
        s = self.size * alpha if self.shrink else self.size
        if s < 0.5:
            return
        r, g, b = self.color
        color = (min(255, int(r * alpha + 50 * (1 - alpha))),
                 min(255, int(g * alpha)),
                 min(255, int(b * alpha)))
        pygame.draw.circle(surf, color, (int(self.x), int(self.y)), max(1, int(s)))

class ParticleSystem:
    def __init__(self):
        self.particles = deque(maxlen=600)

    def emit(self, x, y, color, count=10, speed=3, life=25, size=3, gravity=0):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            spd = random.uniform(0.5, speed)
            self.particles.append(Particle(
                x, y, color,
                math.cos(angle) * spd, math.sin(angle) * spd,
                life=random.randint(life // 2, life),
                size=random.uniform(size * 0.5, size),
                gravity=gravity
            ))

    def emit_directional(self, x, y, color, angle, spread, count=5, speed=4, life=20, size=2):
        for _ in range(count):
            a = angle + random.uniform(-spread, spread)
            spd = random.uniform(speed * 0.5, speed)
            self.particles.append(Particle(
                x, y, color,
                math.cos(a) * spd, math.sin(a) * spd,
                life=random.randint(life // 2, life), size=size
            ))

    def update(self):
        self.particles = deque((p for p in self.particles if p.update()), maxlen=600)

    def draw(self, surf):
        for p in self.particles:
            p.draw(surf)

particles = ParticleSystem()

# ──────────────────── خلفية النجوم ────────────────────
class StarField:
    def __init__(self):
        self.layers = []
        for speed, count, max_size in [(0.3, 60, 1), (0.8, 40, 2), (1.5, 25, 3)]:
            stars = []
            for _ in range(count):
                stars.append([random.randint(0, VW), random.randint(0, VH),
                              random.uniform(0.5, max_size), random.randint(150, 255)])
            self.layers.append((speed, stars))
        # سديم خلفي
        self.nebulae = []
        for _ in range(3):
            self.nebulae.append({
                'x': random.randint(0, VW),
                'y': random.randint(0, VH),
                'r': random.randint(60, 120),
                'color': random.choice([(20, 0, 40), (0, 10, 30), (30, 0, 20)]),
                'speed': random.uniform(0.1, 0.3)
            })

    def update(self):
        for speed, stars in self.layers:
            for s in stars:
                s[1] += speed
                if s[1] > VH:
                    s[0] = random.randint(0, VW)
                    s[1] = 0
        for n in self.nebulae:
            n['y'] += n['speed']
            if n['y'] - n['r'] > VH:
                n['y'] = -n['r']
                n['x'] = random.randint(0, VW)

    def draw(self, surf):
        # سديم
        for n in self.nebulae:
            neb_surf = pygame.Surface((n['r'] * 2, n['r'] * 2), pygame.SRCALPHA)
            for ring in range(n['r'], 0, -3):
                alpha = int(15 * (ring / n['r']))
                c = (*n['color'], alpha)
                pygame.draw.circle(neb_surf, c, (n['r'], n['r']), ring)
            surf.blit(neb_surf, (int(n['x'] - n['r']), int(n['y'] - n['r'])))
        # نجوم
        for speed, stars in self.layers:
            for x, y, size, bright in stars:
                c = (bright, bright, min(255, bright + 30))
                pygame.draw.circle(surf, c, (int(x), int(y)), max(1, int(size)))

starfield = StarField()

# ──────────────────── رسم السفن ────────────────────
def draw_player_ship(surf, x, y, shield_timer=0, weapon_level=1):
    flame_len = random.randint(12, 22)
    pts_flame = [(x - 6, y + 18), (x, y + 18 + flame_len), (x + 6, y + 18)]
    pygame.draw.polygon(surf, ORANGE, pts_flame)
    pts_flame2 = [(x - 3, y + 18), (x, y + 18 + flame_len - 5), (x + 3, y + 18)]
    pygame.draw.polygon(surf, YELLOW, pts_flame2)
    # لهب جانبي
    fl2 = random.randint(6, 12)
    pygame.draw.polygon(surf, (200, 100, 0), [(x - 22, y + 16), (x - 18, y + 16 + fl2), (x - 14, y + 16)])
    pygame.draw.polygon(surf, (200, 100, 0), [(x + 14, y + 16), (x + 18, y + 16 + fl2), (x + 22, y + 16)])

    body = [(x, y - 22), (x - 18, y + 16), (x - 8, y + 12),
            (x, y + 18), (x + 8, y + 12), (x + 18, y + 16)]
    pygame.draw.polygon(surf, (30, 120, 255), body)
    pygame.draw.polygon(surf, CYAN, body, 2)

    wing_l = [(x - 10, y + 5), (x - 28, y + 18), (x - 18, y + 16), (x - 8, y + 12)]
    wing_r = [(x + 10, y + 5), (x + 28, y + 18), (x + 18, y + 16), (x + 8, y + 12)]
    pygame.draw.polygon(surf, (20, 80, 200), wing_l)
    pygame.draw.polygon(surf, (20, 80, 200), wing_r)
    pygame.draw.polygon(surf, CYAN, wing_l, 1)
    pygame.draw.polygon(surf, CYAN, wing_r, 1)

    pygame.draw.ellipse(surf, (100, 200, 255), (x - 5, y - 10, 10, 16))
    pygame.draw.ellipse(surf, WHITE, (x - 3, y - 7, 6, 8))

    if weapon_level >= 2:
        pygame.draw.circle(surf, YELLOW, (int(x - 22), int(y + 16)), 3)
        pygame.draw.circle(surf, YELLOW, (int(x + 22), int(y + 16)), 3)
    if weapon_level >= 3:
        pygame.draw.circle(surf, MAGENTA, (int(x - 14), int(y - 5)), 3)
        pygame.draw.circle(surf, MAGENTA, (int(x + 14), int(y - 5)), 3)
    if weapon_level >= 4:
        pygame.draw.circle(surf, GREEN, (int(x - 26), int(y + 8)), 2)
        pygame.draw.circle(surf, GREEN, (int(x + 26), int(y + 8)), 2)

    if shield_timer > 0:
        alpha = int(100 + 80 * math.sin(pygame.time.get_ticks() * 0.01))
        shield_surf = pygame.Surface((70, 70), pygame.SRCALPHA)
        pygame.draw.circle(shield_surf, (0, 200, 255, min(255, alpha)), (35, 35), 32, 3)
        pygame.draw.circle(shield_surf, (0, 200, 255, min(255, alpha // 3)), (35, 35), 30)
        surf.blit(shield_surf, (x - 35, y - 35))

def draw_enemy(surf, x, y, etype, hp_ratio=1.0, tick=0):
    if etype == 0:
        pts = [(x, y + 15), (x - 15, y - 10), (x - 5, y - 5),
               (x, y - 15), (x + 5, y - 5), (x + 15, y - 10)]
        color = (200, 50, 50) if hp_ratio > 0.5 else (255, 100, 50)
        pygame.draw.polygon(surf, color, pts)
        pygame.draw.polygon(surf, RED, pts, 2)
        pygame.draw.circle(surf, YELLOW, (int(x), int(y)), 4)
    elif etype == 1:
        pts = [(x, y + 12), (x - 20, y), (x - 8, y - 5),
               (x, y - 14), (x + 8, y - 5), (x + 20, y)]
        color = (50, 200, 50) if hp_ratio > 0.5 else (100, 255, 100)
        pygame.draw.polygon(surf, color, pts)
        pygame.draw.polygon(surf, GREEN, pts, 2)
        pygame.draw.circle(surf, WHITE, (int(x), int(y - 2)), 3)
    elif etype == 2:
        pygame.draw.rect(surf, (180, 50, 180), (x - 18, y - 14, 36, 28), border_radius=5)
        pygame.draw.rect(surf, PURPLE, (x - 18, y - 14, 36, 28), 2, border_radius=5)
        pygame.draw.rect(surf, (100, 30, 100), (x - 10, y - 10, 20, 12), border_radius=3)
        pygame.draw.circle(surf, MAGENTA, (int(x - 8), int(y + 5)), 4)
        pygame.draw.circle(surf, MAGENTA, (int(x + 8), int(y + 5)), 4)
    elif etype == 3:
        pygame.draw.ellipse(surf, (80, 0, 0), (x - 45, y - 30, 90, 60))
        pygame.draw.ellipse(surf, RED, (x - 45, y - 30, 90, 60), 3)
        eye_off = math.sin(tick * 0.05) * 3
        pygame.draw.circle(surf, YELLOW, (int(x - 18), int(y - 5 + eye_off)), 10)
        pygame.draw.circle(surf, YELLOW, (int(x + 18), int(y - 5 + eye_off)), 10)
        pygame.draw.circle(surf, RED, (int(x - 18), int(y - 5 + eye_off)), 5)
        pygame.draw.circle(surf, RED, (int(x + 18), int(y - 5 + eye_off)), 5)
        mouth_w = 20 + int(10 * abs(math.sin(tick * 0.03)))
        pygame.draw.ellipse(surf, (150, 0, 0), (x - mouth_w // 2, y + 8, mouth_w, 12))
        pygame.draw.ellipse(surf, ORANGE, (x - mouth_w // 2, y + 8, mouth_w, 12), 2)
        for side in [-1, 1]:
            ax = x + side * 50
            ay = y + math.sin(tick * 0.06 + side) * 8
            pygame.draw.circle(surf, (150, 30, 30), (int(ax), int(ay)), 12)
            pygame.draw.circle(surf, RED, (int(ax), int(ay)), 12, 2)
            pygame.draw.circle(surf, ORANGE, (int(ax), int(ay)), 5)

# ──────────────────── الرصاصات ────────────────────
class Bullet:
    __slots__ = ['x', 'y', 'vx', 'vy', 'color', 'size', 'damage', 'is_player', 'alive', 'trail']
    def __init__(self, x, y, vx=0, vy=-10, color=CYAN, size=3, damage=1, is_player=True):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.color = color
        self.size = size
        self.damage = damage
        self.is_player = is_player
        self.alive = True
        self.trail = deque(maxlen=5)

    def update(self):
        self.trail.append((self.x, self.y))
        self.x += self.vx
        self.y += self.vy
        if self.y < -20 or self.y > VH + 20 or self.x < -20 or self.x > VW + 20:
            self.alive = False

    def draw(self, surf):
        for i, (tx, ty) in enumerate(self.trail):
            alpha = (i + 1) / len(self.trail) * 0.5
            s = self.size * alpha
            if s > 0.5:
                pygame.draw.circle(surf, self.color, (int(tx), int(ty)), max(1, int(s)))
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.size)
        pygame.draw.circle(surf, WHITE, (int(self.x), int(self.y)), max(1, self.size - 1))

    def get_rect(self):
        return pygame.Rect(self.x - self.size, self.y - self.size, self.size * 2, self.size * 2)

# ──────────────────── الباور أبس ────────────────────
class PowerUp:
    TYPES = ['weapon', 'shield', 'health', 'bomb', 'score']
    COLORS = {'weapon': YELLOW, 'shield': CYAN, 'health': GREEN, 'bomb': RED, 'score': GOLD}
    LABELS = {'weapon': 'W', 'shield': 'S', 'health': '+', 'bomb': 'B', 'score': '$'}

    def __init__(self, x, y, ptype=None):
        self.x, self.y = x, y
        self.type = ptype or random.choice(self.TYPES)
        self.color = self.COLORS[self.type]
        self.label = self.LABELS[self.type]
        self.vy = 1.5
        self.alive = True
        self.tick = 0
        self.size = 14

    def update(self):
        self.y += self.vy
        self.tick += 1
        if self.y > VH + 30:
            self.alive = False

    def draw(self, surf):
        pulse = 1 + 0.15 * math.sin(self.tick * 0.1)
        s = int(self.size * pulse)
        glow_surf = pygame.Surface((s * 4, s * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*self.color, 40), (s * 2, s * 2), s * 2)
        surf.blit(glow_surf, (int(self.x - s * 2), int(self.y - s * 2)))
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), s)
        pygame.draw.circle(surf, WHITE, (int(self.x), int(self.y)), s, 2)
        txt = font_sm.render(self.label, True, BLACK)
        surf.blit(txt, (self.x - txt.get_width() // 2, self.y - txt.get_height() // 2))

    def get_rect(self):
        return pygame.Rect(self.x - self.size, self.y - self.size, self.size * 2, self.size * 2)

# ──────────────────── الأعداء ────────────────────
class Enemy:
    CONFIGS = {
        0: {'hp': 2, 'speed': 2, 'score': 100, 'shoot_rate': 90, 'color': RED},
        1: {'hp': 1, 'speed': 3.5, 'score': 150, 'shoot_rate': 60, 'color': GREEN},
        2: {'hp': 5, 'speed': 1.2, 'score': 250, 'shoot_rate': 50, 'color': PURPLE},
        3: {'hp': 50, 'speed': 0.5, 'score': 2000, 'shoot_rate': 20, 'color': RED},
    }

    def __init__(self, x, y, etype=0, level=1):
        cfg = self.CONFIGS[etype]
        self.x, self.y = x, y
        self.etype = etype
        self.max_hp = int(cfg['hp'] * (1 + level * 0.3))
        self.hp = self.max_hp
        self.speed = cfg['speed'] + level * 0.1
        self.score = cfg['score']
        self.shoot_timer = random.randint(0, cfg['shoot_rate'])
        self.shoot_rate = max(10, cfg['shoot_rate'] - level * 3)
        self.alive = True
        self.tick = random.randint(0, 1000)
        self.move_pattern = random.choice(['straight', 'sine', 'zigzag']) if etype != 3 else 'boss'
        self.start_x = x
        self.flash = 0

    def update(self, bullets):
        self.tick += 1
        if self.flash > 0:
            self.flash -= 1

        if self.move_pattern == 'straight':
            self.y += self.speed
        elif self.move_pattern == 'sine':
            self.y += self.speed
            self.x = self.start_x + math.sin(self.tick * 0.05) * 40
        elif self.move_pattern == 'zigzag':
            self.y += self.speed
            self.x += math.copysign(self.speed * 0.8, math.sin(self.tick * 0.08))
            self.x = max(20, min(VW - 20, self.x))
        elif self.move_pattern == 'boss':
            if self.y < 80:
                self.y += self.speed
            else:
                self.x = VW // 2 + math.sin(self.tick * 0.02) * 120
                self.y = 80 + math.sin(self.tick * 0.015) * 20

        self.shoot_timer -= 1
        if self.shoot_timer <= 0 and self.y > 0 and self.y < VH - 50:
            self.shoot_timer = self.shoot_rate
            if self.etype == 3:
                for angle in [-0.3, -0.15, 0, 0.15, 0.3]:
                    bvx = math.sin(angle) * 4
                    bvy = math.cos(angle) * 4
                    bullets.append(Bullet(self.x, self.y + 20, bvx, bvy, ORANGE, 4, 1, False))
            else:
                bullets.append(Bullet(self.x, self.y + 10, 0, 4, RED, 3, 1, False))

        if self.y > VH + 50:
            self.alive = False

    def take_damage(self, dmg):
        self.hp -= dmg
        self.flash = 5
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def draw(self, surf):
        draw_enemy(surf, self.x, self.y, self.etype, self.hp / self.max_hp, self.tick)
        if self.flash > 0:
            flash_surf = pygame.Surface((60, 60), pygame.SRCALPHA)
            pygame.draw.circle(flash_surf, (255, 255, 255, 100), (30, 30), 30)
            surf.blit(flash_surf, (int(self.x - 30), int(self.y - 30)))
        if self.etype >= 2:
            bw = 40 if self.etype == 2 else 80
            bx = self.x - bw // 2
            by = self.y - (20 if self.etype == 2 else 40)
            ratio = self.hp / self.max_hp
            pygame.draw.rect(surf, (60, 0, 0), (bx, by, bw, 5))
            pygame.draw.rect(surf, GREEN if ratio > 0.5 else YELLOW if ratio > 0.25 else RED,
                             (bx, by, int(bw * ratio), 5))

    def get_rect(self):
        if self.etype == 3:
            return pygame.Rect(self.x - 45, self.y - 30, 90, 60)
        elif self.etype == 2:
            return pygame.Rect(self.x - 18, self.y - 14, 36, 28)
        else:
            return pygame.Rect(self.x - 15, self.y - 15, 30, 30)

# ──────────────────── النص المتحرك ────────────────────
class FloatingText:
    def __init__(self, x, y, text, color=GOLD, size='sm'):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.font = font_sm if size == 'sm' else font_md
        self.life = 40
        self.max_life = 40

    def update(self):
        self.y -= 1.5
        self.life -= 1
        return self.life > 0

    def draw(self, surf):
        alpha = self.life / self.max_life
        txt = self.font.render(self.text, True, self.color)
        txt.set_alpha(int(255 * alpha))
        surf.blit(txt, (self.x - txt.get_width() // 2, int(self.y)))

# ──────────────────── اهتزاز الشاشة ────────────────────
class ScreenShake:
    def __init__(self):
        self.intensity = 0
        self.duration = 0

    def trigger(self, intensity=5, duration=10):
        self.intensity = intensity
        self.duration = duration

    def get_offset(self):
        if self.duration > 0:
            self.duration -= 1
            return (random.uniform(-self.intensity, self.intensity),
                    random.uniform(-self.intensity, self.intensity))
        return (0, 0)

shake = ScreenShake()

# ──────────────────── اللعبة الرئيسية ────────────────────
class Game:
    def __init__(self):
        self.state = 'menu'
        self.reset()
        self.high_score = 0
        self.menu_tick = 0

    def reset(self):
        self.player_x = VW // 2
        self.player_y = VH - 80
        self.player_hp = 5
        self.player_max_hp = 5
        self.weapon_level = 1
        self.shield_timer = 0
        self.score = 0
        self.combo = 0
        self.combo_timer = 0
        self.level = 1
        self.kills = 0
        self.kills_for_level = 10
        self.bombs = 2
        self.player_bullets = []
        self.enemy_bullets = []
        self.enemies = []
        self.powerups = []
        self.floating_texts = []
        self.shoot_cooldown = 0
        self.spawn_timer = 0
        self.spawn_rate = 60
        self.boss_spawned = False
        self.invincible = 0
        self.game_tick = 0
        self.total_time = 0
        self.auto_shoot = True
        self.touch_active = False
        self.touch_target = (VW // 2, VH - 80)

    def spawn_enemy(self):
        x = random.randint(30, VW - 30)
        if self.level >= 5 and self.kills % self.kills_for_level == 0 and not self.boss_spawned:
            self.enemies.append(Enemy(VW // 2, -50, 3, self.level))
            self.boss_spawned = True
            snd_boss.play()
            self.floating_texts.append(FloatingText(VW // 2, VH // 2, "BOSS!", RED, 'md'))
            return
        if self.level < 2:
            weights = [0.7, 0.3]
        elif self.level < 4:
            weights = [0.45, 0.3, 0.25]
        else:
            weights = [0.3, 0.25, 0.45]
        etype = random.choices(range(len(weights)), weights=weights)[0]
        self.enemies.append(Enemy(x, -30, etype, self.level))

    def player_shoot(self):
        if self.shoot_cooldown > 0:
            return
        rate = max(4, 10 - self.weapon_level)
        self.shoot_cooldown = rate
        x, y = self.player_x, self.player_y - 22

        if self.weapon_level == 1:
            self.player_bullets.append(Bullet(x, y, 0, -10, CYAN, 3))
            snd_shoot.play()
        elif self.weapon_level == 2:
            self.player_bullets.append(Bullet(x - 8, y, 0, -10, CYAN, 3))
            self.player_bullets.append(Bullet(x + 8, y, 0, -10, CYAN, 3))
            snd_shoot.play()
        elif self.weapon_level == 3:
            self.player_bullets.append(Bullet(x, y, 0, -10, CYAN, 3))
            self.player_bullets.append(Bullet(x - 14, y + 5, -1, -9, YELLOW, 2))
            self.player_bullets.append(Bullet(x + 14, y + 5, 1, -9, YELLOW, 2))
            snd_shoot2.play()
        else:
            self.player_bullets.append(Bullet(x, y, 0, -11, CYAN, 4, 2))
            self.player_bullets.append(Bullet(x - 14, y + 5, -1.5, -9, YELLOW, 2))
            self.player_bullets.append(Bullet(x + 14, y + 5, 1.5, -9, YELLOW, 2))
            self.player_bullets.append(Bullet(x - 22, y + 10, -2.5, -7, MAGENTA, 2))
            self.player_bullets.append(Bullet(x + 22, y + 10, 2.5, -7, MAGENTA, 2))
            snd_shoot2.play()

    def use_bomb(self):
        if self.bombs <= 0:
            return
        self.bombs -= 1
        snd_explode_big.play()
        shake.trigger(10, 20)
        self.enemy_bullets.clear()
        for e in self.enemies:
            killed = e.take_damage(10)
            particles.emit(e.x, e.y, ORANGE, 15, 5, 30, 4)
            if killed:
                self.on_enemy_killed(e)
        for _ in range(5):
            px = random.randint(0, VW)
            py = random.randint(0, VH)
            particles.emit(px, py, WHITE, 20, 6, 35, 5)

    def on_enemy_killed(self, enemy):
        self.kills += 1
        self.combo += 1
        self.combo_timer = 120
        bonus = int(enemy.score * (1 + self.combo * 0.1))
        self.score += bonus

        colors = [RED, ORANGE, YELLOW, WHITE]
        count = 30 if enemy.etype == 3 else 15 if enemy.etype == 2 else 10
        size = 6 if enemy.etype == 3 else 4 if enemy.etype == 2 else 3
        for c in colors:
            particles.emit(enemy.x, enemy.y, c, count // len(colors), 5, 30, size)

        if enemy.etype == 3:
            snd_explode_big.play()
            shake.trigger(12, 25)
            self.floating_texts.append(FloatingText(enemy.x, enemy.y, f"+{bonus}", GOLD, 'md'))
            self.boss_spawned = False
            for _ in range(5):
                self.powerups.append(PowerUp(
                    enemy.x + random.randint(-40, 40),
                    enemy.y + random.randint(-20, 20)
                ))
        else:
            snd_explode.play()
            shake.trigger(3, 8)
            self.floating_texts.append(FloatingText(enemy.x, enemy.y, f"+{bonus}"))

        drop_chance = 0.15 if enemy.etype < 2 else 0.35
        if random.random() < drop_chance:
            self.powerups.append(PowerUp(enemy.x, enemy.y))

        if self.kills % self.kills_for_level == 0 and enemy.etype != 3:
            self.level_up()

    def level_up(self):
        self.level += 1
        self.spawn_rate = max(15, 60 - self.level * 4)
        snd_levelup.play()
        pygame.time.set_timer(pygame.USEREVENT + 1, 150, 1)
        self.floating_texts.append(FloatingText(VW // 2, VH // 2 - 30,
                                                 f"LEVEL {self.level}!", CYAN, 'md'))

    def player_hit(self):
        if self.invincible > 0:
            return
        if self.shield_timer > 0:
            self.shield_timer = 0
            snd_hit.play()
            particles.emit(self.player_x, self.player_y, CYAN, 20, 4, 20, 3)
            self.invincible = 30
            return
        self.player_hp -= 1
        snd_hit.play()
        shake.trigger(8, 15)
        particles.emit(self.player_x, self.player_y, RED, 25, 5, 25, 4)
        self.invincible = 90
        self.combo = 0
        if self.player_hp <= 0:
            self.state = 'gameover'
            if self.score > self.high_score:
                self.high_score = self.score
            particles.emit(self.player_x, self.player_y, WHITE, 50, 8, 40, 6)
            snd_explode_big.play()

    def collect_powerup(self, pu):
        snd_powerup.play()
        particles.emit(pu.x, pu.y, pu.color, 15, 3, 20, 3)
        if pu.type == 'weapon':
            self.weapon_level = min(4, self.weapon_level + 1)
            self.floating_texts.append(FloatingText(pu.x, pu.y, "WEAPON UP!", YELLOW))
        elif pu.type == 'shield':
            self.shield_timer = 600
            self.floating_texts.append(FloatingText(pu.x, pu.y, "SHIELD!", CYAN))
        elif pu.type == 'health':
            self.player_hp = min(self.player_max_hp, self.player_hp + 1)
            self.floating_texts.append(FloatingText(pu.x, pu.y, "HEAL!", GREEN))
        elif pu.type == 'bomb':
            self.bombs = min(5, self.bombs + 1)
            self.floating_texts.append(FloatingText(pu.x, pu.y, "BOMB +1", RED))
        elif pu.type == 'score':
            bonus = 500 * self.level
            self.score += bonus
            self.floating_texts.append(FloatingText(pu.x, pu.y, f"+{bonus}", GOLD))

    def update_playing(self):
        self.game_tick += 1
        self.total_time += 1 / FPS

        if self.touch_active:
            dx = self.touch_target[0] - self.player_x
            dy = self.touch_target[1] - self.player_y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > 3:
                speed = min(8, dist * 0.15)
                self.player_x += (dx / dist) * speed
                self.player_y += (dy / dist) * speed
            if random.random() < 0.3:
                particles.emit_directional(self.player_x, self.player_y + 18,
                                           ORANGE, math.pi / 2, 0.5, 1, 2, 10, 2)

        self.player_x = max(25, min(VW - 25, self.player_x))
        self.player_y = max(50, min(VH - 30, self.player_y))

        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        if self.shield_timer > 0:
            self.shield_timer -= 1
        if self.invincible > 0:
            self.invincible -= 1
        if self.combo_timer > 0:
            self.combo_timer -= 1
            if self.combo_timer == 0:
                self.combo = 0

        if self.auto_shoot:
            self.player_shoot()

        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.spawn_timer = self.spawn_rate
            self.spawn_enemy()

        for b in self.player_bullets:
            b.update()
        self.player_bullets = [b for b in self.player_bullets if b.alive]
        for b in self.enemy_bullets:
            b.update()
        self.enemy_bullets = [b for b in self.enemy_bullets if b.alive]
        for e in self.enemies:
            e.update(self.enemy_bullets)
        self.enemies = [e for e in self.enemies if e.alive]
        for p in self.powerups:
            p.update()
        self.powerups = [p for p in self.powerups if p.alive]

        for b in self.player_bullets:
            if not b.alive:
                continue
            brect = b.get_rect()
            for e in self.enemies:
                if not e.alive:
                    continue
                if brect.colliderect(e.get_rect()):
                    b.alive = False
                    particles.emit(b.x, b.y, b.color, 3, 2, 10, 2)
                    killed = e.take_damage(b.damage)
                    if killed:
                        self.on_enemy_killed(e)
                    break

        prect = pygame.Rect(self.player_x - 12, self.player_y - 18, 24, 36)
        for b in self.enemy_bullets:
            if not b.alive:
                continue
            if b.get_rect().colliderect(prect):
                b.alive = False
                self.player_hit()

        for e in self.enemies:
            if not e.alive:
                continue
            if e.get_rect().colliderect(prect):
                self.player_hit()
                if e.etype < 3:
                    e.alive = False
                    particles.emit(e.x, e.y, ORANGE, 10, 3, 20, 3)

        for p in self.powerups:
            if not p.alive:
                continue
            if p.get_rect().colliderect(prect):
                p.alive = False
                self.collect_powerup(p)

        particles.update()
        self.floating_texts = [ft for ft in self.floating_texts if ft.update()]

    def draw_hud(self, surf):
        txt = font_md.render(f"SCORE: {self.score:,}", True, WHITE)
        surf.blit(txt, (10, 10))
        txt = font_sm.render(f"LV.{self.level}", True, CYAN)
        surf.blit(txt, (VW - txt.get_width() - 10, 10))
        if self.combo > 1:
            combo_txt = font_sm.render(f"x{self.combo} COMBO!", True, GOLD)
            surf.blit(combo_txt, (VW // 2 - combo_txt.get_width() // 2, 10))

        for i in range(self.player_max_hp):
            x = 10 + i * 22
            y = 40
            if i < self.player_hp:
                pygame.draw.polygon(surf, RED, [
                    (x + 8, y + 3), (x + 15, y + 8), (x + 12, y + 15),
                    (x + 8, y + 12), (x + 4, y + 15), (x + 1, y + 8)
                ])
            else:
                pygame.draw.polygon(surf, (60, 20, 20), [
                    (x + 8, y + 3), (x + 15, y + 8), (x + 12, y + 15),
                    (x + 8, y + 12), (x + 4, y + 15), (x + 1, y + 8)
                ], 1)

        for i in range(self.bombs):
            x = 10 + i * 22
            y = 65
            pygame.draw.circle(surf, ORANGE, (x + 8, y + 8), 7)
            pygame.draw.circle(surf, YELLOW, (x + 8, y + 8), 4)
            pygame.draw.line(surf, WHITE, (x + 8, y + 1), (x + 12, y - 3), 2)

        wep_txt = font_xs.render(f"WPN LV.{self.weapon_level}", True, YELLOW)
        surf.blit(wep_txt, (VW - wep_txt.get_width() - 10, 35))
        if self.shield_timer > 0:
            sh_txt = font_xs.render(f"SHIELD {self.shield_timer // 60 + 1}s", True, CYAN)
            surf.blit(sh_txt, (VW - sh_txt.get_width() - 10, 52))

    def draw_menu(self, surf):
        self.menu_tick += 1
        starfield.update()
        starfield.draw(surf)

        title_y = 150 + math.sin(self.menu_tick * 0.03) * 10
        shadow = font_xl.render("SPACE", True, (0, 50, 100))
        surf.blit(shadow, (VW // 2 - shadow.get_width() // 2 + 3, title_y - 30 + 3))
        shadow2 = font_xl.render("WARS", True, (0, 50, 100))
        surf.blit(shadow2, (VW // 2 - shadow2.get_width() // 2 + 3, title_y + 25 + 3))
        t1 = font_xl.render("SPACE", True, CYAN)
        t2 = font_xl.render("WARS", True, WHITE)
        surf.blit(t1, (VW // 2 - t1.get_width() // 2, title_y - 30))
        surf.blit(t2, (VW // 2 - t2.get_width() // 2, title_y + 25))

        for i in range(6):
            angle = self.menu_tick * 0.02 + i * math.pi / 3
            sx = VW // 2 + math.cos(angle) * 140
            sy = title_y + 10 + math.sin(angle) * 40
            size = 2 + math.sin(self.menu_tick * 0.1 + i) * 1
            pygame.draw.circle(surf, YELLOW, (int(sx), int(sy)), max(1, int(size)))

        btn_y = 350
        pulse = 1 + 0.05 * math.sin(self.menu_tick * 0.08)
        btn_w, btn_h = int(180 * pulse), int(50 * pulse)
        btn_rect = pygame.Rect(VW // 2 - btn_w // 2, btn_y, btn_w, btn_h)
        pygame.draw.rect(surf, (0, 80, 150), btn_rect, border_radius=12)
        pygame.draw.rect(surf, CYAN, btn_rect, 2, border_radius=12)
        start_txt = font_md.render("START", True, WHITE)
        surf.blit(start_txt, (VW // 2 - start_txt.get_width() // 2,
                               btn_y + btn_h // 2 - start_txt.get_height() // 2))

        if self.high_score > 0:
            hs_txt = font_sm.render(f"BEST: {self.high_score:,}", True, GOLD)
            surf.blit(hs_txt, (VW // 2 - hs_txt.get_width() // 2, btn_y + 70))

        instructions = [
            "اسحب للتحريك",
            "اطلاق تلقائي",
            "نقرة مزدوجة = قنبلة",
        ]
        for i, line in enumerate(instructions):
            txt = font_xs.render(line, True, (150, 150, 180))
            surf.blit(txt, (VW // 2 - txt.get_width() // 2, 500 + i * 25))

        draw_player_ship(surf, VW // 2, 620, shield_timer=self.menu_tick)
        return btn_rect

    def draw_gameover(self, surf):
        overlay = pygame.Surface((VW, VH), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surf.blit(overlay, (0, 0))

        go_txt = font_xl.render("GAME OVER", True, RED)
        surf.blit(go_txt, (VW // 2 - go_txt.get_width() // 2, 180))

        stats = [
            (f"SCORE: {self.score:,}", WHITE),
            (f"LEVEL: {self.level}", CYAN),
            (f"KILLS: {self.kills}", ORANGE),
            (f"TIME: {int(self.total_time)}s", YELLOW),
            (f"BEST: {self.high_score:,}", GOLD if self.score >= self.high_score else (150, 150, 150)),
        ]
        if self.score >= self.high_score and self.score > 0:
            stats.insert(0, ("NEW RECORD!", GOLD))

        for i, (text, color) in enumerate(stats):
            txt = font_md.render(text, True, color)
            surf.blit(txt, (VW // 2 - txt.get_width() // 2, 260 + i * 40))

        btn_y = 520
        btn_rect = pygame.Rect(VW // 2 - 90, btn_y, 180, 50)
        pygame.draw.rect(surf, (100, 0, 0), btn_rect, border_radius=12)
        pygame.draw.rect(surf, RED, btn_rect, 2, border_radius=12)
        retry_txt = font_md.render("RETRY", True, WHITE)
        surf.blit(retry_txt, (VW // 2 - retry_txt.get_width() // 2,
                               btn_y + 25 - retry_txt.get_height() // 2))

        btn_y2 = 590
        btn_rect2 = pygame.Rect(VW // 2 - 90, btn_y2, 180, 50)
        pygame.draw.rect(surf, (0, 0, 80), btn_rect2, border_radius=12)
        pygame.draw.rect(surf, BLUE, btn_rect2, 2, border_radius=12)
        menu_txt = font_md.render("MENU", True, WHITE)
        surf.blit(menu_txt, (VW // 2 - menu_txt.get_width() // 2,
                              btn_y2 + 25 - menu_txt.get_height() // 2))
        return btn_rect, btn_rect2

    def draw_pause(self, surf):
        overlay = pygame.Surface((VW, VH), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        surf.blit(overlay, (0, 0))
        txt = font_xl.render("PAUSED", True, WHITE)
        surf.blit(txt, (VW // 2 - txt.get_width() // 2, VH // 2 - 60))
        txt2 = font_sm.render("Tap to resume", True, (180, 180, 180))
        surf.blit(txt2, (VW // 2 - txt2.get_width() // 2, VH // 2 + 20))

    def draw_playing(self, surf):
        starfield.update()
        starfield.draw(surf)
        for p in self.powerups:
            p.draw(surf)
        for e in self.enemies:
            e.draw(surf)
        for b in self.enemy_bullets:
            b.draw(surf)
        for b in self.player_bullets:
            b.draw(surf)
        if self.state == 'playing':
            if self.invincible > 0 and self.invincible % 6 < 3:
                pass
            else:
                draw_player_ship(surf, self.player_x, self.player_y,
                               self.shield_timer, self.weapon_level)
        particles.draw(surf)
        for ft in self.floating_texts:
            ft.draw(surf)
        self.draw_hud(surf)

        pause_rect = pygame.Rect(VW - 40, VH - 45, 30, 30)
        pygame.draw.rect(surf, (40, 40, 80), pause_rect, border_radius=5)
        pygame.draw.rect(surf, WHITE, pause_rect, 1, border_radius=5)
        pygame.draw.rect(surf, WHITE, (pause_rect.x + 8, pause_rect.y + 7, 5, 16))
        pygame.draw.rect(surf, WHITE, (pause_rect.x + 17, pause_rect.y + 7, 5, 16))
        return pause_rect

    def run(self):
        running = True
        last_click_time = 0
        menu_btn = retry_btn = pause_btn = menu_btn2 = None

        # سطح الرسم الافتراضي
        game_surface = pygame.Surface((VW, VH))

        while running:
            clock.tick(FPS)
            ox, oy = shake.get_offset()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.USEREVENT + 1:
                    snd_levelup2.play()

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.state == 'playing':
                            self.state = 'paused'
                        elif self.state == 'paused':
                            self.state = 'playing'
                        elif self.state == 'menu':
                            running = False
                    elif event.key == pygame.K_SPACE and self.state == 'playing':
                        self.use_bomb()

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    gx, gy = touch_to_game(*event.pos)
                    now = pygame.time.get_ticks()
                    if self.state == 'menu':
                        if menu_btn and menu_btn.collidepoint(gx, gy):
                            snd_menu.play()
                            self.reset()
                            self.state = 'playing'
                    elif self.state == 'playing':
                        if pause_btn and pause_btn.collidepoint(gx, gy):
                            self.state = 'paused'
                            continue
                        if now - last_click_time < 300:
                            self.use_bomb()
                            last_click_time = 0
                        else:
                            last_click_time = now
                            self.touch_active = True
                            self.touch_target = (gx, gy)
                    elif self.state == 'paused':
                        self.state = 'playing'
                    elif self.state == 'gameover':
                        if retry_btn and retry_btn.collidepoint(gx, gy):
                            snd_menu.play()
                            self.reset()
                            self.state = 'playing'
                        elif menu_btn2 and menu_btn2.collidepoint(gx, gy):
                            snd_menu.play()
                            self.state = 'menu'

                elif event.type == pygame.MOUSEMOTION:
                    if self.touch_active and self.state == 'playing':
                        self.touch_target = touch_to_game(*event.pos)

                elif event.type == pygame.MOUSEBUTTONUP:
                    self.touch_active = False

                elif event.type == pygame.FINGERDOWN:
                    gx, gy = touch_to_game(event.x * SCREEN_W, event.y * SCREEN_H)
                    now = pygame.time.get_ticks()
                    if self.state == 'menu':
                        if menu_btn and menu_btn.collidepoint(gx, gy):
                            snd_menu.play()
                            self.reset()
                            self.state = 'playing'
                    elif self.state == 'playing':
                        if pause_btn and pause_btn.collidepoint(gx, gy):
                            self.state = 'paused'
                            continue
                        if now - last_click_time < 300:
                            self.use_bomb()
                            last_click_time = 0
                        else:
                            last_click_time = now
                            self.touch_active = True
                            self.touch_target = (gx, gy)
                    elif self.state == 'paused':
                        self.state = 'playing'
                    elif self.state == 'gameover':
                        if retry_btn and retry_btn.collidepoint(gx, gy):
                            snd_menu.play()
                            self.reset()
                            self.state = 'playing'
                        elif menu_btn2 and menu_btn2.collidepoint(gx, gy):
                            snd_menu.play()
                            self.state = 'menu'

                elif event.type == pygame.FINGERMOTION:
                    if self.touch_active and self.state == 'playing':
                        gx, gy = touch_to_game(event.x * SCREEN_W, event.y * SCREEN_H)
                        self.touch_target = (gx, gy)

                elif event.type == pygame.FINGERUP:
                    self.touch_active = False

            # التحديث
            if self.state == 'playing':
                self.update_playing()

            # ─── الرسم على السطح الافتراضي ثم تحجيمه ───
            game_surface.fill(DARK_BG)

            if self.state == 'menu':
                menu_btn = self.draw_menu(game_surface)
            elif self.state == 'playing':
                pause_btn = self.draw_playing(game_surface)
            elif self.state == 'paused':
                pause_btn = self.draw_playing(game_surface)
                self.draw_pause(game_surface)
            elif self.state == 'gameover':
                pause_btn = self.draw_playing(game_surface)
                retry_btn, menu_btn2 = self.draw_gameover(game_surface)

            # تحجيم ورسم على الشاشة الحقيقية
            screen.fill(BLACK)
            scaled = pygame.transform.scale(game_surface,
                                             (int(VW * GAME_SCALE), int(VH * GAME_SCALE)))
            screen.blit(scaled, (int(OFFSET_X + ox), int(OFFSET_Y + oy)))
            pygame.display.flip()

        pygame.quit()
        sys.exit()

# ──────────────────── تشغيل ────────────────────
if __name__ == '__main__':
    game = Game()
    game.run()