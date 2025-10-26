# import nfc
# from nfc.clf import RemoteTarget
# import ndef
# print("please.")

# clf = nfc.ContactlessFrontend('usb')
# if clf:
#     target = clf.sense(RemoteTarget('106A'), RemoteTarget('106B'), RemoteTarget('212F'))
#     print(target)
#     tag = nfc.tag.activate(clf, target)
#     print(tag)
# if clf:
#     target = clf.sense(RemoteTarget('106A'), RemoteTarget('106B'), RemoteTarget('212F'))
#     print(target)
#     tag = nfc.tag.activate(clf, target)
#     if tag.ndef:
#         record = ndef.TextRecord("Hello NFC!")
#         tag.ndef.records = [record]  # Write the NDEF message
#         print("Tag written successfully")
#         print(tag.ndef.records)
#     else:
#         print("Tag is not NDEF compatible")
import usb.core

dev = usb.core.find(idVendor=0x072F, idProduct=0x2200)
if dev:
    print("Device found!")
else:
    print("Device not found or backend missing")