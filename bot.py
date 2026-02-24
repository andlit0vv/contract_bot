import asyncio
import random
import datetime
import requests

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

API_TOKEN = "8698344682:AAGjNOJcbbMVcTWMHy2HyPg42j_k8ExGF1w"
BACKEND_URL = "http://127.0.0.1:8000/save-contract"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()


# ---------------- STATES ----------------

class ContractForm(StatesGroup):
    customer_type = State()
    customer_company = State()
    customer_representative = State()
    customer_inn = State()
    customer_bank = State()
    contractor_type = State()
    contractor_company = State()
    contractor_representative = State()
    finish = State()


# ---------------- HELPERS ----------------

def generate_contract_number():
    return f"{datetime.date.today().year}-{random.randint(1000,9999)}"


def generate_inn():
    return str(random.randint(10**9, 10**10 - 1))


# ---------------- START ----------------

@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):

    await state.clear()

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="ООО")],
            [KeyboardButton(text="ИП")],
            [KeyboardButton(text="Самозанятый")]
        ],
        resize_keyboard=True
    )

    await message.answer("Тип заказчика:", reply_markup=keyboard)
    await state.set_state(ContractForm.customer_type)


# ---------------- CUSTOMER ----------------

@dp.message(ContractForm.customer_type)
async def customer_type_handler(message: types.Message, state: FSMContext):
    await state.update_data(customer_type=message.text)

    await message.answer(
        "Введите название компании заказчика "
        "или напишите 'LLM', чтобы сгенерировать."
    )

    await state.set_state(ContractForm.customer_company)


@dp.message(ContractForm.customer_company)
async def customer_company_handler(message: types.Message, state: FSMContext):

    if message.text.lower() == "llm":
        company_name = "Компания, сгенерированная LLM"
    else:
        company_name = message.text

    await state.update_data(customer_company_name=company_name)

    await message.answer("Введите ФИО представителя заказчика:")
    await state.set_state(ContractForm.customer_representative)


@dp.message(ContractForm.customer_representative)
async def customer_rep_handler(message: types.Message, state: FSMContext):
    await state.update_data(customer_representative_name=message.text)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Ввести свой ИНН")],
            [KeyboardButton(text="Сгенерировать ИНН")]
        ],
        resize_keyboard=True
    )

    await message.answer("ИНН заказчика:", reply_markup=keyboard)
    await state.set_state(ContractForm.customer_inn)


@dp.message(ContractForm.customer_inn)
async def customer_inn_handler(message: types.Message, state: FSMContext):

    if "Сгенерировать" in message.text:
        inn = generate_inn()
    else:
        await message.answer("Введите ИНН:")
        return

    await state.update_data(customer_inn=inn)

    await message.answer("Введите банк заказчика или 'Другой':")
    await state.set_state(ContractForm.customer_bank)


@dp.message(ContractForm.customer_bank)
async def customer_bank_handler(message: types.Message, state: FSMContext):

    await state.update_data(customer_bank=message.text)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="ООО")],
            [KeyboardButton(text="ИП")],
            [KeyboardButton(text="Самозанятый")]
        ],
        resize_keyboard=True
    )

    await message.answer("Тип исполнителя:", reply_markup=keyboard)
    await state.set_state(ContractForm.contractor_type)


# ---------------- CONTRACTOR ----------------

@dp.message(ContractForm.contractor_type)
async def contractor_type_handler(message: types.Message, state: FSMContext):
    await state.update_data(contractor_type=message.text)

    await message.answer(
        "Введите название компании исполнителя "
        "или напишите 'LLM', чтобы сгенерировать."
    )

    await state.set_state(ContractForm.contractor_company)


@dp.message(ContractForm.contractor_company)
async def contractor_company_handler(message: types.Message, state: FSMContext):

    if message.text.lower() == "llm":
        company_name = "Исполнитель, сгенерированный LLM"
    else:
        company_name = message.text

    await state.update_data(contractor_company_name=company_name)

    await message.answer("Введите ФИО представителя исполнителя:")
    await state.set_state(ContractForm.contractor_representative)


@dp.message(ContractForm.contractor_representative)
async def contractor_rep_handler(message: types.Message, state: FSMContext):

    await state.update_data(contractor_representative_name=message.text)

    # ------------ FINAL STEP ------------

    data = await state.get_data()

    contract_payload = {
        "contract_number": generate_contract_number(),
        "date": str(datetime.date.today()),
        **data
    }

    try:
        response = requests.post(
            BACKEND_URL,
            json={"data": contract_payload},
            timeout=5
        )

        if response.status_code == 200:
            await message.answer("Данные успешно отправлены на backend.")
        else:
            await message.answer("Ошибка backend.")

    except Exception:
        await message.answer("Backend недоступен.")

    await state.clear()


# ---------------- RUN ----------------

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
