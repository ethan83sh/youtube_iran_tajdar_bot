from telegram import InlineKeyboardButton, InlineKeyboardMarkup

CB_ADD_LINK = "ADD_LINK"
CB_ADD_VIDEO = "ADD_VIDEO"
CB_QUEUE = "QUEUE"
CB_TIME = "TIME"
CB_CANCEL = "CANCEL"
CB_BACK = "BACK_MAIN"
CB_LINK_THUMB_YT = "LINK_THUMB_YT"
CB_LINK_THUMB_MANUAL = "LINK_THUMB_MANUAL"
CB_LINK_TITLE_YT = "LINK_TITLE_YT"
CB_LINK_TITLE_MANUAL = "LINK_TITLE_MANUAL"
CB_LINK_DESC_YT = "LINK_DESC_YT"
CB_LINK_DESC_MANUAL = "LINK_DESC_MANUAL"


def link_thumb_choice_kb():
    rows = [
        [InlineKeyboardButton("تامبنیل اصلی یوتوب", callback_data=CB_LINK_THUMB_YT)],
        [InlineKeyboardButton("تامبنیل دستی آپلود می‌کنم", callback_data=CB_LINK_THUMB_MANUAL)],
        [InlineKeyboardButton("کنسل ↩︎", callback_data=CB_CANCEL)],
    ]
    return InlineKeyboardMarkup(rows)

def link_title_choice_kb():
    rows = [
        [InlineKeyboardButton("تیتر از یوتوب", callback_data=CB_LINK_TITLE_YT)],
        [InlineKeyboardButton("تیتر دستی", callback_data=CB_LINK_TITLE_MANUAL)],
        [InlineKeyboardButton("کنسل ↩︎", callback_data=CB_CANCEL)],
    ]
    return InlineKeyboardMarkup(rows)

def link_desc_choice_kb():
    rows = [
        [InlineKeyboardButton("دیسک از یوتوب", callback_data=CB_LINK_DESC_YT)],
        [InlineKeyboardButton("دیسک دستی", callback_data=CB_LINK_DESC_MANUAL)],
        [InlineKeyboardButton("کنسل ↩︎", callback_data=CB_CANCEL)],
    ]
    return InlineKeyboardMarkup(rows)


def main_menu() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("اضافه کردن با لینک", callback_data=CB_ADD_LINK)],
        [InlineKeyboardButton("اضافه کردن ویدیو", callback_data=CB_ADD_VIDEO)],
        [InlineKeyboardButton("صف انتشار", callback_data=CB_QUEUE)],
        [InlineKeyboardButton("زمان انتشار", callback_data=CB_TIME)],
    ]
    return InlineKeyboardMarkup(rows)

def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("کنسل ↩︎", callback_data=CB_CANCEL)]])

def back_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت به منو ↩︎", callback_data=CB_BACK)]])

CB_TIME_VIEW = "TIME_VIEW"
CB_TIME_SET = "TIME_SET"

def time_menu():
    rows = [
        [InlineKeyboardButton("مشاهده زمان کنونی", callback_data=CB_TIME_VIEW)],
        [InlineKeyboardButton("تغییر زمان کنونی", callback_data=CB_TIME_SET)],
        [InlineKeyboardButton("بازگشت به منو ↩︎", callback_data=CB_BACK)],
    ]
    return InlineKeyboardMarkup(rows)

def queue_menu():
    rows = [
        [InlineKeyboardButton("حذف از صف (با آیدی)", callback_data="QUEUE_DEL")],
        [InlineKeyboardButton("بازگشت به منو ↩︎", callback_data=CB_BACK)],
    ]
    return InlineKeyboardMarkup(rows)
