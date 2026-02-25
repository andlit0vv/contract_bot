import asyncio
import datetime
import json
import random

import requests
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

API_TOKEN = "8698344682:AAGjNOJcbbMVcTWMHy2HyPg42j_k8ExGF1w"
BACKEND_URL = "http://127.0.0.1:8000/generate-contract"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()


class ContractForm(StatesGroup):
    city_choice = State()
    city_custom = State()

    customer_type = State()
    customer_company = State()
    customer_representative = State()
    customer_inn_choice = State()
    customer_inn_manual = State()
    customer_ogrn_choice = State()
    customer_ogrn_manual = State()
    customer_address_choice = State()
    customer_address_manual = State()
    customer_bank_choice = State()
    customer_bank_manual = State()
    customer_bik_choice = State()
    customer_bik_manual = State()
    customer_corr_choice = State()
    customer_corr_manual = State()
    customer_settlement_choice = State()
    customer_settlement_manual = State()
    customer_kpp_choice = State()
    customer_kpp_manual = State()

    contractor_type = State()
    contractor_company = State()
    contractor_representative = State()
    contractor_inn_choice = State()
    contractor_inn_manual = State()
    contractor_ogrn_choice = State()
    contractor_ogrn_manual = State()
    contractor_address_choice = State()
    contractor_address_manual = State()
    contractor_bank_choice = State()
    contractor_bank_manual = State()
    contractor_bik_choice = State()
    contractor_bik_manual = State()
    contractor_corr_choice = State()
    contractor_corr_manual = State()
    contractor_settlement_choice = State()
    contractor_settlement_manual = State()

    project_description = State()


def generate_contract_number() -> str:
    return f"{datetime.date.today().year}-{random.randint(1000, 9999)}"


def generate_inn() -> str:
    return str(random.randint(10**9, 10**10 - 1))


def generate_ogrn(legal_type: str) -> str:
    if legal_type == "ИП":
        return str(random.randint(10**14, 10**15 - 1))
    return str(random.randint(10**12, 10**13 - 1))


def generate_digits(length: int) -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(length))


def city_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Москва", callback_data="city:moscow")],
            [InlineKeyboardButton(text="Другой город", callback_data="city:other")],
        ]
    )


def legal_type_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="ООО", callback_data=f"{prefix}:ooo")],
            [InlineKeyboardButton(text="ИП", callback_data=f"{prefix}:ip")],
            [InlineKeyboardButton(text="Самозанятый", callback_data=f"{prefix}:self")],
        ]
    )


def input_choice_keyboard(prefix: str, own_text: str, auto_text: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=own_text, callback_data=f"{prefix}:manual")],
            [InlineKeyboardButton(text=auto_text, callback_data=f"{prefix}:auto")],
        ]
    )


def address_choice_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Ввести адрес вручную", callback_data=f"{prefix}:manual")],
            [InlineKeyboardButton(text="Отправить геолокацию", callback_data=f"{prefix}:location")],
        ]
    )


def bank_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Т-Банк", callback_data=f"{prefix}:t_bank")],
            [InlineKeyboardButton(text="Сбербанк", callback_data=f"{prefix}:sber")],
            [InlineKeyboardButton(text="Альфа-Банк", callback_data=f"{prefix}:alfa")],
            [InlineKeyboardButton(text="Другой", callback_data=f"{prefix}:manual")],
        ]
    )


def reverse_geocode(latitude: float, longitude: float) -> str:
    try:
        response = requests.get(
            NOMINATIM_REVERSE_URL,
            params={"format": "jsonv2", "lat": latitude, "lon": longitude, "accept-language": "ru"},
            headers={"User-Agent": "contract-bot/1.0"},
            timeout=10,
        )
        if response.status_code != 200:
            return "Адрес по геолокации не определён"

        address = response.json().get("display_name", "").strip()
        return address or "Адрес по геолокации не определён"
    except Exception:
        return "Адрес по геолокации не определён"


