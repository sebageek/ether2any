
import os

netmask = "255.255.255.0"
mtu = 417
ip = ""
camnum = 0
packetDrop = 20

if os.popen("hostname", "r").read().strip() in ("navi", ):
	ip = "10.44.13.1"
	camnum = 0
else:
	ip = "10.44.13.2"
	camnum = 2

if __name__ == '__main__':
	print ip

