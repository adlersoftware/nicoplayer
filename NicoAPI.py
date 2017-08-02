#!/usr/bin/python3
# -*- coding: utf-8 -*-

# "videoid - yyyymmddhhnnss.xml"のファイル名でコメントをダウンロードします。
# "nico_cookie.dump"へクッキー情報を保存します。
# "watchdata.json"へ動画情報（Unicodeエスケープされた）を保存します。
# "watchdata_decode.json"へ動画情報（Unicodeエスケープ解除）を保存します。
# "watchdata_pretty.json"へ動画情報（整形済み）を保存します。

# 参考URL
# http://qiita.com/tor4kichi/items/2f19f533763fe6e3e479


import codecs
import requests
import pickle
from UnescapeUnicode import UnescapeUnicode
from copy import deepcopy
from os import (getcwd, chdir)
from os.path import (abspath, dirname)
from os.path import isfile
from json import loads
from pprint import pprint
from urllib.parse import unquote_plus
from bs4 import BeautifulSoup
from html import unescape
from re import compile
from datetime import datetime


class NicoNico(object):

    def __init__(self):
        self.__headers = {
            'User-Agent':'Mozilla/5.0 (Windows; U; Windows NT 6.1; ja; rv:1.9.1.5) Gecko/20091102 Firefox/3.5.5 (.NET CLR 3.5.30729)',
            'Accept': '*/*',
            'Accept-Language': 'ja,en-us;q=0.7,en;q=0.3',
            'Accept-Charset': 'UTF-8,*',
            'Connection': 'keep-alive',
            'Keep-Alive': '300',
            'Cookie': '; '
        }
        self.__cookie_filename = "nico_cookie.dump"
        self.__watchdata_dic = []
        self.__cookie = None
        self.__videopage = None


    def login(self, mail, password):
        print("===ログイン処理===")
        post_dict = {
            'mail_tel' : mail,
            'password' : password
        }
        self.__headers['Referer']='http://www.nicovideo.jp/'
        self.__headers['Content-type']='application/x-www-form-urlencoded'
        s = requests.session()
        r = s.post(
                'https://secure.nicovideo.jp/secure/login?site=niconico',
                data = post_dict,
                allow_redirects = False     # リダイレクトをなしにしないとクッキーを取得できない
            )
        self.print_response(r)
        if r.status_code != 302:
            raise FailedLoginError()

        self.__cookie = r.cookies
        pickle.dump(self.__cookie, open(self.__cookie_filename, "wb"))

    # クッキーファイルがあればロード、ないしログイン
    def loadCookieOrLogin(self, mail, password):
        if isfile(self.__cookie_filename):
            self.__cookie = pickle.load(open(self.__cookie_filename, "rb"))
        else:
            self.login(mail, password)

    # HTTPレスポンスのヘッダをプリント
    def print_response(self, r):
        print("HTTP/%1.1f %s %s" % (r.raw.version/10, r.status_code, r.reason))
        print("headers=")
        pprint(r.headers)

    # 動画情報を取得し、辞書として保持
    def load_videoinfo(self, videoid):
        print("===動画情報取得処理===")
        r = requests.get(
            'http://www.nicovideo.jp/watch/%s' % videoid,
            cookies = self.__cookie
        )
        self.print_response(r)
        if r.status_code != 200:
            raise FailedVideoInfoDownloadError()

        self.__videopage = r.text
        soup = BeautifulSoup(self.__videopage, 'html.parser')
        # html = soup.prettify("utf-8")
        # with open('%s.html' % videoid, "wb") as file:
        #     file.write(html)
        watchdata_tag = soup.find('div', id='js-initial-watch-data')
        watchdata = watchdata_tag['data-api-data']
        # デバッグのためファイル保存
        f = open('watchdata.json','w')
        f.write(watchdata)
        f.close()
        uu = UnescapeUnicode('watchdata')
        unidata = uu.unescape_unicode(watchdata)
        self.__watchdata_dic = uu.pretty_unicode(unidata)

    # 動画の長さを1/100秒に変換して取得（公式動画のみ）
    def get_video_length(self):
        if self.__watchdata_dic['video']['dmcInfo'] != None:
            return int(self.__watchdata_dic['video']['dmcInfo']['video']['length_seconds']) * 100
        
    # 動画情報のコピーを返す（外部から書き換えてほしくないので）
    def get_videoinfo_copy(self):
        return deepcopy(self.__watchdata_dic)

    # 取得した動画情報でコメントをダウンロード
    def get_comment(self):
        print("===コメント取得処理===")
        if self.__watchdata_dic['video']['dmcInfo'] != None:
            thread_id = self.__watchdata_dic['video']['dmcInfo']['thread']['thread_id']
            needs_key = self.__watchdata_dic['video']['dmcInfo']['thread']['thread_key_required']
            user_id = self.__watchdata_dic['video']['dmcInfo']['user']['user_id']
        else:
            thread_id = self.__watchdata_dic['thread']['ids']['default']
            needs_key = False
            user_id = 0
        message_server = self.__watchdata_dic['thread']['serverUrl']
        print("thread_id=", thread_id)
        print("message_server=", message_server)
        print("needs_key=", str(needs_key))
        print("user_id=", user_id)

        self.__headers['Content-type'] = 'text/xml'
        if needs_key:
            # 公式動画
            r = requests.get(
                'http://flapi.nicovideo.jp/api/getthreadkey?thread=%s' % thread_id,
                cookies = self.__cookie
            )
            self.print_response(r)
            body = r.text   # thread_key,force_184の取得
            print(body)

            r = requests.get(
                '%sthread?thread=%s&version=%s&res_from=%s&scores=%s&user_id=%s&%s'
                % (message_server, thread_id, '20061206', '-1000', '1', user_id, body),
                cookies = self.__cookie
            )
        else:
            # 一般の動画
            r = requests.get(
                '%sthread?thread=%s&version=%s&res_from=%s&scores=%s'
                % (message_server, thread_id, '20061206', '-1000', '1'),
                cookies = self.__cookie
            )
        self.print_response(r)
        if r.status_code != 200:
            raise FailedCommentDownloadError()
        body = r.text

        return body



class FailedLoginError(Exception):
    pass

class FailedVideoInfoDownloadError(Exception):
    pass

class FailedCommentDownloadError(Exception):
    pass

# シンフォギアAXZ1話
# "so31521243"
if __name__ == '__main__':
    chdir(dirname(abspath(__file__)))
    mail = ""
    password = ""
    videoid = "sm9"
    nico = NicoNico()
    nico.loadCookieOrLogin(mail, password)
    #nico.load_videoinfo(videoid)
    # comment_xml = nico.get_comment()
    # f = codecs.open('%s - %s.xml' % (videoid, datetime.now().strftime('%Y%m%d%H%M%S')), 'w', "utf-8")
    # f.write(comment_xml)
    # f.close()
    #print(nico.get_video_length())
