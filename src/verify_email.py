import email
import imaplib
import re
import time

from func_timeout import FunctionTimedOut, func_timeout

import cloudflare_solver

from loguru import logger

from config import config
from globals import GlobalState
from signup import Interrupted
from pool_manager import ThreadPoolManager
from utils import get_webdriver

max_threads = config['emailWorkerNum']
pm = ThreadPoolManager(max_threads)


def click_verify_link(link):
    driver = get_webdriver()
    try:
        func_timeout(5 * 60, cloudflare_solver.bypass, args=(link, driver))
        logger.info('Email verified')
    except FunctionTimedOut:
        logger.warning('Function timed out')
    except Exception as e:
        logger.error(e)
    finally:
        try:
            func_timeout(10,driver.quit)
        except BaseException as e:
            logger.error(f"Error occurred while quitting the driver: {e}")


def verify_email():
    username = config['emailAddr']
    password = config['emailPassword']
    imap_server = config['emailImapServer']
    emailImapPort = config['emailImapPort']
    if not username or not password or not imap_server:
        GlobalState.exception = Interrupted("email config error")
        raise GlobalState.exception
    if emailImapPort:
        mail = imaplib.IMAP4_SSL(imap_server, port=emailImapPort)
    else:
        mail = imaplib.IMAP4_SSL(imap_server)
    try:
        mail.login(username, password)
    except Exception as e:
        GlobalState.exception = Interrupted("email config error")
        raise GlobalState.exception

    logger.info("start to monitor openai verify email")

    def get_html_part(msg):
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == 'text/html':
                    charset = part.get_content_charset()
                    payload = part.get_payload(decode=True)
                    try:
                        return payload.decode(charset or 'utf-8', errors='replace')
                    except LookupError:
                        return payload.decode('utf-8', errors='replace')
        else:
            if msg.get_content_type() == 'text/html':
                charset = msg.get_content_charset()
                payload = msg.get_payload(decode=True)
                try:
                    return payload.decode(charset or 'utf-8', errors='replace')
                except LookupError:
                    return payload.decode('utf-8', errors='replace')

    def check_mail():
        mail.select('INBOX')
        status, messages = mail.search(None, '(UNSEEN)')
        messages = messages[0].split()

        for mail_id in messages:
            status, data = mail.fetch(mail_id, '(RFC822)')
            for response in data:
                if isinstance(response, tuple):
                    msg = email.message_from_bytes(response[1])
                    from_ = msg.get('From')
                    if 'openai' in from_:
                        html_content = get_html_part(msg)
                        if 'Verify your email address' in html_content:
                            link = re.search(r'href="(https://mandrillapp.com[^"]+)"', html_content)
                            if link:
                                link = link.group(1)
                                pm.add_task(lambda: click_verify_link(link))

    try:
        while True:
            check_mail()
            time.sleep(10)
    finally:
        mail.logout()


if __name__ == '__main__':
    verify_email()
