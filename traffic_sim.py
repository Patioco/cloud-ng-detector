import time
import random

LOG = "./detector/test_access.log"

def write(ip):
    with open(LOG, "a") as f:
        f.write(f"{ip} - - [28/Apr/2026:23:59:59] \"GET / HTTP/1.1\" 200 123\n")

def normal_traffic():
    while True:
        write("192.168.1.10")
        time.sleep(random.uniform(0.3, 1.2))

def burst_traffic():
    for _ in range(200):
        write("192.168.1.50")
        time.sleep(0.02)   # 20ms instead of 1ms


def attack(ip="45.12.34.56"):
    for _ in range(2000):
        write(ip)
        time.sleep(0.005)  # 5ms instead of 1ms


if __name__ == "__main__":
    print("Modes:")
    print("1 = normal traffic")
    print("2 = burst traffic")
    print("3 = attack traffic")
    mode = input("Choose mode: ")

    if mode == "1":
        normal_traffic()
    elif mode == "2":
        burst_traffic()
    elif mode == "3":
        attack()
