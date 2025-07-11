"""The central program that ties all the modules together."""

import time
from src.modules.bot import Bot
from src.modules.capture_ws import Capture
from src.modules.notifier import Notifier
from src.modules.watcher import Watcher
from src.modules.listener import Listener
from src.modules.gui import GUI


bot = Bot()
capture = Capture()
notifier = Notifier()
listener = Listener()
watcher = Watcher()

bot.start()
while not bot.ready:
    time.sleep(0.01)

capture.start()
while not capture.ready:
    time.sleep(0.01)

notifier.start()
while not notifier.ready:
    time.sleep(0.01)

watcher.start()
while not watcher.ready:
    time.sleep(0.01)      

listener.start()
while not listener.ready:
    time.sleep(0.01)

print('\n[~] Successfully initialized Auto Maple')

gui = GUI()
gui.start()
