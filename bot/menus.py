from telegram import InlineKeyboardButton, InlineKeyboardMarkup

CB_ADD_LINK = "ADD_LINK"
CB_ADD_VIDEO = "ADD_VIDEO"
CB_QUEUE = "QUEUE"
CB_TIME = "TIME"
CB_CANCEL = "CANCEL"
CB_BACK = "BACK_MAIN"

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
