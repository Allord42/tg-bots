from aiogram.fsm.state import State, StatesGroup


class NameForm(StatesGroup):
    waiting_join_name = State()
    waiting_rename_target = State()
    waiting_rename_new_name = State()


class BirthdayForm(StatesGroup):
    waiting_date = State()
