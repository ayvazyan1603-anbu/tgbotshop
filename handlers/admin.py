"""
Админ-команды.
/testbalance  — временно выдаёт бесконечный баланс (только для ADMIN_ID).
               Реальный баланс в БД НЕ меняется — работает через FSM-флаг.
/addbalance <сумма> — зачислить реальные рубли на свой счёт (для теста пополнений).
"""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from database import repo

logger = logging.getLogger(__name__)
router = Router()

# Ключ в FSM-данных, который включает «бесконечный» режим
INFINITE_BALANCE_KEY = "infinite_balance"


@router.message(Command("testbalance"))
async def cmd_test_balance(message: Message, state: FSMContext) -> None:
    """Включает/выключает бесконечный баланс для текущего пользователя (только admin)."""
    if message.from_user.id != config.admin_id:
        return  # молча игнорируем

    data = await state.get_data()
    current = data.get(INFINITE_BALANCE_KEY, False)
    new_val = not current
    await state.update_data(**{INFINITE_BALANCE_KEY: new_val})

    if new_val:
        await message.answer(
            "✅ <b>Бесконечный баланс ВКЛЮЧЁН</b>\n\n"
            "Теперь ты можешь покупать любые товары без списания средств.\n"
            "Реальный баланс в БД не изменится.\n\n"
            "Повтори /testbalance чтобы выключить.",
            
        )
    else:
        await message.answer(
            "🔴 <b>Бесконечный баланс ВЫКЛЮЧЕН</b>\n\n"
            "Теперь работает обычный режим с реальным балансом.",
            
        )


@router.message(Command("addbalance"))
async def cmd_add_balance(message: Message, session: AsyncSession) -> None:
    """Зачисляет рубли на баланс — только для admin, для тестирования пополнений."""
    if message.from_user.id != config.admin_id:
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /addbalance 1000")
        return
    try:
        amount = float(parts[1])
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Укажи корректную сумму. Пример: /addbalance 500")
        return

    from services.payment_service import credit_balance
    new_balance = await credit_balance(
        session=session,
        user_id=message.from_user.id,
        amount=amount,
        description=f"Тестовое пополнение +{amount:.0f} руб.",
    )
    await message.answer(
        f"✅ Зачислено <b>+{amount:.0f} руб.</b>\n"
        f"Текущий баланс: <b>{new_balance:.2f} руб.</b>"
    )
