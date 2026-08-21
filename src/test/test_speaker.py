from sound import Speaker
from time import sleep

s = Speaker(22)
s.volume(0.2)
print(s)

for i in range(10):
    s.beep(200 + i*100, 0.2)
    sleep(0.35)