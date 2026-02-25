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
    customer_bank_choice = State()
    customer_bank_custom = State()
    contractor_type = State()
    contractor_company = State()
    contractor_representative = State()
    project_description = State()


def generate_contract_number() -> str:
    return f"{datetime.date.today().year}-{random.randint(1000, 9999)}"


def generate_inn() -> str:
    return str(random.randint(10**9, 10**10 - 1))


def city_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Москва", callback_data="city:moscow")],
            [InlineKeyboardButton(text="Другой город", callback_data="city:other")],
        ]
    )


def customer_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="ООО", callback_data="customer_type:ooo")],
            [InlineKeyboardButton(text="ИП", callback_data="customer_type:ip")],
            [InlineKeyboardButton(text="Самозанятый", callback_data="customer_type:self")],
        ]
    )


def customer_inn_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Ввести свой ИНН", callback_data="customer_inn:manual")],
            [InlineKeyboardButton(text="Сгенерировать ИНН", callback_data="customer_inn:auto")],
        ]
    )


def customer_bank_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Т-Банк", callback_data="customer_bank:t_bank")],
            [InlineKeyboardButton(text="Сбербанк", callback_data="customer_bank:sber")],
            [InlineKeyboardButton(text="Альфа-Банк", callback_data="customer_bank:alfa")],
            [InlineKeyboardButton(text="Другой", callback_data="customer_bank:other")],
        ]
    )


def contractor_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="ИП", callback_data="contractor_type:ip")],
            [InlineKeyboardButton(text="Самозанятый", callback_data="contractor_type:self")],
        ]
    )


@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Выберите город:", reply_markup=city_keyboard())
    await state.set_state(ContractForm.city_choice)


@dp.callback_query(ContractForm.city_choice, F.data.startswith("city:"))
async def city_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split(":", maxsplit=1)[1]

    if choice == "moscow":
        await state.update_data(city="Москва")
        await callback.message.edit_text("Город: Москва")
        await callback.message.answer("Тип заказчика:", reply_markup=customer_type_keyboard())
        await state.set_state(ContractForm.customer_type)
    else:
        await callback.message.edit_text("Город: выбран ручной ввод")
        await callback.message.answer("Введите название города:")
        await state.set_state(ContractForm.city_custom)

    await callback.answer()


@dp.message(ContractForm.city_custom)
async def city_custom_handler(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("Тип заказчика:", reply_markup=customer_type_keyboard())
    await state.set_state(ContractForm.customer_type)

def legal_type_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="ООО", callback_data=f"{prefix}:ooo")],
            [InlineKeyboardButton(text="ИП", callback_data=f"{prefix}:ip")],
            [InlineKeyboardButton(text="Самозанятый", callback_data=f"{prefix}:self")],
        ]
    )


def customer_inn_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Ввести свой ИНН", callback_data="customer_inn:manual")],
            [InlineKeyboardButton(text="Сгенерировать ИНН", callback_data="customer_inn:auto")],
        ]
    )


def customer_bank_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Т-Банк", callback_data="customer_bank:t_bank")],
            [InlineKeyboardButton(text="Сбербанк", callback_data="customer_bank:sber")],
            [InlineKeyboardButton(text="Альфа-Банк", callback_data="customer_bank:alfa")],
            [InlineKeyboardButton(text="Другой", callback_data="customer_bank:other")],
        ]
    )


@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Тип заказчика:",
        reply_markup=legal_type_keyboard("customer_type"),
    )
    await state.set_state(ContractForm.customer_type)


@dp.callback_query(ContractForm.customer_type, F.data.startswith("customer_type:"))
async def customer_type_handler(callback: types.CallbackQuery, state: FSMContext):
    selected_map = {
        "ooo": "ООО",
        "ip": "ИП",
        "self": "Самозанятый",
    }
    selected_key = callback.data.split(":", maxsplit=1)[1]
    selected_value = selected_map[selected_key]

    await state.update_data(customer_type=selected_value)
    await callback.message.edit_text(f"Тип заказчика: {selected_value}")
    await callback.message.answer(
        "Введите название компании заказчика или напишите 'LLM', чтобы сгенерировать."
    )
    await callback.answer()
    await state.set_state(ContractForm.customer_company)


@dp.message(ContractForm.customer_company)
async def customer_company_handler(message: types.Message, state: FSMContext):
    company_name = "Компания, сгенерированная LLM" if message.text.lower() == "llm" else message.text
    await state.update_data(customer_company_name=company_name)

    await message.answer("Введите ФИО представителя заказчика:")
    await state.set_state(ContractForm.customer_representative)


