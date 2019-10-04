from bluetooth.ble import DiscoveryService


while True:
    service = DiscoveryService()
    print (type(service))
    for x in dir(service):
        print (x)
    devices = service.discover(2)
    for address, name in devices.items():
        print("name: {}, address: {}".format(name, address))
