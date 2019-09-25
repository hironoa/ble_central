from bluepy.btle import Peripheral, DefaultDelegate, Scanner, BTLEException, UUID
import bluepy.btle
import time
import sys
import struct
from threading import Thread, Timer

Debugging = False
def DBG(*args):
    if Debugging:
        msg = " ".join([str(a) for a in args])
        print(msg)
        sys.stdout.flush()

Verbose = True
def MSG(*args):
    if Verbose:
        msg = " ".join([str(a) for a in args])
        print(msg)
        sys.stdout.flush()

def timeoutRetry(addr):
    MSG('timer expired (%s)' % addr)
    devThread = scannedDevs[addr]
    devThread.forceDisconnect()
    MSG('Thread disconnected (%s)' % addr)


class Test(Thread, Peripheral):
    def __init__(self, dev):
        Peripheral.__init__(self)
        Thread.__init__(self)
        self.setDaemon(True)
        self.dev = dev
        self.isConnected = False
        self.count = 0
        print('thread init %s' % dev.addr)

    def run(self):
        while True:
            t = Timer(30, timeoutRetry, [self.dev.addr])
            t.start()
            while self.isConnected == False:  # つながるまでconnectする
                try:
                    self.connect(self.dev)
                    self.isConnected = True
                except BTLEException as e:
                    DBG('BTLE Exception while connect on ', self.dev.addr)
                    DBG('  type:' + str(type(e)))
                    DBG('  args:' + str(e.args))
                    # pass

            MSG('connected to ', self.dev.addr)

            try:
                for service in self.getServices():
                    MSG("=" * 100)
                    MSG('[[Service]]', service.uuid, service)
                    try:
                        for desc in service.getDescriptors():
                            MSG('[[Desc]] ', desc.uuid, desc.handle, desc.uuid.getCommonName())
                    except:
                        pass
                    for char in service.getCharacteristics():
                        if char.supportsRead():
                            data = char.read()
                        MSG('[[Characteristics]] ', char.uuid, char.getHandle(), char.propertiesToString(), char.properties, data)

                self.writeCharacteristic(69, b'\x00\x00', True)
                MSG('[[Notify?]] ', self.readCharacteristic(69))
                if self.waitForNotifications(1.0):
                    continue

                MSG(self.readCharacteristic(62))
                MSG(str(self.count).encode())
                self.count += 1
                self.writeCharacteristic(62, str(self.count).encode(), True)

                t.cancel()
                time.sleep(1)

            except BTLEException as e:
                DBG('BTLE Exception while getCharacteristics on ', self.dev.addr)
                DBG('  type:' + str(type(e)))
                DBG('  args:' + str(e.args))
                self.disconnect()
                self.isConnected = False
                t.cancel()

    def forceDisconnect(self):
        if self.isConnected:
            self.disconnect()
        self.isConnected = False

scannedDevs = {}

class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):  # スキャンハンドラー
        if isNewDev:  # 新しいデバイスが見つかったら
            # print('Device %s (%s), RSSI=%d dB' % (dev.addr, dev.addrType, dev.rssi))
            for (adtype, desc, value) in dev.getScanData():
                # print('  adtype : %s %s = %s' % (adtype, desc, value))
                if desc == 'Complete Local Name' and value == 'Blank':
                # if desc == 'Complete Local Name' and value == 'BLE-LAB-1':
                    if dev.addr in scannedDevs.keys():  # すでに見つけていたらスキップ
                        return
                    MSG('New %s %s' % (value, dev.addr))
                    # print(scannedDevs)
                    devThread = Test(dev)  # EnvSensorクラスのインスタンスを生成
                    scannedDevs[dev.addr] = devThread
                    devThread.start()  # スレッドを起動

    def handleNotification(self, cHandle, data):
        MSG('[[Notification]] ', data)

def main():
    scanner = Scanner().withDelegate(ScanDelegate())
    while True:
        try:
            scanner.scan(5.0) # スキャンする。デバイスを見つけた後の処理はScanDelegateに任せる
        except BTLEException:
            MSG('BTLE Exception while scannning.')

if __name__ == "__main__":
    main()