import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta, timezone

from bs4 import BeautifulSoup
import re

from database.db import DbConnection


class YandexMailClient:
    def __init__(self, mail: str, token: str, db_conn: DbConnection):
        self.db_conn = db_conn
        self.imap_server = "imap.yandex.com"
        self.email_account = mail
        self.password = token
        self.mail = None

    def connect(self):
        self.mail = imaplib.IMAP4_SSL(self.imap_server)
        self.mail.login(self.email_account, self.password)

    @staticmethod
    def decode_mime_header(header):
        decoded_parts = decode_header(header)
        result = []
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                part = part.decode(encoding or 'utf-8')
            result.append(part)
        return ''.join(result)

    @staticmethod
    def get_code(msg) -> str:
        email_body = None
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                if content_type == "text/plain" and "attachment" not in content_disposition:
                    email_body = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8')
        else:
            email_body = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8')

        if email_body:
            soup = BeautifulSoup(email_body, "html.parser")
            text = soup.get_text()

            text = re.sub(r'http[s]?://\S+', '', text)

            text = re.sub(r'\[image:.*?\]', '', text)

            text = re.sub(r'\s+', ' ', text).strip()

            match = re.search(r'\b\d{6}\b', text)

            if match:
                text = match.group(0)

            return text

    def delete_email(self, email_id):
        self.mail.store(email_id, '+FLAGS', '\\Deleted')

    def fetch_emails(self, user: str, phone: str, time_request: datetime):
        sub_filter = "Подтверждение учетных данных Ozon"

        self.mail.select("inbox")
        status, messages = self.mail.search(None, "ALL")
        if status != "OK":
            raise Exception("Не удалось выполнить поиск писем")

        result_emails = []
        for num in messages[0].split():
            status, data = self.mail.fetch(num, "(RFC822)")
            if status != "OK":
                continue

            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)

            email_subject = self.decode_mime_header(msg.get("Subject", ""))
            if sub_filter not in email_subject:
                continue

            email_date = msg.get("Date")
            time_response = datetime.strptime(email_date, "%a, %d %b %Y %H:%M:%S %z")
            time_response = time_response.astimezone(tz=timezone(timedelta(hours=3)))
            time_response = time_response.replace(tzinfo=None)
            time_request = time_request.replace(tzinfo=None)
            delta = (time_request - time_response).total_seconds()

            if delta > 120:
                continue

            code = self.get_code(msg)
            if code:
                result_emails.append({'code': code,
                                      'email_id': num,
                                      'time_response': time_response})

        if result_emails:
            result_emails.sort(key=lambda x: x['time_response'])
            self.db_conn.update_phone_message(user=user,
                                              phone=phone,
                                              time_response=result_emails[0]['time_response'],
                                              message=result_emails[0]['code'],
                                              marketplace='Ozon')
            self.delete_email(email_id=result_emails[0]['email_id'])
        else:
            raise Exception("Нет подходящих писем")

    def close(self):
        """Закрытие соединения"""
        self.mail.logout()
