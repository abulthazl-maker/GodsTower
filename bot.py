import time
import random
import threading
import requests

from config import BALE_BOT_TOKEN

from database import (
    create_player, get_player, name_exists,
    set_name, set_gender, set_class,
    update_player, add_field, add_stat, get_top, get_top_power,
    get_inventory, add_item, remove_item, clear_inventory,
    get_equipment, equip_item, unequip_item, clear_equipment,
    get_titles, activate_title,
    set_busy, get_busy, clear_busy,
    delete_player, is_admin, is_owner, get_stats,
    ban_player, unban_player, get_all_player_ids, count_players,
    add_admin, remove_admin, get_admins, MAX_ADMINS,
    get_player_by_name,
    CLAN_CREATE_COST, CLAN_RANKS, CLAN_RANK_ORDER,
    CLAN_MAX_MEMBERS, TREASURY_CAP_GOLD, TREASURY_CAP_DIAMOND,
    TREASURY_CAP_ITEMS, clan_name_exists, create_clan,
    get_clan, get_clan_by_name, get_player_clan,
    get_clan_members, get_clan_members_count, set_clan_rank,
    kick_from_clan, delete_clan, add_clan_request,
    get_clan_requests, remove_clan_request, get_top_clans,
    clan_can_withdraw, update_clan, count_clans, count_groups,
    create_group, get_group, get_group_members,
    get_group_count, set_group, delete_group,
    MAX_INVENTORY, waiting,
    log_boss_drop, add_boss_kill, get_boss_kills,
)

# ═══════════════════════════════════════
# API
# ═══════════════════════════════════════

API = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}"
session = requests.Session()


def api(method, data=None, timeout=20):
    try:
        r = session.post(f"{API}/{method}", json=data or {}, timeout=timeout)
        if r.status_code == 400:
            return None
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"API Error [{method}]: {e}")
    return None


def send(chat_id, text, keyboard=None):
    d = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if keyboard:
        d["reply_markup"] = {"inline_keyboard": keyboard}
    return api("sendMessage", d)


def edit(chat_id, message_id, text, keyboard=None):
    d = {"chat_id": chat_id, "message_id": message_id,
         "text": text, "parse_mode": "HTML"}
    if keyboard:
        d["reply_markup"] = {"inline_keyboard": keyboard}
    return api("editMessageText", d)


def answer(cb_id):
    return api("answerCallbackQuery", {"callback_query_id": cb_id}, 5)


def get_updates(offset=None):
    d = {"timeout": 25}
    if offset is not None:
        d["offset"] = offset
    return api("getUpdates", d, 35)


# ═══════════════════════════════════════
# CLASSES
# ═══════════════════════════════════════

CLASSES = [
    {"key": "شمشیرزن", "name": "⚔️ شمشیرزن", "power": 15, "stamina": 15, "speed": 14, "defense": 12, "luck": 9, "chakra": 10, "description": "جنگجوی متعادل."},
    {"key": "نیزه‌دار", "name": "🔱 نیزه‌دار", "power": 14, "stamina": 14, "speed": 16, "defense": 11, "luck": 10, "chakra": 10, "description": "سریع و ماهر."},
    {"key": "نینجا", "name": "🥷 نینجا", "power": 13, "stamina": 12, "speed": 18, "defense": 10, "luck": 13, "chakra": 10, "description": "چابک و مرگبار."},
    {"key": "شمن", "name": "🔮 شمن", "power": 10, "stamina": 12, "speed": 11, "defense": 11, "luck": 12, "chakra": 20, "description": "جادوگر روحانی."},
    {"key": "نگهبان", "name": "🛡️ نگهبان", "power": 12, "stamina": 18, "speed": 10, "defense": 20, "luck": 8, "chakra": 12, "description": "سپر تیم."}
]

CLASS_ICON = {"شمشیرزن": "⚔️", "نیزه‌دار": "🔱", "نینجا": "🥷", "شمن": "🔮", "نگهبان": "🛡️"}

STAT_NAMES = {"power": "💪 قدرت", "stamina": "🛡️ استقامت",
              "speed": "⚡ سرعت", "defense": "🧱 دفاع",
              "luck": "🍀 شانس", "chakra": "🔮 چاکرا"}

# ═══════════════════════════════════════
# SKILLS — قفل 10/20/30/40/50
# ═══════════════════════════════════════

SKILL_UNLOCK_LEVELS = [10, 20, 30, 40, 50]

# هر کلاس 5 مهارت — آخری AoE
SKILLS = {
    # ⚔️ شمشیرزن
    "s1a": {"name": "⚔️ ضربه شمشیر", "multiplier": 3, "qi_cost": 30, "cooldown": 1, "class": "شمشیرزن"},
    "s1b": {"name": "🛡️ دفاع صلیبی", "absorb": 80, "qi_cost": 50, "cooldown": 3, "class": "شمشیرزن"},
    "s1c": {"name": "🌟 الهه نور", "heal_percent": 50, "qi_cost": 80, "cooldown": 3, "class": "شمشیرزن"},
    "s1d": {"name": "⚔️ برش ابعادی", "multiplier": 6, "qi_cost": 120, "cooldown": 4, "class": "شمشیرزن"},
    "s1e": {"name": "👑 قضاوت نهایی", "multiplier": 8, "qi_cost": 180, "cooldown": 6, "class": "شمشیرزن", "aoe": True},

    # 🔱 نیزه‌دار
    "s2a": {"name": "🗡️ ضربه نافذ", "multiplier": 3, "qi_cost": 30, "cooldown": 1, "class": "نیزه‌دار"},
    "s2b": {"name": "🌑 جهش سایه", "dodge": 100, "qi_cost": 45, "cooldown": 3, "class": "نیزه‌دار"},
    "s2c": {"name": "🐉 نفس اژدها", "heal_percent": 40, "qi_cost": 80, "cooldown": 3, "class": "نیزه‌دار"},
    "s2d": {"name": "☄️ نیزه آسمانی", "multiplier": 6, "qi_cost": 120, "cooldown": 4, "class": "نیزه‌دار"},
    "s2e": {"name": "⚡ آخرین نیزه", "multiplier": 8, "qi_cost": 180, "cooldown": 6, "class": "نیزه‌دار", "aoe": True},

    # 🥷 نینجا
    "s3a": {"name": "⭐ شوریکن سریع", "multiplier": 3, "qi_cost": 25, "cooldown": 1, "class": "نینجا"},
    "s3b": {"name": "🌑 سایه‌رو", "dodge": 100, "qi_cost": 40, "cooldown": 3, "class": "نینجا"},
    "s3c": {"name": "🧘 مدیتیشن", "heal_percent": 40, "qi_cost": 70, "cooldown": 3, "class": "نینجا"},
    "s3d": {"name": "💃 رقص مرگ", "multiplier": 6, "qi_cost": 130, "cooldown": 4, "class": "نینجا"},
    "s3e": {"name": "💀 برش روح", "multiplier": 8, "qi_cost": 200, "cooldown": 6, "class": "نینجا", "aoe": True},

    # 🔮 شمن
    "s4a": {"name": "☄️ شهاب‌سنگ", "multiplier": 3, "qi_cost": 30, "cooldown": 1, "class": "شمن"},
    "s4b": {"name": "🔮 سپر روحی", "absorb": 80, "qi_cost": 50, "cooldown": 3, "class": "شمن"},
    "s4c": {"name": "✨ احیای روحی", "heal_percent": 50, "qi_cost": 90, "cooldown": 3, "class": "شمن"},
    "s4d": {"name": "🌠 بارش شهاب", "multiplier": 6, "qi_cost": 130, "cooldown": 4, "class": "شمن"},
    "s4e": {"name": "⚡ قهر آسمان", "multiplier": 8, "qi_cost": 200, "cooldown": 6, "class": "شمن", "aoe": True},

    # 🛡️ نگهبان
    "s5a": {"name": "🌊 موج شکن", "multiplier": 3, "qi_cost": 35, "cooldown": 1, "class": "نگهبان"},
    "s5b": {"name": "🛡️ سپر مقدس", "absorb": 80, "qi_cost": 50, "cooldown": 3, "class": "نگهبان"},
    "s5c": {"name": "💚 نور مقدس", "heal_percent": 50, "qi_cost": 90, "cooldown": 3, "class": "نگهبان"},
    "s5d": {"name": "⚔️ نگهبان ابدی", "multiplier": 6, "qi_cost": 150, "cooldown": 4, "class": "نگهبان"},
    "s5e": {"name": "⚡ قضاوت آسمانی", "multiplier": 8, "qi_cost": 220, "cooldown": 6, "class": "نگهبان", "aoe": True},
}


def get_class_skills(cls):
    return {sid: sk for sid, sk in SKILLS.items() if sk["class"] == cls}


def get_unlocked_skills(cls, level):
    lst = list(get_class_skills(cls).items())
    n = 0
    for i, lv in enumerate(SKILL_UNLOCK_LEVELS):
        if level >= lv:
            n = i + 1
        else:
            break
    return dict(lst[:n])


def has_skills(p):
    return p["level"] >= 10 and p["player_class"] in CLASS_ICON

# ═══════════════════════════════════════
# XP — 2000 × 1.15
# ═══════════════════════════════════════

MAX_LEVEL = 100


def xp_required(lv):
    if lv >= MAX_LEVEL:
        return 0
    return round(2000 * (1.15 ** (lv - 1)))


def add_xp(uid, amount):
    p = get_player(uid)
    if not p or amount <= 0 or p["level"] >= MAX_LEVEL:
        return p
    add_field(uid, "xp", amount)
    p = get_player(uid)
    xp, lv, pts = p["xp"], p["level"], p["stat_points"]
    while lv < MAX_LEVEL:
        need = xp_required(lv)
        if xp < need:
            break
        xp -= need
        lv += 1
        pts += 5
    update_player(uid, xp=xp, level=lv, stat_points=pts)
    return get_player(uid)
  # ═══════════════════════════════════════
# محاسبات — ضریب 200
# ═══════════════════════════════════════

def calc_hp(p): return p["stamina"] * 200
def calc_dm(p): return p["power"] * 200
def calc_qi(p): return p["chakra"] * 50


def calc_dm_class(p, uid):
    if p["player_class"] == "شمن":
        b = get_item_bonus(uid)
        return (p["chakra"] + b["chakra"]) * 200
    return calc_dm_full(p, uid)


def calc_power(p, uid):
    b = get_item_bonus(uid)
    return sum([p["power"] + b["power"], p["stamina"] + b["stamina"],
                p["speed"] + b["speed"], p["defense"] + b["defense"],
                p["luck"] + b["luck"], p["chakra"] + b["chakra"]])


def calc_hp_full(p, uid):
    b = get_item_bonus(uid)
    return (p["stamina"] + b["stamina"]) * 200


def calc_dm_full(p, uid):
    b = get_item_bonus(uid)
    return (p["power"] + b["power"]) * 200


def calc_qi_full(p, uid):
    b = get_item_bonus(uid)
    return (p["chakra"] + b["chakra"]) * 50


# ═══════════════════════════════════════
# GUARDIAN
# ═══════════════════════════════════════

GUARDIAN_UNLOCK = 5


def get_guardian(p):
    if not p or p["level"] < GUARDIAN_UNLOCK:
        return None
    bonus = p["level"] - GUARDIAN_UNLOCK
    hp = 1500 + bonus * 100
    return {"name": "🛡️ نگهبان", "level": p["level"], "hp": hp,
            "max_hp": hp, "dm": 250 + bonus * 20}


# ═══════════════════════════════════════
# ITEMS
# ═══════════════════════════════════════

ITEM_SLOTS = {
    # پایه
    "شمشیر آهنی": "main", "نیزه آهنی": "main", "خنجر آهنی": "main",
    "سپر آهنی": "off", "کلاه آهنی": "head", "زره آهنی": "body",
    "شنل ساده": "cloak", "انگشتر آهنی": "ring",
    "شلوار آهنی": "legs", "کفش آهنی": "boots",
    # ایگنیس
    "شمشیر گدازه": "main", "سپر آتشین": "off", "کلاه گدازه": "head",
    "زره گدازه": "body", "شنل آتش": "cloak", "گردن‌آویز گدازه": "ring",
    "شلوار گدازه": "legs", "کفش گدازه": "boots",
    # فونیکس
    "نیزه فونیکس": "main", "سپر بال": "off", "کلاه پر": "head",
    "زره پر": "body", "شنل آتشین": "cloak", "گردن‌آویز ققنوس": "ring",
    "شلوار پر": "legs", "کفش پر": "boots",
    # نکرومنسر
    "عصای ارواح": "main", "کتاب جادو": "off", "کلاه جادوگر": "head",
    "ردای مرگ": "body", "شنل ارواح": "cloak", "گردن‌آویز روح": "ring",
    "شلوار مرگ": "legs", "کفش سایه": "boots",
    # آرک‌دمون
    "شمشیر تاریکی": "main", "سپر جهنمی": "off", "تاج تاریکی": "head",
    "زره جهنمی": "body", "شنل تاریکی": "cloak", "گردن‌آویز لرد": "ring",
    "شلوار تاریکی": "legs", "کفش جهنمی": "boots",
    # شاه عقرب
    "خنجر زهرآلود": "main", "سپر صدفی": "off", "کلاه زهر": "head",
    "زره پولادی-شنی": "body", "شنل شنی": "cloak", "گردن‌آویز عقرب": "ring",
    "شلوار زهر": "legs", "کفش شنی": "boots",
    # افعی
    "شمشیر افعی": "main", "سپر پولادی": "off", "کلاه افعی": "head",
    "زره افعی": "body", "شنل افعی": "cloak", "گردن‌آویز سم": "ring",
    "شلوار افعی": "legs", "کفش سریع": "boots",
    # ملکه عقرب
    "نیزه زهرآلود": "main", "سپر سلطنتی": "off", "تاج ملکه": "head",
    "زره سلطنتی": "body", "شنل ملکه": "cloak", "گردن‌آویز زهر": "ring",
    "شلوار سلطنتی": "legs", "کفش زهر": "boots",
    # خدای خورشید
    "شمشیر خورشیدی": "main", "سپر طلایی": "off", "تاج خورشید": "head",
    "زره طلایی": "body", "شنل خورشید": "cloak", "گردن‌آویز خورشید": "ring",
    "شلوار طلایی": "legs", "کفش خورشیدی": "boots",
}

ITEM_STATS = {
    # پایه
    "شمشیر آهنی": {"power": 5}, "نیزه آهنی": {"power": 4, "speed": 2},
    "خنجر آهنی": {"speed": 5, "luck": 2}, "سپر آهنی": {"defense": 5},
    "کلاه آهنی": {"defense": 3, "stamina": 2}, "زره آهنی": {"defense": 8, "stamina": 3},
    "شنل ساده": {"speed": 3, "luck": 2}, "انگشتر آهنی": {"luck": 5, "chakra": 3},
    "شلوار آهنی": {"defense": 4, "stamina": 2}, "کفش آهنی": {"speed": 4, "stamina": 1},
    # ایگنیس
    "شمشیر گدازه": {"power": 800, "stamina": 300},
    "سپر آتشین": {"defense": 700, "stamina": 500},
    "کلاه گدازه": {"defense": 300, "stamina": 400},
    "زره گدازه": {"defense": 600, "stamina": 500, "power": 300},
    "شنل آتش": {"speed": 400, "power": 300},
    "گردن‌آویز گدازه": {"power": 600, "stamina": 400},
    "شلوار گدازه": {"defense": 400, "stamina": 400},
    "کفش گدازه": {"speed": 500, "stamina": 300},
    # فونیکس
    "نیزه فونیکس": {"power": 1000, "speed": 800},
    "سپر بال": {"defense": 800, "stamina": 700},
    "کلاه پر": {"speed": 400, "luck": 300},
    "زره پر": {"defense": 700, "stamina": 700, "speed": 500},
    "شنل آتشین": {"speed": 600, "power": 500},
    "گردن‌آویز ققنوس": {"speed": 800, "stamina": 600},
    "شلوار پر": {"speed": 500, "defense": 400},
    "کفش پر": {"speed": 700, "luck": 400},
    # نکرومنسر
    "عصای ارواح": {"chakra": 1000, "power": 800},
    "کتاب جادو": {"chakra": 800, "defense": 700},
    "کلاه جادوگر": {"chakra": 500, "luck": 400},
    "ردای مرگ": {"defense": 800, "stamina": 800, "chakra": 600},
    "شنل ارواح": {"chakra": 700, "speed": 500},
    "گردن‌آویز روح": {"chakra": 900, "luck": 600},
    "شلوار مرگ": {"chakra": 600, "defense": 400},
    "کفش سایه": {"speed": 600, "chakra": 400},
    # آرک‌دمون
    "شمشیر تاریکی": {"power": 2000, "speed": 1000, "chakra": 1000},
    "سپر جهنمی": {"defense": 1500, "stamina": 1500},
    "تاج تاریکی": {"power": 1000, "defense": 800, "chakra": 600},
    "زره جهنمی": {"defense": 2000, "stamina": 2000, "power": 1000},
    "شنل تاریکی": {"speed": 1000, "luck": 800},
    "گردن‌آویز لرد": {"power": 1500, "chakra": 1000},
    "شلوار تاریکی": {"defense": 1200, "stamina": 1000},
    "کفش جهنمی": {"speed": 1200, "stamina": 800},
    # شاه عقرب
    "خنجر زهرآلود": {"power": 1200, "speed": 800, "luck": 600},
    "سپر صدفی": {"defense": 1000, "stamina": 900},
    "کلاه زهر": {"defense": 500, "luck": 500},
    "زره پولادی-شنی": {"defense": 900, "stamina": 900, "power": 500},
    "شنل شنی": {"speed": 800, "luck": 600},
    "گردن‌آویز عقرب": {"power": 1000, "luck": 800},
    "شلوار زهر": {"defense": 700, "stamina": 600},
    "کفش شنی": {"speed": 900, "stamina": 500},
    # افعی
    "شمشیر افعی": {"power": 1500, "speed": 1200},
    "سپر پولادی": {"defense": 1200, "stamina": 1000},
    "کلاه افعی": {"speed": 600, "defense": 500},
    "زره افعی": {"defense": 1100, "stamina": 1100, "speed": 700},
    "شنل افعی": {"speed": 1000, "luck": 800},
    "گردن‌آویز سم": {"speed": 1200, "power": 1000},
    "شلوار افعی": {"defense": 800, "stamina": 700},
    "کفش سریع": {"speed": 1200, "stamina": 600},
    # ملکه
    "نیزه زهرآلود": {"power": 1800, "chakra": 1500},
    "سپر سلطنتی": {"defense": 1500, "stamina": 1200},
    "تاج ملکه": {"chakra": 800, "luck": 700},
    "زره سلطنتی": {"defense": 1400, "stamina": 1400, "power": 1000},
    "شنل ملکه": {"speed": 1000, "chakra": 800},
    "گردن‌آویز زهر": {"chakra": 1500, "luck": 1000},
    "شلوار سلطنتی": {"defense": 1000, "stamina": 800},
    "کفش زهر": {"speed": 1000, "chakra": 800},
    # خدای خورشید
    "شمشیر خورشیدی": {"power": 2500, "speed": 1500, "chakra": 1000},
    "سپر طلایی": {"defense": 2000, "stamina": 1800},
    "تاج خورشید": {"power": 1200, "defense": 1000},
    "زره طلایی": {"defense": 2200, "stamina": 2200, "power": 1500},
    "شنل خورشید": {"speed": 1500, "luck": 1200},
    "گردن‌آویز خورشید": {"power": 2000, "chakra": 1500},
    "شلوار طلایی": {"defense": 1500, "stamina": 1200},
    "کفش خورشیدی": {"speed": 1500, "stamina": 1000},
}