async def ask_customer_ogrn(message: types.Message, state: FSMContext):
    await message.answer(
        "ОГРН/ОГРНИП заказчика:",
        reply_markup=input_choice_keyboard("customer_ogrn", "Ввести вручную", "Сгенерировать ОГРН(ИП)"),
    )
    await state.set_state(ContractForm.customer_ogrn_choice)


async def ask_customer_address(message: types.Message, state: FSMContext):
    await message.answer("Юридический адрес заказчика:", reply_markup=address_choice_keyboard("customer_address"))
    await state.set_state(ContractForm.customer_address_choice)


async def ask_customer_bank(message: types.Message, state: FSMContext):
    await message.answer("Выберите банк заказчика:", reply_markup=bank_keyboard("customer_bank"))
    await state.set_state(ContractForm.customer_bank_choice)


async def ask_customer_bik(message: types.Message, state: FSMContext):
    await message.answer("БИК заказчика:", reply_markup=input_choice_keyboard("customer_bik", "Ввести вручную", "Сгенерировать БИК"))
    await state.set_state(ContractForm.customer_bik_choice)


async def ask_customer_corr(message: types.Message, state: FSMContext):
    await message.answer("к/с заказчика:", reply_markup=input_choice_keyboard("customer_corr", "Ввести вручную", "Сгенерировать к/с"))
    await state.set_state(ContractForm.customer_corr_choice)


async def ask_customer_settlement(message: types.Message, state: FSMContext):
    await message.answer("р/с заказчика:", reply_markup=input_choice_keyboard("customer_settlement", "Ввести вручную", "Сгенерировать р/с"))
    await state.set_state(ContractForm.customer_settlement_choice)


