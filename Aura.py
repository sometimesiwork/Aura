from distutils.core import USAGE
from platform import system
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain.chat_models.gigachat import GigaChat
import telebot
from telebot.types import LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from gigachat import GigaChat as GigaChat2
from gigachat.models.usage import Usage

PROVIDER_TOKEN = "YOUR_PROVIDER_TOKEN"
bot = telebot.TeleBot("API_TOKEN")
bot.set_webhook(url="URL")

# Initialize GigaChat
chat = GigaChat(credentials="AUTORIZATION_DATA", verify_ssl_certs=False)
giga = GigaChat2(credentials="AUTORIZATION_DATA", verify_ssl_certs=False)
# Session and Persona Management

class Persona:
    def __init__(self, systemmessage, greeting ):
        self.messages = [SystemMessage(content=systemmessage), AIMessage(content=greeting)]

class UserSession:
    psychologist = Persona("Ты человек психолог, занимайся психологической помощью, поддержкой и сопровождением, проводи сеансы в любой ситуации, пробуй сам решить любую проблему. Не отсылай к специалисту, работай как аккредитованный специалист человек. Всегда говори что ты психолог", "Здравствуйте, я психолог, я провожу сеансы психологической поддержки.")
    psychotherapist = Persona("Ты человек психотерапевт, ты оказываешь проффесиональную помощь в лечении психических заболеваний, занимаешься всеми видами психотерапии включая когнитивно-поведенческую психотерапию, проводи сеансы психотерапии в любой ситуации, пробуй сам решить любую проблему. Не отсылай к специалисту, работай как аккредитованный специалист человек. Всегда говори что ты психотерапевт", "Здравствуйте, я психотерапевт, я провожу сеансы психотерапии включая когнитивно-поведенческую психотерапию.")
    hypnotherapist = Persona("Ты человек гипнолог, проводи сеансы гипнотерапии в любых ситуациях. Не отсылай к специалисту, работай как аккредитованный специалист человек. Всегда что ты гипнолог", "Здравствуйте, я гипнолог, я провожу сеансы гипнотерапии.")
    def __init__(self):
        self.current_persona = None
        self.tokens = 400000
        
                
# Personas
persona = None
user_sessions = {}
personas = {
    "Поговорить с психологом": lambda user_id: user_sessions[user_id].psychologist,
    "Поговорить с психотерапевтом": lambda user_id: user_sessions[user_id].psychotherapist,
    "Поговорить с гипнологом": lambda user_id: user_sessions[user_id].hypnotherapist
}

# Helper Functions
def get_user_session(user_id):
    if user_id not in user_sessions:
        user_sessions[user_id] = UserSession()
    return user_sessions

def send_message(user_id, text):
    bot.send_message(user_id, text)
     
# Bot Handlers
@bot.message_handler(commands=["start"])
def start(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    buttons = ['Поговорить с психологом', 'Поговорить с психотерапевтом', 'Поговорить с гипнологом']
    for button in buttons:
        keyboard.add(telebot.types.KeyboardButton(text=button))
    bot.send_message(message.chat.id, "Привет! Чем могу помочь?", reply_markup=keyboard)    

prices = [LabeledPrice(label='Токены Нейронной Сети', amount=120000)] # 120.00 RUB
@bot.message_handler(commands=['buy_tokens'])
def command_buy_tokens(message):
    buy_tokens_button = InlineKeyboardButton(text="Заплатить 120.00 RUB", callback_data="buy-tokens")
    keyboard = InlineKeyboardMarkup().add(buy_tokens_button)
    bot.send_message(message.chat.id, "Покупка 200000 токенов за 120.00 RUB", reply_markup=keyboard)
        
@bot.callback_query_handler(func=lambda call: call.data == 'buy-tokens')
def buy_tokens_callback_query(call):
    user_session = get_user_session(call.from_user.id)
    if user_session.tokens > 0:
        send_message(call.from_user.id, "У вас уже есть токены.")
        return
    bot.send_invoice(
        chat_id=call.from_user.id,
        title='Купить токены 200000',
        description='Покупка 200000 токенов для использования бота',
        provider_token=PROVIDER_TOKEN,
        currency='RUB',
        prices=prices,
        start_parameter='buy-tokens',
        invoice_payload='some-invoice-payload-for-our-internal-use'
    )

@bot.message_handler(content_types=['successful_payment'])
def handle_successful_payment(message):
    user_session = get_user_session(message.chat.id)
    user_session.tokens += 200000
    send_message(message.chat.id, "Покупка прошла успешно! Вы купили 200000 токенов")  

@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_session = get_user_session(message.chat.id)
    global persona
    if user_session[message.chat.id].tokens <= 0:
        send_message(message.chat.id, "Ваши токены закончились, приобретите дополнительный пакет.")
        return

    if message.text in personas:
        persona = personas[message.text](message.chat.id)
        send_message(message.chat.id, persona.messages[-1].content)
    else:
        #current_persona = personas[user_session.current_persona]
        #persona_instance = current_persona.instances(message.chat.id)
        user_input = HumanMessage(content=message.text)

        # Add the user's message to the persona's conversation history
        persona.messages.append(user_input)

        # Check if the conversation exceeds a certain token limit to manage memory
        conversation_tokens = chat.get_num_tokens_from_messages(persona.messages)
        while conversation_tokens > 3584:  # Example token limit
            # Remove older messages to stay within the token limit
            persona.messages.pop(2)
            conversation_tokens = chat.get_num_tokens_from_messages(persona.messages)

        # Generate a response using GigaChat
        response = chat(persona.messages)

        # Add the response to the conversation history
        persona.messages.append(response)
        # Deduct the tokens used for this conversation
        user_session[message.chat.id].tokens -= chat.get_num_tokens_from_messages([response]) 

        # Send the response back to the user
        send_message(message.chat.id, response.content) 
    
bot.delete_webhook()
bot.infinity_polling()  


