import asyncio
import datetime
import json
import random
import os
import shutil
from pathlib import Path

import aiohttp
import requests
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaDocument,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

API_TOKEN = "8698344682:AAGjNOJcbbMVcTWMHy2HyPg42j_k8ExGF1w"
BACKEND_URL = "http://127.0.0.1:8000/generate-contract"
BACKEND_TIMEOUT_SECONDS = int(os.getenv("BACKEND_TIMEOUT_SECONDS", "180"))
GENERATED_DOCX_PATH = Path(__file__).resolve().with_name("contractfinal.docx")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

T_BANK_EMOJI_ID = "5228821549838000334"
T_BANK_EMOJI_FALLBACK = "🏦"

SBER_EMOJI_ID = "5258383045232183945"
SBER_EMOJI_FALLBACK = "💫"

ALFA_EMOJI_ID = "5231147734190269621"
ALFA_EMOJI_FALLBACK = "❤️"

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
    contractor_representative = State()
    contractor_requisites_choice = State()
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


def contractor_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="ИП", callback_data="contractor_type:ip")],
            [InlineKeyboardButton(text="ООО", callback_data="contractor_type:ooo")],
            [InlineKeyboardButton(text="Самозанятый", callback_data="contractor_type:self")],
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
    """
    Build bank selection keyboard using InlineKeyboardBuilder.
    Layout:
      Row 1 — T-Bank (primary), Sberbank (success)
      Row 2 — Alfa-Bank (danger), Other (default)
    Falls back to emoji-only text buttons if styles or icon_custom_emoji_id
    are not supported in the current aiogram / Bot API version.
    """

    def make_button(
        text: str,
        suffix: str,
        *,
        style: str | None,
        icon_id: str | None,
        fallback_text: str,
    ) -> InlineKeyboardButton:
        base_kwargs = {
            "text": text,
            "callback_data": f"{prefix}:{suffix}",
        }
        styled_kwargs = dict(base_kwargs)
        if style is not None:
            styled_kwargs["style"] = style
        if icon_id is not None:
            styled_kwargs["icon_custom_emoji_id"] = icon_id

        try:
            return InlineKeyboardButton(**styled_kwargs)
        except TypeError:
            return InlineKeyboardButton(
                text=fallback_text,
                callback_data=f"{prefix}:{suffix}",
            )

    btn_t = make_button(
        text="Т-Банк",
        suffix="t_bank",
        style="default",
        icon_id=T_BANK_EMOJI_ID,
        fallback_text="🏦 Т-Банк",
    )
    btn_s = make_button(
        text="Sberbank",
        suffix="sber",
        style="success",
        icon_id=SBER_EMOJI_ID,
        fallback_text="💫 Sberbank",
    )
    btn_a = make_button(
        text="Alfa-Bank",
        suffix="alfa",
        style="danger",
        icon_id=ALFA_EMOJI_ID,
        fallback_text="❤️ Alfa-Bank",
    )
    btn_other = make_button(
        text="Other",
        suffix="manual",
        style="default",
        icon_id=None,
        fallback_text="Other",
    )

    builder = InlineKeyboardBuilder()
    builder.row(btn_t, btn_s)
    builder.row(btn_a, btn_other)
    return builder.as_markup()


async def reverse_geocode_address(latitude: float, longitude: float) -> str | None:
    """
    Reverse geocode coordinates to a formatted address "Street, House".
    Uses OpenStreetMap Nominatim with proper async requests, User-Agent and timeout.
    Returns None on any failure. Coordinates are not stored.
    """

    # Basic validation of coordinate ranges
    if not (-90.0 <= float(latitude) <= 90.0 and -180.0 <= float(longitude) <= 180.0):
        return None

    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "format": "jsonv2",
        "lat": str(latitude),
        "lon": str(longitude),
        "addressdetails": 1,
    }
    headers = {
        # Adjust contact information if needed to comply with Nominatim usage policy
        "User-Agent": "contract-bot/1.0 (+https://t.me/your_bot_username)",
        "Accept-Language": "ru,en",
    }

    timeout = aiohttp.ClientTimeout(total=5)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params, headers=headers) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return None
    except Exception:
        return None

    address = data.get("address") or {}

    # Extract only street-like fields and house_number; ignore business names.
    street = (
        address.get("road")
        or address.get("pedestrian")
        or address.get("footway")
        or address.get("residential")
        or address.get("street")
    )
    house = address.get("house_number")

    if not street or not house:
        return None

    return f"{street}, {house}"


