import base64
import fcntl
import json
import os
import random
import re
import secrets
import string
import time
import traceback
import uuid

import requests
from func_timeout import func_timeout, FunctionTimedOut
from loguru import logger
from selenium.common import NoSuchElementException, StaleElementReferenceException, TimeoutException, WebDriverException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import cloudflare_solver
from config import config
import utils
from globals import GlobalState


class Interrupted(Exception):
    pass


class Signup:
    def __init__(self):
        self.driver = utils.get_webdriver()

    def sign_up(self):
        try:
            func_timeout(5 * 60, self._sign_up)
        except Interrupted as e:
            logger.error("error in signup: {}".format(e))
            raise e
        except FunctionTimedOut as e:
            logger.warning("signup timeout")
            pass
        except Exception as e:
            traceback.print_exc()
        finally:
            self.driver.quit()


    def _sign_up(self):
        cloudflare_solver.bypass('https://platform.openai.com/signup/', self.driver)
        email_input = WebDriverWait(self.driver, 30).until(
            EC.presence_of_element_located((By.ID, "email"))
        )
        email = self._get_email()
        email_input.send_keys(email)

        # todo check email
        submit_btn = self.driver.find_element(By.XPATH, '//button[@type="submit"]')
        submit_btn.click()

        password_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "password"))
        )

        password = self._get_password()
        password_input.send_keys(password)

        submit_btn = self.driver.find_element(By.XPATH, '//button[@type="submit"]')
        submit_btn.click()

        time.sleep(5)
        while True:
            try:
                self.driver.find_element(By.XPATH, "//h1[text()='Oops!']")
                raise Exception("Oops!")
            except NoSuchElementException:
                pass
            try:
                self.driver.find_element(By.XPATH, "//p[text()='Too many signups from the same IP']")
                GlobalState.exception = Interrupted("Too many signups from the same IP")
                raise GlobalState.exception
            except NoSuchElementException:
                pass
            try:
                self.driver.find_element(By.XPATH, "//h1[text()='Tell us about you']")
                break
            except NoSuchElementException:
                logger.debug(f"{email} wait for email verification")
                self.driver.refresh()
                time.sleep(10)

        name_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Full name']"))
        )
        name_input.send_keys(''.join(random.choices(string.ascii_letters, k=3)))

        birthday_input = self.driver.find_element(By.XPATH, "//input[@placeholder='Birthday']")

        year = random.randint(1980, 2000)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        random_date = "{:02d}/{:02d}/{}".format(day, month, year)

        birthday_input.send_keys(random_date)

        submit_btn = self.driver.find_element(By.XPATH, '//button[@type="submit"]')

        submit_btn.click()

        self._try_solve_arkose_challenge()

        self._save_account(email, password)

    def _get_email(self):
        return ''.join(
            [secrets.choice(string.ascii_letters + string.digits) for _ in range(15)]) + "@" + config['domain']

    def _get_password(self):
        return ''.join(
            [secrets.choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(15)])

    def _get_base64(self, bg_image_url):

        script = """
        var callback = arguments[arguments.length - 1];
        var xhr = new XMLHttpRequest();
        xhr.responseType = 'blob';
        xhr.onload = function() {
            var reader = new FileReader();
            reader.onloadend = function() {
                callback(reader.result);
            };
            reader.readAsDataURL(xhr.response);
        };
        xhr.open('GET', arguments[0]);
        xhr.send();
        """
        # 执行脚本并获取结果
        base64_data = self.driver.execute_async_script(script, bg_image_url)

        return base64_data

    def _get_ans_index(self, que, base64):
        url = "https://api.yescaptcha.com"

        clientKey = config['clientKey']
        if not clientKey:
            GlobalState.exception = Interrupted("match funcaptcha but no yes clientKey")
            raise GlobalState.exception
        json = {
            "clientKey": clientKey,
            "task": {
                "type": "FunCaptchaClassification",
                "image": base64,
                "question": que
            },
            "softID": 31275
        }

        resp = requests.post(url + "/createTask", json=json)
        index = resp.json()['solution']['objects'][0]
        return index

    def _save_and_get_sess(self, email, password):

        for i in range(3):
            logs = self.driver.get_log('performance')
            for log in logs:
                log_json = json.loads(log['message'])['message']
                if log_json['method'] == 'Network.responseReceived' and 'dashboard/onboarding/create_account' in \
                        log_json['params']['response']['url']:
                    request_id = log_json['params']['requestId']
                    try:
                        logger.info(f"{email} signup success. Password: {password}")

                        response = self.driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': request_id})
                        if response and response['body']:
                            if 'session' in response['body']:
                                with open("data/account.txt", "a", encoding="utf-8") as f:
                                    fcntl.flock(f, fcntl.LOCK_EX)
                                    f.write(f"{email}----{password}\n")

                                logger.info(f"{email} signup success!")
                                self._save_challange_image()
                                sess = json.loads(response['body'])['session']['sensitive_id']
                                return sess
                    except WebDriverException as e:
                        pass
            time.sleep(3)
        return None

    def _save_challange_image(self):
        if hasattr(self, 'image_datas') and hasattr(self, 'que') and self.image_datas and self.que:
            path = f'data/solved/{self.que}'
            os.makedirs(path, exist_ok=True)
            for i, image_data in enumerate(self.image_datas):
                base64_string = image_data.split(',')[1]
                data = base64.b64decode(base64_string)
                with open(f"{path}/{uuid.uuid4()}_{self.ans_index[i]}.jpg", "wb") as f:
                    f.write(data)

    def _save_account(self, email, password):
        sess = self._save_and_get_sess(email, password)
        if sess:
            url = "https://api.openai.com/dashboard/billing/credit_grants"
            headers = {
                "Authorization": f"Bearer {sess}",
                "Content-Type": "application/json",
            }

            resp = requests.get(url, headers=headers, allow_redirects=False)
            if resp.status_code == 200:
                data = resp.json()
                if data['total_available'] > 0:
                    with open("data/sess.txt", "a", encoding="utf-8") as f:
                        fcntl.flock(f, fcntl.LOCK_EX)
                        f.write(f"{sess}\n")
                        logger.info(f"{email} save sess success")
                else:
                    logger.warning(f"{email} no credit")
        else:
            logger.warning(f"{email} sess found fail")

    def _try_solve_arkose_challenge(self):
        for i in range(3):
            try:
                try:
                    arkose_frame = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'iframe[title="Verification challenge"]'))
                    )
                    self.driver.switch_to.frame(arkose_frame)
                except StaleElementReferenceException:
                    continue
                except TimeoutException:
                    logger.info("no arkose frame found")
                    return

                try:
                    change_challenge_frame = WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.ID, 'game-core-frame'))
                    )
                except TimeoutException:
                    logger.info("no change challenge frame found")
                    return

                self.driver.switch_to.frame(change_challenge_frame)

                try:
                    WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.XPATH, "//button[text()='Begin puzzle']"))
                    )

                    for i in range(3):
                        try:
                            start_btn = self.driver.find_element(By.XPATH, "//button[text()='Begin puzzle']")
                            start_btn.click()
                        except Exception:
                            pass
                except TimeoutException:
                    pass

                game_type, que, num = self._get_funcaptcha_challenge()

                if not game_type:
                    logger.warning("game type not found")
                    return

                logger.info(f"game type: {game_type}, que: {que}, num: {num}")

                self.que = que
                self.image_datas = []
                self.ans_index = []
                last_bg_image_url = None

                for i in range(num):
                    image_selector = 'img[style*="background-image"]' if game_type == 4 else 'button[style*="background-image"]'

                    image_el = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, image_selector))
                    )
                    style_attribute = image_el.get_attribute('style')
                    match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style_attribute)
                    bg_image_url = match.group(1) if match else None

                    while bg_image_url == last_bg_image_url or bg_image_url is None:
                        image_el = WebDriverWait(self.driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, image_selector))
                        )
                        style_attribute = image_el.get_attribute('style')
                        match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style_attribute)
                        bg_image_url = match.group(1) if match else None

                    last_bg_image_url = bg_image_url

                    base64 = self._get_base64(bg_image_url)
                    self.image_datas.append(base64)
                    index = self._get_ans_index(que, base64)
                    self.ans_index.append(index)

                    if game_type == 4:
                        for j in range(index):
                            next_btn = WebDriverWait(self.driver, 3).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, 'a[role="button"].right-arrow'))
                            )

                            actions = ActionChains(self.driver)
                            actions.move_to_element_with_offset(next_btn, random.randint(1, 5), random.randint(1, 5))
                            actions.click(next_btn)
                            actions.perform()

                        sub_btn = WebDriverWait(self.driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'button.button'))
                        )

                        actions = ActionChains(self.driver)
                        actions.move_to_element_with_offset(sub_btn, random.randint(1, 10), random.randint(1, 10))
                        actions.click(sub_btn)
                        actions.perform()

                    else:
                        image_button = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, f'button[aria-label="Image {index + 1} of 6."]'))
                        )

                        actions = ActionChains(self.driver)
                        actions.move_to_element_with_offset(image_button, random.randint(1, 10), random.randint(1, 10))
                        actions.click(image_button)
                        actions.perform()
                try:
                    try_again_btn = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//button[text()='Try again']"))
                    )
                    try_again_btn.click()
                except TimeoutException:
                    logger.debug("no try again button found may be resolved")
                    return
            except Exception:
                traceback.print_exc()
                logger.warning(f"fail to resolve arkose challenge current retry num {i}")
            finally:
                self.driver.switch_to.default_content()

    def _get_funcaptcha_challenge(self):
        try:
            que_el = WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h2[tabindex='-1']"))
            )
            game_type = 3
            que = que_el.text
            num_elm = WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "p[data-theme='tile-game.roundText']"))
            )
            num = int(re.search(r'of\s+(\d+)', num_elm.text).group(1))

            return game_type, que, num

        except TimeoutException:
            try:
                que_el = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, "//span[@role='text']"))
                )
                game_type = 4
                que_full_text = que_el.text
                que = que_full_text.split('(')[0].strip()
                num = int(re.search(r'\(\d+ of (\d+)\)', que_full_text).group(1))

                return game_type, que, num
            except TimeoutException:
                logger.info("challenge not found")
        return None,None,None


if __name__ == '__main__':
    s = Signup()
    s.sign_up()
