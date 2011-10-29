#!/usr/bin/python
# -*- coding: utf-8 -*-

# TODO
#	Reconnecting to IRC-Server
#	Complete switched networks
#	Reduce debug output / add good output
#	For more security use packet id + srcnick as key for fragmented packages

from conf import *
import pytap
from pytap import TapDevice
import select
import time
import irclib
import commands
import re
import base64
import random

dev = None
headerlen = 1 + 5 + 1 # flag + number + whitespace
packets = {}

def getMacFromIf(iface):
	mac = commands.getoutput("/sbin/ifconfig %s|grep %s|egrep -o '([a-fA-F0-9]{2}(:|.)){6}'" % (iface, iface))
	print "Debug: %s has mac address %s" % (iface, mac)
	return mac

def getDstMacFromPkt(packet):
	if len(packet) < 10:
		return None
	return packet[4:10]

def binToHexStr(binmac):
	return "".join(["%02x" % ord(i) for i in binmac])

def isBroadcast(packet):
	binmac = getDstMacFromPkt(packet)
	# normal broadcast
	if binmac == '\xff\xff\xff\xff\xff\xff':
		return True
	# v6 multicast
	if binmac.startswith('\x33\x33'):
		return True
	return False

def sendToIRC(dev, server):
	msg = dev.read()
	oldencmsg = encmsg = base64.encodestring(msg).replace("\n", "")
	slices = []
	encmsglen = ircmsglen-headerlen
	msgid = "%05d" % random.randint(0, 99999)
	while len(encmsg) > encmsglen:
		slices.append(encmsg[:encmsglen])
		encmsg = encmsg[encmsglen:]
	slices.append(encmsg)
	
	# HUB or SWITCH?
	if mode == "SWITCH" and not isBroadcast(package):
		target = "VPN-%s" % (binToHexStr(getDstMacFromPkt(packet)),)
	else:
		target = broadcastchan
	
	if len(slices) == 0:
		print "DEBUG: EMPTY PACKAGE FROM DEV?"
	elif len(slices) == 1:
		print "Debug: Sending oneliner to dev"
		server.privmsg(target, "o%s %s" % (msgid, slices[0]))
	else:
		print "Debug: Sending fragmented package to dev"
		print " ---- COMPLETE MESSAGE BEFORE SLICES ---- "
		print oldencmsg
		print " ---- SLICES SLICES SLICES ---- "
		print "\n".join(slices)
		print " ---- SLICES SLICES SLICES ---- "
		server.privmsg(target, "b%s %s" % (msgid, slices.pop(0)))
		while len(slices) > 1:
			server.privmsg(target, "c%s %s" % (msgid, slices.pop(0)))
		server.privmsg(target, "e%s %s" % (msgid, slices.pop(0)))

def sendToDev(dev, server, isBroadcast, c, e):
	parsed = pkgre.match(e.arguments()[0])
	if not parsed:
		print "message could not be parsed", e.arguments()[0]
		return
	(flag, msgid, basemsg) = parsed.groups()
	print "flag: %s msgid: %s msg: %s" % (flag, msgid, basemsg)
	try:
		msgid = int(msgid)
	except ValueError:
		print "Debug: messageid was not a number"
		return
	if not ignoreNonMacUser:
		# FIXME: ignore the non prefix-mac user
		if not nickre.match():
			print "is not allowed in our network"
	print e.arguments(), irclib.nm_to_n(e.source()), e.target()
	if flag == "o":
		# oneliner!
		print "Debug: Writing onliner to dev"
		try:
			msg = base64.decodestring(basemsg)
		except base64.binascii.Error, e:
			print "Debug: Error decoding base64 irc message (%s)" % e
			return
		#FIXME if packetAllowed(, , chan)
		dev.write(msg)
	elif flag == 'b':
		if packets.has_key(msgid):
			print "Warning: Overwriting lost package with id %s" % msgid
		packets[msgid] = basemsg
	elif flag in ('c', 'e'):
		if not packets.has_key(msgid):
			print "Error: Continue package has no matching entry in packets, discarding!"
		else:
			packets[msgid] += basemsg
			if flag == 'e':
				arrmsg = packets[msgid]
				del(packets[msgid])
				try:
					print "arrmsg is", arrmsg.replace("\n", "\n\n\n")
					msg = base64.decodestring(arrmsg)
				except base64.binascii.Error, e:
					print "Debug: Error decoding base64 irc message (%s)" % e
					return
				print "Debug: writing fragmented package to dev"
				print binToHexStr(msg)
				dev.write(msg)
	#print "GOT in %s (broadcast %s) from %s msg %s" (e.target(), isBroadcast, irclib.nm_to_n(e.source()), e.arguments()[0])

def packetAllowed(src, nick, packet):
	if not acceptNonMatchingMac:
		# check if user-mac == packetmac
		# FIXME if not getDstMacFromPkt(packet) == 
		pass
	# FIXME: Maybe move nick check to here
	if mode != "HUB" and strictSwichedNetwork:
		if src.startswith("#"): # its a channel
			return False
	return True

def startup():
	# setup the tap device
	dev = TapDevice(pytap.IFF_TAP)
	dev.ifconfig(address=ip, netmask=netmask)
	if gateway != "":
		print "Setting default route %s" % gateway
		os.sys("route add default gw %s")
	
	# setup IRC foo
	ircnick = nickPrefix + getMacFromIf(dev.name).replace(":", "")
	print "Debug: Connectiong to %s as %s" % (ircserver, ircnick)
	
	irc = irclib.IRC()
	irc.add_global_handler("privmsg", lambda c, e: sendToDev(dev, server, False, c, e), -20)
	irc.add_global_handler("pubmsg",  lambda c, e: sendToDev(dev, server, True,  c, e), -20)
	server = irc.server()
	server.connect(ircserver[0], ircserver[1], ircnick)
	server.join(broadcastchan)
	
	try:
		while True:
			sockets = [dev.__fd__]
			# get private irc sockets :)
			sockets.extend(map(lambda x: x._get_socket(), irc.connections))
			sockets = filter(lambda x: x != None, sockets)
			print "sockets", sockets
			(readFDs, _, _) = select.select(sockets, [], [])
			for readFD in readFDs:
				print "EVENT BY", readFD
				if readFD == dev.__fd__:
					sendToIRC(dev, server)
				else:
					print "IRC event"
					irc.process_once(0.1)
	except KeyboardInterrupt:
		pass
	
	print "Shutting down!"
	server.quit("RST")

if __name__ == '__main__':
	startup()
