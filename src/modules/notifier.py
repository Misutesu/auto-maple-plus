import os
import threading
import time
from datetime import datetime

import requests
import pytz
from discord import SyncWebhook, File

import src.common.config as config
import src.modules.automation as automation
from src.gui.automation.main import AutomationParams
from src.gui.notifier_settings.main import NotifSettings
from src.gui.notifier_settings.notification_settings import NotificationSetting


class QmsgNotifier:
    qq = "2092007963"
    
    url = "https://qmsg.zendee.cn/jsend/cfc13357e27a55a34e744303a77d84aa"
    # token cfc13357e27a55a34e744303a77d84aa

    def __init__(self, token):
        self.token = token

    def send(self, message):
        data = {"msg": message, "qq": self.qq}
        response = requests.post(self.url, json=data)
        if response.json()["code"] != 200:
            print(f"QmsgNotifier Error : {response.text}")


class PushPlusNotifier:
    url = "https://www.pushplus.plus/send/"
    # token 57ecaa3c74ad4fde9d33b8e597314ba9

    def __init__(self, token):
        self.token = token

    def send(self, message):
        if self is None:
            print("PushPlusNotifier Error : token null")
            return
        data = {"token": self.token, "title": "AutoMaple", "content": message}
        response = requests.post(self.url, json=data)
        if response.json()["code"] != 200:
            print(f"PushPlusNotifier Error : {response.text}")

    def send_file(self, file_path):
        if self is None:
            print("PushPlusNotifier Error : token null")
            return
        data = {
            "token": self.token,
            "title": "AutoMaple",
            "content": "暂不支持图片:" + file_path,
        }
        response = requests.post(self.url, json=data)
        if response.json()["code"] != 200:
            print(f"PushPlusNotifier Error : {response.text}")


class Notifier:
    def __init__(self):
        self.ready = False
        self.thread = threading.Thread(target=self._main)
        self.thread.daemon = True

    def start(self):
        """Starts this Notifier's thread."""
        print("\n[~] Started notifier")
        self.thread.start()

    def _main(self):
        self.ready = True
        self.lastAlertTimeDict = {}
        self.watchlist = {}
        try:
            config.qmsg = QmsgNotifier(
                NotifSettings("Notifier Settings").get("QmsgKey")
            )
            config.pushPlus = PushPlusNotifier(
                NotifSettings("Notifier Settings").get("PushPlusToken")
            )
            config.webhook = SyncWebhook.from_url(
                NotifSettings("Notifier Settings").get("WebhookURL")
            )
            user_timezone = pytz.timezone(
                NotifSettings("Notifier Settings").get("Timezone")
            )
        except Exception as e:
            print(e)
            print("Discord Webhook URL or Timezone invalid, notifier disabled")
            return
        flaglist = [
            "cursed_rune",
            "no_damage_numbers",
            "map_overcrowded",
            "lie_detector_failed",
            "game_disconnected",
            "character_dead",
            "chatbox_msg",
            "stuck_in_cs",
            "char_in_town",
            "player_stuck",
            "especia_portal",
        ]

        while True:
            # try except to prevent crashing when user is editing while trying to load configs
            # get user settings
            try:
                suppressAll = NotificationSetting("Notification Settings").get(
                    "Suppress_All"
                )
                alertForBotRunning = NotificationSetting("Notification Settings").get(
                    "bot_running_toggle"
                )
                for i in flaglist:
                    self.watchlist[i] = {
                        "toggle": NotificationSetting("Notification Settings").get(
                            i + "_toggle"
                        ),
                        "msg": NotificationSetting("Notification Settings").get(
                            i + "_notice"
                        ),
                    }
                reviveWhenDead = AutomationParams("Automation Settings").get(
                    "revive_when_dead_toggle"
                )
                pauseInTown = AutomationParams("Automation Settings").get(
                    "auto_pause_in_town_toggle"
                )
            except:
                pass

            if config.enabled and suppressAll != True:
                if alertForBotRunning:
                    alertTextForRunning = NotificationSetting(
                        "Notification Settings"
                    ).get("bot_running_notice")
                    self.alert(
                        config.webhook,
                        user_timezone,
                        self.lastAlertTimeDict,
                        alertTextForRunning,
                        alertCD=300,
                    )
                for item in self.watchlist:
                    if getattr(config, item) == True:
                        if self.watchlist[item]["toggle"] == True:
                            alertSent = self.alert(
                                config.webhook,
                                user_timezone,
                                self.lastAlertTimeDict,
                                self.watchlist[item]["msg"],
                            )
                            if item == "character_dead" and reviveWhenDead:
                                # automation.autoRevive()
                                config.listener.toggle_enabled()
                            if item == "char_in_town" and pauseInTown:
                                config.listener.toggle_enabled()
            time.sleep(0.5)

    def alert(self, target, timezone, alertDict, alertText: str, alertCD=60):
        """
        Core notification sending engine that manages send frequency
        """
        alertText = str(alertText)

        if alertText in alertDict:
            lastAlertSeconds = (datetime.now() - alertDict[alertText]).total_seconds()
            if lastAlertSeconds > alertCD:
                alertDict[alertText] = datetime.now()
                alertTextandTime = (
                    alertText
                    + " at "
                    + (timezone.localize(datetime.now())).strftime("%d/%m/%Y %H:%M:%S")
                )
                target.send(content="@wujq " + alertTextandTime)
                config.pushPlus.send(alertTextandTime)
                config.qmsg.send(alertTextandTime)
                return True
            else:
                # print("[ALERT  ] Alert CD {:.2f}s: ".format(alertCD - lastAlertSeconds) +alertText)
                return False
        else:
            alertDict[alertText] = datetime.now()
            alertTextandTime = (
                alertText
                + " at "
                + (timezone.localize(datetime.now())).strftime("%d/%m/%Y %H:%M:%S")
            )
            target.send(content="@wujq " + alertTextandTime)
            config.pushPlus.send(alertTextandTime)
            config.qmsg.send(alertTextandTime)
            print("[ALERT  ] Alert sent: " + alertText)
            return True

    def ping(self, name, volume=0.5):
        """A quick notification for non-dangerous events."""

        # self.mixer.load(get_alert_path(name))
        # self.mixer.set_volume(volume)
        # self.mixer.play()

    def alertFile(self, target, image):
        path = ".\\" + image
        target.send(file=File(path))
        config.pushPlus.send_file(path)
        config.qmsg.send("不支持发送文件")