def location_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Share location", request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def ask_customer_ogrn(message: types.Message, state: FSMContext):
    await message.answer("Введите ОГРН или ОГРНИП заказчика.")
    await state.set_state(ContractForm.customer_ogrn_manual)


async def ask_customer_address(message: types.Message, state: FSMContext):
    await message.answer(
        "Укажите юридический адрес заказчика. Можно отправить текстом или геолокацией.",
        reply_markup=location_reply_keyboard(),
    )
    await state.set_state(ContractForm.customer_address_choice)


async def ask_customer_bank(message: types.Message, state: FSMContext):
    await message.answer("Выберите банк заказчика.", reply_markup=bank_keyboard("customer_bank"))
    await state.set_state(ContractForm.customer_bank_choice)


async def ask_customer_bik(message: types.Message, state: FSMContext):
    await message.answer("БИК заказчика:")
    await state.set_state(ContractForm.customer_bik_manual)


async def ask_customer_corr(message: types.Message, state: FSMContext):
    await message.answer("Введите корреспондентский счет")
    await state.set_state(ContractForm.customer_corr_manual)


async def ask_customer_settlement(message: types.Message, state: FSMContext):
    await message.answer("Введите расчетный счет")
    await state.set_state(ContractForm.customer_settlement_manual)


async def ask_contractor_type(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if data.get("customer_type") == "ООО" and data.get("customer_requisites_mode") != "auto":
        await message.answer("Введите КПП заказчика:")
        await state.set_state(ContractForm.customer_kpp_manual)
        return

    await message.answer("Выберите тип исполнителя.", reply_markup=contractor_type_keyboard())
    await state.set_state(ContractForm.contractor_type)


async def ask_contractor_inn(message: types.Message, state: FSMContext):
    await message.answer("ИНН исполнителя:")
    await state.set_state(ContractForm.contractor_inn_manual)


async def ask_contractor_ogrn(message: types.Message, state: FSMContext):
    await message.answer("ОГРН/ОГРНИП исполнителя:")
    await state.set_state(ContractForm.contractor_ogrn_manual)


async def ask_contractor_address(message: types.Message, state: FSMContext):
    await message.answer(
        "Юридический адрес исполнителя. Отправьте адрес текстом или нажмите кнопку ниже, чтобы поделиться геолокацией.",
        reply_markup=location_reply_keyboard(),
    )
    await state.set_state(ContractForm.contractor_address_choice)


async def ask_contractor_bank(message: types.Message, state: FSMContext):
    await message.answer("Выберите банк исполнителя:", reply_markup=bank_keyboard("contractor_bank"))
    await state.set_state(ContractForm.contractor_bank_choice)


async def ask_contractor_bik(message: types.Message, state: FSMContext):
    await message.answer("БИК исполнителя:")
    await state.set_state(ContractForm.contractor_bik_manual)


async def ask_contractor_corr(message: types.Message, state: FSMContext):
    await message.answer("к/с исполнителя:")
    await state.set_state(ContractForm.contractor_corr_manual)


async def ask_contractor_settlement(message: types.Message, state: FSMContext):
    await message.answer("р/с исполнителя:")
    await state.set_state(ContractForm.contractor_settlement_manual)


async def ask_project_description(message: types.Message, state: FSMContext):
    await message.answer(
        "Кратко опишите проект: что именно необходимо разработать."
    )
    await state.set_state(ContractForm.project_description)


@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет, я бот-составитель договоров на разработку ПО. Чтобы составить договор, мне нужны реквизиты сторон и описание самого ПО.",
    )
    await message.answer(
        "Для начала нужно выбрать, кто с кем договаривается. Выберите тип заказчика.",
        reply_markup=legal_type_keyboard("customer_type"),
    )
    await state.set_state(ContractForm.customer_type)


