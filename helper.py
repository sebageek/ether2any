def getSrcMacFromPkt(packet):
	if len(packet) < 16:
		return None
	return packet[10:16]

def getDstMacFromPkt(packet):
	if len(packet) < 10:
		return None
	return packet[4:10]

def binToHexStr(binmac):
	return "".join(["%02x" % ord(i) for i in binmac])

# checks if packet is a broadcast packet
def isBroadcast(packet):
	binmac = getDstMacFromPkt(packet)
	# normal broadcast
	if binmac == '\xff\xff\xff\xff\xff\xff':
		return True
	# v6 multicast
	if binmac.startswith('\x33\x33'):
		return True
	return False

