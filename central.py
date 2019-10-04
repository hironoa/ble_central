from bluepy.btle import *
import bluepy.btle
import time
import sys
import struct
from threading import Thread, Timer

bluepy.btle.Debugging = False

Debugging = False
def DBG(*args):
    if Debugging:
        msg = " ".join([str(a) for a in args])
        print(msg)
        sys.stdout.flush()


Logging = False
def LOG(*args):
    if Logging:
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
        self.setDelegate(ScanDelegate())
        self.dev = dev
        self.isConnected = False
        self.count = 0
        MSG('thread init ', dev.addr)

    def run(self):
        MSG('thread run ', self.dev.addr)
        while True:
            self.setDelegate(ScanDelegate())
            t = Timer(30, timeoutRetry, [self.dev.addr])
            t.start()

            while self.isConnected == False:  # つながるまでconnectする
                try:
                    self.connect(self.dev)
                    # self.connect(self.dev.addr, bluepy.btle.ADDR_TYPE_RANDOM, self.dev.iface)
                    self.isConnected = True
                except BTLEException as e:
                    DBG('BTLE Exception while connect on ', self.dev.addr)
                    DBG('  type:' + str(type(e)))
                    DBG('  args:' + str(e.args))
                    # pass

                MSG('\n', 'connected to ', self.dev.addr)

            try:
                # self.ScanInformation()

                svc = self.getServiceByUUID('1111')
                MSG(svc)
                for desc in svc.getDescriptors():
                    if desc.uuid.getCommonName() == 'Client Characteristic Configuration':
                        MSG(desc.handle, desc.read(), str(self.readCharacteristic(svc.hndStart+2)))
                        self.writeCharacteristic(desc.handle, b'\x01\x00', True)
                        # desc.write(b'\x01\x00', True)
                        MSG(desc.handle, desc.read())

                while True:
                    if self.waitForNotifications(1.0):
                        continue

                # self.writeCharacteristic(69, b'\x00\x00', True)
                # MSG('[[Notify?]] ', self.readCharacteristic(69))
                # if self.waitForNotifications(1.0):
                #     continue

                # MSG(self.readCharacteristic(62))
                # MSG(str(self.count).encode())
                # self.count += 1
                # self.writeCharacteristic(62, str(self.count).encode(), True)

                t.cancel()
                # time.sleep(1)

            except BTLEException as e:
                MSG('BTLE Exception while getCharacteristics on ', self.dev.addr)
                DBG('  type:' + str(type(e)))
                DBG('  args:' + str(e.args))
                self.disconnect()
                self.isConnected = False
                t.cancel()

    def ScanInformation(self):
        try:
            for service in self.getServices():
                LOG("=" * 100)
                LOG('[[Service]]', service.uuid, service)

                # 以下のServiceのCharacteristicをReadするとエラー？になるため、スキップする
                if service.uuid.getCommonName() == 'Battery Service': continue
                if service.uuid.getCommonName() == 'Current Time Service': continue
                if service.uuid.getCommonName() == '89d3502b-0f36-433a-8ef4-c502ad55f8dc': continue

                for desc in service.getDescriptors():
                    try:
                        LOG('[[Desc]] ', desc.uuid, desc.handle, desc.uuid.getCommonName(), str(desc.read()))
                    except BTLEException as e:
                        LOG('[[Desc]] ', desc.uuid, desc.handle, desc.uuid.getCommonName())
                        # MSG('[[Desc]] ', 'Err', str(type(e)), str(e.args))

                for char in service.getCharacteristics():
                    try:
                        if char.supportsRead():
                            # data = char.read()
                            data = char.peripheral.readCharacteristic(char.getHandle())
                            LOG('[[Characteristics]] ', char.uuid, char.getHandle(), char.propertiesToString(), data)
                        else:
                            LOG('[[Characteristics]] ', char.uuid, char.getHandle(), char.propertiesToString())
                    except BTLEException as e:
                        DBG('[[Characteristics]] ', 'Err', str(type(e)), str(e.args))
                        self.disconnect()
                        self.isConnected = False

        except BTLEException as e:
            DBG('BTLE Exception while getCharacteristics on ', self.dev.addr)
            DBG('  type:' + str(type(e)))
            DBG('  args:' + str(e.args))
            self.disconnect()
            self.isConnected = False
        
    def forceDisconnect(self):
        MSG('forceDisconnect')
        if self.isConnected:
            self.disconnect()
        self.isConnected = False

scannedDevs = {}

class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleNotification(self, cHandle, data):
        MSG('[[Notification]] ', cHandle, data)

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
                    MSG(type(dev))
                    devThread = Test(dev)  # EnvSensorクラスのインスタンスを生成
                    scannedDevs[dev.addr] = devThread
                    devThread.start()  # スレッドを起動

def main():
    scanner = Scanner().withDelegate(ScanDelegate())
    scanner.scan(10.0) # スキャンする。デバイスを見つけた後の処理はScanDelegateに任せる

    # while True:
    #     pass
    while True:
        try:
            scanner.scan(10.0) # スキャンする。デバイスを見つけた後の処理はScanDelegateに任せる
        except BTLEException as e:
            DBG('BTLE Exception while scannning.')
            DBG('  type:' + str(type(e)))
            DBG('  args:' + str(e.args))

if __name__ == "__main__":
    main()
