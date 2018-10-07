# -*- coding: utf-8 -*-
from wox import Wox, WoxAPI
import re
import difflib
import os
import sys
import glob
import subprocess
import json
import urllib
import urllib.request
import requests
import codecs
from bs4 import BeautifulSoup
import time


class Steamlauncher(Wox):
    def __init__(self):
        conf = Steamlauncher.load_conf()
        self.plugin_conf = conf[0]
        self.steam_dir = conf[1]
        self.steam_apps_dir = conf[2]

        self.game_list = Steamlauncher.load_steam_library(self.steam_apps_dir)
        super(Steamlauncher, self).__init__()

    @staticmethod
    def load_conf():
        """
        load configuration and return (steam_dir, steamapps_dir)
        """

        with codecs.open('./config.json', 'r', 'utf-8') as f:
            plugin_conf = json.load(f)

        if not plugin_conf["steam_dir"]:
            steam_dir = None
        else:
            if os.path.isdir(plugin_conf['steam_dir']) and os.path.isfile(os.path.join(plugin_conf['steam_dir'], 'steam.exe')):
                steam_dir = plugin_conf["steam_dir"]
            else:
                steam_dir = False

        if not plugin_conf["steamapps_dir"]:
            steam_apps_dir = None
        elif not os.path.isdir(plugin_conf['steamapps_dir']):
            steam_apps_dir = False
        else:
            steam_apps_dir = plugin_conf["steamapps_dir"]

        return plugin_conf, steam_dir, steam_apps_dir

    @staticmethod
    def load_steam_library(steam_apps_dir):
        game_list = []
        if os.path.exists('./cache.json'):
            with codecs.open('./cache.json', 'r', 'utf-8') as f:
                game_list = json.load(f)
        else:
            game_list = Steamlauncher.save_steam_library(steam_apps_dir)
        return game_list

    @staticmethod
    def save_steam_library(steam_apps_dir):
        game_list = Steamlauncher.query_steam_library(steam_apps_dir)
        with codecs.open('./cache.json', 'w', 'utf-8') as f:
            json.dump(game_list, f, indent=4)
        return game_list

    @staticmethod
    def query_steam_library(steam_apps_dir):
        """
        Load steam library from the steam apps dir.
        return None if the steam apps dir is invalid. Otherwise return list of: {gameid, gameTitle, gameIcon}
        """
        if steam_apps_dir and os.path.isdir(steam_apps_dir):
            game_list = []
            acf_list = glob.glob(os.path.join(
                steam_apps_dir, 'appmanifest_*.acf'))
            if not acf_list:
                return

            for acf_file in acf_list:
                game_id = re.search(r"[0-9]+.acf", acf_file)
                game_id = game_id.group().strip(".acf")
                with codecs.open(acf_file, 'r', 'utf-8') as f:
                    for line in f:
                        if line.find("name") >= 0:
                            game_title = line.strip('\n')
                            game_title = game_title[9:].strip('"')
                            break

                game_icon_path = os.path.join('./icon/', game_id + '.jpg')
                if not os.path.isfile(game_icon_path):
                    game_icon_path = Steamlauncher.get_game_icon(game_id)

                game_list.append(
                    {'gameId': game_id, 'gameTitle': game_title, 'gameIcon': game_icon_path})
        return game_list

    @staticmethod
    def get_game_icon(game_id):
        """
        Download and return the game icon for game_id
        """
        try:
            url = 'https://steamdb.info/app/{}/'.format(game_id)
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:47.0) Gecko/20100101 Firefox/47.0"}
            r = requests.get(url, headers=headers)
            soup = BeautifulSoup(r.text, "html.parser")
            data = soup.find('img', attrs={'class': 'app-icon avatar'})
            img = data.attrs['src']
            urllib.request.urlretrieve(img, './icon/' + game_id + '.jpg')
            return os.path.join('./icon/', game_id + '.jpg')
        except Exception:
            return './icon/missing.png'

    def query(self, query):
        result = []
        steamDir = self.steam_dir
        steamappsDir = self.steam_apps_dir
        gameList = self.game_list

        search_query = query.upper()

        if steamappsDir and search_query in '/STEAM':
            result.append({
                "Title": "Reload steam library",
                "SubTitle": "Press enter to reload the steam library to the plugin",
                "IcoPath": 'icon/launcher.png',
                "JsonRPCAction": {
                    "method": "reloadLibrary",
                    "parameters": [steamappsDir],
                    "dontHideAfterAction": True
                }
            })

        if steamDir and steamappsDir:
            for line in gameList:
                if search_query in line['gameTitle'].upper():
                    result.append({
                        "Title": line['gameTitle'],
                        "SubTitle": str(line['gameId']),
                        "IcoPath": line['gameIcon'],
                        "JsonRPCAction": {
                            "method": "launchGame",
                            "parameters": [line['gameId']],
                            "dontHideAfterAction": False
                        }
                    })
            return result

        if steamDir is None:
            result.append({
                "Title": "Can't find Steam Directory.",
                "SubTitle": "Please add Steam Path:'{}'".format(query),
                "IcoPath": "icon/launcher.png",
                "JsonRPCAction": {
                    "method": "saveSteamDirectory",
                    "parameters": [query],
                    "dontHideAfterAction": True
                }
            })

        if steamappsDir is None:
            result.append({
                "Title": "Can't find Steamapps Directory.",
                "SubTitle": "Please add Steamapps Path:'{}'".format(query),
                "IcoPath": "icon/launcher.png",
                "JsonRPCAction": {
                    "method": "saveSteamAppsDirectory",
                    "parameters": [query],
                    "dontHideAfterAction": True
                }
            })

        if steamDir is False:
            result.append({
                "Title": "Steam path is invalid.",
                "SubTitle": "Try add Steam Path again:'{}'".format(query),
                "IcoPath": "icon/launcher.png",
                "JsonRPCAction": {
                    "method": "saveSteamDirectory",
                    "parameters": [query],
                    "dontHideAfterAction": True
                }
            })

        if steamappsDir is False:
            result.append({
                "Title": "Steamapps path is invalid.",
                "SubTitle": "Try add Steamapps Path again:'{}'".format(query),
                "IcoPath": "icon/launcher.png",
                "JsonRPCAction": {
                    "method": "saveSteamAppsDirectory",
                    "parameters": [query],
                    "dontHideAfterAction": True
                }
            })
        return result

    def saveSteamDirectory(self, path):
        plugin_conf = self.plugin_conf
        plugin_conf['steam_dir'] = re.sub(
            r'[/\\]+', '/', path.rstrip('/\\')) + '/'
        self.steam_dir = plugin_conf['steam_dir']
        with codecs.open('./config.json', 'w', 'utf-8') as f:
            json.dump(plugin_conf, f, indent=4)
        WoxAPI.show_msg("Steam directory path has been saved",
                        plugin_conf['steam_dir'])

    def saveSteamAppsDirectory(self, path):
        plugin_conf = self.plugin_conf
        plugin_conf['steamapps_dir'] = re.sub(
            r'[/\\]+', '/', path.rstrip('/\\')) + '/'
        self.steam_apps_dir = plugin_conf['steamapps_dir']
        with codecs.open('./config.json', 'w', 'utf-8') as f:
            json.dump(plugin_conf, f, indent=4)
        WoxAPI.show_msg("Steam apps directory path has been saved",
                        plugin_conf['steamapps_dir'])

    def reloadLibrary(self, steam_apps_dir):
        self.game_list = Steamlauncher.save_steam_library(steam_apps_dir)
        WoxAPI.show_msg("Steam library has been updated", steam_apps_dir)

    def launchGame(self, game_id):
        subprocess.Popen(['{}steam.exe'.format(
            self.steam_dir), '-applaunch', game_id])


if __name__ == "__main__":
    Steamlauncher()