async def ask_contractor_type(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if data.get("customer_type") == "ООО":
        await message.answer("КПП заказчика:", reply_markup=input_choice_keyboard("customer_kpp", "Ввести вручную", "Сгенерировать КПП"))
        await state.set_state(ContractForm.customer_kpp_choice)
        return

    await message.answer("Тип исполнителя:", reply_markup=legal_type_keyboard("contractor_type"))
    await state.set_state(ContractForm.contractor_type)


async def ask_contractor_inn(message: types.Message, state: FSMContext):
    await message.answer("ИНН исполнителя:", reply_markup=input_choice_keyboard("contractor_inn", "Ввести вручную", "Сгенерировать ИНН"))
    await state.set_state(ContractForm.contractor_inn_choice)


async def ask_contractor_ogrn(message: types.Message, state: FSMContext):
    await message.answer("ОГРН/ОГРНИП исполнителя:", reply_markup=input_choice_keyboard("contractor_ogrn", "Ввести вручную", "Сгенерировать ОГРН(ИП)"))
    await state.set_state(ContractForm.contractor_ogrn_choice)


async def ask_contractor_address(message: types.Message, state: FSMContext):
    await message.answer("Юридический адрес исполнителя:", reply_markup=address_choice_keyboard("contractor_address"))
    await state.set_state(ContractForm.contractor_address_choice)


async def ask_contractor_bank(message: types.Message, state: FSMContext):
    await message.answer("Выберите банк исполнителя:", reply_markup=bank_keyboard("contractor_bank"))
    await state.set_state(ContractForm.contractor_bank_choice)


async def ask_contractor_bik(message: types.Message, state: FSMContext):
    await message.answer("БИК исполнителя:", reply_markup=input_choice_keyboard("contractor_bik", "Ввести вручную", "Сгенерировать БИК"))
    await state.set_state(ContractForm.contractor_bik_choice)


async def ask_contractor_corr(message: types.Message, state: FSMContext):
    await message.answer("к/с исполнителя:", reply_markup=input_choice_keyboard("contractor_corr", "Ввести вручную", "Сгенерировать к/с"))
    await state.set_state(ContractForm.contractor_corr_choice)


async def ask_contractor_settlement(message: types.Message, state: FSMContext):
    await message.answer("р/с исполнителя:", reply_markup=input_choice_keyboard("contractor_settlement", "Ввести вручную", "Сгенерировать р/с"))
    await state.set_state(ContractForm.contractor_settlement_choice)


@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Выберите город:", reply_markup=city_keyboard())
    await state.set_state(ContractForm.city_choice)


@dp.callback_query(ContractForm.city_choice, F.data.startswith("city:"))
async def city_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split(":", maxsplit=1)[1]
    await callback.answer()

    if choice == "moscow":
        await state.update_data(city="Москва")
        await callback.message.edit_text("Город: Москва")
        await callback.message.answer("Тип заказчика:", reply_markup=legal_type_keyboard("customer_type"))
        await state.set_state(ContractForm.customer_type)
        return

    await callback.message.edit_text("Город: выбран ручной ввод")
    await callback.message.answer("Введите название города:")
    await state.set_state(ContractForm.city_custom)


@dp.message(ContractForm.city_custom)
async def city_custom_handler(message: types.Message, state: FSMContext):
    await state.update_data(city=(message.text or "").strip())
    await message.answer("Тип заказчика:", reply_markup=legal_type_keyboard("customer_type"))
    await state.set_state(ContractForm.customer_type)


@dp.callback_query(ContractForm.customer_type, F.data.startswith("customer_type:"))
async def customer_type_handler(callback: types.CallbackQuery, state: FSMContext):
    selected_map = {"ooo": "ООО", "ip": "ИП", "self": "Самозанятый"}
    selected_value = selected_map[callback.data.split(":", maxsplit=1)[1]]

    await state.update_data(customer_type=selected_value)
    await callback.message.edit_text(f"Тип заказчика: {selected_value}")
    await callback.message.answer("Введите название компании заказчика или напишите 'LLM', чтобы сгенерировать.")
    await callback.answer()
    await state.set_state(ContractForm.customer_company)


@dp.message(ContractForm.customer_company)
async def customer_company_handler(message: types.Message, state: FSMContext):
    company_name = "Компания, сгенерированная LLM" if (message.text or "").lower() == "llm" else message.text
    await state.update_data(customer_company_name=company_name)
    await message.answer("Введите ФИО представителя заказчика:")
    await state.set_state(ContractForm.customer_representative)


@dp.message(ContractForm.customer_representative)
async def customer_representative_handler(message: types.Message, state: FSMContext):
    await state.update_data(customer_representative_name=message.text)
    await message.answer("ИНН заказчика:", reply_markup=input_choice_keyboard("customer_inn", "Ввести вручную", "Сгенерировать ИНН"))
    await state.set_state(ContractForm.customer_inn_choice)


@dp.callback_query(ContractForm.customer_inn_choice, F.data.startswith("customer_inn:"))
async def customer_inn_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split(":", maxsplit=1)[1]
    if choice == "auto":
        inn = generate_inn()
        await state.update_data(customer_inn=inn)
        await callback.message.edit_text(f"ИНН заказчика: {inn} (сгенерирован)")
        await ask_customer_ogrn(callback.message, state)
    else:
        await callback.message.edit_text("ИНН заказчика: выбран ручной ввод")
        await callback.message.answer("Введите ИНН заказчика:")
        await state.set_state(ContractForm.customer_inn_manual)
    await callback.answer()


@dp.message(ContractForm.customer_inn_manual)
async def customer_inn_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(customer_inn=message.text)
    await ask_customer_ogrn(message, state)


@dp.callback_query(ContractForm.customer_ogrn_choice, F.data.startswith("customer_ogrn:"))
async def customer_ogrn_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split(":", maxsplit=1)[1]
    legal_type = (await state.get_data()).get("customer_type", "ООО")
    if choice == "auto":
        ogrn = generate_ogrn(legal_type)
        await state.update_data(customer_ogrn_or_ogrnip=ogrn)
        await callback.message.edit_text(f"ОГРН/ОГРНИП заказчика: {ogrn} (сгенерирован)")
        await ask_customer_address(callback.message, state)
    else:
        await callback.message.edit_text("ОГРН/ОГРНИП заказчика: выбран ручной ввод")
        await callback.message.answer("Введите ОГРН/ОГРНИП заказчика:")
        await state.set_state(ContractForm.customer_ogrn_manual)
    await callback.answer()


@dp.message(ContractForm.customer_ogrn_manual)
async def customer_ogrn_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(customer_ogrn_or_ogrnip=message.text)
    await ask_customer_address(message, state)


@dp.callback_query(ContractForm.customer_address_choice, F.data.startswith("customer_address:"))
async def customer_address_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split(":", maxsplit=1)[1]
    if choice == "manual":
        await callback.message.edit_text("Юридический адрес заказчика: выбран ручной ввод")
        await callback.message.answer("Введите юридический адрес заказчика:")
        await state.set_state(ContractForm.customer_address_manual)
    else:
        await callback.message.edit_text("Отправьте геолокацию заказчика (через Telegram location).")
    await callback.answer()


@dp.message(ContractForm.customer_address_choice, F.location)
async def customer_address_location_handler(message: types.Message, state: FSMContext):
    loc = message.location
    address = reverse_geocode(loc.latitude, loc.longitude)
    await state.update_data(customer_legal_address=address)
    await message.answer(f"Геолокация получена. Определённый адрес: {address}")
    await ask_customer_bank(message, state)


@dp.message(ContractForm.customer_address_manual)
async def customer_address_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(customer_legal_address=message.text)
    await ask_customer_bank(message, state)


@dp.callback_query(ContractForm.customer_bank_choice, F.data.startswith("customer_bank:"))
async def customer_bank_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    selected = callback.data.split(":", maxsplit=1)[1]
    bank_map = {"t_bank": "Т-Банк", "sber": "Сбербанк", "alfa": "Альфа-Банк"}
    if selected == "manual":
        await callback.message.edit_text("Банк заказчика: выбран ручной ввод")
        await callback.message.answer("Введите банк заказчика:")
        await state.set_state(ContractForm.customer_bank_manual)
    else:
        await state.update_data(customer_bank=bank_map[selected])
        await callback.message.edit_text(f"Банк заказчика: {bank_map[selected]}")
        await ask_customer_bik(callback.message, state)
    await callback.answer()


@dp.message(ContractForm.customer_bank_manual)
async def customer_bank_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(customer_bank=message.text)
    await ask_customer_bik(message, state)


@dp.callback_query(ContractForm.customer_bik_choice, F.data.startswith("customer_bik:"))
async def customer_bik_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split(":", maxsplit=1)[1]
    if choice == "auto":
        value = generate_digits(9)
        await state.update_data(customer_bik=value)
        await callback.message.edit_text(f"БИК заказчика: {value} (сгенерирован)")
        await ask_customer_corr(callback.message, state)
    else:
        await callback.message.edit_text("БИК заказчика: выбран ручной ввод")
        await callback.message.answer("Введите БИК заказчика:")
        await state.set_state(ContractForm.customer_bik_manual)
    await callback.answer()


@dp.message(ContractForm.customer_bik_manual)
async def customer_bik_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(customer_bik=message.text)
    await ask_customer_corr(message, state)


@dp.callback_query(ContractForm.customer_corr_choice, F.data.startswith("customer_corr:"))
async def customer_corr_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split(":", maxsplit=1)[1]
    if choice == "auto":
        value = generate_digits(20)
        await state.update_data(customer_correspondent_account=value)
        await callback.message.edit_text(f"к/с заказчика: {value} (сгенерирован)")
        await ask_customer_settlement(callback.message, state)
    else:
        await callback.message.edit_text("к/с заказчика: выбран ручной ввод")
        await callback.message.answer("Введите к/с заказчика:")
        await state.set_state(ContractForm.customer_corr_manual)
    await callback.answer()


@dp.message(ContractForm.customer_corr_manual)
async def customer_corr_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(customer_correspondent_account=message.text)
    await ask_customer_settlement(message, state)


@dp.callback_query(ContractForm.customer_settlement_choice, F.data.startswith("customer_settlement:"))
async def customer_settlement_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split(":", maxsplit=1)[1]
    if choice == "auto":
        value = generate_digits(20)
        await state.update_data(customer_settlement_account=value)
        await callback.message.edit_text(f"р/с заказчика: {value} (сгенерирован)")
        await ask_contractor_type(callback.message, state)
    else:
        await callback.message.edit_text("р/с заказчика: выбран ручной ввод")
        await callback.message.answer("Введите р/с заказчика:")
        await state.set_state(ContractForm.customer_settlement_manual)
    await callback.answer()


@dp.message(ContractForm.customer_settlement_manual)
async def customer_settlement_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(customer_settlement_account=message.text)
    await ask_contractor_type(message, state)


@dp.callback_query(ContractForm.customer_kpp_choice, F.data.startswith("customer_kpp:"))
async def customer_kpp_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split(":", maxsplit=1)[1]
    if choice == "auto":
        kpp = generate_digits(9)
        await state.update_data(customer_kpp=kpp)
        await callback.message.edit_text(f"КПП заказчика: {kpp} (сгенерирован)")
        await callback.message.answer("Тип исполнителя:", reply_markup=legal_type_keyboard("contractor_type"))
        await state.set_state(ContractForm.contractor_type)
    else:
        await callback.message.edit_text("КПП заказчика: выбран ручной ввод")
        await callback.message.answer("Введите КПП заказчика:")
        await state.set_state(ContractForm.customer_kpp_manual)
    await callback.answer()


@dp.message(ContractForm.customer_kpp_manual)
async def customer_kpp_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(customer_kpp=message.text)
    await message.answer("Тип исполнителя:", reply_markup=legal_type_keyboard("contractor_type"))
    await state.set_state(ContractForm.contractor_type)


@dp.callback_query(ContractForm.contractor_type, F.data.startswith("contractor_type:"))
async def contractor_type_handler(callback: types.CallbackQuery, state: FSMContext):
    selected_map = {"ooo": "ООО", "ip": "ИП", "self": "Самозанятый"}
    selected_value = selected_map[callback.data.split(":", maxsplit=1)[1]]

    await state.update_data(contractor_type=selected_value)
    await callback.message.edit_text(f"Тип исполнителя: {selected_value}")
    await callback.message.answer("Введите название компании исполнителя или напишите 'LLM', чтобы сгенерировать.")
    await callback.answer()
    await state.set_state(ContractForm.contractor_company)


@dp.message(ContractForm.contractor_company)
async def contractor_company_handler(message: types.Message, state: FSMContext):
    company_name = "Исполнитель, сгенерированный LLM" if (message.text or "").lower() == "llm" else message.text
    await state.update_data(contractor_company_name=company_name)

    await message.answer("Введите ФИО представителя исполнителя:")
    await state.set_state(ContractForm.contractor_representative)


@dp.message(ContractForm.contractor_representative)
async def contractor_representative_handler(message: types.Message, state: FSMContext):
    await state.update_data(contractor_representative_name=message.text)
    await ask_contractor_inn(message, state)


@dp.callback_query(ContractForm.contractor_inn_choice, F.data.startswith("contractor_inn:"))
async def contractor_inn_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split(":", maxsplit=1)[1]
    if choice == "auto":
        value = generate_inn()
        await state.update_data(contractor_inn=value)
        await callback.message.edit_text(f"ИНН исполнителя: {value} (сгенерирован)")
        await ask_contractor_ogrn(callback.message, state)
    else:
        await callback.message.edit_text("ИНН исполнителя: выбран ручной ввод")
        await callback.message.answer("Введите ИНН исполнителя:")
        await state.set_state(ContractForm.contractor_inn_manual)
    await callback.answer()


@dp.message(ContractForm.contractor_inn_manual)
async def contractor_inn_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(contractor_inn=message.text)
    await ask_contractor_ogrn(message, state)


@dp.callback_query(ContractForm.contractor_ogrn_choice, F.data.startswith("contractor_ogrn:"))
async def contractor_ogrn_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split(":", maxsplit=1)[1]
    legal_type = (await state.get_data()).get("contractor_type", "ИП")
    if choice == "auto":
        value = generate_ogrn(legal_type)
        await state.update_data(contractor_ogrn_or_ogrnip=value)
        await callback.message.edit_text(f"ОГРН/ОГРНИП исполнителя: {value} (сгенерирован)")
        await ask_contractor_address(callback.message, state)
    else:
        await callback.message.edit_text("ОГРН/ОГРНИП исполнителя: выбран ручной ввод")
        await callback.message.answer("Введите ОГРН/ОГРНИП исполнителя:")
        await state.set_state(ContractForm.contractor_ogrn_manual)
    await callback.answer()


@dp.message(ContractForm.contractor_ogrn_manual)
async def contractor_ogrn_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(contractor_ogrn_or_ogrnip=message.text)
    await ask_contractor_address(message, state)


@dp.callback_query(ContractForm.contractor_address_choice, F.data.startswith("contractor_address:"))
async def contractor_address_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split(":", maxsplit=1)[1]
    if choice == "manual":
        await callback.message.edit_text("Юридический адрес исполнителя: выбран ручной ввод")
        await callback.message.answer("Введите юридический адрес исполнителя:")
        await state.set_state(ContractForm.contractor_address_manual)
    else:
        await callback.message.edit_text("Отправьте геолокацию исполнителя (через Telegram location).")
    await callback.answer()


@dp.message(ContractForm.contractor_address_choice, F.location)
async def contractor_address_location_handler(message: types.Message, state: FSMContext):
    loc = message.location
    address = reverse_geocode(loc.latitude, loc.longitude)
    await state.update_data(contractor_legal_address=address)
    await message.answer(f"Геолокация получена. Определённый адрес: {address}")
    await ask_contractor_bank(message, state)


@dp.message(ContractForm.contractor_address_manual)
async def contractor_address_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(contractor_legal_address=message.text)
    await ask_contractor_bank(message, state)


@dp.callback_query(ContractForm.contractor_bank_choice, F.data.startswith("contractor_bank:"))
async def contractor_bank_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    selected = callback.data.split(":", maxsplit=1)[1]
    bank_map = {"t_bank": "Т-Банк", "sber": "Сбербанк", "alfa": "Альфа-Банк"}
    if selected == "manual":
        await callback.message.edit_text("Банк исполнителя: выбран ручной ввод")
        await callback.message.answer("Введите банк исполнителя:")
        await state.set_state(ContractForm.contractor_bank_manual)
    else:
        await state.update_data(contractor_bank=bank_map[selected])
        await callback.message.edit_text(f"Банк исполнителя: {bank_map[selected]}")
        await ask_contractor_bik(callback.message, state)
    await callback.answer()


@dp.message(ContractForm.contractor_bank_manual)
async def contractor_bank_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(contractor_bank=message.text)
    await ask_contractor_bik(message, state)


@dp.callback_query(ContractForm.contractor_bik_choice, F.data.startswith("contractor_bik:"))
async def contractor_bik_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split(":", maxsplit=1)[1]
    if choice == "auto":
        value = generate_digits(9)
        await state.update_data(contractor_bik=value)
        await callback.message.edit_text(f"БИК исполнителя: {value} (сгенерирован)")
        await ask_contractor_corr(callback.message, state)
    else:
        await callback.message.edit_text("БИК исполнителя: выбран ручной ввод")
        await callback.message.answer("Введите БИК исполнителя:")
        await state.set_state(ContractForm.contractor_bik_manual)
    await callback.answer()


@dp.message(ContractForm.contractor_bik_manual)
async def contractor_bik_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(contractor_bik=message.text)
    await ask_contractor_corr(message, state)


@dp.callback_query(ContractForm.contractor_corr_choice, F.data.startswith("contractor_corr:"))
async def contractor_corr_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split(":", maxsplit=1)[1]
    if choice == "auto":
        value = generate_digits(20)
        await state.update_data(contractor_correspondent_account=value)
        await callback.message.edit_text(f"к/с исполнителя: {value} (сгенерирован)")
        await ask_contractor_settlement(callback.message, state)
    else:
        await callback.message.edit_text("к/с исполнителя: выбран ручной ввод")
        await callback.message.answer("Введите к/с исполнителя:")
        await state.set_state(ContractForm.contractor_corr_manual)
    await callback.answer()


@dp.message(ContractForm.contractor_corr_manual)
async def contractor_corr_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(contractor_correspondent_account=message.text)
    await ask_contractor_settlement(message, state)


@dp.callback_query(ContractForm.contractor_settlement_choice, F.data.startswith("contractor_settlement:"))
async def contractor_settlement_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split(":", maxsplit=1)[1]
    if choice == "auto":
        value = generate_digits(20)
        await state.update_data(contractor_settlement_account=value)
        await callback.message.edit_text(f"р/с исполнителя: {value} (сгенерирован)")
        await callback.message.answer("Кратко опишите проект (1–5 предложений):")
        await state.set_state(ContractForm.project_description)
    else:
        await callback.message.edit_text("р/с исполнителя: выбран ручной ввод")
        await callback.message.answer("Введите р/с исполнителя:")
        await state.set_state(ContractForm.contractor_settlement_manual)
    await callback.answer()


@dp.message(ContractForm.contractor_settlement_manual)
async def contractor_settlement_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(contractor_settlement_account=message.text)
    await message.answer("Кратко опишите проект (1–5 предложений):")
    await state.set_state(ContractForm.project_description)


@dp.message(ContractForm.project_description)
async def project_description_handler(message: types.Message, state: FSMContext):
    await state.update_data(project_description=message.text)
    data = await state.get_data()

    today = datetime.date.today()
    contract_payload = {
        "contract_number": generate_contract_number(),
        "city": data.get("city") or "Москва",
        "contract_day": str(today.day),
        "contract_month": today.strftime("%m"),
        "contract_year": str(today.year),
        "customer_company_name": data.get("customer_company_name") or "Не указано",
        "customer_representative_name": data.get("customer_representative_name") or "Не указано",
        "customer_representative_basis": "Устава",
        "customer_inn": data.get("customer_inn") or "Не указано",
        "customer_ogrn_or_ogrnip": data.get("customer_ogrn_or_ogrnip") or "Не указано",
        "customer_legal_address": data.get("customer_legal_address") or "Не указано",
        "customer_bank": data.get("customer_bank") or "Не указано",
        "customer_bik": data.get("customer_bik") or "Не указано",
        "customer_correspondent_account": data.get("customer_correspondent_account") or "Не указано",
        "customer_settlement_account": data.get("customer_settlement_account") or "Не указано",
        "customer_kpp": data.get("customer_kpp") or "Не указано",
        "contractor_type": data.get("contractor_type") or "ИП",
        "contractor_company_name": data.get("contractor_company_name") or "Не указано",
        "contractor_representative_name": data.get("contractor_representative_name") or "Не указано",
        "contractor_representative_basis": "Устава",
        "contractor_inn": data.get("contractor_inn") or "Не указано",
        "contractor_ogrn_or_ogrnip": data.get("contractor_ogrn_or_ogrnip") or "Не указано",
        "contractor_legal_address": data.get("contractor_legal_address") or "Не указано",
        "contractor_bank": data.get("contractor_bank") or "Не указано",
        "contractor_bik": data.get("contractor_bik") or "Не указано",
        "contractor_correspondent_account": data.get("contractor_correspondent_account") or "Не указано",
        "contractor_settlement_account": data.get("contractor_settlement_account") or "Не указано",
        "vat_type": "Без НДС",
        "project_description": data.get("project_description") or "",
    }

    print(json.dumps(contract_payload, indent=4, ensure_ascii=False))

    try:
        response = requests.post(BACKEND_URL, json=contract_payload, timeout=10)
        if response.status_code == 200:
            await message.answer("Данные успешно сохранены и отправлены на backend.")
        else:
            await message.answer(f"Backend вернул ошибку: {response.status_code} {response.text}")
    except Exception:
        await message.answer("Backend недоступен. Попробуйте позже.")

    await state.clear()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
