import datetime
from functools import cache
from pathlib import Path
from typing import Annotated, Sequence

from jinja2 import Environment, FileSystemLoader, Template

from trackyai.agent.tools.base import SendTextMessage, TgAction
from trackyai.agent.tools.registry import tool
from trackyai.db import Category, EnvironmentConfiguration, Expense, service_manager


class _UpdateMemory(TgAction):
    def __init__(self, mem: str):
        self.mem = mem

    async def perform(self, user_id: int) -> None:
        await service_manager.memory.update(user_id=user_id, memory=self.mem)


_jinja_env = Environment(loader=FileSystemLoader(searchpath=Path(__file__).parent / 'message_templates'))


@cache
def _load_template(template_name: str) -> Template:
    return _jinja_env.get_template(template_name + '.jinja2')


@tool(terminating=True, scopes='memory')
async def update_memory(new_memory: Annotated[str, 'A new memory to save instead of the previous one']) -> TgAction:
    """
    Updates system memory about the current user with the new memory.
    Note that the new memory replaces the previous one; so any useful details from the previous memory should be
    preserved.
    """
    return _UpdateMemory(new_memory)


@tool(terminating=True)
async def add_category(
    name: Annotated[str, 'The name of the new category. Must differ from existing categories.'],
    description: Annotated[
        str, 'The description of the new category. Should reflect what this category is used for, with some examples.'
    ],
) -> SendTextMessage:
    """Adds a new category to the system. This new category must have a unique name."""
    category: Category = await service_manager.category.add(name=name, description=description)
    message_template = _load_template('add_category')
    return SendTextMessage(text=message_template.render(category=category))


@tool(terminating=True)
async def update_category(
    category_id: Annotated[int, 'The ID of the category to be updated.'],
    new_name: Annotated[str, 'The new name of the category. If name is not updated - must be the current name.'],
    new_description: Annotated[
        str, 'The new description of the category. If description is not updated - must be the current description.'
    ],
) -> SendTextMessage:
    """Updates an existing category with the new name and description."""
    category: Category = await service_manager.category.update(
        category_id=category_id, name=new_name, description=new_description
    )
    message_template = _load_template('update_category')
    return SendTextMessage(text=message_template.render(category=category))


@tool(terminating=True)
async def update_environment_config(
    key: Annotated[str, 'Key of an environment configuration to be updated. Must be present.'],
    value: Annotated[str, 'New value of the environment configuration for the given key.'],
) -> SendTextMessage:
    """Updates an existing environment configuration with the new value for the given key."""
    ec: EnvironmentConfiguration = await service_manager.env_config.update(key=key, value=value)
    message_template = _load_template('update_environment_config')
    return SendTextMessage(text=message_template.render(ec=ec))


@tool(terminating=True)
async def add_expense(
    category_id: Annotated[int, 'The ID of the category for the new expense.'],
    currency: Annotated[str, 'The currency of the expense. If not provided, the default value must be used.'],
    amount: Annotated[float, 'The amount of the expense. Must be greater than or equal to 0.'],
    comment: Annotated[str, 'An optional comment to the expense.'],
) -> SendTextMessage:
    """Adds a new expense to the system. This new expense must correspond to an existing category."""
    expense: Expense = await service_manager.expense.add(
        category_id=category_id, currency=currency, amount=amount, comment=comment
    )
    message_template = _load_template('add_expense')
    return SendTextMessage(text=message_template.render(expense=expense))


@tool(terminating=True)
async def update_expense(
    expense_id: Annotated[int, 'The ID of the expense to be updated.'],
    category_id: Annotated[
        int,
        (
            'The ID of the category for the expense. Must be present. '
            'Must equal to the current one if it is not changing by user request.'
        ),
    ],
    date: Annotated[
        datetime.datetime,
        'The new datetime of the expense. Must equal to the current one if it is not changing by user request.',
    ],
    currency: Annotated[
        str, 'The new currency of the expense. Must equal to the current one if it is not changing by user request.'
    ],
    amount: Annotated[
        float,
        (
            'The new amount of the expense. Must be greater than or equal to 0. '
            'Must equal to the current one if it is not changing by user request.'
        ),
    ],
    comment: Annotated[
        str, 'The new comment of the expense. Must equal to the current one if it is not changing by user request.'
    ],
) -> SendTextMessage:
    """
    Updates an existing expense by id. Characteristics that are not changing must be provided as well;
    they must equal to their current values.
    """
    expense: Expense = await service_manager.expense.update(
        expense_id=expense_id, category_id=category_id, date=date, currency=currency, amount=amount, comment=comment
    )
    message_template = _load_template('update_expense')
    return SendTextMessage(text=message_template.render(expense=expense))


@tool(terminating=True)
async def send_categories() -> SendTextMessage:
    """Sends a list of all available categories to the user."""
    categories: Sequence[Category] = await service_manager.category.get_all()
    message_template = _load_template('send_categories')
    return SendTextMessage(text=message_template.render(categories=categories))


@tool(terminating=True)
async def send_system_configurations() -> SendTextMessage:
    """Sends a list of all current system configurations to the user."""
    ecs: Sequence[EnvironmentConfiguration] = await service_manager.env_config.get_all()
    message_template = _load_template('send_system_configurations')
    return SendTextMessage(text=message_template.render(ecs=ecs))


@tool(terminating=True)
async def send_expense_single(
    expense_id: Annotated[int, 'The ID of the expense to send to the user.'],
) -> SendTextMessage:
    """Sends a single expense to the user (whole information about this expense)."""
    expense: Expense = await service_manager.expense.get(expense_id=expense_id)
    message_template = _load_template('send_expense_single')
    return SendTextMessage(text=message_template.render(expense=expense))


@tool(terminating=True)
async def send_expenses_list(
    expense_ids: Annotated[list[int], 'The list of IDs (integers) of the expenses to send to the user.'],
) -> SendTextMessage:
    """Sends multiple expenses to the user (whole information about expenses)."""
    expenses: Sequence[Expense] = await service_manager.expense.get_many(expense_ids=expense_ids)
    message_template = _load_template('send_expenses')
    return SendTextMessage(text=message_template.render(expenses=expenses))


@tool
async def list_categories() -> str:
    """Loads the list of all available expense categories."""
    categories: Sequence[Category] = await service_manager.category.get_all()
    template = _load_template('list_categories')
    return template.render(categories=categories)


@tool
async def list_environment_configurations() -> str:
    """Loads the list of all environment configurations for the current user."""
    ecs: Sequence[EnvironmentConfiguration] = await service_manager.env_config.get_all()
    template = _load_template('list_environment_configurations')
    return template.render(ecs=ecs)


@tool
async def find_expenses(
    category_id: Annotated[int, ('The ID of the category for the expenses. ')],
    date_from: Annotated[datetime.datetime, 'The datetime from which to find expenses.'],
    date_to: Annotated[datetime.datetime, 'The datetime until which to find expenses.'],
    currency: Annotated[str, 'The currency of expenses to find.'],
    amount_from: Annotated[float, ('The amount from which to find expenses.')],
    amount_to: Annotated[float, ('The amount to which to find expenses.')],
    limit: Annotated[int, 'Limit - maximum number of expenses to find. Put a bigger value if you want to find all.'],
) -> str:
    """Finds a list of expenses in the database according to given filters."""
    expenses: Sequence[Expense] = await service_manager.expense.find(
        category_id=category_id,
        date_from=date_from,
        date_to=date_to,
        currency=currency,
        amount_from=amount_from,
        amount_to=amount_to,
        limit=limit,
    )
    template = _load_template('list_expenses')
    return template.render(expenses=expenses)
