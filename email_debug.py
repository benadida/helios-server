import smtpd
import asyncore
server = smtpd.DebuggingServer(('127.0.0.1', 1025), None)
asyncore.loop()
