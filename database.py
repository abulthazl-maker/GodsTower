import sqlite3
import time

DB = "players.db"
MAX_INVENTORY = 50

OWNER_IDS = [1696799216]
ADMIN_IDS = [1562929674]
MAX_ADMINS = 4

waiting = {}


def connect():
    con = sqlite3.connect(DB, timeout=30, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    return con


def init_db():
    con = connect()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            chat_id INTEGER NOT NULL,
            name TEXT,
            gender TEXT,
            player_class TEXT,
            hp INTEGER DEFAULT 100,
            power INTEGER DEFAULT 0,
            stamina INTEGER DEFAULT 0,
            speed INTEGER DEFAULT 0,
            defense INTEGER DEFAULT 0,
            luck INTEGER DEFAULT 0,
            chakra INTEGER DEFAULT 0,
            talent INTEGER DEFAULT 0,
            stat_points INTEGER DEFAULT 5,
            level INTEGER DEFAULT 1,
            xp INTEGER DEFAULT 0,
            gold INTEGER DEFAULT 0,
            diamonds INTEGER DEFAULT 0,
            vip_level INTEGER DEFAULT 0,
            daily_xp INTEGER DEFAULT 0,
            daily_hunts INTEGER DEFAULT 0,
            daily_boss INTEGER DEFAULT 0,
            last_reset TEXT DEFAULT '',
            kills INTEGER DEFAULT 0,
            deaths INTEGER DEFAULT 0,
            group_id INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0
        )
    """)
    cur.execute("""CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, item_name TEXT NOT NULL)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS equipment (user_id INTEGER NOT NULL, slot TEXT NOT NULL, item_name TEXT, PRIMARY KEY(user_id, slot))""")
    cur.execute("""CREATE TABLE IF NOT EXISTS titles (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, title TEXT NOT NULL, active INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS busy (user_id INTEGER PRIMARY KEY, type TEXT, end_time REAL, extra TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS clans (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, motto TEXT, leader_id INTEGER NOT NULL, treasury_gold INTEGER DEFAULT 0, treasury_diamond INTEGER DEFAULT 0, treasury_items INTEGER DEFAULT 0, treasury_level INTEGER DEFAULT 1, created_at REAL)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS clan_members (user_id INTEGER PRIMARY KEY, clan_id INTEGER NOT NULL, rank TEXT DEFAULT 'member', joined_at REAL)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS clan_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, clan_id INTEGER NOT NULL, user_id INTEGER NOT NULL, created_at REAL, UNIQUE(clan_id, user_id))""")
    cur.execute("""CREATE TABLE IF NOT EXISTS clan_alliances (id INTEGER PRIMARY KEY AUTOINCREMENT, clan_a INTEGER NOT NULL, clan_b INTEGER NOT NULL, created_at REAL, UNIQUE(clan_a, clan_b))""")
    cur.execute("""CREATE TABLE IF NOT EXISTS groups (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, leader_id INTEGER NOT NULL, created_at REAL)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS boss_drops (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, boss_key TEXT NOT NULL, item_name TEXT NOT NULL, dropped_at REAL)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS boss_kills (user_id INTEGER NOT NULL, boss_key TEXT NOT NULL, kills INTEGER DEFAULT 0, PRIMARY KEY(user_id, boss_key))""")
    con.commit()
    con.close()


# ═════ PLAYER ═════

def get_player(uid):
    con = connect()
    row = con.execute("SELECT * FROM players WHERE user_id=?", (uid,)).fetchone()
    con.close()
    return dict(row) if row else None


def get_player_by_name(name):
    con = connect()
    row = con.execute("SELECT * FROM players WHERE name=?", (name,)).fetchone()
    con.close()
    return dict(row) if row else None


def create_player(uid, chat_id):
    con = connect()
    con.execute("INSERT OR IGNORE INTO players(user_id, chat_id) VALUES(?, ?)", (uid, chat_id))
    con.commit()
    con.close()


def update_player(uid, **data):
    if not data:
        return
    fields = ", ".join(f"{k}=?" for k in data)
    con = connect()
    con.execute(f"UPDATE players SET {fields} WHERE user_id=?", (*data.values(), uid))
    con.commit()
    con.close()


def add_field(uid, field, amount):
    allowed = {"hp", "power", "stamina", "speed", "defense", "luck", "chakra",
               "talent", "stat_points", "level", "xp", "gold", "diamonds",
               "vip_level", "daily_xp", "daily_hunts", "daily_boss", "kills", "deaths"}
    if field not in allowed:
        return False
    con = connect()
    con.execute(f"UPDATE players SET {field}={field}+? WHERE user_id=?", (amount, uid))
    con.commit()
    con.close()
    return True


def name_exists(name):
    con = connect()
    row = con.execute("SELECT 1 FROM players WHERE name=? LIMIT 1", (name,)).fetchone()
    con.close()
    return bool(row)


def set_name(uid, name): update_player(uid, name=name)
def set_gender(uid, gender): update_player(uid, gender=gender)
def set_class(uid, player_class): update_player(uid, player_class=player_class)


def add_stat(uid, stat, amount=1):
    allowed = {"power", "stamina", "speed", "defense", "luck", "chakra"}
    if stat not in allowed or amount <= 0:
        return False
    p = get_player(uid)
    if not p or p["stat_points"] < amount:
        return False
    update_player(uid, **{stat: p[stat] + amount, "stat_points": p["stat_points"] - amount})
    return True


def delete_player(uid):
    con = connect()
    for t in ["players", "inventory", "equipment", "titles", "busy",
              "clan_members", "clan_requests", "boss_drops", "boss_kills"]:
        try:
            con.execute(f"DELETE FROM {t} WHERE user_id=?", (uid,))
        except Exception:
            pass
    con.commit()
    con.close()


def get_top(order, limit=10):
    allowed = {"level", "gold", "kills", "deaths"}
    if order not in allowed:
        return []
    con = connect()
    rows = con.execute(
        f"SELECT name, level, player_class, {order} as val "
        f"FROM players WHERE name IS NOT NULL ORDER BY {order} DESC LIMIT ?",
        (limit,)
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


def get_top_power(limit=10):
    con = connect()
    rows = con.execute("""
        SELECT name, level, player_class,
               (power + stamina + speed + defense + luck + chakra) as val
        FROM players WHERE name IS NOT NULL ORDER BY val DESC LIMIT ?
    """, (limit,)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def count_players():
    con = connect()
    n = con.execute("SELECT COUNT(*) FROM players WHERE name IS NOT NULL").fetchone()[0]
    con.close()
    return n


def get_all_player_ids():
    con = connect()
    rows = con.execute("SELECT user_id FROM players WHERE name IS NOT NULL").fetchall()
    con.close()
    return [r["user_id"] for r in rows]


# ═════ INVENTORY ═════

def add_item(uid, item, qty=1):
    if qty <= 0:
        return False
    con = connect()
    c = con.execute("SELECT COUNT(*) FROM inventory WHERE user_id=?", (uid,)).fetchone()[0]
    if c + qty > MAX_INVENTORY:
        con.close()
        return False
    for _ in range(qty):
        con.execute("INSERT INTO inventory(user_id, item_name) VALUES(?, ?)", (uid, item))
    con.commit()
    con.close()
    return True


def remove_item(uid, item, qty=1):
    if qty <= 0:
        return False
    con = connect()
    rows = con.execute("SELECT id FROM inventory WHERE user_id=? AND item_name=? LIMIT ?",
                       (uid, item, qty)).fetchall()
    if len(rows) < qty:
        con.close()
        return False
    ids = [str(r["id"]) for r in rows]
    con.execute(f"DELETE FROM inventory WHERE id IN ({','.join(ids)})")
    con.commit()
    con.close()
    return True


def get_inventory(uid):
    con = connect()
    rows = con.execute(
        "SELECT item_name, COUNT(*) as qty, MIN(id) as first_id "
        "FROM inventory WHERE user_id=? GROUP BY item_name ORDER BY first_id",
        (uid,)).fetchall()
    con.close()
    return [{"item_name": r["item_name"], "quantity": r["qty"]} for r in rows]


def clear_inventory(uid):
    con = connect()
    con.execute("DELETE FROM inventory WHERE user_id=?", (uid,))
    con.commit()
    con.close()


# ═════ EQUIPMENT ═════

SLOTS = {"head": "🪖", "body": "👕", "cloak": "🪽", "main": "⚔️",
         "off": "🛡️", "ring": "💍", "legs": "👖", "boots": "🥾"}


def get_equipment(uid):
    con = connect()
    rows = con.execute(
        "SELECT slot, item_name FROM equipment WHERE user_id=? AND item_name IS NOT NULL",
        (uid,)).fetchall()
    con.close()
    return {r["slot"]: r["item_name"] for r in rows}


def equip_item(uid, slot, item):
    if slot not in SLOTS:
        return False
    con = connect()
    con.execute("""INSERT INTO equipment(user_id, slot, item_name) VALUES(?, ?, ?)
                   ON CONFLICT(user_id, slot) DO UPDATE SET item_name=excluded.item_name""",
                (uid, slot, item))
    con.commit()
    con.close()
    return True


def unequip_item(uid, slot):
    con = connect()
    con.execute("DELETE FROM equipment WHERE user_id=? AND slot=?", (uid, slot))
    con.commit()
    con.close()


def clear_equipment(uid):
    con = connect()
    con.execute("DELETE FROM equipment WHERE user_id=?", (uid,))
    con.commit()
    con.close()


# ═════ TITLES ═════

def add_title(uid, title):
    con = connect()
    con.execute("INSERT INTO titles(user_id, title) VALUES(?, ?)", (uid, title))
    con.commit()
    con.close()


def get_titles(uid):
    con = connect()
    rows = con.execute("SELECT title, active FROM titles WHERE user_id=? ORDER BY id",
                       (uid,)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def activate_title(uid, title):
    con = connect()
    con.execute("UPDATE titles SET active=0 WHERE user_id=?", (uid,))
    con.execute("UPDATE titles SET active=1 WHERE user_id=? AND title=?", (uid, title))
    con.commit()
    con.close()


# ═════ BUSY ═════

def set_busy(uid, btype, end_time, extra=None):
    con = connect()
    con.execute("""INSERT INTO busy(user_id, type, end_time, extra) VALUES(?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                   type=excluded.type, end_time=excluded.end_time, extra=excluded.extra""",
                (uid, btype, end_time, extra))
    con.commit()
    con.close()


def get_busy(uid):
    con = connect()
    row = con.execute("SELECT * FROM busy WHERE user_id=?", (uid,)).fetchone()
    con.close()
    return dict(row) if row else None


def clear_busy(uid):
    con = connect()
    con.execute("DELETE FROM busy WHERE user_id=?", (uid,))
    con.commit()
    con.close()


# ═════ CLANS ═════

CLAN_CREATE_COST = 500_000
CLAN_MAX_MEMBERS = 20

CLAN_RANKS = {"leader": "👑 رئیس خاندان", "noble": "💎 ارجمند",
              "family": "🏠 عضو خانواده", "commander": "⚔️ فرمانده",
              "member": "👤 عضو"}
CLAN_RANK_ORDER = ["leader", "noble", "family", "commander", "member"]

TREASURY_CAP_GOLD = [0, 50_000, 100_000, 250_000, 500_000,
                     1_000_000, 2_000_000, 3_000_000, 4_000_000, 5_000_000]
TREASURY_CAP_DIAMOND = [0, 50, 100, 250, 500, 1_000, 2_000, 3_000, 4_000, 5_000]
TREASURY_CAP_ITEMS = [0, 4, 6, 8, 10, 12, 14, 16, 18, 20]


def clan_name_exists(name):
    con = connect()
    row = con.execute("SELECT 1 FROM clans WHERE name=? LIMIT 1", (name,)).fetchone()
    con.close()
    return bool(row)


def create_clan(name, motto, leader_id):
    con = connect()
    cur = con.execute("INSERT INTO clans(name, motto, leader_id, created_at) VALUES(?,?,?,?)",
                      (name, motto, leader_id, time.time()))
    cid = cur.lastrowid
    con.execute("INSERT INTO clan_members(user_id, clan_id, rank, joined_at) VALUES(?,?,?,?)",
                (leader_id, cid, "leader", time.time()))
    con.commit()
    con.close()
    return cid


def get_clan(cid):
    con = connect()
    row = con.execute("SELECT * FROM clans WHERE id=?", (cid,)).fetchone()
    con.close()
    return dict(row) if row else None


def get_clan_by_name(name):
    con = connect()
    row = con.execute("SELECT * FROM clans WHERE name=?", (name,)).fetchone()
    con.close()
    return dict(row) if row else None


def get_player_clan(uid):
    con = connect()
    row = con.execute("SELECT * FROM clan_members WHERE user_id=?", (uid,)).fetchone()
    con.close()
    return dict(row) if row else None


def get_clan_members(cid):
    con = connect()
    rows = con.execute("""SELECT cm.user_id, cm.rank, cm.joined_at, p.name, p.level, p.player_class
                          FROM clan_members cm
                          LEFT JOIN players p ON p.user_id=cm.user_id
                          WHERE cm.clan_id=? ORDER BY cm.joined_at ASC""", (cid,)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def get_clan_members_count(cid):
    con = connect()
    n = con.execute("SELECT COUNT(*) FROM clan_members WHERE clan_id=?", (cid,)).fetchone()[0]
    con.close()
    return n


def set_clan_rank(uid, rank):
    if rank not in CLAN_RANKS:
        return False
    con = connect()
    con.execute("UPDATE clan_members SET rank=? WHERE user_id=?", (rank, uid))
    con.commit()
    con.close()
    return True


def kick_from_clan(uid):
    con = connect()
    con.execute("DELETE FROM clan_members WHERE user_id=?", (uid,))
    con.commit()
    con.close()


def delete_clan(cid):
    con = connect()
    con.execute("DELETE FROM clan_members WHERE clan_id=?", (cid,))
    con.execute("DELETE FROM clan_requests WHERE clan_id=?", (cid,))
    con.execute("DELETE FROM clan_alliances WHERE clan_a=? OR clan_b=?", (cid, cid))
    con.execute("DELETE FROM clans WHERE id=?", (cid,))
    con.commit()
    con.close()


def add_clan_request(cid, uid):
    con = connect()
    try:
        con.execute("INSERT INTO clan_requests(clan_id, user_id, created_at) VALUES(?,?,?)",
                    (cid, uid, time.time()))
        con.commit()
        ok = True
    except sqlite3.IntegrityError:
        ok = False
    con.close()
    return ok


def get_clan_requests(cid):
    con = connect()
    rows = con.execute("""SELECT cr.user_id, cr.created_at, p.name, p.level, p.player_class
                          FROM clan_requests cr
                          LEFT JOIN players p ON p.user_id=cr.user_id
                          WHERE cr.clan_id=? ORDER BY cr.created_at ASC LIMIT 20""",
                       (cid,)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def remove_clan_request(cid, uid):
    con = connect()
    con.execute("DELETE FROM clan_requests WHERE clan_id=? AND user_id=?", (cid, uid))
    con.commit()
    con.close()


def get_top_clans(limit=10):
    con = connect()
    rows = con.execute("""
        SELECT c.id, c.name, c.motto, c.treasury_gold, c.treasury_level,
               (SELECT COUNT(*) FROM clan_members WHERE clan_id=c.id) as members,
               COALESCE((SELECT SUM(p.level) FROM clan_members cm
                         LEFT JOIN players p ON p.user_id=cm.user_id
                         WHERE cm.clan_id=c.id), 0) as total_level
        FROM clans c ORDER BY total_level DESC LIMIT ?""", (limit,)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def count_clans():
    con = connect()
    n = con.execute("SELECT COUNT(*) FROM clans").fetchone()[0]
    con.close()
    return n


def clan_can_withdraw(rank):
    return rank in ("leader", "noble", "family")


def update_clan(cid, **data):
    if not data:
        return
    fields = ", ".join(f"{k}=?" for k in data)
    con = connect()
    con.execute(f"UPDATE clans SET {fields} WHERE id=?", (*data.values(), cid))
    con.commit()
    con.close()


# ═════ GROUPS ═════

def create_group(name, leader_id):
    con = connect()
    cur = con.execute("INSERT INTO groups(name, leader_id, created_at) VALUES(?,?,?)",
                      (name, leader_id, time.time()))
    gid = cur.lastrowid
    con.commit()
    con.close()
    return gid


def get_group(gid):
    con = connect()
    row = con.execute("SELECT * FROM groups WHERE id=?", (gid,)).fetchone()
    con.close()
    return dict(row) if row else None


def get_group_members(gid, limit=5):
    con = connect()
    rows = con.execute("SELECT user_id, name, level, player_class FROM players "
                       "WHERE group_id=? ORDER BY level DESC LIMIT ?", (gid, limit)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def get_group_count(gid):
    con = connect()
    n = con.execute("SELECT COUNT(*) FROM players WHERE group_id=?", (gid,)).fetchone()[0]
    con.close()
    return n


def count_groups():
    con = connect()
    n = con.execute("SELECT COUNT(*) FROM groups").fetchone()[0]
    con.close()
    return n


def set_group(uid, gid):
    update_player(uid, group_id=gid)


def delete_group(gid):
    con = connect()
    con.execute("UPDATE players SET group_id=0 WHERE group_id=?", (gid,))
    con.execute("DELETE FROM groups WHERE id=?", (gid,))
    con.commit()
    con.close()


# ═════ BOSS LOGS ═════

def log_boss_drop(uid, bkey, iname):
    con = connect()
    con.execute("INSERT INTO boss_drops(user_id, boss_key, item_name, dropped_at) VALUES(?,?,?,?)",
                (uid, bkey, iname, time.time()))
    con.commit()
    con.close()


def add_boss_kill(uid, bkey):
    con = connect()
    con.execute("""INSERT INTO boss_kills(user_id, boss_key, kills) VALUES(?, ?, 1)
                   ON CONFLICT(user_id, boss_key) DO UPDATE SET kills = kills + 1""",
                (uid, bkey))
    con.commit()
    con.close()


def get_boss_kills(uid):
    con = connect()
    rows = con.execute("SELECT boss_key, kills FROM boss_kills WHERE user_id=?", (uid,)).fetchall()
    con.close()
    return {r["boss_key"]: r["kills"] for r in rows}


# ═════ ADMIN ═════

def is_owner(uid): return uid in OWNER_IDS
def is_admin(uid): return uid in ADMIN_IDS or uid in OWNER_IDS


def add_admin(uid):
    if uid in OWNER_IDS: return False, "مالکه"
    if uid in ADMIN_IDS: return False, "قبلاً ادمین"
    if len(ADMIN_IDS) >= MAX_ADMINS: return False, f"حداکثر {MAX_ADMINS}"
    ADMIN_IDS.append(uid)
    return True, "اضافه شد"


def remove_admin(uid):
    if uid in ADMIN_IDS:
        ADMIN_IDS.remove(uid)
        return True
    return False


def get_admins(): return list(ADMIN_IDS)


def get_stats():
    con = connect()
    s = {}
    s["players"] = con.execute("SELECT COUNT(*) FROM players WHERE name IS NOT NULL").fetchone()[0]
    s["clans"] = con.execute("SELECT COUNT(*) FROM clans").fetchone()[0]
    s["groups"] = con.execute("SELECT COUNT(*) FROM groups").fetchone()[0]
    s["total_gold"] = con.execute("SELECT COALESCE(SUM(gold),0) FROM players").fetchone()[0]
    s["total_diamond"] = con.execute("SELECT COALESCE(SUM(diamonds),0) FROM players").fetchone()[0]
    s["total_kills"] = con.execute("SELECT COALESCE(SUM(kills),0) FROM players").fetchone()[0]
    s["banned"] = con.execute("SELECT COUNT(*) FROM players WHERE is_banned=1").fetchone()[0]
    con.close()
    return s


def ban_player(uid): update_player(uid, is_banned=1)
def unban_player(uid): update_player(uid, is_banned=0)


init_db()