@dp.callback_query(ContractForm.city_choice, F.data.startswith("city:"))
async def city_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    choice = callback.data.split(":", maxsplit=1)[1]

    if choice == "moscow":
        await state.update_data(city="Москва")
        await callback.message.edit_text("Город: Москва")
        await ask_project_description(callback.message, state)
        return

    await callback.message.edit_text("Город: выбран ручной ввод")
    await callback.message.answer("Введите название города:")
    await state.set_state(ContractForm.city_custom)


@dp.message(ContractForm.city_custom)
async def city_custom_handler(message: types.Message, state: FSMContext):
    await state.update_data(city=(message.text or "").strip())
    await ask_project_description(message, state)


@dp.callback_query(ContractForm.customer_type, F.data.startswith("customer_type:"))
async def customer_type_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    selected_map = {"ooo": "ООО", "ip": "ИП", "self": "Самозанятый"}
    selected_value = selected_map[callback.data.split(":", maxsplit=1)[1]]

    if selected_value != "ООО":
        await callback.message.edit_text(
            "Sorry, we currently cannot generate this type of contract. Please select another type.",
            reply_markup=legal_type_keyboard("customer_type"),
        )
        return

    await state.update_data(customer_type=selected_value)
    await callback.message.edit_text(f"Тип заказчика: {selected_value}")
    await callback.message.answer(
        "Введите название компании, например, T2Mobile."
    )
    await state.set_state(ContractForm.customer_company)


@dp.message(ContractForm.customer_company)
async def customer_company_handler(message: types.Message, state: FSMContext):
    company_name = "Компания, сгенерированная LLM" if (message.text or "").lower() == "llm" else message.text
    await state.update_data(customer_company_name=company_name)
    await message.answer("Введите ФИО представителя заказчика.")
    await state.set_state(ContractForm.customer_representative)


@dp.message(ContractForm.customer_representative)
async def customer_representative_handler(message: types.Message, state: FSMContext):
    await state.update_data(customer_representative_name=message.text)
    await message.answer(
        "Как заполнить юридические реквизиты заказчика?",
        reply_markup=input_choice_keyboard("customer_inn", "Ввести вручную", "Сгенерировать автоматически"),
    )
    await state.set_state(ContractForm.customer_inn_choice)


@dp.callback_query(ContractForm.customer_inn_choice, F.data.startswith("customer_inn:"))
async def customer_inn_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    choice = callback.data.split(":", maxsplit=1)[1]
    if choice == "auto":
        data = await state.get_data()
        legal_type = data.get("customer_type", "ООО")

        inn = generate_inn()
        ogrn = generate_ogrn(legal_type)
        bik = generate_digits(9)
        correspondent = generate_digits(20)
        settlement = generate_digits(20)

        update_payload = {
            "customer_requisites_mode": "auto",
            "customer_inn": inn,
            "customer_ogrn_or_ogrnip": ogrn,
            "customer_bik": bik,
            "customer_correspondent_account": correspondent,
            "customer_settlement_account": settlement,
        }

        if legal_type == "ООО":
            update_payload["customer_kpp"] = generate_digits(9)

        await state.update_data(**update_payload)

        await callback.message.edit_text("Реквизиты заказчика будут сформированы автоматически.")
        await callback.message.answer("Теперь укажем юридический адрес и банк заказчика.")
        await ask_customer_address(callback.message, state)
    else:
        await state.update_data(customer_requisites_mode="manual")
        await callback.message.edit_text("Выбран ручной ввод реквизитов заказчика.")
        await callback.message.answer("Введите ИНН заказчика.")
        await state.set_state(ContractForm.customer_inn_manual)