@dp.message(ContractForm.customer_representative)
async def customer_representative_handler(message: types.Message, state: FSMContext):
    await state.update_data(customer_representative_name=message.text)
    await message.answer("ИНН заказчика:", reply_markup=customer_inn_keyboard())
    await state.set_state(ContractForm.customer_inn_choice)


@dp.callback_query(ContractForm.customer_inn_choice, F.data.startswith("customer_inn:"))
async def customer_inn_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split(":", maxsplit=1)[1]



@dp.callback_query(ContractForm.customer_inn_choice, F.data.startswith("customer_inn:"))
async def customer_inn_choice_handler(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split(":", maxsplit=1)[1]

    if choice == "auto":
        inn = generate_inn()
        await state.update_data(customer_inn=inn)
        await callback.message.edit_text(f"ИНН заказчика: {inn} (сгенерирован)")
        await callback.message.answer("Выберите банк заказчика:", reply_markup=customer_bank_keyboard())
        await state.set_state(ContractForm.customer_bank_choice)
    else:
        await callback.message.edit_text("ИНН заказчика: выбран ручной ввод")
        await callback.message.answer("Введите ИНН заказчика:")
        await state.set_state(ContractForm.customer_inn_manual)

    await callback.answer()


@dp.message(ContractForm.customer_inn_manual)
async def customer_inn_manual_handler(message: types.Message, state: FSMContext):
    await state.update_data(customer_inn=message.text)
    await message.answer("Выберите банк заказчика:", reply_markup=customer_bank_keyboard())
    await state.set_state(ContractForm.customer_bank_choice)


@dp.callback_query(ContractForm.customer_bank_choice, F.data.startswith("customer_bank:"))
async def customer_bank_handler(callback: types.CallbackQuery, state: FSMContext):
    selected_key = callback.data.split(":", maxsplit=1)[1]
    bank_map = {
        "t_bank": "Т-Банк",
        "sber": "Сбербанк",
        "alfa": "Альфа-Банк",
    }

    if selected_key == "other":
        await callback.message.edit_text("Банк заказчика: выбран вариант 'Другой'")
        await callback.message.answer("Введите название банка заказчика:")
        await state.set_state(ContractForm.customer_bank_custom)
    else:
        selected_bank = bank_map[selected_key]
        await state.update_data(customer_bank=selected_bank)
        await callback.message.edit_text(f"Банк заказчика: {selected_bank}")
        await callback.message.answer("Тип исполнителя:", reply_markup=contractor_type_keyboard())
        await state.set_state(ContractForm.contractor_type)

    await callback.answer()


@dp.message(ContractForm.customer_bank_custom)
async def customer_bank_custom_handler(message: types.Message, state: FSMContext):
    await state.update_data(customer_bank=message.text)
    await message.answer("Тип исполнителя:", reply_markup=contractor_type_keyboard())
    await state.set_state(ContractForm.contractor_type)

@dp.callback_query(ContractForm.customer_bank_choice, F.data.startswith("customer_bank:"))
async def customer_bank_handler(callback: types.CallbackQuery, state: FSMContext):
    selected_key = callback.data.split(":", maxsplit=1)[1]
    bank_map = {
        "t_bank": "Т-Банк",
        "sber": "Сбербанк",
        "alfa": "Альфа-Банк",
    }

    if selected_key == "other":
        await callback.message.edit_text("Банк заказчика: выбран вариант 'Другой'")
        await callback.message.answer("Введите название банка заказчика:")
        await state.set_state(ContractForm.customer_bank_custom)
    else:
        selected_bank = bank_map[selected_key]
        await state.update_data(customer_bank=selected_bank)
        await callback.message.edit_text(f"Банк заказчика: {selected_bank}")
        await callback.message.answer(
            "Тип исполнителя:",
            reply_markup=legal_type_keyboard("contractor_type"),
        )
        await state.set_state(ContractForm.contractor_type)

@dp.callback_query(ContractForm.contractor_type, F.data.startswith("contractor_type:"))
async def contractor_type_handler(callback: types.CallbackQuery, state: FSMContext):
    selected_map = {
        "ip": "ИП",
        "self": "Самозанятый",
    }
    selected_key = callback.data.split(":", maxsplit=1)[1]
    selected_value = selected_map[selected_key]

    await state.update_data(contractor_type=selected_value)
    await callback.message.edit_text(f"Тип исполнителя: {selected_value}")

    if selected_key == "ip":
        await callback.message.answer("Введите название ИП (Фамилию). Например: “ИП Акимов”")
    else:
        await callback.message.answer("Введите ФИО полностью")

    await callback.answer()


@dp.message(ContractForm.customer_bank_custom)
async def customer_bank_custom_handler(message: types.Message, state: FSMContext):
    await state.update_data(customer_bank=message.text)
    await message.answer(
        "Тип исполнителя:",
        reply_markup=legal_type_keyboard("contractor_type"),
    )
    await state.set_state(ContractForm.contractor_type)


@dp.callback_query(ContractForm.contractor_type, F.data.startswith("contractor_type:"))
async def contractor_type_handler(callback: types.CallbackQuery, state: FSMContext):
    selected_map = {
        "ooo": "ООО",
        "ip": "ИП",
        "self": "Самозанятый",
    }
    selected_key = callback.data.split(":", maxsplit=1)[1]
    selected_value = selected_map[selected_key]

    await state.update_data(contractor_type=selected_value)
    await callback.message.edit_text(f"Тип исполнителя: {selected_value}")
    await callback.message.answer(
        "Введите название компании исполнителя или напишите 'LLM', чтобы сгенерировать."
    )
    await callback.answer()
    await state.set_state(ContractForm.contractor_company)


@dp.message(ContractForm.contractor_company)
async def contractor_company_handler(message: types.Message, state: FSMContext):
    company_name = "Исполнитель, сгенерированный LLM" if message.text.lower() == "llm" else message.text
    await state.update_data(contractor_company_name=company_name)

    await message.answer("Введите ФИО представителя исполнителя:")
    await state.set_state(ContractForm.contractor_representative)


@dp.message(ContractForm.contractor_representative)
async def contractor_representative_handler(message: types.Message, state: FSMContext):
    await state.update_data(contractor_representative_name=message.text)
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
        "city": "Не указан",
        "contract_day": str(today.day),
        "contract_month": today.strftime("%m"),
        "contract_year": str(today.year),
        "customer_company_name": data.get("customer_company_name") or "Не указано",
        "customer_representative_name": data.get("customer_representative_name") or "Не указано",
        "customer_representative_basis": "Устава",
        "customer_inn": data.get("customer_inn") or "Не указано",
        "customer_ogrn_or_ogrnip": "Не указано",
        "customer_legal_address": "Не указано",
        "customer_bank": data.get("customer_bank") or "Не указано",
        "customer_bik": "Не указано",
        "customer_correspondent_account": "Не указано",
        "customer_settlement_account": "Не указано",
        "contractor_type": data.get("contractor_type") or "ИП",
        "contractor_company_name": data.get("contractor_company_name") or "Не указано",
        "contractor_representative_name": data.get("contractor_representative_name") or "Не указано",
        "contractor_representative_basis": "Устава",
        "contractor_inn": "Не указано",
        "contractor_ogrn_or_ogrnip": "Не указано",
        "contractor_legal_address": "Не указано",
        "contractor_bank": "Не указано",
        "contractor_bik": "Не указано",
        "contractor_correspondent_account": "Не указано",
        "contractor_settlement_account": "Не указано",
        "vat_type": "Без НДС",
        "date": str(datetime.date.today()),
        "customer": {
            "type": data.get("customer_type"),
            "company_name": data.get("customer_company_name"),
            "representative_name": data.get("customer_representative_name"),
            "inn": data.get("customer_inn"),
            "bank": data.get("customer_bank"),
        },
        "contractor": {
            "type": data.get("contractor_type"),
            "company_name": data.get("contractor_company_name"),
            "representative_name": data.get("contractor_representative_name"),
        },
        "project_description": data.get("project_description"),
    }

    print(json.dumps(contract_payload, indent=4, ensure_ascii=False))

    try:
        response = requests.post(BACKEND_URL, json=contract_payload, timeout=5)
        if response.status_code == 200:
            await message.answer("Данные успешно сохранены и отправлены на backend.")
        else:
            await message.answer(f"Backend вернул ошибку: {response.status_code} {response.text}")
            await message.answer(f"Backend вернул ошибку: {response.status_code}")
    except Exception:
        await message.answer("Backend недоступен. Попробуйте позже.")

    await state.clear()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
