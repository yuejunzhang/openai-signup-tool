import random
import time

from loguru import logger
from selenium.common import TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import title_is, presence_of_element_located, staleness_of
from selenium.webdriver.support.wait import WebDriverWait

from utils import get_webdriver

CHALLENGE_TITLES = [
    # Cloudflare
    'Just a moment...',
    # DDoS-GUARD
    'DDoS-Guard'
]
CHALLENGE_SELECTORS = [
    # Cloudflare
    '#cf-challenge-running', '.ray_id', '.attack-box', '#cf-please-wait', '#challenge-spinner', '#trk_jschal_js',
    # Custom CloudFlare for EbookParadijs, Film-Paleis, MuziekFabriek and Puur-Hollands
    'td.info #js_info',
    # Fairlane / pararius.com
    'div.vc div.text-box h2'
]
SHORT_TIMEOUT = 1

def click_verify(driver: WebDriver):
    logger.debug("waiting for the Cloudflare verify checkbox...")
    time.sleep(random.randint(5,10))
    logger.debug(f"================Body: {driver.body}, Page Title: {driver.title}")
    try:
        logger.debug("Try to find the Cloudflare verify checkbox...")
        iframe = driver.find_element(By.XPATH, "//iframe[starts-with(@id, 'cf-chl-widget-')]")
        driver.switch_to.frame(iframe)
        checkbox = driver.find_element(
            by=By.XPATH,
            value='//*[@id="challenge-stage"]/div/label/input',
        )
        if checkbox:
            actions = ActionChains(driver)
            actions.move_to_element_with_offset(checkbox, random.randint(2,6), random.randint(2,8))
            actions.click(checkbox)
            actions.perform()
            logger.debug("Cloudflare verify checkbox found and clicked!")
    except Exception:
        logger.debug("Cloudflare verify checkbox not found on the page.")
    finally:
        driver.switch_to.default_content()

    try:
        logger.debug("Try to find the Cloudflare 'Verify you are human' button...")
        button = driver.find_element(
            by=By.XPATH,
            value="//input[@type='button' and @value='Verify you are human']",
        )
        if button:
            actions = ActionChains(driver)
            actions.move_to_element_with_offset(button, random.randint(2,6), random.randint(2,8))
            actions.click(button)
            actions.perform()
            logger.debug("The Cloudflare 'Verify you are human' button found and clicked!")
    except Exception:
        logger.debug("The Cloudflare 'Verify you are human' button not found on the page.")

    time.sleep(2)


def bypass(link,driver):
    
    driver.get(link)
    driver.start_session()
    
    driver.get(link)
    driver.start_session()

    # todo check ban

    page_title = driver.title


    challenge_found = False
    for title in CHALLENGE_TITLES:
        if title.lower() == page_title.lower():
            challenge_found = True
            logger.debug("Challenge detected. Title found: " + page_title)
            break
    if not challenge_found:
        # find challenge by selectors
        for selector in CHALLENGE_SELECTORS:
            found_elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if len(found_elements) > 0:
                challenge_found = True
                logger.debug("Challenge detected. Selector found: " + selector)
                break

    attempt = 0
    if challenge_found:
        while True:
            try:
                attempt = attempt + 1
                # wait until the title changes
                for title in CHALLENGE_TITLES:
                    logger.debug("Waiting for title (attempt " + str(attempt) + "): " + title)
                    WebDriverWait(driver, SHORT_TIMEOUT).until_not(title_is(title))

                # then wait until all the selectors disappear
                for selector in CHALLENGE_SELECTORS:
                    logger.debug("Waiting for selector (attempt " + str(attempt) + "): " + selector)
                    WebDriverWait(driver, SHORT_TIMEOUT).until_not(
                        presence_of_element_located((By.CSS_SELECTOR, selector)))

                # all elements not found
                break

            except TimeoutException:
                logger.debug("Timeout waiting for selector")

                click_verify(driver)

                # update the html (cloudflare reloads the page every 5 s)
                html_element = driver.find_element(By.TAG_NAME, "html")

        # waits until cloudflare redirection ends
        logger.debug("Waiting for redirect")
        # noinspection PyBroadException
        try:
            WebDriverWait(driver, SHORT_TIMEOUT).until(staleness_of(html_element))
        except Exception:
            logger.debug("Timeout waiting for redirect")

        logger.debug("Challenge solved!")

