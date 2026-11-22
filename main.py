import os
import sqlite3
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ChatMemberHandler,
    ContextTypes
)

TOKEN = os.getenv("BOT_TOKEN")
RULES_URL = "https://t.me/GOKULDHAM_SOCIETY_RULES"
DB = "bot_data.db"


def db():
    return sqlite3.connect(DB)


def setup_db():
    with db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS links (
                link TEXT PRIMARY KEY,
                owner INTEGER,
                name TEXT
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS joins (
                user INTEGER,
                inviter INTEGER,
                name TEXT,
                PRIMARY KEY(user)
            )
        """)


def get_group():
    with db() as con:
        row = con.execute(
            "SELECT value FROM settings WHERE key='group'"
        ).fetchone()
    return int(row[0]) if row else None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to GOKULDHAM SOCIETY Help Bot! ❤️\n\n"
        "Use /help to see all commands."
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "G S HELP BOT\n\n"
        "/invite - Get your personal invite link\n"
        "/mylinks - Your invitation link\n"
        "/stats - Your invitation statistics\n"
        "/top - Top inviters\n"
        "/rules - Group rules\n"
        "/help - Help menu\n\n"
        "Admin: /setup"
    )


async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"GOKULDHAM SOCIETY RULES:\n{RULES_URL}"
    )


async def setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        await update.message.reply_text(
            "Run /setup inside your group as an admin."
        )
        return

    member = await context.bot.get_chat_member(chat.id, user.id)

    if member.status not in ("administrator", "creator"):
        await update.message.reply_text("Only group admins can use this.")
        return

    with db() as con:
        con.execute(
            "INSERT OR REPLACE INTO settings VALUES ('group', ?)",
            (str(chat.id),)
        )

    await update.message.reply_text(
        "GOKULDHAM SOCIETY connected successfully! ❤️"
    )


async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    group = get_group()

    if not group:
        await update.message.reply_text(
            "Admin must first run /setup in the group."
        )
        return

    with db() as con:
        row = con.execute(
            "SELECT link FROM links WHERE owner=?",
            (user.id,)
        ).fetchone()

    if row:
        link = row[0]
    else:
        try:
            invite_link = await context.bot.create_chat_invite_link(
                chat_id=group,
                name=f"User {user.id}"
            )
            link = invite_link.invite_link

            with db() as con:
                con.execute(
                    "INSERT INTO links VALUES (?, ?, ?)",
                    (link, user.id, user.full_name)
                )

        except Exception as e:
            await update.message.reply_text(
                "Invite link nahi ban paya. Admin se permission check karwao."
            )
            print(e)
            return

    await update.message.reply_text(
        f"Your personal invitation link:\n\n{link}\n\n"
        "Share this link with your friends!"
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    with db() as con:
        count = con.execute(
            "SELECT COUNT(*) FROM joins WHERE inviter=?",
            (user.id,)
        ).fetchone()[0]

    await update.message.reply_text(
        f"Your invitation statistics:\n\n"
        f"Total members invited: {count}"
    )


async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with db() as con:
        rows = con.execute("""
            SELECT name, COUNT(*) AS total
            FROM joins
            GROUP BY inviter
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()

    if not rows:
        await update.message.reply_text("No invitations recorded yet.")
        return

    result = "🏆 TOP INVITERS\n\n"
    for i, (name, count) in enumerate(rows, 1):
        result += f"{i}. {name} — {count}\n"

    await update.message.reply_text(result)


async def track_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    event = update.chat_member
    old = event.old_chat_member
    new = event.new_chat_member

    if old.is_member or not new.is_member:
        return

    used_link = event.invite_link

    if not used_link:
        return

    link = used_link.invite_link
    user = new.user

    with db() as con:
        row = con.execute(
            "SELECT owner, name FROM links WHERE link=?",
            (link,)
        ).fetchone()

        if not row:
            return

        inviter_id, inviter_name = row

        if inviter_id == user.id:
            return

        con.execute(
            "INSERT OR IGNORE INTO joins VALUES (?, ?, ?)",
            (user.id, inviter_id, inviter_name)
        )


def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is missing.")

    setup_db()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("setup", setup))
    app.add_handler(CommandHandler("invite", invite))
    app.add_handler(CommandHandler("mylinks", invite))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("top", top))

    app.add_handler(
        ChatMemberHandler(track_join, ChatMemberHandler.CHAT_MEMBER)
    )

    print("G S Help Bot is running!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
