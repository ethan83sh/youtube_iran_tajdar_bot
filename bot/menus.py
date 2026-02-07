from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# ---- Main menu callbacks ----
CB_ADD_LINK = "ADD_LINK"
CB_ADD_VIDEO = "ADD_VIDEO"
CB_QUEUE = "QUEUE"
CB_QUEUE_REFRESH = "QUEUE_REFRESH"
CB_TIME = "TIME"

CB_CANCEL = "CANCEL"
CB_BACK_MAIN = "BACK_MAIN"

# ---- Link flow callbacks ----
CB_LINK_THUMB_YT = "LINK_THUMB_YT"
CB_LINK_THUMB_MANUAL = "LINK_THUMB_MANUAL"

CB_LINK_TITLE_YT = "LINK_TITLE_YT"
CB_LINK_TITLE_MANUAL = "LINK_TITLE_MANUAL"

CB_LINK_DESC_YT = "LINK_DESC_YT"
CB_LINK_DESC_MANUAL = "LINK_DESC_MANUAL"

# ---- Time menu callbacks ----
CB_TIME_VIEW = "TIME_VIEW"
CB_TIME_SET = "TIME_SET"

# ---- Queue item callbacks (prefixes) ----
CB_QUEUE_ITEM = "QUEUE_ITEM:"  # +id  (کلیک روی آیتم در لیست -> منوی آیتم)
CB_QUEUE_ITEM_VIEW = "QUEUE_ITEM_VIEW:"  # +id
CB_QUEUE_ITEM_DEL = "QUEUE_ITEM_DEL:"  # +id

CB_QUEUE_ITEM_EDIT_TITLE = "QUEUE_ITEM_EDIT_TITLE:"  # +id
CB_QUEUE_ITEM_EDIT_DESC = "QUEUE_ITEM_EDIT_DESC:"  # +id
CB_QUEUE_ITEM_EDIT_THUMB = "QUEUE_ITEM_EDIT_THUMB:"  # +id

CB_QUEUE_REORDER = "QUEUE_REORDER:"  # +id
CB_QUEUE_POS = "QUEUE_POS:"  # +pos


# -----------------------------
# Common keyboards
# -----------------------------
def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("کنسل ↩︎", callback_data=CB_CANCEL)]])


def back_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت به منو ↩︎", callback_data=CB_BACK_MAIN)]])


# -----------------------------
# Main menu
# -----------------------------
def main_menu() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("اضافه کردن با لینک", callback_data=CB_ADD_LINK)],
        [InlineKeyboardButton("اضافه کردن ویدیو", callback_data=CB_ADD_VIDEO)],
        [InlineKeyboardButton("صف انتشار", callback_data=CB_QUEUE)],
        [InlineKeyboardButton("زمان انتشار", callback_data=CB_TIME)],
    ]
    return InlineKeyboardMarkup(rows)


def main_kb() -> InlineKeyboardMarkup:
    return main_menu()


# -----------------------------
# Link: thumb/title/desc choice
# -----------------------------
def link_thumb_choice_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("تامبنیل اصلی یوتوب", callback_data=CB_LINK_THUMB_YT)],
        [InlineKeyboardButton("تامبنیل دستی آپلود می‌کنم", callback_data=CB_LINK_THUMB_MANUAL)],
        [InlineKeyboardButton("کنسل ↩︎", callback_data=CB_CANCEL)],
    ]
    return InlineKeyboardMarkup(rows)


def link_title_choice_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("تیتر از یوتوب", callback_data=CB_LINK_TITLE_YT)],
        [InlineKeyboardButton("تیتر دستی", callback_data=CB_LINK_TITLE_MANUAL)],
        [InlineKeyboardButton("کنسل ↩︎", callback_data=CB_CANCEL)],
    ]
    return InlineKeyboardMarkup(rows)


def link_desc_choice_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("دیسک از یوتوب", callback_data=CB_LINK_DESC_YT)],
        [InlineKeyboardButton("دیسک دستی", callback_data=CB_LINK_DESC_MANUAL)],
        [InlineKeyboardButton("کنسل ↩︎", callback_data=CB_CANCEL)],
    ]
    return InlineKeyboardMarkup(rows)


# -----------------------------
# Time menu
# -----------------------------
def time_menu() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("مشاهده زمان کنونی", callback_data=CB_TIME_VIEW)],
        [InlineKeyboardButton("تغییر زمان کنونی", callback_data=CB_TIME_SET)],
        [InlineKeyboardButton("بازگشت به منو ↩︎", callback_data=CB_BACK_MAIN)],
    ]
    return InlineKeyboardMarkup(rows)


# -----------------------------
# Queue list + item menu
# -----------------------------
def queue_list_kb(items):
    rows = []
    for it in items:
        # sqlite3.Row از طریق [] و keys() قابل خوندنه، get نداره
        title = ""
        if it is not None:
            if hasattr(it, "keys"):
                # sqlite3.Row
                title = ((it["title"] if "title" in it.keys() else "") or "").strip()
                if not title:
                    title = ((it["source_url"] if "source_url" in it.keys() else "") or "").strip()
            else:
                # dict-like
                title = (it.get("title") or it.get("source_url") or "").strip()

        if len(title) > 40:
            title = title[:37] + "..."

        rows.append([InlineKeyboardButton(f"#{it['id']} — {title}", callback_data=f"{CB_QUEUE_ITEM}{it['id']}")])

    rows.append([InlineKeyboardButton("🔄 بروزرسانی", callback_data=CB_QUEUE_REFRESH)])
    rows.append([InlineKeyboardButton("بازگشت به منو ↩︎", callback_data=CB_BACK_MAIN)])
    return InlineKeyboardMarkup(rows)



def queue_item_kb(item_id: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("👁 مشاهده کامل", callback_data=f"{CB_QUEUE_ITEM_VIEW}{item_id}")],
        [InlineKeyboardButton("✏️ ادیت تیتر", callback_data=f"{CB_QUEUE_ITEM_EDIT_TITLE}{item_id}")],
        [InlineKeyboardButton("📝 ادیت دیسکریپشن", callback_data=f"{CB_QUEUE_ITEM_EDIT_DESC}{item_id}")],
        [InlineKeyboardButton("🖼 تغییر پوستر", callback_data=f"{CB_QUEUE_ITEM_EDIT_THUMB}{item_id}")],
        [InlineKeyboardButton("🔀 تغییر ترتیب در صف", callback_data=f"{CB_QUEUE_REORDER}{item_id}")],
        [InlineKeyboardButton("🗑 حذف از صف", callback_data=f"{CB_QUEUE_ITEM_DEL}{item_id}")],
        # برگشت‌ها
        [InlineKeyboardButton("بازگشت ↩︎", callback_data=CB_QUEUE_REFRESH)],
        [InlineKeyboardButton("بازگشت به منو ↩︎", callback_data=CB_BACK_MAIN)],
    ]
    return InlineKeyboardMarkup(rows)


def queue_pick_position_kb(n: int) -> InlineKeyboardMarkup:
    """
    n: تعداد آیتم‌های صف
    """
    rows = []
    row = []
    for i in range(1, n + 1):
        row.append(InlineKeyboardButton(str(i), callback_data=f"{CB_QUEUE_POS}{i}"))
        if len(row) == 5:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append([InlineKeyboardButton("کنسل ↩︎", callback_data=CB_CANCEL)])
    return InlineKeyboardMarkup(rows)
