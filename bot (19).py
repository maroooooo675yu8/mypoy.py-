# ========== الجزء 1: الإعدادات والمكتبات والدوال المساعدة + نظام صلاحيات الرتب ==========

import sys
if sys.version_info >= (3, 13):
    import audioop
else:
    try:
        import audioop_lts as audioop
    except ImportError:
        import audioop

import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput, Select
import json
import os
import random
import asyncio
import math
import re
from datetime import datetime, timedelta
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import aiohttp
from dotenv import load_dotenv

# ===== تحميل متغيرات البيئة =====
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN not found! Check your .env file")

# ===== قواعد البيانات =====
DATA_FILE = 'user_data.json'
CONFIG_FILE = 'bot_config.json'
GUILD_CONFIG_FILE = 'guild_config.json'
WARNINGS_FILE = 'warnings_data.json'
ROLES_CONFIG_FILE = 'roles_config.json'
VC_CONFIG_FILE = 'vc_config.json'
BANK_DATA_FILE = 'bank_data.json'
BANK_LOGS_FILE = 'bank_logs_config.json'
ROLE_LOGS_FILE = 'role_logs_config.json'
COMP_DATA_FILE = 'competition_data.json'
INVITE_DATA_FILE = 'invite_data.json'
MOD_APPS_IMAGE = 'mod_apply.jpg'
MOD_LOGS_FILE = 'mod_logs_config.json'
TICKET_IMAGE_CONFIG_FILE = 'ticket_image_config.json'

# ===== إعدادات الإنفايت =====
INVITE_REWARD = 350  # كريدت مكافأة الإنفايت
INVITE_MIN_STAY_MINUTES = 10  # أقل وقت لازم العضو الجديد يقعد عشان المكافأة تتحسب

# ===== إعدادات الـ XP المتدرجة =====
def get_xp_for_level(level):
    if level == 1:
        return 0
    total = 0
    for i in range(1, level):
        total += i * 100
    return total

def get_level_from_xp(xp):
    level = 1
    while True:
        required = get_xp_for_level(level + 1)
        if xp < required:
            return level
        level += 1

def get_xp_needed_for_next_level(level):
    return level * 100

def get_current_level_xp(xp, level):
    level_start = get_xp_for_level(level)
    return xp - level_start

# إعدادات الشوب (الأسعار الأساسية - البوسترز ياخدوا خصم 25%)
SHOP_ITEMS = {
    "double_xp": {
        "1h": {"price": 270, "duration": 1, "booster_price": 203},
        "3h": {"price": 630, "duration": 3, "booster_price": 473},
        "6h": {"price": 990, "duration": 6, "booster_price": 743},
        "12h": {"price": 1440, "duration": 12, "booster_price": 1080},
        "24h": {"price": 1980, "duration": 24, "booster_price": 1485},
        "1w": {"price": 9000, "duration": 168, "booster_price": 6750}
    },
    "rank_color": {"price": 1000, "booster_price": 750, "description": "لون النصوط والصناديق"},
    "name_colors": {
        "Red": {"price": 2000, "level_required": 30, "role_name": "Red"},
        "Green": {"price": 2000, "level_required": 30, "role_name": "Green"},
        "White": {"price": 2000, "level_required": 30, "role_name": "White"},
        "Purple": {"price": 2000, "level_required": 30, "role_name": "Purple"},
        "Pink": {"price": 2000, "level_required": 30, "role_name": "Pink"},
        "Blue": {"price": 2000, "level_required": 30, "role_name": "Blue"},
        "Cyan": {"price": 2000, "level_required": 30, "role_name": "Cyan"},
        "Ecto": {"price": 2000, "level_required": 30, "role_name": "Ecto"},
        "VIP Purple": {"price": 4500, "level_required": 30, "role_name": "VIP Purple"},
        "VIP Pink": {"price": 4500, "level_required": 30, "role_name": "VIP Pink"},
        "VIP Blue": {"price": 4500, "level_required": 30, "role_name": "VIP Blue"},
        "VIP Cyan": {"price": 4500, "level_required": 30, "role_name": "VIP Cyan"},
        "Black": {"price": 7000, "level_required": 30, "role_name": "Black"}
    },
    "remove_color": {"price": 250, "description": "إزالة لون الاسم"},
    "bg_color": {"price": 1500, "booster_price": 1125, "description": "لون خلفية كارت الرانك"}
}

DEFAULT_CONFIG = {
    "xp_cooldown": 30,
    "xp_min": 10,
    "xp_max": 15,
    "level_up_credits": 50
}

# ===== إعدادات الـ VC XP =====
DEFAULT_VC_CONFIG = {
    "vc_xp_per_minute": 10,      # كل دقيقة كام XP
    "vc_xp_min": 5,               # أقل XP (لما الدقيقة متكتملش)
    "vc_xp_max": 15,              # أقصى XP
    "vc_active_only": False,      # هل لازم يكون active (مش mute/deafen)
    "vc_boost_multiplier": 1.5    # مضاعف البوستر
}

def load_vc_config():
    if os.path.exists(VC_CONFIG_FILE):
        with open(VC_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_vc_config(cfg):
    with open(VC_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)

def get_guild_vc_config(guild_id):
    cfg = load_vc_config()
    return cfg.get(str(guild_id), DEFAULT_VC_CONFIG.copy())

def set_guild_vc_config(guild_id, settings):
    cfg = load_vc_config()
    cfg[str(guild_id)] = settings
    save_vc_config(cfg)

# ===== نظام لوجات البنك والرتب =====

def load_bank_logs_config():
    if os.path.exists(BANK_LOGS_FILE):
        with open(BANK_LOGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_bank_logs_config(cfg):
    with open(BANK_LOGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)

def load_role_logs_config():
    if os.path.exists(ROLE_LOGS_FILE):
        with open(ROLE_LOGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_role_logs_config(cfg):
    with open(ROLE_LOGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)

def get_bank_logs_channel(guild_id):
    cfg = load_bank_logs_config()
    return cfg.get(str(guild_id), {}).get("channel_id")

def set_bank_logs_channel(guild_id, channel_id):
    cfg = load_bank_logs_config()
    cfg[str(guild_id)] = {"channel_id": channel_id}
    save_bank_logs_config(cfg)

def get_role_logs_channel(guild_id):
    cfg = load_role_logs_config()
    return cfg.get(str(guild_id), {}).get("channel_id")

def set_role_logs_channel(guild_id, channel_id):
    cfg = load_role_logs_config()
    cfg[str(guild_id)] = {"channel_id": channel_id}
    save_role_logs_config(cfg)

async def send_bank_log(bot_instance, guild_id, embed):
    """إرسال لوج بنكي للشانل المحدد"""
    channel_id = get_bank_logs_channel(guild_id)
    if not channel_id:
        return
    channel = bot_instance.get_channel(int(channel_id))
    if not channel:
        return
    try:
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Error sending bank log: {e}")

async def send_role_log(bot_instance, guild_id, embed):
    """إرسال لوج رتب للشانل المحدد"""
    channel_id = get_role_logs_channel(guild_id)
    if not channel_id:
        return
    channel = bot_instance.get_channel(int(channel_id))
    if not channel:
        return
    try:
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Error sending role log: {e}")

async def log_bank_investment(bot_instance, member, company_name, amount, won, profit=0):
    """تسجيل عملية استثمار"""
    if won:
        color = discord.Color.green()
        status = "✅ ناجح"
        result_text = f"ربح **{profit:,}** كريدت"
    else:
        color = discord.Color.red()
        status = "❌ خاسر"
        result_text = f"خسر **{amount:,}** كريدت"

    embed = discord.Embed(
        title="📈 عملية استثمار",
        color=color,
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 المستثمر", value=f"{member.mention}\n`{member}`", inline=True)
    embed.add_field(name="🏢 الشركة", value=f"`{company_name}`", inline=True)
    embed.add_field(name="💰 المبلغ", value=f"`{amount:,}` كريدت", inline=True)
    embed.add_field(name="📊 النتيجة", value=f"{status}\n{result_text}", inline=True)
    embed.add_field(name="🆔 الآيدي", value=f"`{member.id}`", inline=True)
    embed.add_field(name="📅 التاريخ", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=True)

    await send_bank_log(bot_instance, member.guild.id, embed)

async def log_bank_transfer(bot_instance, guild_id, sender, receiver, amount):
    """تسجيل عملية تحويل كريدت"""
    embed = discord.Embed(
        title="💱 عملية تحويل",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    embed.add_field(name="📤 المرسل", value=f"{sender.mention}\n`{sender}`", inline=True)
    embed.add_field(name="📥 المستلم", value=f"{receiver.mention}\n`{receiver}`", inline=True)
    embed.add_field(name="💰 المبلغ", value=f"`{amount:,}` كريدت", inline=True)
    embed.add_field(name="📅 التاريخ", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=True)

    await send_bank_log(bot_instance, guild_id, embed)

async def log_bank_loan(bot_instance, member, amount, action="سحب"):
    """تسجيل عملية قرض"""
    if action == "سحب":
        color = discord.Color.gold()
        title = "💰 سحب قرض"
    else:
        color = discord.Color.green()
        title = "💳 سداد قرض"

    embed = discord.Embed(
        title=title,
        color=color,
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 العضو", value=f"{member.mention}\n`{member}`", inline=True)
    embed.add_field(name="💰 المبلغ", value=f"`{amount:,}` كريدت", inline=True)
    embed.add_field(name="📋 العملية", value=f"`{action}`", inline=True)
    embed.add_field(name="🆔 الآيدي", value=f"`{member.id}`", inline=True)
    embed.add_field(name="📅 التاريخ", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=True)

    await send_bank_log(bot_instance, member.guild.id, embed)

async def log_role_change(bot_instance, guild_id, member, role, action, moderator=None):
    """تسجيل تغيير رتبة"""
    if action == "إضافة":
        color = discord.Color.green()
        title = "🎭 إضافة رتبة"
    else:
        color = discord.Color.red()
        title = "🎭 إزالة رتبة"

    embed = discord.Embed(
        title=title,
        color=color,
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 العضو", value=f"{member.mention}\n`{member}`", inline=True)
    embed.add_field(name="🎭 الرتبة", value=f"{role.mention}\n`{role.name}`", inline=True)
    embed.add_field(name="📋 العملية", value=f"`{action}`", inline=True)
    if moderator:
        embed.add_field(name="👮‍♂️ المُنفِّذ", value=f"{moderator.mention}\n`{moderator}`", inline=True)
    embed.add_field(name="🆔 الآيدي", value=f"`{member.id}`", inline=True)
    embed.add_field(name="📅 التاريخ", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=True)

    await send_role_log(bot_instance, guild_id, embed)

# ===== نظام الكولداون العام =====
command_cooldowns = {}

def check_global_cooldown(user_id):
    now = datetime.now().timestamp()
    if user_id in command_cooldowns:
        last_used = command_cooldowns[user_id]
        if now - last_used < 3:
            return False, 3 - (now - last_used)
    command_cooldowns[user_id] = now
    return True, 0

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)

def load_guild_config():
    if os.path.exists(GUILD_CONFIG_FILE):
        with open(GUILD_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_guild_config(cfg):
    with open(GUILD_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)

def load_warnings():
    if os.path.exists(WARNINGS_FILE):
        with open(WARNINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_warnings(data):
    with open(WARNINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# ===== نظام صلاحيات الرتب =====
def load_roles_config():
    if os.path.exists(ROLES_CONFIG_FILE):
        with open(ROLES_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_roles_config(cfg):
    with open(ROLES_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)

def get_role_permissions(guild_id, role_id):
    cfg = load_roles_config()
    guild_roles = cfg.get(str(guild_id), {})
    return guild_roles.get(str(role_id), {})

# ===== نظام صورة التيكت الديناميكية =====
def load_ticket_image_config():
    if os.path.exists(TICKET_IMAGE_CONFIG_FILE):
        with open(TICKET_IMAGE_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_ticket_image_config(cfg):
    with open(TICKET_IMAGE_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)

def get_ticket_image_url(guild_id):
    cfg = load_ticket_image_config()
    return cfg.get(str(guild_id), {}).get("image_url")

def set_ticket_image_url(guild_id, image_url):
    cfg = load_ticket_image_config()
    if str(guild_id) not in cfg:
        cfg[str(guild_id)] = {}
    cfg[str(guild_id)]["image_url"] = image_url
    save_ticket_image_config(cfg)

def get_ticket_panel_info(guild_id):
    """Get the stored ticket panel message/channel IDs"""
    cfg = load_ticket_image_config()
    guild_cfg = cfg.get(str(guild_id), {})
    return guild_cfg.get("panel_channel_id"), guild_cfg.get("panel_message_id")

def set_ticket_panel_info(guild_id, channel_id, message_id):
    """Save ticket panel message/channel IDs for auto-updating"""
    cfg = load_ticket_image_config()
    if str(guild_id) not in cfg:
        cfg[str(guild_id)] = {}
    cfg[str(guild_id)]["panel_channel_id"] = channel_id
    cfg[str(guild_id)]["panel_message_id"] = message_id
    save_ticket_image_config(cfg)

def get_ticket_roles(guild):
    """الحصول على كل الرتب اللي عندها صلاحية ticket"""
    cfg = load_roles_config()
    guild_roles = cfg.get(str(guild.id), {})
    ticket_roles = []
    for role_id, perms in guild_roles.items():
        if perms.get("ticket", False):
            role = guild.get_role(int(role_id))
            if role:
                ticket_roles.append(role)
    return ticket_roles

def set_role_permissions(guild_id, role_id, permissions):
    cfg = load_roles_config()
    if str(guild_id) not in cfg:
        cfg[str(guild_id)] = {}
    cfg[str(guild_id)][str(role_id)] = permissions
    save_roles_config(cfg)

def has_role_permission(member, permission):
    if member.guild_permissions.administrator:
        return True
    
    for role in member.roles:
        perms = get_role_permissions(member.guild.id, role.id)
        if perms.get(permission, False):
            return True
    return False

def can_use_warn(member): return has_role_permission(member, "warn")
def can_use_timeout(member): return has_role_permission(member, "timeout")
def can_use_untimeout(member): return has_role_permission(member, "untimeout")
def can_use_warnings(member): return has_role_permission(member, "warnings")
def can_use_mute(member): return has_role_permission(member, "mute")
def can_use_unmute(member): return has_role_permission(member, "unmute")
def can_use_kick(member): return has_role_permission(member, "kick")
def can_use_ban(member): return has_role_permission(member, "ban")
def can_use_unban(member): return has_role_permission(member, "unban")
def can_use_clear(member): return has_role_permission(member, "clear")
def can_use_role(member): return has_role_permission(member, "role")
def can_use_prison(member): return has_role_permission(member, "prison")
def can_use_unprison(member): return has_role_permission(member, "unprison")
def can_use_comp_win(member): return has_role_permission(member, "comp_win")
def can_use_comp_leaderboard(member): return has_role_permission(member, "comp_leaderboard")
def can_use_ticket(member): return has_role_permission(member, "ticket")
def can_use_talk(member): return has_role_permission(member, "talk")
def can_use_lead_reset(member): return has_role_permission(member, "lead_reset")
def can_use_lock(member): return has_role_permission(member, "lock")
def can_use_unlock(member): return has_role_permission(member, "unlock")

# ===== نظام الإنفايت =====
def load_invite_data():
    if os.path.exists(INVITE_DATA_FILE):
        with open(INVITE_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_invite_data(data):
    with open(INVITE_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

invite_data = load_invite_data()

# تخزين الإنفايتات قبل الجوين عشان نقارن
guild_invites_cache = {}

# تخزين وقت دخول العضو عشان نتحقق من الأنتي-أبيوز
member_join_times = {}

# تخزين الأعضاء اللي لسه ما أخدوش مكافأة (pending)
pending_invite_rewards = {}

def get_invite_user(guild_id, user_id):
    gid = str(guild_id)
    uid = str(user_id)
    if gid not in invite_data:
        invite_data[gid] = {}
    if uid not in invite_data[gid]:
        invite_data[gid][uid] = {
            "invited_count": 0,
            "total_earned": 0,
            "invited_members": []
        }
        save_invite_data(invite_data)
    return invite_data[gid][uid]

def is_member_already_invited(guild_id, member_id):
    """تحقق إذا العضو ده اتدعى قبل كده (عشان نفس الشخص ميتحسبش أكتر من مرة)"""
    gid = str(guild_id)
    mid = str(member_id)
    guild_invites = invite_data.get(gid, {})
    for uid, data in guild_invites.items():
        if not isinstance(data, dict):
            continue
        for inv in data.get("invited_members", []):
            if inv.get("user_id") == mid:
                return True
    return False

def is_level_enabled(guild_id):
    cfg = load_guild_config()
    return cfg.get(str(guild_id), {}).get("level_enabled", False)

def set_level_enabled(guild_id, enabled):
    cfg = load_guild_config()
    if str(guild_id) not in cfg:
        cfg[str(guild_id)] = {}
    cfg[str(guild_id)]["level_enabled"] = enabled
    save_guild_config(cfg)

# ===== دوال اللوجز =====
def get_log_channel(guild_id, log_type):
    cfg = load_guild_config()
    return cfg.get(str(guild_id), {}).get("logs", {}).get(log_type)

def set_log_channel(guild_id, log_type, channel_id):
    cfg = load_guild_config()
    if str(guild_id) not in cfg:
        cfg[str(guild_id)] = {}
    if "logs" not in cfg[str(guild_id)]:
        cfg[str(guild_id)]["logs"] = {}
    cfg[str(guild_id)]["logs"][log_type] = channel_id
    save_guild_config(cfg)

def is_anti_cheat_enabled(guild_id):
    cfg = load_guild_config()
    return cfg.get(str(guild_id), {}).get("anti_cheat_enabled", False)

def set_anti_cheat_enabled(guild_id, enabled):
    cfg = load_guild_config()
    if str(guild_id) not in cfg:
        cfg[str(guild_id)] = {}
    cfg[str(guild_id)]["anti_cheat_enabled"] = enabled
    save_guild_config(cfg)

# ===== دالة التحقق من البوستر =====
def is_server_booster(member):
    return member.premium_since is not None

# ===== دالة الحصول على السعر =====
def get_item_price(item_key, sub_key=None, member=None):
    is_booster = False
    if member and isinstance(member, discord.Member):
        is_booster = is_server_booster(member)
    
    if sub_key and item_key in SHOP_ITEMS and sub_key in SHOP_ITEMS[item_key]:
        item = SHOP_ITEMS[item_key][sub_key]
        if is_booster and "booster_price" in item:
            return item["booster_price"], True
        return item["price"], False
    
    elif item_key in SHOP_ITEMS and sub_key is None:
        item = SHOP_ITEMS[item_key]
        if is_booster and "booster_price" in item:
            return item["booster_price"], True
        return item["price"], False
    
    return 0, False

user_data = load_data()
bot_config = load_config()
warnings_data = load_warnings()

# ===== تحديث ألوان الأعضاء القدامى للرمادي الفاتح =====
def update_old_colors():
    updated = 0
    old_colors = ["#1a1a1a", "#2C2F33", "#1a1a1a", "#2c2f33"]
    for gid, guild_users in user_data.items():
        if not isinstance(guild_users, dict):
            continue
        for user_id, data in guild_users.items():
            if not isinstance(data, dict):
                continue
            current_color = data.get("card_bg_color", "")
            if current_color in old_colors or current_color.lower() in [c.lower() for c in old_colors]:
                data["card_bg_color"] = "#36393F"
                updated += 1
    if updated > 0:
        save_data(user_data)
        print(f"✅ تم تحديث ألوان {updated} عضو للرمادي الفاتح (#36393F)")

# تنفيذ التحديث
update_old_colors()

def get_user_data(guild_id, user_id):
    gid = str(guild_id)
    uid = str(user_id)
    if gid not in user_data:
        user_data[gid] = {}
    if uid not in user_data[gid]:
        user_data[gid][uid] = {
            "xp": 0,
            "level": 1,
            "credits": 100,
            "rank_color": "#DC143C",
            "card_bg_color": "#36393F",
            "double_xp_until": None,
            "warnings": 0,
            "muted_until": None,
            "dm_muted": False,
            "last_xp_time": 0,
            "double_xp_active": False,
            "voice_join_time": None,
            "name_color": None
        }
        save_data(user_data)
    return user_data[gid][uid]

def add_warning(guild_id, user_id, reason, moderator):
    gid = str(guild_id)
    uid = str(user_id)
    if gid not in warnings_data:
        warnings_data[gid] = {}
    if uid not in warnings_data[gid]:
        warnings_data[gid][uid] = []
    
    warning = {
        "guild_id": gid,
        "reason": reason,
        "moderator": moderator,
        "date": datetime.now().isoformat(),
        "number": len(warnings_data[gid][uid]) + 1
    }
    warnings_data[gid][uid].append(warning)
    save_warnings(warnings_data)
    return warning["number"]

def get_user_warnings(guild_id, user_id):
    gid = str(guild_id)
    uid = str(user_id)
    return warnings_data.get(gid, {}).get(uid, [])

def clear_warnings(guild_id, user_id):
    gid = str(guild_id)
    uid = str(user_id)
    if gid not in warnings_data:
        warnings_data[gid] = {}
    warnings_data[gid][uid] = []
    save_warnings(warnings_data)

def has_double_xp(guild_id, user_id):
    user = get_user_data(guild_id, user_id)
    if user.get("double_xp_until"):
        try:
            expiry = datetime.fromisoformat(user["double_xp_until"])
            if datetime.now() < expiry:
                user["double_xp_active"] = True
                save_data(user_data)
                return True
            else:
                user["double_xp_until"] = None
                user["double_xp_active"] = False
                save_data(user_data)
        except:
            user["double_xp_until"] = None
            save_data(user_data)
    return False

def get_double_xp_time_remaining(guild_id, user_id):
    user = get_user_data(guild_id, user_id)
    if user.get("double_xp_until"):
        try:
            expiry = datetime.fromisoformat(user["double_xp_until"])
            remaining = expiry - datetime.now()
            if remaining.total_seconds() > 0:
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                return f"{hours}h {minutes}m"
        except:
            pass
    return None

def is_muted(guild_id, user_id):
    user = get_user_data(guild_id, user_id)
    if user.get("muted_until"):
        try:
            if datetime.now() < datetime.fromisoformat(user["muted_until"]):
                return True
            user["muted_until"] = None
            save_data(user_data)
        except:
            user["muted_until"] = None
            save_data(user_data)
    return False

def get_rank(guild_id, user_id, guild):
    all_users = []
    guild_data = user_data.get(str(guild_id), {})
    for uid, data in guild_data.items():
        if not isinstance(data, dict):
            continue
        try:
            member = guild.get_member(int(uid))
            if member and not member.bot:
                all_users.append((uid, data.get("xp", 0)))
        except:
            pass
    
    all_users.sort(key=lambda x: x[1], reverse=True)
    
    for i, (uid, xp) in enumerate(all_users, 1):
        if uid == str(user_id):
            return i, len(all_users)
    
    return len(all_users) + 1, len(all_users)

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    try:
        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return (r, g, b)
    except:
        pass
    return (26, 26, 26)

def get_level_rewards(level):
    base_credits = 50
    milestone_levels = [5, 10, 15, 20, 25, 30, 35, 40, 50, 60, 70, 80, 90, 100]
    
    if level in milestone_levels:
        bonus = 100
        features = []
        if level >= 5:
            features.append("• Send GIFs and pictures")
        if level >= 10:
            features.append("• Send voice messages")
        if level >= 15:
            features.append("• A Role")
        if level >= 20:
            features.append("• Create threads")
        if level >= 25:
            features.append("• Change Nicknames")
        if level >= 30:
            features.append("• Create polls")
        if level >= 35:
            features.append("• Priority speaker")
        if level >= 40:
            features.append("• A Role")
        if level >= 50:
            features.append("• Soundboard perm")
        if level >= 60:
            features.append("• 1k Lake credits (that you can use in shop)")
        if level >= 70:
            features.append("• You will get a special treatment <:special:1486339688422834206>")
        if level >= 80:
            features.append("• A Role")
        if level >= 90:
            features.append("• مش عارف يسطا انت معندكش حياة الصراحة")
        if level >= 100:
            features.append("• Custom role with custom color, icon, and name 👑")
        return base_credits, bonus, features, True
    
    return base_credits, 0, [], False

# ========== دوال مساعدة للألوان ==========

async def remove_old_name_color(member):
    """إزالة أي رتبة لون قديمة من العضو"""
    color_roles = [
        "Red", "Green", "White", "Purple", "Pink", "Blue", "Cyan", "Ecto",
        "VIP Purple", "VIP Pink", "VIP Blue", "VIP Cyan", "Black"
    ]
    removed = []
    for role_name in color_roles:
        role = discord.utils.get(member.guild.roles, name=role_name)
        if role and role in member.roles:
            try:
                await member.remove_roles(role)
                removed.append(role_name)
            except:
                pass
    return removed

async def add_name_color(member, color_name):
    """إضافة رتبة لون للعضو (بعد إزالة القديم)"""
    await remove_old_name_color(member)
    role = discord.utils.get(member.guild.roles, name=color_name)
    if role:
        try:
            await member.add_roles(role)
            return True
        except:
            return False
    return False

# ========== الجزء 2: نظام اللوجز وإنشاء الإمبدات ==========

async def create_log_embed(member, action, reason=None, duration=None, moderator=None, color=None):
    if color is None:
        color = discord.Color.blue()
    
    embed = discord.Embed(
        title=f"📝 {action}",
        color=color,
        timestamp=datetime.now()
    )
    
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 العضو", value=f"{member.mention}\n`{member}`", inline=True)
    
    if moderator:
        embed.add_field(name="👮‍♂️ المُنفِّذ", value=f"{moderator.mention}\n`{moderator}`", inline=True)
    
    if duration:
        embed.add_field(name="⏰ المدة", value=f"`{duration}`", inline=True)
    
    if reason:
        embed.add_field(name="📝 السبب", value=reason, inline=False)
    
    embed.add_field(name="🆔 الآيدي", value=f"`{member.id}`", inline=True)
    embed.add_field(name="📅 التاريخ", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=True)
    
    return embed

async def send_log(bot, guild_id, log_type, member, action, reason=None, duration=None, moderator=None, color=None):
    channel_id = get_log_channel(guild_id, log_type)
    if not channel_id:
        return
    
    channel = bot.get_channel(int(channel_id))
    if not channel:
        return
    
    embed = await create_log_embed(member, action, reason, duration, moderator, color)
    await channel.send(embed=embed)

async def log_shop_purchase(bot, member, item_name, price, duration=None, is_booster=False):
    guild_id = member.guild.id
    channel_id = get_log_channel(guild_id, "shop")
    if not channel_id:
        return
    
    channel = bot.get_channel(int(channel_id))
    if not channel:
        return
    
    embed = discord.Embed(
        title="🛒 عملية شراء جديدة",
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 المشتري", value=f"{member.mention}\n`{member}`", inline=True)
    embed.add_field(name="🛍️ المنتج", value=f"`{item_name}`", inline=True)
    
    if is_booster:
        embed.add_field(name="💰 السعر", value=f"`{price}` كريدت (خصم بوستر 25% 🚀)", inline=True)
    else:
        embed.add_field(name="💰 السعر", value=f"`{price}` كريدت", inline=True)
    
    if duration:
        embed.add_field(name="⏰ المدة", value=f"`{duration}`", inline=True)
    
    embed.add_field(name="🆔 الآيدي", value=f"`{member.id}`", inline=True)
    embed.add_field(name="📅 التاريخ", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=True)
    
    await channel.send(embed=embed)

async def log_ban(bot, member, reason=None, moderator=None):
    await send_log(bot, member.guild.id, "ban", member, "حظر عضو", reason, None, moderator, discord.Color.dark_red())

async def log_kick(bot, member, reason=None, moderator=None):
    await send_log(bot, member.guild.id, "kick", member, "طرد عضو", reason, None, moderator, discord.Color.orange())

async def log_timeout(bot, member, duration, reason=None, moderator=None):
    await send_log(bot, member.guild.id, "timeout_mute", member, "تايم أوت", reason, duration, moderator, discord.Color.orange())

async def log_mute(bot, member, duration, reason=None, moderator=None):
    await send_log(bot, member.guild.id, "timeout_mute", member, "ميوت", reason, duration, moderator, discord.Color.red())

async def log_join(bot, member):
    guild_id = member.guild.id
    channel_id = get_log_channel(guild_id, "join_leave")
    if not channel_id:
        return
    
    channel = bot.get_channel(int(channel_id))
    if not channel:
        return
    
    embed = discord.Embed(
        title="✅ دخول عضو جديد",
        description=f"{member.mention} انضم للسيرفر!",
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 الاسم", value=f"`{member}`", inline=True)
    embed.add_field(name="🆔 الآيدي", value=f"`{member.id}`", inline=True)
    embed.add_field(name="📅 تاريخ الإنشاء", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
    embed.add_field(name="👥 عدد الأعضاء", value=f"`{len(member.guild.members)}`", inline=True)
    
    await channel.send(embed=embed)

async def log_leave(bot, member):
    guild_id = member.guild.id
    channel_id = get_log_channel(guild_id, "join_leave")
    if not channel_id:
        return
    
    channel = bot.get_channel(int(channel_id))
    if not channel:
        return
    
    embed = discord.Embed(
        title="❌ خروج عضو",
        description=f"{member.mention} غادر السيرفر!",
        color=discord.Color.red(),
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 الاسم", value=f"`{member}`", inline=True)
    embed.add_field(name="🆔 الآيدي", value=f"`{member.id}`", inline=True)
    embed.add_field(name="📅 تاريخ الانضمام", value=f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "غير معروف", inline=True)
    embed.add_field(name="👥 عدد الأعضاء", value=f"`{len(member.guild.members)}`", inline=True)
    
    await channel.send(embed=embed)

async def log_message_delete(bot, message):
    if message.author.bot:
        return
    
    guild_id = message.guild.id
    channel_id = get_log_channel(guild_id, "msg")
    if not channel_id:
        return
    
    channel = bot.get_channel(int(channel_id))
    if not channel:
        return
    
    embed = discord.Embed(
        title="🗑️ رسالة محذوفة",
        color=discord.Color.orange(),
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=message.author.display_avatar.url)
    embed.add_field(name="👤 المرسل", value=f"{message.author.mention}\n`{message.author}`", inline=True)
    embed.add_field(name="📍 القناة", value=f"{message.channel.mention}", inline=True)
    
    if message.content:
        embed.add_field(name="📝 المحتوى", value=message.content[:1024] or "لا يوجد محتوى", inline=False)
    
    if message.attachments:
        files = "\n".join([att.url for att in message.attachments[:5]])
        embed.add_field(name="📎 المرفقات", value=files, inline=False)
    
    await channel.send(embed=embed)

async def log_message_edit(bot, before, after):
    if before.author.bot or before.content == after.content:
        return
    
    guild_id = before.guild.id
    channel_id = get_log_channel(guild_id, "msg")
    if not channel_id:
        return
    
    channel = bot.get_channel(int(channel_id))
    if not channel:
        return
    
    embed = discord.Embed(
        title="✏️ رسالة معدلة",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=before.author.display_avatar.url)
    embed.add_field(name="👤 المرسل", value=f"{before.author.mention}\n`{before.author}`", inline=True)
    embed.add_field(name="📍 القناة", value=f"{before.channel.mention}\n[اذهب للرسالة]({after.jump_url})", inline=True)
    embed.add_field(name="📝 قبل", value=before.content[:1024] or "لا يوجد محتوى", inline=False)
    embed.add_field(name="📝 بعد", value=after.content[:1024] or "لا يوجد محتوى", inline=False)
    
    await channel.send(embed=embed)

# ========== الجزء 3: نظام مكافحة السبام والشتائم ==========

BAD_WORDS = [
    "كسمك", "خول", "الخول", "شرموط", "شرموطه", 
    "علء", "علق", "ديوث", "وسخ", "وسخه",
    "هنيكك", "انيكك", "الاحبه", "عرص", "العرص", "كسمينك",
    "سكس", "هايج", "قستك", "كوس", "كوسمك", "طيز", "زب", "نيك",
    "متناك", "متناكة", "قحبة", "قحبه", "شرمطة", "منيك", "منيوك"
]

def contains_bad_words(text):
    text_lower = text.lower()
    words_in_text = re.findall(r'\b\w+\b', text_lower)
    
    for bad_word in BAD_WORDS:
        if bad_word in words_in_text:
            return True
    
    return False

class AntiCheatSystem:
    def __init__(self):
        self.spam_tracker = {}
    
    def check_spam(self, user_id):
        now = datetime.now().timestamp()
        
        if user_id not in self.spam_tracker:
            self.spam_tracker[user_id] = []
        
        self.spam_tracker[user_id].append(now)
        self.spam_tracker[user_id] = [t for t in self.spam_tracker[user_id] if now - t < 6]
        
        return len(self.spam_tracker[user_id]) >= 4
    
    async def handle_bad_words(self, message, bot):
        if not contains_bad_words(message.content):
            return False
        
        try:
            await message.delete()
            
            bot_msg = await message.channel.send(
                f"🛑 {message.author.mention} - ممنوع استخدام كلمات غير لائقة! (تم حذف الرسالة فقط)"
            )
            
            await asyncio.sleep(5)
            await bot_msg.delete()
            
            return True
            
        except Exception as e:
            print(f"Error in handle_bad_words: {e}")
            return False
    
    async def handle_spam(self, message, bot):
        if not self.check_spam(message.author.id):
            return False
        
        try:
            await message.delete()
            await message.author.timeout(timedelta(minutes=3), reason="إرسال رسائل بشكل متكرر (سبام)")
            
            bot_msg = await message.channel.send(
                f"كفايا سبام يا حبيبي هو فرح (تم اعطاء تايم اوت لـ {message.author.mention}) لمده 3 دقائق 🛑"
            )
            
            await asyncio.sleep(5)
            await bot_msg.delete()
            
            await log_timeout(bot, message.author, "3 دقائق", "إرسال رسائل بشكل متكرر (سبام)", bot.user)
            return True
            
        except Exception as e:
            print(f"Error in handle_spam: {e}")
            return False

anti_cheat = AntiCheatSystem()

# ========== الجزء 4: إنشاء صورة الرانك + إدارة الرتب (المعدلة النهائية) ==========

async def create_welcome_image(member):
    """
    Creates a welcome card with blurred avatar background,
    circular avatar in center, username, and 'Welcome to the Server' text.
    Returns a BytesIO image buffer.
    """
    width, height = 800, 400
    white = (255, 255, 255)
    shadow_color = (0, 0, 0)

    # Load fonts
    try:
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "arial.ttf",
        ]
        name_font = None
        for font_path in font_paths:
            if os.path.exists(font_path):
                name_font = ImageFont.truetype(font_path, 32)
                welcome_font = ImageFont.truetype(font_path, 24)
                break
        if name_font is None:
            raise Exception("No font found")
    except:
        name_font = ImageFont.load_default()
        welcome_font = ImageFont.load_default()

    # Fetch avatar
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(str(member.display_avatar.url)) as resp:
                avatar_data = await resp.read()
                avatar_original = Image.open(BytesIO(avatar_data)).convert('RGBA')
    except:
        avatar_original = Image.new('RGBA', (256, 256), (88, 101, 242, 255))

    # === Background: Blurred avatar ===
    bg = avatar_original.convert('RGB').resize((width, height))
    bg = bg.filter(ImageFilter.GaussianBlur(radius=25))
    # Darken the background
    dark_overlay = Image.new('RGB', (width, height), (0, 0, 0))
    bg = Image.blend(bg, dark_overlay, 0.4)

    img = bg.copy()
    draw = ImageDraw.Draw(img)

    # === Circular avatar in center ===
    avatar_size = 150
    av_x = (width - avatar_size) // 2
    av_y = 50

    # White ring around avatar
    ring_pad = 5
    ring_mask = Image.new('L', (width, height), 0)
    ring_draw = ImageDraw.Draw(ring_mask)
    ring_draw.ellipse(
        [av_x - ring_pad, av_y - ring_pad,
         av_x + avatar_size + ring_pad, av_y + avatar_size + ring_pad],
        fill=255
    )
    ring_layer = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    ring_layer_draw = ImageDraw.Draw(ring_layer)
    ring_layer_draw.ellipse(
        [av_x - ring_pad, av_y - ring_pad,
         av_x + avatar_size + ring_pad, av_y + avatar_size + ring_pad],
        fill=(255, 255, 255, 200)
    )
    img.paste(Image.new('RGB', (width, height), (255, 255, 255)),
              (0, 0), ring_mask)

    # Paste circular avatar
    avatar_resized = avatar_original.resize((avatar_size, avatar_size))
    mask = Image.new('L', (avatar_size, avatar_size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse([0, 0, avatar_size, avatar_size], fill=255)
    img.paste(avatar_resized, (av_x, av_y), mask)

    # === Username with dark background bar ===
    username = member.display_name
    if len(username) > 22:
        username = username[:19] + "..."

    name_bbox = draw.textbbox((0, 0), username, font=name_font)
    name_w = name_bbox[2] - name_bbox[0]
    name_h = name_bbox[3] - name_bbox[1]
    name_y = av_y + avatar_size + 30

    # Dark semi-transparent bar behind username
    bar_padding_x = 40
    bar_padding_y = 10
    bar_x1 = (width - name_w) // 2 - bar_padding_x
    bar_x2 = (width + name_w) // 2 + bar_padding_x
    bar_y1 = name_y - bar_padding_y
    bar_y2 = name_y + name_h + bar_padding_y

    bar_overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    bar_draw = ImageDraw.Draw(bar_overlay)
    bar_draw.rounded_rectangle([bar_x1, bar_y1, bar_x2, bar_y2], radius=8, fill=(0, 0, 0, 160))
    img = Image.alpha_composite(img.convert('RGBA'), bar_overlay).convert('RGB')
    draw = ImageDraw.Draw(img)

    # Draw username text (centered)
    draw.text(((width - name_w) // 2, name_y), username, fill=white, font=name_font)

    # === "Welcome to the Server" text ===
    welcome_text = "Welcome to the Server"
    wt_bbox = draw.textbbox((0, 0), welcome_text, font=welcome_font)
    wt_w = wt_bbox[2] - wt_bbox[0]
    wt_h = wt_bbox[3] - wt_bbox[1]
    wt_y = bar_y2 + 15

    # Dark bar behind welcome text
    wbar_x1 = (width - wt_w) // 2 - 30
    wbar_x2 = (width + wt_w) // 2 + 30
    wbar_y1 = wt_y - 8
    wbar_y2 = wt_y + wt_h + 8

    wbar_overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    wbar_draw = ImageDraw.Draw(wbar_overlay)
    wbar_draw.rounded_rectangle([wbar_x1, wbar_y1, wbar_x2, wbar_y2], radius=8, fill=(0, 0, 0, 160))
    img = Image.alpha_composite(img.convert('RGBA'), wbar_overlay).convert('RGB')
    draw = ImageDraw.Draw(img)

    draw.text(((width - wt_w) // 2, wt_y), welcome_text, fill=white, font=welcome_font)

    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer


async def create_leaderboard_image(users_list, guild):
    """
    users_list: list of (member, data) tuples, already sorted
    Returns a BytesIO image buffer
    """
    # ===== Settings =====
    row_height = 80
    padding = 20
    avatar_size = 50
    header_height = 70
    width = 750
    count = len(users_list)
    height = header_height + (row_height * count) + padding * 2

    # Colors
    bg_color = (32, 34, 37)          # Dark background
    card_bg = (47, 49, 54)           # Card background
    row_bg = (54, 57, 63)            # Row background
    row_alt_bg = (47, 49, 54)        # Alternate row
    gold = (255, 185, 50)            # Gold for title & #1
    silver = (192, 192, 192)         # Silver for #2
    bronze = (205, 127, 50)          # Bronze for #3
    white = (255, 255, 255)
    gray = (180, 180, 180)
    light_gray = (140, 140, 140)
    separator = (60, 63, 68)

    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Draw main card
    draw.rounded_rectangle([10, 10, width - 10, height - 10], radius=15, fill=card_bg)

    # Load fonts
    try:
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:/Windows/Fonts/arial.ttf"
        ]
        title_font = None
        for font_path in font_paths:
            if os.path.exists(font_path):
                title_font = ImageFont.truetype(font_path, 26)
                name_font = ImageFont.truetype(font_path, 20)
                stats_font = ImageFont.truetype(font_path, 16)
                rank_font = ImageFont.truetype(font_path, 28)
                small_font = ImageFont.truetype(font_path, 14)
                break
        if title_font is None:
            raise Exception("No font found")
    except:
        title_font = ImageFont.load_default()
        name_font = ImageFont.load_default()
        stats_font = ImageFont.load_default()
        rank_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # ===== Draw Title =====
    title_text = "Leaderboard"
    title_ar = "| \u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u062a\u0635\u062f\u0631\u064a\u0646"
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    title_w = title_bbox[2] - title_bbox[0]
    ar_bbox = draw.textbbox((0, 0), title_ar, font=stats_font)
    ar_w = ar_bbox[2] - ar_bbox[0]
    total_title_w = title_w + ar_w + 10
    title_x = (width - total_title_w) // 2
    draw.text((title_x, 22), title_text, fill=gold, font=title_font)
    draw.text((title_x + title_w + 10, 28), title_ar, fill=gold, font=stats_font)

    # Decorative line under title
    draw.line([(30, header_height - 5), (width - 30, header_height - 5)], fill=gold, width=2)

    # ===== Fetch avatars concurrently =====
    avatar_images = []
    async with aiohttp.ClientSession() as session:
        for member, data in users_list:
            try:
                async with session.get(str(member.display_avatar.url)) as resp:
                    avatar_data = await resp.read()
                    av = Image.open(BytesIO(avatar_data)).convert('RGBA')
                    av = av.resize((avatar_size, avatar_size))
                    avatar_images.append(av)
            except:
                avatar_images.append(None)

    # ===== Draw Rows =====
    for i, (member, data) in enumerate(users_list):
        y = header_height + padding + (row_height * i)
        row_fill = row_bg if i % 2 == 0 else row_alt_bg

        # Row background
        draw.rounded_rectangle([20, y, width - 20, y + row_height - 5], radius=10, fill=row_fill)

        # Rank number color
        if i == 0:
            rank_color = gold
        elif i == 1:
            rank_color = silver
        elif i == 2:
            rank_color = bronze
        else:
            rank_color = light_gray

        # Rank number
        rank_text = f"#{i + 1}"
        draw.text((35, y + (row_height - 5) // 2 - 16), rank_text, fill=rank_color, font=rank_font)

        # Avatar (circular)
        av_x = 90
        av_y = y + (row_height - 5 - avatar_size) // 2
        if avatar_images[i] is not None:
            mask = Image.new('L', (avatar_size, avatar_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse([0, 0, avatar_size, avatar_size], fill=255)
            img.paste(avatar_images[i], (av_x, av_y), mask)
        else:
            draw.ellipse([av_x, av_y, av_x + avatar_size, av_y + avatar_size], fill=rank_color)

        # Username
        username = member.display_name
        if len(username) > 18:
            username = username[:15] + "..."
        draw.text((av_x + avatar_size + 15, y + 12), username, fill=white, font=name_font)

        # Level under username
        level = data.get('level', 1)
        level_text = f"LVL {level}"
        draw.text((av_x + avatar_size + 15, y + 38), level_text, fill=light_gray, font=small_font)

        # Stats on the right side: CR (credits) | XP | Rank
        credits = data.get('credits', 0)
        xp = data.get('xp', 0)

        stats_text = f"CR: {credits:,}  |  XP: {xp:,}  |  LVL: {level}"
        stats_bbox = draw.textbbox((0, 0), stats_text, font=stats_font)
        stats_w = stats_bbox[2] - stats_bbox[0]
        draw.text((width - 40 - stats_w, y + (row_height - 5) // 2 - 10), stats_text, fill=gray, font=stats_font)

        # Separator line (except last row)
        if i < count - 1:
            line_y = y + row_height - 3
            draw.line([(30, line_y), (width - 30, line_y)], fill=separator, width=1)

    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer


async def create_invite_leaderboard_image(inviters_list, guild):
    """
    inviters_list: list of (member, inv_data) tuples, already sorted by invited_count
    Returns a BytesIO image buffer
    """
    # ===== Settings =====
    row_height = 80
    padding = 20
    avatar_size = 50
    header_height = 70
    width = 750
    count = len(inviters_list)
    height = header_height + (row_height * count) + padding * 2

    # Colors
    bg_color = (32, 34, 37)
    card_bg = (47, 49, 54)
    row_bg = (54, 57, 63)
    row_alt_bg = (47, 49, 54)
    gold = (255, 185, 50)
    silver = (192, 192, 192)
    bronze = (205, 127, 50)
    white = (255, 255, 255)
    gray = (180, 180, 180)
    light_gray = (140, 140, 140)
    separator = (60, 63, 68)

    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Draw main card
    draw.rounded_rectangle([10, 10, width - 10, height - 10], radius=15, fill=card_bg)

    # Load fonts
    try:
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:/Windows/Fonts/arial.ttf"
        ]
        title_font = None
        for font_path in font_paths:
            if os.path.exists(font_path):
                title_font = ImageFont.truetype(font_path, 26)
                name_font = ImageFont.truetype(font_path, 20)
                stats_font = ImageFont.truetype(font_path, 16)
                rank_font = ImageFont.truetype(font_path, 28)
                small_font = ImageFont.truetype(font_path, 14)
                break
        if title_font is None:
            raise Exception("No font found")
    except:
        title_font = ImageFont.load_default()
        name_font = ImageFont.load_default()
        stats_font = ImageFont.load_default()
        rank_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # ===== Draw Title =====
    title_text = "Invite Leaderboard"
    title_ar = "| \u0644\u0648\u062d\u0629 \u0645\u062a\u0635\u062f\u0631\u064a\u0646 \u0627\u0644\u062f\u0639\u0648\u0627\u062a"
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    title_w = title_bbox[2] - title_bbox[0]
    ar_bbox = draw.textbbox((0, 0), title_ar, font=stats_font)
    ar_w = ar_bbox[2] - ar_bbox[0]
    total_title_w = title_w + ar_w + 10
    title_x = (width - total_title_w) // 2
    draw.text((title_x, 22), title_text, fill=gold, font=title_font)
    draw.text((title_x + title_w + 10, 28), title_ar, fill=gold, font=stats_font)

    # Decorative line under title
    draw.line([(30, header_height - 5), (width - 30, header_height - 5)], fill=gold, width=2)

    # ===== Fetch avatars concurrently =====
    avatar_images = []
    async with aiohttp.ClientSession() as session:
        for member, inv_data in inviters_list:
            try:
                async with session.get(str(member.display_avatar.url)) as resp:
                    avatar_data = await resp.read()
                    av = Image.open(BytesIO(avatar_data)).convert('RGBA')
                    av = av.resize((avatar_size, avatar_size))
                    avatar_images.append(av)
            except:
                avatar_images.append(None)

    # ===== Draw Rows =====
    for i, (member, inv_data) in enumerate(inviters_list):
        y = header_height + padding + (row_height * i)
        row_fill = row_bg if i % 2 == 0 else row_alt_bg

        # Row background
        draw.rounded_rectangle([20, y, width - 20, y + row_height - 5], radius=10, fill=row_fill)

        # Rank number color
        if i == 0:
            rank_color = gold
        elif i == 1:
            rank_color = silver
        elif i == 2:
            rank_color = bronze
        else:
            rank_color = light_gray

        # Rank number
        rank_text = f"#{i + 1}"
        draw.text((35, y + (row_height - 5) // 2 - 16), rank_text, fill=rank_color, font=rank_font)

        # Avatar (circular)
        av_x = 90
        av_y = y + (row_height - 5 - avatar_size) // 2
        if avatar_images[i] is not None:
            mask = Image.new('L', (avatar_size, avatar_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse([0, 0, avatar_size, avatar_size], fill=255)
            img.paste(avatar_images[i], (av_x, av_y), mask)
        else:
            draw.ellipse([av_x, av_y, av_x + avatar_size, av_y + avatar_size], fill=rank_color)

        # Username
        username = member.display_name
        if len(username) > 18:
            username = username[:15] + "..."
        draw.text((av_x + avatar_size + 15, y + 15), username, fill=white, font=name_font)

        # Invites count under username
        inv_count = inv_data.get("invited_count", 0)
        sub_text = f"Invites: {inv_count}"
        draw.text((av_x + avatar_size + 15, y + 42), sub_text, fill=light_gray, font=small_font)

        # Stats on the right side
        total_earned = inv_data.get("total_earned", 0)
        stats_text = f"Invites: {inv_count}  |  CR: {total_earned:,}"
        stats_bbox = draw.textbbox((0, 0), stats_text, font=stats_font)
        stats_w = stats_bbox[2] - stats_bbox[0]
        draw.text((width - 40 - stats_w, y + (row_height - 5) // 2 - 10), stats_text, fill=gray, font=stats_font)

        # Separator line (except last row)
        if i < count - 1:
            line_y = y + row_height - 3
            draw.line([(30, line_y), (width - 30, line_y)], fill=separator, width=1)

    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer


async def create_rank_card(user, member, guild):
    width, height = 900, 280
    
    hex_color = user.get("rank_color", "#DC143C")
    bg_hex_color = user.get("card_bg_color", "#36393F")
    
    accent_color = hex_to_rgb(hex_color)
    card_bg_color = hex_to_rgb(bg_hex_color)
    
    img = Image.new('RGB', (width, height), card_bg_color)
    draw = ImageDraw.Draw(img)
    
    draw.rounded_rectangle([0, 0, width, height], radius=15, fill=card_bg_color)
    
    avatar_size = 90
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(str(member.display_avatar.url)) as resp:
                avatar_data = await resp.read()
                avatar = Image.open(BytesIO(avatar_data)).convert('RGBA')
                avatar = avatar.resize((avatar_size, avatar_size))
                
                mask = Image.new('L', (avatar_size, avatar_size), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse([0, 0, avatar_size, avatar_size], fill=255)
                
                img.paste(avatar, (25, 50), mask)
    except:
        draw.ellipse([25, 50, 25+avatar_size, 50+avatar_size], fill=accent_color)
    
    try:
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:/Windows/Fonts/arial.ttf"
        ]
        
        big_font = None
        medium_font = None
        small_font = None
        tiny_font = None
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                big_font = ImageFont.truetype(font_path, 36)
                medium_font = ImageFont.truetype(font_path, 24)
                small_font = ImageFont.truetype(font_path, 18)
                tiny_font = ImageFont.truetype(font_path, 14)
                break
        
        if big_font is None:
            raise Exception("No font found")
            
    except:
        big_font = ImageFont.load_default()
        medium_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
        tiny_font = ImageFont.load_default()
    
    rank, total = get_rank(guild.id, member.id, guild)
    level = user["level"]
    
    rank_text = f"RANK #{rank}"
    draw.text((130, 20), rank_text, fill=(255, 170, 0), font=big_font)
    
    level_text = f"LEVEL {level}"
    rank_bbox = draw.textbbox((0, 0), rank_text, font=big_font)
    rank_width = rank_bbox[2] - rank_bbox[0]
    draw.text((140 + rank_width, 20), level_text, fill=(255, 255, 255), font=big_font)
    
    double_xp_status = "ON" if has_double_xp(guild.id, member.id) else "OFF"
    status_color = (0, 255, 0) if double_xp_status == "ON" else (255, 0, 0)
    draw.text((width - 200, 20), f"Double XP: {double_xp_status}", fill=status_color, font=small_font)
    
    if is_server_booster(member):
        booster_color = (244, 127, 255)
        draw.text((width - 200, 40), "1.5x XP", fill=booster_color, font=small_font)
    
    username = str(member)
    if len(username) > 20:
        username = username[:17] + "..."
    draw.text((130, 65), username, fill=(255, 255, 255), font=medium_font)
    
    current_xp_in_level = get_current_level_xp(user["xp"], level)
    xp_needed = get_xp_needed_for_next_level(level)
    xp_left = xp_needed - current_xp_in_level
    
    xp_left_text = f"{xp_left} XP left"
    draw.text((width - 180, 65), xp_left_text, fill=(150, 150, 150), font=small_font)
    
    current_xp_text = f"{current_xp_in_level} XP"
    draw.text((width - 120, 90), current_xp_text, fill=(255, 255, 255), font=medium_font)
    
    bar_x = 130
    bar_y = 120
    bar_width = 550
    bar_height = 15
    
    darker_bg = tuple(max(0, c - 30) for c in card_bg_color)
    draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height], 
                          radius=8, fill=darker_bg)
    
    progress = current_xp_in_level / xp_needed if xp_needed > 0 else 0
    fill_width = int(bar_width * progress)
    if fill_width > 0:
        draw.rounded_rectangle([bar_x, bar_y, bar_x + fill_width, bar_y + bar_height], 
                              radius=8, fill=accent_color)
    
    box_y = 160
    box_height = 80
    box_width = 200
    gap = 15
    start_x = 25
    
    stats = [
        ("Rank", f"#{rank}"),
        ("Level", str(level)),
        ("XP", str(user["xp"])),
        ("Credits", str(user["credits"]))
    ]
    
    for i, (label, value) in enumerate(stats):
        x = start_x + (box_width + gap) * i
        
        draw.rounded_rectangle([x, box_y, x + box_width, box_y + box_height], 
                              radius=10, fill=accent_color)
        
        draw.text((x + 10, box_y + 10), label, fill=(255, 255, 255), font=small_font)
        draw.text((x + 10, box_y + 35), value, fill=(255, 255, 255), font=medium_font)
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer

# ======= دوال إدارة رتب اللفل (المعدلة النهائية - مضمونة 100%) =======

async def give_single_level_role(member, level):
    """
    تشيل الرتبة القديمة بس وتحط الجديدة
    بالضبط زي ما انت عايز:
    - لفل 10 = يتشال لفل 5
    - لفل 15 = يتشال لفل 10
    - لفل 20 = يتشال لفل 15
    - لفل 25 = يتشال لفل 20
    - لفل 30 = يتشال لفل 25
    - لفل 35 = يتشال لفل 30
    - لفل 40 = يتشال لفل 35
    - لفل 50 = يتشال لفل 40
    - لفل 60 = يتشال لفل 50
    - لفل 70 = يتشال لفل 60
    - لفل 80 = يتشال لفل 70
    - لفل 90 = يتشال لفل 80
    - لفل 100 = يتشال لفل 90
    """
    level_roles = {
        5: "Level 5",
        10: "Level 10",
        15: "Level 15",
        20: "Level 20",
        25: "Level 25",
        30: "Level 30",
        35: "Level 35",
        40: "Level 40",
        50: "Level 50",
        60: "Level 60",
        70: "Level 70",
        80: "Level 80",
        90: "Level 90",
        100: "Level 100"
    }
    
    removed_roles = []
    added_role = None
    
    # لو اللفل مش من اللفلات اللي ليها رتب، نخرج
    if level not in level_roles:
        return None
    
    # الرتبة الجديدة اللي المفروض نضيفها
    new_role_name = level_roles[level]
    new_role = discord.utils.get(member.guild.roles, name=new_role_name)
    
    # نتأكد إن الرتبة الجديدة موجودة في السيرفر
    if not new_role:
        print(f"❌ رتبة {new_role_name} مش موجودة في السيرفر!")
        return None
    
    # نشيل الرتبة القديمة (اللي أقل من اللفل الحالي)
    old_level = None
    level_list = [5, 10, 15, 20, 25, 30, 35, 40, 50, 60, 70, 80, 90, 100]
    
    # لو اللفل الحالي في القائمة، نجيب الرتبة اللي قبله
    current_index = level_list.index(level) if level in level_list else -1
    if current_index > 0:
        old_level = level_list[current_index - 1]
    
    if old_level and old_level in level_roles:
        old_role_name = level_roles[old_level]
        old_role = discord.utils.get(member.guild.roles, name=old_role_name)
        if old_role and old_role in member.roles:
            try:
                await member.remove_roles(old_role)
                removed_roles.append(old_role_name)
                print(f"✅ إزالة {old_role_name} من {member.name}")
            except Exception as e:
                print(f"❌ فشل إزالة {old_role_name}: {e}")
    
    # نضيف الرتبة الجديدة لو مش موجودة
    if new_role not in member.roles:
        try:
            await member.add_roles(new_role)
            added_role = new_role_name
            print(f"✅ إضافة {new_role_name} لـ {member.name}")
        except Exception as e:
            print(f"❌ فشل إضافة {new_role_name}: {e}")
    else:
        print(f"ℹ️ {member.name} عنده {new_role_name} بالفعل")
    
    return added_role

async def remove_all_level_roles(member):
    """يشيل كل رتب اللفل من العضو (للاستخدام في التحذيرات فقط)"""
    level_roles = ["Level 5", "Level 10", "Level 15", "Level 20", "Level 25", 
                   "Level 30", "Level 35", "Level 40", "Level 50", "Level 60", 
                   "Level 70", "Level 80", "Level 90", "Level 100"]
    removed_roles = []
    
    for role_name in level_roles:
        role = discord.utils.get(member.guild.roles, name=role_name)
        if role and role in member.roles:
            try:
                await member.remove_roles(role)
                removed_roles.append(role_name)
                print(f"✅ إزالة {role_name} من {member.name} (تصفير)")
            except:
                pass
    return removed_roles

async def send_level_up_dm(member, level, base_credits, bonus, features, new_role_name, is_milestone):
    """إرسال رسالة لفل أب مبسطة في الخاص"""
    if is_milestone:
        msg = f"🎉 Congratulations! You reached level {level} and received {base_credits} credits!\n"
        if bonus > 0:
            msg += f"you got {bonus} credits bonus 🎁\n"
        if new_role_name:
            msg += f"You got the **{new_role_name}** role! 🎭\n"
        if features:
            msg += "New features unlocked:\n"
            msg += "\n".join(features)
    else:
        msg = f"🎉 Level Up! You reached level {level} and received {base_credits} credits!"
    
    await member.send(msg)

# ========== الجزء 5: كلاسات الـ UI والشوب والتيكت (محدثة بالقائمة المنسدلة) ==========

class DoubleXPView(View):
    def __init__(self, user_id, member):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.member = member
        self.create_buttons()
    
    def create_buttons(self):
        is_booster = is_server_booster(self.member)
        self.clear_items()
        
        durations = [
            ("1h", "1 Hour"),
            ("3h", "3 Hours"),
            ("6h", "6 Hours"),
            ("12h", "12 Hours"),
            ("24h", "24 Hours"),
            ("1w", "1 Week")
        ]
        
        row = 0
        for i, (key, label) in enumerate(durations):
            price, _ = get_item_price("double_xp", key, self.member)
            hours = SHOP_ITEMS["double_xp"][key]["duration"]
            
            if i >= 3:
                row = 1
            
            button = Button(
                label=f"{label} - {price} Credits",
                style=discord.ButtonStyle.success,
                emoji="⚡",
                row=row,
                custom_id=f"buy_{key}"
            )
            button.callback = lambda interaction, k=key: self.buy_double_xp(interaction, k)
            self.add_item(button)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ ده مش شوبك!", ephemeral=True)
            return False
        return True
    
    async def buy_double_xp(self, interaction: discord.Interaction, duration_key: str):
        can_use, remaining = check_global_cooldown(interaction.user.id)
        if not can_use:
            await interaction.response.send_message(f"⏳ انتظر {remaining:.1f} ثانية!", ephemeral=True)
            return
            
        user = get_user_data(interaction.guild.id, interaction.user.id)
        
        price, is_discounted = get_item_price("double_xp", duration_key, self.member)
        hours = SHOP_ITEMS["double_xp"][duration_key]["duration"]
        
        if user["credits"] < price:
            await interaction.response.send_message(f"❌ معاكش كريدت كفاية! محتاج {price} كريدت", ephemeral=True)
            return
        
        user["credits"] -= price
        
        if user.get("double_xp_until") and datetime.now() < datetime.fromisoformat(user["double_xp_until"]):
            current_expiry = datetime.fromisoformat(user["double_xp_until"])
            new_expiry = current_expiry + timedelta(hours=hours)
        else:
            new_expiry = datetime.now() + timedelta(hours=hours)
        
        user["double_xp_until"] = new_expiry.isoformat()
        user["double_xp_active"] = True
        save_data(user_data)
        
        duration_text = f"{hours} ساعة" if hours < 24 else f"{hours//24} يوم"
        await log_shop_purchase(interaction.client, interaction.user, "Double XP", price, duration_text, is_discounted)
        
        embed = discord.Embed(title="✅ تم الشراء بنجاح!", description=f"اشتريت **Double XP** لمدة **{hours}** ساعة!", color=discord.Color.green())
        embed.add_field(name="💰 السعر", value=f"{price} كريدت {'(خصم بوستر 25% 🚀)' if is_discounted else ''}", inline=True)
        embed.add_field(name="💳 الرصيد المتبقي", value=f"{user['credits']} كريدت", inline=True)
        embed.add_field(name="⏰ ينتهي في", value=f"<t:{int(new_expiry.timestamp())}:R>", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class RankColorModal(Modal, title="🎨 Set Rank Card Color"):
    color_input = TextInput(label="Enter color name or hex code", placeholder="مثال: red أو #FF5733", required=True, max_length=20)
    
    async def on_submit(self, interaction: discord.Interaction):
        can_use, remaining = check_global_cooldown(interaction.user.id)
        if not can_use:
            await interaction.response.send_message(f"⏳ انتظر {remaining:.1f} ثانية!", ephemeral=True)
            return
            
        user = get_user_data(interaction.guild.id, interaction.user.id)
        
        price, is_discounted = get_item_price("rank_color", member=interaction.user)
        
        if user["credits"] < price:
            await interaction.response.send_message(f"❌ معاكش كريدت كفاية! محتاج {price} كريدت", ephemeral=True)
            return
        
        color = self.color_input.value.strip()
        
        valid_colors = {
            "red": "#FF0000", "green": "#00FF00", "blue": "#0000FF",
            "yellow": "#FFFF00", "purple": "#800080", "orange": "#FFA500",
            "pink": "#FFC0CB", "cyan": "#00FFFF", "white": "#FFFFFF",
            "black": "#000000", "gold": "#FFD700", "silver": "#C0C0C0",
            "crimson": "#DC143C", "lime": "#00FF00", "navy": "#000080",
            "brown": "#8B4513", "gray": "#808080", "grey": "#808080",
            "violet": "#EE82EE", "indigo": "#4B0082", "turquoise": "#40E0D0",
            "magenta": "#FF00FF", "teal": "#008080", "coral": "#FF7F50",
            "salmon": "#FA8072", "khaki": "#F0E68C", "plum": "#DDA0DD",
            "orchid": "#DA70D6", "maroon": "#800000", "olive": "#808000"
        }
        
        hex_color = None
        if color.lower() in valid_colors:
            hex_color = valid_colors[color.lower()]
        elif color.startswith("#") and len(color) == 7:
            hex_color = color.upper()
        else:
            await interaction.response.send_message("❌ لون غير صحيح! استخدم اسم لون أو كود HEX (مثل #FF5733)", ephemeral=True)
            return
        
        try:
            test_rgb = hex_to_rgb(hex_color)
        except:
            await interaction.response.send_message("❌ كود اللون غير صحيح!", ephemeral=True)
            return
        
        user["credits"] -= price
        user["rank_color"] = hex_color
        save_data(user_data)
        
        await log_shop_purchase(interaction.client, interaction.user, "Rank Color", price, is_booster=is_discounted)
        
        embed = discord.Embed(title="✅ تم تغيير لون الرانك!", description=f"اللون الجديد: **{hex_color}**\n(لون النصوط والصناديق)", color=discord.Color.green())
        embed.add_field(name="💰 السعر", value=f"{price} كريدت {'(خصم بوستر 25% 🚀)' if is_discounted else ''}", inline=True)
        embed.add_field(name="💳 الرصيد المتبقي", value=f"{user['credits']} كريدت", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ===== قائمة ألوان الباكجراوند =====

class BackgroundColorSelect(Select):
    def __init__(self, user_id, member):
        self.user_id = user_id
        self.member = member
        
        bg_colors = [
            ("Dark Gray (Default)", "#36393F", "\u2b1b"),
            ("Black", "#1a1a2e", "\u2b1b"),
            ("Deep Navy", "#0f3460", "\ud83c\udf0a"),
            ("Dark Purple", "#2d1b69", "\ud83d\udfe3"),
            ("Dark Red", "#6b0000", "\ud83d\udfe5"),
            ("Dark Green", "#1b4332", "\ud83d\udfe2"),
            ("Dark Blue", "#003566", "\ud83d\udd35"),
            ("Dark Teal", "#004d4d", "\ud83d\udc8e"),
            ("Midnight", "#191970", "\ud83c\udf19"),
            ("Dark Brown", "#3d2b1f", "\ud83d\udfe4"),
            ("Charcoal", "#2c2c2c", "\u25fc\ufe0f"),
            ("Dark Olive", "#3c4a2e", "\ud83e\uded2"),
            ("Dark Crimson", "#4a0000", "\u2764\ufe0f"),
            ("Dark Cyan", "#003b46", "\ud83e\uddca"),
            ("Dark Magenta", "#4a004a", "\ud83d\udc9c"),
            ("Dark Gold", "#4a3800", "\ud83c\udf1f"),
            ("Steel Blue", "#2a4a6b", "\ud83d\udd37"),
            ("Forest", "#0b3d0b", "\ud83c\udf32"),
            ("Wine", "#4a0028", "\ud83c\udf77"),
            ("Slate", "#3b4252", "\ud83e\udea8"),
        ]
        
        options = []
        for name, hex_code, emoji in bg_colors:
            options.append(
                discord.SelectOption(
                    label=name,
                    value=hex_code,
                    emoji=emoji,
                    description=f"{hex_code}"
                )
            )
        
        super().__init__(
            placeholder="اختر لون الباكجراوند...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("مش ليك!", ephemeral=True)
            return
        
        hex_color = self.values[0]
        await self.buy_bg_color(interaction, hex_color)
    
    async def buy_bg_color(self, interaction, hex_color):
        user = get_user_data(interaction.guild.id, interaction.user.id)
        price, is_discounted = get_item_price("bg_color", member=interaction.user)
        
        if user["credits"] < price:
            await interaction.response.send_message(
                f"معاكش كريدت كفاية! محتاج **{price}** كريدت (عندك {user['credits']})",
                ephemeral=True
            )
            return
        
        user["credits"] -= price
        user["card_bg_color"] = hex_color
        save_data(user_data)
        
        await log_shop_purchase(interaction.client, interaction.user, "Background Color", price, is_booster=is_discounted)
        
        discount_text = " (خصم بوستر 25%)" if is_discounted else ""
        embed = discord.Embed(
            title="تم تغيير لون الباكجراوند!",
            description=f"اللون الجديد: **{hex_color}**\nاستخدم `/rank` عشان تشوف الشكل الجديد!",
            color=discord.Color.green()
        )
        embed.add_field(name="السعر", value=f"{price} كريدت{discount_text}", inline=True)
        embed.add_field(name="الرصيد المتبقي", value=f"{user['credits']} كريدت", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class BackgroundColorView(View):
    def __init__(self, user_id, member):
        super().__init__(timeout=60)
        self.add_item(BackgroundColorSelect(user_id, member))


# ===== قائمة الألوان المنسدلة الجديدة (زي التيكت بالظبط) =====
class NameColorSelect(Select):
    def __init__(self, user_id, member):
        self.user_id = user_id
        self.member = member
        
        # تجهيز خيارات الألوان
        options = []
        
        # الألوان العادية (2000)
        normal_colors = ["Red", "Green", "White", "Purple", "Pink", "Blue", "Cyan", "Ecto"]
        for color in normal_colors:
            options.append(
                discord.SelectOption(
                    label=f"{color}",
                    description=f"السعر: 2000 كريدت",
                    emoji="🎨",
                    value=f"color_{color}"
                )
            )
        
        # ألوان VIP (4500)
        vip_colors = ["VIP Purple", "VIP Pink", "VIP Blue", "VIP Cyan"]
        for color in vip_colors:
            options.append(
                discord.SelectOption(
                    label=f"{color}",
                    description=f"السعر: 4500 كريدت",
                    emoji="💎",
                    value=f"color_{color}"
                )
            )
        
        # اللون الأسود (7000)
        options.append(
            discord.SelectOption(
                label="Black",
                description="السعر: 7000 كريدت",
                emoji="🖤",
                value="color_Black"
            )
        )
        
        super().__init__(
            placeholder="🎨 اختر لون من القائمة...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        # التأكد من أن المستخدم هو نفسه
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ ده مش شوبك!", ephemeral=True)
            return
        
        value = self.values[0]  # color_Red مثلاً
        color_name = value.replace("color_", "")
        
        # تحديد السعر حسب اللون
        normal_colors = ["Red", "Green", "White", "Purple", "Pink", "Blue", "Cyan", "Ecto"]
        vip_colors = ["VIP Purple", "VIP Pink", "VIP Blue", "VIP Cyan"]
        
        if color_name in normal_colors:
            price = 2000
        elif color_name in vip_colors:
            price = 4500
        elif color_name == "Black":
            price = 7000
        else:
            price = 2000
        
        # تنفيذ عملية الشراء
        await self.buy_color(interaction, color_name, price)
    
    async def buy_color(self, interaction: discord.Interaction, color_name: str, price: int):
        can_use, remaining = check_global_cooldown(interaction.user.id)
        if not can_use:
            await interaction.response.send_message(f"⏳ انتظر {remaining:.1f} ثانية!", ephemeral=True)
            return
        
        user = get_user_data(interaction.guild.id, interaction.user.id)
        current_level = user["level"]
        
        # شرط Level 30
        if current_level < 30:
            embed = discord.Embed(
                title="⛔ مش هينفع تشتري لون دلوقتي",
                description=(
                    f"• لفلك الحالي: **Level {current_level}**\n"
                    f"• المطلوب: **Level 30**\n\n"
                    f"⚠️ لازم توصل لفل 30 عشان تقدر تشتري ألوان!\n\n"
                    f"💡 كمل في الشات والرومات الصوتية وهتوصل بسرعة إن شاء الله 💪"
                ),
                color=discord.Color.orange()
            )
            embed.set_footer(text="كل ما تلفل أكتر، كل ما تفتحلك ميزات أكتر!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if user["credits"] < price:
            await interaction.response.send_message(f"❌ معاكش كريدت كفاية! محتاج {price} كريدت", ephemeral=True)
            return
        
        # إضافة اللون
        success = await add_name_color(interaction.user, color_name)
        
        if success:
            user["credits"] -= price
            user["name_color"] = color_name
            save_data(user_data)
            
            await log_shop_purchase(interaction.client, interaction.user, f"Name Color - {color_name}", price)
            
            embed = discord.Embed(
                title="✅ تم شراء اللون!",
                description=f"لون اسمك بقى **{color_name}**",
                color=discord.Color.green()
            )
            embed.add_field(name="💰 السعر", value=f"{price} كريدت", inline=True)
            embed.add_field(name="💳 الرصيد المتبقي", value=f"{user['credits']} كريدت", inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("❌ فشل إضافة اللون! تأكد إن الرتبة موجودة في السيرفر", ephemeral=True)

# ===== فيو الألوان الجديد (يحتوي على القائمة المنسدلة + زر الإزالة) =====
class NameColorView(View):
    def __init__(self, user_id, member):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.member = member
        self.add_item(NameColorSelect(user_id, member))
        self.add_item(RemoveColorButton(user_id, member))

class RemoveColorButton(Button):
    def __init__(self, user_id, member):
        super().__init__(
            label="🧹 إزالة اللون - 250 كريدت",
            style=discord.ButtonStyle.danger,
            emoji="🧹",
            row=1
        )
        self.user_id = user_id
        self.member = member
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ ده مش شوبك!", ephemeral=True)
            return
        
        can_use, remaining = check_global_cooldown(interaction.user.id)
        if not can_use:
            await interaction.response.send_message(f"⏳ انتظر {remaining:.1f} ثانية!", ephemeral=True)
            return
        
        user = get_user_data(interaction.guild.id, interaction.user.id)
        price = 250
        
        if user["credits"] < price:
            await interaction.response.send_message(f"❌ معاكش كريدت كفاية! محتاج {price} كريدت", ephemeral=True)
            return
        
        # إزالة أي لون قديم
        removed = await remove_old_name_color(interaction.user)
        
        if removed:
            user["credits"] -= price
            user["name_color"] = None
            save_data(user_data)
            
            await log_shop_purchase(interaction.client, interaction.user, "Remove Color", price)
            
            embed = discord.Embed(
                title="🧹 تم إزالة اللون",
                description="تم إزالة لون اسمك بنجاح!",
                color=discord.Color.green()
            )
            embed.add_field(name="💰 السعر", value=f"{price} كريدت", inline=True)
            embed.add_field(name="💳 الرصيد المتبقي", value=f"{user['credits']} كريدت", inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("ℹ️ معندكش لون عشان تشيله!", ephemeral=True)

class ShopView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="⚡ Double XP", style=discord.ButtonStyle.primary, emoji="✨", custom_id="shop:double_xp", row=0)
    async def double_xp_btn(self, interaction: discord.Interaction, button: Button):
        user = get_user_data(interaction.guild.id, interaction.user.id)
        
        can_use, remaining = check_global_cooldown(interaction.user.id)
        if not can_use:
            await interaction.response.send_message(f"⏳ انتظر {remaining:.1f} ثانية!", ephemeral=True)
            return
        
        is_booster = is_server_booster(interaction.user)
        
        time_left = get_double_xp_time_remaining(interaction.guild.id, interaction.user.id)
        status_text = f"⚡ الحالة: {'مفعل' if has_double_xp(interaction.guild.id, interaction.user.id) else 'غير مفعل'}"
        if time_left:
            status_text += f" (متبقي: {time_left})"
        
        if is_booster:
            status_text += "\n🚀 **لأنك بوستر، تحصل على خصم 25% على كل المنتجات!**"
            
        embed = discord.Embed(title="✨ Double XP - Choose Duration", description=f"اختار مدة Double XP\n\nرصيدك الحالي: **{user['credits']}** كريدت\n\n{status_text}", color=discord.Color.gold())
        view = DoubleXPView(interaction.user.id, interaction.user)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="🎨 Rank Color", style=discord.ButtonStyle.primary, emoji="🖌️", custom_id="shop:rank_color", row=0)
    async def rank_color_btn(self, interaction: discord.Interaction, button: Button):
        can_use, remaining = check_global_cooldown(interaction.user.id)
        if not can_use:
            await interaction.response.send_message(f"⏳ انتظر {remaining:.1f} ثانية!", ephemeral=True)
            return
            
        modal = RankColorModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="🖼️ BG Color", style=discord.ButtonStyle.primary, emoji="🖼️", custom_id="shop:bg_color", row=0)
    async def bg_color_btn(self, interaction: discord.Interaction, button: Button):
        can_use, remaining = check_global_cooldown(interaction.user.id)
        if not can_use:
            await interaction.response.send_message(f"⏳ انتظر {remaining:.1f} ثانية!", ephemeral=True)
            return
        
        user = get_user_data(interaction.guild.id, interaction.user.id)
        current_bg = user.get("card_bg_color", "#36393F")
        price, is_discounted = get_item_price("bg_color", member=interaction.user)
        
        discount_text = " (خصم بوستر 25% 🚀)" if is_discounted else ""
        embed = discord.Embed(
            title="🖼️ Background Color - لون الباكجراوند",
            description=(
                f"🎨 لونك الحالي: **{current_bg}**\n\n"
                f"💰 السعر: **{price}** كريدت{discount_text}\n"
                f"💳 رصيدك: **{user['credits']}** كريدت\n\n"
                f"📋 **اختر لون من القائمة أدناه:**"
            ),
            color=discord.Color.purple()
        )
        
        view = BackgroundColorView(interaction.user.id, interaction.user)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="🎨 Name Color", style=discord.ButtonStyle.success, emoji="🌈", custom_id="shop:name_color", row=1)
    async def name_color_btn(self, interaction: discord.Interaction, button: Button):
        can_use, remaining = check_global_cooldown(interaction.user.id)
        if not can_use:
            await interaction.response.send_message(f"⏳ انتظر {remaining:.1f} ثانية!", ephemeral=True)
            return
        
        user = get_user_data(interaction.guild.id, interaction.user.id)
        current_level = user["level"]
        
        # رسالة تحذيرية قبل الدخول
        if current_level < 30:
            embed = discord.Embed(
                title="🎨 ألوان الأسماء",
                description=(
                    f"⚠️ **ميزة الألوان متاحة فقط لـ Level 30+**\n"
                    f"📊 لفلك الحالي: **Level {current_level}**\n\n"
                    f"🔒 الألوان مقفولة عليك دلوقتي\n"
                    f"⚡ كمل وكسب XP عشان تفتحها!"
                ),
                color=discord.Color.orange()
            )
            embed.set_footer(text="خليك نشيط وهتوصل بسرعة!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # لو لفل 30+ يكمل عادي
        current_color = user.get("name_color")
        if current_color:
            status = f"✅ لونك الحالي: **{current_color}**"
        else:
            status = "❌ معندكش لون"
        
        embed = discord.Embed(
            title="🎨 Name Colors - ألوان الأسماء",
            description=f"{status}\n\n📋 **اختر لون من القائمة أدناه:**\n\n• **الألوان العادية:** 2000💰\n• **ألوان VIP:** 4500💰\n• **الأسود:** 7000💰\n\n🧹 **إزالة اللون:** 250💰",
            color=discord.Color.blue()
        )
        
        view = NameColorView(interaction.user.id, interaction.user)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# نظام التيكت
class TicketControlView(View):
    def __init__(self, ticket_channel, ticket_owner):
        super().__init__(timeout=None)
        self.ticket_channel = ticket_channel
        self.ticket_owner = ticket_owner
        self.claimed_by = None
    
    @discord.ui.button(label="🔒 غلق التيكت", style=discord.ButtonStyle.primary, emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.manage_channels and not can_use_ticket(interaction.user) and interaction.user.id != self.ticket_owner.id:
            await interaction.response.send_message("❌ مالكش صلاحية!", ephemeral=True)
            return
        
        await interaction.response.send_message("🔒 تم غلق التيكت!")
        
        overwrites = self.ticket_channel.overwrites
        for target in overwrites:
            overwrites[target].send_messages = False
        
        await self.ticket_channel.edit(overwrites=overwrites)
        
        reopen_view = TicketReopenView(self.ticket_channel, self.ticket_owner, self.claimed_by)
        await self.ticket_channel.send("🔒 **التيكت مقفول**\nاستخدم الأزرار تحت:", view=reopen_view)
    
    @discord.ui.button(label="🗑️ حذف التيكت", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_ticket(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.manage_channels and not can_use_ticket(interaction.user):
            await interaction.response.send_message("❌ مالكش صلاحية!", ephemeral=True)
            return
        
        await interaction.response.send_message("⏳ جاري حذف التيكت بعد 5 ثواني...")
        await asyncio.sleep(5)
        await self.ticket_channel.delete()
    
    @discord.ui.button(label="👤 أخذ التيكت", style=discord.ButtonStyle.success, emoji="👤")
    async def claim_ticket(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.manage_channels and not can_use_ticket(interaction.user):
            await interaction.response.send_message("❌ مالكش صلاحية!", ephemeral=True)
            return
        
        if self.claimed_by:
            await interaction.response.send_message(f"❌ التيكت متاخد بالفعل من {self.claimed_by.mention}!", ephemeral=True)
            return
        
        self.claimed_by = interaction.user
        
        # منع الكل من الكتابة ماعدا صاحب التيكت + اللي عامل claim + البوت
        overwrites = self.ticket_channel.overwrites
        for target in list(overwrites.keys()):
            if target == interaction.guild.default_role:
                continue
            if target == interaction.guild.me:
                continue
            if isinstance(target, discord.Member):
                if target.id == self.ticket_owner.id:
                    overwrites[target].send_messages = True
                else:
                    overwrites[target].send_messages = False
            elif isinstance(target, discord.Role):
                if target.permissions.administrator:
                    continue
                overwrites[target] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=False, read_message_history=True
                )
        
        # التأكد إن اللي عامل claim يقدر يكتب
        overwrites[interaction.user] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True
        )
        # التأكد إن صاحب التيكت يقدر يكتب
        overwrites[self.ticket_owner] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True
        )
        
        await self.ticket_channel.edit(overwrites=overwrites)
        await interaction.response.send_message(f"✅ {interaction.user.mention} أخذ التيكت!\n📝 دلوقتي بس صاحب التيكت واللي أخد التيكت يقدروا يكتبوا.")
    
    @discord.ui.button(label="🚪 ترك التيكت", style=discord.ButtonStyle.secondary, emoji="🚪")
    async def leave_ticket(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id == self.ticket_owner.id:
            await interaction.response.send_message("❌ صاحب التيكت مينفعش يمشي!", ephemeral=True)
            return
        
        was_claimer = self.claimed_by and interaction.user.id == self.claimed_by.id
        
        if was_claimer:
            self.claimed_by = None
            # إرجاع صلاحيات الكتابة لرتب التيكت والأدمن
            overwrites = self.ticket_channel.overwrites
            for target in list(overwrites.keys()):
                if target == interaction.guild.default_role:
                    continue
                if target == interaction.guild.me:
                    continue
                if isinstance(target, discord.Role):
                    if target.permissions.administrator:
                        continue
                    # إرجاع صلاحية الكتابة للرتب اللي عندها ticket
                    ticket_roles = get_ticket_roles(interaction.guild)
                    if target in ticket_roles or target.permissions.manage_channels:
                        overwrites[target] = discord.PermissionOverwrite(
                            view_channel=True, send_messages=True, read_message_history=True
                        )
            await self.ticket_channel.edit(overwrites=overwrites)
        
        await self.ticket_channel.set_permissions(interaction.user, overwrite=None)
        await interaction.response.send_message(f"👋 {interaction.user.mention} ساب التيكت!")
    
    @discord.ui.button(label="➕ إضافة عضو", style=discord.ButtonStyle.primary, emoji="➕")
    async def add_member(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.manage_channels and not can_use_ticket(interaction.user) and interaction.user.id != self.ticket_owner.id:
            await interaction.response.send_message("❌ مالكش صلاحية!", ephemeral=True)
            return
        
        modal = AddMemberModal(self.ticket_channel)
        await interaction.response.send_modal(modal)

class AddMemberModal(Modal, title="➕ إضافة عضو للتيكت"):
    member_input = TextInput(
        label="منشن العضو أو الآيدي",
        placeholder="@username أو 123456789",
        required=True,
        max_length=100
    )
    
    def __init__(self, ticket_channel):
        super().__init__()
        self.ticket_channel = ticket_channel
    
    async def on_submit(self, interaction: discord.Interaction):
        member_str = self.member_input.value.strip()
        
        member_id = None
        if member_str.startswith("<@") and member_str.endswith(">"):
            try:
                member_id = int(member_str.replace("<@", "").replace("!", "").replace(">", ""))
            except:
                pass
        elif member_str.isdigit():
            member_id = int(member_str)
        else:
            member = discord.utils.get(interaction.guild.members, name=member_str.replace("@", ""))
            if member:
                member_id = member.id
        
        if not member_id:
            await interaction.response.send_message("❌ ما قدرتش ألاقي العضو ده! استخدم المنشن أو الآيدي.", ephemeral=True)
            return
        
        member = interaction.guild.get_member(member_id)
        if not member:
            await interaction.response.send_message("❌ العضو ده مش موجود في السيرفر!", ephemeral=True)
            return
        
        try:
            await self.ticket_channel.set_permissions(member, 
                                                      view_channel=True, 
                                                      send_messages=True, 
                                                      read_message_history=True)
            await interaction.response.send_message(f"✅ تم إضافة {member.mention} للتيكت!")
        except Exception as e:
            await interaction.response.send_message(f"❌ حدث خطأ: {e}", ephemeral=True)

class TicketReopenView(View):
    def __init__(self, ticket_channel, ticket_owner, claimed_by):
        super().__init__(timeout=None)
        self.ticket_channel = ticket_channel
        self.ticket_owner = ticket_owner
        self.claimed_by = claimed_by
    
    @discord.ui.button(label="🔓 إعادة فتح التيكت", style=discord.ButtonStyle.success, emoji="🔓")
    async def reopen_ticket(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.manage_channels and not can_use_ticket(interaction.user) and interaction.user.id != self.ticket_owner.id:
            await interaction.response.send_message("❌ مالكش صلاحية!", ephemeral=True)
            return
        
        overwrites = self.ticket_channel.overwrites
        for target in overwrites:
            if target != interaction.guild.default_role:
                overwrites[target].send_messages = True
        
        await self.ticket_channel.edit(overwrites=overwrites)
        control_view = TicketControlView(self.ticket_channel, self.ticket_owner)
        await interaction.response.send_message("🔓 **تم إعادة فتح التيكت!**", view=control_view)
    
    @discord.ui.button(label="🗑️ حذف نهائي", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def final_delete(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.manage_channels and not can_use_ticket(interaction.user):
            await interaction.response.send_message("❌ مالكش صلاحية!", ephemeral=True)
            return
        
        await interaction.response.send_message("⏳ جاري الحذف النهائي...")
        await asyncio.sleep(3)
        await self.ticket_channel.delete()

class TicketSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Question about the server", description="Visible to everyone", emoji="❓", value="question"),
            discord.SelectOption(label="Help / Solve a problem", description="Visible to everyone", emoji="🛠️", value="help"),
            discord.SelectOption(label="Verification Girl", description="Visible ONLY to users with the female role", emoji="🎀", value="verification_girl"),
            discord.SelectOption(label="Report User", description="Report a user for breaking rules", emoji="🚨", value="report"),
            discord.SelectOption(label="Partnership", description="Request a partnership", emoji="🤝", value="partnership")
        ]
        super().__init__(placeholder="Select a category", min_values=1, max_values=1, options=options)
    
    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        guild = interaction.guild
        user = interaction.user
        
        if category == "verification_girl":
            female_role = discord.utils.get(guild.roles, name="female")
            if not female_role or female_role not in user.roles:
                await interaction.response.send_message("❌ ده التيكت للبنات بس!", ephemeral=True)
                return
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }
        
        for role in guild.roles:
            if role.permissions.manage_channels or role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        
        # إضافة الرتب اللي عندها صلاحية ticket
        ticket_roles = get_ticket_roles(guild)
        for role in ticket_roles:
            if role not in overwrites:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        
        channel_name = f"ticket-{user.name}-{category}"
        channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites, category=interaction.channel.category)
        
        embed = discord.Embed(title=f"🎫 Ticket - {category.replace('_', ' ').title()}", description=f"مرحباً {user.mention}!\nفريق الدعم هيجي يساعدك قريب.", color=discord.Color.blue())
        embed.add_field(name="الفئة", value=category.replace('_', ' ').title(), inline=True)
        embed.add_field(name="صاحب التيكت", value=user.mention, inline=True)
        
        control_view = TicketControlView(channel, user)
        await channel.send(f"🚨 {user.mention}", embed=embed, view=control_view)
        await interaction.response.send_message(f"✅ تم إنشاء تيكت: {channel.mention}", ephemeral=True)

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

# ========== باقي الكود (الأجزاء 6-8) زي ما هو من الكود السابق ==========
# ========== الجزء 6: كلاس البوت والأحداث الرئيسية (المعدل) ==========

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True
intents.invites = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=".", intents=intents, help_command=None)
        self.synced = False
    
    async def setup_hook(self):
        # تسجيل الـ Views الدائمة عشان تشتغل بعد إعادة تشغيل البوت
        self.add_view(BankMainView())
        self.add_view(ShopView())
        self.add_view(InfoEmbedsView())
        self.add_view(ModApplicationView())

        if not self.synced:
            print("⏳ جاري تسجيل الأوامر...")
            for guild in self.guilds:
                try:
                    self.tree.copy_global_to(guild=guild)
                    synced = await self.tree.sync(guild=guild)
                    print(f"✅ {guild.name}: {len(synced)} أمر")
                except Exception as e:
                    print(f"❌ {guild.name}: {e}")
            self.synced = True
    
    async def on_ready(self):
        print(f'🤖 البوت شغال: {self.user}')
        print(f'📊 في {len(self.guilds)} سيرفر')
        
        # تغيير حالة البوت
        await self.change_presence(
            activity=discord.CustomActivity(
                name="/help — Muz.gg —"
            ),
            status=discord.Status.online
        )
        
        # كاش الإنفايتات لكل السيرفرات
        for guild in self.guilds:
            try:
                guild_invites_cache[guild.id] = await guild.invites()
            except Exception as e:
                print(f"❌ خطأ في جلب الإنفايتات لـ {guild.name}: {e}")
        print("✅ تم تحميل كاش الإنفايتات")
        
        self.cleanup_cooldowns.start()
        self.voice_xp_task.start()
        self.warnings_cleanup_task.start()
        self.invite_reward_checker.start()

    @tasks.loop(minutes=5)
    async def cleanup_cooldowns(self):
        now = datetime.now().timestamp()
        to_remove = [uid for uid, time in command_cooldowns.items() if now - time > 300]
        for uid in to_remove:
            del command_cooldowns[uid]

    @tasks.loop(minutes=1)
    async def voice_xp_task(self):
        """
        نظام XP الصوتي (كل دقيقة) مع إعدادات VC القابلة للتعديل
        """
        for guild in self.guilds:
            if not is_level_enabled(guild.id):
                continue
            
            # جلب إعدادات VC لهذا السيرفر
            vc_config = get_guild_vc_config(guild.id)
            xp_per_minute = vc_config.get("vc_xp_per_minute", 10)
            xp_min = vc_config.get("vc_xp_min", 5)
            xp_max = vc_config.get("vc_xp_max", 15)
            active_only = vc_config.get("vc_active_only", False)
            boost_multiplier = vc_config.get("vc_boost_multiplier", 1.5)
            
            for channel in guild.voice_channels:
                for member in channel.members:
                    if member.bot:
                        continue
                    
                    # لو active_only مفعل، نتأكد انه مش mute/deafen
                    if active_only and (member.voice.self_mute or member.voice.self_deaf):
                        continue
                    
                    if is_muted(guild.id, member.id):
                        continue
                    
                    user = get_user_data(guild.id, member.id)
                    old_level = user["level"]
                    
                    # XP الأساسي (random بين min و max)
                    xp_gain = random.randint(xp_min, xp_max)
                    
                    # مضاعفة الـ XP لو مشتري Double XP
                    if has_double_xp(guild.id, member.id):
                        xp_gain *= 2
                    
                    # مضاعف البوستر
                    if is_server_booster(member):
                        xp_gain = int(xp_gain * boost_multiplier)
                    
                    # زود الـ XP
                    user["xp"] += xp_gain
                    
                    # احسب اللفل الجديد
                    new_level = get_level_from_xp(user["xp"])
                    user["level"] = new_level
                    
                    # عدل الرتب بس لما اللفل يتغير فعلاً
                    if new_level > old_level:
                        base_credits, bonus, features, is_milestone = get_level_rewards(new_level)
                        total_credits = base_credits + bonus
                        user["credits"] += total_credits
                        
                        # جلب الرتبة الجديدة
                        new_role = await give_single_level_role(member, new_level)
                        
                        # إرسال DM
                        try:
                            await send_level_up_dm(member, new_level, base_credits, bonus, features, new_role, is_milestone)
                        except:
                            pass
                    
                    save_data(user_data)

    @tasks.loop(hours=1)
    async def warnings_cleanup_task(self):
        """تاسك لتنظيف التحذيرات القديمة بعد 7 أيام"""
        now = datetime.now()
        for gid in list(warnings_data.keys()):
            guild_warnings = warnings_data.get(gid, {})
            if not isinstance(guild_warnings, dict):
                continue
            for user_id in list(guild_warnings.keys()):
                user_warns = guild_warnings[user_id]
                if not user_warns:
                    continue
                
                last_warning = user_warns[-1]
                last_warning_date = datetime.fromisoformat(last_warning['date'])
                
                if (now - last_warning_date).days >= 7:
                    warnings_data[gid][user_id] = []
                    save_warnings(warnings_data)
                    
                    guild_ud = user_data.get(gid, {})
                    if str(user_id) in guild_ud:
                        guild_ud[str(user_id)]["warnings"] = 0
                        save_data(user_data)
                    
                    print(f"🧹 تم تنظيف تحذيرات المستخدم {user_id} في السيرفر {gid} بعد 7 أيام")

    @tasks.loop(minutes=1)
    async def invite_reward_checker(self):
        """تاسك لفحص الأعضاء الجدد اللي دخلوا من إنفايت ومر عليهم الوقت الكافي"""
        now = datetime.now()
        to_remove = []
        for key, data in pending_invite_rewards.items():
            join_time = datetime.fromisoformat(data["join_time"])
            elapsed = (now - join_time).total_seconds() / 60
            
            if elapsed >= INVITE_MIN_STAY_MINUTES:
                inviter_id = data["inviter_id"]
                member_id = data["member_id"]
                guild_id = data["guild_id"]
                member_name = data["member_name"]
                
                # إضافة المكافأة
                inviter_user = get_user_data(guild_id, inviter_id)
                inviter_user["credits"] += INVITE_REWARD
                save_data(user_data)
                
                # تحديث بيانات الإنفايت
                inv_data = get_invite_user(guild_id, inviter_id)
                inv_data["invited_count"] += 1
                inv_data["total_earned"] += INVITE_REWARD
                inv_data["invited_members"].append({
                    "user_id": str(member_id),
                    "name": member_name,
                    "date": now.isoformat()
                })
                save_invite_data(invite_data)
                
                # إرسال DM للداعي
                try:
                    guild = self.get_guild(guild_id)
                    if guild:
                        inviter_member = guild.get_member(inviter_id)
                        if inviter_member:
                            embed = discord.Embed(
                                title="🎉 مكافأة إنفايت!",
                                description=(
                                    f"**{member_name}** دخل السيرفر من لينك الدعوة بتاعك وقعد أكتر من {INVITE_MIN_STAY_MINUTES} دقيقة!\n\n"
                                    f"💰 **كسبت {INVITE_REWARD} كريدت!**\n"
                                    f"📊 إجمالي الناس اللي دعيتهم: **{inv_data['invited_count']}**\n"
                                    f"💎 إجمالي الكريدت من الدعوات: **{inv_data['total_earned']:,}**"
                                ),
                                color=discord.Color.green(),
                                timestamp=now
                            )
                            embed.set_footer(text="Invite System")
                            await inviter_member.send(embed=embed)
                except Exception as e:
                    print(f"خطأ في إرسال DM مكافأة الإنفايت: {e}")
                
                to_remove.append(key)
        
        for key in to_remove:
            del pending_invite_rewards[key]

bot = MyBot()

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return
    
    if not is_level_enabled(member.guild.id):
        return
    
    if after.channel and not before.channel:
        user = get_user_data(member.guild.id, member.id)
        user["voice_join_time"] = datetime.now().isoformat()
        save_data(user_data)
    
    elif before.channel and not after.channel:
        user = get_user_data(member.guild.id, member.id)
        user["voice_join_time"] = None
        save_data(user_data)

@bot.event
async def on_member_join(member):
    try:
        await log_join(bot, member)
    except Exception as e:
        print(f"Error in on_member_join log: {e}")
    
    # === نظام تتبع الإنفايت ===
    try:
        guild = member.guild
        # جلب الإنفايتات الجديدة
        new_invites = await guild.invites()
        old_invites = guild_invites_cache.get(guild.id, [])
        
        inviter = None
        for new_inv in new_invites:
            for old_inv in old_invites:
                if new_inv.code == old_inv.code and new_inv.uses > old_inv.uses:
                    inviter = new_inv.inviter
                    break
            if inviter:
                break
        
        # تحديث الكاش
        guild_invites_cache[guild.id] = new_invites
        
        if inviter and inviter.id != member.id and not member.bot:
            # تحقق إذا العضو ده اتدعى قبل كده (مرة واحدة بس لكل شخص)
            if is_member_already_invited(guild.id, member.id):
                print(f"⚠️ {member.display_name} اتدعى قبل كده — مفيش مكافأة تاني")
            else:
                # تسجيل الدعوة كـ pending (مش هنديه المكافأة لسه)
                key = f"{guild.id}_{member.id}"
                pending_invite_rewards[key] = {
                    "inviter_id": inviter.id,
                    "member_id": member.id,
                    "member_name": member.display_name,
                    "guild_id": guild.id,
                    "join_time": datetime.now().isoformat()
                }
                member_join_times[member.id] = datetime.now()
                print(f"📨 {member.display_name} دخل من إنفايت {inviter.display_name} — في انتظار {INVITE_MIN_STAY_MINUTES} دقيقة...")
    except Exception as e:
        print(f"Error in invite tracking: {e}")
    
    # Welcome image + embed
    try:
        cfg = load_guild_config()
        welcome_channel_id = cfg.get(str(member.guild.id), {}).get("welcome_channel")
        if welcome_channel_id:
            channel = bot.get_channel(int(welcome_channel_id))
            if channel:
                dash_cfg = get_dashboard_guild_config(member.guild.id)
                member_count = len(member.guild.members)

                # Build welcome embed
                w_title = (dash_cfg.get("welcome_title") or "Greetings, {member}").replace("{member}", member.display_name).replace("{server}", member.guild.name).replace("{count}", f"{member_count:,}")
                w_body = (dash_cfg.get("welcome_message") or "").replace("{member}", member.mention).replace("{server}", member.guild.name).replace("{count}", f"{member_count:,}")
                w_footer = (dash_cfg.get("welcome_footer") or "").replace("{member}", member.display_name).replace("{server}", member.guild.name).replace("{count}", f"{member_count:,}")
                w_image = dash_cfg.get("welcome_image")

                welcome_embed = discord.Embed(
                    title=f"╭─ {w_title}",
                    description=(
                        f"{w_body}\n\n"
                        f"> {w_footer}"
                    ),
                    color=DASH_COLOR_MAIN if 'DASH_COLOR_MAIN' in dir() else 0x2B2D31,
                    timestamp=datetime.now()
                )

                if member.guild.icon:
                    welcome_embed.set_author(name=member.guild.name, icon_url=member.guild.icon.url)
                else:
                    welcome_embed.set_author(name=member.guild.name)

                welcome_embed.set_thumbnail(url=member.display_avatar.url)

                if w_image:
                    welcome_embed.set_image(url=w_image)
                else:
                    # Fallback: use generated welcome image
                    img_buffer = await create_welcome_image(member)
                    file = discord.File(img_buffer, filename="welcome.png")
                    welcome_embed.set_image(url="attachment://welcome.png")
                    await channel.send(content=member.mention, embed=welcome_embed, file=file)
                    return  # already sent with file

                await channel.send(content=member.mention, embed=welcome_embed)
    except Exception as e:
        print(f"Error in welcome image: {e}")

@bot.event
async def on_member_remove(member):
    try:
        await log_leave(bot, member)
    except Exception as e:
        print(f"Error in on_member_remove: {e}")
    
    # === أنتي-أبيوز الإنفايت ===
    # لو العضو طلع قبل ما يكمل الوقت المطلوب، نلغي المكافأة
    try:
        key = f"{member.guild.id}_{member.id}"
        if key in pending_invite_rewards:
            inviter_id = pending_invite_rewards[key]["inviter_id"]
            del pending_invite_rewards[key]
            print(f"🚫 {member.display_name} طلع قبل {INVITE_MIN_STAY_MINUTES} دقيقة — المكافأة ملغية للداعي {inviter_id}")
        
        # تحديث كاش الإنفايتات
        try:
            guild_invites_cache[member.guild.id] = await member.guild.invites()
        except:
            pass
        
        if member.id in member_join_times:
            del member_join_times[member.id]
    except Exception as e:
        print(f"Error in invite anti-abuse: {e}")

@bot.event
async def on_invite_create(invite):
    """تحديث كاش الإنفايتات لما حد يعمل لينك جديد"""
    try:
        guild_invites_cache[invite.guild.id] = await invite.guild.invites()
    except Exception as e:
        print(f"Error updating invite cache on create: {e}")

@bot.event
async def on_invite_delete(invite):
    """تحديث كاش الإنفايتات لما لينك يتمسح"""
    try:
        guild_invites_cache[invite.guild.id] = await invite.guild.invites()
    except Exception as e:
        print(f"Error updating invite cache on delete: {e}")

@bot.event
async def on_message_delete(message):
    if message.guild:
        try:
            await log_message_delete(bot, message)
        except Exception as e:
            print(f"Error in on_message_delete: {e}")

@bot.event
async def on_message_edit(before, after):
    if before.guild:
        try:
            await log_message_edit(bot, before, after)
        except Exception as e:
            print(f"Error in on_message_edit: {e}")

@bot.event
async def on_message(message):
    # تجاهل رسائل البوتات
    if message.author.bot:
        return
    
    # التحقق من الميوت
    if message.guild and is_muted(message.guild.id, message.author.id):
        return
    
    # معالجة الأوامر الأولوية
    if message.content.startswith('.'):
        # === نظام الاختصارات المخصصة ===
        if message.guild:
            try:
                dash_cfg = get_dashboard_guild_config(message.guild.id)
                custom_aliases = dash_cfg.get("aliases", {})
                if custom_aliases:
                    msg_content = message.content[1:].strip()  # بعد النقطة
                    first_word = msg_content.split()[0] if msg_content else ""
                    for original_cmd, alias in custom_aliases.items():
                        if alias and first_word == alias:
                            rest = msg_content[len(first_word):]
                            message.content = f".{original_cmd}{rest}"
                            break
            except Exception as e:
                print(f"Error in alias resolution: {e}")
        await bot.process_commands(message)
        return
    
    # نظام مكافحة السبام والشتائم
    if message.guild and is_anti_cheat_enabled(message.guild.id):
        try:
            if await anti_cheat.handle_bad_words(message, bot):
                return
            if await anti_cheat.handle_spam(message, bot):
                return
        except Exception as e:
            print(f"Error in anti_cheat: {e}")
    
    # نظام الـ XP
    if not message.guild:
        return
    
    if not is_level_enabled(message.guild.id):
        return
    
    user_id = str(message.author.id)
    user = get_user_data(message.guild.id, user_id)
    
    # احفظ اللفل القديم قبل التعديل
    old_level = user["level"]
    
    now = datetime.now().timestamp()
    cooldown = bot_config.get("xp_cooldown", 30)
    last_xp = user.get("last_xp_time", 0)
    
    if now - last_xp < cooldown:
        return
    
    xp_min = bot_config.get("xp_min", 10)
    xp_max = bot_config.get("xp_max", 15)
    xp_gain = random.randint(xp_min, xp_max)
    
    # مضاعفة الـ XP
    if has_double_xp(message.guild.id, message.author.id):
        xp_gain *= 2
    
    # 1.5x XP للبوسترز
    if is_server_booster(message.author):
        xp_gain = int(xp_gain * 1.5)
    
    # زود الـ XP
    user["xp"] += xp_gain
    user["last_xp_time"] = now
    
    # احسب اللفل الجديد
    new_level = get_level_from_xp(user["xp"])
    user["level"] = new_level
    
    # عدل الرتب بس لما اللفل يتغير فعلاً
    if new_level > old_level:
        base_credits, bonus, features, is_milestone = get_level_rewards(new_level)
        total_credits = base_credits + bonus
        user["credits"] += total_credits
        
        # جلب الرتبة الجديدة
        new_role = await give_single_level_role(message.author, new_level)
        
        # إرسال DM
        if not user.get("dm_muted"):
            try:
                await send_level_up_dm(message.author, new_level, base_credits, bonus, features, new_role, is_milestone)
            except:
                pass
    
    save_data(user_data)

# ========== الجزء 7: اختصارات المودريشن (Prefix Commands) ==========

@bot.command(name="وارن")
async def cmd_warn(ctx, member: discord.Member, *, reason: str = "لا يوجد سبب"):
    """اختصار التحذير: .وارن @عضو السبب"""
    if not can_use_warn(ctx.author):
        await ctx.send("❌ مالكش صلاحية لاستخدام أمر التحذير!")
        return
    
    try:
        if member.top_role >= ctx.author.top_role:
            await ctx.send("❌ لا يمكن تحذير عضو أعلى منك!")
            return
        
        user = get_user_data(ctx.guild.id, member.id)
        user["warnings"] += 1
        warning_num = add_warning(ctx.guild.id, member.id, reason, ctx.author.id)
        
        punishment = None
        punishment_icon = ""
        
        if user["warnings"] == 2:
            try:
                await member.timeout(timedelta(minutes=10), reason="2 تحذيرات")
                punishment = "⏱️ تايم اوت 10 دقائق"
                punishment_icon = "⏱️"
                await log_timeout(bot, member, "10 دقائق", "2 تحذيرات", ctx.author)
            except Exception as e:
                print(f"Error in timeout: {e}")
                
        elif user["warnings"] == 3:
            try:
                await member.timeout(timedelta(minutes=30), reason="3 تحذيرات")
                punishment = "⏱️ تايم اوت 30 دقيقة"
                punishment_icon = "⏱️"
                await log_timeout(bot, member, "30 دقيقة", "3 تحذيرات", ctx.author)
            except Exception as e:
                print(f"Error in timeout: {e}")
                
        elif user["warnings"] >= 4:
            try:
                await remove_all_level_roles(member)
            except Exception as e:
                print(f"Error removing roles: {e}")
            user["level"] = 1
            user["xp"] = 0
            user["credits"] = 100
            user["warnings"] = 0
            clear_warnings(ctx.guild.id, member.id)
            punishment = "🔄 تصفير اللفل والكريدت ومسح التحذيرات"
            punishment_icon = "🔄"
        
        save_data(user_data)
        
        # إرسال DM
        try:
            dm_embed = discord.Embed(title="⚠️ تحذير جديد", description=f"تم تحذيرك في سيرفر **{ctx.guild.name}**", color=discord.Color.orange())
            dm_embed.add_field(name="📝 السبب", value=reason, inline=False)
            dm_embed.add_field(name="🔢 عدد التحذيرات", value=f"{user['warnings']}/4", inline=True)
            if punishment:
                dm_embed.add_field(name="⛔ العقوبة", value=punishment, inline=False)
            dm_embed.add_field(name="⏰ ملاحظة", value="التحذيرات هتتشال بعد 7 أيام لو مجالكش تحذيرات تانية!", inline=False)
            await member.send(embed=dm_embed)
        except Exception as e:
            print(f"Error sending DM: {e}")
        
        # إرسال الرد في الإمبد
        embed = discord.Embed(title="⚠️ تحذير جديد", color=discord.Color.orange(), timestamp=datetime.now())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👤 العضو", value=member.mention, inline=True)
        embed.add_field(name="👮‍♂️ المُحذِّر", value=ctx.author.mention, inline=True)
        embed.add_field(name="📝 السبب", value=reason, inline=False)
        embed.add_field(name="🔢 التحذيرات", value=f"`{user['warnings']}/4`", inline=True)
        
        # حساب الوقت المتبقي للتنظيف
        if user["warnings"] > 0:
            user_warnings = get_user_warnings(ctx.guild.id, member.id)
            if user_warnings:
                last_warning = user_warnings[-1]
                last_date = datetime.fromisoformat(last_warning['date'])
                expiry_date = last_date + timedelta(days=7)
                time_left = expiry_date - datetime.now()
                days_left = time_left.days
                hours_left = time_left.seconds // 3600
                
                time_text = f"{days_left} يوم و {hours_left} ساعة" if days_left > 0 else f"{hours_left} ساعة"
                embed.add_field(name="⏰ يتم ازالة كل التحذيرات بعد", value=f"{time_text}", inline=False)
        
        if punishment:
            embed.add_field(name=f"{punishment_icon} العقوبة التلقائية", value=punishment, inline=False)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"Error in warn command: {e}")
        await ctx.send(f"❌ حدث خطأ: {e}")

@bot.command(name="انوارن")
async def cmd_unwarn(ctx, member: discord.Member):
    """اختصار إزالة التحذير: .انوارن @عضو"""
    if not can_use_warn(ctx.author):
        await ctx.send("❌ مالكش صلاحية لاستخدام هذا الأمر!")
        return
    
    try:
        user = get_user_data(ctx.guild.id, member.id)
        
        if user["warnings"] > 0:
            user["warnings"] -= 1
            save_data(user_data)
            
            try:
                await member.send(f"✅ تم إزالة تحذير منك في **{ctx.guild.name}**!\nالآن: {user['warnings']}/4")
            except:
                pass
            
            embed = discord.Embed(title="✅ إزالة تحذير", color=discord.Color.green(), timestamp=datetime.now())
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="👤 العضو", value=member.mention, inline=True)
            embed.add_field(name="👮‍♂️ المُنفِّذ", value=ctx.author.mention, inline=True)
            embed.add_field(name="🔢 التحذيرات الحالية", value=f"`{user['warnings']}/4`", inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ {member.mention} مالوش تحذيرات!")
            
    except Exception as e:
        print(f"Error in unwarn command: {e}")
        await ctx.send(f"❌ حدث خطأ: {e}")

@bot.command(name="تحذيرات")
async def cmd_warnings(ctx, member: discord.Member = None):
    """اختصار عرض التحذيرات: .تحذيرات @عضو"""
    if not can_use_warnings(ctx.author):
        await ctx.send("❌ مالكش صلاحية لاستخدام هذا الأمر!")
        return
    
    try:
        target = member or ctx.author
        user_warnings = get_user_warnings(ctx.guild.id, target.id)
        user = get_user_data(ctx.guild.id, target.id)
        
        embed = discord.Embed(title=f"⚠️ تحذيرات {target.display_name}", description=f"عدد التحذيرات: **{len(user_warnings)}/4**", color=discord.Color.orange())
        embed.set_thumbnail(url=target.display_avatar.url)
        
        if user_warnings:
            for i, warning in enumerate(user_warnings[-4:], 1):
                date = datetime.fromisoformat(warning['date']).strftime("%Y-%m-%d %H:%M")
                embed.add_field(name=f"تحذير #{i}", value=f"**السبب:** {warning['reason']}\n**من:** <@{warning['moderator']}>\n**التاريخ:** {date}", inline=False)
            
            # إضافة وقت التنظيف
            last_warning = user_warnings[-1]
            last_date = datetime.fromisoformat(last_warning['date'])
            expiry_date = last_date + timedelta(days=7)
            time_left = expiry_date - datetime.now()
            
            if time_left.total_seconds() > 0:
                days_left = time_left.days
                hours_left = time_left.seconds // 3600
                minutes_left = (time_left.seconds % 3600) // 60
                
                if days_left > 0:
                    time_text = f"{days_left} يوم و {hours_left} ساعة و {minutes_left} دقيقة"
                elif hours_left > 0:
                    time_text = f"{hours_left} ساعة و {minutes_left} دقيقة"
                else:
                    time_text = f"{minutes_left} دقيقة"
                
                embed.add_field(name="⏰ يتم ازالة كل التحذيرات بعد", value=f"{time_text}", inline=False)
        else:
            embed.add_field(name="✅", value="مفيش تحذيرات!", inline=False)
        
        status = "🟢 آمن"
        if user['warnings'] == 1:
            status = "🟡 تحذير أول"
        elif user['warnings'] == 2:
            status = "🟠 تحذير ثاني (تايم اوت 10 دق)"
        elif user['warnings'] == 3:
            status = "🔴 تحذير ثالث (تايم اوت 30 دق)"
        elif user['warnings'] >= 4:
            status = "⛔ تحذير رابع (Reset Level)"
        
        embed.add_field(name="📊 الحالة الحالية", value=status, inline=False)
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"Error in warnings command: {e}")
        await ctx.send(f"❌ حدث خطأ: {e}")

@bot.command(name="بان", aliases=["انطر"])
async def cmd_ban(ctx, member: discord.Member, *, reason: str = "لا يوجد سبب"):
    """اختصار الحظر: .بان أو .انطر @عضو السبب"""
    if not can_use_ban(ctx.author):
        await ctx.send("❌ مالكش صلاحية لاستخدام أمر الحظر!")
        return
    
    try:
        if member.top_role >= ctx.author.top_role:
            await ctx.send("❌ لا يمكن حظر عضو أعلى منك!")
            return
        
        # إرسال اللوج
        try:
            await log_ban(bot, member, reason, ctx.author)
        except Exception as e:
            print(f"Error logging ban: {e}")
        
        # إرسال DM
        try:
            await member.send(f"🔨 تم حظرك من **{ctx.guild.name}**!\nالسبب: {reason}")
        except:
            pass
        
        # تنفيذ الحظر
        await member.ban(reason=reason)
        
        embed = discord.Embed(title="🔨 حظر عضو", color=discord.Color.dark_red(), timestamp=datetime.now())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👤 العضو", value=member.mention, inline=True)
        embed.add_field(name="👮‍♂️ المُنفِّذ", value=ctx.author.mention, inline=True)
        embed.add_field(name="📝 السبب", value=reason, inline=False)
        await ctx.send(embed=embed)
        
    except discord.Forbidden:
        await ctx.send("❌ البوت لا يملك صلاحية لحظر هذا العضو!")
    except Exception as e:
        print(f"Error in ban command: {e}")
        await ctx.send(f"❌ حدث خطأ: {e}")

@bot.command(name="انباند")
async def cmd_unban(ctx, user_id: str):
    """اختصار فك الحظر: .انباند الايدي"""
    if not can_use_unban(ctx.author):
        await ctx.send("❌ مالكش صلاحية لاستخدام هذا الأمر!")
        return
    
    try:
        user = await bot.fetch_user(int(user_id))
        await ctx.guild.unban(user)
        
        embed = discord.Embed(title="✅ فك حظر", description=f"تم فك حظر **{user.name}** بنجاح!", color=discord.Color.green(), timestamp=datetime.now())
        embed.add_field(name="👮‍♂️ المُنفِّذ", value=ctx.author.mention, inline=True)
        await ctx.send(embed=embed)
        
    except discord.NotFound:
        await ctx.send("❌ لم يتم العثور على المستخدم!")
    except discord.Forbidden:
        await ctx.send("❌ البوت لا يملك صلاحية لفك الحظر!")
    except Exception as e:
        print(f"Error in unban command: {e}")
        await ctx.send(f"❌ حدث خطأ: {e}")

@bot.command(name="كيك")
async def cmd_kick(ctx, member: discord.Member, *, reason: str = "لا يوجد سبب"):
    """اختصار الطرد: .كيك @عضو السبب"""
    if not can_use_kick(ctx.author):
        await ctx.send("❌ مالكش صلاحية لاستخدام أمر الطرد!")
        return
    
    try:
        if member.top_role >= ctx.author.top_role:
            await ctx.send("❌ لا يمكن طرد عضو أعلى منك!")
            return
        
        # إرسال اللوج
        try:
            await log_kick(bot, member, reason, ctx.author)
        except Exception as e:
            print(f"Error logging kick: {e}")
        
        # إرسال DM
        try:
            await member.send(f"👢 تم طردك من **{ctx.guild.name}**!\nالسبب: {reason}")
        except:
            pass
        
        # تنفيذ الطرد
        await member.kick(reason=reason)
        
        embed = discord.Embed(title="👢 طرد عضو", color=discord.Color.orange(), timestamp=datetime.now())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👤 العضو", value=member.mention, inline=True)
        embed.add_field(name="👮‍♂️ المُنفِّذ", value=ctx.author.mention, inline=True)
        embed.add_field(name="📝 السبب", value=reason, inline=False)
        await ctx.send(embed=embed)
        
    except discord.Forbidden:
        await ctx.send("❌ البوت لا يملك صلاحية لطرد هذا العضو!")
    except Exception as e:
        print(f"Error in kick command: {e}")
        await ctx.send(f"❌ حدث خطأ: {e}")

@bot.command(name="تايم")
async def cmd_timeout(ctx, member: discord.Member, minutes: int, *, reason: str = "لا يوجد سبب"):
    """اختصار التايم أوت: .تايم @عضو الدقائق السبب"""
    if not can_use_timeout(ctx.author):
        await ctx.send("❌ مالكش صلاحية لاستخدام أمر التايم أوت!")
        return
    
    try:
        if member.top_role >= ctx.author.top_role:
            await ctx.send("❌ لا يمكن!")
            return
        
        # تنفيذ التايم أوت
        await member.timeout(timedelta(minutes=minutes), reason=reason)
        
        # إرسال DM
        try:
            await member.send(f"⏱️ تم عمل تايم اوت ليك في **{ctx.guild.name}** لمدة {minutes} دقيقة!\nالسبب: {reason}")
        except:
            pass
        
        # إرسال اللوج
        try:
            await log_timeout(bot, member, f"{minutes} دقيقة", reason, ctx.author)
        except Exception as e:
            print(f"Error logging timeout: {e}")
        
        embed = discord.Embed(title="⏱️ تايم اوت", color=discord.Color.orange(), timestamp=datetime.now())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👤 العضو", value=member.mention, inline=True)
        embed.add_field(name="👮‍♂️ المُنفِّذ", value=ctx.author.mention, inline=True)
        embed.add_field(name="⏰ المدة", value=f"`{minutes}` دقيقة", inline=True)
        embed.add_field(name="📝 السبب", value=reason, inline=False)
        await ctx.send(embed=embed)
        
    except discord.Forbidden:
        await ctx.send("❌ البوت لا يملك صلاحية لعمل تايم أوت لهذا العضو!")
    except Exception as e:
        print(f"Error in timeout command: {e}")
        await ctx.send(f"❌ حدث خطأ: {e}")

@bot.command(name="انتايم")
async def cmd_untimeout(ctx, member: discord.Member):
    """اختصار فك التايم أوت: .انتايم @عضو"""
    if not can_use_untimeout(ctx.author):
        await ctx.send("❌ مالكش صلاحية لاستخدام هذا الأمر!")
        return
    
    try:
        await member.timeout(None)
        
        try:
            await member.send(f"✅ تم فك تايم اوتك في **{ctx.guild.name}**!")
        except:
            pass
        
        embed = discord.Embed(title="✅ فك تايم اوت", color=discord.Color.green(), timestamp=datetime.now())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👤 العضو", value=member.mention, inline=True)
        embed.add_field(name="👮‍♂️ المُنفِّذ", value=ctx.author.mention, inline=True)
        await ctx.send(embed=embed)
        
    except discord.Forbidden:
        await ctx.send("❌ البوت لا يملك صلاحية لفك تايم أوت هذا العضو!")
    except Exception as e:
        print(f"Error in untimeout command: {e}")
        await ctx.send(f"❌ حدث خطأ: {e}")

@bot.command(name="ميوت")
async def cmd_mute(ctx, member: discord.Member, hours: int, *, reason: str = "لا يوجد سبب"):
    """اختصار الميوت: .ميوت @عضو الساعات السبب"""
    if not can_use_mute(ctx.author):
        await ctx.send("❌ مالكش صلاحية لاستخدام أمر الميوت!")
        return
    
    try:
        if member.top_role >= ctx.author.top_role:
            await ctx.send("❌ لا يمكن!")
            return
        
        user = get_user_data(ctx.guild.id, member.id)
        expiry = datetime.now() + timedelta(hours=hours)
        user["muted_until"] = expiry.isoformat()
        save_data(user_data)
        
        try:
            await member.send(f"🔇 تم عمل ميوت ليك في **{ctx.guild.name}** لمدة {hours} ساعة!\nالسبب: {reason}")
        except:
            pass
        
        # إرسال اللوج
        try:
            await log_mute(bot, member, f"{hours} ساعة", reason, ctx.author)
        except Exception as e:
            print(f"Error logging mute: {e}")
        
        embed = discord.Embed(title="🔇 ميوت", color=discord.Color.red(), timestamp=datetime.now())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👤 العضو", value=member.mention, inline=True)
        embed.add_field(name="👮‍♂️ المُنفِّذ", value=ctx.author.mention, inline=True)
        embed.add_field(name="⏰ المدة", value=f"`{hours}` ساعة", inline=True)
        embed.add_field(name="📝 السبب", value=reason, inline=False)
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"Error in mute command: {e}")
        await ctx.send(f"❌ حدث خطأ: {e}")

@bot.command(name="انميوت")
async def cmd_unmute(ctx, member: discord.Member):
    """اختصار فك الميوت: .انميوت @عضو"""
    if not can_use_unmute(ctx.author):
        await ctx.send("❌ مالكش صلاحية لاستخدام هذا الأمر!")
        return
    
    try:
        user = get_user_data(ctx.guild.id, member.id)
        user["muted_until"] = None
        save_data(user_data)
        
        try:
            await member.send(f"🔊 تم فك ميوتك في **{ctx.guild.name}**!")
        except:
            pass
        
        embed = discord.Embed(title="🔊 فك ميوت", color=discord.Color.green(), timestamp=datetime.now())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👤 العضو", value=member.mention, inline=True)
        embed.add_field(name="👮‍♂️ المُنفِّذ", value=ctx.author.mention, inline=True)
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"Error in unmute command: {e}")
        await ctx.send(f"❌ حدث خطأ: {e}")

@bot.command(name="رول")
async def cmd_role(ctx, member: discord.Member, role: discord.Role):
    """اختصار إعطاء/إزالة رول: .رول @عضو @رول"""
    if not can_use_role(ctx.author):
        await ctx.send("❌ مالكش صلاحية لاستخدام أمر الرتب!")
        return
    
    try:
        # التحقق من أن الرتبة ليست أعلى من رتبة البوت
        if role.position >= ctx.guild.me.top_role.position:
            await ctx.send("❌ البوت لا يستطيع التحكم في هذه الرتبة (رتبة البوت أقل)!")
            return
        
        if role in member.roles:
            try:
                await member.remove_roles(role)
            except discord.Forbidden:
                await ctx.send("❌ البوت لا يملك صلاحية لإزالة هذه الرتبة!")
                return
            action = "إزالة"
            color = discord.Color.red()
        else:
            try:
                await member.add_roles(role)
            except discord.Forbidden:
                await ctx.send("❌ البوت لا يملك صلاحية لإعطاء هذه الرتبة!")
                return
            action = "إعطاء"
            color = discord.Color.green()
        
        embed = discord.Embed(title=f"🎭 {action} رول", color=color, timestamp=datetime.now())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👤 العضو", value=member.mention, inline=True)
        embed.add_field(name="👮‍♂️ المُنفِّذ", value=ctx.author.mention, inline=True)
        embed.add_field(name="🎭 الرول", value=role.mention, inline=True)
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"Error in role command: {e}")
        await ctx.send(f"❌ حدث خطأ: {e}")

@bot.command(name="مسح")
async def cmd_clear(ctx, amount: int = 10):
    """اختصار مسح الرسائل: .مسح العدد"""
    if not can_use_clear(ctx.author):
        await ctx.send("❌ مالكش صلاحية لاستخدام أمر المسح!")
        return
    
    if amount < 1 or amount > 100:
        await ctx.send("❌ يجب أن يكون العدد بين 1 و 100!")
        return
    
    try:
        deleted = await ctx.channel.purge(limit=amount + 1)
        embed = discord.Embed(
            title="🗑️ تم المسح",
            description=f"تم مسح **{len(deleted)-1}** رسالة بنجاح!",
            color=discord.Color.green()
        )
        msg = await ctx.send(embed=embed)
        await asyncio.sleep(3)
        await msg.delete()
        
    except Exception as e:
        print(f"Error in clear command: {e}")
        await ctx.send(f"❌ حدث خطأ: {e}")

@bot.command(name="رانك")
@commands.cooldown(1, 3, commands.BucketType.user)
async def cmd_rank(ctx, member: discord.Member = None):
    target = member or ctx.author
    if target.bot:
        await ctx.send("❌ البوتات مالهاش رانك!")
        return
    
    user = get_user_data(ctx.guild.id, target.id)
    try:
        img_buffer = await create_rank_card(user, target, ctx.guild)
        file = discord.File(img_buffer, filename="rank.png")
        await ctx.send(file=file)
    except Exception as e:
        print(f"Error: {e}")
        await ctx.send(f"📊 {target.display_name} | Level {user['level']} | XP: {user['xp']}")

@bot.command(name="قفل")
async def cmd_lock(ctx, *, reason: str = None):
    """اختصار قفل الشات: .قفل السبب"""
    if not (can_use_warn(ctx.author) or can_use_lock(ctx.author)):
        await ctx.send("❌ مالكش صلاحية!")
        return
    
    channel = ctx.channel
    default_role = ctx.guild.default_role
    current_overwrites = channel.overwrites_for(default_role)
    
    if current_overwrites.send_messages is False:
        await ctx.send("❌ الشات مقفول أصلاً!")
        return
    
    current_overwrites.send_messages = False
    await channel.set_permissions(default_role, overwrite=current_overwrites)
    embed = discord.Embed(
        title="🔒 تم قفل الشات",
        description=f"**بواسطة:** {ctx.author.mention}",
        color=discord.Color.red()
    )
    if reason:
        embed.add_field(name="السبب", value=reason)
    await ctx.send(embed=embed)

@bot.command(name="فتح")
async def cmd_unlock(ctx, *, reason: str = None):
    """اختصار فتح الشات: .فتح السبب"""
    if not (can_use_warn(ctx.author) or can_use_unlock(ctx.author)):
        await ctx.send("❌ مالكش صلاحية!")
        return
    
    channel = ctx.channel
    default_role = ctx.guild.default_role
    current_overwrites = channel.overwrites_for(default_role)
    
    if current_overwrites.send_messages is not False:
        await ctx.send("❌ الشات مفتوح أصلاً!")
        return
    
    current_overwrites.send_messages = None
    await channel.set_permissions(default_role, overwrite=current_overwrites)
    embed = discord.Embed(
        title="🔓 تم فتح الشات",
        description=f"**بواسطة:** {ctx.author.mention}",
        color=discord.Color.green()
    )
    if reason:
        embed.add_field(name="السبب", value=reason)
    await ctx.send(embed=embed)

@bot.command()
@commands.is_owner()
@commands.cooldown(1, 10, commands.BucketType.user)
async def sync(ctx):
    await ctx.send("⏳ جاري التسجيل...")
    try:
        guild = ctx.guild
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        await ctx.send(f"✅ تم تسجيل {len(synced)} أمر!")
    except Exception as e:
        await ctx.send(f"❌ خطأ: {e}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ انتظر {error.retry_after:.1f} ثانية!")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ ما عندكش صلاحيات!")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ ما لقيتش العضو!")
    else:
        print(f"Error: {error}")

# ========== الجزء 8: أوامر السلاش للمستخدمين والأدمن + أوامر إدارة XP + أوامر المودريشن (محدث) ==========

# ========== أوامر السلاش للمستخدمين ==========

@bot.tree.command(name="shop", description="🛒 فتح متجر الكريدت")
async def slash_shop(interaction: discord.Interaction):
    can_use, remaining = check_global_cooldown(interaction.user.id)
    if not can_use:
        await interaction.response.send_message(f"⏳ انتظر {remaining:.1f} ثانية!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🛒 Server Shop", 
        description="اضغط على الزر عشان تشتري حاجة!", 
        color=discord.Color.blue()
    )
    embed.add_field(name="⚡ Double XP", value="ضاعف الـ XP اللي بتجمعه\n💰 270 - 9000 كريدت", inline=False)
    embed.add_field(name="🎨 Rank Color", value="غيّر لون النصوص والصناديق في كارت الرانك\n💰 1000 كريدت", inline=False)
    embed.add_field(name="🖼️ BG Color", value="غيّر لون خلفية كارت الرانك\n💰 1500 كريدت", inline=False)
    embed.add_field(name="🎨 Name Color", value="غيّر لون اسمك في السيرفر (Level 30+)\n💰 2000 - 7000 كريدت", inline=False)
    embed.add_field(name="🧹 Remove Color", value="إزالة لون الاسم\n💰 250 كريدت", inline=False)
    embed.set_footer(text="🚀 البوسترز ليهم خصم 25% على كل المنتجات!")
    view = ShopView()
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="shop_setup", description="🛒 إعداد الشوب في شانل معين (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(channel="الشانل")
@app_commands.checks.has_permissions(administrator=True)
async def slash_shop_setup(interaction: discord.Interaction, channel: discord.TextChannel):
    try:
        embed = discord.Embed(
            title="🛒 Server Shop",
            description=(
                "**مرحباً بيك في الشوب!** 🎉\n"
                "اضغط على الأزرار تحت عشان تشتري حاجة! 👇"
            ),
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.add_field(name="⚡ Double XP", value="> ضاعف الـ XP اللي بتجمعه\n> 💰 270 - 9000 كريدت", inline=False)
        embed.add_field(name="🎨 Rank Color", value="> غيّر لون النصوص والصناديق في كارت الرانك\n> 💰 1000 كريدت", inline=False)
        embed.add_field(name="🖼️ BG Color", value="> غيّر لون خلفية كارت الرانك\n> 💰 1500 كريدت", inline=False)
        embed.add_field(name="🎨 Name Color", value="> غيّر لون اسمك في السيرفر (Level 30+)\n> 💰 2000 - 7000 كريدت", inline=False)
        embed.add_field(name="🧹 Remove Color", value="> إزالة لون الاسم\n> 💰 250 كريدت", inline=False)
        embed.set_footer(text="🚀 البوسترز ليهم خصم 25% على كل المنتجات!")
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        view = ShopView()
        await channel.send(embed=embed, view=view)

        confirm = discord.Embed(
            title="✅ تم الإرسال",
            description=f"تم إعداد الشوب في {channel.mention} بالأزرار!",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=confirm, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ حصل خطأ: {e}", ephemeral=True)

# ========== نظام الإنفايت — أوامر ==========

@bot.tree.command(name="invites", description="📊 عرض إحصائيات الدعوات بتاعتك أو بتاعت عضو")
@app_commands.describe(member="العضو (اختياري)")
async def slash_invites(interaction: discord.Interaction, member: discord.Member = None):
    can_use, remaining = check_global_cooldown(interaction.user.id)
    if not can_use:
        await interaction.response.send_message(f"⏳ انتظر {remaining:.1f} ثانية!", ephemeral=True)
        return
    
    target = member or interaction.user
    inv_data = get_invite_user(interaction.guild.id, target.id)
    
    embed = discord.Embed(
        title=f"📊 إحصائيات الدعوات — {target.display_name}",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="👥 عدد الدعوات", value=f"**{inv_data['invited_count']}**", inline=True)
    embed.add_field(name="💰 إجمالي الكريدت", value=f"**{inv_data['total_earned']:,}**", inline=True)
    embed.add_field(name="💎 المكافأة لكل دعوة", value=f"**{INVITE_REWARD}** كريدت", inline=True)
    
    # آخر 5 دعوات
    if inv_data["invited_members"]:
        recent = inv_data["invited_members"][-5:]
        recent.reverse()
        recent_text = ""
        for inv in recent:
            date = datetime.fromisoformat(inv["date"]).strftime("%Y-%m-%d")
            recent_text += f"> 👤 **{inv['name']}** — {date}\n"
        embed.add_field(name="📋 آخر الدعوات", value=recent_text, inline=False)
    
    embed.set_footer(text="Invite System")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="invite_leaderboard", description="🏆 لوحة متصدرين الدعوات")
async def slash_invite_leaderboard(interaction: discord.Interaction):
    can_use, remaining = check_global_cooldown(interaction.user.id)
    if not can_use:
        await interaction.response.send_message(f"⏳ انتظر {remaining:.1f} ثانية!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    # ترتيب حسب عدد الدعوات
    guild_invite_data = invite_data.get(str(interaction.guild.id), {})
    sorted_inviters = sorted(
        [(uid, data) for uid, data in guild_invite_data.items() if isinstance(data, dict) and data.get("invited_count", 0) > 0],
        key=lambda x: x[1]["invited_count"],
        reverse=True
    )[:10]
    
    if not sorted_inviters:
        await interaction.followup.send(
            embed=discord.Embed(
                title="🏆 لوحة متصدرين الدعوات",
                description="مفيش دعوات لسه! كن أول واحد يدعي حد 📨",
                color=discord.Color.gold()
            )
        )
        return
    
    # تحويل الداتا لقائمة (member, inv_data)
    inviters_list = []
    for uid, data in sorted_inviters:
        try:
            member_obj = interaction.guild.get_member(int(uid))
            if member_obj:
                inviters_list.append((member_obj, data))
        except:
            pass
    
    if not inviters_list:
        await interaction.followup.send(
            embed=discord.Embed(
                title="🏆 لوحة متصدرين الدعوات",
                description="مفيش دعوات لسه! كن أول واحد يدعي حد 📨",
                color=discord.Color.gold()
            )
        )
        return
    
    try:
        img_buffer = await create_invite_leaderboard_image(inviters_list, interaction.guild)
        file = discord.File(img_buffer, filename="invite_leaderboard.png")
        await interaction.followup.send(file=file)
    except Exception as e:
        print(f"Error creating invite leaderboard image: {e}")
        # Fallback to embed
        embed = discord.Embed(
            title="🏆 لوحة متصدرين الدعوات",
            description="أكتر ناس دعوا أعضاء للسيرفر!",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        for i, (member_obj, data) in enumerate(inviters_list, 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"#{i}")
            embed.add_field(
                name=f"{medal} {member_obj.display_name}",
                value=f"👥 **{data['invited_count']}** دعوة | 💰 **{data['total_earned']:,}** كريدت",
                inline=False
            )
        embed.set_footer(text="Invite System — شارك واكسب!")
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="rank", description="📊 عرض رانكك")
@app_commands.describe(member="العضو (اختياري)")
async def slash_rank(interaction: discord.Interaction, member: discord.Member = None):
    can_use, remaining = check_global_cooldown(interaction.user.id)
    if not can_use:
        await interaction.response.send_message(f"⏳ انتظر {remaining:.1f} ثانية!", ephemeral=True)
        return
        
    await interaction.response.defer()
    target = member or interaction.user
    if target.bot:
        await interaction.followup.send("❌ البوتات مالهاش رانك!", ephemeral=True)
        return
    
    user = get_user_data(interaction.guild.id, target.id)
    try:
        img_buffer = await create_rank_card(user, target, interaction.guild)
        file = discord.File(img_buffer, filename="rank.png")
        await interaction.followup.send(file=file)
    except Exception as e:
        print(f"Error: {e}")
        await interaction.followup.send(f"📊 {target.display_name} | Level {user['level']} | XP: {user['xp']}")

@bot.tree.command(name="leaderboard", description="🏆 لوحة المتصدرين")
@app_commands.describe(limit="عدد الأشخاص (5-20)")
async def slash_leaderboard(interaction: discord.Interaction, limit: int = 10):
    can_use, remaining = check_global_cooldown(interaction.user.id)
    if not can_use:
        await interaction.response.send_message(f"⏳ انتظر {remaining:.1f} ثانية!", ephemeral=True)
        return
        
    await interaction.response.defer()
    limit = max(5, min(20, limit))
    
    all_users = []
    guild_user_data = user_data.get(str(interaction.guild.id), {})
    for uid, data in guild_user_data.items():
        if not isinstance(data, dict):
            continue
        try:
            member = interaction.guild.get_member(int(uid))
            if member and not member.bot:
                all_users.append((member, data))
        except:
            pass
    
    all_users.sort(key=lambda x: x[1]["xp"], reverse=True)
    all_users = all_users[:limit]
    
    try:
        img_buffer = await create_leaderboard_image(all_users, interaction.guild)
        file = discord.File(img_buffer, filename="leaderboard.png")
        await interaction.followup.send(file=file)
    except Exception as e:
        print(f"Leaderboard image error: {e}")
        # Fallback to embed if image fails
        embed = discord.Embed(title="🏆 لوحة المتصدرين", description=f"أفضل {len(all_users)} عضو", color=discord.Color.gold())
        for i, (member, data) in enumerate(all_users, 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"#{i}")
            embed.add_field(name=f"{medal} {member.display_name}", value=f"Level {data['level']} | {data['xp']} XP | {data['credits']} 💰", inline=False)
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="credits", description="💰 عرض رصيدك")
@app_commands.describe(member="العضو (اختياري)")
async def slash_credits(interaction: discord.Interaction, member: discord.Member = None):
    can_use, remaining = check_global_cooldown(interaction.user.id)
    if not can_use:
        await interaction.response.send_message(f"⏳ انتظر {remaining:.1f} ثانية!", ephemeral=True)
        return
        
    await interaction.response.defer()
    target = member or interaction.user
    user = get_user_data(interaction.guild.id, target.id)
    await interaction.followup.send(f"💰 رصيد {target.mention}: **{user['credits']}** كريدت")

@bot.tree.command(name="warnings", description="⚠️ عرض تحذيرات عضو مع الأسباب والوقت المتبقي")
@app_commands.describe(member="العضو (اختياري)")
async def slash_warnings(interaction: discord.Interaction, member: discord.Member = None):
    can_use, remaining = check_global_cooldown(interaction.user.id)
    if not can_use:
        await interaction.response.send_message(f"⏳ انتظر {remaining:.1f} ثانية!", ephemeral=True)
        return
        
    await interaction.response.defer()
    target = member or interaction.user
    user_warnings = get_user_warnings(interaction.guild.id, target.id)
    user = get_user_data(interaction.guild.id, target.id)
    
    embed = discord.Embed(title=f"⚠️ تحذيرات {target.display_name}", description=f"عدد التحذيرات: **{len(user_warnings)}/4**", color=discord.Color.orange())
    embed.set_thumbnail(url=target.display_avatar.url)
    
    if user_warnings:
        for i, warning in enumerate(user_warnings[-4:], 1):
            date = datetime.fromisoformat(warning['date']).strftime("%Y-%m-%d %H:%M")
            embed.add_field(name=f"تحذير #{i}", value=f"**السبب:** {warning['reason']}\n**من:** <@{warning['moderator']}>\n**التاريخ:** {date}", inline=False)
        
        last_warning = user_warnings[-1]
        last_date = datetime.fromisoformat(last_warning['date'])
        expiry_date = last_date + timedelta(days=7)
        time_left = expiry_date - datetime.now()
        
        if time_left.total_seconds() > 0:
            days_left = time_left.days
            hours_left = time_left.seconds // 3600
            minutes_left = (time_left.seconds % 3600) // 60
            
            if days_left > 0:
                time_text = f"{days_left} يوم و {hours_left} ساعة و {minutes_left} دقيقة"
            elif hours_left > 0:
                time_text = f"{hours_left} ساعة و {minutes_left} دقيقة"
            else:
                time_text = f"{minutes_left} دقيقة"
            
            embed.add_field(name="⏰ يتم ازالة كل التحذيرات بعد", value=f"{time_text}", inline=False)
    else:
        embed.add_field(name="✅", value="مفيش تحذيرات!", inline=False)
    
    status = "🟢 آمن"
    if user['warnings'] == 1:
        status = "🟡 تحذير أول"
    elif user['warnings'] == 2:
        status = "🟠 تحذير ثاني (تايم اوت 10 دق)"
    elif user['warnings'] == 3:
        status = "🔴 تحذير ثالث (تايم اوت 30 دق)"
    elif user['warnings'] >= 4:
        status = "⛔ تحذير رابع (Reset Level)"
    
    embed.add_field(name="📊 الحالة الحالية", value=status, inline=False)
    await interaction.followup.send(embed=embed)

# ========== أوامر الأدمن والمودريشن + إعدادات اللوجز + إعدادات الإمبد ==========

RULES_EMBED = discord.Embed(
    title=".Kingdom's rules:",
    description=
    "<:line:1444508770649636924>\n\n"

    "**1 \u2022** <:rules:1444435371654909952> **\u0627\u062d\u062a\u0631\u0645 \u0627\u0644\u0627\u062e\u0631\u064a\u0646**\n"
    "\u0644\u0627 \u062a\u062a\u0646\u0645\u0631, \u0627\u0648 \u0636\u064a\u0642, \u0627\u0648 \u062a\u062a\u0639\u0627\u0635\u0631, \u0627\u0648 \u062a\u0627\u062e\u062f \u0634\u062e\u0635 \u0645\u062d\u062a\u0648\u0649 \u0648 \u062a\u0647\u064a\u0646 \u0641\u064a\u0647 \u0628\u0634\u0643\u0644 \u0633\u064a\u0626, \u0639\u0627\u0645\u0644 "
    "\u0627\u0644\u0646\u0627\u0633 \u0643\u0645\u0627 \u062a\u062d\u0628 \u0627\u0646 \u062a\u0639\u0627\u0645\u0644\n\n"

    "<:line:1444508770649636924>\n\n"

    "**2 \u2022** <:rules:1444435371654909952> **\u062e\u0644\u064a \u0627\u0644\u0634\u0627\u062a \u0646\u0636\u064a\u0641**\n"
    "\u0627\u0644\u0633\u0628\u0627\u0645 \u0648 \u0627\u0644\u0631\u0633\u0627\u0626\u0644 \u0627\u0644\u0645\u0637\u0648\u0644\u0629 \u0627\u0648 \u0627\u0644\u0644\u064a\u0646\u0643\u0627\u062a \u0645\u0645\u0646\u0648\u0639\u0629\n\n"

    "<:line:1444508770649636924>\n\n"

    "**3 \u2022** <:rules:1444435371654909952> **\u0644\u0627\u062a\u062a\u0631\u062c\u064a \u0639\u0644\u064a \u0631\u062a\u0628**\n"
    "\u0644\u0627 \u062a\u062a\u0648\u0633\u0644 \u0627\u0644\u0633\u062a\u0627\u0641 \u0639\u0644\u0649 \u0631\u062a\u0628 \u0627\u0648 \u062a\u0632\u0639\u062c\u0647\u0645\n\n"

    "<:line:1444508770649636924>\n\n"

    "**4 \u2022** <:rules:1444435371654909952> **\u0643\u0646 \u0631\u062c\u0644**\n"
    "\u063a\u064a\u0631 \u0645\u0633\u0645\u0648\u062d \u0627\u0644\u0645\u0639\u0627\u0643\u0633\u0629, \u0627\u0648 \u0627\u0644\u0633\u0645\u0628\u0646\u0647, \u0627\u0648 \u0627\u0646\u0643 \u062a\u062e\u0644\u064a \u0627\u064a \u0628\u0646\u062a \u062a\u0634\u0639\u0631 \u0628\u0639\u062f\u0645 \u0627\u0631\u062a\u064a\u0627\u062d\n\n"

    "<:line:1444508770649636924>\n\n"

    "**5 \u2022** <:rules:1444435371654909952> **\u0627\u0628\u062a\u0639\u062f \u0639\u0646 \u0627\u0644\u0645\u0632\u0627\u062d \u0627\u0644\u062f\u064a\u0646\u064a \u0648 \u0627\u0644\u0633\u064a\u0627\u0633\u064a**\n"
    "\u0627\u062d\u062a\u0631\u0645 \u0627\u062e\u0648\u0643 \u0627\u0644\u0645\u0633\u064a\u062d\u064a \u0627\u0648 \u0627\u0644\u0645\u0633\u0644\u0645 \u0627\u0648 \u0627\u064a\u0627 \u0643\u0627\u0646\u062a \u062f\u064a\u0627\u0646\u062a\u0647, \u0645\u062a\u0647\u0632\u0631\u0634 \u0639\u0644\u0649 \u0645\u0639\u062a\u0642\u062f\u0627\u062a\u0647\u0645 \u0628\u0623\u064a \u0634\u0643\u0644 "
    "\u0645\u0646 \u0627\u0644\u0627\u0634\u0643\u0627\u0644, \u0648 \u064a\u062c\u0628 \u0627\u0644\u062a\u062d\u062f\u062b \u0641\u064a \u0627\u0644\u0633\u064a\u0627\u0633\u0629 \u0628\u0634\u0643\u0644 \u0645\u0628\u0627\u0644\u063a \u0641\u064a\u0647\n\n"

    "<:line:1444508770649636924>\n\n"

    "**6 \u2022** <:rules:1444435371654909952> **\u0627\u0644\u0645\u062d\u062a\u0648\u064a \u0627\u0644\u0627\u0628\u0627\u062d\u064a**\n"
    "\u063a\u064a\u0631 \u0645\u0633\u0645\u0648\u062d \u0627\u0628\u062f\u0627 \u0628\u0646\u0634\u0631 \u0627\u064a \u0645\u062d\u062a\u0648\u064a \u063a\u064a\u0631 \u0627\u062e\u0644\u0627\u0642\u064a, \u064a\u062a\u0636\u0645\u0646 \u0643\u0644 \u0645\u0646 : \u0635\u0648\u0631, \u0645\u0644\u0635\u0642\u0627\u062a, "
    "\u0631\u0633\u0627\u0626\u0644, \u0631\u0648\u0627\u0628\u0637, \u0635\u0648\u0631\u062a\u0643, \u0627\u0633\u0645\u0643, \u0627\u0648 \u062d\u062a\u064a \u0627\u064a \u0634\u064a \u0627\u062e\u0631 \u064a\u0648\u062c\u062f \u0628\u0647 \u0627\u064a \u0646\u0648\u0639 \u0645\u0646 \u0627\u0646\u0648\u0627\u0639 "
    "\u0627\u0644\u0645\u062d\u062a\u0648\u064a \u0627\u0644\u063a\u064a\u0631 \u0644\u0627\u0626\u0642\n\n"

    "<:line:1444508770649636924>\n\n"

    "**7 \u2022** <:rules:1444435371654909952> **\u0644\u0627 \u062a\u0631\u0648\u062c \u0644\u0633\u064a\u0631\u0641\u0631\u0627\u062a \u0627\u062e\u0631\u064a \u0627\u0648 \u0639\u0645\u0644\u0643 \u0627\u0644\u062e\u0627\u0635**\n"
    "\u063a\u064a\u0631 \u0645\u0633\u0645\u0648\u062d \u0628\u0627\u0644\u062a\u0631\u0648\u064a\u062c \u0644\u0633\u064a\u0631\u0641\u0631\u0643 \u0627\u0648 \u0644\u0645\u0644\u0643\u0643 \u0627\u0648 \u0627\u064a \u0634\u064a \u0627\u062e\u0631, \u0644\u0627 \u062f\u0627\u062e\u0644 \u0627\u0644\u0633\u064a\u0631\u0641\u0631 \u0648\u0644\u0627 \u062d\u062a\u064a \u0641\u064a "
    "\u0627\u0644\u062e\u0627\u0635",
    color=discord.Color.dark_grey(),
    timestamp=datetime.now()
)

AVAILABLE_PERMISSIONS = [
    "warn", "timeout", "warnings", "untimeout", 
    "mute", "unmute", "kick", "ban", "unban", 
    "clear", "role", "prison", "unprison",
    "comp_win", "comp_leaderboard", "ticket", "talk",
    "lead_reset", "lock", "unlock"
]

class PermissionSelect(Select):
    def __init__(self, role: discord.Role, current_perms: dict):
        options = []
        for perm in AVAILABLE_PERMISSIONS:
            is_enabled = current_perms.get(perm, False)
            emoji = "✅" if is_enabled else "❌"
            options.append(discord.SelectOption(
                label=f"{perm.replace('_', ' ').title()}",
                value=perm,
                description=f"{'مفعل' if is_enabled else 'معطل'} - اضغط للتبديل",
                emoji=emoji,
                default=is_enabled
            ))
        
        super().__init__(
            placeholder="اختر الصلاحيات لتفعيلها/تعطيلها",
            min_values=1,
            max_values=len(AVAILABLE_PERMISSIONS),
            options=options
        )
        self.role = role
        self.current_perms = current_perms.copy()

    async def callback(self, interaction: discord.Interaction):
        selected = self.values
        
        for perm in AVAILABLE_PERMISSIONS:
            if perm in selected:
                self.current_perms[perm] = not self.current_perms.get(perm, False)
        
        set_role_permissions(interaction.guild.id, self.role.id, self.current_perms)
        
        enabled = [p for p, v in self.current_perms.items() if v]
        disabled = [p for p, v in self.current_perms.items() if not v]
        
        embed = discord.Embed(
            title=f"✅ تم تحديث صلاحيات {self.role.name}",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        if enabled:
            embed.add_field(
                name="✅ الصلاحيات المفعلة",
                value=", ".join([f"`{p}`" for p in enabled]),
                inline=False
            )
        if disabled:
            embed.add_field(
                name="❌ الصلاحيات المعطلة",
                value=", ".join([f"`{p}`" for p in disabled]) or "لا يوجد",
                inline=False
            )
        
        view = RolePermissionsView(self.role, self.current_perms)
        await interaction.response.edit_message(embed=embed, view=view)

class RolePermissionsView(View):
    def __init__(self, role: discord.Role, current_perms: dict):
        super().__init__(timeout=180)
        self.role = role
        self.add_item(PermissionSelect(role, current_perms))
        self.add_item(SavePermissionsButton(role, current_perms))
        self.add_item(CancelButton())

class SavePermissionsButton(Button):
    def __init__(self, role: discord.Role, perms: dict):
        super().__init__(
            label="حفظ وخروج",
            style=discord.ButtonStyle.success,
            emoji="💾"
        )
        self.role = role
        self.perms = perms

    async def callback(self, interaction: discord.Interaction):
        enabled = [p for p, v in self.perms.items() if v]
        embed = discord.Embed(
            title="✅ تم الحفظ بنجاح",
            description=f"تم حفظ صلاحيات رتبة {self.role.mention}",
            color=discord.Color.green()
        )
        if enabled:
            embed.add_field(
                name="الصلاحيات المفعلة",
                value=", ".join([f"`{p}`" for p in enabled]),
                inline=False
            )
        await interaction.response.edit_message(embed=embed, view=None)

class CancelButton(Button):
    def __init__(self):
        super().__init__(
            label="إلغاء",
            style=discord.ButtonStyle.danger,
            emoji="❌"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content="❌ تم إلغاء العملية",
            embed=None,
            view=None
        )

class InfoEmbedsView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="🚀 Booster Perks", style=discord.ButtonStyle.primary, emoji="🚀", custom_id="info:booster_perks", row=0)
    async def booster_perks_btn(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title="🚀 Booster Perks - مميزات البوستر",
            description="لو عملت بوست للسيرفر هتكون ايه مميزاتك؟",
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="1 • 💰 خصم 25% على الشوب",
            value="يتضمن كل شي موجود في الشوب ✅",
            inline=False
        )
        embed.add_field(
            name="2 • ⚡ زيادة 1.5x XP",
            value="يعني بتجمع XP اسرع من اي حد ✅",
            inline=False
        )
        embed.add_field(
            name="3 • 🎭 رول مميزه مش عند اي حد",
            value="@.wealthy ✅",
            inline=False
        )
        embed.add_field(
            name="4 • 🎁 جميع مميزات اللفلات",
            value="و كله من غير ما تلفل بما فيهم رول باي اسم و شكل انت عاوزه ✅",
            inline=False
        )
        embed.add_field(
            name="5 • 👑 هيكون ليك معامله خاصه جدا",
            value="<:special:1486339688422834206> ✅",
            inline=False
        )
        
        embed.set_footer(text="شكراً لدعمك السيرفر! 💜")
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="📋 Roles Info", style=discord.ButtonStyle.secondary, emoji="📋", custom_id="info:roles_info", row=0)
    async def roles_info_btn(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title="📋 Roles Info - معلومات عن الرتب",
            description="الرتب في السيرفر بتيجي من نظام اللفل (Level System)",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="🎯 ازاي تجمع XP؟",
            value="• تكلم في الشات\n• اقعد في الرومات الصوتية\n• اشتري Double XP من الشوب",
            inline=False
        )
        
        embed.add_field(
            name="🏆 الرتب حسب اللفل",
            value="• **Level 5** - Send GIFs and pictures\n"
                  "• **Level 10** - Send voice messages\n"
                  "• **Level 15** - A Role\n"
                  "• **Level 20** - Create threads\n"
                  "• **Level 25** - Change Nicknames\n"
                  "• **Level 30** - Create polls\n"
                  "• **Level 35** - Priority speaker\n"
                  "• **Level 40** - A Role\n"
                  "• **Level 50** - Soundboard perm\n"
                  "• **Level 60** - 1k Lake credits (that you can use in shop)\n"
                  "• **Level 70** - You will get a special treatment <:special:1486339688422834206>\n"
                  "• **Level 80** - A Role\n"
                  "• **Level 90** - مش عارف يسطا انت معندكش حياة الصراحة\n"
                  "• **Level 100** - Custom role with custom color, icon, and name 👑",
            inline=False
        )
        
        embed.add_field(
            name="💡 نصيحة",
            value="كل ما تلفل أكتر، كل ما تاخد مميزات أكتر وكريدت أكتر! 🔥",
            inline=False
        )
        
        embed.set_footer(text="استخدم /rank عشان تشوف رانكك")
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Rules", style=discord.ButtonStyle.danger, emoji="📜", custom_id="info:rules", row=0)
    async def rules_btn(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title=".Kingdom's rules:",
            description=
            "<:line:1444508770649636924>\n\n"

            "**1 \u2022** <:rules:1444435371654909952> **\u0627\u062d\u062a\u0631\u0645 \u0627\u0644\u0627\u062e\u0631\u064a\u0646**\n"
            "\u0644\u0627 \u062a\u062a\u0646\u0645\u0631, \u0627\u0648 \u0636\u064a\u0642, \u0627\u0648 \u062a\u062a\u0639\u0627\u0635\u0631, \u0627\u0648 \u062a\u0627\u062e\u062f \u0634\u062e\u0635 \u0645\u062d\u062a\u0648\u0649 \u0648 \u062a\u0647\u064a\u0646 \u0641\u064a\u0647 \u0628\u0634\u0643\u0644 \u0633\u064a\u0626, \u0639\u0627\u0645\u0644 "
            "\u0627\u0644\u0646\u0627\u0633 \u0643\u0645\u0627 \u062a\u062d\u0628 \u0627\u0646 \u062a\u0639\u0627\u0645\u0644\n\n"

            "<:line:1444508770649636924>\n\n"

            "**2 \u2022** <:rules:1444435371654909952> **\u062e\u0644\u064a \u0627\u0644\u0634\u0627\u062a \u0646\u0636\u064a\u0641**\n"
            "\u0627\u0644\u0633\u0628\u0627\u0645 \u0648 \u0627\u0644\u0631\u0633\u0627\u0626\u0644 \u0627\u0644\u0645\u0637\u0648\u0644\u0629 \u0627\u0648 \u0627\u0644\u0644\u064a\u0646\u0643\u0627\u062a \u0645\u0645\u0646\u0648\u0639\u0629\n\n"

            "<:line:1444508770649636924>\n\n"

            "**3 \u2022** <:rules:1444435371654909952> **\u0644\u0627\u062a\u062a\u0631\u062c\u064a \u0639\u0644\u064a \u0631\u062a\u0628**\n"
            "\u0644\u0627 \u062a\u062a\u0648\u0633\u0644 \u0627\u0644\u0633\u062a\u0627\u0641 \u0639\u0644\u0649 \u0631\u062a\u0628 \u0627\u0648 \u062a\u0632\u0639\u062c\u0647\u0645\n\n"

            "<:line:1444508770649636924>\n\n"

            "**4 \u2022** <:rules:1444435371654909952> **\u0643\u0646 \u0631\u062c\u0644**\n"
            "\u063a\u064a\u0631 \u0645\u0633\u0645\u0648\u062d \u0627\u0644\u0645\u0639\u0627\u0643\u0633\u0629, \u0627\u0648 \u0627\u0644\u0633\u0645\u0628\u0646\u0647, \u0627\u0648 \u0627\u0646\u0643 \u062a\u062e\u0644\u064a \u0627\u064a \u0628\u0646\u062a \u062a\u0634\u0639\u0631 \u0628\u0639\u062f\u0645 \u0627\u0631\u062a\u064a\u0627\u062d\n\n"

            "<:line:1444508770649636924>\n\n"

            "**5 \u2022** <:rules:1444435371654909952> **\u0627\u0628\u062a\u0639\u062f \u0639\u0646 \u0627\u0644\u0645\u0632\u0627\u062d \u0627\u0644\u062f\u064a\u0646\u064a \u0648 \u0627\u0644\u0633\u064a\u0627\u0633\u064a**\n"
            "\u0627\u062d\u062a\u0631\u0645 \u0627\u062e\u0648\u0643 \u0627\u0644\u0645\u0633\u064a\u062d\u064a \u0627\u0648 \u0627\u0644\u0645\u0633\u0644\u0645 \u0627\u0648 \u0627\u064a\u0627 \u0643\u0627\u0646\u062a \u062f\u064a\u0627\u0646\u062a\u0647, \u0645\u062a\u0647\u0632\u0631\u0634 \u0639\u0644\u0649 \u0645\u0639\u062a\u0642\u062f\u0627\u062a\u0647\u0645 \u0628\u0623\u064a \u0634\u0643\u0644 "
            "\u0645\u0646 \u0627\u0644\u0627\u0634\u0643\u0627\u0644, \u0648 \u064a\u062c\u0628 \u0627\u0644\u062a\u062d\u062f\u062b \u0641\u064a \u0627\u0644\u0633\u064a\u0627\u0633\u0629 \u0628\u0634\u0643\u0644 \u0645\u0628\u0627\u0644\u063a \u0641\u064a\u0647\n\n"

            "<:line:1444508770649636924>\n\n"

            "**6 \u2022** <:rules:1444435371654909952> **\u0627\u0644\u0645\u062d\u062a\u0648\u064a \u0627\u0644\u0627\u0628\u0627\u062d\u064a**\n"
            "\u063a\u064a\u0631 \u0645\u0633\u0645\u0648\u062d \u0627\u0628\u062f\u0627 \u0628\u0646\u0634\u0631 \u0627\u064a \u0645\u062d\u062a\u0648\u064a \u063a\u064a\u0631 \u0627\u062e\u0644\u0627\u0642\u064a, \u064a\u062a\u0636\u0645\u0646 \u0643\u0644 \u0645\u0646 : \u0635\u0648\u0631, \u0645\u0644\u0635\u0642\u0627\u062a, "
            "\u0631\u0633\u0627\u0626\u0644, \u0631\u0648\u0627\u0628\u0637, \u0635\u0648\u0631\u062a\u0643, \u0627\u0633\u0645\u0643, \u0627\u0648 \u062d\u062a\u064a \u0627\u064a \u0634\u064a \u0627\u062e\u0631 \u064a\u0648\u062c\u062f \u0628\u0647 \u0627\u064a \u0646\u0648\u0639 \u0645\u0646 \u0627\u0646\u0648\u0627\u0639 "
            "\u0627\u0644\u0645\u062d\u062a\u0648\u064a \u0627\u0644\u063a\u064a\u0631 \u0644\u0627\u0626\u0642\n\n"

            "<:line:1444508770649636924>\n\n"

            "**7 \u2022** <:rules:1444435371654909952> **\u0644\u0627 \u062a\u0631\u0648\u062c \u0644\u0633\u064a\u0631\u0641\u0631\u0627\u062a \u0627\u062e\u0631\u064a \u0627\u0648 \u0639\u0645\u0644\u0643 \u0627\u0644\u062e\u0627\u0635**\n"
            "\u063a\u064a\u0631 \u0645\u0633\u0645\u0648\u062d \u0628\u0627\u0644\u062a\u0631\u0648\u064a\u062c \u0644\u0633\u064a\u0631\u0641\u0631\u0643 \u0627\u0648 \u0644\u0645\u0644\u0643\u0643 \u0627\u0648 \u0627\u064a \u0634\u064a \u0627\u062e\u0631, \u0644\u0627 \u062f\u0627\u062e\u0644 \u0627\u0644\u0633\u064a\u0631\u0641\u0631 \u0648\u0644\u0627 \u062d\u062a\u064a \u0641\u064a "
            "\u0627\u0644\u062e\u0627\u0635",
            color=discord.Color.dark_grey(),
            timestamp=datetime.now()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="setup_embeds", description="📜 إرسال إمبد المعلومات مع الأزرار (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(channel="الشانل")
@app_commands.checks.has_permissions(administrator=True)
async def slash_setup_embeds(interaction: discord.Interaction, channel: discord.TextChannel):
    try:
        embed = discord.Embed(
            title="📚 معلومات السيرفر",
            description=(
                "**أهلاً بيك في السيرفر!** 🎉\n"
                "هنا هتلاقي كل المعلومات اللي محتاجها.\n"
                "اضغط على الأزرار تحت عشان تعرف أكتر! 👇"
            ),
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        embed.add_field(
            name="🚀 Booster Perks",
            value="> اعرف مميزات البوستر والخصومات",
            inline=True
        )
        embed.add_field(
            name="📋 Roles Info",
            value="> معلومات عن الرتب ونظام اللفل",
            inline=True
        )
        embed.add_field(
            name="📜 Rules",
            value="> قوانين السيرفر اللي لازم تعرفها",
            inline=True
        )
        embed.set_footer(text="اختار اللي تحبه من تحت 👇")
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        
        view = InfoEmbedsView()
        await channel.send(embed=embed, view=view)
        
        confirm = discord.Embed(
            title="✅ تم الإرسال",
            description=f"تم إرسال الإمبد في {channel.mention}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=confirm, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ حصل خطأ: {e}", ephemeral=True)

@bot.tree.command(name="setup_boost_notification", description="🚀 إعداد روم نوتيفيكيشن البوست (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(channel="الروم")
@app_commands.checks.has_permissions(administrator=True)
async def slash_setup_boost_notification(interaction: discord.Interaction, channel: discord.TextChannel):
    cfg = load_guild_config()
    if str(interaction.guild.id) not in cfg:
        cfg[str(interaction.guild.id)] = {}
    cfg[str(interaction.guild.id)]["boost_channel"] = channel.id
    save_guild_config(cfg)
    
    embed = discord.Embed(
        title="✅ تم الإعداد",
        description=f"روم نوتيفيكيشن البوست: {channel.mention}",
        color=discord.Color.purple()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="setup_command_roles", description="⚙️ إعداد صلاحيات الرتب للأوامر الإدارية (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(role="الرتبة التي تريد إعداد صلاحياتها")
@app_commands.checks.has_permissions(administrator=True)
async def slash_setup_command_roles(interaction: discord.Interaction, role: discord.Role):
    await interaction.response.defer(ephemeral=True)
    
    current_perms = get_role_permissions(interaction.guild.id, role.id)
    
    enabled = [p for p, v in current_perms.items() if v]
    disabled = [p for p, v in current_perms.items() if not v]
    
    embed = discord.Embed(
        title=f"⚙️ إعداد صلاحيات {role.name}",
        description=f"اختر الصلاحيات من القائمة أدناه\n\n"
                   f"📝 **ملاحظة:** اضغط على الصلاحية لتفعيلها/تعطيلها\n"
                   f"يمكنك اختيار أكثر من صلاحية في نفس الوقت",
        color=discord.Color.blue()
    )
    
    if enabled:
        embed.add_field(
            name="✅ الصلاحيات المفعلة حالياً",
            value=", ".join([f"`{p}`" for p in enabled]),
            inline=False
        )
    else:
        embed.add_field(
            name="⚠️ تنبيه",
            value="لا توجد صلاحيات مفعلة لهذه الرتبة حالياً",
            inline=False
        )
    
    view = RolePermissionsView(role, current_perms)
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="view_role_permissions", description="👁️ عرض صلاحيات رتبة معينة (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(role="الرتبة")
@app_commands.checks.has_permissions(administrator=True)
async def slash_view_role_permissions(interaction: discord.Interaction, role: discord.Role):
    await interaction.response.defer(ephemeral=True)
    
    perms = get_role_permissions(interaction.guild.id, role.id)
    enabled = [p for p, v in perms.items() if v]
    disabled = [p for p in AVAILABLE_PERMISSIONS if not perms.get(p, False)]
    
    embed = discord.Embed(
        title=f"👁️ صلاحيات {role.name}",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    if enabled:
        embed.add_field(
            name="✅ مفعلة",
            value="\n".join([f"• `{p}`" for p in enabled]),
            inline=True
        )
    if disabled:
        embed.add_field(
            name="❌ معطلة",
            value="\n".join([f"• `{p}`" for p in disabled]),
            inline=True
        )
    
    members_with_role = [m for m in interaction.guild.members if role in m.roles and not m.bot]
    if members_with_role:
        member_list = ", ".join([m.mention for m in members_with_role[:5]])
        if len(members_with_role) > 5:
            member_list += f" و {len(members_with_role) - 5} آخرين"
        embed.add_field(
            name=f"👥 أعضاء الرتبة ({len(members_with_role)})",
            value=member_list,
            inline=False
        )
    
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="remove_role_permissions", description="🗑️ إزالة جميع صلاحيات رتبة (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(role="الرتبة", confirm="اكتب CONFIRM للتأكيد")
@app_commands.checks.has_permissions(administrator=True)
async def slash_remove_role_permissions(interaction: discord.Interaction, role: discord.Role, confirm: str = None):
    await interaction.response.defer(ephemeral=True)
    
    if confirm != "CONFIRM":
        await interaction.followup.send(
            f"⚠️ هل أنت متأكد من إزالة جميع صلاحيات رتبة {role.mention}؟\n"
            f"اكتب `CONFIRM` في خيار confirm لتأكيد العملية.",
            ephemeral=True
        )
        return
    
    cfg = load_roles_config()
    if str(interaction.guild.id) in cfg and str(role.id) in cfg[str(interaction.guild.id)]:
        del cfg[str(interaction.guild.id)][str(role.id)]
        save_roles_config(cfg)
        
        embed = discord.Embed(
            title="✅ تم الإزالة",
            description=f"تم إزالة جميع صلاحيات رتبة {role.mention} بنجاح",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        await interaction.followup.send(
            f"ℹ️ رتبة {role.mention} ليس لديها صلاحيات مخصصة أصلاً",
            ephemeral=True
        )

@bot.tree.command(name="setup_embed", description="📜 إرسال إمبد القوانين في شانل معين (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(channel="الشانل اللي هتتبعت فيه الإمبد")
@app_commands.checks.has_permissions(administrator=True)
async def slash_setup_embed(interaction: discord.Interaction, channel: discord.TextChannel):
    try:
        await channel.send(embed=RULES_EMBED)
        
        embed = discord.Embed(
            title="✅ تم الإرسال",
            description=f"تم إرسال إمبد القوانين في {channel.mention}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ البوت ما عندوش صلاحية يرسل في الشانل ده!", 
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ حصل خطأ: {e}", 
            ephemeral=True
        )

@bot.tree.command(name="setup_log_msg", description="📝 إعداد روم لوج الرسائل (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(channel="الروم")
@app_commands.checks.has_permissions(administrator=True)
async def slash_setup_log_msg(interaction: discord.Interaction, channel: discord.TextChannel):
    set_log_channel(interaction.guild.id, "msg", channel.id)
    embed = discord.Embed(
        title="✅ تم الإعداد",
        description=f"روم لوج الرسائل: {channel.mention}",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="setup_log_shop", description="🛒 إعداد روم لوج المشتريات (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(channel="الروم")
@app_commands.checks.has_permissions(administrator=True)
async def slash_setup_log_shop(interaction: discord.Interaction, channel: discord.TextChannel):
    set_log_channel(interaction.guild.id, "shop", channel.id)
    embed = discord.Embed(
        title="✅ تم الإعداد",
        description=f"روم لوج المشتريات: {channel.mention}",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="setup_log_ban", description="🔨 إعداد روم لوج الحظر (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(channel="الروم")
@app_commands.checks.has_permissions(administrator=True)
async def slash_setup_log_ban(interaction: discord.Interaction, channel: discord.TextChannel):
    set_log_channel(interaction.guild.id, "ban", channel.id)
    embed = discord.Embed(
        title="✅ تم الإعداد",
        description=f"روم لوج الحظر: {channel.mention}",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="setup_log_kick", description="👢 إعداد روم لوج الطرد (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(channel="الروم")
@app_commands.checks.has_permissions(administrator=True)
async def slash_setup_log_kick(interaction: discord.Interaction, channel: discord.TextChannel):
    set_log_channel(interaction.guild.id, "kick", channel.id)
    embed = discord.Embed(
        title="✅ تم الإعداد",
        description=f"روم لوج الطرد: {channel.mention}",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="setup_log_join_leave", description="🚪 إعداد روم لوج دخول/خروج الأعضاء (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(channel="الروم")
@app_commands.checks.has_permissions(administrator=True)
async def slash_setup_log_join_leave(interaction: discord.Interaction, channel: discord.TextChannel):
    set_log_channel(interaction.guild.id, "join_leave", channel.id)
    embed = discord.Embed(
        title="✅ تم الإعداد",
        description=f"روم لوج دخول/خروج الأعضاء: {channel.mention}",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="setup_timeout_mute_logs", description="⏱️ إعداد روم لوج التايم أوت والميوت (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(channel="الروم")
@app_commands.checks.has_permissions(administrator=True)
async def slash_setup_timeout_mute_logs(interaction: discord.Interaction, channel: discord.TextChannel):
    set_log_channel(interaction.guild.id, "timeout_mute", channel.id)
    embed = discord.Embed(
        title="✅ تم الإعداد",
        description=f"روم لوج التايم أوت والميوت: {channel.mention}",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="setup_welcome", description="👋 إعداد روم الترحيب بالأعضاء الجدد (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(channel="روم الترحيب")
@app_commands.checks.has_permissions(administrator=True)
async def slash_setup_welcome(interaction: discord.Interaction, channel: discord.TextChannel):
    cfg = load_guild_config()
    guild_id = str(interaction.guild.id)
    if guild_id not in cfg:
        cfg[guild_id] = {}
    cfg[guild_id]["welcome_channel"] = str(channel.id)
    save_guild_config(cfg)
    embed = discord.Embed(
        title="✅ تم الإعداد",
        description=f"روم الترحيب: {channel.mention}\nهيتبعت صورة ترحيب + منشن لأي عضو جديد يدخل السيرفر!",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="anti_cheat_enable", description="🛡️ تفعيل/تعطيل نظام مكافحة السبام (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(enabled="تفعيل (True) أو تعطيل (False)")
@app_commands.checks.has_permissions(administrator=True)
async def slash_anti_cheat_enable(interaction: discord.Interaction, enabled: bool):
    set_anti_cheat_enabled(interaction.guild.id, enabled)
    status = "✅ تم التفعيل" if enabled else "❌ تم التعطيل"
    embed = discord.Embed(
        title="🛡️ نظام مكافحة السبام",
        description=f"{status} بنجاح!",
        color=discord.Color.green() if enabled else discord.Color.red()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="dm", description="📨 إرسال رسالة خاصة لكل أعضاء السيرفر (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(message="الرسالة")
@app_commands.checks.has_permissions(administrator=True)
async def slash_dm(interaction: discord.Interaction, message: str):
    await interaction.response.defer(ephemeral=True)
    
    sent_count = 0
    failed_count = 0
    
    await interaction.followup.send("⏳ جاري الإرسال...", ephemeral=True)
    
    for member in interaction.guild.members:
        if member.bot:
            continue
        
        try:
            await member.send(f"📨 **رسالة من {interaction.guild.name}:**\n\n{message}\n\n- من {interaction.user.mention}")
            sent_count += 1
            await asyncio.sleep(0.5)
        except:
            failed_count += 1
    
    embed = discord.Embed(
        title="✅ تم الإرسال",
        description=f"**تم:** {sent_count}\n**فشل:** {failed_count}",
        color=discord.Color.green()
    )
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="lock", description="🔒 قفل الشات")
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(reason="السبب (اختياري)")
async def slash_lock(interaction: discord.Interaction, reason: str = None):
    if not (can_use_warn(interaction.user) or can_use_lock(interaction.user)):
        await interaction.response.send_message("❌ مالكش صلاحية!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    channel = interaction.channel
    default_role = interaction.guild.default_role
    current_overwrites = channel.overwrites_for(default_role)
    
    if current_overwrites.send_messages is False:
        await interaction.followup.send("❌ الشات مقفول أصلاً!", ephemeral=True)
        return
    
    current_overwrites.send_messages = False
    await channel.set_permissions(default_role, overwrite=current_overwrites)
    embed = discord.Embed(
        title="🔒 تم قفل الشات",
        description=f"**بواسطة:** {interaction.user.mention}",
        color=discord.Color.red()
    )
    if reason:
        embed.add_field(name="السبب", value=reason)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="unlock", description="🔓 فتح الشات")
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(reason="السبب (اختياري)")
async def slash_unlock(interaction: discord.Interaction, reason: str = None):
    if not (can_use_warn(interaction.user) or can_use_unlock(interaction.user)):
        await interaction.response.send_message("❌ مالكش صلاحية!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    channel = interaction.channel
    default_role = interaction.guild.default_role
    current_overwrites = channel.overwrites_for(default_role)
    
    if current_overwrites.send_messages is not False:
        await interaction.followup.send("❌ الشات مفتوح أصلاً!", ephemeral=True)
        return
    
    current_overwrites.send_messages = None
    await channel.set_permissions(default_role, overwrite=current_overwrites)
    embed = discord.Embed(
        title="🔓 تم فتح الشات",
        description=f"**بواسطة:** {interaction.user.mention}",
        color=discord.Color.green()
    )
    if reason:
        embed.add_field(name="السبب", value=reason)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="talk", description="🗣️ البوت يتكلم بدالك")
@app_commands.describe(message="الرسالة")
async def slash_talk(interaction: discord.Interaction, message: str):
    if not can_use_talk(interaction.user):
        await interaction.response.send_message("❌ مالكش صلاحية لاستخدام أمر talk!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        await interaction.channel.send(message)
        await interaction.followup.send("✅ تم!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ خطأ: {e}", ephemeral=True)

@bot.tree.command(name="ticket_setup", description="🎫 إعداد نظام التيكت (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def slash_ticket_setup(interaction: discord.Interaction):
    embed = discord.Embed(title="🎫 Support Tickets", description="Select an option below to open a ticket.", color=discord.Color.blue())
    
    # Load dynamic image from config first, fallback to local file
    dynamic_image_url = get_ticket_image_url(interaction.guild.id)
    file = None
    if dynamic_image_url:
        embed.set_image(url=dynamic_image_url)
    else:
        ticket_img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ticket_image.jpg")
        if os.path.exists(ticket_img_path):
            file = discord.File(ticket_img_path, filename="ticket_image.jpg")
            embed.set_image(url="attachment://ticket_image.jpg")
    
    view = TicketView()
    if file:
        msg = await interaction.response.send_message(embed=embed, file=file, view=view)
    else:
        msg = await interaction.response.send_message(embed=embed, view=view)
    
    # Save panel info for auto-updating later
    sent = await interaction.original_response()
    set_ticket_panel_info(interaction.guild.id, interaction.channel.id, sent.id)

@bot.tree.command(name="set_ticket_image", description="🖼️ تغيير صورة بانل التيكت (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(image_url="رابط الصورة الجديدة")
@app_commands.checks.has_permissions(administrator=True)
async def slash_set_ticket_image(interaction: discord.Interaction, image_url: str):
    await interaction.response.defer(ephemeral=True)
    
    # Validate URL format
    if not image_url.startswith(("http://", "https://")):
        await interaction.followup.send("❌ الرابط لازم يبدأ بـ http:// أو https://", ephemeral=True)
        return
    
    # Save the new image URL
    set_ticket_image_url(interaction.guild.id, image_url)
    
    # Try to auto-update the existing ticket panel message
    panel_channel_id, panel_message_id = get_ticket_panel_info(interaction.guild.id)
    panel_updated = False
    
    if panel_channel_id and panel_message_id:
        try:
            channel = interaction.guild.get_channel(int(panel_channel_id))
            if channel:
                msg = await channel.fetch_message(int(panel_message_id))
                if msg and msg.author.id == bot.user.id:
                    new_embed = discord.Embed(
                        title="🎫 Support Tickets",
                        description="Select an option below to open a ticket.",
                        color=discord.Color.blue()
                    )
                    new_embed.set_image(url=image_url)
                    view = TicketView()
                    await msg.edit(embed=new_embed, view=view, attachments=[])
                    panel_updated = True
        except Exception as e:
            print(f"Error updating ticket panel: {e}")
    
    if panel_updated:
        await interaction.followup.send(
            f"✅ تم تحديث صورة التيكت وتم تعديل البانل تلقائياً!\n🖼️ الصورة الجديدة: {image_url}",
            ephemeral=True
        )
    else:
        await interaction.followup.send(
            f"✅ تم حفظ صورة التيكت الجديدة!\n🖼️ الرابط: {image_url}\n⚠️ مفيش بانل تيكت محفوظ - استخدم `/ticket_setup` لإنشاء بانل جديد بالصورة.",
            ephemeral=True
        )

@bot.tree.command(name="level_mode_enable", description="⚙️ تفعيل/إيقاف نظام اللفل (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(enabled="تفعيل (True) أو إيقاف (False)")
@app_commands.checks.has_permissions(administrator=True)
async def slash_level_mode(interaction: discord.Interaction, enabled: bool):
    await interaction.response.defer()
    set_level_enabled(interaction.guild.id, enabled)
    status = "✅ تم التفعيل" if enabled else "❌ تم الإيقاف"
    embed = discord.Embed(title="⚙️ نظام اللفل", description=f"{status} بنجاح!", color=discord.Color.green() if enabled else discord.Color.red())
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="give_level", description="📈 إعطاء لفل لعضو (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(member="العضو", levels="عدد اللفلات")
@app_commands.checks.has_permissions(administrator=True)
async def slash_give_level(interaction: discord.Interaction, member: discord.Member, levels: int):
    await interaction.response.defer()
    user = get_user_data(interaction.guild.id, member.id)
    old_level = user["level"]
    user["level"] += levels
    user["xp"] = get_xp_for_level(user["level"])
    save_data(user_data)
    
    await give_single_level_role(member, user["level"])
    
    try:
        await member.send(f"🎉 تم ترقيتك للفل **{user['level']}** في سيرفر **{interaction.guild.name}**!")
    except:
        pass
    
    embed = discord.Embed(title="📈 إعطاء لفل", color=discord.Color.green(), timestamp=datetime.now())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 العضو", value=member.mention, inline=True)
    embed.add_field(name="👮‍♂️ المُنفِّذ", value=interaction.user.mention, inline=True)
    embed.add_field(name="📊 التفاصيل", value=f"اللفل القديم: `{old_level}`\nاللفل الجديد: `{user['level']}`", inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="take_level", description="📉 خصم لفل من عضو (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(member="العضو", levels="عدد اللفلات")
@app_commands.checks.has_permissions(administrator=True)
async def slash_take_level(interaction: discord.Interaction, member: discord.Member, levels: int):
    await interaction.response.defer()
    user = get_user_data(interaction.guild.id, member.id)
    old_level = user["level"]
    user["level"] = max(1, user["level"] - levels)
    user["xp"] = get_xp_for_level(user["level"])
    save_data(user_data)
    
    await give_single_level_role(member, user["level"])
    
    try:
        await member.send(f"⚠️ تم خصم {levels} لفل منك في **{interaction.guild.name}**!\nلفلك الحالي: {user['level']}")
    except:
        pass
    
    embed = discord.Embed(title="📉 خصم لفل", color=discord.Color.red(), timestamp=datetime.now())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 العضو", value=member.mention, inline=True)
    embed.add_field(name="👮‍♂️ المُنفِّذ", value=interaction.user.mention, inline=True)
    embed.add_field(name="📊 التفاصيل", value=f"اللفل القديم: `{old_level}`\nاللفل الجديد: `{user['level']}`", inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="give_credit", description="💰 إعطاء كريدت (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(member="العضو", amount="المبلغ")
@app_commands.checks.has_permissions(administrator=True)
async def slash_give_credit(interaction: discord.Interaction, member: discord.Member, amount: int):
    await interaction.response.defer()
    user = get_user_data(interaction.guild.id, member.id)
    user["credits"] += amount
    save_data(user_data)
    
    try:
        await member.send(f"💰 تم إضافة **{amount}** كريدت لحسابك في **{interaction.guild.name}**!")
    except:
        pass
    
    embed = discord.Embed(title="💰 إعطاء كريدت", color=discord.Color.green(), timestamp=datetime.now())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 العضو", value=member.mention, inline=True)
    embed.add_field(name="👮‍♂️ المُنفِّذ", value=interaction.user.mention, inline=True)
    embed.add_field(name="💵 المبلغ", value=f"`{amount}` كريدت", inline=True)
    embed.add_field(name="💳 الرصيد الجديد", value=f"`{user['credits']}` كريدت", inline=True)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="take_credit", description="💰 خصم كريدت (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(member="العضو", amount="المبلغ")
@app_commands.checks.has_permissions(administrator=True)
async def slash_take_credit(interaction: discord.Interaction, member: discord.Member, amount: int):
    await interaction.response.defer()
    user = get_user_data(interaction.guild.id, member.id)
    old_credits = user["credits"]
    user["credits"] = max(0, user["credits"] - amount)
    save_data(user_data)
    
    try:
        await member.send(f"⚠️ تم خصم **{amount}** كريدت من حسابك في **{interaction.guild.name}**!")
    except:
        pass
    
    embed = discord.Embed(title="💰 خصم كريدت", color=discord.Color.red(), timestamp=datetime.now())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 العضو", value=member.mention, inline=True)
    embed.add_field(name="👮‍♂️ المُنفِّذ", value=interaction.user.mention, inline=True)
    embed.add_field(name="💵 المبلغ", value=f"`{amount}` كريدت", inline=True)
    embed.add_field(name="💳 الرصيد", value=f"السابق: `{old_credits}`\nالجديد: `{user['credits']}`", inline=True)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="reset_level", description="🔄 تصفير لفل عضو (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(member="العضو", reason="السبب (اختياري)")
@app_commands.checks.has_permissions(administrator=True)
async def slash_reset_level(interaction: discord.Interaction, member: discord.Member, reason: str = "لا يوجد سبب"):
    await interaction.response.defer()
    user = get_user_data(interaction.guild.id, member.id)
    old_level = user["level"]
    
    removed_roles = await remove_all_level_roles(member)
    
    user["level"] = 1
    user["xp"] = 0
    save_data(user_data)
    
    try:
        await member.send(f"🔄 تم تصفير لفلك في **{interaction.guild.name}**!\nالسبب: {reason}")
    except:
        pass
    
    embed = discord.Embed(title="🔄 تصفير لفل", color=discord.Color.red(), timestamp=datetime.now())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 العضو", value=member.mention, inline=True)
    embed.add_field(name="👮‍♂️ المُنفِّذ", value=interaction.user.mention, inline=True)
    embed.add_field(name="📊 التفاصيل", value=f"اللفل القديم: `{old_level}`\nاللفل الجديد: `1`\n📝 السبب: {reason}", inline=False)
    if removed_roles:
        embed.add_field(name="🎭 الرتب المشالة", value=", ".join(removed_roles), inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="resetall", description="🔄 تصفير لفل وكريدت كل الأعضاء (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(confirm="اكتب CONFIRM عشان تتأكد")
@app_commands.checks.has_permissions(administrator=True)
async def slash_resetall(interaction: discord.Interaction, confirm: str):
    await interaction.response.defer()
    
    if confirm != "CONFIRM":
        await interaction.followup.send("❌ لازم تكتب `CONFIRM`!", ephemeral=True)
        return
    
    reset_count = 0
    roles_removed_count = 0
    
    await interaction.followup.send("⏳ جاري التصفير...")
    
    for member in interaction.guild.members:
        if member.bot:
            continue
        
        user = get_user_data(interaction.guild.id, member.id)
        
        if user["level"] > 1 or user["credits"] != 100 or user["xp"] > 0:
            removed = await remove_all_level_roles(member)
            if removed:
                roles_removed_count += len(removed)
            
            user["level"] = 1
            user["xp"] = 0
            user["credits"] = 100
            user["warnings"] = 0
            user["double_xp_until"] = None
            user["double_xp_active"] = False
            
            reset_count += 1
    
    save_data(user_data)
    
    embed = discord.Embed(
        title="🔄 تم تصفير الكل",
        description=f"**الأعضاء:** {reset_count}\n**الرتب:** {roles_removed_count}",
        color=discord.Color.red(),
        timestamp=datetime.now()
    )
    embed.add_field(name="👮‍♂️ المُنفِّذ", value=interaction.user.mention, inline=True)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="level_settings", description="⚙️ إعدادات نظام اللفل (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(cooldown="الوقت بين XP", xp_min="أقل XP", xp_max="أقصى XP", level_credits="كريدت عند اللفل أب")
@app_commands.checks.has_permissions(administrator=True)
async def slash_level_settings(interaction: discord.Interaction, cooldown: int = None, xp_min: int = None, xp_max: int = None, level_credits: int = None):
    await interaction.response.defer(ephemeral=True)
    global bot_config
    
    if cooldown is not None:
        bot_config["xp_cooldown"] = max(1, cooldown)
    if xp_min is not None:
        bot_config["xp_min"] = max(1, min(1000, xp_min))
    if xp_max is not None:
        bot_config["xp_max"] = max(1, min(1000, xp_max))
    if level_credits is not None:
        bot_config["level_up_credits"] = max(0, level_credits)
    
    if bot_config["xp_min"] > bot_config["xp_max"]:
        bot_config["xp_min"], bot_config["xp_max"] = bot_config["xp_max"], bot_config["xp_min"]
    
    save_config(bot_config)
    
    embed = discord.Embed(title="⚙️ إعدادات نظام اللفل", description="تم التحديث!", color=discord.Color.blue())
    embed.add_field(name="⏱️ Cooldown", value=f"`{bot_config['xp_cooldown']}` ثانية", inline=True)
    embed.add_field(name="📊 XP Range", value=f"`{bot_config['xp_min']}` - `{bot_config['xp_max']}`", inline=True)
    embed.add_field(name="💰 Level Up Credits", value=f"`{bot_config['level_up_credits']}`", inline=True)
    await interaction.followup.send(embed=embed, ephemeral=True)

# ===== الأوامر الجديدة: level_vc_setting, add_xp, remove_xp =====

@bot.tree.command(name="level_vc_setting", description="🎙️ إعدادات نظام الـ VC XP (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    xp_per_minute="كل دقيقة كام XP (مثلاً 10)",
    xp_min="أقل XP ممكن (مثلاً 5)",
    xp_max="أقصى XP ممكن (مثلاً 15)",
    active_only="فقط الأعضاء النشطين (True/False)",
    boost_multiplier="مضاعف البوستر (مثلاً 1.5)"
)
@app_commands.checks.has_permissions(administrator=True)
async def slash_level_vc_setting(
    interaction: discord.Interaction, 
    xp_per_minute: int = None,
    xp_min: int = None, 
    xp_max: int = None,
    active_only: bool = None,
    boost_multiplier: float = None
):
    await interaction.response.defer(ephemeral=True)
    
    current = get_guild_vc_config(interaction.guild.id)
    
    if xp_per_minute is not None:
        current["vc_xp_per_minute"] = max(1, min(100, xp_per_minute))
    if xp_min is not None:
        current["vc_xp_min"] = max(1, min(100, xp_min))
    if xp_max is not None:
        current["vc_xp_max"] = max(1, min(100, xp_max))
    if active_only is not None:
        current["vc_active_only"] = active_only
    if boost_multiplier is not None:
        current["vc_boost_multiplier"] = max(1.0, min(3.0, boost_multiplier))
    
    if current["vc_xp_min"] > current["vc_xp_max"]:
        current["vc_xp_min"], current["vc_xp_max"] = current["vc_xp_max"], current["vc_xp_min"]
    
    set_guild_vc_config(interaction.guild.id, current)
    
    embed = discord.Embed(
        title="🎙️ إعدادات VC XP",
        description="تم تحديث الإعدادات بنجاح!",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="⏱️ XP لكل دقيقة", 
        value=f"`{current['vc_xp_per_minute']}`", 
        inline=True
    )
    embed.add_field(
        name="📊 مدى XP", 
        value=f"`{current['vc_xp_min']}` - `{current['vc_xp_max']}`", 
        inline=True
    )
    embed.add_field(
        name="🎯 نشطين فقط", 
        value=f"`{current['vc_active_only']}`", 
        inline=True
    )
    embed.add_field(
        name="🚀 مضاعف البوستر", 
        value=f"`{current['vc_boost_multiplier']}x`", 
        inline=True
    )
    
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="add_xp", description="➕ إضافة XP لعضو (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    member="العضو",
    amount="كمية XP (مثلاً 100)",
    reason="السبب (اختياري)"
)
@app_commands.checks.has_permissions(administrator=True)
async def slash_add_xp(interaction: discord.Interaction, member: discord.Member, amount: int, reason: str = "لا يوجد سبب"):
    await interaction.response.defer()
    
    if amount <= 0:
        await interaction.followup.send("❌ كمية XP يجب أن تكون أكبر من 0!", ephemeral=True)
        return
    
    if member.bot:
        await interaction.followup.send("❌ لا يمكن إضافة XP للبوتات!", ephemeral=True)
        return
    
    user = get_user_data(interaction.guild.id, member.id)
    old_level = user["level"]
    old_xp = user["xp"]
    
    user["xp"] += amount
    new_level = get_level_from_xp(user["xp"])
    user["level"] = new_level
    
    if new_level > old_level:
        base_credits, bonus, features, is_milestone = get_level_rewards(new_level)
        total_credits = base_credits + bonus
        user["credits"] += total_credits
        new_role = await give_single_level_role(member, new_level)
        
        try:
            await send_level_up_dm(member, new_level, base_credits, bonus, features, new_role, is_milestone)
        except:
            pass
    
    save_data(user_data)
    
    embed = discord.Embed(
        title="➕ تم إضافة XP",
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 العضو", value=member.mention, inline=True)
    embed.add_field(name="👮‍♂️ المُنفِّذ", value=interaction.user.mention, inline=True)
    embed.add_field(name="📊 XP قبل", value=f"`{old_xp}`", inline=True)
    embed.add_field(name="📊 XP بعد", value=f"`{user['xp']}`", inline=True)
    embed.add_field(name="➕ المضاف", value=f"`+{amount}`", inline=True)
    embed.add_field(name="📈 اللفل", value=f"`{old_level}` → `{new_level}`", inline=True)
    
    if reason != "لا يوجد سبب":
        embed.add_field(name="📝 السبب", value=reason, inline=False)
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="remove_xp", description="➖ خصم XP من عضو (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    member="العضو",
    amount="كمية XP (مثلاً 100)",
    reason="السبب (اختياري)"
)
@app_commands.checks.has_permissions(administrator=True)
async def slash_remove_xp(interaction: discord.Interaction, member: discord.Member, amount: int, reason: str = "لا يوجد سبب"):
    await interaction.response.defer()
    
    if amount <= 0:
        await interaction.followup.send("❌ كمية XP يجب أن تكون أكبر من 0!", ephemeral=True)
        return
    
    if member.bot:
        await interaction.followup.send("❌ لا يمكن خصم XP من البوتات!", ephemeral=True)
        return
    
    user = get_user_data(interaction.guild.id, member.id)
    old_level = user["level"]
    old_xp = user["xp"]
    
    user["xp"] = max(0, user["xp"] - amount)
    new_level = get_level_from_xp(user["xp"])
    user["level"] = new_level
    
    if new_level < old_level:
        new_role = await give_single_level_role(member, new_level)
    
    save_data(user_data)
    
    embed = discord.Embed(
        title="➖ تم خصم XP",
        color=discord.Color.orange(),
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 العضو", value=member.mention, inline=True)
    embed.add_field(name="👮‍♂️ المُنفِّذ", value=interaction.user.mention, inline=True)
    embed.add_field(name="📊 XP قبل", value=f"`{old_xp}`", inline=True)
    embed.add_field(name="📊 XP بعد", value=f"`{user['xp']}`", inline=True)
    embed.add_field(name="➖ المخصوم", value=f"`-{amount}`", inline=True)
    embed.add_field(name="📈 اللفل", value=f"`{old_level}` → `{new_level}`", inline=True)
    
    if reason != "لا يوجد سبب":
        embed.add_field(name="📝 السبب", value=reason, inline=False)
    
    await interaction.followup.send(embed=embed)

# ===== أمر فحص وإصلاح الرتب (احتياطي) =====

@bot.tree.command(name="fix_my_roles", description="🔧 إصلاح رتب اللفل بتاعتك (لو في مشكلة)")
async def slash_fix_my_roles(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    user = get_user_data(interaction.guild.id, interaction.user.id)
    level = user["level"]
    
    result = await give_single_level_role(interaction.user, level)
    
    if result:
        await interaction.followup.send(f"✅ تم إصلاح رتبك! حصلت على {result}", ephemeral=True)
    else:
        level_roles = {
            5: "Level 5", 10: "Level 10", 15: "Level 15",
            20: "Level 20", 25: "Level 25", 30: "Level 30", 35: "Level 35",
            40: "Level 40", 50: "Level 50", 60: "Level 60", 70: "Level 70",
            80: "Level 80", 90: "Level 90", 100: "Level 100"
        }
        if level in level_roles:
            expected = level_roles[level]
            role = discord.utils.get(interaction.guild.roles, name=expected)
            if not role:
                await interaction.followup.send(f"❌ رتبة {expected} مش موجودة في السيرفر! من فضلك أنشئها", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ ماقدرتش أضيف الرتبة. تأكد إن البوت عنده صلاحية Manage Roles", ephemeral=True)
        else:
            await interaction.followup.send(f"ℹ️ لفلك {level} ملهاش رتبة مخصصة", ephemeral=True)

# ========== Slash Commands - مودريشن (كل أوامر المودريشن كسلاش) ==========

@bot.tree.command(name="warn", description="⚠️ تحذير عضو")
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(member="العضو", reason="السبب")
async def slash_warn(interaction: discord.Interaction, member: discord.Member, reason: str = "لا يوجد سبب"):
    if not can_use_warn(interaction.user):
        await interaction.response.send_message("❌ مالكش صلاحية!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    if member.top_role >= interaction.user.top_role:
        await interaction.followup.send("❌ لا يمكن تحذير عضو أعلى منك!", ephemeral=True)
        return
    
    user = get_user_data(interaction.guild.id, member.id)
    user["warnings"] += 1
    warning_num = add_warning(interaction.guild.id, member.id, reason, interaction.user.id)
    
    punishment = None
    if user["warnings"] == 2:
        await member.timeout(timedelta(minutes=10), reason="2 تحذيرات")
        punishment = "⏱️ تايم اوت 10 دقائق"
        await log_timeout(bot, member, "10 دقائق", "2 تحذيرات", interaction.user)
    elif user["warnings"] == 3:
        await member.timeout(timedelta(minutes=30), reason="3 تحذيرات")
        punishment = "⏱️ تايم اوت 30 دقيقة"
        await log_timeout(bot, member, "30 دقيقة", "3 تحذيرات", interaction.user)
    elif user["warnings"] >= 4:
        await remove_all_level_roles(member)
        user["level"] = 1
        user["xp"] = 0
        user["credits"] = 100
        user["warnings"] = 0
        clear_warnings(interaction.guild.id, member.id)
        punishment = "🔄 تصفير اللفل والكريدت"
    
    save_data(user_data)
    
    try:
        dm_embed = discord.Embed(title="⚠️ تحذير جديد", description=f"تم تحذيرك في **{interaction.guild.name}**", color=discord.Color.orange())
        dm_embed.add_field(name="📝 السبب", value=reason, inline=False)
        dm_embed.add_field(name="🔢 عدد التحذيرات", value=f"{user['warnings']}/4", inline=True)
        if punishment:
            dm_embed.add_field(name="⛔ العقوبة", value=punishment, inline=False)
        await member.send(embed=dm_embed)
    except:
        pass
    
    embed = discord.Embed(title="⚠️ تحذير جديد", color=discord.Color.orange(), timestamp=datetime.now())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 العضو", value=member.mention, inline=True)
    embed.add_field(name="👮‍♂️ المُحذِّر", value=interaction.user.mention, inline=True)
    embed.add_field(name="📝 السبب", value=reason, inline=False)
    embed.add_field(name="🔢 التحذيرات", value=f"`{user['warnings']}/4`", inline=True)
    if punishment:
        embed.add_field(name="⛔ العقوبة", value=punishment, inline=False)
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="unwarn", description="✅ إزالة تحذير")
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(member="العضو")
async def slash_unwarn(interaction: discord.Interaction, member: discord.Member):
    if not can_use_warn(interaction.user):
        await interaction.response.send_message("❌ مالكش صلاحية!", ephemeral=True)
        return
    
    await interaction.response.defer()
    user = get_user_data(interaction.guild.id, member.id)
    
    if user["warnings"] > 0:
        user["warnings"] -= 1
        save_data(user_data)
        
        try:
            await member.send(f"✅ تم إزالة تحذير منك في **{interaction.guild.name}**!")
        except:
            pass
        
        embed = discord.Embed(title="✅ إزالة تحذير", color=discord.Color.green(), timestamp=datetime.now())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👤 العضو", value=member.mention, inline=True)
        embed.add_field(name="👮‍♂️ المُنفِّذ", value=interaction.user.mention, inline=True)
        embed.add_field(name="🔢 التحذيرات", value=f"`{user['warnings']}/4`", inline=False)
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"❌ {member.mention} مالوش تحذيرات!")

@bot.tree.command(name="timeout", description="⏱️ تايم اوت عضو")
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(member="العضو", minutes="الدقائق", reason="السبب")
async def slash_timeout(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "لا يوجد سبب"):
    if not can_use_timeout(interaction.user):
        await interaction.response.send_message("❌ مالكش صلاحية!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    if member.top_role >= interaction.user.top_role:
        await interaction.followup.send("❌ لا يمكن!", ephemeral=True)
        return
    
    try:
        await member.timeout(timedelta(minutes=minutes), reason=reason)
    except discord.Forbidden:
        await interaction.followup.send("❌ البوت لا يملك صلاحية!", ephemeral=True)
        return
    
    try:
        await member.send(f"⏱️ تايم اوت {minutes} دقيقة في **{interaction.guild.name}**!\nالسبب: {reason}")
    except:
        pass
    
    await log_timeout(bot, member, f"{minutes} دقيقة", reason, interaction.user)
    
    embed = discord.Embed(title="⏱️ تايم اوت", color=discord.Color.orange(), timestamp=datetime.now())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 العضو", value=member.mention, inline=True)
    embed.add_field(name="👮‍♂️ المُنفِّذ", value=interaction.user.mention, inline=True)
    embed.add_field(name="⏰ المدة", value=f"`{minutes}` دقيقة", inline=True)
    embed.add_field(name="📝 السبب", value=reason, inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="untimeout", description="✅ فك تايم اوت")
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(member="العضو")
async def slash_untimeout(interaction: discord.Interaction, member: discord.Member):
    if not can_use_untimeout(interaction.user):
        await interaction.response.send_message("❌ مالكش صلاحية!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    try:
        await member.timeout(None)
    except discord.Forbidden:
        await interaction.followup.send("❌ البوت لا يملك صلاحية!", ephemeral=True)
        return
    
    try:
        await member.send(f"✅ تم فك تايم اوتك في **{interaction.guild.name}**!")
    except:
        pass
    
    embed = discord.Embed(title="✅ فك تايم اوت", color=discord.Color.green(), timestamp=datetime.now())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 العضو", value=member.mention, inline=True)
    embed.add_field(name="👮‍♂️ المُنفِّذ", value=interaction.user.mention, inline=True)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="mute", description="🔇 ميوت عضو")
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(member="العضو", hours="الساعات", reason="السبب")
async def slash_mute(interaction: discord.Interaction, member: discord.Member, hours: int, reason: str = "لا يوجد سبب"):
    if not can_use_mute(interaction.user):
        await interaction.response.send_message("❌ مالكش صلاحية!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    if member.top_role >= interaction.user.top_role:
        await interaction.followup.send("❌ لا يمكن!", ephemeral=True)
        return
    
    user = get_user_data(interaction.guild.id, member.id)
    expiry = datetime.now() + timedelta(hours=hours)
    user["muted_until"] = expiry.isoformat()
    save_data(user_data)
    
    try:
        await member.send(f"🔇 ميوت {hours} ساعة في **{interaction.guild.name}**!\nالسبب: {reason}")
    except:
        pass
    
    await log_mute(bot, member, f"{hours} ساعة", reason, interaction.user)
    
    embed = discord.Embed(title="🔇 ميوت", color=discord.Color.red(), timestamp=datetime.now())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 العضو", value=member.mention, inline=True)
    embed.add_field(name="👮‍♂️ المُنفِّذ", value=interaction.user.mention, inline=True)
    embed.add_field(name="⏰ المدة", value=f"`{hours}` ساعة", inline=True)
    embed.add_field(name="📝 السبب", value=reason, inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="unmute", description="🔊 فك ميوت")
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(member="العضو")
async def slash_unmute(interaction: discord.Interaction, member: discord.Member):
    if not can_use_unmute(interaction.user):
        await interaction.response.send_message("❌ مالكش صلاحية!", ephemeral=True)
        return
    
    await interaction.response.defer()
    user = get_user_data(interaction.guild.id, member.id)
    user["muted_until"] = None
    save_data(user_data)
    
    try:
        await member.send(f"🔊 تم فك ميوتك في **{interaction.guild.name}**!")
    except:
        pass
    
    embed = discord.Embed(title="🔊 فك ميوت", color=discord.Color.green(), timestamp=datetime.now())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 العضو", value=member.mention, inline=True)
    embed.add_field(name="👮‍♂️ المُنفِّذ", value=interaction.user.mention, inline=True)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="kick", description="👢 طرد عضو")
@app_commands.default_permissions(kick_members=True)
@app_commands.describe(member="العضو", reason="السبب")
async def slash_kick(interaction: discord.Interaction, member: discord.Member, reason: str = "لا يوجد سبب"):
    if not can_use_kick(interaction.user):
        await interaction.response.send_message("❌ مالكش صلاحية!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    if member.top_role >= interaction.user.top_role:
        await interaction.followup.send("❌ لا يمكن طرد عضو أعلى منك!", ephemeral=True)
        return
    
    await log_kick(bot, member, reason, interaction.user)
    
    try:
        await member.send(f"👢 تم طردك من **{interaction.guild.name}**!\nالسبب: {reason}")
    except:
        pass
    
    try:
        await member.kick(reason=reason)
    except discord.Forbidden:
        await interaction.followup.send("❌ البوت لا يملك صلاحية!", ephemeral=True)
        return
    
    embed = discord.Embed(title="👢 طرد عضو", color=discord.Color.orange(), timestamp=datetime.now())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 العضو", value=member.mention, inline=True)
    embed.add_field(name="👮‍♂️ المُنفِّذ", value=interaction.user.mention, inline=True)
    embed.add_field(name="📝 السبب", value=reason, inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="ban", description="🔨 حظر عضو")
@app_commands.default_permissions(ban_members=True)
@app_commands.describe(member="العضو", reason="السبب")
async def slash_ban(interaction: discord.Interaction, member: discord.Member, reason: str = "لا يوجد سبب"):
    if not can_use_ban(interaction.user):
        await interaction.response.send_message("❌ مالكش صلاحية!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    if member.top_role >= interaction.user.top_role:
        await interaction.followup.send("❌ لا يمكن حظر عضو أعلى منك!", ephemeral=True)
        return
    
    await log_ban(bot, member, reason, interaction.user)
    
    try:
        await member.send(f"🔨 تم حظرك من **{interaction.guild.name}**!\nالسبب: {reason}")
    except:
        pass
    
    try:
        await member.ban(reason=reason)
    except discord.Forbidden:
        await interaction.followup.send("❌ البوت لا يملك صلاحية!", ephemeral=True)
        return
    
    embed = discord.Embed(title="🔨 حظر عضو", color=discord.Color.dark_red(), timestamp=datetime.now())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 العضو", value=member.mention, inline=True)
    embed.add_field(name="👮‍♂️ المُنفِّذ", value=interaction.user.mention, inline=True)
    embed.add_field(name="📝 السبب", value=reason, inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="unban", description="✅ فك حظر")
@app_commands.default_permissions(ban_members=True)
@app_commands.describe(user_id="آيدي العضو")
async def slash_unban(interaction: discord.Interaction, user_id: str):
    if not can_use_unban(interaction.user):
        await interaction.response.send_message("❌ مالكش صلاحية!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    try:
        user = await bot.fetch_user(int(user_id))
        await interaction.guild.unban(user)
        embed = discord.Embed(title="✅ فك حظر", description=f"تم فك حظر **{user.name}**!", color=discord.Color.green())
        embed.add_field(name="👮‍♂️ المُنفِّذ", value=interaction.user.mention, inline=True)
        await interaction.followup.send(embed=embed)
    except discord.NotFound:
        await interaction.followup.send("❌ لم يتم العثور على المستخدم!", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("❌ البوت لا يملك صلاحية!", ephemeral=True)

@bot.tree.command(name="prison", description="🔒 حبس عضو (إعطاء رتبة prison)")
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(member="العضو المراد حبسه", reason="السبب")
async def slash_prison(interaction: discord.Interaction, member: discord.Member, reason: str = "لا يوجد سبب"):
    if not can_use_prison(interaction.user):
        await interaction.response.send_message("❌ مالكش صلاحية لاستخدام أمر الحبس!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    if member.top_role >= interaction.user.top_role:
        await interaction.followup.send("❌ لا يمكن حبس عضو أعلى منك!", ephemeral=True)
        return
    
    # البحث عن رتبة prison أو إنشائها لو مش موجودة
    prison_role = discord.utils.get(interaction.guild.roles, name="prison")
    if not prison_role:
        try:
            prison_role = await interaction.guild.create_role(
                name="prison",
                color=discord.Color.dark_gray(),
                reason="Prison role created automatically"
            )
            # نقل الرتبة فوق @everyone
            await prison_role.edit(position=1)
        except discord.Forbidden:
            await interaction.followup.send("❌ البوت مش قادر يعمل رتبة! تأكد من الصلاحيات.", ephemeral=True)
            return
    
    # تحقق لو العضو عنده الرتبة أصلاً
    if prison_role in member.roles:
        await interaction.followup.send(f"⚠️ {member.mention} محبوس أصلاً!", ephemeral=True)
        return
    
    try:
        await member.add_roles(prison_role, reason=f"Prison by {interaction.user.display_name}: {reason}")
        
        embed = discord.Embed(
            title="🔒 تم الحبس",
            color=discord.Color.dark_gray(),
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👤 العضو", value=member.mention, inline=True)
        embed.add_field(name="👮‍♂️ المُنفِّذ", value=interaction.user.mention, inline=True)
        embed.add_field(name="📝 السبب", value=reason, inline=False)
        await interaction.followup.send(embed=embed)
        
        # محاولة إرسال DM للعضو
        try:
            await member.send(f"🔒 تم حبسك في **{interaction.guild.name}**!\nالسبب: {reason}")
        except:
            pass
    except discord.Forbidden:
        await interaction.followup.send("❌ البوت مش قادر يدي الرتبة! تأكد إن رتبة البوت أعلى من رتبة prison.", ephemeral=True)

@bot.tree.command(name="unprison", description="🔓 فك حبس عضو (إزالة رتبة prison)")
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(member="العضو المراد فك حبسه")
async def slash_unprison(interaction: discord.Interaction, member: discord.Member):
    if not can_use_unprison(interaction.user):
        await interaction.response.send_message("❌ مالكش صلاحية لاستخدام أمر فك الحبس!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    prison_role = discord.utils.get(interaction.guild.roles, name="prison")
    if not prison_role:
        await interaction.followup.send("❌ مفيش رتبة prison في السيرفر!", ephemeral=True)
        return
    
    if prison_role not in member.roles:
        await interaction.followup.send(f"⚠️ {member.mention} مش محبوس أصلاً!", ephemeral=True)
        return
    
    try:
        await member.remove_roles(prison_role, reason=f"Unprisoned by {interaction.user.display_name}")
        
        embed = discord.Embed(
            title="🔓 تم فك الحبس",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👤 العضو", value=member.mention, inline=True)
        embed.add_field(name="👮‍♂️ المُنفِّذ", value=interaction.user.mention, inline=True)
        await interaction.followup.send(embed=embed)
        
        # محاولة إرسال DM للعضو
        try:
            await member.send(f"🔓 تم فك حبسك في **{interaction.guild.name}**! خلّيك ملتزم 🙌")
        except:
            pass
    except discord.Forbidden:
        await interaction.followup.send("❌ البوت مش قادر يشيل الرتبة! تأكد من الصلاحيات.", ephemeral=True)

@bot.tree.command(name="role", description="🎭 إعطاء/إزالة رول")
@app_commands.default_permissions(manage_roles=True)
@app_commands.describe(member="العضو", role="الرول")
async def slash_role(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not can_use_role(interaction.user):
        await interaction.response.send_message("❌ مالكش صلاحية!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    if role.position >= interaction.guild.me.top_role.position:
        await interaction.followup.send("❌ رتبة البوت أقل!", ephemeral=True)
        return
    
    if role in member.roles:
        try:
            await member.remove_roles(role)
        except discord.Forbidden:
            await interaction.followup.send("❌ لا يمكن إزالة الرتبة!", ephemeral=True)
            return
        action = "إزالة"
        color = discord.Color.red()
    else:
        try:
            await member.add_roles(role)
        except discord.Forbidden:
            await interaction.followup.send("❌ لا يمكن إعطاء الرتبة!", ephemeral=True)
            return
        action = "إعطاء"
        color = discord.Color.green()
    
    embed = discord.Embed(title=f"🎭 {action} رول", color=color, timestamp=datetime.now())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 العضو", value=member.mention, inline=True)
    embed.add_field(name="👮‍♂️ المُنفِّذ", value=interaction.user.mention, inline=True)
    embed.add_field(name="🎭 الرول", value=role.mention, inline=True)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="clear", description="🗑️ مسح رسائل")
@app_commands.default_permissions(manage_messages=True)
@app_commands.describe(amount="العدد (1-100)")
async def slash_clear(interaction: discord.Interaction, amount: int = 10):
    if not can_use_clear(interaction.user):
        await interaction.response.send_message("❌ مالكش صلاحية!", ephemeral=True)
        return
    
    can_use, remaining = check_global_cooldown(interaction.user.id)
    if not can_use:
        await interaction.response.send_message(f"⏳ انتظر {remaining:.1f} ثانية!", ephemeral=True)
        return
    
    if amount < 1 or amount > 100:
        await interaction.response.send_message("❌ يجب أن يكون بين 1 و 100!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    
    embed = discord.Embed(title="🗑️ تم المسح", description=f"تم مسح **{len(deleted)}** رسالة!", color=discord.Color.green())
    await interaction.followup.send(embed=embed, ephemeral=True)
# ========== أوامر معلومات الـ XP و Double XP ==========

@bot.tree.command(name="xp_info", description="📊 عرض كل معلومات الـ XP بتاعتك")
@app_commands.describe(member="العضو (اختياري)")
async def slash_xp_info(interaction: discord.Interaction, member: discord.Member = None):
    can_use, remaining = check_global_cooldown(interaction.user.id)
    if not can_use:
        await interaction.response.send_message(f"⏳ انتظر {remaining:.1f} ثانية!", ephemeral=True)
        return

    await interaction.response.defer()
    target = member or interaction.user

    if target.bot:
        await interaction.followup.send("❌ البوتات مالهاش XP!", ephemeral=True)
        return

    user = get_user_data(interaction.guild.id, target.id)
    level = user["level"]
    xp = user["xp"]
    credits_val = user["credits"]

    # حساب تفاصيل اللفل
    xp_needed_next = get_xp_needed_for_next_level(level)
    current_level_xp = get_current_level_xp(xp, level)
    total_xp_for_next = get_xp_for_level(level + 1)
    xp_remaining = total_xp_for_next - xp

    # حساب نسبة التقدم
    if xp_needed_next > 0:
        progress_percent = min(100, int((current_level_xp / xp_needed_next) * 100))
    else:
        progress_percent = 100

    # الرانك في السيرفر
    rank_pos, total_members = get_rank(interaction.guild.id, target.id, interaction.guild)

    # حالة الدبل XP
    if has_double_xp(interaction.guild.id, target.id):
        time_left = get_double_xp_time_remaining(interaction.guild.id, target.id)
        double_xp_line = f"> ⚡ **Double XP:** مفعل — ينتهي بعد **{time_left}**"
    else:
        double_xp_line = "> ⚡ **Double XP:** غير مفعل"

    # حالة البوستر
    if is_server_booster(target):
        booster_line = "> 🚀 **Server Booster:** نعم (1.5x XP + خصم 25%)"
    else:
        booster_line = "> 🚀 **Server Booster:** لا"

    # حالة الميوت
    if is_muted(interaction.guild.id, target.id):
        mute_line = "> 🔇 **الحالة:** ميوت"
    else:
        mute_line = "> 🔊 **الحالة:** نشط"

    # لون الاسم
    name_color = user.get("name_color", None)
    if name_color:
        color_line = f"> 🎨 **لون الاسم:** {name_color}"
    else:
        color_line = "> 🎨 **لون الاسم:** افتراضي"

    # الإمبد الاحترافي
    embed_color = discord.Color.from_str(user.get("rank_color", "#DC143C"))

    # بناء الوصف الكامل في description
    description = (
        f"```\n"
        f"Level {level}  •  Rank #{rank_pos}/{total_members}  •  {credits_val:,} Credits\n"
        f"```\n"
        f"\n"
        f"**⚡ XP Details**\n"
        f"> **إجمالي XP:** {xp:,}\n"
        f"> **XP في اللفل:** {current_level_xp:,} / {xp_needed_next:,}\n"
        f"> **المتبقي للفل {level + 1}:** {xp_remaining:,} XP\n"
        f"\n"
        f"**🔥 Status**\n"
        f"{double_xp_line}\n"
        f"{booster_line}\n"
        f"{mute_line}\n"
        f"{color_line}"
    )

    embed = discord.Embed(
        title=f"📊 XP Info — {target.display_name}",
        description=description,
        color=embed_color,
        timestamp=datetime.now()
    )

    embed.set_thumbnail(url=target.display_avatar.url)

    embed.set_footer(
        text=f"طلب بواسطة {interaction.user.display_name}",
        icon_url=interaction.user.display_avatar.url
    )

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="double_xp_info", description="⚡ عرض كل معلومات الـ Double XP بتاعتك")
@app_commands.describe(member="العضو (اختياري)")
async def slash_double_xp_info(interaction: discord.Interaction, member: discord.Member = None):
    can_use, remaining = check_global_cooldown(interaction.user.id)
    if not can_use:
        await interaction.response.send_message(f"⏳ انتظر {remaining:.1f} ثانية!", ephemeral=True)
        return

    await interaction.response.defer()
    target = member or interaction.user

    if target.bot:
        await interaction.followup.send("❌ البوتات مالهاش Double XP!", ephemeral=True)
        return

    user = get_user_data(interaction.guild.id, target.id)
    is_active = has_double_xp(interaction.guild.id, target.id)

    if is_active:
        embed_color = discord.Color.gold()
    else:
        embed_color = discord.Color.dark_grey()

    if is_active:
        # ===== حالة مفعل =====
        expiry_str = user.get("double_xp_until")
        remaining_text = "غير متاح"
        time_bar_text = ""
        expiry_section = ""
        purchase_section = ""

        if expiry_str:
            try:
                expiry = datetime.fromisoformat(expiry_str)
                remaining_time = expiry - datetime.now()
                total_seconds = max(0, remaining_time.total_seconds())

                # حساب الوقت المتبقي بالتفصيل
                days = int(total_seconds // 86400)
                hours = int((total_seconds % 86400) // 3600)
                minutes = int((total_seconds % 3600) // 60)

                time_parts = []
                if days > 0:
                    time_parts.append(f"{days} يوم")
                if hours > 0:
                    time_parts.append(f"{hours} ساعة")
                if minutes > 0:
                    time_parts.append(f"{minutes} دقيقة")
                remaining_text = " و ".join(time_parts) if time_parts else "أقل من دقيقة"

                time_bar_text = ""

                # تاريخ الانتهاء
                expiry_ts = int(expiry.timestamp())
                expiry_section = (
                    f"\n"
                    f"**📅 ينتهي في**\n"
                    f"> <t:{expiry_ts}:F>\n"
                    f"> (<t:{expiry_ts}:R>)\n"
                )

                # تاريخ التفعيل التقريبي
                # نحاول نحسب من أقرب مدة من الشوب
                durations_hours = sorted([item["duration"] for item in SHOP_ITEMS["double_xp"].values()])
                remaining_hours = total_seconds / 3600
                # نختار أقرب مدة أكبر من أو تساوي الوقت المتبقي
                purchased_duration = durations_hours[-1]  # افتراضي
                for d in durations_hours:
                    if d >= remaining_hours:
                        purchased_duration = d
                        break
                purchase_time = expiry - timedelta(hours=purchased_duration)
                purchase_ts = int(purchase_time.timestamp())
                purchase_section = (
                    f"\n"
                    f"**🕐 تاريخ الشراء (تقريبي)**\n"
                    f"> <t:{purchase_ts}:F>\n"
                    f"> (<t:{purchase_ts}:R>)\n"
                )

            except Exception:
                pass

        description = (
            f"```\n"
            f"🟢  Double XP: مفعل\n"
            f"```\n"
            f"\n"
            f"**⏳ الوقت المتبقي**\n"
            f"> {remaining_text}\n"
            f"{time_bar_text}"
            f"{expiry_section}"
            f"{purchase_section}"
            f"\n"
            f"**🎁 المميزات النشطة**\n"
            f"> ✅ **2x XP** على كل الرسائل\n"
            f"> ✅ **2x XP** في الرومات الصوتية\n"
            f"> ✅ تسريع التقدم في اللفلات\n"
        )

    else:
        # ===== حالة مش مفعل =====
        is_booster = is_server_booster(target)
        prices_lines = []
        for key, item in SHOP_ITEMS["double_xp"].items():
            duration = item["duration"]
            if duration < 24:
                dur_text = f"{duration} ساعة"
            elif duration == 24:
                dur_text = "يوم واحد"
            else:
                dur_text = f"{duration // 24} أيام" if duration // 24 > 1 else "أسبوع"

            if is_booster and "booster_price" in item:
                price = item["booster_price"]
                prices_lines.append(f"> `{dur_text}` ➜ ~~{item['price']}~~ **{price}** كريدت 🚀")
            else:
                prices_lines.append(f"> `{dur_text}` ➜ **{item['price']}** كريدت")

        prices_text = "\n".join(prices_lines)

        description = (
            f"```\n"
            f"🔴  Double XP: غير مفعل\n"
            f"```\n"
            f"\n"
            f"مفيش Double XP نشط حالياً لهذا العضو.\n"
            f"\n"
            f"**🛒 الأسعار المتاحة**\n"
            f"{prices_text}\n"
        )

    # معلومات إضافية
    booster_bonus = ""
    if is_server_booster(target):
        booster_bonus = "\n> 🚀 **بوستر:** XP إضافي 1.5x فوق الدبل!"

    description += (
        f"\n"
        f"**ℹ️ معلومات إضافية**\n"
        f"> **الرصيد:** {user['credits']:,} كريدت"
        f"{booster_bonus}"
    )

    embed = discord.Embed(
        title=f"⚡ Double XP Info — {target.display_name}",
        description=description,
        color=embed_color,
        timestamp=datetime.now()
    )

    embed.set_thumbnail(url=target.display_avatar.url)

    embed.set_footer(
        text=f"طلب بواسطة {interaction.user.display_name}",
        icon_url=interaction.user.display_avatar.url
    )

    await interaction.followup.send(embed=embed)


# ========== نظام البنك ==========

BANK_COMPANIES = {
    "moka": {"name": "شركة موكا الحرامية", "emoji": None, "win_rate": 50, "risky": False, "multiplier": 1},
    "muz": {"name": "شركة Muz", "emoji": None, "win_rate": 50, "risky": False, "multiplier": 1},
    "saif": {"name": "شركة سيف اللي مش حرامي", "emoji": None, "win_rate": 50, "risky": False, "multiplier": 1},
    "kingdom": {"name": "شركة المملكة", "emoji": None, "win_rate": 30, "risky": True, "multiplier": 3},
    "cheese": {"name": "شركة الجبنة الاسطنبولي", "emoji": None, "win_rate": 30, "risky": True, "multiplier": 4},
}

BANK_MIN_INVEST = 500
BANK_MAX_INVEST = 5000

BANK_MIN_LEVEL = 5
BANK_LOAN_MIN = 500
BANK_LOAN_MAX = 7000
BANK_LOAN_DAYS = 7
BANK_INTEREST_RATE = 0.50  # 50%
BANK_MAX_INVESTMENTS_PER_DAY = 5

def load_bank_data():
    if os.path.exists(BANK_DATA_FILE):
        with open(BANK_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_bank_data(data):
    with open(BANK_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

bank_data = load_bank_data()

def get_bank_user(guild_id, user_id):
    gid = str(guild_id)
    uid = str(user_id)
    if gid not in bank_data:
        bank_data[gid] = {}
    if uid not in bank_data[gid]:
        bank_data[gid][uid] = {
            "loan_amount": 0,
            "loan_date": None,
            "transfers": [],
            "investments_today": 0,
            "last_investment_date": None,
        }
        save_bank_data(bank_data)
    return bank_data[gid][uid]

def check_loan_expiry():
    """تحقق من القروض المنتهية وخصم من الرصيد"""
    now = datetime.now()
    for gid, guild_bank in bank_data.items():
        if not isinstance(guild_bank, dict):
            continue
        for uid, bdata in guild_bank.items():
            if not isinstance(bdata, dict):
                continue
            if bdata.get("loan_amount", 0) > 0 and bdata.get("loan_date"):
                try:
                    loan_date = datetime.fromisoformat(bdata["loan_date"])
                    if (now - loan_date).days >= BANK_LOAN_DAYS:
                        user = get_user_data(gid, int(uid))
                        user["credits"] -= bdata["loan_amount"]
                        bdata["loan_amount"] = 0
                        bdata["loan_date"] = None
                        save_data(user_data)
                        save_bank_data(bank_data)
                except:
                    pass

def add_transfer_record(guild_id, sender_id, receiver_id, amount, sender_name, receiver_name):
    sender_bank = get_bank_user(guild_id, sender_id)
    receiver_bank = get_bank_user(guild_id, receiver_id)
    record = {
        "from_id": str(sender_id),
        "to_id": str(receiver_id),
        "from_name": sender_name,
        "to_name": receiver_name,
        "amount": amount,
        "date": datetime.now().isoformat()
    }
    sender_bank["transfers"].insert(0, record)
    if len(sender_bank["transfers"]) > 20:
        sender_bank["transfers"] = sender_bank["transfers"][:20]
    receiver_bank["transfers"].insert(0, record)
    if len(receiver_bank["transfers"]) > 20:
        receiver_bank["transfers"] = receiver_bank["transfers"][:20]
    save_bank_data(bank_data)

BANK_INVEST_COOLDOWN_HOURS = 4

def get_investments_remaining(guild_id, user_id):
    buser = get_bank_user(guild_id, user_id)
    now = datetime.now()
    last_date = buser.get("last_investment_date")
    reset = False
    if last_date is None:
        reset = True
    else:
        try:
            last_dt = datetime.fromisoformat(last_date)
            if (now - last_dt).total_seconds() >= BANK_INVEST_COOLDOWN_HOURS * 3600:
                reset = True
        except Exception:
            reset = True
    if reset:
        buser["investments_today"] = 0
        buser["last_investment_date"] = now.isoformat()
        save_bank_data(bank_data)
    return BANK_MAX_INVESTMENTS_PER_DAY - buser["investments_today"]


def create_bank_stock_image():
    """صورة أسهم عشوائية للبنك الرئيسي"""
    width, height = 800, 400
    bg_dark = (24, 25, 28)
    card_bg = (35, 39, 42)
    grid_color = (50, 53, 57)
    green = (46, 204, 113)
    red = (231, 76, 60)
    gold = (255, 215, 0)
    white = (255, 255, 255)
    gray = (150, 152, 155)

    img = Image.new('RGB', (width, height), bg_dark)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([10, 10, width - 10, height - 10], radius=15, fill=card_bg)

    # شبكة خلفية
    for x in range(40, width - 20, 40):
        draw.line([(x, 60), (x, height - 50)], fill=grid_color, width=1)
    for y in range(60, height - 40, 30):
        draw.line([(40, y), (width - 20, y)], fill=grid_color, width=1)

    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    except:
        title_font = ImageFont.load_default()
        label_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # عنوان
    draw.text((30, 20), "Lake Bank - Market Overview", fill=gold, font=title_font)

    # 3 خطوط أسهم عشوائية
    colors = [green, red, (0, 176, 244)]
    names = ["DRK", "MUZ", "BTC"]
    chart_left = 50
    chart_right = width - 30
    chart_top = 80
    chart_bottom = height - 60

    for idx, (color, name) in enumerate(zip(colors, names)):
        points = []
        y_val = random.randint(chart_top + 40, chart_bottom - 40)
        for x in range(chart_left, chart_right, 8):
            y_val += random.randint(-15, 15)
            y_val = max(chart_top, min(chart_bottom, y_val))
            points.append((x, y_val))
        if len(points) >= 2:
            draw.line(points, fill=color, width=2)
        # اسم السهم
        last_pt = points[-1] if points else (chart_right, chart_top + 60 * idx)
        draw.text((last_pt[0] + 5, last_pt[1] - 6), name, fill=color, font=label_font)

    # أرقام على المحور
    for i, y in enumerate(range(chart_top, chart_bottom, 40)):
        val = 1000 - i * 50
        draw.text((15, y - 5), str(val), fill=gray, font=small_font)

    # تاريخ أسفل
    draw.text((chart_left, height - 40), datetime.now().strftime("%Y-%m-%d %H:%M"), fill=gray, font=label_font)

    # مؤشرات
    indicators = [("▲ DRK +2.4%", green), ("▼ MUZ -1.8%", red), ("▲ BTC +0.9%", (0, 176, 244))]
    ix = width - 380
    for txt, col in indicators:
        draw.text((ix, height - 40), txt, fill=col, font=label_font)
        ix += 130

    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer


def create_investment_result_image(company_name, won, amount, profit=0):
    """صورة نتيجة الاستثمار - سهم أخضر لو فاز، أحمر لو خسر"""
    width, height = 700, 380
    bg_dark = (24, 25, 28)
    card_bg = (35, 39, 42)
    grid_color = (50, 53, 57)

    if won:
        main_color = (46, 204, 113)  # أخضر
        title_text = "نجح استثمارك"
        result_text = f"لقد نجح استثمارك وربحت {profit:,} كريدت!"
        arrow_direction = "up"
    else:
        main_color = (231, 76, 60)  # أحمر
        title_text = "فشل استثمارك"
        result_text = f"لقد خسرت كل المبلغ ({amount:,} كريدت)"
        arrow_direction = "down"

    img = Image.new('RGB', (width, height), bg_dark)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([8, 8, width - 8, height - 8], radius=15, fill=card_bg)

    # شريط علوي ملون
    draw.rounded_rectangle([8, 8, width - 8, 70], radius=15, fill=main_color)
    draw.rectangle([8, 45, width - 8, 70], fill=main_color)

    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
        sub_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
        body_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except:
        title_font = ImageFont.load_default()
        sub_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # عنوان
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    title_w = title_bbox[2] - title_bbox[0]
    draw.text(((width - title_w) // 2, 22), title_text, fill=(255, 255, 255), font=title_font)

    # رسم الشارت
    chart_left = 40
    chart_right = width - 40
    chart_top = 90
    chart_bottom = 280
    gray = (150, 152, 155)

    # شبكة خلفية
    for x in range(chart_left, chart_right, 35):
        draw.line([(x, chart_top), (x, chart_bottom)], fill=grid_color, width=1)
    for y in range(chart_top, chart_bottom, 25):
        draw.line([(chart_left, y), (chart_right, y)], fill=grid_color, width=1)

    # خط السهم
    points = []
    num_points = 40
    step = (chart_right - chart_left) / num_points

    if arrow_direction == "up":
        y_start = chart_bottom - 20
        y_end = chart_top + 20
        for i in range(num_points + 1):
            x = chart_left + i * step
            progress = i / num_points
            base_y = y_start + (y_end - y_start) * progress
            noise = random.randint(-10, 10)
            y = max(chart_top, min(chart_bottom, base_y + noise))
            points.append((x, y))
    else:
        y_start = chart_top + 20
        y_end = chart_bottom - 20
        for i in range(num_points + 1):
            x = chart_left + i * step
            progress = i / num_points
            base_y = y_start + (y_end - y_start) * progress
            noise = random.randint(-10, 10)
            y = max(chart_top, min(chart_bottom, base_y + noise))
            points.append((x, y))

    # ملء تحت الخط
    if len(points) >= 2:
        fill_color = (main_color[0], main_color[1], main_color[2], 40)
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            draw.polygon([(x1, y1), (x2, y2), (x2, chart_bottom), (x1, chart_bottom)],
                         fill=(main_color[0], main_color[1], main_color[2]))

        # الخط الرئيسي فوق
        draw.line(points, fill=(255, 255, 255), width=3)

    # سهم كبير
    arrow_x = width - 80
    arrow_y = chart_top + 30
    if arrow_direction == "up":
        draw.polygon([(arrow_x, arrow_y + 40), (arrow_x + 30, arrow_y), (arrow_x + 60, arrow_y + 40)], fill=main_color)
        draw.rectangle([arrow_x + 15, arrow_y + 40, arrow_x + 45, arrow_y + 80], fill=main_color)
    else:
        draw.polygon([(arrow_x, arrow_y + 40), (arrow_x + 30, arrow_y + 80), (arrow_x + 60, arrow_y + 40)], fill=main_color)
        draw.rectangle([arrow_x + 15, arrow_y, arrow_x + 45, arrow_y + 40], fill=main_color)

    # اسم الشركة
    company_bbox = draw.textbbox((0, 0), company_name, font=sub_font)
    company_w = company_bbox[2] - company_bbox[0]
    draw.text(((width - company_w) // 2, chart_bottom + 10), company_name, fill=main_color, font=sub_font)

    # نص النتيجة
    result_bbox = draw.textbbox((0, 0), result_text, font=body_font)
    result_w = result_bbox[2] - result_bbox[0]
    draw.text(((width - result_w) // 2, chart_bottom + 38), result_text, fill=gray, font=body_font)

    # تاريخ
    date_text = datetime.now().strftime("Lake Bank • %Y-%m-%d %H:%M")
    draw.text((chart_left, height - 30), date_text, fill=(100, 100, 100), font=small_font)

    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer


# ===== أزرار وقوائم البنك =====

class TransferAmountModal(Modal, title="💱 تحويل كريدت"):
    member_id_input = TextInput(
        label="ID العضو المراد التحويل إليه",
        placeholder="مثال: 123456789012345678",
        required=True,
        max_length=20
    )
    amount_input = TextInput(
        label="المبلغ",
        placeholder="مثال: 500",
        required=True,
        max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        can_use, remaining = check_global_cooldown(interaction.user.id)
        if not can_use:
            await interaction.response.send_message(f"⏳ انتظر {remaining:.1f} ثانية!", ephemeral=True)
            return

        try:
            target_id = int(self.member_id_input.value.strip())
            amount = int(self.amount_input.value.strip())
        except ValueError:
            await interaction.response.send_message("❌ أدخل أرقام صحيحة!", ephemeral=True)
            return

        if amount <= 0:
            await interaction.response.send_message("❌ المبلغ لازم يكون أكبر من 0!", ephemeral=True)
            return

        if target_id == interaction.user.id:
            await interaction.response.send_message("❌ مينفعش تحول لنفسك!", ephemeral=True)
            return

        sender = get_user_data(interaction.guild.id, interaction.user.id)
        if sender["credits"] < amount:
            await interaction.response.send_message(f"❌ رصيدك مش كفاية! معاك **{sender['credits']:,}** كريدت", ephemeral=True)
            return

        target_member = interaction.guild.get_member(target_id)
        if not target_member:
            await interaction.response.send_message("❌ العضو مش موجود في السيرفر!", ephemeral=True)
            return

        if target_member.bot:
            await interaction.response.send_message("❌ مينفعش تحول لبوت!", ephemeral=True)
            return

        receiver = get_user_data(interaction.guild.id, target_id)
        sender["credits"] -= amount
        receiver["credits"] += amount
        save_data(user_data)

        add_transfer_record(
            interaction.guild.id, interaction.user.id, target_id, amount,
            interaction.user.display_name, target_member.display_name
        )

        embed = discord.Embed(
            title="✅ تم التحويل بنجاح!",
            description=(
                f"**المرسل:** {interaction.user.mention}\n"
                f"**المستلم:** {target_member.mention}\n"
                f"**المبلغ:** {amount:,} كريدت\n\n"
                f"💳 رصيدك المتبقي: **{sender['credits']:,}** كريدت"
            ),
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # === إرسال DM للمرسل ===
        try:
            sender_dm_embed = discord.Embed(
                title="💸 تم التحويل بنجاح!",
                description=(
                    f"**تم تحويل** `{amount:,}` **كريدت إلى** {target_member.mention} (`{target_member.display_name}`)\n\n"
                    f"💳 **رصيدك المتبقي:** `{sender['credits']:,}` كريدت"
                ),
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            sender_dm_embed.set_footer(text=f"🏦 Lake Bank — {interaction.guild.name}")
            await interaction.user.send(embed=sender_dm_embed)
        except Exception:
            pass

        # === إرسال DM للمستلم ===
        try:
            receiver_dm_embed = discord.Embed(
                title="📥 تم استلام كريدت!",
                description=(
                    f"**تم استلام** `{amount:,}` **كريدت من** {interaction.user.mention} (`{interaction.user.display_name}`)\n\n"
                    f"💳 **رصيدك الحالي:** `{receiver['credits']:,}` كريدت"
                ),
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            receiver_dm_embed.set_footer(text=f"🏦 Lake Bank — {interaction.guild.name}")
            await target_member.send(embed=receiver_dm_embed)
        except Exception:
            pass

        # === لوج التحويل ===
        try:
            await log_bank_transfer(bot, interaction.guild.id, interaction.user, target_member, amount)
        except Exception as e:
            print(f"Error logging bank transfer: {e}")


class TransfersSubView(View):
    def __init__(self, user_id):
        super().__init__(timeout=120)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ ده مش بنكك!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="📜 آخر التحويلات", style=discord.ButtonStyle.secondary, emoji="📜")
    async def view_transfers(self, interaction: discord.Interaction, button: Button):
        buser = get_bank_user(interaction.guild.id, interaction.user.id)
        transfers = buser.get("transfers", [])

        if not transfers:
            await interaction.response.send_message("📭 مفيش تحويلات لسه!", ephemeral=True)
            return

        lines = []
        for i, t in enumerate(transfers[:10]):
            date_str = ""
            try:
                dt = datetime.fromisoformat(t["date"])
                date_str = dt.strftime("%m/%d %H:%M")
            except:
                date_str = "?"

            if str(t["from_id"]) == str(interaction.user.id):
                lines.append(f"> 🔴 **-{t['amount']:,}** ➜ {t['to_name']} — `{date_str}`")
            else:
                lines.append(f"> 🟢 **+{t['amount']:,}** من {t['from_name']} — `{date_str}`")

        embed = discord.Embed(
            title="📜 آخر التحويلات",
            description="\n".join(lines),
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.set_footer(text=f"آخر {len(lines)} تحويلات")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="💸 تحويل كريدت", style=discord.ButtonStyle.success, emoji="💸")
    async def transfer_credits(self, interaction: discord.Interaction, button: Button):
        modal = TransferAmountModal()
        await interaction.response.send_modal(modal)


class LoanAmountModal(Modal, title="💰 سحب قرض"):
    amount_input = TextInput(
        label="مبلغ القرض (500 - 7000)",
        placeholder="مثال: 2000",
        required=True,
        max_length=6
    )

    async def on_submit(self, interaction: discord.Interaction):
        can_use, remaining = check_global_cooldown(interaction.user.id)
        if not can_use:
            await interaction.response.send_message(f"⏳ انتظر {remaining:.1f} ثانية!", ephemeral=True)
            return

        try:
            amount = int(self.amount_input.value.strip())
        except ValueError:
            await interaction.response.send_message("❌ أدخل رقم صحيح!", ephemeral=True)
            return

        user = get_user_data(interaction.guild.id, interaction.user.id)
        if user["level"] < BANK_MIN_LEVEL:
            await interaction.response.send_message(f"❌ لازم تكون **Level {BANK_MIN_LEVEL}** أو أعلى عشان تاخد قرض!", ephemeral=True)
            return

        buser = get_bank_user(interaction.guild.id, interaction.user.id)
        if buser["loan_amount"] > 0:
            await interaction.response.send_message(
                f"❌ عندك قرض مفتوح بالفعل بقيمة **{buser['loan_amount']:,}** كريدت!\nسد القرض الأول قبل ما تاخد واحد جديد.",
                ephemeral=True
            )
            return

        if amount < BANK_LOAN_MIN or amount > BANK_LOAN_MAX:
            await interaction.response.send_message(
                f"❌ المبلغ لازم يكون بين **{BANK_LOAN_MIN:,}** و **{BANK_LOAN_MAX:,}** كريدت!",
                ephemeral=True
            )
            return

        # إعطاء القرض
        buser["loan_amount"] = amount
        buser["loan_date"] = datetime.now().isoformat()
        save_bank_data(bank_data)

        user["credits"] += amount
        save_data(user_data)

        expiry = datetime.now() + timedelta(days=BANK_LOAN_DAYS)
        expiry_ts = int(expiry.timestamp())

        embed = discord.Embed(
            title="✅ تم سحب القرض بنجاح!",
            description=(
                f"**💰 مبلغ القرض:** {amount:,} كريدت\n"
                f"**💳 رصيدك الجديد:** {user['credits']:,} كريدت\n"
                f"**📅 آخر موعد للسداد:** <t:{expiry_ts}:F>\n"
                f"**⏰ متبقي:** <t:{expiry_ts}:R>\n\n"
                f"⚠️ **تحذير:** لو مسدتش القرض قبل الموعد، رصيدك هيكون **بالسالب**!"
            ),
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # === لوج سحب القرض ===
        try:
            await log_bank_loan(bot, interaction.user, amount, "سحب")
        except Exception as e:
            print(f"Error logging bank loan: {e}")


class RepayConfirmView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ ده مش بنكك!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✅ نعم، سد القرض", style=discord.ButtonStyle.success)
    async def confirm_repay(self, interaction: discord.Interaction, button: Button):
        buser = get_bank_user(interaction.guild.id, interaction.user.id)
        loan = buser.get("loan_amount", 0)

        if loan <= 0:
            await interaction.response.send_message("❌ مفيش قرض عليك!", ephemeral=True)
            return

        user = get_user_data(interaction.guild.id, interaction.user.id)
        if user["credits"] < loan:
            await interaction.response.send_message(
                f"❌ رصيدك مش كفاية! محتاج **{loan:,}** كريدت ومعاك **{user['credits']:,}** كريدت.",
                ephemeral=True
            )
            return

        user["credits"] -= loan
        save_data(user_data)

        buser["loan_amount"] = 0
        buser["loan_date"] = None
        save_bank_data(bank_data)

        embed = discord.Embed(
            title="✅ تم سداد القرض بنجاح!",
            description=(
                f"**💰 المبلغ المسدد:** {loan:,} كريدت\n"
                f"**💳 رصيدك المتبقي:** {user['credits']:,} كريدت\n\n"
                f"✨ أحسنت! دلوقتي تقدر تاخد قرض جديد."
            ),
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # === لوج سداد القرض ===
        try:
            await log_bank_loan(bot, interaction.user, loan, "سداد")
        except Exception as e:
            print(f"Error logging bank loan repay: {e}")

        self.stop()

    @discord.ui.button(label="❌ لا، إلغاء", style=discord.ButtonStyle.danger)
    async def cancel_repay(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("👌 تم الإلغاء.", ephemeral=True)
        self.stop()


class InvestmentAmountModal(Modal, title="📈 مبلغ الاستثمار"):
    amount_input = TextInput(
        label="كم كريدت عايز تستثمر؟",
        placeholder="من 500 لـ 5000",
        required=True,
        max_length=10
    )

    def __init__(self, company_key):
        super().__init__()
        self.company_key = company_key

    async def on_submit(self, interaction: discord.Interaction):
        can_use, remaining = check_global_cooldown(interaction.user.id)
        if not can_use:
            await interaction.response.send_message(f"⏳ انتظر {remaining:.1f} ثانية!", ephemeral=True)
            return

        try:
            amount = int(self.amount_input.value.strip())
        except ValueError:
            await interaction.response.send_message("❌ أدخل رقم صحيح!", ephemeral=True)
            return

        if amount < BANK_MIN_INVEST:
            await interaction.response.send_message(f"❌ أقل مبلغ للاستثمار هو **{BANK_MIN_INVEST:,}** كريدت!", ephemeral=True)
            return

        if amount > BANK_MAX_INVEST:
            await interaction.response.send_message(f"❌ أعلى مبلغ للاستثمار هو **{BANK_MAX_INVEST:,}** كريدت!", ephemeral=True)
            return

        user = get_user_data(interaction.guild.id, interaction.user.id)
        if user["level"] < BANK_MIN_LEVEL:
            await interaction.response.send_message(f"❌ لازم تكون **Level {BANK_MIN_LEVEL}** أو أعلى!", ephemeral=True)
            return

        remaining_inv = get_investments_remaining(interaction.guild.id, interaction.user.id)
        if remaining_inv <= 0:
            await interaction.response.send_message(
                "❌ استنفذت عدد الاستثمارات (5/5)! ارجع بعد 4 ساعات.",
                ephemeral=True
            )
            return

        if user["credits"] < amount:
            await interaction.response.send_message(
                f"❌ رصيدك مش كفاية! معاك **{user['credits']:,}** كريدت",
                ephemeral=True
            )
            return

        company = BANK_COMPANIES.get(self.company_key)
        if not company:
            await interaction.response.send_message("❌ شركة غير موجودة!", ephemeral=True)
            return

        # خصم المبلغ
        user["credits"] -= amount
        save_data(user_data)

        # تحديث عداد الاستثمارات
        buser = get_bank_user(interaction.guild.id, interaction.user.id)
        buser["investments_today"] += 1
        save_bank_data(bank_data)

        # وقت الانتظار
        wait_time = random.randint(60, 180)  # 1-3 دقايق
        wait_minutes = wait_time // 60
        wait_seconds = wait_time % 60

        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"📈 تم استثمارك — {company['name']}",
                description=(
                    f"**الشركة:** {company['name']}\n"
                    f"**المبلغ:** {amount:,} كريدت\n"
                    f"**مدة الاستثمار:** {wait_minutes} دقيقة{'و ' + str(wait_seconds) + ' ثانية' if wait_seconds > 0 else ''}\n"
                    f"**نسبة الفوز:** {company['win_rate']}%\n"
                    f"{'**شركة خطرة!** لو فزت هتاخد ' + str(company['multiplier']) + 'x كريدت' if company['risky'] else f'**الفائدة:** {int(BANK_INTEREST_RATE * 100)}%'}\n\n"
                    f"هنبعتلك النتيجة على الخاص بعد انتهاء مدة الاستثمار..."
                ),
                color=discord.Color.gold(),
                timestamp=datetime.now()
            ),
            ephemeral=True
        )

        # انتظار ثم إرسال النتيجة على الخاص
        await asyncio.sleep(wait_time)

        # تحديد النتيجة
        win_roll = random.randint(1, 100)
        won = win_roll <= company["win_rate"]

        if won:
            if company["risky"]:
                profit = amount * company["multiplier"]  # مضاعف حسب الشركة
            else:
                profit = amount + int(amount * BANK_INTEREST_RATE)  # المبلغ + 50% فائدة

            user_fresh = get_user_data(interaction.guild.id, interaction.user.id)
            user_fresh["credits"] += profit
            save_data(user_data)

            result_img = create_investment_result_image(company["name"], True, amount, profit)

            embed = discord.Embed(
                title=f"✅ نجح استثمارك! — {company['name']}",
                description=(
                    f"**الشركة:** {company['name']}\n"
                    f"**المبلغ المستثمر:** {amount:,} كريدت\n"
                    f"**الربح:** {profit:,} كريدت"
                    f"{f' ({company["multiplier"]}x لأنها شركة خطرة!)' if company['risky'] else f' (المبلغ + {int(BANK_INTEREST_RATE * 100)}% فائدة)'}\n"
                    f"**رصيدك الجديد:** {user_fresh['credits']:,} كريدت"
                ),
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
        else:
            result_img = create_investment_result_image(company["name"], False, amount)

            user_fresh = get_user_data(interaction.guild.id, interaction.user.id)
            embed = discord.Embed(
                title=f"❌ فشل استثمارك — {company['name']}",
                description=(
                    f"**الشركة:** {company['name']}\n"
                    f"**المبلغ المفقود:** {amount:,} كريدت\n"
                    f"**لقد خسرت كل المبلغ**\n"
                    f"**رصيدك الحالي:** {user_fresh['credits']:,} كريدت"
                ),
                color=discord.Color.red(),
                timestamp=datetime.now()
            )

        embed.set_image(url="attachment://investment_result.png")
        file = discord.File(result_img, filename="investment_result.png")

        try:
            await interaction.user.send(embed=embed, file=file)
        except discord.Forbidden:
            # لو الخاص مقفول، نبعت في نفس القناة
            try:
                await interaction.followup.send(
                    content=f"{interaction.user.mention} مقدرناش نبعتلك على الخاص! النتيجة هنا:",
                    embed=embed,
                    file=file,
                    ephemeral=True
                )
            except:
                pass

        # === لوج الاستثمار ===
        try:
            await log_bank_investment(bot, interaction.user, company["name"], amount, won, profit if won else 0)
        except Exception as e:
            print(f"Error logging bank investment: {e}")


class InvestmentCompanySelect(Select):
    def __init__(self):
        options = []
        for key, company in BANK_COMPANIES.items():
            risk_label = f" ⚠️ خطر — {company['multiplier']}x" if company["risky"] else ""
            options.append(
                discord.SelectOption(
                    label=company["name"],
                    description=f"نسبة الفوز: {company['win_rate']}%{risk_label}",
                    value=key,
                    emoji=company.get("emoji")
                )
            )
        super().__init__(
            placeholder="شوف عايز تستثمر مع مين...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        company_key = self.values[0]
        modal = InvestmentAmountModal(company_key)
        await interaction.response.send_modal(modal)


class InvestmentView(View):
    def __init__(self, user_id):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.add_item(InvestmentCompanySelect())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ ده مش بنكك!", ephemeral=True)
            return False
        return True


class BankMainView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="التحويلات", style=discord.ButtonStyle.primary, emoji="💱", row=0, custom_id="bank_main:transfers")
    async def transfers_btn(self, interaction: discord.Interaction, button: Button):
        try:
            can_use, remaining = check_global_cooldown(interaction.user.id)
            if not can_use:
                await interaction.response.send_message(f"⏳ انتظر {remaining:.1f} ثانية!", ephemeral=True)
                return

            user = get_user_data(interaction.guild.id, interaction.user.id)
            embed = discord.Embed(
                title="💱 التحويلات البنكية",
                description=(
                    f"💳 **رصيدك الحالي:** {user['credits']:,} كريدت\n\n"
                    f"اختر عملية من الأزرار أدناه:"
                ),
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            view = TransfersSubView(interaction.user.id)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            print(f"Error in transfers_btn: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ حصل خطأ، حاول تاني.", ephemeral=True)

    @discord.ui.button(label="سحب قرض", style=discord.ButtonStyle.success, emoji="💰", row=0, custom_id="bank_main:loan")
    async def loan_btn(self, interaction: discord.Interaction, button: Button):
        try:
            can_use, remaining = check_global_cooldown(interaction.user.id)
            if not can_use:
                await interaction.response.send_message(f"⏳ انتظر {remaining:.1f} ثانية!", ephemeral=True)
                return

            user = get_user_data(interaction.guild.id, interaction.user.id)
            if user["level"] < BANK_MIN_LEVEL:
                await interaction.response.send_message(
                    f"❌ لازم تكون **Level {BANK_MIN_LEVEL}** أو أعلى عشان تاخد قرض!\n📊 لفلك الحالي: **Level {user['level']}**",
                    ephemeral=True
                )
                return

            buser = get_bank_user(interaction.guild.id, interaction.user.id)
            if buser["loan_amount"] > 0:
                loan_date = datetime.fromisoformat(buser["loan_date"])
                expiry = loan_date + timedelta(days=BANK_LOAN_DAYS)
                expiry_ts = int(expiry.timestamp())
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="❌ عندك قرض مفتوح!",
                        description=(
                            f"**💰 مبلغ القرض:** {buser['loan_amount']:,} كريدت\n"
                            f"**📅 آخر موعد:** <t:{expiry_ts}:F>\n"
                            f"**⏰ متبقي:** <t:{expiry_ts}:R>\n\n"
                            f"سد القرض الأول عشان تقدر تاخد واحد جديد!"
                        ),
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
                return

            modal = LoanAmountModal()
            await interaction.response.send_modal(modal)
        except Exception as e:
            print(f"Error in loan_btn: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ حصل خطأ، حاول تاني.", ephemeral=True)

    @discord.ui.button(label="سد القرض", style=discord.ButtonStyle.danger, emoji="💳", row=0, custom_id="bank_main:repay")
    async def repay_btn(self, interaction: discord.Interaction, button: Button):
        try:
            can_use, remaining = check_global_cooldown(interaction.user.id)
            if not can_use:
                await interaction.response.send_message(f"⏳ انتظر {remaining:.1f} ثانية!", ephemeral=True)
                return

            buser = get_bank_user(interaction.guild.id, interaction.user.id)
            if buser.get("loan_amount", 0) <= 0:
                await interaction.response.send_message("✅ مفيش قرض عليك حالياً!", ephemeral=True)
                return

            user = get_user_data(interaction.guild.id, interaction.user.id)
            loan = buser["loan_amount"]

            embed = discord.Embed(
                title="💳 سد القرض",
                description=(
                    f"هل أنت عايز تسد قرضك بالفعل؟\n\n"
                    f"**💰 مبلغ القرض:** {loan:,} كريدت\n"
                    f"**💳 رصيدك الحالي:** {user['credits']:,} كريدت\n\n"
                    f"{'✅ رصيدك كافي!' if user['credits'] >= loan else '⚠️ رصيدك مش كافي لسداد القرض!'}"
                ),
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            view = RepayConfirmView(interaction.user.id)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            print(f"Error in repay_btn: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ حصل خطأ، حاول تاني.", ephemeral=True)

    @discord.ui.button(label="الاستثمار", style=discord.ButtonStyle.success, emoji="📈", row=1, custom_id="bank_main:invest")
    async def invest_btn(self, interaction: discord.Interaction, button: Button):
        try:
            can_use, remaining = check_global_cooldown(interaction.user.id)
            if not can_use:
                await interaction.response.send_message(f"⏳ انتظر {remaining:.1f} ثانية!", ephemeral=True)
                return

            user = get_user_data(interaction.guild.id, interaction.user.id)
            if user["level"] < BANK_MIN_LEVEL:
                await interaction.response.send_message(
                    f"❌ لازم تكون **Level {BANK_MIN_LEVEL}** أو أعلى عشان تستثمر!\n📊 لفلك الحالي: **Level {user['level']}**",
                    ephemeral=True
                )
                return

            remaining_inv = get_investments_remaining(interaction.guild.id, interaction.user.id)
            if remaining_inv <= 0:
                await interaction.response.send_message(
                    "❌ استنفذت عدد الاستثمارات (5/5)! ارجع بعد 4 ساعات.",
                    ephemeral=True
                )
                return

            embed = discord.Embed(
                title="📈 اختر شركة الاستثمار",
                description=(
                    f"**رصيدك:** {user['credits']:,} كريدت\n"
                    f"**المتبقي:** {remaining_inv}/{BANK_MAX_INVESTMENTS_PER_DAY}\n"
                    f"**الحد:** من {BANK_MIN_INVEST:,} لـ {BANK_MAX_INVEST:,} كريدت\n\n"
                    f"اختر الشركة من القائمة أدناه:"
                ),
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            view = InvestmentView(interaction.user.id)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            print(f"Error in invest_btn: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ حصل خطأ، حاول تاني.", ephemeral=True)

    @discord.ui.button(label="معلومات عن البنك", style=discord.ButtonStyle.secondary, emoji="ℹ️", row=1, custom_id="bank_main:info")
    async def info_btn(self, interaction: discord.Interaction, button: Button):
        try:
            embed = discord.Embed(
                title="🏦 معلومات عن Lake Bank",
                description=(
                    f"**📋 القواعد والمعلومات:**\n\n"
                    f"**💱 التحويلات:**\n"
                    f"> • تقدر تحول كريدت لأي عضو في السيرفر\n"
                    f"> • آخر 20 تحويلة بتتحفظ في السجل\n\n"
                    f"**💰 القروض:**\n"
                    f"> • الحد الأدنى: **{BANK_LOAN_MIN:,}** كريدت\n"
                    f"> • الحد الأقصى: **{BANK_LOAN_MAX:,}** كريدت\n"
                    f"> • مدة السداد: **{BANK_LOAN_DAYS}** أيام\n"
                    f"> • ⚠️ لو مسدتش في الوقت، رصيدك هيكون **بالسالب**\n"
                    f"> • مينفعش تاخد أكتر من قرض في نفس الوقت\n\n"
                    f"**📈 الاستثمار:**\n"
                    f"> • **5 شركات** متاحة للاستثمار\n"
                    f"> • 3 شركات عادية: **50%** نسبة فوز + **50%** فائدة\n"
                    f"> • 2 شركات خطرة: **30%** نسبة فوز (المملكة 3x / الجبنة الاسطنبولي 4x)\n"
                    f"> • مدة الاستثمار: **1-3 دقائق**\n"
                    f"> • الحد الأقصى: **{BANK_MAX_INVESTMENTS_PER_DAY}** استثمارات كل 4 ساعات\n"
                    f"> • النتيجة هتوصلك على الخاص\n"
                    f"> • لو خسرت بتخسر كل المبلغ\n\n"
                    f"**🔒 المتطلبات:**\n"
                    f"> • **Level {BANK_MIN_LEVEL}+** عشان تقدر تسحب قروض أو تستثمر\n\n"
                    f"**📊 الشركات:**\n"
                    f"> موكا الحرامية -- Muz -- سيف اللي مش حرامي\n"
                    f"> المملكة (خطر 3x) -- الجبنة الاسطنبولي (خطر 4x)"
                ),
                color=discord.Color.dark_gold(),
                timestamp=datetime.now()
            )
            embed.set_footer(text="Lake Bank — استثمر بحكمة!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"Error in info_btn: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ حصل خطأ، حاول تاني.", ephemeral=True)


@bot.tree.command(name="bank", description="🏦 البنك — تحويلات، قروض، واستثمار (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def slash_bank(interaction: discord.Interaction):
    await interaction.response.defer()

    # تحقق من القروض المنتهية
    check_loan_expiry()

    # صورة البنك
    stock_img = create_bank_stock_image()
    file = discord.File(stock_img, filename="bank_chart.png")

    embed = discord.Embed(
        title="🏦 Lake Bank",
        description="اختر عملية من الأزرار أدناه 👇",
        color=discord.Color.dark_gold()
    )
    embed.set_image(url="attachment://bank_chart.png")
    embed.set_footer(text="Lake Bank — استثمر بحكمة!")

    view = BankMainView()
    await interaction.followup.send(embed=embed, file=file, view=view)


# ========== أوامر أدمن البنك واللوجات ==========

@bot.tree.command(name="bank_setup", description="🏦 إعداد نظام البنك في الشانل الحالي (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def slash_bank_setup(interaction: discord.Interaction):
    await interaction.response.defer()

    channel = interaction.channel

    embed = discord.Embed(
        title="🏦 Lake Bank",
        description=(
            "**مرحباً بك في Lake Bank!**\n\n"
            "استخدم الأمر `/bank` عشان تفتح حسابك البنكي.\n\n"
            "**الخدمات المتاحة:**\n"
            "> 💱 **التحويلات** — حول كريدت لأي عضو\n"
            "> 💰 **القروض** — اسحب قرض وسده خلال 7 أيام\n"
            "> 📈 **الاستثمار** — استثمر في شركات مختلفة\n\n"
            "**الشركات العادية (50% فوز -- فائدة 50%):**\n"
            "> موكا الحرامية -- Muz -- سيف اللي مش حرامي\n\n"
            "**الشركات الخطرة (30% فوز):**\n"
            "> المملكة (3x كريدت) -- الجبنة الاسطنبولي (4x كريدت)\n\n"
            f"**🔒 المتطلبات:** Level {BANK_MIN_LEVEL}+ للقروض والاستثمار"
        ),
        color=discord.Color.dark_gold(),
        timestamp=datetime.now()
    )
    embed.set_footer(text="Lake Bank — استثمر بحكمة!")
    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)

    view = BankMainView()
    msg = await channel.send(embed=embed, view=view)
    try:
        await msg.pin()
    except Exception as e:
        print(f"Error pinning bank setup: {e}")

    confirm = discord.Embed(
        title="✅ تم إعداد البنك",
        description=f"تم إعداد نظام البنك في {channel.mention} وتثبيت الرسالة!",
        color=discord.Color.green()
    )
    await interaction.followup.send(embed=confirm, ephemeral=True)


@bot.tree.command(name="bank_logs", description="📊 إعداد لوج البنك في الشانل الحالي (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def slash_bank_logs(interaction: discord.Interaction):
    await interaction.response.defer()

    channel = interaction.channel
    guild_id = interaction.guild.id

    # حفظ الشانل كشانل لوج البنك
    set_bank_logs_channel(guild_id, channel.id)

    embed = discord.Embed(
        title="📊 Lake Bank — سجل الأحداث",
        description=(
            "**تم تفعيل لوج البنك في هذه الروم!**\n\n"
            "هيتم تسجيل كل الأحداث التالية هنا:\n\n"
            "> 📈 **الاستثمارات** — مين استثمر، في أنهي شركة، كسب ولا خسر\n"
            "> 💱 **التحويلات** — مين حول لمين وكام\n"
            "> 💰 **القروض** — سحب وسداد القروض\n\n"
            "كل حدث هيظهر بالتفصيل مع الوقت والتاريخ."
        ),
        color=discord.Color.dark_gold(),
        timestamp=datetime.now()
    )
    embed.set_footer(text="Lake Bank Logs — تتبع كل الأحداث")
    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)

    msg = await channel.send(embed=embed)
    try:
        await msg.pin()
    except Exception as e:
        print(f"Error pinning bank logs: {e}")

    confirm = discord.Embed(
        title="✅ تم إعداد لوج البنك",
        description=f"تم تفعيل لوج البنك في {channel.mention} وتثبيت الرسالة!\nكل أحداث البنك هتتسجل هنا.",
        color=discord.Color.green()
    )
    await interaction.followup.send(embed=confirm, ephemeral=True)


@bot.tree.command(name="role_logs", description="🎭 إعداد لوج الرتب في الشانل الحالي (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def slash_role_logs(interaction: discord.Interaction):
    await interaction.response.defer()

    channel = interaction.channel
    guild_id = interaction.guild.id

    # حفظ الشانل كشانل لوج الرتب
    set_role_logs_channel(guild_id, channel.id)

    embed = discord.Embed(
        title="🎭 سجل الرتب",
        description=(
            "**تم تفعيل لوج الرتب في هذه الروم!**\n\n"
            "هيتم تسجيل كل تغييرات الرتب هنا:\n\n"
            "> ✅ **إضافة رتبة** — لما حد ياخد رتبة جديدة\n"
            "> ❌ **إزالة رتبة** — لما رتبة تتشال من حد\n"
            "> 📊 **رتب اللفل** — الترقيات التلقائية\n\n"
            "كل تغيير هيظهر بالتفصيل مع الوقت والتاريخ والمنفذ."
        ),
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    embed.set_footer(text="Role Logs — تتبع كل تغييرات الرتب")
    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)

    msg = await channel.send(embed=embed)
    try:
        await msg.pin()
    except Exception as e:
        print(f"Error pinning role logs: {e}")

    confirm = discord.Embed(
        title="✅ تم إعداد لوج الرتب",
        description=f"تم تفعيل لوج الرتب في {channel.mention} وتثبيت الرسالة!\nكل تغييرات الرتب هتتسجل هنا.",
        color=discord.Color.green()
    )
    await interaction.followup.send(embed=confirm, ephemeral=True)


# ========== حدث البوست الجديد ==========

@bot.event
async def on_member_update(before, after):
    # === نوتيفيكيشن البوست ===
    if before.premium_since is None and after.premium_since is not None:
        guild_id = after.guild.id
        cfg = load_guild_config()
        channel_id = cfg.get(str(guild_id), {}).get("boost_channel")
        
        if channel_id:
            channel = bot.get_channel(int(channel_id))
            if channel:
                embed = discord.Embed(
                    title="🚀 New Booster!",
                    description=f"اوفففف تسلم ايدك يا كبير {after.mention} عمل بوست للسيرفر!\n\nاتمنى انك تشوف ال **Boost Perks** عشان تشوف المزايا الي اتفتحتلك 🚀",
                    color=discord.Color.purple(),
                    timestamp=datetime.now()
                )
                embed.set_thumbnail(url=after.display_avatar.url)
                await channel.send(embed=embed)

    # === تتبع تغييرات الرتب ===
    if before.roles != after.roles:
        guild_id = after.guild.id

        # الرتب المضافة
        added_roles = set(after.roles) - set(before.roles)
        for role in added_roles:
            if role.is_default():
                continue
            try:
                await log_role_change(bot, guild_id, after, role, "إضافة")
            except Exception as e:
                print(f"Error logging role add: {e}")

        # الرتب المزالة
        removed_roles = set(before.roles) - set(after.roles)
        for role in removed_roles:
            if role.is_default():
                continue
            try:
                await log_role_change(bot, guild_id, after, role, "إزالة")
            except Exception as e:
                print(f"Error logging role remove: {e}")

# ========== نظام المسابقات ==========

COMP_WIN_CREDITS = 250  # كريدت لكل إجابة صح

def load_comp_data():
    if os.path.exists(COMP_DATA_FILE):
        with open(COMP_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_comp_data(data):
    with open(COMP_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

comp_data = load_comp_data()

def get_comp_user(guild_id, user_id):
    gid = str(guild_id)
    uid = str(user_id)
    if gid not in comp_data:
        comp_data[gid] = {}
    if uid not in comp_data[gid]:
        comp_data[gid][uid] = {"points": 0, "name": "", "avatar_url": ""}
    return comp_data[gid][uid]

def get_comp_leaderboard(guild_id, top_n=10):
    gid = str(guild_id)
    if gid not in comp_data:
        return []
    users = []
    for uid, udata in comp_data[gid].items():
        if udata["points"] > 0:
            users.append({"user_id": uid, **udata})
    users.sort(key=lambda x: x["points"], reverse=True)
    return users[:top_n]

def reset_comp_leaderboard(guild_id):
    gid = str(guild_id)
    if gid in comp_data:
        comp_data[gid] = {}
        save_comp_data(comp_data)


async def create_comp_win_image(member, points, credits_earned):
    """صورة إجابة صح — تصميم مميز"""
    width, height = 700, 200
    bg_dark = (18, 18, 22)
    card_bg = (30, 32, 36)
    accent_gold = (255, 185, 0)
    accent_green = (80, 220, 120)
    white = (255, 255, 255)
    light_gray = (180, 180, 185)
    border_glow = (255, 185, 0)

    img = Image.new('RGB', (width, height), bg_dark)
    draw = ImageDraw.Draw(img)

    # خلفية الكارت مع حدود ذهبية
    draw.rounded_rectangle([8, 8, width - 8, height - 8], radius=18, fill=card_bg, outline=border_glow, width=2)

    # خط ذهبي علوي للزينة
    draw.rectangle([8, 8, width - 8, 14], fill=accent_gold)

    # الأفاتار بحلقة ذهبية
    avatar_size = 120
    avatar_x, avatar_y = 30, (height - avatar_size) // 2

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(str(member.display_avatar.url)) as resp:
                avatar_bytes = await resp.read()
        avatar_img = Image.open(BytesIO(avatar_bytes)).resize((avatar_size, avatar_size))

        # قناع دائري
        mask = Image.new('L', (avatar_size, avatar_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse([0, 0, avatar_size, avatar_size], fill=255)

        # حلقة ذهبية
        ring_size = avatar_size + 8
        ring_x = avatar_x - 4
        ring_y = avatar_y - 4
        draw.ellipse([ring_x, ring_y, ring_x + ring_size, ring_y + ring_size], outline=accent_gold, width=3)

        # لصق الأفاتار
        img.paste(avatar_img, (avatar_x, avatar_y), mask)
    except:
        draw.ellipse([avatar_x, avatar_y, avatar_x + avatar_size, avatar_y + avatar_size], fill=(60, 60, 65), outline=accent_gold, width=3)

    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        name_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        info_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except:
        title_font = ImageFont.load_default()
        name_font = ImageFont.load_default()
        info_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    text_x = avatar_x + avatar_size + 30

    # اسم العضو
    display_name = member.display_name
    if len(display_name) > 18:
        display_name = display_name[:16] + ".."
    draw.text((text_x, 30), display_name, fill=white, font=name_font)

    # خط فاصل صغير
    draw.line([(text_x, 60), (text_x + 250, 60)], fill=(60, 62, 68), width=1)

    # نقطة + كريدت في صناديق
    # صندوق النقطة
    box_y = 75
    draw.rounded_rectangle([text_x, box_y, text_x + 150, box_y + 40], radius=8, fill=(40, 45, 40), outline=accent_green, width=2)
    draw.text((text_x + 12, box_y + 8), f"+1 Point", fill=accent_green, font=info_font)

    # صندوق الكريدت
    draw.rounded_rectangle([text_x + 165, box_y, text_x + 370, box_y + 40], radius=8, fill=(45, 42, 30), outline=accent_gold, width=2)
    draw.text((text_x + 177, box_y + 8), f"+{credits_earned:,} Credits", fill=accent_gold, font=info_font)

    # مجموع النقاط
    draw.text((text_x, 130), f"Total: {points} Points", fill=light_gray, font=small_font)

    # علامة صح
    check_x = width - 60
    check_y = height // 2 - 15
    draw.text((check_x, check_y), "W", fill=accent_green, font=title_font)

    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf


async def create_comp_leaderboard_image(guild, leaderboard):
    """لوحة المتصدرين — بوديوم مع أفاتارات"""
    width, height = 900, 650
    bg_dark = (14, 14, 18)
    card_bg = (28, 30, 34)
    gold = (255, 200, 50)
    silver = (190, 195, 210)
    bronze = (210, 140, 60)
    white = (255, 255, 255)
    light_gray = (160, 162, 168)
    green = (80, 220, 120)
    dim_text = (120, 122, 128)

    img = Image.new('RGB', (width, height), bg_dark)
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
        rank_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        name_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        points_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 17)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        list_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except:
        title_font = name_font = rank_font = points_font = small_font = list_font = ImageFont.load_default()

    # عنوان
    title_text = "Competition Leaderboard"
    t_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    t_w = t_bbox[2] - t_bbox[0]
    draw.text(((width - t_w) // 2, 15), title_text, fill=gold, font=title_font)

    # خط تحت العنوان
    draw.line([(100, 55), (width - 100, 55)], fill=(50, 52, 58), width=2)

    if not leaderboard:
        empty_text = "No competition data yet"
        e_bbox = draw.textbbox((0, 0), empty_text, font=name_font)
        e_w = e_bbox[2] - e_bbox[0]
        draw.text(((width - e_w) // 2, height // 2 - 10), empty_text, fill=dim_text, font=name_font)
        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return buf

    # تحميل أفاتارات أول 3 لاعبين
    avatars = []
    async with aiohttp.ClientSession() as session:
        for i, entry in enumerate(leaderboard[:3]):
            try:
                url = entry.get("avatar_url", "")
                if url:
                    async with session.get(url) as resp:
                        av_bytes = await resp.read()
                    avatars.append(Image.open(BytesIO(av_bytes)))
                else:
                    avatars.append(None)
            except:
                avatars.append(None)

    podium_colors = [gold, silver, bronze]
    podium_labels = ["#1", "#2", "#3"]
    # مواقع البوديوم: المركز الأول في النص، الثاني شمال، الثالث يمين
    podium_positions = [
        (width // 2 - 110, 70, 220, 280),    # #1 وسط (أطول)
        (50, 120, 200, 230),                   # #2 شمال
        (width - 250, 130, 200, 220),          # #3 يمين
    ]
    avatar_sizes = [100, 80, 80]

    for i in range(min(3, len(leaderboard))):
        entry = leaderboard[i]
        px, py, pw, ph = podium_positions[i]
        color = podium_colors[i]
        av_size = avatar_sizes[i]

        # صندوق البوديوم
        draw.rounded_rectangle([px, py, px + pw, py + ph], radius=14, fill=card_bg, outline=color, width=3)

        # الأفاتار
        av_x = px + (pw - av_size) // 2
        av_y = py + 15

        if i < len(avatars) and avatars[i]:
            try:
                av_img = avatars[i].resize((av_size, av_size))
                mask = Image.new('L', (av_size, av_size), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse([0, 0, av_size, av_size], fill=255)

                # حلقة
                ring_pad = 4
                draw.ellipse([av_x - ring_pad, av_y - ring_pad, av_x + av_size + ring_pad, av_y + av_size + ring_pad], outline=color, width=3)
                img.paste(av_img, (av_x, av_y), mask)
            except:
                draw.ellipse([av_x, av_y, av_x + av_size, av_y + av_size], fill=(50, 52, 58), outline=color, width=3)
        else:
            draw.ellipse([av_x, av_y, av_x + av_size, av_y + av_size], fill=(50, 52, 58), outline=color, width=3)

        # الاسم
        name = entry.get("name", "Unknown")
        if len(name) > 14:
            name = name[:12] + ".."
        n_bbox = draw.textbbox((0, 0), name, font=name_font)
        n_w = n_bbox[2] - n_bbox[0]
        draw.text((px + (pw - n_w) // 2, av_y + av_size + 10), name, fill=white, font=name_font)

        # الترتيب
        r_bbox = draw.textbbox((0, 0), podium_labels[i], font=rank_font)
        r_w = r_bbox[2] - r_bbox[0]
        draw.text((px + (pw - r_w) // 2, av_y + av_size + 35), podium_labels[i], fill=color, font=rank_font)

        # النقاط
        pts_text = f"{entry['points']} Points"
        p_bbox = draw.textbbox((0, 0), pts_text, font=points_font)
        p_w = p_bbox[2] - p_bbox[0]
        draw.text((px + (pw - p_w) // 2, av_y + av_size + 75), pts_text, fill=green, font=points_font)

        # الكريدت
        creds = entry['points'] * COMP_WIN_CREDITS
        cr_text = f"{creds:,} Credits"
        c_bbox = draw.textbbox((0, 0), cr_text, font=small_font)
        c_w = c_bbox[2] - c_bbox[0]
        draw.text((px + (pw - c_w) // 2, av_y + av_size + 98), cr_text, fill=gold, font=small_font)

    # باقي المراكز (4-10) كقائمة تحت البوديوم
    list_y_start = 380
    if len(leaderboard) > 3:
        draw.line([(50, list_y_start - 10), (width - 50, list_y_start - 10)], fill=(40, 42, 48), width=1)

        for i, entry in enumerate(leaderboard[3:], start=4):
            row_y = list_y_start + (i - 4) * 36
            if row_y > height - 40:
                break

            # صف مع خلفية متبادلة
            row_bg = (32, 34, 38) if i % 2 == 0 else (26, 28, 32)
            draw.rounded_rectangle([50, row_y, width - 50, row_y + 32], radius=6, fill=row_bg)

            # الترتيب
            draw.text((70, row_y + 5), f"#{i}", fill=dim_text, font=list_font)

            # الاسم
            name = entry.get("name", "Unknown")
            if len(name) > 20:
                name = name[:18] + ".."
            draw.text((130, row_y + 5), name, fill=white, font=list_font)

            # النقاط
            pts_text = f"{entry['points']} pts"
            draw.text((500, row_y + 5), pts_text, fill=green, font=list_font)

            # الكريدت
            creds = entry['points'] * COMP_WIN_CREDITS
            draw.text((650, row_y + 5), f"{creds:,} cr", fill=gold, font=list_font)

    # فوتر
    footer_text = f"Lake Competition"
    f_bbox = draw.textbbox((0, 0), footer_text, font=small_font)
    f_w = f_bbox[2] - f_bbox[0]
    draw.text(((width - f_w) // 2, height - 25), footer_text, fill=dim_text, font=small_font)

    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf


# === أوامر المسابقة ===

@bot.command(name="W")
async def cmd_comp_win(ctx, member: discord.Member = None):
    """اختصار: .W @عضو — يعطي نقطة + 250 كريدت"""
    if not can_use_comp_win(ctx.author):
        await ctx.send("❌ مالكش صلاحية لاستخدام أمر .W!", delete_after=3)
        return

    if not member:
        await ctx.send("منشن العضو! مثال: `.W @عضو`", delete_after=5)
        return

    if member.bot:
        await ctx.send("مينفعش تمنشن بوت!", delete_after=3)
        return

    # تحديث نقاط المسابقة
    comp_user = get_comp_user(ctx.guild.id, member.id)
    comp_user["points"] += 1
    comp_user["name"] = member.display_name
    comp_user["avatar_url"] = str(member.display_avatar.url)
    save_comp_data(comp_data)

    # إضافة كريدت
    user = get_user_data(ctx.guild.id, member.id)
    user["credits"] += COMP_WIN_CREDITS
    save_data(user_data)

    # إنشاء صورة الفوز
    win_img = await create_comp_win_image(member, comp_user["points"], COMP_WIN_CREDITS)
    file = discord.File(win_img, filename="comp_win.png")
    await ctx.send(file=file)

    # حذف رسالة الأمر
    try:
        await ctx.message.delete()
    except:
        pass


@bot.command(name="L")
async def cmd_comp_leaderboard(ctx):
    """اختصار: .L — يعرض لوحة المتصدرين"""
    if not can_use_comp_leaderboard(ctx.author):
        await ctx.send("❌ مالكش صلاحية لاستخدام أمر .L!", delete_after=3)
        return
    
    leaderboard = get_comp_leaderboard(ctx.guild.id)
    lb_img = await create_comp_leaderboard_image(ctx.guild, leaderboard)
    file = discord.File(lb_img, filename="comp_leaderboard.png")
    await ctx.send(file=file)

    try:
        await ctx.message.delete()
    except:
        pass


@bot.tree.command(name="lead_reset", description="ريست لوحة المسابقة")
async def slash_lead_reset(interaction: discord.Interaction):
    if not can_use_lead_reset(interaction.user):
        await interaction.response.send_message("❌ مالكش صلاحية لاستخدام أمر lead_reset!", ephemeral=True)
        return
    
    reset_comp_leaderboard(interaction.guild.id)
    await interaction.response.send_message(
        embed=discord.Embed(
            title="تم ريست لوحة المسابقة",
            description="تم مسح كل النقاط! اللوحة فاضية دلوقتي وجاهزة لمسابقة جديدة.",
            color=discord.Color.green()
        ),
        ephemeral=True
    )


# ========== نظام تقديم الإدارة ==========

def load_mod_logs_config():
    if os.path.exists(MOD_LOGS_FILE):
        with open(MOD_LOGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_mod_logs_config(cfg):
    with open(MOD_LOGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)

def get_mod_logs_channel(guild_id, app_type):
    """الحصول على شانل اللوج حسب النوع: trial_mod أو event_manager"""
    cfg = load_mod_logs_config()
    return cfg.get(str(guild_id), {}).get(app_type)

def set_mod_logs_channel(guild_id, app_type, channel_id):
    """تحديد شانل اللوج حسب النوع"""
    cfg = load_mod_logs_config()
    if str(guild_id) not in cfg:
        cfg[str(guild_id)] = {}
    cfg[str(guild_id)][app_type] = channel_id
    save_mod_logs_config(cfg)

async def send_mod_app_log(bot_instance, guild_id, app_type, member, answers):
    """إرسال لوج تقديم إدارة تلقائي للشانل المحدد"""
    channel_id = get_mod_logs_channel(guild_id, app_type)
    if not channel_id:
        return
    channel = bot_instance.get_channel(int(channel_id))
    if not channel:
        return

    if app_type == "event_manager":
        title = "🎉 تقديم جديد — Event Manager"
        color = discord.Color.blue()
    else:
        title = "🛡️ تقديم جديد — Trial Mod"
        color = discord.Color.red()

    embed = discord.Embed(
        title=title,
        color=color,
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 المتقدم", value=f"{member.mention}\n`{member}`", inline=True)
    embed.add_field(name="🆔 الآيدي", value=f"`{member.id}`", inline=True)
    embed.add_field(name="📅 التاريخ", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=True)

    for question, answer in answers.items():
        embed.add_field(name=f"❓ {question}", value=f"```{answer}```", inline=False)

    embed.set_footer(text="نظام تقديم الإدارة")

    try:
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Error sending mod app log: {e}")


class EventManagerModal(Modal, title="📋 تقديم Event Manager"):
    q1 = TextInput(label="اسمك وعمرك ولفلك؟", placeholder="مثال: أحمد - 20 سنة - لفل 15", required=True, max_length=150)
    q2 = TextInput(label="مده تفاعلك؟", placeholder="اكتب مده تفاعلك هنا...", required=True, max_length=100)
    q3 = TextInput(label="ليه عايز تكون Event Manager؟", placeholder="اكتب سببك هنا...", required=True, style=discord.TextStyle.paragraph, max_length=500)
    q4 = TextInput(label="ايه الي يخلينا نقبلك؟", placeholder="اكتب هنا...", required=True, style=discord.TextStyle.paragraph, max_length=500)
    q5 = TextInput(label="لو اتقبلت هتعمل فعاليات يومية ومنظمة؟", placeholder="اكتب إجابتك هنا...", required=True, style=discord.TextStyle.paragraph, max_length=500)

    async def on_submit(self, interaction: discord.Interaction):
        answers = {
            "اسمك وعمرك ولفلك": self.q1.value,
            "مده تفاعلك": self.q2.value,
            "ليه عايز تكون Event Manager": self.q3.value,
            "ايه الي يخلينا نقبلك": self.q4.value,
            "هتعمل فعاليات يومية ومنظمة": self.q5.value,
        }

        embed = discord.Embed(
            title="✅ تم إرسال تقديمك بنجاح!",
            description="تقديمك على **Event Manager** تم إرساله.\nالإدارة هتراجعه وهيتم الرد عليك.",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # إرسال اللوج تلقائي للشانل المحدد
        await send_mod_app_log(bot, interaction.guild.id, "event_manager", interaction.user, answers)


class TrialModModal(Modal, title="📋 تقديم Trial Mod"):
    q1 = TextInput(label="اسمك وعمرك ولفلك؟", placeholder="مثال: أحمد - 20 سنة - لفل 15", required=True, max_length=150)
    q2 = TextInput(label="مده تفاعلك وليك كام سنه في الديسكورد؟", placeholder="مثال: 5 ساعات يومياً - 3 سنين", required=True, max_length=150)
    q3 = TextInput(label="ليه حابب تبقا من الإدارة؟", placeholder="اكتب سببك هنا...", required=True, style=discord.TextStyle.paragraph, max_length=500)
    q4 = TextInput(label="لو بقيت إدارة ممكن نستفاد ايه منك؟", placeholder="اكتب هنا...", required=True, style=discord.TextStyle.paragraph, max_length=500)
    q5 = TextInput(label="لو حد عمل سبام/شتم ايه تصرفك؟", placeholder="اكتب موقفك هنا...", required=True, style=discord.TextStyle.paragraph, max_length=500)

    async def on_submit(self, interaction: discord.Interaction):
        answers = {
            "اسمك وعمرك ولفلك": self.q1.value,
            "مده تفاعلك وكام سنه في الديسكورد": self.q2.value,
            "ليه حابب تبقا من الإدارة": self.q3.value,
            "لو بقيت إدارة نستفاد ايه منك": self.q4.value,
            "لو حد عمل سبام أو شتم ايه تصرفك": self.q5.value,
        }

        embed = discord.Embed(
            title="✅ تم إرسال تقديمك بنجاح!",
            description="تقديمك على **Trial Mod** تم إرساله.\nالإدارة هتراجعه وهيتم الرد عليك.",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # إرسال اللوج تلقائي للشانل المحدد
        await send_mod_app_log(bot, interaction.guild.id, "trial_mod", interaction.user, answers)


class ModApplicationView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="تقديم Event Manager", style=discord.ButtonStyle.secondary, emoji="🎉", custom_id="mod_apply:event_manager")
    async def event_manager_btn(self, interaction: discord.Interaction, button: Button):
        modal = EventManagerModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="تقديم Trial Mod", style=discord.ButtonStyle.secondary, emoji="🛡️", custom_id="mod_apply:trial_mod")
    async def trial_mod_btn(self, interaction: discord.Interaction, button: Button):
        modal = TrialModModal()
        await interaction.response.send_modal(modal)


class ModApplicationViewDisabled(View):
    def __init__(self):
        super().__init__(timeout=None)
        btn1 = Button(label="تقديم Event Manager", style=discord.ButtonStyle.secondary, emoji="🎉", custom_id="mod_apply_closed:event_manager", disabled=True)
        btn2 = Button(label="تقديم Trial Mod", style=discord.ButtonStyle.secondary, emoji="🛡️", custom_id="mod_apply_closed:trial_mod", disabled=True)
        self.add_item(btn1)
        self.add_item(btn2)


@bot.tree.command(name="mods", description="📋 فتح نظام تقديم الإدارة (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def slash_mods(interaction: discord.Interaction):
    await interaction.response.defer()

    embed = discord.Embed(
        title="📋 تقديم الإدارة",
        description=(
            "**مرحباً بك في نظام تقديم الإدارة!**\n\n"
            "اختر الوظيفة اللي عايز تقدم عليها من الأزرار أدناه 👇\n\n"
            "🎉 **Event Manager** — مسؤول عن الفعاليات والأنشطة\n"
            "🛡️ **Trial Mod** — مود تجريبي للإدارة\n\n"
            "⚠️ **ملاحظة:** التقديم مرة واحدة فقط، اكتب إجاباتك بعناية!"
        ),
        color=discord.Color.purple(),
        timestamp=datetime.now()
    )
    embed.set_footer(text="نظام تقديم الإدارة")

    view = ModApplicationView()

    if os.path.exists(MOD_APPS_IMAGE):
        file = discord.File(MOD_APPS_IMAGE, filename="mod_apply.jpg")
        embed.set_image(url="attachment://mod_apply.jpg")
        await interaction.followup.send(embed=embed, file=file, view=view)
    else:
        await interaction.followup.send(embed=embed, view=view)


@bot.tree.command(name="close_mod", description="🔒 قفل تقديم الإدارة (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def slash_close_mod(interaction: discord.Interaction):
    await interaction.response.defer()

    channel = interaction.channel
    found = False

    async for message in channel.history(limit=50):
        if message.author == bot.user and message.embeds:
            for emb in message.embeds:
                if emb.title and "تقديم الإدارة" in emb.title:
                    closed_embed = discord.Embed(
                        title="📋 تقديم الإدارة — مغلق 🔒",
                        description=(
                            "**التقديم مغلق حالياً!**\n\n"
                            "التقديم على الإدارة مقفول دلوقتي.\n"
                            "استنى لحد ما الإدارة تفتح التقديم تاني."
                        ),
                        color=discord.Color.dark_grey(),
                        timestamp=datetime.now()
                    )
                    closed_embed.set_footer(text="نظام تقديم الإدارة — مغلق")
                    disabled_view = ModApplicationViewDisabled()
                    await message.edit(embed=closed_embed, view=disabled_view)
                    found = True
                    break
        if found:
            break

    if found:
        await interaction.followup.send(
            embed=discord.Embed(title="🔒 تم قفل التقديم!", description="تم قفل نظام تقديم الإدارة بنجاح.", color=discord.Color.red()),
            ephemeral=True
        )
    else:
        await interaction.followup.send(
            embed=discord.Embed(title="❌ مفيش رسالة تقديم!", description="مفيش رسالة تقديم إدارة في آخر 50 رسالة في الشانل دي.", color=discord.Color.red()),
            ephemeral=True
        )


@bot.tree.command(name="logs_mod", description="📜 تحديد شانل لوجات تقديمات Trial Mod (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(channel="الشانل اللي هيتبعت فيها لوجات تقديمات Trial Mod")
async def slash_logs_mod(interaction: discord.Interaction, channel: discord.TextChannel):
    set_mod_logs_channel(interaction.guild.id, "trial_mod", channel.id)
    await interaction.response.send_message(
        embed=discord.Embed(
            title="✅ تم تحديد شانل لوجات Trial Mod!",
            description=f"كل تقديم جديد على **Trial Mod** هيتبعت تلقائي في {channel.mention}",
            color=discord.Color.green()
        ),
        ephemeral=True
    )


@bot.tree.command(name="logs_event_manager", description="📜 تحديد شانل لوجات تقديمات Event Manager (أدمن فقط)")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(channel="الشانل اللي هيتبعت فيها لوجات تقديمات Event Manager")
async def slash_logs_event_manager(interaction: discord.Interaction, channel: discord.TextChannel):
    set_mod_logs_channel(interaction.guild.id, "event_manager", channel.id)
    await interaction.response.send_message(
        embed=discord.Embed(
            title="✅ تم تحديد شانل لوجات Event Manager!",
            description=f"كل تقديم جديد على **Event Manager** هيتبعت تلقائي في {channel.mention}",
            color=discord.Color.green()
        ),
        ephemeral=True
    )


# ========== الجزء: نظام الداشبورد المتكامل ==========

DASHBOARD_CONFIG_FILE = 'dashboard_config.json'

def load_dashboard_config():
    if os.path.exists(DASHBOARD_CONFIG_FILE):
        with open(DASHBOARD_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_dashboard_config(cfg):
    with open(DASHBOARD_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)

def get_dashboard_guild_config(guild_id):
    cfg = load_dashboard_config()
    gid = str(guild_id)
    if gid not in cfg:
        cfg[gid] = {
            "welcome_channel": None,
            "welcome_message": "your journey brings to our kingdom *gates*, you are our {count} traveller, your tale begins now.",
            "welcome_image": None,
            "welcome_title": "Greetings, {member}",
            "welcome_footer": "we hope you enjoy your time here.\ncheck our channels!",
            "goodbye_channel": None,
            "goodbye_message": "وداعاً {member}! 😢",
            "auto_role": None,
            "command_prefix": ".",
            "aliases": {},
        }
        save_dashboard_config(cfg)
    return cfg[gid]

def set_dashboard_guild_config(guild_id, key, value):
    cfg = load_dashboard_config()
    gid = str(guild_id)
    if gid not in cfg:
        cfg[gid] = {}
    cfg[gid][key] = value
    save_dashboard_config(cfg)


# ===== ثيم الداشبورد =====
DASH_COLOR_MAIN = 0x2B2D31       # رمادي داكن أنيق
DASH_COLOR_SUCCESS = 0x57F287    # أخضر
DASH_COLOR_WARNING = 0xFEE75C    # أصفر
DASH_COLOR_DANGER = 0xED4245     # أحمر
DASH_COLOR_INFO = 0x5865F2       # أزرق ديسكورد
DASH_COLOR_ACCENT = 0xEB459E     # وردي


# ==========================================
#       الداشبورد الرئيسي - القائمة
# ==========================================

class DashboardMainView(View):
    def __init__(self, guild: discord.Guild, author_id: int):
        super().__init__(timeout=300)
        self.guild = guild
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ الداشبورد ده مش ليك!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="📋 اللوجات", style=discord.ButtonStyle.primary, emoji="📋", row=0)
    async def logs_btn(self, interaction: discord.Interaction, button: Button):
        embed, view = build_logs_panel(self.guild, self.author_id)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="⚙️ نظام اللفل", style=discord.ButtonStyle.primary, emoji="⚙️", row=0)
    async def level_btn(self, interaction: discord.Interaction, button: Button):
        embed, view = build_level_panel(self.guild, self.author_id)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🎙️ VC XP", style=discord.ButtonStyle.primary, emoji="🎙️", row=0)
    async def vc_btn(self, interaction: discord.Interaction, button: Button):
        embed, view = build_vc_panel(self.guild, self.author_id)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🛡️ الحماية", style=discord.ButtonStyle.primary, emoji="🛡️", row=0)
    async def anticheat_btn(self, interaction: discord.Interaction, button: Button):
        embed, view = build_anticheat_panel(self.guild, self.author_id)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="👋 الترحيب", style=discord.ButtonStyle.success, emoji="👋", row=1)
    async def welcome_btn(self, interaction: discord.Interaction, button: Button):
        embed, view = build_welcome_panel(self.guild, self.author_id)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🎭 الصلاحيات", style=discord.ButtonStyle.success, emoji="🎭", row=1)
    async def perms_btn(self, interaction: discord.Interaction, button: Button):
        embed, view = build_permissions_panel(self.guild, self.author_id)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🎫 التيكت", style=discord.ButtonStyle.success, emoji="🎫", row=1)
    async def ticket_btn(self, interaction: discord.Interaction, button: Button):
        embed, view = build_ticket_panel(self.guild, self.author_id)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="📊 نظرة عامة", style=discord.ButtonStyle.secondary, emoji="📊", row=2)
    async def overview_btn(self, interaction: discord.Interaction, button: Button):
        embed, view = build_overview_panel(self.guild, self.author_id)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🔤 الاختصارات", style=discord.ButtonStyle.secondary, emoji="🔤", row=2)
    async def aliases_btn(self, interaction: discord.Interaction, button: Button):
        embed, view = build_aliases_panel(self.guild, self.author_id)
        await interaction.response.edit_message(embed=embed, view=view)


def build_main_dashboard_embed(guild: discord.Guild):
    total_members = guild.member_count or len(guild.members)
    online = sum(1 for m in guild.members if m.status != discord.Status.offline)
    bots = sum(1 for m in guild.members if m.bot)
    humans = total_members - bots

    level_status = "✅ مفعل" if is_level_enabled(guild.id) else "❌ معطل"
    anticheat_status = "✅ مفعل" if is_anti_cheat_enabled(guild.id) else "❌ معطل"

    embed = discord.Embed(
        title="",
        description="",
        color=DASH_COLOR_MAIN,
        timestamp=datetime.now()
    )

    # Header
    embed.set_author(
        name=f"🎛️ لوحة التحكم — {guild.name}",
        icon_url=guild.icon.url if guild.icon else None
    )

    embed.description = (
        f"```ansi\n"
        f"\u001b[2;36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\u001b[0m\n"
        f"\u001b[1;37m   مرحباً في لوحة التحكم الخاصة بالبوت   \u001b[0m\n"
        f"\u001b[2;36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\u001b[0m\n"
        f"```\n"
        f"اختر قسم من الأزرار بالأسفل للتعديل على إعدادات السيرفر.\n"
        f"كل التغييرات بتتحفظ تلقائياً وبتكون خاصة بالسيرفر ده بس.\n"
    )

    embed.add_field(
        name="📊 إحصائيات سريعة",
        value=(
            f"> 👥 الأعضاء: **{humans:,}**\n"
            f"> 🤖 البوتات: **{bots:,}**\n"
            f"> 🟢 أونلاين: **{online:,}**"
        ),
        inline=True
    )

    embed.add_field(
        name="⚡ الحالة",
        value=(
            f"> 📈 اللفل: {level_status}\n"
            f"> 🛡️ الحماية: {anticheat_status}\n"
            f"> 📋 القنوات: **{len(guild.text_channels)}**"
        ),
        inline=True
    )

    embed.add_field(
        name="\u200b",
        value=(
            "```\n"
                "📋 اللوجات     ⚙️ اللفل     🎙️ VC XP\n"
                "🛡️ الحماية     👋 الترحيب   🎭 الصلاحيات\n"
                "🎫 التيكت     📊 نظرة عامة  🔤 الاختصارات\n"
            "```"
        ),
        inline=False
    )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.set_footer(text="لوحة التحكم • التغييرات تتحفظ تلقائياً", icon_url=guild.me.display_avatar.url if guild.me else None)

    return embed


# ==========================================
#       1. بانل اللوجات
# ==========================================

def build_logs_panel(guild: discord.Guild, author_id: int):
    cfg = load_guild_config()
    guild_cfg = cfg.get(str(guild.id), {})
    logs = guild_cfg.get("logs", {})

    log_types = {
        "general": "📝 عام",
        "join": "📥 دخول",
        "leave": "📤 خروج",
        "delete": "🗑️ حذف رسائل",
        "edit": "✏️ تعديل رسائل",
        "shop": "🛒 الشوب",
    }

    bank_ch = get_bank_logs_channel(guild.id)
    role_ch = get_role_logs_channel(guild.id)

    lines = []
    for key, label in log_types.items():
        ch_id = logs.get(key)
        if ch_id:
            lines.append(f"> {label}: <#{ch_id}>")
        else:
            lines.append(f"> {label}: `غير محدد` ⚠️")

    if bank_ch:
        lines.append(f"> 🏦 البنك: <#{bank_ch}>")
    else:
        lines.append(f"> 🏦 البنك: `غير محدد` ⚠️")

    if role_ch:
        lines.append(f"> 🎭 الرتب: <#{role_ch}>")
    else:
        lines.append(f"> 🎭 الرتب: `غير محدد` ⚠️")

    embed = discord.Embed(
        color=DASH_COLOR_INFO,
        timestamp=datetime.now()
    )
    embed.set_author(name="📋 إعدادات اللوجات", icon_url=guild.icon.url if guild.icon else None)
    embed.description = (
        f"```ansi\n"
        f"\u001b[1;34m   إعدادات قنوات اللوجات   \u001b[0m\n"
        f"```\n"
        f"حدد القنوات اللي هيتبعت فيها اللوجات:\n\n"
        + "\n".join(lines) +
        f"\n\n💡 **اختر نوع اللوج من القائمة وحدد القناة**"
    )
    embed.set_footer(text="لوحة التحكم • اللوجات")

    view = LogsSettingsView(guild, author_id)
    return embed, view


class LogTypeSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="عام", value="general", emoji="📝", description="اللوجات العامة"),
            discord.SelectOption(label="دخول", value="join", emoji="📥", description="لوج دخول الأعضاء"),
            discord.SelectOption(label="خروج", value="leave", emoji="📤", description="لوج خروج الأعضاء"),
            discord.SelectOption(label="حذف رسائل", value="delete", emoji="🗑️", description="لوج حذف الرسائل"),
            discord.SelectOption(label="تعديل رسائل", value="edit", emoji="✏️", description="لوج تعديل الرسائل"),
            discord.SelectOption(label="الشوب", value="shop", emoji="🛒", description="لوج الشراء من الشوب"),
            discord.SelectOption(label="البنك", value="bank", emoji="🏦", description="لوج عمليات البنك"),
            discord.SelectOption(label="الرتب", value="roles", emoji="🎭", description="لوج تغيير الرتب"),
        ]
        super().__init__(placeholder="اختر نوع اللوج...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        log_type = self.values[0]
        modal = LogChannelModal(log_type, interaction.guild)
        await interaction.response.send_modal(modal)


class LogChannelModal(Modal):
    def __init__(self, log_type: str, guild: discord.Guild):
        labels = {
            "general": "عام", "join": "دخول", "leave": "خروج",
            "delete": "حذف رسائل", "edit": "تعديل رسائل", "shop": "الشوب",
            "bank": "البنك", "roles": "الرتب"
        }
        super().__init__(title=f"📋 تحديد قناة لوج {labels.get(log_type, log_type)}")
        self.log_type = log_type
        self.guild = guild
        self.channel_input = TextInput(
            label="آيدي القناة أو اسمها",
            placeholder="مثال: 123456789 أو general-logs",
            required=True,
            max_length=100
        )
        self.add_item(self.channel_input)

    async def on_submit(self, interaction: discord.Interaction):
        value = self.channel_input.value.strip()

        # Try to find the channel
        channel = None
        # By ID
        if value.isdigit():
            channel = interaction.guild.get_channel(int(value))
        # By mention
        elif value.startswith("<#") and value.endswith(">"):
            try:
                ch_id = int(value[2:-1])
                channel = interaction.guild.get_channel(ch_id)
            except:
                pass
        # By name
        if not channel:
            channel = discord.utils.get(interaction.guild.text_channels, name=value.lower().replace("#", "").strip())

        if not channel:
            await interaction.response.send_message("❌ مش لاقي القناة دي! تأكد من الآيدي أو الاسم.", ephemeral=True)
            return

        if self.log_type == "bank":
            set_bank_logs_channel(interaction.guild.id, channel.id)
        elif self.log_type == "roles":
            set_role_logs_channel(interaction.guild.id, channel.id)
        else:
            set_log_channel(interaction.guild.id, self.log_type, channel.id)

        embed, view = build_logs_panel(interaction.guild, interaction.user.id)
        confirm_embed = discord.Embed(
            description=f"✅ تم تحديد {channel.mention} كقناة لوج بنجاح!",
            color=DASH_COLOR_SUCCESS
        )
        await interaction.response.edit_message(embed=embed, view=view)
        await interaction.followup.send(embed=confirm_embed, ephemeral=True)


class LogsSettingsView(View):
    def __init__(self, guild: discord.Guild, author_id: int):
        super().__init__(timeout=300)
        self.guild = guild
        self.author_id = author_id
        self.add_item(LogTypeSelect())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ مش ليك!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🔙 رجوع", style=discord.ButtonStyle.secondary, row=2)
    async def back_btn(self, interaction: discord.Interaction, button: Button):
        embed = build_main_dashboard_embed(self.guild)
        view = DashboardMainView(self.guild, self.author_id)
        await interaction.response.edit_message(embed=embed, view=view)


# ==========================================
#       2. بانل نظام اللفل
# ==========================================

def build_level_panel(guild: discord.Guild, author_id: int):
    enabled = is_level_enabled(guild.id)
    status_icon = "✅" if enabled else "❌"
    status_text = "مفعل" if enabled else "معطل"

    embed = discord.Embed(
        color=DASH_COLOR_INFO if enabled else DASH_COLOR_DANGER,
        timestamp=datetime.now()
    )
    embed.set_author(name="⚙️ إعدادات نظام اللفل", icon_url=guild.icon.url if guild.icon else None)

    embed.description = (
        f"```ansi\n"
        f"\u001b[1;33m   نظام اللفل والـ XP   \u001b[0m\n"
        f"```\n"
        f"> **الحالة:** {status_icon} {status_text}\n\n"
        f"**⏱️ إعدادات XP:**\n"
        f"> Cooldown: **{bot_config.get('xp_cooldown', 30)}** ثانية\n"
        f"> XP Range: **{bot_config.get('xp_min', 10)}** - **{bot_config.get('xp_max', 15)}**\n"
        f"> كريدت عند اللفل أب: **{bot_config.get('level_up_credits', 50)}**\n"
    )
    embed.set_footer(text="لوحة التحكم • نظام اللفل")

    view = LevelSettingsView(guild, author_id, enabled)
    return embed, view


class LevelSettingsView(View):
    def __init__(self, guild: discord.Guild, author_id: int, enabled: bool):
        super().__init__(timeout=300)
        self.guild = guild
        self.author_id = author_id
        self.enabled = enabled

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ مش ليك!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="تفعيل / إيقاف", style=discord.ButtonStyle.success, emoji="🔄", row=0)
    async def toggle_btn(self, interaction: discord.Interaction, button: Button):
        new_state = not self.enabled
        set_level_enabled(self.guild.id, new_state)
        self.enabled = new_state
        embed, view = build_level_panel(self.guild, self.author_id)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="تعديل الإعدادات", style=discord.ButtonStyle.primary, emoji="✏️", row=0)
    async def edit_btn(self, interaction: discord.Interaction, button: Button):
        modal = LevelSettingsModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🔙 رجوع", style=discord.ButtonStyle.secondary, row=1)
    async def back_btn(self, interaction: discord.Interaction, button: Button):
        embed = build_main_dashboard_embed(self.guild)
        view = DashboardMainView(self.guild, self.author_id)
        await interaction.response.edit_message(embed=embed, view=view)


class LevelSettingsModal(Modal, title="⚙️ إعدادات الـ XP"):
    cooldown_input = TextInput(
        label="Cooldown (ثانية)",
        placeholder=f"الحالي: {bot_config.get('xp_cooldown', 30)}",
        required=False,
        max_length=5
    )
    xp_min_input = TextInput(
        label="أقل XP",
        placeholder=f"الحالي: {bot_config.get('xp_min', 10)}",
        required=False,
        max_length=5
    )
    xp_max_input = TextInput(
        label="أقصى XP",
        placeholder=f"الحالي: {bot_config.get('xp_max', 15)}",
        required=False,
        max_length=5
    )
    credits_input = TextInput(
        label="كريدت عند اللفل أب",
        placeholder=f"الحالي: {bot_config.get('level_up_credits', 50)}",
        required=False,
        max_length=5
    )

    async def on_submit(self, interaction: discord.Interaction):
        global bot_config
        changed = []

        if self.cooldown_input.value.strip():
            try:
                val = max(1, int(self.cooldown_input.value.strip()))
                bot_config["xp_cooldown"] = val
                changed.append(f"⏱️ Cooldown: **{val}** ثانية")
            except ValueError:
                pass

        if self.xp_min_input.value.strip():
            try:
                val = max(1, min(1000, int(self.xp_min_input.value.strip())))
                bot_config["xp_min"] = val
                changed.append(f"📊 أقل XP: **{val}**")
            except ValueError:
                pass

        if self.xp_max_input.value.strip():
            try:
                val = max(1, min(1000, int(self.xp_max_input.value.strip())))
                bot_config["xp_max"] = val
                changed.append(f"📊 أقصى XP: **{val}**")
            except ValueError:
                pass

        if self.credits_input.value.strip():
            try:
                val = max(0, int(self.credits_input.value.strip()))
                bot_config["level_up_credits"] = val
                changed.append(f"💰 كريدت: **{val}**")
            except ValueError:
                pass

        if bot_config["xp_min"] > bot_config["xp_max"]:
            bot_config["xp_min"], bot_config["xp_max"] = bot_config["xp_max"], bot_config["xp_min"]

        save_config(bot_config)

        embed, view = build_level_panel(interaction.guild, interaction.user.id)
        await interaction.response.edit_message(embed=embed, view=view)
        if changed:
            confirm = discord.Embed(
                description="✅ **تم التحديث:**\n" + "\n".join(changed),
                color=DASH_COLOR_SUCCESS
            )
            await interaction.followup.send(embed=confirm, ephemeral=True)


# ==========================================
#       3. بانل VC XP
# ==========================================

def build_vc_panel(guild: discord.Guild, author_id: int):
    vc_cfg = get_guild_vc_config(guild.id)

    embed = discord.Embed(
        color=DASH_COLOR_INFO,
        timestamp=datetime.now()
    )
    embed.set_author(name="🎙️ إعدادات VC XP", icon_url=guild.icon.url if guild.icon else None)

    active_only_text = "✅ نعم" if vc_cfg.get("vc_active_only", False) else "❌ لا"

    embed.description = (
        f"```ansi\n"
        f"\u001b[1;35m   إعدادات XP الرومات الصوتية   \u001b[0m\n"
        f"```\n"
        f"> **⏱️ XP لكل دقيقة:** `{vc_cfg.get('vc_xp_per_minute', 10)}`\n"
        f"> **📊 مدى XP:** `{vc_cfg.get('vc_xp_min', 5)}` - `{vc_cfg.get('vc_xp_max', 15)}`\n"
        f"> **🎯 نشطين فقط:** {active_only_text}\n"
        f"> **🚀 مضاعف البوستر:** `{vc_cfg.get('vc_boost_multiplier', 1.5)}x`\n"
        f"\n💡 **اضغط على تعديل لتغيير الإعدادات**"
    )
    embed.set_footer(text="لوحة التحكم • VC XP")

    view = VCSettingsView(guild, author_id)
    return embed, view


class VCSettingsView(View):
    def __init__(self, guild: discord.Guild, author_id: int):
        super().__init__(timeout=300)
        self.guild = guild
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ مش ليك!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="تعديل الإعدادات", style=discord.ButtonStyle.primary, emoji="✏️", row=0)
    async def edit_btn(self, interaction: discord.Interaction, button: Button):
        modal = VCSettingsModal(self.guild.id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="تفعيل/إيقاف Active Only", style=discord.ButtonStyle.success, emoji="🎯", row=0)
    async def toggle_active_btn(self, interaction: discord.Interaction, button: Button):
        vc_cfg = get_guild_vc_config(self.guild.id)
        vc_cfg["vc_active_only"] = not vc_cfg.get("vc_active_only", False)
        set_guild_vc_config(self.guild.id, vc_cfg)
        embed, view = build_vc_panel(self.guild, self.author_id)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🔙 رجوع", style=discord.ButtonStyle.secondary, row=1)
    async def back_btn(self, interaction: discord.Interaction, button: Button):
        embed = build_main_dashboard_embed(self.guild)
        view = DashboardMainView(self.guild, self.author_id)
        await interaction.response.edit_message(embed=embed, view=view)


class VCSettingsModal(Modal, title="🎙️ إعدادات VC XP"):
    def __init__(self, guild_id):
        super().__init__()
        self.guild_id = guild_id
        vc_cfg = get_guild_vc_config(guild_id)
        self.xp_per_min = TextInput(
            label="XP لكل دقيقة",
            placeholder=f"الحالي: {vc_cfg.get('vc_xp_per_minute', 10)}",
            required=False, max_length=5
        )
        self.xp_min = TextInput(
            label="أقل XP",
            placeholder=f"الحالي: {vc_cfg.get('vc_xp_min', 5)}",
            required=False, max_length=5
        )
        self.xp_max = TextInput(
            label="أقصى XP",
            placeholder=f"الحالي: {vc_cfg.get('vc_xp_max', 15)}",
            required=False, max_length=5
        )
        self.boost_mult = TextInput(
            label="مضاعف البوستر (مثلاً 1.5)",
            placeholder=f"الحالي: {vc_cfg.get('vc_boost_multiplier', 1.5)}",
            required=False, max_length=5
        )
        self.add_item(self.xp_per_min)
        self.add_item(self.xp_min)
        self.add_item(self.xp_max)
        self.add_item(self.boost_mult)

    async def on_submit(self, interaction: discord.Interaction):
        vc_cfg = get_guild_vc_config(self.guild_id)
        changed = []

        if self.xp_per_min.value.strip():
            try:
                val = max(1, min(100, int(self.xp_per_min.value.strip())))
                vc_cfg["vc_xp_per_minute"] = val
                changed.append(f"⏱️ XP/دقيقة: **{val}**")
            except ValueError:
                pass
        if self.xp_min.value.strip():
            try:
                val = max(1, min(100, int(self.xp_min.value.strip())))
                vc_cfg["vc_xp_min"] = val
                changed.append(f"📊 أقل XP: **{val}**")
            except ValueError:
                pass
        if self.xp_max.value.strip():
            try:
                val = max(1, min(100, int(self.xp_max.value.strip())))
                vc_cfg["vc_xp_max"] = val
                changed.append(f"📊 أقصى XP: **{val}**")
            except ValueError:
                pass
        if self.boost_mult.value.strip():
            try:
                val = max(1.0, min(3.0, float(self.boost_mult.value.strip())))
                vc_cfg["vc_boost_multiplier"] = val
                changed.append(f"🚀 مضاعف: **{val}x**")
            except ValueError:
                pass

        if vc_cfg["vc_xp_min"] > vc_cfg["vc_xp_max"]:
            vc_cfg["vc_xp_min"], vc_cfg["vc_xp_max"] = vc_cfg["vc_xp_max"], vc_cfg["vc_xp_min"]

        set_guild_vc_config(self.guild_id, vc_cfg)

        embed, view = build_vc_panel(interaction.guild, interaction.user.id)
        await interaction.response.edit_message(embed=embed, view=view)
        if changed:
            confirm = discord.Embed(
                description="✅ **تم التحديث:**\n" + "\n".join(changed),
                color=DASH_COLOR_SUCCESS
            )
            await interaction.followup.send(embed=confirm, ephemeral=True)


# ==========================================
#       4. بانل الحماية (Anti-Cheat)
# ==========================================

def build_anticheat_panel(guild: discord.Guild, author_id: int):
    enabled = is_anti_cheat_enabled(guild.id)
    status_icon = "✅" if enabled else "❌"
    status_text = "مفعل" if enabled else "معطل"
    color = DASH_COLOR_SUCCESS if enabled else DASH_COLOR_DANGER

    embed = discord.Embed(
        color=color,
        timestamp=datetime.now()
    )
    embed.set_author(name="🛡️ إعدادات الحماية", icon_url=guild.icon.url if guild.icon else None)

    embed.description = (
        f"```ansi\n"
        f"\u001b[1;31m   نظام الحماية و الأنتي تشيت   \u001b[0m\n"
        f"```\n"
        f"> **الحالة:** {status_icon} {status_text}\n\n"
        f"**🛡️ المميزات:**\n"
        f"> 🚫 **مكافحة السبام** — حظر مؤقت للمرسلين المتكررين\n"
        f"> 🤬 **فلتر الكلمات** — حذف تلقائي للكلمات السيئة\n"
        f"> ⏱️ **تايم اوت** — 3 دقائق للسبامرز\n"
        f"\n💡 **اضغط الزر لتفعيل أو إيقاف النظام**"
    )
    embed.set_footer(text="لوحة التحكم • الحماية")

    view = AntiCheatSettingsView(guild, author_id, enabled)
    return embed, view


class AntiCheatSettingsView(View):
    def __init__(self, guild: discord.Guild, author_id: int, enabled: bool):
        super().__init__(timeout=300)
        self.guild = guild
        self.author_id = author_id
        self.enabled = enabled

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ مش ليك!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="تفعيل / إيقاف", style=discord.ButtonStyle.success, emoji="🔄", row=0)
    async def toggle_btn(self, interaction: discord.Interaction, button: Button):
        new_state = not self.enabled
        set_anti_cheat_enabled(self.guild.id, new_state)
        self.enabled = new_state
        embed, view = build_anticheat_panel(self.guild, self.author_id)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🔙 رجوع", style=discord.ButtonStyle.secondary, row=1)
    async def back_btn(self, interaction: discord.Interaction, button: Button):
        embed = build_main_dashboard_embed(self.guild)
        view = DashboardMainView(self.guild, self.author_id)
        await interaction.response.edit_message(embed=embed, view=view)


# ==========================================
#       5. بانل الترحيب
# ==========================================

def build_welcome_panel(guild: discord.Guild, author_id: int):
    dash_cfg = get_dashboard_guild_config(guild.id)

    welcome_ch = dash_cfg.get("welcome_channel")
    welcome_msg = dash_cfg.get("welcome_message", "")
    welcome_title = dash_cfg.get("welcome_title", "Greetings, {member}")
    welcome_footer = dash_cfg.get("welcome_footer", "")
    welcome_image = dash_cfg.get("welcome_image")
    goodbye_ch = dash_cfg.get("goodbye_channel")
    goodbye_msg = dash_cfg.get("goodbye_message", "وداعاً {member}! 😢")
    auto_role = dash_cfg.get("auto_role")

    embed = discord.Embed(
        color=DASH_COLOR_ACCENT,
        timestamp=datetime.now()
    )
    embed.set_author(name="👋 إعدادات الترحيب والوداع", icon_url=guild.icon.url if guild.icon else None)

    image_status = f"`✅ محدد`" if welcome_image else "`صورة تلقائية`"

    embed.description = (
        f"```ansi\n"
        f"\u001b[1;35m   نظام الترحيب والوداع   \u001b[0m\n"
        f"```\n"
        f"**📥 الترحيب:**\n"
        f"> القناة: {f'<#{welcome_ch}>' if welcome_ch else '`غير محدد` ⚠️'}\n"
        f"> العنوان: `{welcome_title[:40]}{'...' if len(welcome_title) > 40 else ''}`\n"
        f"> الرسالة: `{welcome_msg[:40]}{'...' if len(welcome_msg) > 40 else ''}`\n"
        f"> الذيل: `{welcome_footer[:40]}{'...' if len(welcome_footer) > 40 else ''}`\n"
        f"> الصورة: {image_status}\n\n"
        f"**📤 الوداع:**\n"
        f"> القناة: {f'<#{goodbye_ch}>' if goodbye_ch else '`غير محدد` ⚠️'}\n"
        f"> الرسالة: `{goodbye_msg[:50]}{'...' if len(goodbye_msg) > 50 else ''}`\n\n"
        f"**🎭 رتبة تلقائية:**\n"
        f"> {f'<@&{auto_role}>' if auto_role else '`غير محدد`'}\n\n"
        f"💡 **المتغيرات:** `{{member}}` = منشن العضو, `{{server}}` = اسم السيرفر, `{{count}}` = عدد الأعضاء"
    )

    if welcome_image:
        embed.set_image(url=welcome_image)

    embed.set_footer(text="لوحة التحكم • الترحيب")

    view = WelcomeSettingsView(guild, author_id)
    return embed, view


class WelcomeSettingsView(View):
    def __init__(self, guild: discord.Guild, author_id: int):
        super().__init__(timeout=300)
        self.guild = guild
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ مش ليك!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="تعديل الترحيب", style=discord.ButtonStyle.primary, emoji="📥", row=0)
    async def edit_welcome_btn(self, interaction: discord.Interaction, button: Button):
        modal = WelcomeMessageModal(self.guild.id, "welcome")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🖼️ صورة الترحيب", style=discord.ButtonStyle.primary, emoji="🖼️", row=0)
    async def welcome_image_btn(self, interaction: discord.Interaction, button: Button):
        modal = WelcomeImageModal(self.guild.id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="تعديل الوداع", style=discord.ButtonStyle.primary, emoji="📤", row=1)
    async def edit_goodbye_btn(self, interaction: discord.Interaction, button: Button):
        modal = WelcomeMessageModal(self.guild.id, "goodbye")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="رتبة تلقائية", style=discord.ButtonStyle.success, emoji="🎭", row=1)
    async def auto_role_btn(self, interaction: discord.Interaction, button: Button):
        modal = AutoRoleModal(self.guild.id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🔙 رجوع", style=discord.ButtonStyle.secondary, row=2)
    async def back_btn(self, interaction: discord.Interaction, button: Button):
        embed = build_main_dashboard_embed(self.guild)
        view = DashboardMainView(self.guild, self.author_id)
        await interaction.response.edit_message(embed=embed, view=view)


class WelcomeMessageModal(Modal):
    def __init__(self, guild_id, msg_type):
        labels = {"welcome": "الترحيب", "goodbye": "الوداع"}
        super().__init__(title=f"✏️ تعديل رسالة {labels[msg_type]}")
        self.guild_id = guild_id
        self.msg_type = msg_type
        dash_cfg = get_dashboard_guild_config(guild_id)

        self.channel_input = TextInput(
            label="آيدي القناة",
            placeholder="مثال: 123456789",
            required=False,
            max_length=25,
            default=str(dash_cfg.get(f"{msg_type}_channel", "")) if dash_cfg.get(f"{msg_type}_channel") else ""
        )

        if msg_type == "welcome":
            self.title_input = TextInput(
                label="عنوان الترحيب",
                placeholder="مثال: Greetings, {member}",
                required=False,
                max_length=100,
                default=dash_cfg.get("welcome_title", "Greetings, {member}")
            )
            self.message_input = TextInput(
                label="نص الرسالة",
                placeholder="استخدم {member} و {server} و {count}",
                required=False,
                max_length=500,
                style=discord.TextStyle.paragraph,
                default=dash_cfg.get("welcome_message", "")
            )
            self.footer_input = TextInput(
                label="الذيل (النص السفلي)",
                placeholder="مثال: we hope you enjoy your time here.",
                required=False,
                max_length=200,
                style=discord.TextStyle.paragraph,
                default=dash_cfg.get("welcome_footer", "")
            )
            self.add_item(self.channel_input)
            self.add_item(self.title_input)
            self.add_item(self.message_input)
            self.add_item(self.footer_input)
        else:
            self.title_input = None
            self.footer_input = None
            self.message_input = TextInput(
                label="الرسالة",
                placeholder="استخدم {member} و {server} و {count}",
                required=False,
                max_length=500,
                style=discord.TextStyle.paragraph,
                default=dash_cfg.get(f"{msg_type}_message", "")
            )
            self.add_item(self.channel_input)
            self.add_item(self.message_input)

    async def on_submit(self, interaction: discord.Interaction):
        changed = []
        if self.channel_input.value.strip():
            ch_val = self.channel_input.value.strip()
            if ch_val.isdigit():
                channel = interaction.guild.get_channel(int(ch_val))
                if channel:
                    set_dashboard_guild_config(self.guild_id, f"{self.msg_type}_channel", channel.id)
                    changed.append(f"📺 القناة: {channel.mention}")
                else:
                    await interaction.response.send_message("❌ القناة مش موجودة!", ephemeral=True)
                    return

        if self.message_input.value.strip():
            set_dashboard_guild_config(self.guild_id, f"{self.msg_type}_message", self.message_input.value.strip())
            changed.append(f"💬 الرسالة: تم التحديث")

        if self.title_input and self.title_input.value.strip():
            set_dashboard_guild_config(self.guild_id, "welcome_title", self.title_input.value.strip())
            changed.append(f"📝 العنوان: تم التحديث")

        if self.footer_input and self.footer_input.value.strip():
            set_dashboard_guild_config(self.guild_id, "welcome_footer", self.footer_input.value.strip())
            changed.append(f"📃 الذيل: تم التحديث")

        embed, view = build_welcome_panel(interaction.guild, interaction.user.id)
        await interaction.response.edit_message(embed=embed, view=view)
        if changed:
            confirm = discord.Embed(description="✅ **تم التحديث:**\n" + "\n".join(changed), color=DASH_COLOR_SUCCESS)
            await interaction.followup.send(embed=confirm, ephemeral=True)


class WelcomeImageModal(Modal, title="🖼️ صورة الترحيب"):
    image_input = TextInput(
        label="رابط الصورة (URL)",
        placeholder="https://example.com/image.png — فارغ للإزالة",
        required=False,
        max_length=500
    )

    def __init__(self, guild_id):
        super().__init__()
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        value = self.image_input.value.strip()

        if not value:
            set_dashboard_guild_config(self.guild_id, "welcome_image", None)
            embed, view = build_welcome_panel(interaction.guild, interaction.user.id)
            await interaction.response.edit_message(embed=embed, view=view)
            await interaction.followup.send(
                embed=discord.Embed(description="✅ تم إزالة الصورة — هيتعرض الصورة التلقائية", color=DASH_COLOR_SUCCESS),
                ephemeral=True
            )
            return

        if not (value.startswith("http://") or value.startswith("https://")):
            await interaction.response.send_message("❌ الرابط لازم يبدأ بـ http:// أو https://", ephemeral=True)
            return

        set_dashboard_guild_config(self.guild_id, "welcome_image", value)
        embed, view = build_welcome_panel(interaction.guild, interaction.user.id)
        await interaction.response.edit_message(embed=embed, view=view)
        await interaction.followup.send(
            embed=discord.Embed(description=f"✅ تم تحديث صورة الترحيب!", color=DASH_COLOR_SUCCESS),
            ephemeral=True
        )


class AutoRoleModal(Modal, title="🎭 رتبة تلقائية عند الدخول"):
    role_input = TextInput(
        label="آيدي الرتبة أو اسمها (فارغ لإلغاء)",
        placeholder="مثال: 123456789 أو Member",
        required=False,
        max_length=100
    )

    def __init__(self, guild_id):
        super().__init__()
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        value = self.role_input.value.strip()

        if not value:
            set_dashboard_guild_config(self.guild_id, "auto_role", None)
            embed, view = build_welcome_panel(interaction.guild, interaction.user.id)
            await interaction.response.edit_message(embed=embed, view=view)
            await interaction.followup.send(embed=discord.Embed(description="✅ تم إلغاء الرتبة التلقائية", color=DASH_COLOR_SUCCESS), ephemeral=True)
            return

        role = None
        if value.isdigit():
            role = interaction.guild.get_role(int(value))
        if not role:
            role = discord.utils.get(interaction.guild.roles, name=value)

        if not role:
            await interaction.response.send_message("❌ مش لاقي الرتبة دي!", ephemeral=True)
            return

        set_dashboard_guild_config(self.guild_id, "auto_role", role.id)
        embed, view = build_welcome_panel(interaction.guild, interaction.user.id)
        await interaction.response.edit_message(embed=embed, view=view)
        await interaction.followup.send(embed=discord.Embed(description=f"✅ الرتبة التلقائية: {role.mention}", color=DASH_COLOR_SUCCESS), ephemeral=True)


# ==========================================
#       6. بانل الصلاحيات
# ==========================================

PERMISSION_LABELS = {
    "warn": "⚠️ تحذير",
    "timeout": "⏱️ تايم اوت",
    "untimeout": "✅ إلغاء تايم اوت",
    "warnings": "📋 عرض التحذيرات",
    "mute": "🔇 ميوت",
    "unmute": "🔊 إلغاء ميوت",
    "kick": "👢 طرد",
    "ban": "🔨 حظر",
    "unban": "🔓 إلغاء حظر",
    "clear": "🧹 مسح رسائل",
    "role": "🎭 إدارة رتب",
    "prison": "🔒 سجن",
    "unprison": "🔓 إلغاء سجن",
    "ticket": "🎫 التيكت",
    "talk": "🗣️ التكلم بالبوت",
    "lead_reset": "🔄 تصفير الليدربورد",
    "lock": "🔒 قفل الشات",
    "unlock": "🔓 فتح الشات",
    "comp_win": "🏆 فوز مسابقة",
    "comp_leaderboard": "📊 ليدربورد المسابقات",
}


def build_permissions_panel(guild: discord.Guild, author_id: int):
    embed = discord.Embed(
        color=DASH_COLOR_INFO,
        timestamp=datetime.now()
    )
    embed.set_author(name="🎭 إعدادات الصلاحيات", icon_url=guild.icon.url if guild.icon else None)

    cfg = load_roles_config()
    guild_roles = cfg.get(str(guild.id), {})

    if guild_roles:
        lines = []
        for role_id, perms in guild_roles.items():
            role = guild.get_role(int(role_id))
            if not role:
                continue
            active_perms = [PERMISSION_LABELS.get(p, p) for p, v in perms.items() if v]
            if active_perms:
                lines.append(f"> **{role.name}:** {', '.join(active_perms[:5])}{'...' if len(active_perms) > 5 else ''}")
        roles_text = "\n".join(lines) if lines else "> لا توجد صلاحيات مخصصة"
    else:
        roles_text = "> لا توجد صلاحيات مخصصة"

    embed.description = (
        f"```ansi\n"
        f"\u001b[1;32m   إدارة صلاحيات الرتب   \u001b[0m\n"
        f"```\n"
        f"**الرتب المُعَدّة:**\n{roles_text}\n\n"
        f"💡 **اختر رتبة من القائمة لتعديل صلاحياتها**"
    )
    embed.set_footer(text="لوحة التحكم • الصلاحيات")

    view = PermissionsSettingsView(guild, author_id)
    return embed, view


class PermRoleSelect(Select):
    def __init__(self, guild: discord.Guild):
        roles = [r for r in guild.roles if not r.is_default() and not r.is_bot_managed() and not r.managed]
        roles.sort(key=lambda r: r.position, reverse=True)
        roles = roles[:25]  # Discord limit

        options = []
        for role in roles:
            options.append(
                discord.SelectOption(
                    label=role.name[:100],
                    value=str(role.id),
                    description=f"ID: {role.id}"
                )
            )

        if not options:
            options = [discord.SelectOption(label="لا توجد رتب", value="none")]

        super().__init__(placeholder="اختر رتبة...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("❌ لا توجد رتب!", ephemeral=True)
            return

        role_id = int(self.values[0])
        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.response.send_message("❌ الرتبة مش موجودة!", ephemeral=True)
            return

        embed, view = build_role_perms_detail(interaction.guild, interaction.user.id, role)
        await interaction.response.edit_message(embed=embed, view=view)


def build_role_perms_detail(guild: discord.Guild, author_id: int, role: discord.Role):
    current_perms = get_role_permissions(guild.id, role.id)

    lines = []
    for perm_key, perm_label in PERMISSION_LABELS.items():
        is_on = current_perms.get(perm_key, False)
        icon = "✅" if is_on else "❌"
        lines.append(f"> {icon} {perm_label}")

    embed = discord.Embed(
        color=role.color if role.color != discord.Color.default() else DASH_COLOR_INFO,
        timestamp=datetime.now()
    )
    embed.set_author(name=f"🎭 صلاحيات — {role.name}", icon_url=guild.icon.url if guild.icon else None)
    embed.description = (
        f"```\n"
        f"   تعديل صلاحيات {role.name}\n"
        f"```\n"
        + "\n".join(lines) +
        f"\n\n💡 **اختر الصلاحيات من القائمة لتفعيلها/إيقافها**"
    )
    embed.set_footer(text="لوحة التحكم • صلاحيات الرتبة")

    view = RolePermDetailView(guild, author_id, role)
    return embed, view


class PermToggleSelect(Select):
    def __init__(self, guild_id: int, role: discord.Role):
        self.role = role
        self.guild_id = guild_id
        current_perms = get_role_permissions(guild_id, role.id)

        options = []
        for perm_key, perm_label in PERMISSION_LABELS.items():
            is_on = current_perms.get(perm_key, False)
            options.append(
                discord.SelectOption(
                    label=perm_label.split(" ", 1)[1] if " " in perm_label else perm_label,
                    value=perm_key,
                    emoji="✅" if is_on else "❌",
                    description="مفعل — اضغط لإيقاف" if is_on else "معطل — اضغط لتفعيل"
                )
            )

        super().__init__(placeholder="اختر صلاحية لتبديلها...", options=options[:25], min_values=1, max_values=len(options[:25]))

    async def callback(self, interaction: discord.Interaction):
        current_perms = get_role_permissions(self.guild_id, self.role.id)

        for perm_key in self.values:
            current_perms[perm_key] = not current_perms.get(perm_key, False)

        set_role_permissions(self.guild_id, self.role.id, current_perms)

        embed, view = build_role_perms_detail(interaction.guild, interaction.user.id, self.role)
        await interaction.response.edit_message(embed=embed, view=view)


class RolePermDetailView(View):
    def __init__(self, guild: discord.Guild, author_id: int, role: discord.Role):
        super().__init__(timeout=300)
        self.guild = guild
        self.author_id = author_id
        self.role = role
        self.add_item(PermToggleSelect(guild.id, role))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ مش ليك!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🔙 رجوع للصلاحيات", style=discord.ButtonStyle.secondary, row=2)
    async def back_btn(self, interaction: discord.Interaction, button: Button):
        embed, view = build_permissions_panel(self.guild, self.author_id)
        await interaction.response.edit_message(embed=embed, view=view)


class PermissionsSettingsView(View):
    def __init__(self, guild: discord.Guild, author_id: int):
        super().__init__(timeout=300)
        self.guild = guild
        self.author_id = author_id
        self.add_item(PermRoleSelect(guild))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ مش ليك!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🔙 رجوع", style=discord.ButtonStyle.secondary, row=2)
    async def back_btn(self, interaction: discord.Interaction, button: Button):
        embed = build_main_dashboard_embed(self.guild)
        view = DashboardMainView(self.guild, self.author_id)
        await interaction.response.edit_message(embed=embed, view=view)


# ==========================================
#       7. بانل التيكت
# ==========================================

def build_ticket_panel(guild: discord.Guild, author_id: int):
    ticket_img = get_ticket_image_url(guild.id)
    panel_ch, panel_msg = get_ticket_panel_info(guild.id)

    embed = discord.Embed(
        color=DASH_COLOR_INFO,
        timestamp=datetime.now()
    )
    embed.set_author(name="🎫 إعدادات التيكت", icon_url=guild.icon.url if guild.icon else None)

    # Ticket roles
    ticket_roles = get_ticket_roles(guild)
    roles_text = ", ".join([r.mention for r in ticket_roles]) if ticket_roles else "`لا توجد`"

    embed.description = (
        f"```ansi\n"
        f"\u001b[1;34m   إعدادات نظام التيكت   \u001b[0m\n"
        f"```\n"
        f"**🖼️ صورة البانل:**\n"
        f"> {f'[الرابط]({ticket_img})' if ticket_img else '`غير محدد — هيستخدم الصورة الافتراضية`'}\n\n"
        f"**📍 بانل التيكت:**\n"
        f"> {f'القناة: <#{panel_ch}>' if panel_ch else '`غير موجود — استخدم /ticket_setup`'}\n\n"
        f"**🎭 رتب التيكت:**\n"
        f"> {roles_text}\n\n"
        f"💡 **غيّر صورة البانل أو أعد إعداد التيكت من هنا**"
    )
    embed.set_footer(text="لوحة التحكم • التيكت")

    if ticket_img:
        embed.set_thumbnail(url=ticket_img)

    view = TicketSettingsView(guild, author_id)
    return embed, view


class TicketSettingsView(View):
    def __init__(self, guild: discord.Guild, author_id: int):
        super().__init__(timeout=300)
        self.guild = guild
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ مش ليك!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="تغيير صورة البانل", style=discord.ButtonStyle.primary, emoji="🖼️", row=0)
    async def change_image_btn(self, interaction: discord.Interaction, button: Button):
        modal = TicketImageModal(self.guild.id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🔙 رجوع", style=discord.ButtonStyle.secondary, row=1)
    async def back_btn(self, interaction: discord.Interaction, button: Button):
        embed = build_main_dashboard_embed(self.guild)
        view = DashboardMainView(self.guild, self.author_id)
        await interaction.response.edit_message(embed=embed, view=view)


class TicketImageModal(Modal, title="🖼️ تغيير صورة بانل التيكت"):
    image_url_input = TextInput(
        label="رابط الصورة",
        placeholder="https://example.com/image.png",
        required=True,
        max_length=500
    )

    def __init__(self, guild_id):
        super().__init__()
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        url = self.image_url_input.value.strip()
        if not url.startswith(("http://", "https://")):
            await interaction.response.send_message("❌ الرابط لازم يبدأ بـ http:// أو https://", ephemeral=True)
            return

        set_ticket_image_url(self.guild_id, url)

        # Try to auto-update panel
        panel_ch_id, panel_msg_id = get_ticket_panel_info(self.guild_id)
        panel_updated = False
        if panel_ch_id and panel_msg_id:
            try:
                channel = interaction.guild.get_channel(int(panel_ch_id))
                if channel:
                    msg = await channel.fetch_message(int(panel_msg_id))
                    if msg and msg.author.id == interaction.client.user.id:
                        new_embed = discord.Embed(
                            title="🎫 Support Tickets",
                            description="Select an option below to open a ticket.",
                            color=discord.Color.blue()
                        )
                        new_embed.set_image(url=url)
                        view = TicketView()
                        await msg.edit(embed=new_embed, view=view, attachments=[])
                        panel_updated = True
            except Exception as e:
                print(f"Error updating ticket panel from dashboard: {e}")

        embed, view = build_ticket_panel(interaction.guild, interaction.user.id)
        await interaction.response.edit_message(embed=embed, view=view)

        status = "وتم تعديل البانل تلقائياً!" if panel_updated else "(استخدم `/ticket_setup` لإنشاء بانل جديد)"
        await interaction.followup.send(
            embed=discord.Embed(description=f"✅ تم حفظ الصورة الجديدة {status}", color=DASH_COLOR_SUCCESS),
            ephemeral=True
        )


# ==========================================
#       8. بانل الاختصارات (Aliases)
# ==========================================

# قائمة الأوامر الأصلية القابلة للتغيير
AVAILABLE_COMMANDS = {
    "وارن": "⚠️ تحذير",
    "انوارن": "✅ إزالة تحذير",
    "تحذيرات": "📋 عرض التحذيرات",
    "بان": "🔨 حظر",
    "انباند": "🔓 فك حظر",
    "كيك": "👢 طرد",
    "تايم": "⏱️ تايم اوت",
    "انتايم": "✅ فك تايم اوت",
    "ميوت": "🔇 ميوت",
    "انميوت": "🔊 فك ميوت",
    "رول": "🎭 إدارة رتب",
    "مسح": "🧹 مسح رسائل",
    "رانك": "📊 رانك",
    "قفل": "🔒 قفل شات",
    "فتح": "🔓 فتح شات",
}


def build_aliases_panel(guild: discord.Guild, author_id: int):
    dash_cfg = get_dashboard_guild_config(guild.id)
    aliases = dash_cfg.get("aliases", {})

    embed = discord.Embed(
        color=DASH_COLOR_INFO,
        timestamp=datetime.now()
    )
    embed.set_author(name="🔤 إعدادات الاختصارات", icon_url=guild.icon.url if guild.icon else None)

    lines = []
    for cmd, label in AVAILABLE_COMMANDS.items():
        custom = aliases.get(cmd)
        if custom:
            lines.append(f"> {label}: `.{cmd}` ➜ `.{custom}`")
        else:
            lines.append(f"> {label}: `.{cmd}`")

    embed.description = (
        f"```ansi\n"
        f"\u001b[1;36m   اختصارات الأوامر   \u001b[0m\n"
        f"```\n"
        f"**الأوامر الحالية:**\n"
        + "\n".join(lines) + "\n\n"
        f"💡 **اختر أمر من القائمة لتغيير اختصاره**\n"
        f"📌 الاختصار الأصلي يفضل يشتغل + الاختصار الجديد"
    )
    embed.set_footer(text="لوحة التحكم • الاختصارات")

    view = AliasesSettingsView(guild, author_id)
    return embed, view


class AliasCommandSelect(Select):
    def __init__(self, guild: discord.Guild):
        self.target_guild = guild
        options = []
        dash_cfg = get_dashboard_guild_config(guild.id)
        aliases = dash_cfg.get("aliases", {})

        for cmd, label in AVAILABLE_COMMANDS.items():
            custom = aliases.get(cmd)
            desc = f"الاختصار الحالي: .{custom}" if custom else f"الأصلي: .{cmd}"
            options.append(
                discord.SelectOption(
                    label=f".{cmd} — {label}",
                    value=cmd,
                    description=desc[:100],
                    emoji="✏️" if custom else "📝"
                )
            )

        super().__init__(
            placeholder="اختر أمر لتغيير اختصاره...",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        selected_cmd = self.values[0]
        modal = AliasEditModal(self.target_guild.id, selected_cmd)
        await interaction.response.send_modal(modal)


class AliasEditModal(Modal):
    def __init__(self, guild_id, command_name):
        cmd_label = AVAILABLE_COMMANDS.get(command_name, command_name)
        super().__init__(title=f"✏️ تغيير اختصار {cmd_label}")
        self.guild_id = guild_id
        self.command_name = command_name

        dash_cfg = get_dashboard_guild_config(guild_id)
        current_alias = dash_cfg.get("aliases", {}).get(command_name, "")

        self.alias_input = TextInput(
            label=f"الاختصار الجديد لـ .{command_name}",
            placeholder=f"مثال: warn أو تحذير (فارغ لإزالة الاختصار)",
            required=False,
            max_length=30,
            default=current_alias
        )
        self.add_item(self.alias_input)

    async def on_submit(self, interaction: discord.Interaction):
        value = self.alias_input.value.strip()

        dash_cfg = get_dashboard_guild_config(self.guild_id)
        aliases = dash_cfg.get("aliases", {})

        if not value:
            # إزالة الاختصار
            if self.command_name in aliases:
                del aliases[self.command_name]
                set_dashboard_guild_config(self.guild_id, "aliases", aliases)

            embed, view = build_aliases_panel(interaction.guild, interaction.user.id)
            await interaction.response.edit_message(embed=embed, view=view)
            await interaction.followup.send(
                embed=discord.Embed(
                    description=f"✅ تم إزالة الاختصار المخصص لـ `.{self.command_name}`",
                    color=DASH_COLOR_SUCCESS
                ),
                ephemeral=True
            )
            return

        # التحقق من عدم تعارض الاختصار
        for cmd, existing_alias in aliases.items():
            if existing_alias == value and cmd != self.command_name:
                await interaction.response.send_message(
                    f"❌ الاختصار `.{value}` مستخدم بالفعل لأمر `.{cmd}`!",
                    ephemeral=True
                )
                return

        # التحقق من عدم تعارض مع أوامر أصلية
        if value in AVAILABLE_COMMANDS and value != self.command_name:
            await interaction.response.send_message(
                f"❌ `.{value}` هو اسم أمر أصلي! اختر اسم تاني.",
                ephemeral=True
            )
            return

        aliases[self.command_name] = value
        set_dashboard_guild_config(self.guild_id, "aliases", aliases)

        embed, view = build_aliases_panel(interaction.guild, interaction.user.id)
        await interaction.response.edit_message(embed=embed, view=view)
        await interaction.followup.send(
            embed=discord.Embed(
                description=f"✅ تم تغيير اختصار `.{self.command_name}` إلى `.{value}`",
                color=DASH_COLOR_SUCCESS
            ),
            ephemeral=True
        )


class AliasesSettingsView(View):
    def __init__(self, guild: discord.Guild, author_id: int):
        super().__init__(timeout=300)
        self.guild = guild
        self.author_id = author_id
        self.add_item(AliasCommandSelect(guild))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ مش ليك!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🗑️ مسح كل الاختصارات", style=discord.ButtonStyle.danger, emoji="🗑️", row=2)
    async def clear_all_btn(self, interaction: discord.Interaction, button: Button):
        set_dashboard_guild_config(self.guild.id, "aliases", {})
        embed, view = build_aliases_panel(self.guild, self.author_id)
        await interaction.response.edit_message(embed=embed, view=view)
        await interaction.followup.send(
            embed=discord.Embed(description="✅ تم مسح كل الاختصارات المخصصة", color=DASH_COLOR_SUCCESS),
            ephemeral=True
        )

    @discord.ui.button(label="🔙 رجوع", style=discord.ButtonStyle.secondary, row=2)
    async def back_btn(self, interaction: discord.Interaction, button: Button):
        embed = build_main_dashboard_embed(self.guild)
        view = DashboardMainView(self.guild, self.author_id)
        await interaction.response.edit_message(embed=embed, view=view)


# ==========================================
#       9. بانل النظرة العامة
# ==========================================

def build_overview_panel(guild: discord.Guild, author_id: int):
    embed = discord.Embed(
        color=DASH_COLOR_MAIN,
        timestamp=datetime.now()
    )
    embed.set_author(name=f"📊 نظرة عامة — {guild.name}", icon_url=guild.icon.url if guild.icon else None)

    # Server stats
    total_members = guild.member_count or len(guild.members)
    bots = sum(1 for m in guild.members if m.bot)
    humans = total_members - bots
    online = sum(1 for m in guild.members if m.status != discord.Status.offline)
    boosters = guild.premium_subscription_count or 0
    boost_level = guild.premium_tier

    # System status
    level_status = "✅" if is_level_enabled(guild.id) else "❌"
    anticheat_status = "✅" if is_anti_cheat_enabled(guild.id) else "❌"

    # Log channels count
    guild_cfg = load_guild_config().get(str(guild.id), {})
    logs = guild_cfg.get("logs", {})
    log_count = sum(1 for v in logs.values() if v)
    bank_log = "✅" if get_bank_logs_channel(guild.id) else "❌"
    role_log = "✅" if get_role_logs_channel(guild.id) else "❌"

    # VC config
    vc_cfg = get_guild_vc_config(guild.id)

    # Roles config
    roles_cfg = load_roles_config().get(str(guild.id), {})
    configured_roles = len(roles_cfg)

    # Dashboard config
    dash_cfg = get_dashboard_guild_config(guild.id)

    embed.description = (
        f"```ansi\n"
        f"\u001b[1;37m   ملخص شامل لإعدادات السيرفر   \u001b[0m\n"
        f"```\n"
    )

    embed.add_field(
        name="👥 الأعضاء",
        value=(
            f"> 🧑 البشر: **{humans:,}**\n"
            f"> 🤖 البوتات: **{bots}**\n"
            f"> 🟢 أونلاين: **{online:,}**\n"
            f"> 🚀 بوسترز: **{boosters}** (Tier {boost_level})"
        ),
        inline=True
    )

    embed.add_field(
        name="⚡ الأنظمة",
        value=(
            f"> 📈 اللفل: {level_status}\n"
            f"> 🛡️ الحماية: {anticheat_status}\n"
            f"> 📋 اللوجات: **{log_count}** قناة\n"
            f"> 🏦 لوج البنك: {bank_log}\n"
            f"> 🎭 لوج الرتب: {role_log}"
        ),
        inline=True
    )

    embed.add_field(
        name="🎙️ VC XP",
        value=(
            f"> ⏱️ XP/دقيقة: **{vc_cfg.get('vc_xp_per_minute', 10)}**\n"
            f"> 📊 المدى: **{vc_cfg.get('vc_xp_min', 5)}-{vc_cfg.get('vc_xp_max', 15)}**\n"
            f"> 🚀 مضاعف: **{vc_cfg.get('vc_boost_multiplier', 1.5)}x**\n"
            f"> 🎯 نشط فقط: {'✅' if vc_cfg.get('vc_active_only') else '❌'}"
        ),
        inline=True
    )

    embed.add_field(
        name="📊 إعدادات XP",
        value=(
            f"> ⏱️ Cooldown: **{bot_config.get('xp_cooldown', 30)}s**\n"
            f"> 📊 المدى: **{bot_config.get('xp_min', 10)}-{bot_config.get('xp_max', 15)}**\n"
            f"> 💰 كريدت/لفل: **{bot_config.get('level_up_credits', 50)}**"
        ),
        inline=True
    )

    embed.add_field(
        name="🎭 الصلاحيات",
        value=(
            f"> الرتب المُعَدّة: **{configured_roles}**\n"
            f"> 📋 القنوات: **{len(guild.text_channels)}**\n"
            f"> 🔊 الصوتية: **{len(guild.voice_channels)}**"
        ),
        inline=True
    )

    embed.add_field(
        name="👋 الترحيب",
        value=(
            f"> 📥 قناة الترحيب: {'✅' if dash_cfg.get('welcome_channel') else '❌'}\n"
            f"> 📤 قناة الوداع: {'✅' if dash_cfg.get('goodbye_channel') else '❌'}\n"
            f"> 🎭 رتبة تلقائية: {'✅' if dash_cfg.get('auto_role') else '❌'}"
        ),
        inline=True
    )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    if guild.banner:
        embed.set_image(url=guild.banner.url)

    embed.set_footer(text="لوحة التحكم • نظرة عامة")

    view = OverviewBackView(guild, author_id)
    return embed, view


class OverviewBackView(View):
    def __init__(self, guild: discord.Guild, author_id: int):
        super().__init__(timeout=300)
        self.guild = guild
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ مش ليك!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🔄 تحديث", style=discord.ButtonStyle.primary, emoji="🔄", row=0)
    async def refresh_btn(self, interaction: discord.Interaction, button: Button):
        embed, view = build_overview_panel(self.guild, self.author_id)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🔙 رجوع", style=discord.ButtonStyle.secondary, row=0)
    async def back_btn(self, interaction: discord.Interaction, button: Button):
        embed = build_main_dashboard_embed(self.guild)
        view = DashboardMainView(self.guild, self.author_id)
        await interaction.response.edit_message(embed=embed, view=view)


# ==========================================
#       أمر /dashboard
# ==========================================

@bot.tree.command(name="dashboard", description="🎛️ لوحة التحكم — إدارة إعدادات البوت والسيرفر")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def slash_dashboard(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    embed = build_main_dashboard_embed(interaction.guild)
    view = DashboardMainView(interaction.guild, interaction.user.id)

    await interaction.followup.send(embed=embed, view=view, ephemeral=True)


# ========== تشغيل البوت ==========
if __name__ == "__main__":
    try:
        print("🚀 جاري تشغيل البوت...")
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("❌ فشل تسجيل الدخول! تأكد من التوكن في ملف .env")
    except Exception as e:
        print(f"❌ حدث خطأ غير متوقع: {e}")