@dp.message(ContractForm.customer_inn_manual)
async def customer_inn_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(customer_inn=message.text)
    await ask_customer_ogrn(message, state)


@dp.callback_query(ContractForm.customer_ogrn_choice, F.data.startswith("customer_ogrn:"))
async def customer_ogrn_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    choice = callback.data.split(":", maxsplit=1)[1]
    legal_type = (await state.get_data()).get("customer_type", "ООО")
    if choice == "auto":
        ogrn = generate_ogrn(legal_type)
        await state.update_data(customer_ogrn_or_ogrnip=ogrn)
        await callback.message.edit_text(f"ОГРН/ОГРНИП заказчика: {ogrn} (сгенерирован)")
        await ask_customer_address(callback.message, state)
    else:
        await callback.message.edit_text("ОГРН/ОГРНИП заказчика: выбран ручной ввод")
        await callback.message.answer("Введите ОГРН или ОГРНИП заказчика.")
        await state.set_state(ContractForm.customer_ogrn_manual)


@dp.message(ContractForm.customer_ogrn_manual)
async def customer_ogrn_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(customer_ogrn_or_ogrnip=message.text)
    await ask_customer_address(message, state)


@dp.message(ContractForm.customer_address_choice, F.location)
async def customer_address_location_handler(message: types.Message, state: FSMContext):
    loc = message.location
    formatted = await reverse_geocode_address(loc.latitude, loc.longitude)
    if formatted:
        await state.update_data(customer_legal_address=formatted)
        await message.answer(
            f"Определён юридический адрес заказчика: {formatted}",
            reply_markup=ReplyKeyboardRemove(),
        )
        await ask_customer_bank(message, state)
    else:
        await message.answer(
            "Адрес не удалось определить автоматически. Введите его вручную.",
            reply_markup=ReplyKeyboardRemove(),
        )
        # Остаёмся в состоянии ContractForm.customer_address_choice и ждём текстовый ввод


