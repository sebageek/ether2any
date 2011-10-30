#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
sys.path.append("../../../")

from ether2any import Ether2Any

from conf import Conf
import time
import irclib
import re
import base64
import random
import logging
import subprocess
from ether2any.helper import getDstMacFromPkt, isBroadcast, binToHexStr

# TODO
#	replace base64 with something better
#	write switching part

class IrcVPN(Ether2Any):
	headerlen = 1 + 5 + 1 # flag + number + whitespace
	pkgre = re.compile("^([a-zA-Z])(\d{5}) (.*)$")
	
	def __init__(self):
		Ether2Any.__init__(self, tap=True)
		self.irclog = self.setupLogging("IrcVPN")
		self.irclog.setLevel(logging.WARN)
		
		# === Load config values ===
		network = Conf.get("network", {'mtu': 1500})
		self.ircmsglen = Conf.get("ircmsglen", 400)
		self.ircserver = Conf.get("ircserver")
		self.broadcastchan = Conf.get("broadcastchan")
		self.nickPrefix = Conf.get("nickPrefix", "VPN")
		self.postConnectCmd = Conf.get("postConnectCmd", None)
		self.voiceWord = Conf.get("voicebot", None)
		if self.voiceWord:
			self.voiceWord = self.voiceWord.get("voiceword", None)
		self.mode = Conf.get("mode", "HUB")
		self.ignoreNonMacUser = Conf.get("ignoreNonMacUser", True)
		self.acceptNonMatchingMac = Conf.get("acceptNonMatchingMac", True)
		self.strictSwichedNetwork = Conf.get("strictSwichedNetwork", False)
		
		if self.mode not in ("HUB", "SWITCH"):
			raise ValueError("mode needs to be either HUB or SWITCH")
		self.irclog.info("Starting the IRC Public Network")
		self.packets = {}
		self._setupIrc()
		self.nickre = re.compile("^%s[a-fA-F0-9]{12}$" % (self.nickPrefix,))
		self.dev.ifconfig(**network)
		self.dev.up()
	
	def sendToNet(self, packet):
		# split message so that it's not longer than ircmsglen
		oldencmsg = encmsg = base64.b64encode(packet).strip("\n")
		slices = []
		encmsglen = self.ircmsglen-self.headerlen
		msgid = "%05d" % random.randint(0, 99999)
		while len(encmsg) > encmsglen:
			slices.append(encmsg[:encmsglen])
			encmsg = encmsg[encmsglen:]
		slices.append(encmsg)
		
		# HUB or SWITCH?
		if self.mode == "SWITCH" and not isBroadcast(packet):
			target = "%s%s" % (self.nickPrefix, binToHexStr(getDstMacFromPkt(packet)),)
		else:
			target = self.broadcastchan
		self.irclog.info("Sending %d packet(s) (total len %d) to %s" % (len(slices), len(oldencmsg), target))
		
		if len(slices) == 0:
			self.irclog.error("Got EMPTY packet from dev!")
		elif len(slices) == 1:
			# send in one line (o)
			self.server.privmsg(target, "o%s %s" % (msgid, slices[0]))
		else:
			# send fragmented (b, c, e)
			self.server.privmsg(target, "b%s %s" % (msgid, slices.pop(0)))
			while len(slices) > 1:
				self.server.privmsg(target, "c%s %s" % (msgid, slices.pop(0)))
			self.server.privmsg(target, "e%s %s" % (msgid, slices.pop(0)))
	
	def sendToDev(self, socket):
		# proc one irc event
		self.irclog.debug("Processing irc event")
		self.irc.process_once(0.1)
	
	def sendToDevIrcCallback(self, isBroadcast, c, e):
		parsed = self.pkgre.match(e.arguments()[0])
		nick = irclib.nm_to_n(e.source())
		target = e.target()
		if not parsed:
			self.irclog.debug("irc-input: Message could not be parsed (\"%s\")" % (e.arguments()[0],))
			return
		(flag, msgid, basemsg) = parsed.groups()
		self.irclog.debug("irc-input: source: %s target: %s flag: %s msgid: %s msg: %s" % (nick, target, flag, msgid, basemsg))
		if self.ignoreNonMacUser:
			if not self.nickre.match(nick):
				self.irclog.debug("%s is not allowed in our network" % nick)
				return
		if flag == "o":
			# oneliner!
			try:
				msg = base64.b64decode(basemsg)
			except base64.binascii.Error, e:
				self.irclog.warning("Error decoding base64 irc message (%s)" % e)
				return
			if self.packetAllowed(nick, target, msg):
				self.dev.write(msg)
		elif flag == 'b':
			if self.packets.has_key(msgid):
				self.irclog.warning("Overwriting lost package with id %s" % msgid)
			try:
				# we need to decode at least part of the ethernet header
				# choosing 64 chars at random (shouldn't break padding)
				partmsg = base64.b64decode(basemsg[:64])
				if len(partmsg) < 24:
					raise ValueError()
			except (base64.binascii.Error, ValueError):
				self.irclog.warning("Could not decode parted base64 message, discarding")
				return
			self.packets[msgid] = basemsg
		elif flag in ('c', 'e'):
			if not self.packets.has_key(msgid):
				self.irclog.warning("Continue package with id %d has no matching entry in packets, discarding!" % msgid)
			else:
				self.packets[msgid] += basemsg
				if flag == 'e':
					arrmsg = self.packets[msgid]
					del(self.packets[msgid])
					try:
						msg = base64.b64decode(arrmsg)
					except base64.binascii.Error, e:
						self.irclog.debug("Error decoding base64 irc message (%s)" % e)
						return
					if self.packetAllowed(nick, target, msg):
						self.dev.write(msg)
			self.irclog.debug("Packet written")
	
	def packetAllowed(self, nick, target, packet):
		if not self.acceptNonMatchingMac and not binToHexStr(getDstMacFromPkt(packet)) == nick[-12:]:
			return False
		if self.mode != "HUB" and self.strictSwichedNetwork:
			if target.startswith("#"): # its a channel
				return False
		return True
	
	def printNotice(self, c, e):
		self.irclog.info("NOTICE: %s %s" % (e.source(), e.arguments()[0]))
	
	def _setupIrc(self):
		ircnick = self.nickPrefix + self.dev.getMac().replace(":", "")
		
		self.irc = irclib.IRC()
		self.irc.add_global_handler("privmsg", lambda c, e: self.sendToDevIrcCallback(False, c, e), -20)
		self.irc.add_global_handler("pubmsg",  lambda c, e: self.sendToDevIrcCallback(True,  c, e), -20)
		self.irc.add_global_handler("privnotice",  self.printNotice, -20)
		self.server = self.irc.server()
		self.server.connect(self.ircserver[0], self.ircserver[1], ircnick)
		self.server.join(self.broadcastchan)
		if self.voiceWord:
			self.irclog.info("Sending voiceword to %s" % self.broadcastchan)
			self.server.privmsg(self.broadcastchan, self.voiceWord)
		
		# add sockets
		self.readSockets = map(lambda x: x._get_socket(), self.irc.connections)
		self.readSockets = filter(lambda x: x != None, self.readSockets)
		
		# execute post connect command
		if self.postConnectCmd:
			cmd = self.postConnectCmd
			if cmd.find("%s") >= 0:
				print cmd
				cmd = cmd % (self.dev.getName(),)
			subprocess.Popen(cmd, shell=True)
	
	def quit(self):
		self.server.quit("RST")

if __name__ == '__main__':
	ircvpn = IrcVPN()
	ircvpn.run()

