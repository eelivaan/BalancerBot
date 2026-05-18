import bluetooth
import struct
from machine import Pin
from utime import sleep_ms

class BLESerial:
    _IRQ_CENTRAL_CONNECT = 1
    _IRQ_CENTRAL_DISCONNECT = 2
    _IRQ_GATTS_WRITE = 3
    _IRQ_SCAN_RESULT = 5
    _IRQ_SCAN_DONE = 6

    _FLAG_WRITE = 0x0008
    _FLAG_NOTIFY = 0x0010

    # Nordic UART Service (NUS) UUIDs.
    _UART_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
    _UART_TX = (
        bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E"),
        _FLAG_NOTIFY,
    )
    _UART_RX = (
        bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E"),
        _FLAG_WRITE,
    )
    _UART_SERVICE = (
        _UART_UUID,
        (_UART_TX, _UART_RX),
    )

    def __init__(self, msg_callback=None) -> None:
        self.ble = bluetooth.BLE()
        self.connections = set()
        self.tx_handle = None
        self.rx_handle = None
        self.msg_callback = msg_callback
        self.msg_buffer = bytearray()

        self.ble.irq(self.ble_callback)
        self.ble.active(True)

        if 1:
            ((self.tx_handle, self.rx_handle),) = self.ble.gatts_register_services((self._UART_SERVICE,))
            self.ble.gap_advertise(50_000, adv_data=self.advertising_payload())
            print("BLE UART advertising as <PicoBLE>...")
        else:
            print("Scanning...")
            self.ble.gap_scan(5000)

    def deactivate(self):
        self.ble.active(False)


    def advertising_payload(self, name="PicoBLE"):
        payload = bytearray()
        payload += b"\x02\x01\x06"  # General discoverable + BR/EDR not supported.
        name_bytes = name.encode("utf-8")
        payload += struct.pack("BB", len(name_bytes) + 1, 0x09) + name_bytes
        # 128-bit UUID omitted to stay within the 31-byte BLE advertising limit.
        return payload


    def send(self, data):
        if isinstance(data, str):
            data = data.encode("utf-8")
        for conn_handle in self.connections:
            self.ble.gatts_notify(conn_handle, self.tx_handle, data)


    def ble_callback(self, event, data):
        if event == BLESerial._IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            self.connections.add(conn_handle)
            print("Central connected:", conn_handle)
            self.send("Hello")

        elif event == BLESerial._IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            if conn_handle in self.connections:
                self.connections.remove(conn_handle)
            print("Central disconnected:", conn_handle)
            if self.ble.active():
                self.ble.gap_advertise(50_000, adv_data=self.advertising_payload())

        elif event == BLESerial._IRQ_GATTS_WRITE:
            conn_handle, value_handle = data
            if value_handle == self.rx_handle:
                incoming = self.ble.gatts_read(self.rx_handle)
                self.msg_buffer.extend(incoming)
                if b'\0' in self.msg_buffer:
                    (msg, self.msg_buffer) = self.msg_buffer.split(b'\0', 1)  # Split at null terminator
                    if self.msg_callback:
                        self.msg_callback(msg.decode("utf-8", "replace"))
                # Echo back received bytes to emulate a serial terminal.
                self.send(incoming)

        elif event == BLESerial._IRQ_SCAN_RESULT:
            (addr_type, addr, adv_type, rssi, adv_data) = data
            print(addr_type, bytes(addr), adv_type, rssi, bytes(adv_data))

        elif event == BLESerial._IRQ_SCAN_DONE:
            print("Scan ready")


    def is_connected(self):
        return len(self.connections) > 0


if __name__ == "__main__":
    # test connectivity
    ble = BLESerial()
    ledpin = Pin("LED", Pin.OUT)
    while True:
        try:
            ledpin.toggle()
            sleep_ms(500)
        except KeyboardInterrupt:
            break
    ledpin.off()
    print("Finished.")
    ble.deactivate()
