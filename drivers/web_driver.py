from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

def create_web_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
    return driver
