from serial import Serial
from time import sleep

code = """
with open('data.csv', 'r') as f:
    while line := f.readline():
        print(line.strip(), end='\\n')
"""

with Serial('COM9', 115200, timeout=5) as ser:
    print("COM9 opened")
    sleep(1)
    ser.write(b'\n')
    sleep(1)
    ser.write(b'\x03\n') # CTRL-C
    sleep(1)
    ser.write(b'\x02\n') # CTRL-B
    sleep(1)
    print(ser.read_all().decode(errors="ignore"))

    print("Writing...")
    ser.write(code.encode() + b'\n')
    print("Reading...")
    sleep(5)
    
    data = ser.read_all().decode() #type: str
    data = data.replace('\r', '') # Remove carriage returns
    data = data[data.find('time') : data.rfind('>>>')]
    with open('data.csv', 'w') as f:
        f.write(data)

    sleep(3)
    print(ser.read_all().decode(errors="ignore"))

print("COM9 closed")

#input("Press any key to continue...")