STAT_ICONS = {"power": "💪", "stamina": "🛡️", "speed": "⚡",
              "defense": "🧱", "luck": "🍀", "chakra": "🔮"}


def get_item_bonus(uid):
    eq = get_equipment(uid)
    bonus = {"power": 0, "stamina": 0, "speed": 0,
             "defense": 0, "luck": 0, "chakra": 0}
    for slot, item in eq.items():
        for stat, val in ITEM_STATS.get(item, {}).items():
            bonus[stat] += val
    return bonus


# ═══════════════════════════════════════
# متغیرهای سراسری
# ═══════════════════════════════════════

battles = {}
boss_battles = {}
group_battles = {}  # نبرد گروهی


# ═══════════════════════════════════════
# DUNGEON — دشمنان
# ═══════════════════════════════════════

ENEMIES = {
    "🌱 اولیه":    [("🐄 گاو", 100), ("🐑 گوسفند", 150), ("🐔 مرغ", 200), ("🦆 اردک", 250)],
    "⚔️ آماتور":   [("🐺 گرگ", 5000), ("🐆 پلنگ", 7500), ("🐅 ببر", 10000), ("🦁 شیر", 15000)],
    "🛡️ معمولی":  [("👺 گابلین", 50000), ("🐺 سبروس", 75000), ("😈 شیطانک", 100000), ("☠️ جلاد", 150000)],
    "🔥 حرفه‌ای":  [("🐉 اژدها", 1000000), ("🧟 لیچ", 1250000), ("🌊 لویاتان", 1500000), ("⚔️ زبک", 2000000)],
    "👑 لجندری":  [("⚔️ نال", 2500000), ("🕷️ ونوم", 3000000), ("⚡ زئوس", 4000000), ("🗡️ سیلورسن", 5000000)]
}

ENEMY_XP = {
    "🌱 اولیه": 5_000,        # ← تغییر
    "⚔️ آماتور": 50_000,
    "🛡️ معمولی": 200_000,
    "🔥 حرفه‌ای": 1_000_000,
    "👑 لجندری": 5_000_000
}

LEVEL_MIN = {"🌱 اولیه": 1, "⚔️ آماتور": 11, "🛡️ معمولی": 21,
             "🔥 حرفه‌ای": 31, "👑 لجندری": 41}

# ─── مرتبه جدید ───

RANK_MULTIPLIERS = {1: 1, 2: 25, 3: 50, 4: 75, 5: 100}

RANK_NAMES = {1: "🥉 معمولی", 2: "🥈 مرتبه ۱", 3: "🥇 مرتبه ۲",
              4: "💎 مرتبه ۳", 5: "👑 مکس"}


def get_player_rank(level):
    if level < 60:
        return 1
    elif level < 70:
        return 2
    elif level < 80:
        return 3
    elif level < 90:
        return 4
    else:
        return 5


def get_rank_multiplier(rank):
    return RANK_MULTIPLIERS.get(rank, 1)


# ═══════════════════════════════════════
# HUNT
# ═══════════════════════════════════════

def start_hunt(uid, level):
    if uid in battles:
        return None
    p = get_player(uid)
    if not p:
        return None

    enemy, base_hp = random.choice(ENEMIES[level])
    rank = get_player_rank(p["level"])
    mult = get_rank_multiplier(rank)
    enemy_hp = base_hp * mult
    enemy_dm = int(enemy_hp * 0.33)

    battles[uid] = {
        "players": [{
            "uid": uid, "name": p["name"], "level": p["level"],
            "hp": calc_hp_full(p, uid), "max_hp": calc_hp_full(p, uid),
            "qi": calc_qi_full(p, uid), "max_qi": calc_qi_full(p, uid),
            "dm": calc_dm_class(p, uid), "guardian": get_guardian(p),
        }],
        "enemy": {"name": enemy, "level": LEVEL_MIN[level],
                  "hp": enemy_hp, "max_hp": enemy_hp, "dm": enemy_dm,
                  "rank": rank, "rank_name": RANK_NAMES[rank]},
        "level": level, "start": time.time(), "skill_cd": {},
    }
    return battles[uid]


def battle_text(uid):
    b = battles.get(uid)
    if not b:
        return "⚔️ نبردی نیست."
    pl = b["players"][0]
    en = b["enemy"]
    lines = ["⚔️━━━━━━━━━━━━━━━━⚔️",
             "      <b>𝐁𝐀𝐓𝐓𝐋𝐄</b>",
             "⚔️━━━━━━━━━━━━━━━━⚔️", "",
             "╭━━━━━━━━━━━━━━━━╮",
             f"┃ 👤 <b>{pl['name']}</b> | Lv.{pl['level']}",
             f"┃ ❤️ {pl['hp']:,}",
             f"┃ 🔵 {pl['qi']:,}/{pl['max_qi']:,}"]
    g = pl.get("guardian")
    if g and g["hp"] > 0:
        lines.append("┃")
        lines.append(f"┃ {g['name']} | Lv.{g['level']}")
        lines.append(f"┃    ❤️ {g['hp']:,}  ⚔️ {g['dm']:,}")
    lines += ["╰━━━━━━━━━━━━━━━━╯", "",
              "         ⚔️ <b>VS</b> ⚔️", "",
              "╭━━━━━━━━━━━━━━━━╮",
              f"┃ <b>{en['name']}</b> | Lv.{en['level']}",
              f"┃ {en['rank_name']}",
              f"┃ ❤️ {max(0, en['hp']):,}",
              "╰━━━━━━━━━━━━━━━━╯",
              "⚔️━━━━━━━━━━━━━━━━⚔️"]
    return "\n".join(lines)


def battle_keyboard(uid):
    p = get_player(uid)
    kb = [[{"text": "⚔️ حمله", "callback_data": "attack"},
           {"text": "🏃 فرار", "callback_data": "run"}]]
    if p and has_skills(p):
        kb[0].insert(1, {"text": "🔮 مهارت", "callback_data": "skill_menu"})
    return kb


def player_attack(uid):
    p = get_player(uid)
    b = battles.get(uid)
    if not p:
        return None
    if not b:
        return "⚔️ <b>نبردی نیست.</b>"

    pl = b["players"][0]
    en = b["enemy"]
    dmg_p = max(1, pl["dm"])
    en["hp"] -= dmg_p

    dmg_g = 0
    g = pl.get("guardian")
    if g and g["hp"] > 0:
        dmg_g = max(1, g["dm"])
        en["hp"] -= dmg_g

    total = dmg_p + dmg_g

    for sk in list(b.get("skill_cd", {}).keys()):
        b["skill_cd"][sk] -= 1
        if b["skill_cd"][sk] <= 0:
            del b["skill_cd"][sk]

    if en["hp"] <= 0:
        gained = ENEMY_XP[b["level"]] * get_rank_multiplier(en["rank"])
        gold = gained // 2
        en_name, rank_name = en["name"], en["rank_name"]
        battles.pop(uid, None)
        add_xp(uid, gained)
        add_field(uid, "gold", gold)
        add_field(uid, "kills", 1)
        return ("🏆━━━━━━━━━━━━━━━━━🏆\n"
                "      <b>𝐕𝐈𝐂𝐓𝐎𝐑𝐘</b>\n"
                "🏆━━━━━━━━━━━━━━━━━🏆\n\n"
                f"☠️ <b>{pl['name']}</b> » {en_name}\n"
                f"        {rank_name}\n\n"
                "╭━━━━━━━━━━━━━━━━╮\n"
                f"┃ 💥 آسیب: <b>{total:,}</b>\n"
                f"┃ ✨ تجربه: <b>{gained:,}</b>\n"
                f"┃ 🪙 طلا: <b>{gold:,}</b>\n"
                "╰━━━━━━━━━━━━━━━━╯")

    edmg = en["dm"]
    red = min(p["defense"] * 0.1, 80)
    edmg = max(1, int(edmg * (1 - red / 100)))

    if g and g["hp"] > 0:
        gd = edmg // 2
        pl["hp"] -= edmg - gd
        g["hp"] -= gd
        if g["hp"] <= 0:
            g["hp"] = 0
    else:
        pl["hp"] -= edmg

    if pl["hp"] <= 0:
        en_name = en["name"]
        battles.pop(uid, None)
        add_field(uid, "deaths", 1)
        return ("💀━━━━━━━━━━━━━━━━━💀\n"
                "      💀 <b>شکست</b> 💀\n"
                "💀━━━━━━━━━━━━━━━━━💀\n\n"
                f"☠️ {en_name} زنده ماند...")
    return battle_text(uid)


def use_skill(uid, sid):
    p = get_player(uid)
    b = battles.get(uid)
    if not p or not b:
        return None
    sk = SKILLS.get(sid)
    if not sk or sk["class"] != p["player_class"]:
        return "❌"
    if sid not in get_unlocked_skills(p["player_class"], p["level"]):
        return "❌ مهارت باز نشده!"

    pl = b["players"][0]
    en = b["enemy"]
    cd = b.get("skill_cd", {}).get(sid, 0)
    if cd > 0:
        return f"⏳ کول‌داون! {cd} نوبت."
    if pl["qi"] < sk["qi_cost"]:
        return f"❌ QI کافی نیست! نیاز: {sk['qi_cost']}"

    pl["qi"] -= sk["qi_cost"]

    if "multiplier" in sk:
        dmg = pl["dm"] * sk["multiplier"]
        en["hp"] -= dmg
        result = f"{sk['name']}\n💥 دمیج: <b>{dmg:,}</b>"
    elif "heal_percent" in sk:
        heal = (pl["max_hp"] * sk["heal_percent"]) // 100
        pl["hp"] = min(pl["max_hp"], pl["hp"] + heal)
        result = f"{sk['name']}\n💚 HP: <b>{pl['hp']:,}</b>"
    elif "dodge" in sk or "absorb" in sk:
        result = f"{sk['name']}\n✨ آماده دفاع!"
        b["pending_defense"] = sk
    else:
        return "❌"

    b["skill_cd"][sid] = sk["cooldown"]

    if en["hp"] <= 0:
        gained = ENEMY_XP[b["level"]] * get_rank_multiplier(en["rank"])
        gold = gained // 2
        en_name, rank_name = en["name"], en["rank_name"]
        battles.pop(uid, None)
        add_xp(uid, gained)
        add_field(uid, "gold", gold)
        add_field(uid, "kills", 1)
        return (f"{result}\n\n🏆━━━━━━━━━━━━━━━━━🏆\n"
                f"☠️ <b>{en_name}</b> نابود شد.\n"
                f"        {rank_name}\n\n"
                f"✨ تجربه: <b>{gained:,}</b>\n"
                f"🪙 طلا: <b>{gold:,}</b>")

    edmg = en["dm"]
    red = min(p["defense"] * 0.1, 80)
    edmg = max(1, int(edmg * (1 - red / 100)))

    pending = b.get("pending_defense")
    if pending:
        if "dodge" in pending:
            edmg = 0
        elif "absorb" in pending:
            edmg = int(edmg * (1 - pending["absorb"] / 100))
        b.pop("pending_defense", None)

    g = pl.get("guardian")
    if g and g["hp"] > 0 and edmg > 0:
        gd = edmg // 2
        pl["hp"] -= edmg - gd
        g["hp"] -= gd
        if g["hp"] <= 0:
            g["hp"] = 0
    elif edmg > 0:
        pl["hp"] -= edmg

    if pl["hp"] <= 0:
        battles.pop(uid, None)
        add_field(uid, "deaths", 1)
        return f"{result}\n\n💀 شکست خوردی..."
    return f"{result}\n\n" + battle_text(uid)


def skill_menu_battle(uid):
    p = get_player(uid)
    b = battles.get(uid)
    if not p or not b or not has_skills(p):
        return "❌", []

    pl = b["players"][0]
    cds = b.get("skill_cd", {})
    unlocked = get_unlocked_skills(p["player_class"], p["level"])

    kb = []
    for sid, sk in unlocked.items():
        cd = cds.get(sid, 0)
        can = pl["qi"] >= sk["qi_cost"] and cd == 0
        icon = "✅" if can else "🔒"
        cd_txt = f" — {cd}" if cd > 0 else ""
        kb.append([{"text": f"{icon} {sk['name']} (QI:{sk['qi_cost']}){cd_txt}",
                    "callback_data": f"skill:{sid}" if can else "skill_noop"}])
    kb.append([{"text": "◀️ بازگشت", "callback_data": "skill_back"}])

    text = (f"🔮 <b>مهارت‌های {p['player_class']}</b>\n\n"
            f"🔵 QI: <b>{pl['qi']:,}/{pl['max_qi']:,}</b>")
    return text, kb


def scout(uid):
    r = random.random()
    if r < 0.001:
        add_field(uid, "diamonds", 1)
        return "💎 الماس ×1"
    if r < 0.15:
        g = random.randint(100, 5000)
        add_field(uid, "gold", g)
        return f"💰 +{g:,} طلا"
    item = random.choice(["🦴 استخون", "🐾 لاشه", "🍎 میوه"])
    if add_item(uid, item):
        return f"{item} ×1"
    return "🎒 پر است."


def dungeon_farm(uid, chat_id):
    if get_busy(uid):
        return False
    res = random.choice(["⛏️ سنگ آهن", "🌿 جینسینگ", "🍃 برگ هلو", "🖤 سنگ فولاد"])
    set_busy(uid, "farm", time.time() + 10, res)

    def fin():
        time.sleep(10)
        b = get_busy(uid)
        if b and b["type"] == "farm":
            clear_busy(uid)
            if add_item(uid, res):
                send(chat_id, f"✅ فارم کامل! 🎁 {res}",
                     [[{"text": "🎒", "callback_data": "inventory"}]])
            else:
                send(chat_id, "⚠️ کیف پر!")

    threading.Thread(target=fin, daemon=True).start()
    return res


