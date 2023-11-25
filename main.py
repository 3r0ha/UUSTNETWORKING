import logging
import asyncio
import aiosqlite

from aiogram.dispatcher.filters import Text
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage



API_TOKEN = '6835315645:AAGPyEZKih_bTD7uj4N86_pWxKF73z8F0oc'
ADMIN_ID = 989037374


logging.basicConfig(level=logging.INFO)


bot = Bot(token=API_TOKEN)

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class Form(StatesGroup):
    name = State()
    faculty = State()
    group = State()
    about_me = State()
    interests = State()
    newname = State()
    newfaculty = State()
    newgroup = State()
    newabout_me = State()
    newinterests = State()
    photo = State()
    edit_name = State()
    edit_faculty = State()
    edit_group = State()
    edit_photo = State()


dp.middleware.setup(LoggingMiddleware())


async def init_db():
    db = await aiosqlite.connect('users.db')
    await db.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        name TEXT,
                        faculty TEXT,
                        group_number TEXT,
                        about_me TEXT,
                        interests TEXT,
                        photo_id TEXT)''')
    await db.commit()
    await db.close()


async def fetch_all_user_ids():
    async with aiosqlite.connect('users.db') as db:
        cursor = await db.execute("SELECT user_id FROM users")
        user_ids = await cursor.fetchall()
        return [user_id[0] for user_id in user_ids]


@dp.message_handler(commands=['post'], user_id = ADMIN_ID)

async def handle_broadcast_command(message: types.Message):
    broadcast_message = message.get_args()
    if not broadcast_message:
        await message.reply("Пожалуйста, введите сообщение для рассылки после команды.Например: /post Ваше сообщение здесь.")
        return

    user_ids = await fetch_all_user_ids()
    for user_id in user_ids:
        try:
            await bot.send_message(user_id, broadcast_message)
        except Exception as e:
            print(f"Could not send message to {user_id}: {e}")

# Функция для удаления данных пользователя
async def delete_user_data(user_id):
    async with aiosqlite.connect('users.db') as db:
        await db.execute("DELETE FROM users WHERE user_id =?", (user_id,))
        await db.commit()


@dp.message_handler(commands=['delete_me'])
async def confirm_delete_user_data(message: types.Message):
    keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("Удалить мои данные", callback_data ="confirm_delete"))
    await message.answer("Вы уверены, что хотите удалить все свои данные?", reply_markup = keyboard)


@dp.callback_query_handler(lambda c: c.data =='confirm_delete')
async def process_callback_button_delete(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    await bot.answer_callback_query(callback_query.id)
    await delete_user_data(user_id)
    await bot.send_message(user_id, "Ваши данные были удалены.")


                    # Обработчик команды /start
@dp.message_handler(commands='start', state='*')
async def cmd_start(message: types.Message, state: FSMContext):
    await init_db()
    db = await aiosqlite.connect('users.db')
    res = await db.execute(f'''SELECT * FROM users WHERE user_id = {message.from_user.id}''')
    res = await res.fetchall()
    print(res)
    if res == []:
        await Form.name.set()
        await message.reply("👋 Привет! Я - бот для поиска единомышленников. Давай заполним твою анкету. Для начала, как тебя зовут?")
    else:
        kb = [
            [types.KeyboardButton(text="👨‍💻 Мой профиль")],
            [types.KeyboardButton(text="👁 Смотреть анкеты")]
        ]
        keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
        await message.reply("Добро пожаловать! Воспользуйтесь кнопками ниже, чтобы посмотреть свой профиль или анкеты других пользователей",  reply_markup=keyboard)

@dp.message_handler(state=Form.name)
async def process_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
    await Form.next()
    await message.reply("Какой у тебя факультет?")


@dp.message_handler(state=Form.faculty)
async def process_faculty(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['faculty'] = message.text
    await Form.next()
    await message.reply("В какой группе ты учишься?")

@dp.message_handler(state=Form.group)
async def process_faculty(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['group'] = message.text
    await Form.next()
    await message.reply("Расскажи о себе. Пользователи будут видеть информацию в твоей анкете.")

@dp.message_handler(state=Form.about_me)
async def process_faculty(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['about_me'] = message.text
    await Form.next()
    await message.reply("Перечисли свои интересы, они должны идти через запятую. (Например: программирование, C++, backend)")


@dp.message_handler(state=Form.interests)
async def process_group(message: types.Message, state: FSMContext):
    interests_lower = message.text.lower()
    async with state.proxy() as data:
        data['interests'] = interests_lower
    await Form.photo.set()
    await message.reply("Загрузи своё фото", reply = False)


@dp.message_handler(content_types=['photo'], state=Form.photo)
async def process_photo(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['photo'] = message.photo[0].file_id
        db = await aiosqlite.connect('users.db')
        await db.execute('INSERT INTO users (user_id, username, name, faculty, group_number, about_me, interests, photo_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                         (message.from_user.id, message.from_user.username, data['name'], data['faculty'], data['group'],data['about_me'],data['interests'],data['photo']))
        await db.commit()
        await db.close()

    await state.finish()
    kb = [
        [types.KeyboardButton(text="👨‍💻 Мой профиль")],
        [types.KeyboardButton(text="👁 Смотреть анкеты")]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer("Спасибо за регистрацию! Воспользуйтесь кнопками ниже, чтобы посмотреть свой профиль или анкеты других пользователей", reply_markup=keyboard)

# Получение данных пользователя из БД
async def get_user_data(user_id):
    db = await aiosqlite.connect('users.db')
    cursor = await db.execute('SELECT name, faculty, group_number, photo_id FROM users WHERE user_id = ?', (user_id,))
    row = await cursor.fetchone()
    await cursor.close()
    await db.close()
    return row

# Обработчик команды /profile
@dp.message_handler(text='👨‍💻 Мой профиль')
async def cmd_profile(message: types.Message):
    user_id = message.from_user.id
    user_data = await get_user_data(user_id)
    if user_data:
        name, faculty, group, about_me, photo_id = user_data
        await bot.send_photo(chat_id=message.chat.id, photo=photo_id, caption=f"👨‍💻 Ваш профиль\n\nИмя: {name}\nФакультет: {faculty}\nГруппа: {group}\nО себе: {about_me}\n\n🛠 Для редактирования профиля воспользуйтесь командами:\n\n/edit_name - изменить имя\n/edit_faculty - изменить факультет\n/edit_group - изменить группу\n/edit_about - изменить информацию о себе\n/edit_interests - изменить интересы\n\n🗑 Если вы хотите удалить свою анкету - используйте команду /delete_me")
    else:
        await message.reply("Вы еще не зарегистрировались. Пожалуйста, нажмите /start и пройдите регистрацию")


async def get_user_data(user_id):
    db = await aiosqlite.connect('users.db')
    cursor = await db.execute('SELECT name, faculty, group_number, about_me, photo_id FROM users WHERE user_id = ?', (user_id,))
    row = await cursor.fetchone()
    await cursor.close()
    await db.close()
    return row


async def get_users_for_search(current_user_id):
    db = await aiosqlite.connect('users.db')
    current_user_interests_query = 'SELECT interests FROM users WHERE user_id = ?'
    cursor = await db.execute(current_user_interests_query, (current_user_id,))
    current_user_interests_row = await cursor.fetchone()
    if current_user_interests_row:
        current_user_interests = current_user_interests_row[0]
    else:
        current_user_interests = ''
    if not current_user_interests:
        matching_users_query = 'SELECT user_id, username, name, faculty, group_number, about_me, interests, photo_id FROM users WHERE 1 = 0'
    else:
        interests_parts = ["interests LIKE '%{}%'".format(interest.strip()) for interest in current_user_interests.split(',')]

        interests_query_part = " OR ".join(interests_parts)

        matching_users_query = f"SELECT user_id, username, name, faculty, group_number, about_me, interests, photo_id FROM users WHERE user_id != ? AND ({interests_query_part})"

    cursor = await db.execute(matching_users_query, (current_user_id,))
    rows = await cursor.fetchall()
    await cursor.close()
    await db.close()
    return rows


@dp.message_handler(text='👁 Смотреть анкеты')
async def cmd_search(message: types.Message):
    user_id = message.from_user.id
    users = await get_users_for_search(user_id)
    if users:
        for user in users:
            user_id, username, name, faculty, group, about_me, interests, photo_id = user
            await bot.send_photo(chat_id=message.chat.id, photo=photo_id, caption=f"Имя: {name}\nФакультет: {faculty}\nГруппа: {group}\nО себе: {about_me}\nИнтересы:{interests}\n\nЕго аккаунт Telegram: @{username}")
    else:
        await message.reply("Пользователи не найдены. Скорее всего, нет пользователей с интересами, как у вас 😔")
async def update_user_data(user_id, column, data):
    async with aiosqlite.connect('users.db') as db:
        query = f"UPDATE users SET {column} = ? WHERE user_id = ?"
        await db.execute(query, (data, user_id))
        await db.commit()

@dp.message_handler(commands=['edit_name'], state='*')
async def prompt_name(message: types.Message):
    await Form.newname.set()
    await bot.send_message(message.from_user.id, "Пожалуйста, введите ваше новое имя:")

@dp.message_handler(state=Form.newname)
async def update_name(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    new_name = message.text
    await update_user_data(user_id, "name", new_name)
    await bot.send_message(message.from_user.id, "Ваше имя обновлено!")
    await state.finish()
@dp.message_handler(commands=['edit_faculty'], state='*')
async def prompt_faculty(message: types.Message):
    await Form.newfaculty.set()
    await bot.send_message(message.from_user.id, "Пожалуйста, введите ваш новый факультет:")

@dp.message_handler(state=Form.newfaculty)
async def update_faculty(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    new_faculty = message.text
    await update_user_data(user_id, "faculty", new_faculty)
    await bot.send_message(message.from_user.id, "Ваш факультет обновлен!")
    await state.finish()
@dp.message_handler(commands=['edit_group'], state='*')
async def prompt_group(message: types.Message):
    await Form.newgroup.set()
    await bot.send_message(message.from_user.id, "Пожалуйста, введите вашу новую группу:")

@dp.message_handler(state=Form.newgroup)
async def update_group(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    new_group = message.text
    await update_user_data(user_id, "group_number", new_group)
    await bot.send_message(message.from_user.id, "Ваша группа обновлена!")
    await state.finish()
@dp.message_handler(commands=['edit_about'], state='*')
async def prompt_about(message: types.Message):
    await Form.newabout_me.set()
    await bot.send_message(message.from_user.id, "Пожалуйста, введите ваше новое описание:")

@dp.message_handler(state=Form.newabout_me)
async def update_about(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    new_about_me = message.text
    await update_user_data(user_id, "about_me", new_about_me)
    await bot.send_message(message.from_user.id, "Ваше описание обновлено!")
    await state.finish()
@dp.message_handler(commands=['edit_interests'], state='*')
async def prompt_interests(message: types.Message):
    await Form.newinterests.set()
    await bot.send_message(message.from_user.id, "Пожалуйста, введите ваши интересы через запятую:")

@dp.message_handler(state=Form.newinterests)
async def update_interests(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    new_interests_lower = message.text.lower()
    await update_user_data(user_id, "interests", new_interests_lower)
    await bot.send_message(message.from_user.id, "Ваши интересы обновлены!")
    await state.finish()

@dp.message_handler(content_types=types.ContentTypes.TEXT, state="*")
async def message_unrecognized(message: types.Message):
    await message.reply("Я не понимаю тебя. Пожалуйста, воспользуйся кнопками или нажми /start")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
    