import imaplib
import email
from email.header import decode_header
import re
import time
import telebot
from threading import Thread
import threading

# Telegram bot credentials
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""

# Gmail credentials
GMAIL_USER = "willnaif69@gmail.com"
GMAIL_PASS = ""
IMAP_SERVER = "imap.gmail.com"

# Initialize bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Global state
monitoring_active = False
monitor_thread = None
processed_emails = set()
monitoring_lock = threading.Lock()

def check_email_loop():
    global monitoring_active
    while True:
        with monitoring_lock:
            if not monitoring_active:
                break
        try:
            check_emails()
        except Exception as e:
            print(f"Error in check_email_loop: {e}")
        time.sleep(5)

def check_emails():
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(GMAIL_USER, GMAIL_PASS)
        mail.select("inbox")

        # Search for Rockstar OTP emails
        status, messages = mail.search(None, 'FROM "noreply@rockstargames.com" SUBJECT "Your Rockstar Games verification code"')
        
        if status == "OK" and messages[0]:
            for num in messages[0].split():
                if num in processed_emails:
                    continue
                
                status, data = mail.fetch(num, "(RFC822)")
                if status == "OK":
                    msg = email.message_from_bytes(data[0][1])
                    
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode()
                                process_email_body(body, num)
                    else:
                        body = msg.get_payload(decode=True).decode()
                        process_email_body(body, num)
                    
                    mail.store(num, '+FLAGS', '\\Seen')
        
        mail.logout()
        
    except Exception as e:
        print(f"Error in check_emails: {e}")

def process_email_body(body, num):
    otp = extract_otp(body)
    if otp:
        send_to_telegram(otp)
        processed_emails.add(num)

def extract_otp(body):
    try:
        pattern = r'Enter this code on the identity verification screen:\s*(\d{6})'
        match = re.search(pattern, body)
        if match:
            return match.group(1)
        
        match = re.search(r'(\d{6})', body)
        return match.group(1) if match else None
    except Exception as e:
        print(f"Error extracting OTP: {e}")
        return None

def send_to_telegram(otp):
    try:
        message = f"🎮 Rockstar Games OTP: {otp}\n⏰ Time: {time.strftime('%H:%M:%S')}"
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        print(f"Sent OTP to Telegram: {otp}")
    except Exception as e:
        print(f"Error sending to Telegram: {e}")

def start_monitoring():
    global monitoring_active, monitor_thread
    with monitoring_lock:
        if not monitoring_active:
            monitoring_active = True
            monitor_thread = Thread(target=check_email_loop)
            monitor_thread.daemon = True
            monitor_thread.start()
            return True
    return False

def stop_monitoring():
    global monitoring_active, monitor_thread
    with monitoring_lock:
        monitoring_active = False
        if monitor_thread:
            monitor_thread.join(timeout=1)
            return True
    return False

# Telegram command handlers
@bot.message_handler(commands=['start'])
def handle_start(message):
    if str(message.chat.id) == TELEGRAM_CHAT_ID:
        if start_monitoring():
            bot.reply_to(message, "🟢 OTP Monitor started! I'll notify you when new codes arrive.\n\nUse /stop to stop monitoring.")
        else:
            bot.reply_to(message, "⚠️ Monitoring is already active!")
    else:
        bot.reply_to(message, "❌ Unauthorized access.")

@bot.message_handler(commands=['stop'])
def handle_stop(message):
    if str(message.chat.id) == TELEGRAM_CHAT_ID:
        if stop_monitoring():
            bot.reply_to(message, "🔴 OTP Monitor stopped.\n\nUse /start to start monitoring again.")
        else:
            bot.reply_to(message, "⚠️ Monitoring is not active!")
    else:
        bot.reply_to(message, "❌ Unauthorized access.")

@bot.message_handler(commands=['status'])
def handle_status(message):
    if str(message.chat.id) == TELEGRAM_CHAT_ID:
        status = "🟢 Active" if monitoring_active else "🔴 Inactive"
        bot.reply_to(message, f"Monitor Status: {status}\n\nProcessed emails: {len(processed_emails)}")
    else:
        bot.reply_to(message, "❌ Unauthorized access.")

if __name__ == "__main__":
    print("Bot started! Send /start in Telegram to begin monitoring.")
    bot.infinity_polling()
