import time
from functools import wraps


def convert_ms(milliseconds: int = 0):
    seconds = int((milliseconds / 1000) % 60)
    minutes = int((milliseconds / (1000 * 60)) % 60)
    hours = int((milliseconds / (1000 * 60 * 60)) % 24)
    time_list = [
        f"{hours} hour(s)", f"{minutes} minute(s)", f"{seconds} second(s)"]
    time_list = [t for t in time_list if t.split()[0] != '0']
    return ', '.join(time_list)


def timed(f):
    @wraps(f)
    def wrapper(*args, **kwds):
        start = time.time()
        result = f(*args, **kwds)
        elapsed = int(1000 * (time.time() - start))
        if elapsed > 1000:
            print(f"{f.__module__}.{f.__name__}: {convert_ms(milliseconds=elapsed)}")
        return result

    return wrapper