@dp.message(ContractForm.customer_address_choice, F.text)
async def customer_address_text_handler(message: types.Message, state: FSMContext):
    await state.update_data(customer_legal_address=message.text)
    await message.answer(
        "Юридический адрес заказчика сохранен.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await ask_customer_bank(message, state)


@dp.message(ContractForm.customer_address_manual)
async def customer_address_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(customer_legal_address=message.text)
    await ask_customer_bank(message, state)


@dp.callback_query(ContractForm.customer_bank_choice, F.data.startswith("customer_bank:"))
async def customer_bank_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    selected = callback.data.split(":", maxsplit=1)[1]
    data = await state.get_data()
    bank_map = {"t_bank": "Т-Банк", "sber": "Сбербанк", "alfa": "Альфа-Банк"}
    if selected == "manual":
        await callback.message.edit_text("Банк заказчика: выбран ручной ввод")
        await callback.message.answer("Введите банк заказчика:")
        await state.set_state(ContractForm.customer_bank_manual)
    else:
        await state.update_data(customer_bank=bank_map[selected])
        await callback.message.edit_text(f"Банк заказчика: {bank_map[selected]}")
        # In auto requisites mode, all numeric fields are already generated;
        # proceed directly to contractor block without asking BIK/corr/settlement.
        if data.get("customer_requisites_mode") == "auto":
            await callback.message.answer("Отлично, данные заказчика полностью сформированы.")
            await ask_contractor_type(callback.message, state)
        else:
            await ask_customer_bik(callback.message, state)


@dp.message(ContractForm.customer_bank_manual)
async def customer_bank_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(customer_bank=message.text)
    await ask_customer_bik(message, state)


@dp.callback_query(ContractForm.customer_bik_choice, F.data.startswith("customer_bik:"))
async def customer_bik_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
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


@dp.message(ContractForm.customer_bik_manual)
async def customer_bik_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(customer_bik=message.text)
    await ask_customer_corr(message, state)


@dp.callback_query(ContractForm.customer_corr_choice, F.data.startswith("customer_corr:"))
async def customer_corr_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    choice = callback.data.split(":", maxsplit=1)[1]
    if choice == "auto":
        value = generate_digits(20)
        await state.update_data(customer_correspondent_account=value)
        await callback.message.edit_text(f"Корреспондентский счет: {value} (сгенерирован)")
        await ask_customer_settlement(callback.message, state)
    else:
        await callback.message.edit_text("Корреспондентский счет: выбран ручной ввод")
        await callback.message.answer("Введите корреспондентский счет")
        await state.set_state(ContractForm.customer_corr_manual)


@dp.message(ContractForm.customer_corr_manual)
async def customer_corr_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(customer_correspondent_account=message.text)
    await ask_customer_settlement(message, state)


@dp.callback_query(ContractForm.customer_settlement_choice, F.data.startswith("customer_settlement:"))
async def customer_settlement_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    choice = callback.data.split(":", maxsplit=1)[1]
    if choice == "auto":
        value = generate_digits(20)
        await state.update_data(customer_settlement_account=value)
        await callback.message.edit_text(f"Расчетный счет: {value} (сгенерирован)")
        await ask_contractor_type(callback.message, state)
    else:
        await callback.message.edit_text("Расчетный счет: выбран ручной ввод")
        await callback.message.answer("Введите расчетный счет")
        await state.set_state(ContractForm.customer_settlement_manual)


@dp.message(ContractForm.customer_settlement_manual)
async def customer_settlement_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(customer_settlement_account=message.text)
    await ask_contractor_type(message, state)


@dp.callback_query(ContractForm.customer_kpp_choice, F.data.startswith("customer_kpp:"))
async def customer_kpp_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    choice = callback.data.split(":", maxsplit=1)[1]
    if choice == "auto":
        kpp = generate_digits(9)
        await state.update_data(customer_kpp=kpp)
        await callback.message.edit_text(f"КПП заказчика: {kpp} (сгенерирован)")
        await callback.message.answer("Тип исполнителя:", reply_markup=contractor_type_keyboard())
        await state.set_state(ContractForm.contractor_type)
    else:
        await callback.message.edit_text("КПП заказчика: выбран ручной ввод")
        await callback.message.answer("Введите КПП заказчика:")
        await state.set_state(ContractForm.customer_kpp_manual)


@dp.message(ContractForm.customer_kpp_manual)
async def customer_kpp_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(customer_kpp=message.text)
    await message.answer("Тип исполнителя:", reply_markup=contractor_type_keyboard())
    await state.set_state(ContractForm.contractor_type)


@dp.callback_query(ContractForm.contractor_type, F.data.startswith("contractor_type:"))
async def contractor_type_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    selected_map = {"ooo": "ООО", "ip": "ИП", "self": "Самозанятый"}
    selected_value = selected_map[callback.data.split(":", maxsplit=1)[1]]

    if selected_value != "ИП":
        await callback.message.edit_text(
            "Sorry, we currently cannot generate this type of contract. Please select another type.",
            reply_markup=contractor_type_keyboard(),
        )
        return

    await state.update_data(contractor_type=selected_value)
    await callback.message.edit_text(f"Тип исполнителя: {selected_value}")
    await callback.message.answer("Введите полное ФИО исполнителя (ИП):")
    await state.set_state(ContractForm.contractor_representative)


@dp.message(ContractForm.contractor_representative)
async def contractor_representative_handler(message: types.Message, state: FSMContext):
    full_name = (message.text or "").strip()
    if not full_name:
        await message.answer("Пожалуйста, введите полное ФИО исполнителя (ИП).")
        return

    parts = full_name.split()
    surname = parts[0] if parts else ""
    if surname:
        await state.update_data(contractor_company_name=f"ИП {surname}")

    await state.update_data(contractor_representative_name=full_name)
    await message.answer(
        "Как вы хотите заполнить юридические реквизиты исполнителя?",
        reply_markup=input_choice_keyboard(
            "contractor_requisites",
            "Ввести вручную",
            "Сгенерировать автоматически",
        ),
    )
    await state.set_state(ContractForm.contractor_requisites_choice)


@dp.callback_query(ContractForm.contractor_requisites_choice, F.data.startswith("contractor_requisites:"))
async def contractor_requisites_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    choice = callback.data.split(":", maxsplit=1)[1]
    if choice == "auto":
        data = await state.get_data()
        legal_type = data.get("contractor_type", "ИП")

        inn = generate_inn()
        ogrn = generate_ogrn(legal_type)
        bik = generate_digits(9)
        correspondent = generate_digits(20)
        settlement = generate_digits(20)

        await state.update_data(
            contractor_requisites_mode="auto",
            contractor_inn=inn,
            contractor_ogrn_or_ogrnip=ogrn,
            contractor_bik=bik,
            contractor_correspondent_account=correspondent,
            contractor_settlement_account=settlement,
        )
        await callback.message.edit_text("Реквизиты исполнителя будут сгенерированы автоматически.")
        await callback.message.answer("Теперь укажем юридический адрес и банк исполнителя.")
        await ask_contractor_address(callback.message, state)
    else:
        await state.update_data(contractor_requisites_mode="manual")
        await callback.message.edit_text("Реквизиты исполнителя: выбран ручной ввод.")
        await callback.message.answer("Введите ИНН исполнителя:")
        await state.set_state(ContractForm.contractor_inn_manual)


@dp.callback_query(ContractForm.contractor_inn_choice, F.data.startswith("contractor_inn:"))
async def contractor_inn_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
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


@dp.message(ContractForm.contractor_inn_manual)
async def contractor_inn_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(contractor_inn=message.text)
    await ask_contractor_ogrn(message, state)


@dp.callback_query(ContractForm.contractor_ogrn_choice, F.data.startswith("contractor_ogrn:"))
async def contractor_ogrn_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
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


@dp.message(ContractForm.contractor_ogrn_manual)
async def contractor_ogrn_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(contractor_ogrn_or_ogrnip=message.text)
    await ask_contractor_address(message, state)


@dp.message(ContractForm.contractor_address_choice, F.location)
async def contractor_address_location_handler(message: types.Message, state: FSMContext):
    loc = message.location
    formatted = await reverse_geocode_address(loc.latitude, loc.longitude)
    if formatted:
        await state.update_data(contractor_legal_address=formatted)
        await message.answer(
            f"Определён юридический адрес исполнителя: {formatted}",
            reply_markup=ReplyKeyboardRemove(),
        )
        await ask_contractor_bank(message, state)
    else:
        await message.answer(
            "Не удалось определить адрес по геолокации. Пожалуйста, введите юридический адрес исполнителя вручную.",
            reply_markup=ReplyKeyboardRemove(),
        )
        # Остаёмся в состоянии ContractForm.contractor_address_choice и ждём текстовый ввод


@dp.message(ContractForm.contractor_address_choice, F.text)
async def contractor_address_text_handler(message: types.Message, state: FSMContext):
    await state.update_data(contractor_legal_address=message.text)
    await message.answer(
        "Юридический адрес исполнителя сохранен.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await ask_contractor_bank(message, state)


@dp.message(ContractForm.contractor_address_manual)
async def contractor_address_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(contractor_legal_address=message.text)
    await ask_contractor_bank(message, state)


@dp.callback_query(ContractForm.contractor_bank_choice, F.data.startswith("contractor_bank:"))
async def contractor_bank_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    selected = callback.data.split(":", maxsplit=1)[1]
    data = await state.get_data()
    bank_map = {"t_bank": "Т-Банк", "sber": "Сбербанк", "alfa": "Альфа-Банк"}
    if selected == "manual":
        await callback.message.edit_text("Банк исполнителя: выбран ручной ввод")
        await callback.message.answer("Введите банк исполнителя:")
        await state.set_state(ContractForm.contractor_bank_manual)
    else:
        await state.update_data(contractor_bank=bank_map[selected])
        await callback.message.edit_text(f"Банк исполнителя: {bank_map[selected]}")
        # In auto requisites mode, all numeric fields are already generated;
        # proceed directly to city selection without asking BIK/corr/settlement.
        if data.get("contractor_requisites_mode") == "auto":
            await callback.message.answer("Отлично, персональные данные сторон сформированы.")
            await callback.message.answer("Остался один шаг. Выберите город.", reply_markup=city_keyboard())
            await state.set_state(ContractForm.city_choice)
        else:
            await ask_contractor_bik(callback.message, state)


@dp.message(ContractForm.contractor_bank_manual)
async def contractor_bank_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(contractor_bank=message.text)
    await ask_contractor_bik(message, state)


@dp.callback_query(ContractForm.contractor_bik_choice, F.data.startswith("contractor_bik:"))
async def contractor_bik_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
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


@dp.message(ContractForm.contractor_bik_manual)
async def contractor_bik_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(contractor_bik=message.text)
    await ask_contractor_corr(message, state)


@dp.callback_query(ContractForm.contractor_corr_choice, F.data.startswith("contractor_corr:"))
async def contractor_corr_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
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


@dp.message(ContractForm.contractor_corr_manual)
async def contractor_corr_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(contractor_correspondent_account=message.text)
    await ask_contractor_settlement(message, state)


@dp.callback_query(ContractForm.contractor_settlement_choice, F.data.startswith("contractor_settlement:"))
async def contractor_settlement_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    choice = callback.data.split(":", maxsplit=1)[1]
    if choice == "auto":
        value = generate_digits(20)
        await state.update_data(contractor_settlement_account=value)
        await callback.message.edit_text(f"р/с исполнителя: {value} (сгенерирован)")
        await callback.message.answer("Остался один шаг. Выберите город.", reply_markup=city_keyboard())
        await state.set_state(ContractForm.city_choice)
    else:
        await callback.message.edit_text("р/с исполнителя: выбран ручной ввод")
        await callback.message.answer("Введите р/с исполнителя:")
        await state.set_state(ContractForm.contractor_settlement_manual)


@dp.message(ContractForm.contractor_settlement_manual)
async def contractor_settlement_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(contractor_settlement_account=message.text)
    await message.answer("Остался один шаг. Выберите город.", reply_markup=city_keyboard())
    await state.set_state(ContractForm.city_choice)


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
        response = requests.post(
            BACKEND_URL,
            json=contract_payload,
            timeout=BACKEND_TIMEOUT_SECONDS,
        )
        if response.status_code == 200:
            backend_payload = response.json()
            output_file = backend_payload.get("output_file")
            generated_docx_path = GENERATED_DOCX_PATH
            if output_file:
                generated_docx_path = Path(__file__).resolve().with_name(output_file)

            if not generated_docx_path.exists():
                await message.answer(
                    "Договор сформирован, но не удалось найти итоговый DOCX файл для отправки."
                )
            else:
                generated_pdf_path = generated_docx_path.with_suffix(".pdf")
                shutil.copyfile(generated_docx_path, generated_pdf_path)

                await message.answer(
                    "Ваш договор готов! Можете скачать его из следующего сообщения"
                )
                await bot.send_media_group(
                    chat_id=message.chat.id,
                    media=[
                        InputMediaDocument(media=FSInputFile(str(generated_docx_path))),
                        InputMediaDocument(media=FSInputFile(str(generated_pdf_path))),
                    ],
                )
        else:
            await message.answer(f"Backend вернул ошибку: {response.status_code} {response.text}")
    except requests.exceptions.Timeout:
        await message.answer(
            "Backend не успел ответить вовремя. "
            "Увеличьте BACKEND_TIMEOUT_SECONDS или проверьте скорость ответа OpenAI."
        )
    except requests.exceptions.ConnectionError:
        await message.answer(
            "Не удалось подключиться к backend. "
            "Проверьте, что uvicorn запущен и доступен по адресу http://127.0.0.1:8000."
        )
    except requests.exceptions.RequestException as exc:
        await message.answer(f"Ошибка запроса к backend: {exc}")

    await state.clear()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
