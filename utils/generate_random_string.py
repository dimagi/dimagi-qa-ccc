import random
import string

""""Genrates random strings that are passed as user inputs across various areasn in CCHQ"""

chars = string.ascii_lowercase + string.digits
random_string = ''.join(random.choices(chars, k=6))
N = 10
random_number = random.randint(100, 19999)


def fetch_random_string():
    return random_string


def fetch_phone_number():
    min_value = pow(10, N - 1)
    max_value = pow(10, N) - 1
    return str(random.randint(min_value, max_value))


def fetch_random_digit():
    return str(random_number)


def fetch_random_boolean():
    return random.choice([True, False])


def fetch_random_digit_with_range(start, end):
    return str(random.randint(start, end))


def fetch_string_with_special_chars(length):
    return ''.join(
        random.choices(
            string.ascii_lowercase + string.digits + string.punctuation,
            k=length
        )
    )

