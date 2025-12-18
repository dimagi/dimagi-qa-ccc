from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# def create_web_driver():
#     options = webdriver.ChromeOptions()
#     options.add_argument("--start-maximized")
#
#     driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
#     return driver

def create_web_driver():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")

    driver = webdriver.Chrome(options=options)
    return driver