def camp(uid, chat_id):
    if get_busy(uid):
        return False
    set_busy(uid, "camp", time.time() + 10, None)

    def fin():
        time.sleep(10)
        b = get_busy(uid)
        if not b or b["type"] != "camp":
            return
        clear_busy(uid)
        p = get_player(uid)
        mx = calc_hp_full(p, uid)
        m = random.randint(1, 4)
        if m == 1:
            nhp, txt = mx, "❤️ HP کاملاً بازیابی شد!"
        elif m == 2:
            nhp, txt = mx // 2, "❤️ نصف شد."
        elif m == 3:
            nhp, txt = p["hp"], "☁️ تغییری نشد."
        else:
            nhp, txt = max(1, p["hp"] - mx // 10), "⚠️ HP از دست رفت!"
        update_player(uid, hp=nhp)
        send(chat_id, f"✅ اتراق!\n{txt}\n❤️ {nhp:,}/{mx:,}",
             [[{"text": "🏰", "callback_data": "dungeon"}]])

    threading.Thread(target=fin, daemon=True).start()
    return True
  # ═══════════════════════════════════════
# REGIONS
# ═══════════════════════════════════════

REGIONS = {
    "🌋 آتشفشان جهنمی": {
        "min_level": 50,
        "desc": "منطقه‌ای سوزان که باس‌های افسانه‌ای در آن زندگی می‌کنند.",
        "bosses": [
            {"key": "ignis", "name": "🐉 ایگنیس، ارباب گدازه", "level": 50,
             "hp": 1_500_000, "dm": 15_000, "defense": 400, "unlock_level": 50,
             "drops": [
                 {"item": "شمشیر گدازه", "chance": 12}, {"item": "سپر آتشین", "chance": 12},
                 {"item": "کلاه گدازه", "chance": 15}, {"item": "زره گدازه", "chance": 10},
                 {"item": "شنل آتش", "chance": 15}, {"item": "گردن‌آویز گدازه", "chance": 10},
                 {"item": "شلوار گدازه", "chance": 15}, {"item": "کفش گدازه", "chance": 15},
                 {"item": "جعبه برنزی", "chance": 25},
             ]},
            {"key": "phoenix", "name": "🔥 فونیکس خاکستر", "level": 55,
             "hp": 2_500_000, "dm": 25_000, "defense": 500, "unlock_level": 55,
             "drops": [
                 {"item": "نیزه فونیکس", "chance": 12}, {"item": "سپر بال", "chance": 12},
                 {"item": "کلاه پر", "chance": 15}, {"item": "زره پر", "chance": 10},
                 {"item": "شنل آتشین", "chance": 15}, {"item": "گردن‌آویز ققنوس", "chance": 10},
                 {"item": "شلوار پر", "chance": 15}, {"item": "کفش پر", "chance": 15},
                 {"item": "جعبه نقره‌ای", "chance": 25},
             ]},
            {"key": "necromancer", "name": "💀 نکرومنسر آتشفشان", "level": 60,
             "hp": 4_000_000, "dm": 40_000, "defense": 600, "unlock_level": 60,
             "drops": [
                 {"item": "عصای ارواح", "chance": 12}, {"item": "کتاب جادو", "chance": 12},
                 {"item": "کلاه جادوگر", "chance": 15}, {"item": "ردای مرگ", "chance": 10},
                 {"item": "شنل ارواح", "chance": 15}, {"item": "گردن‌آویز روح", "chance": 10},
                 {"item": "شلوار مرگ", "chance": 15}, {"item": "کفش سایه", "chance": 15},
                 {"item": "جعبه طلایی", "chance": 20},
             ]},
            {"key": "archdemon", "name": "🌑 آرک‌دمون، لرد آتشفشان", "level": 65,
             "hp": 7_500_000, "dm": 70_000, "defense": 800, "unlock_level": 65,
             "drops": [
                 {"item": "شمشیر تاریکی", "chance": 5}, {"item": "سپر جهنمی", "chance": 5},
                 {"item": "تاج تاریکی", "chance": 8}, {"item": "زره جهنمی", "chance": 5},
                 {"item": "شنل تاریکی", "chance": 10}, {"item": "گردن‌آویز لرد", "chance": 8},
                 {"item": "شلوار تاریکی", "chance": 10}, {"item": "کفش جهنمی", "chance": 10},
                 {"item": "جعبه آتشفشانی", "chance": 20},
                 {"item": "کلید باس مخفی", "chance": 8},
             ]},
        ]
    },
    "🏜️ بیابان مرگ": {
        "min_level": 65,
        "desc": "بیابانی خشک و بی‌رحم.",
        "bosses": [
            {"key": "scorpion_king", "name": "🏜️ شاه عقرب", "level": 65,
             "hp": 6_000_000, "dm": 55_000, "defense": 700, "unlock_level": 65,
             "drops": [
                 {"item": "خنجر زهرآلود", "chance": 12}, {"item": "سپر صدفی", "chance": 12},
                 {"item": "کلاه زهر", "chance": 15}, {"item": "زره پولادی-شنی", "chance": 10},
                 {"item": "شنل شنی", "chance": 15}, {"item": "گردن‌آویز عقرب", "chance": 10},
                 {"item": "شلوار زهر", "chance": 15}, {"item": "کفش شنی", "chance": 15},
                 {"item": "جعبه طلایی", "chance": 25},
             ]},
            {"key": "sand_viper", "name": "🐍 افعی شنی", "level": 70,
             "hp": 8_000_000, "dm": 70_000, "defense": 750, "unlock_level": 70,
             "drops": [
                 {"item": "شمشیر افعی", "chance": 12}, {"item": "سپر پولادی", "chance": 12},
                 {"item": "کلاه افعی", "chance": 15}, {"item": "زره افعی", "chance": 10},
                 {"item": "شنل افعی", "chance": 15}, {"item": "گردن‌آویز سم", "chance": 10},
                 {"item": "شلوار افعی", "chance": 15}, {"item": "کفش سریع", "chance": 15},
                 {"item": "جعبه طلایی", "chance": 25},
             ]},
            {"key": "scorpion_queen", "name": "🦂 ملکه عقرب", "level": 75,
             "hp": 10_000_000, "dm": 85_000, "defense": 850, "unlock_level": 75,
             "drops": [
                 {"item": "نیزه زهرآلود", "chance": 12}, {"item": "سپر سلطنتی", "chance": 12},
                 {"item": "تاج ملکه", "chance": 15}, {"item": "زره سلطنتی", "chance": 10},
                 {"item": "شنل ملکه", "chance": 15}, {"item": "گردن‌آویز زهر", "chance": 10},
                 {"item": "شلوار سلطنتی", "chance": 15}, {"item": "کفش زهر", "chance": 15},
                 {"item": "جعبه آتشفشانی", "chance": 20},
             ]},
            {"key": "sun_god", "name": "☀️ خدای خورشید", "level": 80,
             "hp": 13_000_000, "dm": 110_000, "defense": 1000, "unlock_level": 80,
             "drops": [
                 {"item": "شمشیر خورشیدی", "chance": 5}, {"item": "سپر طلایی", "chance": 5},
                 {"item": "تاج خورشید", "chance": 8}, {"item": "زره طلایی", "chance": 5},
                 {"item": "شنل خورشید", "chance": 10}, {"item": "گردن‌آویز خورشید", "chance": 8},
                 {"item": "شلوار طلایی", "chance": 10}, {"item": "کفش خورشیدی", "chance": 10},
                 {"item": "جعبه آتشفشانی", "chance": 20},
             ]},
        ]
    }
}


# ═══════════════════════════════════════
# BOSS SYSTEM — تکی
# ═══════════════════════════════════════

def boss_regions_menu(level=1):
    kb = []
    for rname, r in REGIONS.items():
        if level >= r["min_level"]:
            kb.append([{"text": f"{rname} (Lv.{r['min_level']}+)",
                        "callback_data": f"boss:region:{rname}"}])
        else:
            kb.append([{"text": f"🔒 {rname} (Lv.{r['min_level']}+)",
                        "callback_data": "boss:locked"}])
    kb.append([{"text": "◀️ بازگشت", "callback_data": "dungeon"}])
    return kb


def boss_region_menu(rname, player_level=1):
    r = REGIONS.get(rname)
    if not r:
        return [], ""
    kb = []
    for b in r["bosses"]:
        if player_level >= b["unlock_level"]:
            kb.append([{"text": f"{b['name']} (Lv.{b['level']})",
                        "callback_data": f"boss:select:{rname}:{b['key']}"}])
        else:
            kb.append([{"text": f"🔒 {b['name']} (Lv.{b['unlock_level']}+)",
                        "callback_data": "boss:locked"}])
    kb.append([{"text": "◀️ بازگشت", "callback_data": "boss:regions"}])
    text = (f"{rname}\n\n━━━━━━━━━━━━━━━━━━\n\n"
            f"📖 {r['desc']}\n\n🎯 حداقل سطح: <b>{r['min_level']}</b>\n"
            f"👹 تعداد باس‌ها: <b>{len(r['bosses'])}</b>")
    return kb, text


def boss_select_text(rname, bkey):
    r = REGIONS.get(rname)
    if not r:
        return None, []
    b = next((x for x in r["bosses"] if x["key"] == bkey), None)
    if not b:
        return None, []
    xp = b["hp"] * 2
    gold = xp // 2
    text = (f"{b['name']}\n\n━━━━━━━━━━━━━━━━━━\n\n"
            f"⭐ لول: <b>{b['level']}</b>\n"
            f"❤️ HP: <b>{b['hp']:,}</b>\n"
            f"⚔️ دمیج: <b>{b['dm']:,}</b>\n"
            f"🧱 دفاع: <b>{b['defense']}</b>\n\n"
            f"✨ تجربه: <b>{xp:,}</b>\n"
            f"🪙 طلا: <b>{gold:,}</b>\n\n"
            "🎁 <b>دراپ‌ها:</b>\n")
    for d in b["drops"][:5]:
        text += f"  • {d['item']} ({d['chance']}%)\n"
    if len(b["drops"]) > 5:
        text += f"  • و {len(b['drops']) - 5} آیتم دیگه...\n"
    kb = [[{"text": "⚔️ نبرد", "callback_data": f"boss:fight:{rname}:{bkey}"}],
          [{"text": "◀️ بازگشت", "callback_data": f"boss:region:{rname}"}]]
    return text, kb


def start_boss_battle(uid, rname, bkey):
    p = get_player(uid)
    r = REGIONS.get(rname)
    if not p or not r:
        return None
    if p["level"] < r["min_level"]:
        return "level_low"
    b = next((x for x in r["bosses"] if x["key"] == bkey), None)
    if not b:
        return None
    if p["level"] < b["unlock_level"]:
        return "locked"

    boss_battles[uid] = {
        "player": {
            "uid": uid, "name": p["name"], "level": p["level"],
            "hp": calc_hp_full(p, uid), "max_hp": calc_hp_full(p, uid),
            "qi": calc_qi_full(p, uid), "max_qi": calc_qi_full(p, uid),
            "dm": calc_dm_class(p, uid),
        },
        "boss": {
            "key": b["key"], "name": b["name"], "level": b["level"],
            "hp": b["hp"], "max_hp": b["hp"], "dm": b["dm"],
            "defense": b["defense"], "drops": b["drops"],
            "xp": b["hp"] * 2, "gold": b["hp"],
        },
        "region": rname, "start": time.time(), "skill_cd": {},
    }
    return boss_battles[uid]


def boss_battle_text(uid):
    b = boss_battles.get(uid)
    if not b:
        return "⚔️ نبردی نیست."
    pl, bo = b["player"], b["boss"]
    hp_pct = max(0, pl["hp"]) * 100 // pl["max_hp"]
    bo_pct = max(0, bo["hp"]) * 100 // bo["max_hp"]
    hp_bar = "█" * (hp_pct // 10) + "░" * (10 - hp_pct // 10)
    bo_bar = "█" * (bo_pct // 10) + "░" * (10 - bo_pct // 10)
    return ("🌋━━━━━━━━━━━━━━━━━━🌋\n"
            "      <b>𝐁𝐎𝐒𝐒 𝐁𝐀𝐓𝐓𝐋𝐄</b>\n"
            "🌋━━━━━━━━━━━━━━━━━━🌋\n\n"
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            f"┃ 👤 <b>{pl['name']}</b> | Lv.{pl['level']}\n"
            f"┃ ❤️ {pl['hp']:,}/{pl['max_hp']:,}\n"
            f"┃ [{hp_bar}]\n"
            f"┃ 🔵 QI: {pl['qi']:,}/{pl['max_qi']:,}\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            "         ⚔️ <b>VS</b> ⚔️\n\n"
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            f"┃ {bo['name']}\n┃ Lv.{bo['level']}\n"
            f"┃ ❤️ {max(0, bo['hp']):,}/{bo['max_hp']:,}\n"
            f"┃ [{bo_bar}]\n"
            f"┃ ⚔️ دمیج: {bo['dm']:,}\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n"
            "🌋━━━━━━━━━━━━━━━━━━🌋")


def boss_battle_keyboard(uid):
    p = get_player(uid)
    kb = [[{"text": "⚔️ حمله", "callback_data": "boss:attack"},
           {"text": "🏃 فرار", "callback_data": "boss:run"}]]
    if p and has_skills(p):
        kb[0].insert(1, {"text": "🔮 مهارت", "callback_data": "boss:skill_menu"})
    return kb


def _boss_victory(uid):
    b = boss_battles.get(uid)
    if not b:
        return None
    bo = b["boss"]
    rname = b["region"]

    add_xp(uid, bo["xp"])
    add_field(uid, "gold", bo["gold"])
    add_field(uid, "kills", 1)
    add_boss_kill(uid, bo["key"])

    dropped, failed = [], []
    for d in bo["drops"]:
        if random.randint(1, 100) <= d["chance"]:
            if add_item(uid, d["item"], 1):
                dropped.append(d["item"])
                log_boss_drop(uid, bo["key"], d["item"])
            else:
                failed.append(d["item"])

    boss_battles.pop(uid, None)
    kills = get_boss_kills(uid).get(bo["key"], 0)

    text = ("🏆━━━━━━━━━━━━━━━━━🏆\n"
            "      <b>𝐕𝐈𝐂𝐓𝐎𝐑𝐘</b>\n"
            "🏆━━━━━━━━━━━━━━━━━🏆\n\n"
            f"☠️ <b>{bo['name']}</b> نابود شد!\n"
            f"🎯 کشتار: <b>{kills}x</b>\n\n"
            "╭━━━━━━━━━━━━━━━━━━╮\n"
            f"┃ 🌋 منطقه: {rname}\n"
            f"┃ ✨ تجربه: <b>{bo['xp']:,}</b>\n"
            f"┃ 🪙 طلا: <b>{bo['gold']:,}</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n")
    if dropped:
        text += "🎁 <b>دراپ‌ها:</b>\n"
        for i in dropped:
            text += f"  ✅ {i}\n"
    else:
        text += "🎁 <b>دراپ:</b> ❌ هیچی\n"
    if failed:
        text += "\n⚠️ کیف پر بود:\n"
        for i in failed:
            text += f"  ⚠️ {i}\n"
    return text


def boss_player_attack(uid):
    p = get_player(uid)
    b = boss_battles.get(uid)
    if not p or not b:
        return None
    pl, bo = b["player"], b["boss"]
    dmg = max(1, int(pl["dm"] * (1 - min(bo["defense"] / 1000, 0.5))))
    bo["hp"] -= dmg
    for sk in list(b.get("skill_cd", {}).keys()):
        b["skill_cd"][sk] -= 1
        if b["skill_cd"][sk] <= 0:
            del b["skill_cd"][sk]
    if bo["hp"] <= 0:
        return _boss_victory(uid)
    edmg = max(1, int(bo["dm"] * (1 - min(p["defense"] * 0.1, 80) / 100)))
    pl["hp"] -= edmg
    if pl["hp"] <= 0:
        boss_battles.pop(uid, None)
        add_field(uid, "deaths", 1)
        return (f"💀━━━━━━━━━━━━━━━━━💀\n"
                f"      💀 <b>شکست</b> 💀\n"
                f"💀━━━━━━━━━━━━━━━━━💀\n\n"
                f"☠️ <b>{bo['name']}</b> زنده ماند...")
    return boss_battle_text(uid)


def boss_use_skill(uid, sid):
    p = get_player(uid)
    b = boss_battles.get(uid)
    if not p or not b:
        return None
    sk = SKILLS.get(sid)
    if not sk or sk["class"] != p["player_class"]:
        return "❌"
    if sid not in get_unlocked_skills(p["player_class"], p["level"]):
        return "❌ باز نشده!"
    pl, bo = b["player"], b["boss"]
    cd = b.get("skill_cd", {}).get(sid, 0)
    if cd > 0:
        return f"⏳ کول‌داون! {cd}"
    if pl["qi"] < sk["qi_cost"]:
        return f"❌ QI کم! نیاز: {sk['qi_cost']}"
    pl["qi"] -= sk["qi_cost"]

    if "multiplier" in sk:
        dmg = max(1, int(pl["dm"] * sk["multiplier"] * (1 - min(bo["defense"] / 1000, 0.5))))
        bo["hp"] -= dmg
        result = f"{sk['name']}\n💥 دمیج: <b>{dmg:,}</b>"
    elif "heal_percent" in sk:
        heal = (pl["max_hp"] * sk["heal_percent"]) // 100
        pl["hp"] = min(pl["max_hp"], pl["hp"] + heal)
        result = f"{sk['name']}\n💚 HP: <b>{pl['hp']:,}</b>"
    elif "dodge" in sk or "absorb" in sk:
        result = f"{sk['name']}\n✨ دفاع!"
        b["pending_defense"] = sk
    else:
        return "❌"

    b["skill_cd"][sid] = sk["cooldown"]
    if bo["hp"] <= 0:
        return _boss_victory(uid)

    edmg = max(1, int(bo["dm"] * (1 - min(p["defense"] * 0.1, 80) / 100)))
    pending = b.get("pending_defense")
    if pending:
        if "dodge" in pending:
            edmg = 0
        elif "absorb" in pending:
            edmg = int(edmg * (1 - pending["absorb"] / 100))
        b.pop("pending_defense", None)
    pl["hp"] -= edmg
    if pl["hp"] <= 0:
        boss_battles.pop(uid, None)
        add_field(uid, "deaths", 1)
        return f"{result}\n\n💀 شکست..."
    return f"{result}\n\n" + boss_battle_text(uid)


def boss_skill_menu(uid):
    p = get_player(uid)
    b = boss_battles.get(uid)
    if not p or not b or not has_skills(p):
        return "❌", []
    pl = b["player"]
    cds = b.get("skill_cd", {})
    unlocked = get_unlocked_skills(p["player_class"], p["level"])
    kb = []
    for sid, sk in unlocked.items():
        cd = cds.get(sid, 0)
        can = pl["qi"] >= sk["qi_cost"] and cd == 0
        icon = "✅" if can else "🔒"
        cd_txt = f" — {cd}" if cd > 0 else ""
        kb.append([{"text": f"{icon} {sk['name']} (QI:{sk['qi_cost']}){cd_txt}",
                    "callback_data": f"boss:skill:{sid}" if can else "boss:skill_noop"}])
    kb.append([{"text": "◀️ بازگشت", "callback_data": "boss:skill_back"}])
    text = f"🔮 <b>{p['player_class']}</b>\n🔵 QI: <b>{pl['qi']:,}</b>"
    return text, kb


# ═══════════════════════════════════════
# GROUP BATTLE — نبرد گروهی نوبتی
# ═══════════════════════════════════════

# ساختار:
# group_battles[group_id] = {
#   "players": [ {uid, name, level, hp, max_hp, qi, max_qi, dm, alive} ],
#   "bosses":  [ {key, name, hp, max_hp, dm, defense, owner_uid} ],
#   "turn": 0,           # 0-4 = بازیکن‌ها، 5 = باس‌ها
#   "round": 1,
#   "region": str,
#   "boss_key": str,
#   "chat_id": int,
#   "msg_id": int,
# }

def start_group_battle(uid, rname, bkey):
    """شروع نبرد گروهی — رئیس گروه"""
    p = get_player(uid)
    if not p or not p["group_id"]:
        return "no_group"

    gid = p["group_id"]
    g = get_group(gid)
    if not g or g["leader_id"] != uid:
        return "not_leader"

    if gid in group_battles:
        return "in_battle"

    r = REGIONS.get(rname)
    if not r:
        return "no_region"
    boss_data = next((x for x in r["bosses"] if x["key"] == bkey), None)
    if not boss_data:
        return "no_boss"

    members = get_group_members(gid, 5)
    if len(members) < 1:
        return "no_members"

    players = []
    bosses = []
    for m in members:
        p2 = get_player(m["user_id"])
        if not p2:
            continue
        players.append({
            "uid": p2["user_id"], "name": p2["name"], "level": p2["level"],
            "hp": calc_hp_full(p2, p2["user_id"]),
            "max_hp": calc_hp_full(p2, p2["user_id"]),
            "qi": calc_qi_full(p2, p2["user_id"]),
            "max_qi": calc_qi_full(p2, p2["user_id"]),
            "dm": calc_dm_class(p2, p2["user_id"]),
            "alive": True,
        })
        # هر بازیکن یه باس
        bosses.append({
            "key": boss_data["key"],
            "name": boss_data["name"],
            "hp": boss_data["hp"], "max_hp": boss_data["hp"],
            "dm": boss_data["dm"], "defense": boss_data["defense"],
            "owner_uid": p2["user_id"],  # باس مال این بازیکن
            "alive": True,
        })

    group_battles[gid] = {
        "players": players,
        "bosses": bosses,
        "turn": 0,
        "round": 1,
        "region": rname,
        "boss_key": bkey,
        "gid": gid,
        "skill_cd": {},
        "pending_defense": {},
        "start": time.time(),
    }
    return group_battles[gid]


def group_battle_text(gid):
    b = group_battles.get(gid)
    if not b:
        return "⚔️ نبردی نیست."

    lines = ["🌋━━━━━━━━━━━━━━━━━🌋",
             "   <b>𝐆𝐑𝐎𝐔𝐏 𝐁𝐀𝐓𝐓𝐋𝐄</b>",
             "   👥 نبرد گروهی",
             "🌋━━━━━━━━━━━━━━━━━🌋",
             f"🎯 راند: <b>{b['round']}</b>",
             ""]

    # بازیکن‌ها
    lines.append("👥 <b>بازیکن‌ها:</b>")
    for i, pl in enumerate(b["players"]):
        if not pl["alive"]:
            lines.append(f"  {i+1}. 💀 <b>{pl['name']}</b> (مرده)")
        else:
            marker = "🔸" if b["turn"] == i else "  "
            lines.append(f"{marker} {i+1}. <b>{pl['name']}</b> | Lv.{pl['level']}")
            lines.append(f"     ❤️ {pl['hp']:,}/{pl['max_hp']:,}")
    lines.append("")

    # باس‌ها
    lines.append("👹 <b>باس‌ها:</b>")
    for i, bo in enumerate(b["bosses"]):
        if not bo["alive"]:
            lines.append(f"  {i+1}. ☠️ <b>{bo['name']}</b> (مرده)")
        else:
            lines.append(f"  {i+1}. {bo['name']}")
            lines.append(f"     ❤️ {max(0, bo['hp']):,}/{bo['max_hp']:,}")

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━")
    if b["turn"] < 5:
        # نوبت بازیکن
        cur = b["players"][b["turn"]]
        if cur["alive"]:
            lines.append(f"🎯 نوبت: <b>{cur['name']}</b>")
        else:
            lines.append(f"⏭️ نوبت <b>{cur['name']}</b> — مرده، رد شد")
    else:
        lines.append("👹 نوبت <b>باس‌ها</b>")
    lines.append("━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)


def group_battle_keyboard(gid):
    b = group_battles.get(gid)
    if not b:
        return []
    if b["turn"] >= 5:
        return [[{"text": "▶️ ادامه (باس‌ها)", "callback_data": f"gb:monster:{gid}"}]]
    cur = b["players"][b["turn"]]
    if not cur["alive"]:
        return [[{"text": "⏭️ رد کردن نوبت", "callback_data": f"gb:skip:{gid}"}]]
    p2 = get_player(cur["uid"])
    kb = [[{"text": "⚔️ حمله", "callback_data": f"gb:attack:{gid}"}]]
    if p2 and has_skills(p2):
        kb[0].insert(1, {"text": "🔮 مهارت", "callback_data": f"gb:skill_menu:{gid}"})
    kb.append([{"text": "🏃 فرار گروهی", "callback_data": f"gb:run:{gid}"}])
    return kb


def gb_player_attack(gid):
    b = group_battles.get(gid)
    if not b:
        return None
    t = b["turn"]
    if t >= 5:
        return None
    pl = b["players"][t]
    if not pl["alive"]:
        b["turn"] += 1
        return group_battle_text(gid)

    # باس صاحب این بازیکن
    boss = next((x for x in b["bosses"] if x["owner_uid"] == pl["uid"] and x["alive"]), None)
    if not boss:
        # باسش مرده، بره سراغ باس بعدی
        boss = next((x for x in b["bosses"] if x["alive"]), None)
    if not boss:
        # همه باس‌ها مردن → پیروزی
        return gb_victory(gid)

    dmg = max(1, int(pl["dm"] * (1 - min(boss["defense"] / 1000, 0.5))))
    boss["hp"] -= dmg

    # کول‌داون بازیکن
    key = f"{pl['uid']}_{gid}"
    cds = b["skill_cd"].get(pl["uid"], {})
    for sk in list(cds.keys()):
        cds[sk] -= 1
        if cds[sk] <= 0:
            del cds[sk]
    b["skill_cd"][pl["uid"]] = cds

    if boss["hp"] <= 0:
        boss["alive"] = False
        boss["hp"] = 0

    # چک برد
    if not any(x["alive"] for x in b["bosses"]):
        return gb_victory(gid)

    # برو نوبت بعدی
    b["turn"] += 1
    if b["turn"] >= 5:
        return "boss_turn"  # علامت برای شروع نوبت باس‌ها

    return group_battle_text(gid)


def gb_skip_turn(gid):
    b = group_battles.get(gid)
    if not b:
        return None
    b["turn"] += 1
    if b["turn"] >= 5:
        return "boss_turn"
    return group_battle_text(gid)


def gb_monster_turn(gid):
    """نوبت همه باس‌ها — هر باس به بازیکن خودش حمله می‌کنه"""
    b = group_battles.get(gid)
    if not b:
        return None

    for boss in b["bosses"]:
        if not boss["alive"]:
            continue
        # بازیکن صاحب باس
        pl = next((x for x in b["players"] if x["uid"] == boss["owner_uid"]), None)
        if not pl or not pl["alive"]:
            # صاحب باس مرده → حمله به یه بازیکن زنده دیگه
            alive_pls = [x for x in b["players"] if x["alive"]]
            if not alive_pls:
                break
            pl = random.choice(alive_pls)

        p2 = get_player(pl["uid"])
        if not p2:
            continue
        edmg = max(1, int(boss["dm"] * (1 - min(p2["defense"] * 0.1, 80) / 100)))
        pl["hp"] -= edmg
        if pl["hp"] <= 0:
            pl["hp"] = 0
            pl["alive"] = False
            add_field(pl["uid"], "deaths", 1)

    # چک باخت
    if not any(x["alive"] for x in b["players"]):
        return gb_defeat(gid)

    b["round"] += 1
    b["turn"] = 0
    # بازیکن‌های مرده رو skip کن
    while b["turn"] < 5 and not b["players"][b["turn"]]["alive"]:
        b["turn"] += 1
    if b["turn"] >= 5:
        return "boss_turn"

    return group_battle_text(gid)


def gb_victory(gid):
    b = group_battles.get(gid)
    if not b:
        return None
    rname = b["region"]
    boss_key = b["boss_key"]
    r = REGIONS.get(rname)
    boss_data = next((x for x in r["bosses"] if x["key"] == boss_key), None) if r else None

    # پاداش: هر بازیکن زنده، XP و طلا باس خودش
    text = ("🏆━━━━━━━━━━━━━━━━━🏆\n"
            "   <b>𝐆𝐑𝐎𝐔𝐏 𝐕𝐈𝐂𝐓𝐎𝐑𝐘</b>\n"
            "🏆━━━━━━━━━━━━━━━━━🏆\n\n"
            "🎉 همه باس‌ها نابود شدن!\n\n")

    if boss_data:
        for pl in b["players"]:
            if not pl["alive"]:
                continue
            xp = boss_data["hp"] * 2
            gold = xp // 2
            add_xp(pl["uid"], xp)
            add_field(pl["uid"], "gold", gold)
            add_field(pl["uid"], "kills", 1)

            # دراپ
            drops_got = []
            for d in boss_data["drops"]:
                if random.randint(1, 100) <= d["chance"]:
                    if add_item(pl["uid"], d["item"], 1):
                        drops_got.append(d["item"])

            text += f"👤 <b>{pl['name']}</b>\n"
            text += f"  ✨ {xp:,} | 🪙 {gold:,}\n"
            if drops_got:
                text += f"  🎁 {', '.join(drops_got)}\n"
            text += "\n"

    group_battles.pop(gid, None)
    return text


def gb_defeat(gid):
    b = group_battles.get(gid)
    if not b:
        return None
    text = ("💀━━━━━━━━━━━━━━━━━💀\n"
            "   <b>𝐆𝐑𝐎𝐔𝐏 𝐃𝐄𝐅𝐄𝐀𝐓</b>\n"
            "💀━━━━━━━━━━━━━━━━━💀\n\n"
            "همه بازیکن‌ها مردن...\n"
            "قوی‌تر برگردید! 🔥")
    group_battles.pop(gid, None)
    return text


def gb_skill_menu(gid):
    b = group_battles.get(gid)
    if not b:
        return "❌", []
    t = b["turn"]
    if t >= 5:
        return "❌", []
    pl = b["players"][t]
    p2 = get_player(pl["uid"])
    if not p2 or not has_skills(p2):
        return "❌", []

    cds = b["skill_cd"].get(pl["uid"], {})
    unlocked = get_unlocked_skills(p2["player_class"], p2["level"])
    kb = []
    for sid, sk in unlocked.items():
        cd = cds.get(sid, 0)
        can = pl["qi"] >= sk["qi_cost"] and cd == 0
        icon = "✅" if can else "🔒"
        cd_txt = f" — {cd}" if cd > 0 else ""
        kb.append([{"text": f"{icon} {sk['name']} (QI:{sk['qi_cost']}){cd_txt}",
                    "callback_data": f"gb:skill:{sid}:{gid}" if can else "gb:noop"}])
    kb.append([{"text": "◀️ بازگشت", "callback_data": f"gb:back:{gid}"}])
    text = f"🔮 <b>{p2['player_class']}</b>\n🔵 QI: <b>{pl['qi']:,}/{pl['max_qi']:,}</b>"
    return text, kb


def gb_use_skill(gid, sid):
    b = group_battles.get(gid)
    if not b:
        return None
    t = b["turn"]
    if t >= 5:
        return None
    pl = b["players"][t]
    p2 = get_player(pl["uid"])
    if not p2:
        return None
    sk = SKILLS.get(sid)
    if not sk or sk["class"] != p2["player_class"]:
        return "❌"
    if sid not in get_unlocked_skills(p2["player_class"], p2["level"]):
        return "❌ باز نشده!"

    cds = b["skill_cd"].get(pl["uid"], {})
    if cds.get(sid, 0) > 0:
        return f"⏳ کول‌داون {cds[sid]}"
    if pl["qi"] < sk["qi_cost"]:
        return f"❌ QI کم! نیاز: {sk['qi_cost']}"
    pl["qi"] -= sk["qi_cost"]

    result = ""
    is_aoe = sk.get("aoe", False)

    if "multiplier" in sk:
        if is_aoe:
            # دمیج به همه باس‌ها (نصف)
            total_dmg = 0
            for boss in b["bosses"]:
                if not boss["alive"]:
                    continue
                d = max(1, int(pl["dm"] * sk["multiplier"] / 2 *
                               (1 - min(boss["defense"] / 1000, 0.5))))
                boss["hp"] -= d
                total_dmg += d
                if boss["hp"] <= 0:
                    boss["alive"] = False
                    boss["hp"] = 0
            result = f"{sk['name']} 🌊\n💥 مجموع: <b>{total_dmg:,}</b>"
        else:
            boss = next((x for x in b["bosses"] if x["owner_uid"] == pl["uid"] and x["alive"]), None)
            if not boss:
                boss = next((x for x in b["bosses"] if x["alive"]), None)
            if boss:
                d = max(1, int(pl["dm"] * sk["multiplier"] *
                               (1 - min(boss["defense"] / 1000, 0.5))))
                boss["hp"] -= d
                if boss["hp"] <= 0:
                    boss["alive"] = False
                    boss["hp"] = 0
                result = f"{sk['name']}\n💥 دمیج: <b>{d:,}</b>"
    elif "heal_percent" in sk:
        heal = (pl["max_hp"] * sk["heal_percent"]) // 100
        pl["hp"] = min(pl["max_hp"], pl["hp"] + heal)
        result = f"{sk['name']}\n💚 HP: <b>{pl['hp']:,}</b>"
    elif "dodge" in sk or "absorb" in sk:
        result = f"{sk['name']}\n✨ دفاع!"
        b["pending_defense"][pl["uid"]] = sk
    else:
        return "❌"

    cds[sid] = sk["cooldown"]
    b["skill_cd"][pl["uid"]] = cds

    if not any(x["alive"] for x in b["bosses"]):
        return gb_victory(gid)

    b["turn"] += 1
    if b["turn"] >= 5:
        return f"{result}\n\n⏭️ نوبت باس‌ها"
    while b["turn"] < 5 and not b["players"][b["turn"]]["alive"]:
        b["turn"] += 1
    if b["turn"] >= 5:
        return f"{result}\n\n⏭️ نوبت باس‌ها"
    return f"{result}\n\n" + group_battle_text(gid)
  # ═══════════════════════════════════════
# BLACK MARKET
# ═══════════════════════════════════════

BLACK_MARKET_ITEMS = {
    "weapons": {
        "شمشیر گدازه": {"price": 10_000_000, "currency": "gold", "desc": "⚔️ ایگنیس"},
        "نیزه فونیکس": {"price": 15_000_000, "currency": "gold", "desc": "🔱 فونیکس"},
        "عصای ارواح": {"price": 20_000_000, "currency": "gold", "desc": "🔮 نکرومنسر"},
        "خنجر زهرآلود": {"price": 30_000_000, "currency": "gold", "desc": "🗡️ شاه عقرب"},
        "شمشیر افعی": {"price": 40_000_000, "currency": "gold", "desc": "⚔️ افعی"},
        "شمشیر تاریکی": {"price": 24_000, "currency": "diamond", "desc": "🌑 آرک‌دمون"},
        "شمشیر خورشیدی": {"price": 16_000, "currency": "diamond", "desc": "☀️ خورشید"},
    },
    "armors": {
        "زره گدازه": {"price": 12_000_000, "currency": "gold", "desc": "🔥 ایگنیس"},
        "زره پر": {"price": 15_000_000, "currency": "gold", "desc": "🔥 فونیکس"},
        "ردای مرگ": {"price": 20_000_000, "currency": "gold", "desc": "💀 نکرومنسر"},
        "زره پولادی-شنی": {"price": 30_000_000, "currency": "gold", "desc": "🏜️ شاه عقرب"},
        "زره افعی": {"price": 40_000_000, "currency": "gold", "desc": "🐍 افعی"},
        "زره جهنمی": {"price": 24_000, "currency": "diamond", "desc": "🌑 آرک‌دمون"},
        "زره طلایی": {"price": 16_000, "currency": "diamond", "desc": "☀️ خورشید"},
    },
    "shields": {
        "سپر آتشین": {"price": 10_000_000, "currency": "gold", "desc": "🛡️ ایگنیس"},
        "سپر بال": {"price": 15_000_000, "currency": "gold", "desc": "🛡️ فونیکس"},
        "کتاب جادو": {"price": 20_000_000, "currency": "gold", "desc": "📖 نکرومنسر"},
        "سپر صدفی": {"price": 30_000_000, "currency": "gold", "desc": "🛡️ شاه عقرب"},
        "سپر جهنمی": {"price": 24_000, "currency": "diamond", "desc": "🛡️ آرک‌دمون"},
        "سپر طلایی": {"price": 16_000, "currency": "diamond", "desc": "🛡️ خورشید"},
    },
    "heads": {
        "کلاه گدازه": {"price": 8_000_000, "currency": "gold", "desc": "🪖 ایگنیس"},
        "کلاه پر": {"price": 12_000_000, "currency": "gold", "desc": "🪖 فونیکس"},
        "کلاه جادوگر": {"price": 15_000_000, "currency": "gold", "desc": "🪖 نکرومنسر"},
        "تاج ملکه": {"price": 50_000_000, "currency": "gold", "desc": "👑 ملکه عقرب"},
        "تاج تاریکی": {"price": 24_000, "currency": "diamond", "desc": "👑 آرک‌دمون"},
        "تاج خورشید": {"price": 16_000, "currency": "diamond", "desc": "👑 خورشید"},
    },
    "necklaces": {
        "گردن‌آویز گدازه": {"price": 15_000_000, "currency": "gold", "desc": "📿 ایگنیس"},
        "گردن‌آویز ققنوس": {"price": 15_000_000, "currency": "gold", "desc": "📿 فونیکس"},
        "گردن‌آویز روح": {"price": 20_000_000, "currency": "gold", "desc": "📿 نکرومنسر"},
        "گردن‌آویز زهر": {"price": 50_000_000, "currency": "gold", "desc": "📿 ملکه"},
        "گردن‌آویز لرد": {"price": 24_000, "currency": "diamond", "desc": "📿 آرک‌دمون"},
        "گردن‌آویز خورشید": {"price": 16_000, "currency": "diamond", "desc": "📿 خورشید"},
    },
    "others": {
        "شنل آتش": {"price": 8_000_000, "currency": "gold", "desc": "🪽 ایگنیس"},
        "شنل تاریکی": {"price": 24_000, "currency": "diamond", "desc": "🪽 آرک‌دمون"},
        "کفش جهنمی": {"price": 24_000, "currency": "diamond", "desc": "🥾 آرک‌دمون"},
        "کفش خورشیدی": {"price": 16_000, "currency": "diamond", "desc": "🥾 خورشید"},
    },
    "limited": {
        "کلید باس مخفی": {"price": 5_000_000, "currency": "gold", "desc": "🎫 باس مخفی"},
        "کارت تغییر کلاس": {"price": 3_000, "currency": "diamond", "desc": "🎫 تغییر کلاس"},
        "بلیط XP دوبرابر": {"price": 1_500, "currency": "diamond", "desc": "🎫 XP ×2 (۲۴س)"},
        "اسکین طلایی": {"price": 10_000, "currency": "diamond", "desc": "🎫 اسکین"},
    }
}


def black_market_text():
    return ("🏪 <b>بازار سیاه</b>\n\n━━━━━━━━━━━━━━━━━━\n\n"
            "🌑 <i>«هیس... فقط برای تو دارم...»</i>\n\n"
            "اینجا چیزهایی پیدا میشه که\n"
            "تو فروشگاه رسمی پیدا نمی‌کنی.\n\n"
            "⚠️ <b>فقط برای جسورها!</b>")


def black_market_menu():
    return [
        [{"text": "🗡️ سلاح‌ها", "callback_data": "bm:weapons"},
         {"text": "🛡️ زره‌ها", "callback_data": "bm:armors"}],
        [{"text": "🛡️ سپرها", "callback_data": "bm:shields"},
         {"text": "🪖 کلاه‌ها", "callback_data": "bm:heads"}],
        [{"text": "📿 گردن‌آویزها", "callback_data": "bm:necklaces"},
         {"text": "📦 سایر", "callback_data": "bm:others"}],
        [{"text": "🎫 محدود", "callback_data": "bm:limited"}],
        [{"text": "◀️ بازگشت", "callback_data": "back"}]
    ]


def bm_category_text(cat):
    titles = {"weapons": "🗡️ سلاح‌ها", "armors": "🛡️ زره‌ها",
              "shields": "🛡️ سپرها", "heads": "🪖 کلاه‌ها",
              "necklaces": "📿 گردن‌آویزها", "others": "📦 سایر",
              "limited": "🎫 محدود"}
    return f"{titles.get(cat, '🏪')}\n\n━━━━━━━━━━━━━━━━━━\n\nروی آیتم بزن:"


def bm_category_menu(cat):
    items = BLACK_MARKET_ITEMS.get(cat, {})
    kb = []
    for name, info in items.items():
        if info["currency"] == "gold":
            pt = f"{info['price']:,} 🪙"
        else:
            pt = f"{info['price']:,} 💎"
        kb.append([{"text": f"{name} — {pt}",
                    "callback_data": f"bm:item:{cat}:{name}"}])
    kb.append([{"text": "◀️ بازگشت", "callback_data": "black_market"}])
    return kb


def bm_item_text(cat, name):
    info = BLACK_MARKET_ITEMS.get(cat, {}).get(name)
    if not info:
        return "❌"
    if info["currency"] == "gold":
        pt = f"{info['price']:,} 🪙"
    else:
        pt = f"{info['price']:,} 💎"
    stats = ITEM_STATS.get(name, {})
    sl = "\n".join(f"{STAT_ICONS[s]} {s}: +{v}" for s, v in stats.items()) or "—"
    return (f"<b>{name}</b>\n\n📖 {info['desc']}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n📊 <b>آمار:</b>\n{sl}\n"
            f"━━━━━━━━━━━━━━━━━━\n\n💰 قیمت: <b>{pt}</b>")


def bm_item_menu(cat, name):
    return [[{"text": "💰 خرید", "callback_data": f"bm:buy:{cat}:{name}"}],
            [{"text": "◀️", "callback_data": f"bm:{cat}"}]]


# ═══════════════════════════════════════
# MENUS
# ═══════════════════════════════════════

def main_menu():
    return [
        [{"text": "👤 شخصیت", "callback_data": "character"},
         {"text": "🎒 کیف", "callback_data": "inventory"}],
        [{"text": "🏰 دانجن", "callback_data": "dungeon"},
         {"text": "🗼 برج", "callback_data": "tower"}],
        [{"text": "🗺️ مکان", "callback_data": "location"},
         {"text": "🏪 فروشگاه", "callback_data": "shop"}],
        [{"text": "👑 خاندان", "callback_data": "clan"},
         {"text": "🏆 رتبه‌بندی", "callback_data": "ranking"}],
        [{"text": "🏪 بازار سیاه", "callback_data": "black_market"},
         {"text": "⚙️ تنظیمات", "callback_data": "settings"}]
    ]


def main_menu_admin(uid):
    kb = main_menu()
    if is_admin(uid):
        role = "👑 مالک" if is_owner(uid) else "🛡️ ادمین"
        kb.append([{"text": f"🔧 پنل {role}", "callback_data": "admin"}])
    return kb


def dungeon_menu():
    return [
        [{"text": "⚔️ شکار", "callback_data": "dungeon:hunt"},
         {"text": "🔍 گشت‌زنی", "callback_data": "dungeon:scout"}],
        [{"text": "🌾 فارم", "callback_data": "dungeon:farm"},
         {"text": "⛺ اتراق", "callback_data": "dungeon:camp"}],
        [{"text": "🐉 باس تکی", "callback_data": "dungeon:boss"}],
        [{"text": "👥 نبرد گروهی", "callback_data": "dungeon:gb"}],
        [{"text": "◀️ بازگشت", "callback_data": "back"}]
    ]


def hunt_menu(player_level):
    rank = get_player_rank(player_level)
    rank_name = RANK_NAMES[rank]
    mult = RANK_MULTIPLIERS[rank]
    kb = []
    for name in ENEMIES:
        min_lv = LEVEL_MIN[name]
        if player_level >= min_lv:
            kb.append([{"text": f"{name} (Lv.{min_lv}+)",
                        "callback_data": f"hunt:{name}"}])
        else:
            kb.append([{"text": f"🔒 {name} (Lv.{min_lv}+)",
                        "callback_data": "hunt:locked"}])
    kb.append([{"text": "◀️ بازگشت", "callback_data": "dungeon"}])
    return kb, rank_name, mult


def location_menu():
    return [
        [{"text": "☕ قهوه‌خانه", "callback_data": "loc:coffee"},
         {"text": "🌾 مزرعه", "callback_data": "loc:farm"}],
        [{"text": "⚒️ آهنگر", "callback_data": "loc:smith"},
         {"text": "⚗️ کیمیاگری", "callback_data": "loc:alchemy"}],
        [{"text": "🌑 جنوس", "callback_data": "loc:genos"}],
        [{"text": "◀️ بازگشت", "callback_data": "back"}]
    ]


def coffee_menu():
    return [
        [{"text": "😴 استراحت", "callback_data": "coffee:rest"},
         {"text": "👥 گروه", "callback_data": "coffee:group"}],
        [{"text": "📜 مأموریت", "callback_data": "coffee:mission"},
         {"text": "🍵 نوشیدنی", "callback_data": "coffee:drink"}],
        [{"text": "💬 گفتگو", "callback_data": "coffee:chat"}],
        [{"text": "◀️ بازگشت", "callback_data": "location"}]
    ]


def character_menu(p):
    kb = [[{"text": "👑 پروفایل", "callback_data": "profile"},
           {"text": "📊 آمار", "callback_data": "stats"}]]
    if has_skills(p):
        kb.append([{"text": "🔮 مهارت", "callback_data": "skills"},
                   {"text": "⚔️ تجهیزات", "callback_data": "equipment"}])
        kb.append([{"text": "🏷️ عنوان", "callback_data": "titles"}])
    else:
        kb.append([{"text": "⚔️ تجهیزات", "callback_data": "equipment"},
                   {"text": "🏷️ عنوان", "callback_data": "titles"}])
    kb.append([{"text": "◀️ بازگشت", "callback_data": "back"}])
    return kb


def ranking_menu():
    return [
        [{"text": "⭐ سطح", "callback_data": "rank:level"},
         {"text": "☠️ کشتار", "callback_data": "rank:kills"}],
        [{"text": "💰 پول", "callback_data": "rank:gold"},
         {"text": "⚔️ قدرت", "callback_data": "rank:power"}],
        [{"text": "◀️ بازگشت", "callback_data": "back"}]
    ]


def settings_menu():
    return [
        [{"text": "✏️ تغییر نام", "callback_data": "set:name"},
         {"text": "⚧️ تغییر جنسیت", "callback_data": "set:gender"}],
        [{"text": "🗑️ حذف حساب", "callback_data": "set:delete"}],
        [{"text": "◀️ بازگشت", "callback_data": "back"}]
    ]


def gender_menu():
    return [[{"text": "👨 مرد", "callback_data": "gender:male"},
             {"text": "👩 زن", "callback_data": "gender:female"}]]


def class_menu(index):
    kb, nav = [], []
    if index > 0:
        nav.append({"text": "◀️", "callback_data": f"class:prev:{index}"})
    if index < len(CLASSES) - 1:
        nav.append({"text": "▶️", "callback_data": f"class:next:{index}"})
    if nav:
        kb.append(nav)
    kb.append([{"text": "👑 انتخاب", "callback_data": f"class:select:{index}"}])
    return kb


# ═══════════════════════════════════════
# RANKING
# ═══════════════════════════════════════

def ranking_text(order, title, unit=""):
    rows = get_top(order, 10)
    text = f"🏆 <b>{title}</b>\n\n━━━━━━━━━━━━━━━━━━\n\n"
    if not rows:
        return text + "🔒 خالی"
    medals = ["🥇", "🥈", "🥉"]
    for i, r in enumerate(rows):
        medal = medals[i] if i < 3 else f"{i+1}."
        val = r["val"]
        val_str = f"{val:,}{unit}" if isinstance(val, int) else val
        text += f"{medal} <b>{r['name']}</b>\n"
        text += f"    ⭐ Lv.{r['level']} | {val_str}\n\n"
    return text


def ranking_power_text():
    rows = get_top_power(10)
    text = "🏆 <b>قدرتمندترین‌ها</b>\n\n━━━━━━━━━━━━━━━━━━\n\n"
    if not rows:
        return text + "🔒 خالی"
    medals = ["🥇", "🥈", "🥉"]
    for i, r in enumerate(rows):
        medal = medals[i] if i < 3 else f"{i+1}."
        text += f"{medal} <b>{r['name']}</b>\n"
        text += f"    ⭐ Lv.{r['level']} | ⚡ {r['val']:,}\n\n"
    return text


# ═══════════════════════════════════════
# INVENTORY
# ═══════════════════════════════════════

PAGE_SIZE = 5


def inventory_text(items):
    total = sum(i["quantity"] for i in items)
    text = f"🎒 <b>کیف</b>\n\n📦 <b>{total}</b>/{MAX_INVENTORY}\n"
    if not items:
        text += "\n<i>خالیه</i>"
    return text


def inventory_menu(uid, page=0):
    items = get_inventory(uid)
    total_pages = max(1, (len(items) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    start = page * PAGE_SIZE
    cur = items[start:start + PAGE_SIZE]
    kb = []
    for item in cur:
        kb.append([{"text": f"{item['item_name']} ×{item['quantity']}",
                    "callback_data": f"item:{item['item_name']}"}])
    nav = []
    if page > 0:
        nav.append({"text": "◀️", "callback_data": f"inventory:{page - 1}"})
    if page < total_pages - 1:
        nav.append({"text": "▶️", "callback_data": f"inventory:{page + 1}"})
    if nav:
        kb.append(nav)
    kb.append([{"text": "◀️ بازگشت", "callback_data": "back"}])
    return kb


def open_inventory(chat_id, uid, page=0, message_id=None):
    items = get_inventory(uid)
    text = inventory_text(items)
    kb = inventory_menu(uid, page)
    if message_id:
        edit(chat_id, message_id, text, kb)
    else:
        send(chat_id, text, kb)


def get_item(uid, name):
    for i in get_inventory(uid):
        if i["item_name"] == name:
            return i
    return None


def get_equipped_slot(uid, name):
    eq = get_equipment(uid)
    for slot, item in eq.items():
        if item == name:
            return slot
    return None


def item_menu(uid, name):
    eq_slot = get_equipped_slot(uid, name)
    if eq_slot:
        first = {"text": "🔓 درآوردن", "callback_data": f"unequip:{name}"}
    else:
        first = {"text": "⚔️ تجهیز", "callback_data": f"equip:{name}"}
    return [[first, {"text": "❌ حذف", "callback_data": f"delete:{name}"}],
            [{"text": "◀️ بازگشت", "callback_data": "inventory:0"}]]


def open_item(chat_id, uid, name, message_id=None):
    item = get_item(uid, name)
    if not item:
        send(chat_id, "❌ در کیف نیست.")
        return
    stats = ITEM_STATS.get(name, {})
    sl = "\n".join(f"{STAT_ICONS[s]} {s}: +{v}" for s, v in stats.items()) or "بدون آمار"
    text = (f"<b>{item['item_name']}</b>\n\n×{item['quantity']}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n📊 <b>آمار:</b>\n{sl}\n━━━━━━━━━━━━━━━━━━")
    kb = item_menu(uid, name)
    if message_id:
        edit(chat_id, message_id, text, kb)
    else:
        send(chat_id, text, kb)


# ═══════════════════════════════════════
# EQUIPMENT / TITLES
# ═══════════════════════════════════════

def equipment_text(uid):
    eq = get_equipment(uid)
    lines = ["⚔️ <b>تجهیزات</b>", ""]
    for slot, title in [("head", "🪖 کلاه"), ("body", "👕 بالاتنه"),
                        ("cloak", "🪽 شنل"), ("main", "⚔️ دست اصلی"),
                        ("off", "🛡️ دست فرعی"), ("ring", "💍 انگشتر"),
                        ("legs", "👖 پایین‌تنه"), ("boots", "🥾 کفش")]:
        lines.append(f"{title}: {eq.get(slot) or 'خالی'}")
    return "\n".join(lines)


def titles_text(uid):
    titles = get_titles(uid)
    active = next((t["title"] for t in titles if t["active"]), None)
    text = f"🏷️ <b>عنوان</b>\n\nلقب فعلی: {active or 'بدون لقب'}\n\n📜 عنوان‌ها:\n\n"
    if not titles:
        text += "🔒 خالی"
    return text


def titles_menu(uid):
    titles = get_titles(uid)
    kb = []
    for t in titles:
        txt = f"✅ {t['title']}" if t["active"] else t["title"]
        kb.append([{"text": txt, "callback_data": f"title:{t['title']}"}])
    kb.append([{"text": "◀️", "callback_data": "character"}])
    return kb
  # ═══════════════════════════════════════
# CLAN MENUS
# ═══════════════════════════════════════

def clan_no_member_menu():
    return [
        [{"text": "🏗️ ساخت خاندان", "callback_data": "clan:create"},
         {"text": "🔍 جست‌وجو", "callback_data": "clan:search"}],
        [{"text": "📜 لیست", "callback_data": "clan:list"}],
        [{"text": "◀️ بازگشت", "callback_data": "back"}]
    ]


def clan_main_menu(is_leader=False):
    kb = [
        [{"text": "👥 اعضا", "callback_data": "clan:members"},
         {"text": "🏆 رتبه", "callback_data": "clan:ranking"}],
        [{"text": "💰 خزانه", "callback_data": "clan:treasury"},
         {"text": "🤝 اتحاد", "callback_data": "clan:alliance"}],
    ]
    if is_leader:
        kb.append([{"text": "➕ افزودن", "callback_data": "clan:add_member"},
                   {"text": "➖ اخراج", "callback_data": "clan:kick"}])
        kb.append([{"text": "⬆️ ارتقا", "callback_data": "clan:promote"},
                   {"text": "📩 درخواست‌ها", "callback_data": "clan:requests"}])
        kb.append([{"text": "💥 انحلال", "callback_data": "clan:disband"}])
    kb.append([{"text": "◀️ بازگشت", "callback_data": "back"}])
    return kb


def clan_ranking_menu():
    return [
        [{"text": "⭐ سطح", "callback_data": "clan:r:level"},
         {"text": "👥 اعضا", "callback_data": "clan:r:members"}],
        [{"text": "💰 خزانه", "callback_data": "clan:r:gold"}],
        [{"text": "◀️", "callback_data": "clan"}]
    ]


def clan_view_text(clan, rank, uid):
    mc = get_clan_members_count(clan["id"])
    leader = get_player(clan["leader_id"])
    lname = leader["name"] if leader else "—"
    rank_name = CLAN_RANKS.get(rank, "—")
    return (f"👑 <b>خاندان {clan['name']}</b>\n\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"📖 {clan['motto'] or '—'}\n"
            f"👑 رهبر: {lname}\n"
            f"👥 اعضا: {mc}/{CLAN_MAX_MEMBERS}\n"
            f"🏅 رتبه تو: {rank_name}\n"
            f"⭐ سطح خزانه: {clan['treasury_level']}/10\n\n"
            f"💰 {clan['treasury_gold']:,} 🪙\n"
            f"💎 {clan['treasury_diamond']:,}\n"
            "━━━━━━━━━━━━━━━━━━")


def clan_member_line(m):
    icon = CLASS_ICON.get(m["player_class"], "")
    rank_name = CLAN_RANKS.get(m["rank"], "")
    if m["rank"] in ("leader", "noble"):
        pt = "🔒"
    else:
        p = get_player(m["user_id"])
        pt = f"{calc_power(p, m['user_id']):,}" if p else "—"
    return (f"{rank_name}\n"
            f"👤 <b>{m['name'] or '—'}</b> | Lv.{m['level'] or 0} {icon}\n"
            f"⚡ {pt}\n")


# ═══════════════════════════════════════
# GROUP MENUS
# ═══════════════════════════════════════

def group_no_member_menu():
    return [
        [{"text": "🏗️ ساخت گروه", "callback_data": "group:create"}],
        [{"text": "◀️ بازگشت", "callback_data": "loc:coffee"}]
    ]


def group_member_menu(is_leader=False):
    kb = [[{"text": "👥 اعضا", "callback_data": "group:members"}]]
    if is_leader:
        kb.append([{"text": "➕ افزودن عضو", "callback_data": "group:add"}])
        kb.append([{"text": "➖ اخراج عضو", "callback_data": "group:kick"}])
    kb.append([{"text": "🚪 ترک گروه", "callback_data": "group:leave"}])
    kb.append([{"text": "◀️ بازگشت", "callback_data": "loc:coffee"}])
    return kb


def group_view_text(g):
    mc = get_group_count(g["id"])
    leader = get_player(g["leader_id"])
    lname = leader["name"] if leader else "—"
    return (f"👥 <b>گروه {g['name'] or 'بی‌نام'}</b>\n\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"👑 رهبر: {lname}\n"
            f"👥 اعضا: {mc}/5\n"
            "━━━━━━━━━━━━━━━━━━")


# ═══════════════════════════════════════
# ADMIN MENUS
# ═══════════════════════════════════════

def admin_menu(uid):
    if is_owner(uid):
        return [
            [{"text": "👤 مدیریت بازیکن", "callback_data": "admin:player"}],
            [{"text": "🎁 اهدا", "callback_data": "admin:gift"}],
            [{"text": "💰 طلا", "callback_data": "admin:gold"},
             {"text": "💎 الماس", "callback_data": "admin:diamond"}],
            [{"text": "📊 آمار", "callback_data": "admin:stats"}],
            [{"text": "📢 پیام همگانی", "callback_data": "admin:broadcast"}],
            [{"text": "🏰 خاندان", "callback_data": "admin:clan"}],
            [{"text": "🛡️ ادمین‌ها", "callback_data": "admin:admins"}],
            [{"text": "🚫 بن/آنبن", "callback_data": "admin:ban"}],
            [{"text": "🗑️ حذف همه", "callback_data": "admin:del_all"}],
            [{"text": "◀️ بازگشت", "callback_data": "back"}]
        ]
    else:
        return [
            [{"text": "👤 مدیریت بازیکن", "callback_data": "admin:player"}],
            [{"text": "🎁 اهدا", "callback_data": "admin:gift"}],
            [{"text": "💰 طلا", "callback_data": "admin:gold"},
             {"text": "💎 الماس", "callback_data": "admin:diamond"}],
            [{"text": "📊 آمار", "callback_data": "admin:stats"}],
            [{"text": "📢 پیام همگانی", "callback_data": "admin:broadcast"}],
            [{"text": "◀️ بازگشت", "callback_data": "back"}]
        ]


def admin_player_menu(uid):
    kb = [
        [{"text": "✏️ سطح", "callback_data": "admin:set_level"}],
        [{"text": "💰 طلا", "callback_data": "admin:set_gold"}],
        [{"text": "💎 الماس", "callback_data": "admin:set_diamond"}],
        [{"text": "⚡ آمار", "callback_data": "admin:set_stats"}],
        [{"text": "🎒 افزودن آیتم", "callback_data": "admin:add_item"}],
    ]
    if is_owner(uid):
        kb.append([{"text": "🗑️ پاک کیف", "callback_data": "admin:clear_inv"}])
        kb.append([{"text": "❌ حذف بازیکن", "callback_data": "admin:del_player"}])
    kb.append([{"text": "◀️ بازگشت", "callback_data": "admin"}])
    return kb


def admin_admins_menu():
    admins = get_admins()
    kb = []
    for aid in admins:
        p = get_player(aid)
        name = p["name"] if p else f"ID:{aid}"
        kb.append([{"text": f"❌ {name}", "callback_data": f"admin:rm_admin:{aid}"}])
    if len(admins) < MAX_ADMINS:
        kb.append([{"text": "➕ افزودن ادمین", "callback_data": "admin:add_admin"}])
    kb.append([{"text": "◀️ بازگشت", "callback_data": "admin"}])
    return kb


# ═══════════════════════════════════════
# PLAYER / STAGE / TEXT
# ═══════════════════════════════════════

def player(uid, chat_id):
    p = get_player(uid)
    if p:
        return p
    create_player(uid, chat_id)
    return get_player(uid)


def stage(p):
    if not p.get("name"):
        return "name"
    if not p.get("gender"):
        return "gender"
    if not p.get("player_class"):
        return "class"
    return "complete"


def main_text():
    return ("👑 <b>GODS TOWER</b>\n\n"
            "🌸 روز 1 | فصل بهار\n\n"
            "«سفرت از همین‌جا آغاز می‌شود...»")


def class_text(index):
    c = CLASSES[index]
    return (f"{c['name']}\n\n📊 <b>آمار پایه</b>\n\n"
            f"💪 {c['power']}\n🛡️ {c['stamina']}\n⚡ {c['speed']}\n"
            f"🧱 {c['defense']}\n🍀 {c['luck']}\n🔮 {c['chakra']}\n\n"
            f"📖 {c['description']}")


def profile_text(p):
    uid = p["user_id"]
    b = get_item_bonus(uid)
    base_hp = p["stamina"] * 200
    base_qi = p["chakra"] * 50
    hp = (p["stamina"] + b["stamina"]) * 200
    qi = (p["chakra"] + b["chakra"]) * 50
    if p["player_class"] == "شمن":
        dm = (p["chakra"] + b["chakra"]) * 200
        base_dm = p["chakra"] * 200
    else:
        dm = (p["power"] + b["power"]) * 200
        base_dm = p["power"] * 200

    xp_next = xp_required(p["level"])
    xp_txt = f"{p['xp']:,}/{xp_next:,}" if xp_next else "MAX"
    titles = get_titles(uid)
    active_t = next((t["title"] for t in titles if t["active"]), None)

    clan_txt = "—"
    cm = get_player_clan(uid)
    if cm:
        cl = get_clan(cm["clan_id"])
        if cl:
            clan_txt = f"{cl['name']}"

    def ln(label, base, tot):
        d = tot - base
        return f"{label}: {tot:,} <i>(+{d:,})</i>\n" if d > 0 else f"{label}: {tot:,}\n"

    text = ("╭━━━━━━━ 👑 ━━━━━━━╮\n"
            "      <b>𝐏𝐑𝐎𝐅𝐈𝐋𝐄</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            f"👤 {p['name']}\n"
            f"⚔️ {CLASS_ICON.get(p['player_class'],'')} {p['player_class']}\n"
            f"🏷️ {active_t or 'بدون لقب'}\n"
            f"👑 {clan_txt}\n\n"
            f"⭐ LV: {p['level']}\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"🪙 {p['gold']:,}\n💎 {p['diamonds']:,}\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            + ln("❤️ HP", base_hp, hp)
            + ln("☯️ QI", base_qi, qi)
            + f"✨ XP: {xp_txt}\n"
            + ln("⚔️ DM", base_dm, dm)
            + f"☠️ کشتار: {p['kills']:,}\n")

    g = get_guardian(p)
    if g:
        text += f"\n━━━━━━━━━━━━━━━━━━\n🛡️ نگهبان Lv.{g['level']}\n"
    return text


def stats_text(p):
    uid = p["user_id"]
    b = get_item_bonus(uid)

    def row(icon, name, base, bo):
        return f"{icon} {name}: {base} <i>(+{bo})</i>\n" if bo > 0 else f"{icon} {name}: {base}\n"

    return ("╭━━━━━ 📊 ━━━━━╮\n"
            "      <b>𝐒𝐓𝐀𝐓𝐒</b>\n"
            "╰━━━━━━━━━━━━━━━━━━╯\n\n"
            + row("💪", "قدرت", p["power"], b["power"])
            + row("🛡️", "استقامت", p["stamina"], b["stamina"])
            + row("⚡", "سرعت", p["speed"], b["speed"])
            + row("🧱", "دفاع", p["defense"], b["defense"])
            + row("🍀", "شانس", p["luck"], b["luck"])
            + row("🔮", "چاکرا", p["chakra"], b["chakra"])
            + f"\n━━━━━━━━━━━━━━━━━━\n\n🎯 امتیاز: {p['stat_points']}")


def increase_stats_menu(p):
    pts = p["stat_points"]
    kb = []
    for stat, name in STAT_NAMES.items():
        row = [{"text": f"{name} +1", "callback_data": f"stat:{stat}:1"}]
        if pts >= 10:
            row.append({"text": f"{name} +10", "callback_data": f"stat:{stat}:10"})
        kb.append(row)
    kb.append([{"text": "◀️", "callback_data": "stats"}])
    return kb


def skills_text(p):
    if p["player_class"] not in CLASS_ICON:
        return ("🔮 <b>مهارت‌ها</b>\n\n❌ فقط رزمی.",
                [[{"text": "◀️", "callback_data": "character"}]])
    if p["level"] < 10:
        return (f"🔮 <b>مهارت‌ها</b>\n\n🔒 از لول 10\nسطح: {p['level']}",
                [[{"text": "◀️", "callback_data": "character"}]])

    qi = calc_qi_full(p, p["user_id"])
    all_sk = list(get_class_skills(p["player_class"]).items())
    unlocked = get_unlocked_skills(p["player_class"], p["level"])

    lines = [f"🔮 <b>{p['player_class']}</b>", "", f"🔵 QI: <b>{qi:,}</b>", ""]
    for i, (sid, sk) in enumerate(all_sk):
        lv = SKILL_UNLOCK_LEVELS[i] if i < len(SKILL_UNLOCK_LEVELS) else 50
        if sid in unlocked:
            lines.append(f"✅ <b>{sk['name']}</b>")
            if "multiplier" in sk:
                tag = " 🌊" if sk.get("aoe") else ""
                lines.append(f"   💥 ×{sk['multiplier']}{tag}")
            if "heal_percent" in sk:
                lines.append(f"   💚 {sk['heal_percent']}%")
            if "dodge" in sk:
                lines.append(f"   ✨ {sk['dodge']}%")
            if "absorb" in sk:
                lines.append(f"   🛡️ {sk['absorb']}%")
            lines.append(f"   🔵 QI:{sk['qi_cost']} | ⏳{sk['cooldown']}")
            lines.append("")
        else:
            lines.append(f"🔒 <b>{sk['name']}</b> (لول {lv})")
            lines.append("")
    return "\n".join(lines), [[{"text": "◀️", "callback_data": "character"}]]
  # ═══════════════════════════════════════
# MESSAGE
# ═══════════════════════════════════════

def handle_message(message):
    chat = message.get("chat") or {}
    user = message.get("from") or {}
    chat_id = chat.get("id")
    uid = user.get("id")
    if chat_id is None or uid is None:
        return
    text = (message.get("text") or "").strip()
    print(f"{uid}: {text}")
    p = player(uid, chat_id)

    if p.get("is_banned"):
        send(chat_id, "🚫 بن شدی.")
        return

    # ═══════════ /start ═══════════
    if text == "/start":
        if stage(p) == "complete":
            send(chat_id, main_text(), main_menu_admin(uid))
        elif stage(p) == "name":
            send(chat_id, "👑 <b>ساخت قهرمان</b>\n\n✍️ اسم:")
        elif stage(p) == "gender":
            send(chat_id, "⚧️ جنسیت:", gender_menu())
        else:
            send(chat_id, class_text(0), class_menu(0))
        return

    # ═══════════ /admin ═══════════
    if text == "/admin":
        if not is_admin(uid):
            send(chat_id, "⛔"); return
        role = "👑 مالک" if is_owner(uid) else "🛡️ ادمین"
        send(chat_id, f"🔧 <b>پنل {role}</b>", admin_menu(uid))
        return

    # ═══════════ /testitems ═══════════
    if text == "/testitems":
        items = [("شمشیر آهنی", 2), ("زره آهنی", 1), ("کفش آهنی", 1)]
        added = [f"{n}×{q}" for n, q in items if add_item(uid, n, q)]
        send(chat_id, "🧪 " + "، ".join(added) if added else "⚠️ پر")
        return

    # ═══════════ waiting ═══════════
    if uid in waiting:
        w = waiting[uid]
        wt = w["type"]

        # ─── نام جدید ───
        if wt == "new_name":
            name = " ".join(text.split())
            if not 3 <= len(name) <= 20:
                send(chat_id, "❌ ۳-۲۰ کاراکتر."); return
            if name_exists(name):
                send(chat_id, "❌ گرفته شده."); return
            set_name(uid, name)
            waiting.pop(uid, None)
            send(chat_id, f"✅ نام: <b>{name}</b>",
                 [[{"text": "⚙️", "callback_data": "settings"}]])
            return

        # ─── نام خاندان ───
        if wt == "clan_name":
            name = " ".join(text.split())
            if not 3 <= len(name) <= 20:
                send(chat_id, "❌ ۳-۲۰."); return
            if clan_name_exists(name):
                send(chat_id, "❌ گرفته شده."); return
            waiting[uid] = {"type": "clan_motto", "name": name}
            send(chat_id, "📖 شعار (حداکثر ۵۰):",
                 [[{"text": "◀️", "callback_data": "clan"}]])
            return

        if wt == "clan_motto":
            motto = " ".join(text.split())[:50]
            name = w["name"]
            if p["gold"] < CLAN_CREATE_COST:
                waiting.pop(uid, None)
                send(chat_id, "❌ طلا کم."); return
            add_field(uid, "gold", -CLAN_CREATE_COST)
            clan_id = create_clan(name, motto, uid)
            waiting.pop(uid, None)
            cl = get_clan(clan_id)
            send(chat_id, f"🏗️ <b>{name}</b> ساخته شد!\n\n" + clan_view_text(cl, "leader", uid),
                 clan_main_menu(True))
            return

        # ─── جست‌وجو خاندان ───
        if wt == "clan_search":
            name = " ".join(text.split())
            cl = get_clan_by_name(name)
            waiting.pop(uid, None)
            if not cl:
                send(chat_id, "❌ پیدا نشد.",
                     [[{"text": "◀️", "callback_data": "clan"}]]); return
            send(chat_id,
                 f"👑 <b>{cl['name']}</b>\n📖 {cl['motto'] or '—'}\n"
                 f"👥 {get_clan_members_count(cl['id'])}",
                 [[{"text": "📩 درخواست", "callback_data": f"clan:req:{cl['id']}"}],
                  [{"text": "◀️", "callback_data": "clan"}]])
            return

        # ─── نام گروه ───
        if wt == "group_name":
            name = " ".join(text.split())[:20] or "بی‌نام"
            gid = create_group(name, uid)
            set_group(uid, gid)
            waiting.pop(uid, None)
            g = get_group(gid)
            send(chat_id, f"🏗️ گروه <b>{name}</b>\n\n" + group_view_text(g),
                 group_member_menu(True))
            return

        # ─── افزودن عضو به گروه (با اسم) ───
        if wt == "group_add":
            if not p["group_id"]:
                waiting.pop(uid, None); return
            g = get_group(p["group_id"])
            if not g or g["leader_id"] != uid:
                send(chat_id, "❌ فقط رئیس.")
                waiting.pop(uid, None); return
            if get_group_count(g["id"]) >= 5:
                send(chat_id, "❌ پر (۵ نفر).")
                waiting.pop(uid, None); return
            target_name = " ".join(text.split())
            target = get_player_by_name(target_name)
            if not target:
                send(chat_id, f"❌ «{target_name}» پیدا نشد.")
                waiting.pop(uid, None); return
            if target["user_id"] == uid:
                send(chat_id, "❌ خودت.")
                waiting.pop(uid, None); return
            if target["group_id"]:
                send(chat_id, "❌ قبلاً تو گروهه.")
                waiting.pop(uid, None); return
            set_group(target["user_id"], g["id"])
            waiting.pop(uid, None)
            send(chat_id, f"✅ <b>{target_name}</b> اضافه شد!\n👥 {get_group_count(g['id'])}/5",
                 group_member_menu(True))
            send(target["chat_id"],
                 f"🎉 به گروه <b>{g['name']}</b> اضافه شدی!",
                 [[{"text": "👥", "callback_data": "coffee:group"}]])
            return

        # ─── اخراج عضو از گروه ───
        if wt == "group_kick":
            if not p["group_id"]:
                waiting.pop(uid, None); return
            g = get_group(p["group_id"])
            if not g or g["leader_id"] != uid:
                waiting.pop(uid, None); return
            target_name = " ".join(text.split())
            target = get_player_by_name(target_name)
            if not target or target["group_id"] != g["id"] or target["user_id"] == uid:
                send(chat_id, "❌ پیدا نشد.")
                waiting.pop(uid, None); return
            set_group(target["user_id"], 0)
            waiting.pop(uid, None)
            send(chat_id, f"✅ {target_name} اخراج شد.",
                 group_member_menu(True))
            return

        # ─── افزودن عضو به خاندان (با اسم) ───
        if wt == "clan_add_member":
            cm = get_player_clan(uid)
            if not cm or cm["rank"] != "leader":
                waiting.pop(uid, None); return
            cl_id = cm["clan_id"]
            if get_clan_members_count(cl_id) >= CLAN_MAX_MEMBERS:
                send(chat_id, "❌ پر.")
                waiting.pop(uid, None); return
            tname = " ".join(text.split())
            target = get_player_by_name(tname)
            if not target:
                send(chat_id, f"❌ «{tname}» نیست.")
                waiting.pop(uid, None); return
            if get_player_clan(target["user_id"]):
                send(chat_id, "❌ تو یه خاندانه.")
                waiting.pop(uid, None); return
            from database import connect
            con = connect()
            con.execute("INSERT INTO clan_members(user_id, clan_id, rank, joined_at) VALUES(?,?,?,?)",
                        (target["user_id"], cl_id, "member", time.time()))
            con.commit()
            con.close()
            waiting.pop(uid, None)
            send(chat_id, f"✅ {tname} اضافه شد!", clan_main_menu(True))
            return

        # ─── اخراج عضو از خاندان ───
        if wt == "clan_kick":
            cm = get_player_clan(uid)
            if not cm or cm["rank"] != "leader":
                waiting.pop(uid, None); return
            tname = " ".join(text.split())
            target = get_player_by_name(tname)
            if not target:
                send(chat_id, "❌ نیست.")
                waiting.pop(uid, None); return
            tc = get_player_clan(target["user_id"])
            if not tc or tc["clan_id"] != cm["clan_id"] or target["user_id"] == uid:
                send(chat_id, "❌ عضو خاندان تو نیست.")
                waiting.pop(uid, None); return
            kick_from_clan(target["user_id"])
            waiting.pop(uid, None)
            send(chat_id, f"✅ {tname} اخراج شد.", clan_main_menu(True))
            return

        # ─── ارتقا عضو ───
        if wt == "clan_promote":
            cm = get_player_clan(uid)
            if not cm or cm["rank"] != "leader":
                waiting.pop(uid, None); return
            tname = " ".join(text.split())
            target = get_player_by_name(tname)
            if not target:
                send(chat_id, "❌ نیست.")
                waiting.pop(uid, None); return
            tc = get_player_clan(target["user_id"])
            if not tc or tc["clan_id"] != cm["clan_id"]:
                send(chat_id, "❌ عضو تو نیست.")
                waiting.pop(uid, None); return
            order = CLAN_RANK_ORDER
            cur_idx = order.index(tc["rank"]) if tc["rank"] in order else len(order) - 1
            if cur_idx <= 1:
                send(chat_id, "❌ بالاترین رتبه.")
                waiting.pop(uid, None); return
            new_rank = order[cur_idx - 1]
            set_clan_rank(target["user_id"], new_rank)
            waiting.pop(uid, None)
            send(chat_id, f"✅ {tname} → {CLAN_RANKS[new_rank]}", clan_main_menu(True))
            return

        # ═══════════ ADMIN ═══════════
        if wt == "admin_set_level":
            if not is_admin(uid):
                waiting.pop(uid, None); return
            try:
                tid, val = text.split(); tid, val = int(tid), int(val)
            except ValueError:
                send(chat_id, "❌ <code>id level</code>")
                waiting.pop(uid, None); return
            if not get_player(tid):
                send(chat_id, "❌ نیست."); waiting.pop(uid, None); return
            update_player(tid, level=val)
            waiting.pop(uid, None)
            send(chat_id, f"✅ سطح: {val}", [[{"text": "👤", "callback_data": "admin:player"}]])
            return

        if wt == "admin_set_gold":
            if not is_admin(uid):
                waiting.pop(uid, None); return
            try:
                tid, val = text.split(); tid, val = int(tid), int(val)
            except ValueError:
                send(chat_id, "❌ <code>id amount</code>")
                waiting.pop(uid, None); return
            if not get_player(tid):
                send(chat_id, "❌"); waiting.pop(uid, None); return
            update_player(tid, gold=val)
            waiting.pop(uid, None)
            send(chat_id, f"✅ طلا: {val:,}", [[{"text": "👤", "callback_data": "admin:player"}]])
            return

        if wt == "admin_set_diamond":
            if not is_admin(uid):
                waiting.pop(uid, None); return
            try:
                tid, val = text.split(); tid, val = int(tid), int(val)
            except ValueError:
                send(chat_id, "❌"); waiting.pop(uid, None); return
            if not get_player(tid):
                send(chat_id, "❌"); waiting.pop(uid, None); return
            update_player(tid, diamonds=val)
            waiting.pop(uid, None)
            send(chat_id, f"✅ الماس: {val:,}", [[{"text": "👤", "callback_data": "admin:player"}]])
            return

        if wt == "admin_set_stats":
            if not is_admin(uid):
                waiting.pop(uid, None); return
            try:
                tid, val = text.split(); tid, val = int(tid), int(val)
            except ValueError:
                send(chat_id, "❌"); waiting.pop(uid, None); return
            if not get_player(tid):
                send(chat_id, "❌"); waiting.pop(uid, None); return
            update_player(tid, power=val, stamina=val, speed=val,
                          defense=val, luck=val, chakra=val)
            waiting.pop(uid, None)
            send(chat_id, f"✅ آمار: {val}", [[{"text": "👤", "callback_data": "admin:player"}]])
            return

        if wt == "admin_add_item":
            if not is_admin(uid):
                waiting.pop(uid, None); return
            parts = text.split(" ", 2)
            try:
                if len(parts) == 3:
                    tid, iname, qty = int(parts[0]), parts[1], int(parts[2])
                elif len(parts) == 2:
                    tid, iname, qty = int(parts[0]), parts[1], 1
                else:
                    raise ValueError
            except ValueError:
                send(chat_id, "❌ <code>id item qty</code>")
                waiting.pop(uid, None); return
            if not get_player(tid):
                send(chat_id, "❌"); waiting.pop(uid, None); return
            ok = add_item(tid, iname, qty)
            waiting.pop(uid, None)
            send(chat_id, f"{'✅' if ok else '❌ پر/نامعتبر'}",
                 [[{"text": "👤", "callback_data": "admin:player"}]])
            return

        # ─── فقط مالک ───
        if wt == "admin_clear_inv":
            if not is_owner(uid):
                waiting.pop(uid, None); return
            try:
                tid = int(text.strip())
            except ValueError:
                waiting.pop(uid, None); return
            if not get_player(tid):
                send(chat_id, "❌"); waiting.pop(uid, None); return
            clear_inventory(tid)
            waiting.pop(uid, None)
            send(chat_id, "✅ کیف پاک شد.", [[{"text": "👤", "callback_data": "admin:player"}]])
            return

        if wt == "admin_del_player":
            if not is_owner(uid):
                waiting.pop(uid, None); return
            try:
                tid = int(text.strip())
            except ValueError:
                waiting.pop(uid, None); return
            if not get_player(tid):
                send(chat_id, "❌"); waiting.pop(uid, None); return
            delete_player(tid)
            waiting.pop(uid, None)
            send(chat_id, "🗑️ حذف شد.", [[{"text": "🔧", "callback_data": "admin"}]])
            return

        if wt == "admin_ban":
            if not is_owner(uid):
                waiting.pop(uid, None); return
            try:
                tid = int(text.strip())
            except ValueError:
                waiting.pop(uid, None); return
            if not get_player(tid):
                send(chat_id, "❌"); waiting.pop(uid, None); return
            ban_player(tid)
            waiting.pop(uid, None)
            send(chat_id, "🚫 بن شد.", [[{"text": "🔧", "callback_data": "admin"}]])
            return

        if wt == "admin_unban":
            if not is_owner(uid):
                waiting.pop(uid, None); return
            try:
                tid = int(text.strip())
            except ValueError:
                waiting.pop(uid, None); return
            unban_player(tid)
            waiting.pop(uid, None)
            send(chat_id, "✅ آنبن شد.", [[{"text": "🔧", "callback_data": "admin"}]])
            return

        if wt == "admin_add_admin":
            if not is_owner(uid):
                waiting.pop(uid, None); return
            try:
                tid = int(text.strip())
            except ValueError:
                waiting.pop(uid, None); return
            ok, msg = add_admin(tid)
            waiting.pop(uid, None)
            send(chat_id, f"{'✅' if ok else '❌'} {msg}", admin_admins_menu())
            return

        if wt == "admin_gold":
            if not is_admin(uid):
                waiting.pop(uid, None); return
            try:
                tid, val = text.split(); tid, val = int(tid), int(val)
            except ValueError:
                send(chat_id, "❌ <code>id amount</code>")
                waiting.pop(uid, None); return
            if not get_player(tid):
                send(chat_id, "❌"); waiting.pop(uid, None); return
            add_field(tid, "gold", val)
            waiting.pop(uid, None)
            sign = "+" if val >= 0 else ""
            send(chat_id, f"💰 {sign}{val:,}", [[{"text": "🔧", "callback_data": "admin"}]])
            return

        if wt == "admin_diamond":
            if not is_admin(uid):
                waiting.pop(uid, None); return
            try:
                tid, val = text.split(); tid, val = int(tid), int(val)
            except ValueError:
                send(chat_id, "❌"); waiting.pop(uid, None); return
            if not get_player(tid):
                send(chat_id, "❌"); waiting.pop(uid, None); return
            add_field(tid, "diamonds", val)
            waiting.pop(uid, None)
            sign = "+" if val >= 0 else ""
            send(chat_id, f"💎 {sign}{val:,}", [[{"text": "🔧", "callback_data": "admin"}]])
            return

        if wt == "admin_gift_all":
            if not is_admin(uid):
                waiting.pop(uid, None); return
            try:
                field, val = text.split(); val = int(val)
            except ValueError:
                send(chat_id, "❌ <code>gold 1000</code>")
                waiting.pop(uid, None); return
            if field not in ("gold", "diamonds"):
                send(chat_id, "❌ gold یا diamonds")
                waiting.pop(uid, None); return
            ids = get_all_player_ids()
            for t in ids:
                add_field(t, field, val)
            waiting.pop(uid, None)
            send(chat_id, f"🎁 به {len(ids)} نفر +{val:,}",
                 [[{"text": "🔧", "callback_data": "admin"}]])
            return

        if wt == "admin_gift_one":
            if not is_admin(uid):
                waiting.pop(uid, None); return
            try:
                tid, field, val = text.split()
                tid, val = int(tid), int(val)
            except ValueError:
                send(chat_id, "❌ <code>id gold 1000</code>")
                waiting.pop(uid, None); return
            if field not in ("gold", "diamonds"):
                send(chat_id, "❌"); waiting.pop(uid, None); return
            if not get_player(tid):
                send(chat_id, "❌"); waiting.pop(uid, None); return
            add_field(tid, field, val)
            waiting.pop(uid, None)
            send(chat_id, f"🎁 +{val:,} {field}", [[{"text": "🔧", "callback_data": "admin"}]])
            return

        if wt == "admin_broadcast":
            if not is_admin(uid):
                waiting.pop(uid, None); return
            ids = get_all_player_ids()
            sent = 0
            for tid in ids:
                r = send(tid, f"📢 <b>پیام همگانی</b>\n\n{text}")
                if r and r.get("ok"):
                    sent += 1
            waiting.pop(uid, None)
            send(chat_id, f"✅ {sent}/{len(ids)}", [[{"text": "🔧", "callback_data": "admin"}]])
            return

        if wt == "admin_clan_gold":
            if not is_owner(uid):
                waiting.pop(uid, None); return
            try:
                name, val = text.rsplit(" ", 1); val = int(val)
            except ValueError:
                waiting.pop(uid, None); return
            cl = get_clan_by_name(name)
            if not cl:
                send(chat_id, "❌"); waiting.pop(uid, None); return
            update_clan(cl["id"], treasury_gold=cl["treasury_gold"] + val)
            waiting.pop(uid, None)
            send(chat_id, f"✅ +{val:,}", [[{"text": "🔧", "callback_data": "admin:clan"}]])
            return

        if wt == "admin_clan_level":
            if not is_owner(uid):
                waiting.pop(uid, None); return
            try:
                name, val = text.rsplit(" ", 1); val = int(val)
            except ValueError:
                waiting.pop(uid, None); return
            if not 1 <= val <= 10:
                send(chat_id, "❌ 1-10"); waiting.pop(uid, None); return
            cl = get_clan_by_name(name)
            if not cl:
                send(chat_id, "❌"); waiting.pop(uid, None); return
            update_clan(cl["id"], treasury_level=val)
            waiting.pop(uid, None)
            send(chat_id, f"✅ {val}", [[{"text": "🔧", "callback_data": "admin:clan"}]])
            return

        if wt == "admin_clan_del":
            if not is_owner(uid):
                waiting.pop(uid, None); return
            cl = get_clan_by_name(text.strip())
            if not cl:
                send(chat_id, "❌"); waiting.pop(uid, None); return
            delete_clan(cl["id"])
            waiting.pop(uid, None)
            send(chat_id, "🗑️", [[{"text": "🔧", "callback_data": "admin:clan"}]])
            return

        waiting.pop(uid, None)

    # ═══════════ مراحل ثبت‌نام ═══════════
    s = stage(p)
    if s == "name":
        name = " ".join(text.split())
        if not 3 <= len(name) <= 20:
            send(chat_id, "❌ ۳-۲۰."); return
        if name_exists(name):
            send(chat_id, "❌ گرفته شده."); return
        set_name(uid, name)
        send(chat_id, "⚧️ جنسیت:", gender_menu())
        return
    if s in ("gender", "class"):
        send(chat_id, "⚠️ با دکمه.")
        return

    send(chat_id, "👑 از دکمه‌ها استفاده کن.", main_menu_admin(uid))
  # ═══════════════════════════════════════
# CALLBACK
# ═══════════════════════════════════════

def handle_callback(callback):
    cb_id = callback.get("id")
    data = callback.get("data", "")
    msg = callback.get("message") or {}
    chat = msg.get("chat") or {}
    user = callback.get("from") or {}
    chat_id = chat.get("id")
    msg_id = msg.get("message_id")
    uid = user.get("id")

    if chat_id is None or uid is None:
        return
    if cb_id:
        answer(cb_id)

    p = get_player(uid)
    if not p:
        return

    # ─── بازگشت ───
    if data == "back":
        send(chat_id, main_text(), main_menu_admin(uid))
        return

    if data in ("boss:locked", "hunt:locked", "gb:noop"):
        return

    # ─── جنسیت ───
    if data in ("gender:male", "gender:female"):
        set_gender(uid, "مرد" if data.endswith("male") else "زن")
        send(chat_id, class_text(0), class_menu(0))
        return

    # ─── کلاس ───
    if data.startswith("class:"):
        parts = data.split(":")
        if len(parts) != 3:
            return
        try:
            idx = int(parts[2])
        except ValueError:
            return
        if not 0 <= idx < len(CLASSES):
            return
        action = parts[1]
        if action == "prev":
            idx = max(0, idx - 1)
            edit(chat_id, msg_id, class_text(idx), class_menu(idx))
        elif action == "next":
            idx = min(len(CLASSES) - 1, idx + 1)
            edit(chat_id, msg_id, class_text(idx), class_menu(idx))
        elif action == "select":
            c = CLASSES[idx]
            set_class(uid, c["key"])
            update_player(uid, power=c["power"], stamina=c["stamina"],
                          speed=c["speed"], defense=c["defense"],
                          luck=c["luck"], chakra=c["chakra"],
                          stat_points=5, hp=c["stamina"] * 200)
            send(chat_id, main_text(), main_menu_admin(uid))
        return

    # ═══════════ شخصیت ═══════════
    if data == "character":
        send(chat_id, "👤 <b>شخصیت</b>", character_menu(p)); return
    if data == "profile":
        send(chat_id, profile_text(p), [[{"text": "◀️", "callback_data": "character"}]]); return
    if data == "stats":
        send(chat_id, stats_text(p),
             [[{"text": "📈 افزایش", "callback_data": "increase_stats"}],
              [{"text": "◀️", "callback_data": "character"}]]); return
    if data == "increase_stats":
        send(chat_id, f"📈 امتیاز: {p['stat_points']}", increase_stats_menu(p)); return
    if data.startswith("stat:"):
        parts = data.split(":")
        if len(parts) != 3: return
        stat, amt = parts[1], parts[2]
        try: amount = int(amt)
        except ValueError: return
        if amount not in (1, 10): return
        if add_stat(uid, stat, amount):
            p = get_player(uid)
            edit(chat_id, msg_id, f"📈 امتیاز: {p['stat_points']}", increase_stats_menu(p))
        return
    if data == "skills":
        txt, kb = skills_text(p)
        send(chat_id, txt, kb); return
    if data == "equipment":
        send(chat_id, equipment_text(uid), [[{"text": "◀️", "callback_data": "character"}]]); return
    if data == "titles":
        send(chat_id, titles_text(uid), titles_menu(uid)); return
    if data.startswith("title:"):
        activate_title(uid, data.split(":", 1)[1])
        send(chat_id, titles_text(uid), titles_menu(uid)); return

    # ═══════════ کیف ═══════════
    if data == "inventory":
        open_inventory(chat_id, uid); return
    if data.startswith("inventory:"):
        try: page = int(data.split(":")[1])
        except (ValueError, IndexError): page = 0
        open_inventory(chat_id, uid, page, msg_id); return
    if data.startswith("item:"):
        open_item(chat_id, uid, data.split(":", 1)[1], msg_id); return
    if data.startswith("equip:"):
        name = data.split(":", 1)[1]
        if not get_item(uid, name):
            return
        slot = ITEM_SLOTS.get(name)
        if not slot:
            return
        equip_item(uid, slot, name)
        edit(chat_id, msg_id, f"✅ {name} تجهیز شد.",
             [[{"text": "🎒", "callback_data": "inventory"}],
              [{"text": "⚔️", "callback_data": "equipment"}]]); return
    if data.startswith("unequip:"):
        name = data.split(":", 1)[1]
        slot = get_equipped_slot(uid, name)
        if slot:
            unequip_item(uid, slot)
            edit(chat_id, msg_id, f"🔓 {name}",
                 [[{"text": "🎒", "callback_data": "inventory"}],
                  [{"text": "⚔️", "callback_data": "equipment"}]]); return
    if data.startswith("delete:"):
        name = data.split(":", 1)[1]
        item = get_item(uid, name)
        if not item: return
        slot = get_equipped_slot(uid, name)
        if item["quantity"] <= 1 and slot:
            unequip_item(uid, slot)
        if remove_item(uid, name, 1):
            edit(chat_id, msg_id, "✅ حذف شد.",
                 [[{"text": "🎒", "callback_data": "inventory"}]]); return

    # ═══════════ دانجن ═══════════
    if data == "dungeon":
        send(chat_id, "🏰 <b>دانجن</b>", dungeon_menu()); return
    if data == "dungeon:hunt":
        kb, rname, mult = hunt_menu(p["level"])
        send(chat_id,
             f"⚔️ <b>شکار</b>\n\n🎯 مرتبه: <b>{rname}</b>\n📊 ضریب: ×{mult}",
             kb); return
    if data.startswith("hunt:"):
        level = data[5:]
        b = start_hunt(uid, level)
        if not b:
            send(chat_id, "⚠️ در نبردی."); return
        send(chat_id, battle_text(uid), battle_keyboard(uid)); return
    if data == "battle":
        if uid in battles:
            send(chat_id, battle_text(uid), battle_keyboard(uid))
        return
    if data == "attack":
        res = player_attack(uid)
        if not res: return
        if res.startswith(("🏆", "💀")) or "نبردی نیست" in res:
            edit(chat_id, msg_id, res, [[{"text": "🏰", "callback_data": "dungeon"}]])
        else:
            edit(chat_id, msg_id, res, battle_keyboard(uid))
        return
    if data == "run":
        battles.pop(uid, None)
        edit(chat_id, msg_id, "🏃 فرار.",
             [[{"text": "🏰", "callback_data": "dungeon"}]]); return
    if data == "skill_menu":
        txt, kb = skill_menu_battle(uid)
        if txt:
            edit(chat_id, msg_id, txt, kb)
        return
    if data == "skill_back":
        if uid in battles:
            edit(chat_id, msg_id, battle_text(uid), battle_keyboard(uid))
        return
    if data == "skill_noop":
        return
    if data.startswith("skill:"):
        sid = data.split(":", 1)[1]
        res = use_skill(uid, sid)
        if not res: return
        if res.startswith(("🏆", "💀", "❌", "⏳")):
            edit(chat_id, msg_id, res, [[{"text": "🏰", "callback_data": "dungeon"}]])
        else:
            edit(chat_id, msg_id, res, battle_keyboard(uid))
        return

    # ─── گشت‌زنی / فارم / اتراق ───
    if data == "dungeon:scout":
        res = scout(uid)
        send(chat_id, f"🔍 {res}",
             [[{"text": "🔍", "callback_data": "dungeon:scout"},
               {"text": "◀️", "callback_data": "dungeon"}]]); return
    if data == "dungeon:farm":
        if get_busy(uid):
            send(chat_id, "⏳ مشغول."); return
        r = dungeon_farm(uid, chat_id)
        if r:
            send(chat_id, f"🌾 ۱۰ ثانیه... 🎁 {r}",
                 [[{"text": "◀️", "callback_data": "dungeon"}]]); return
    if data == "dungeon:camp":
        if camp(uid, chat_id):
            send(chat_id, "⛺ ۱۰ ثانیه...", [[{"text": "◀️", "callback_data": "dungeon"}]])
        return

    # ─── باس تکی ───
    if data == "dungeon:boss":
        send(chat_id, "🐉 <b>باس‌ها</b>", boss_regions_menu(p["level"])); return
    if data == "boss:regions":
        send(chat_id, "🐉 <b>باس‌ها</b>", boss_regions_menu(p["level"])); return
    if data.startswith("boss:region:"):
        rname = data.split(":", 2)[2]
        kb, txt = boss_region_menu(rname, p["level"])
        if kb:
            edit(chat_id, msg_id, txt, kb)
        return
    if data.startswith("boss:select:"):
        parts = data.split(":", 3)
        if len(parts) < 4: return
        txt, kb = boss_select_text(parts[2], parts[3])
        if txt:
            edit(chat_id, msg_id, txt, kb)
        return
    if data.startswith("boss:fight:"):
        parts = data.split(":", 3)
        if len(parts) < 4: return
        if uid in boss_battles:
            send(chat_id, "⚠️ در نبردی."); return
        res = start_boss_battle(uid, parts[2], parts[3])
        if res == "level_low":
            send(chat_id, "❌ سطح کم."); return
        if res == "locked":
            send(chat_id, "🔒 باز نشده."); return
        if not res:
            return
        send(chat_id, boss_battle_text(uid), boss_battle_keyboard(uid)); return
    if data == "boss:battle":
        if uid in boss_battles:
            send(chat_id, boss_battle_text(uid), boss_battle_keyboard(uid))
        return
    if data == "boss:attack":
        res = boss_player_attack(uid)
        if not res: return
        if res.startswith(("🏆", "💀")) or "نبردی نیست" in res:
            edit(chat_id, msg_id, res, [[{"text": "🐉", "callback_data": "boss:regions"}]])
        else:
            edit(chat_id, msg_id, res, boss_battle_keyboard(uid))
        return
    if data == "boss:run":
        boss_battles.pop(uid, None)
        edit(chat_id, msg_id, "🏃 فرار.",
             [[{"text": "🐉", "callback_data": "boss:regions"}]]); return
    if data == "boss:skill_menu":
        txt, kb = boss_skill_menu(uid)
        if txt:
            edit(chat_id, msg_id, txt, kb)
        return
    if data == "boss:skill_back":
        if uid in boss_battles:
            edit(chat_id, msg_id, boss_battle_text(uid), boss_battle_keyboard(uid))
        return
    if data == "boss:skill_noop":
        return
    if data.startswith("boss:skill:"):
        sid = data.split(":", 2)[2]
        res = boss_use_skill(uid, sid)
        if not res: return
        if res.startswith(("🏆", "💀", "❌", "⏳")):
            edit(chat_id, msg_id, res, [[{"text": "🐉", "callback_data": "boss:regions"}]])
        else:
            edit(chat_id, msg_id, res, boss_battle_keyboard(uid))
        return

    # ═══════════ نبرد گروهی ═══════════
    if data == "dungeon:gb":
        if not p["group_id"]:
            send(chat_id, "❌ عضو گروه نیستی.",
                 [[{"text": "◀️", "callback_data": "dungeon"}]]); return
        g = get_group(p["group_id"])
        if not g or g["leader_id"] != uid:
            send(chat_id, "❌ فقط رئیس گروه.",
                 [[{"text": "◀️", "callback_data": "dungeon"}]]); return
        # انتخاب منطقه باس
        send(chat_id,
             "👥 <b>نبرد گروهی</b>\n\nمنطقه رو انتخاب کن:\n"
             "<i>هر بازیکن با یه باس می‌جنگه</i>",
             boss_regions_menu(p["level"])) ; return

    if data.startswith("gb:region:"):
        rname = data.split(":", 2)[2]
        r = REGIONS.get(rname)
        if not r:
            return
        kb = []
        for b in r["bosses"]:
            if p["level"] >= b["unlock_level"]:
                kb.append([{"text": f"{b['name']}",
                            "callback_data": f"gb:start:{rname}:{b['key']}"}])
        kb.append([{"text": "◀️", "callback_data": "dungeon:gb"}])
        edit(chat_id, msg_id,
             f"👥 <b>نبرد گروهی</b>\n\n{rname}\n\nباس رو انتخاب کن:",
             kb); return

    if data.startswith("gb:start:"):
        parts = data.split(":", 3)
        if len(parts) < 4: return
        rname, bkey = parts[2], parts[3]
        res = start_group_battle(uid, rname, bkey)
        if res == "no_group":
            send(chat_id, "❌ گروه نداری."); return
        if res == "not_leader":
            send(chat_id, "❌ فقط رئیس."); return
        if res == "in_battle":
            send(chat_id, "⚠️ نبرد در جریانه."); return
        if not res:
            send(chat_id, "❌ خطا."); return
        gid = p["group_id"]
        r = send(chat_id, group_battle_text(gid), group_battle_keyboard(gid))
        if r and r.get("ok"):
            group_battles[gid]["chat_id"] = chat_id
            group_battles[gid]["msg_id"] = r["result"]["message_id"]
        return

    # ─── دکمه‌های نبرد گروهی ───
    if data.startswith("gb:attack:"):
        gid = int(data.split(":")[2])
        b = group_battles.get(gid)
        if not b:
            return
        # فقط نوبت خودش
        t = b["turn"]
        if t >= 5 or b["players"][t]["uid"] != uid:
            send(chat_id, "⏳ نوبت تو نیست."); return
        res = gb_player_attack(gid)
        if res is None: return
        if res == "boss_turn":
            res = gb_monster_turn(gid)
        if res and res.startswith(("🏆", "💀")):
            edit(chat_id, b["msg_id"], res, [[{"text": "🏰", "callback_data": "dungeon"}]])
        elif res:
            edit(chat_id, b["msg_id"], res, group_battle_keyboard(gid))
        return

    if data.startswith("gb:skip:"):
        gid = int(data.split(":")[2])
        b = group_battles.get(gid)
        if not b: return
        t = b["turn"]
        if t >= 5 or b["players"][t]["uid"] != uid:
            send(chat_id, "⏳ نوبت تو نیست."); return
        res = gb_skip_turn(gid)
        if res == "boss_turn":
            res = gb_monster_turn(gid)
        if res and res.startswith(("🏆", "💀")):
            edit(chat_id, b["msg_id"], res, [[{"text": "🏰", "callback_data": "dungeon"}]])
        elif res:
            edit(chat_id, b["msg_id"], res, group_battle_keyboard(gid))
        return

    if data.startswith("gb:monster:"):
        gid = int(data.split(":")[2])
        b = group_battles.get(gid)
        if not b or b["turn"] < 5:
            return
        res = gb_monster_turn(gid)
        if res == "boss_turn":
            res = gb_monster_turn(gid)  # اگه همه مردن دوباره
        if res and res.startswith(("🏆", "💀")):
            edit(chat_id, b["msg_id"], res, [[{"text": "🏰", "callback_data": "dungeon"}]])
        elif res:
            edit(chat_id, b["msg_id"], res, group_battle_keyboard(gid))
        return

    if data.startswith("gb:skill_menu:"):
        gid = int(data.split(":")[2])
        txt, kb = gb_skill_menu(gid)
        if txt and txt != "❌":
            edit(chat_id, msg_id, txt, kb)
        return
    if data.startswith("gb:back:"):
        gid = int(data.split(":")[2])
        b = group_battles.get(gid)
        if b:
            edit(chat_id, msg_id, group_battle_text(gid), group_battle_keyboard(gid))
        return
    if data.startswith("gb:skill:"):
        parts = data.split(":", 3)
        if len(parts) < 4: return
        sid, gid = parts[2], int(parts[3])
        b = group_battles.get(gid)
        if not b: return
        t = b["turn"]
        if t >= 5 or b["players"][t]["uid"] != uid:
            send(chat_id, "⏳ نوبت تو نیست."); return
        res = gb_use_skill(gid, sid)
        if not res: return
        if res.startswith(("🏆", "💀")):
            edit(chat_id, b["msg_id"], res, [[{"text": "🏰", "callback_data": "dungeon"}]])
        else:
            edit(chat_id, b["msg_id"], res, group_battle_keyboard(gid))
        return
    if data.startswith("gb:run:"):
        gid = int(data.split(":")[2])
        group_battles.pop(gid, None)
        edit(chat_id, msg_id, "🏃 فرار گروهی.",
             [[{"text": "🏰", "callback_data": "dungeon"}]]); return

    # ═══════════ مکان ═══════════
    if data == "location":
        send(chat_id, "🗺️ <b>مکان</b>", location_menu()); return
    if data == "loc:coffee":
        send(chat_id, "☕ <b>قهوه‌خانه</b>", coffee_menu()); return
    if data == "coffee:rest":
        mx = calc_hp_full(p, uid)
        if p["hp"] >= mx:
            send(chat_id, "☕ پره."); return
        update_player(uid, hp=mx)
        send(chat_id, f"☕ HP: {mx:,}",
             [[{"text": "◀️", "callback_data": "loc:coffee"}]]); return
    if data in ("coffee:mission", "coffee:drink", "coffee:chat",
                "loc:farm", "loc:smith", "loc:alchemy", "loc:genos"):
        send(chat_id, "🔒 به‌زودی...",
             [[{"text": "◀️", "callback_data": "location"}]]); return

    if data == "shop":
        send(chat_id, "🏪 به‌زودی...",
             [[{"text": "◀️", "callback_data": "back"}]]); return
    if data == "tower":
        send(chat_id, "🗼 به‌زودی...",
             [[{"text": "◀️", "callback_data": "back"}]]); return

    # ═══════════ رتبه‌بندی ═══════════
    if data == "ranking":
        send(chat_id, "🏆 <b>رتبه‌بندی</b>", ranking_menu()); return
    if data == "rank:level":
        send(chat_id, ranking_text("level", "برترین‌ها"),
             [[{"text": "◀️", "callback_data": "ranking"}]]); return
    if data == "rank:kills":
        send(chat_id, ranking_text("kills", "قاتل‌ها", " ☠️"),
             [[{"text": "◀️", "callback_data": "ranking"}]]); return
    if data == "rank:gold":
        send(chat_id, ranking_text("gold", "پولدارها", " 🪙"),
             [[{"text": "◀️", "callback_data": "ranking"}]]); return
    if data == "rank:power":
        send(chat_id, ranking_power_text(),
             [[{"text": "◀️", "callback_data": "ranking"}]]); return

    # ═══════════ بازار سیاه ═══════════
    if data == "black_market":
        send(chat_id, black_market_text(), black_market_menu()); return
    if data in ("bm:weapons", "bm:armors", "bm:shields", "bm:heads",
                "bm:necklaces", "bm:others", "bm:limited"):
        cat = data.split(":")[1]
        edit(chat_id, msg_id, bm_category_text(cat), bm_category_menu(cat)); return
    if data.startswith("bm:item:"):
        parts = data.split(":", 3)
        if len(parts) < 4: return
        edit(chat_id, msg_id, bm_item_text(parts[2], parts[3]),
             bm_item_menu(parts[2], parts[3])); return
    if data.startswith("bm:buy:"):
        parts = data.split(":", 3)
        if len(parts) < 4: return
        cat, name = parts[2], parts[3]
        info = BLACK_MARKET_ITEMS.get(cat, {}).get(name)
        if not info: return
        cur = "gold" if info["currency"] == "gold" else "diamonds"
        if p[cur] < info["price"]:
            send(chat_id, f"❌ {info['price']:,} کم داری."); return
        add_field(uid, cur, -info["price"])
        if add_item(uid, name, 1):
            send(chat_id, f"✅ {name}",
                 [[{"text": "🎒", "callback_data": "inventory"}],
                  [{"text": "◀️", "callback_data": f"bm:{cat}"}]]); return
        add_field(uid, cur, info["price"])
        send(chat_id, "❌ کیف پر!")
        return

    # ═══════════ تنظیمات ═══════════
    if data == "settings":
        send(chat_id, "⚙️", settings_menu()); return
    if data == "set:name":
        waiting[uid] = {"type": "new_name"}
        send(chat_id, "✏️ اسم جدید:",
             [[{"text": "◀️", "callback_data": "settings"}]]); return
    if data == "set:gender":
        send(chat_id, "⚧️",
             [[{"text": "👨", "callback_data": "set:gender:male"},
               {"text": "👩", "callback_data": "set:gender:female"}]]); return
    if data.startswith("set:gender:"):
        g = data.split(":")[2]
        update_player(uid, gender="مرد" if g == "male" else "زن")
        send(chat_id, "✅", [[{"text": "⚙️", "callback_data": "settings"}]]); return
    if data == "set:delete":
        send(chat_id, "⚠️ مطمئنی؟",
             [[{"text": "بله", "callback_data": "set:delete:yes"}],
              [{"text": "❌", "callback_data": "settings"}]]); return
    if data == "set:delete:yes":
        delete_player(uid)
        create_player(uid, chat_id)
        send(chat_id, "🗑️ /start بزن."); return

    # ═══════════ خاندان ═══════════
    if data == "clan":
        cm = get_player_clan(uid)
        if cm:
            cl = get_clan(cm["clan_id"])
            if cl:
                send(chat_id, clan_view_text(cl, cm["rank"], uid),
                     clan_main_menu(cm["rank"] == "leader"))
                return
        send(chat_id, "👑 خاندان نداری.", clan_no_member_menu()); return
    if data == "clan:create":
        if p["gold"] < CLAN_CREATE_COST:
            send(chat_id, f"❌ نیاز: {CLAN_CREATE_COST:,}"); return
        waiting[uid] = {"type": "clan_name"}
        send(chat_id, "🏗️ اسم خاندان:",
             [[{"text": "◀️", "callback_data": "clan"}]]); return
    if data == "clan:search":
        waiting[uid] = {"type": "clan_search"}
        send(chat_id, "🔍 اسم:",
             [[{"text": "◀️", "callback_data": "clan"}]]); return
    if data == "clan:list":
        top = get_top_clans(10)
        if not top:
            send(chat_id, "📜 خالی"); return
        lines = ["📜 <b>برترین خاندان‌ها</b>", ""]
        for i, c in enumerate(top):
            m = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
            lines.append(f"{m} <b>{c['name']}</b> | 👥{c['members']}")
        send(chat_id, "\n".join(lines),
             [[{"text": "◀️", "callback_data": "clan"}]]); return
    if data.startswith("clan:req:"):
        cl_id = int(data.split(":")[2])
        if get_player_clan(uid):
            send(chat_id, "❌ تو یه خاندانی."); return
        if add_clan_request(cl_id, uid):
            send(chat_id, "✅ ثبت شد.")
        else:
            send(chat_id, "⚠️ قبلاً دادی.")
        return
    if data == "clan:members":
        cm = get_player_clan(uid)
        if not cm: return
        cl = get_clan(cm["clan_id"])
        members = get_clan_members(cl["id"])
        members.sort(key=lambda m: (
            m["rank"] in ("leader", "noble"),
            get_player(m["user_id"]) and calc_power(get_player(m["user_id"]), m["user_id"]) or 0
        ), reverse=True)
        lines = [f"👥 <b>{cl['name']}</b>", ""]
        for m in members[:5]:
            lines.append(clan_member_line(m))
        send(chat_id, "\n".join(lines),
             [[{"text": "◀️", "callback_data": "clan"}]]); return
    if data == "clan:ranking":
        send(chat_id, "🏆", clan_ranking_menu()); return
    if data == "clan:r:members":
        top = get_top_clans(10)
        lines = ["👥 پرعضوترین"]
        for c in sorted(top, key=lambda x: -x["members"])[:10]:
            lines.append(f"• {c['name']} — {c['members']}")
        send(chat_id, "\n".join(lines), [[{"text": "◀️", "callback_data": "clan:ranking"}]]); return
    if data == "clan:r:gold":
        top = get_top_clans(10)
        lines = ["💰 ثروتمندترین"]
        for c in sorted(top, key=lambda x: -x["treasury_gold"])[:10]:
            lines.append(f"• {c['name']} — {c['treasury_gold']:,}")
        send(chat_id, "\n".join(lines), [[{"text": "◀️", "callback_data": "clan:ranking"}]]); return
    if data == "clan:r:level":
        send(chat_id, ranking_text("level", "برترین"),
             [[{"text": "◀️", "callback_data": "clan:ranking"}]]); return
    if data == "clan:treasury":
        cm = get_player_clan(uid)
        if not cm: return
        cl = get_clan(cm["clan_id"])
        send(chat_id, f"💰 {cl['treasury_gold']:,} 🪙 | 💎 {cl['treasury_diamond']:,}",
             [[{"text": "◀️", "callback_data": "clan"}]]); return
    if data == "clan:alliance":
        send(chat_id, "🤝 به‌زودی...",
             [[{"text": "◀️", "callback_data": "clan"}]]); return
    if data == "clan:add_member":
        cm = get_player_clan(uid)
        if not cm or cm["rank"] != "leader":
            return
        waiting[uid] = {"type": "clan_add_member"}
        send(chat_id, "➕ اسم عضو:",
             [[{"text": "◀️", "callback_data": "clan"}]]); return
    if data == "clan:kick":
        cm = get_player_clan(uid)
        if not cm or cm["rank"] != "leader":
            return
        waiting[uid] = {"type": "clan_kick"}
        send(chat_id, "➖ اسم عضو:",
             [[{"text": "◀️", "callback_data": "clan"}]]); return
    if data == "clan:promote":
        cm = get_player_clan(uid)
        if not cm or cm["rank"] != "leader":
            return
        waiting[uid] = {"type": "clan_promote"}
        send(chat_id, "⬆️ اسم عضو:",
             [[{"text": "◀️", "callback_data": "clan"}]]); return
    if data == "clan:requests":
        cm = get_player_clan(uid)
        if not cm or cm["rank"] != "leader":
            return
        reqs = get_clan_requests(cm["clan_id"])
        if not reqs:
            send(chat_id, "📩 خالی", [[{"text": "◀️", "callback_data": "clan"}]])
            return
        kb = []
        for r in reqs:
            kb.append([{"text": f"✅ {r['name']}",
                        "callback_data": f"clan:accept:{r['user_id']}"}])
        kb.append([{"text": "◀️", "callback_data": "clan"}])
        send(chat_id, f"📩 {len(reqs)} درخواست", kb); return
    if data.startswith("clan:accept:"):
        tgt = int(data.split(":")[2])
        cm = get_player_clan(uid)
        if not cm or cm["rank"] != "leader": return
        if get_clan_members_count(cm["clan_id"]) >= CLAN_MAX_MEMBERS:
            send(chat_id, "❌ پر."); return
        from database import connect
        con = connect()
        con.execute("DELETE FROM clan_members WHERE user_id=?", (tgt,))
        con.execute("INSERT INTO clan_members(user_id, clan_id, rank, joined_at) VALUES(?,?,?,?)",
                    (tgt, cm["clan_id"], "member", time.time()))
        con.execute("DELETE FROM clan_requests WHERE user_id=?", (tgt,))
        con.commit(); con.close()
        send(chat_id, "✅ اضافه شد.",
             [[{"text": "◀️", "callback_data": "clan"}]]); return
    if data == "clan:disband":
        cm = get_player_clan(uid)
        if not cm or cm["rank"] != "leader": return
        send(chat_id, "💥 مطمئنی؟",
             [[{"text": "بله", "callback_data": "clan:disband:yes"}],
              [{"text": "❌", "callback_data": "clan"}]]); return
    if data == "clan:disband:yes":
        cm = get_player_clan(uid)
        if not cm or cm["rank"] != "leader": return
        delete_clan(cm["clan_id"])
        send(chat_id, "💥 منحل شد.", [[{"text": "👑", "callback_data": "clan"}]]); return

    # ═══════════ گروه ═══════════
    if data == "coffee:group":
        if p["group_id"]:
            g = get_group(p["group_id"])
            if g:
                send(chat_id, group_view_text(g),
                     group_member_menu(g["leader_id"] == uid))
                return
        send(chat_id, "👥 گروه نداری.", group_no_member_menu()); return
    if data == "group:create":
        waiting[uid] = {"type": "group_name"}
        send(chat_id, "🏗️ اسم گروه:",
             [[{"text": "◀️", "callback_data": "coffee:group"}]]); return
    if data == "group:members":
        g = get_group(p["group_id"])
        if not g: return
        members = get_group_members(g["id"], 5)
        lines = [f"👥 <b>{g['name']}</b>", ""]
        for i, m in enumerate(members, 1):
            lines.append(f"{i}. <b>{m['name']}</b> | Lv.{m['level']}")
        send(chat_id, "\n".join(lines),
             [[{"text": "◀️", "callback_data": "coffee:group"}]]); return
    if data == "group:add":
        g = get_group(p["group_id"])
        if not g or g["leader_id"] != uid:
            send(chat_id, "❌ فقط رئیس."); return
        if get_group_count(g["id"]) >= 5:
            send(chat_id, "❌ پر (۵)."); return
        waiting[uid] = {"type": "group_add"}
        send(chat_id, "➕ اسم بازیکن:",
             [[{"text": "◀️", "callback_data": "coffee:group"}]]); return
    if data == "group:kick":
        g = get_group(p["group_id"])
        if not g or g["leader_id"] != uid:
            return
        waiting[uid] = {"type": "group_kick"}
        send(chat_id, "➖ اسم بازیکن:",
             [[{"text": "◀️", "callback_data": "coffee:group"}]]); return
    if data == "group:leave":
        send(chat_id, "🚪 مطمئنی؟",
             [[{"text": "بله", "callback_data": "group:leave:yes"}],
              [{"text": "❌", "callback_data": "coffee:group"}]]); return
    if data == "group:leave:yes":
        g = get_group(p["group_id"])
        if g and g["leader_id"] == uid:
            delete_group(g["id"])
            send(chat_id, "🚪 منحل شد.")
        else:
            set_group(uid, 0)
            send(chat_id, "🚪 خارج شدی.")
        return

    # ═══════════ ادمین ═══════════
    if data == "admin":
        if not is_admin(uid):
            send(chat_id, "⛔"); return
        role = "👑 مالک" if is_owner(uid) else "🛡️ ادمین"
        send(chat_id, f"🔧 پنل {role}", admin_menu(uid)); return
    if data == "admin:player":
        if not is_admin(uid): return
        send(chat_id, "👤", admin_player_menu(uid)); return
    if data == "admin:set_level":
        if not is_admin(uid): return
        waiting[uid] = {"type": "admin_set_level"}
        send(chat_id, "✏️ <code>id level</code>",
             [[{"text": "◀️", "callback_data": "admin:player"}]]); return
    if data == "admin:set_gold":
        if not is_admin(uid): return
        waiting[uid] = {"type": "admin_set_gold"}
        send(chat_id, "💰 <code>id amount</code>",
             [[{"text": "◀️", "callback_data": "admin:player"}]]); return
    if data == "admin:set_diamond":
        if not is_admin(uid): return
        waiting[uid] = {"type": "admin_set_diamond"}
        send(chat_id, "💎 <code>id amount</code>",
             [[{"text": "◀️", "callback_data": "admin:player"}]]); return
    if data == "admin:set_stats":
        if not is_admin(uid): return
        waiting[uid] = {"type": "admin_set_stats"}
        send(chat_id, "⚡ <code>id value</code>",
             [[{"text": "◀️", "callback_data": "admin:player"}]]); return
    if data == "admin:add_item":
        if not is_admin(uid): return
        waiting[uid] = {"type": "admin_add_item"}
        send(chat_id, "🎒 <code>id item qty</code>",
             [[{"text": "◀️", "callback_data": "admin:player"}]]); return
    if data == "admin:clear_inv":
        if not is_owner(uid): return
        waiting[uid] = {"type": "admin_clear_inv"}
        send(chat_id, "🗑️ <code>id</code>",
             [[{"text": "◀️", "callback_data": "admin:player"}]]); return
    if data == "admin:del_player":
        if not is_owner(uid): return
        waiting[uid] = {"type": "admin_del_player"}
        send(chat_id, "❌ <code>id</code>",
             [[{"text": "◀️", "callback_data": "admin:player"}]]); return
    if data == "admin:gift":
        if not is_admin(uid): return
        send(chat_id, "🎁",
             [[{"text": "همه", "callback_data": "admin:gift:all"},
               {"text": "یکی", "callback_data": "admin:gift:one"}],
              [{"text": "◀️", "callback_data": "admin"}]]); return
    if data == "admin:gift:all":
        if not is_admin(uid): return
        waiting[uid] = {"type": "admin_gift_all"}
        send(chat_id, "🎁 <code>gold 1000000</code>",
             [[{"text": "◀️", "callback_data": "admin:gift"}]]); return
    if data == "admin:gift:one":
        if not is_admin(uid): return
        waiting[uid] = {"type": "admin_gift_one"}
        send(chat_id, "🎁 <code>id gold 500000</code>",
             [[{"text": "◀️", "callback_data": "admin:gift"}]]); return
    if data == "admin:gold":
        if not is_admin(uid): return
        waiting[uid] = {"type": "admin_gold"}
        send(chat_id, "💰 <code>id amount</code> (+/-)",
             [[{"text": "◀️", "callback_data": "admin"}]]); return
    if data == "admin:diamond":
        if not is_admin(uid): return
        waiting[uid] = {"type": "admin_diamond"}
        send(chat_id, "💎 <code>id amount</code> (+/-)",
             [[{"text": "◀️", "callback_data": "admin"}]]); return
    if data == "admin:stats":
        if not is_admin(uid): return
        s = get_stats()
        send(chat_id,
             f"📊 <b>آمار</b>\n\n👥 {s['players']}\n🏰 {s['clans']}\n"
             f"👥 {s['groups']}\n🪙 {s['total_gold']:,}\n💎 {s['total_diamond']:,}\n"
             f"☠️ {s['total_kills']:,}\n🚫 {s['banned']}",
             [[{"text": "◀️", "callback_data": "admin"}]]); return
    if data == "admin:broadcast":
        if not is_admin(uid): return
        waiting[uid] = {"type": "admin_broadcast"}
        send(chat_id, "📢 پیام:",
             [[{"text": "◀️", "callback_data": "admin"}]]); return
    if data == "admin:clan":
        if not is_owner(uid): return
        send(chat_id, "🏰",
             [[{"text": "💰", "callback_data": "admin:clan:gold"},
               {"text": "⭐", "callback_data": "admin:clan:level"}],
              [{"text": "🗑️", "callback_data": "admin:clan:del"}],
              [{"text": "◀️", "callback_data": "admin"}]]); return
    if data == "admin:clan:gold":
        if not is_owner(uid): return
        waiting[uid] = {"type": "admin_clan_gold"}
        send(chat_id, "💰 <code>name amount</code>",
             [[{"text": "◀️", "callback_data": "admin:clan"}]]); return
    if data == "admin:clan:level":
        if not is_owner(uid): return
        waiting[uid] = {"type": "admin_clan_level"}
        send(chat_id, "⭐ <code>name level</code>",
             [[{"text": "◀️", "callback_data": "admin:clan"}]]); return
    if data == "admin:clan:del":
        if not is_owner(uid): return
        waiting[uid] = {"type": "admin_clan_del"}
        send(chat_id, "🗑️ name",
             [[{"text": "◀️", "callback_data": "admin:clan"}]]); return
    if data == "admin:admins":
        if not is_owner(uid): return
        send(chat_id, f"🛡️ {len(get_admins())}/{MAX_ADMINS}",
             admin_admins_menu()); return
    if data == "admin:add_admin":
        if not is_owner(uid): return
        waiting[uid] = {"type": "admin_add_admin"}
        send(chat_id, "🛡️ آیدی عددی:",
             [[{"text": "◀️", "callback_data": "admin:admins"}]]); return
    if data.startswith("admin:rm_admin:"):
        if not is_owner(uid): return
        tgt = int(data.split(":")[2])
        remove_admin(tgt)
        send(chat_id, "✅", admin_admins_menu()); return
    if data == "admin:ban":
        if not is_owner(uid): return
        send(chat_id, "🚫",
             [[{"text": "بن", "callback_data": "admin:ban:do"},
               {"text": "آنبن", "callback_data": "admin:ban:undo"}],
              [{"text": "◀️", "callback_data": "admin"}]]); return
    if data == "admin:ban:do":
        if not is_owner(uid): return
        waiting[uid] = {"type": "admin_ban"}
        send(chat_id, "🚫 id:",
             [[{"text": "◀️", "callback_data": "admin:ban"}]]); return
    if data == "admin:ban:undo":
        if not is_owner(uid): return
        waiting[uid] = {"type": "admin_unban"}
        send(chat_id, "✅ id:",
             [[{"text": "◀️", "callback_data": "admin:ban"}]]); return
    if data == "admin:del_all":
        if not is_owner(uid): return
        send(chat_id, "⚠️ مطمئنی؟ همه بازیکنان!",
             [[{"text": "بله", "callback_data": "admin:del_all:yes"}],
              [{"text": "❌", "callback_data": "admin"}]]); return
    if data == "admin:del_all:yes":
        if not is_owner(uid): return
        from database import connect
        con = connect()
        for t in ["players", "inventory", "equipment", "titles", "busy",
                  "clan_members", "clan_requests", "boss_drops", "boss_kills",
                  "clans", "groups"]:
            try:
                con.execute(f"DELETE FROM {t}")
            except Exception:
                pass
        con.commit(); con.close()
        send(chat_id, "🗑️ پاک شد!", [[{"text": "🔧", "callback_data": "admin"}]]); return


# ═══════════════════════════════════════
# UPDATE / MAIN
# ═══════════════════════════════════════

def handle_update(update):
    if update.get("message"):
        handle_message(update["message"])
    elif update.get("callback_query"):
        handle_callback(update["callback_query"])


def main():
    print("GodsTower Bot is running...")
    offset = None
    while True:
        try:
            result = get_updates(offset)
            if not result or not result.get("ok"):
                time.sleep(3)
                continue
            for u in result.get("result", []):
                uid_ = u.get("update_id")
                if uid_ is not None:
                    offset = uid_ + 1
                try:
                    handle_update(u)
                except Exception as e:
                    print(f"Update Error: {e}")
        except KeyboardInterrupt:
            print("\nBot stopped.")
            break
        except Exception as e:
            print(f"Main Error: {e}")
            time.sleep(3)


if __name__ == "__main__":
    main()