import nfc, nfc.clf
import binascii

def on_connect(tag):
	print(tag)
	print(tag.type)
	print(binascii.hexlify(tag.identifier).upper())

if __name__ == '__main__':
	clf = nfc.ContactlessFrontend("usb")
	
	rdwr_options = {
		'targets': ['212F' , '424F'], #Felicaに限定
		'on-connect': on_connect,
	}
	
	clf.connect(rdwr=rdwr_options)
