#!/usr/bin/python3
# -*- coding: utf-8 -*-


import sys
import json
import time
import threading
from os import (getcwd, chdir)
from os.path import (abspath, dirname, basename, isfile)
from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import *
from PyQt5.QtGui import (QColor, QPainter, QPalette, QBrush, QFont)
from Nicomment import Nicomment, NicommentMoving
import xml.etree.ElementTree as ET
import NicoAPI


class Nicoplayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.__before_time = 3*100  # 開始前の時間　1/100秒
        self.__videoid = ""
        self.__account_file = 'nico_account.json'

        self.setGeometry(100, 100, 1280, 640)
        self.setVideoTitle('')
        # ウィジェット
        self.video_widget = VideoWidget(self)
        self.video_widget.update_playTimeLabel(0)
        self.setCentralWidget(self.video_widget)
        self.comment_dock = QDockWidget("Comment", self)
        self.comment_dock.setWidget(CommentWidget(self))
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.comment_dock)
        # 背景を透明にする
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        self.__timer = TimerThread(self)
        self.__comment = CommentThread(self.__timer, self.video_widget, self.video_widget.seekbar)

    def start_play(self):
        if self.__videoid == '':
            QMessageBox.warning(self, "Nicoplayer", "コメントを取得してください")
        elif self.__timer.vpos() < self.__timer.playTime():
            # スレッドは一度しか起動できないため、新しくつくる
            vpos = self.__timer.vpos()
            playtime = self.__timer.playTime()
            self.__timer = TimerThread(self, vpos, playtime)
            commentlist = self.__comment.commentList()
            self.__comment = CommentThread(self.__timer, self.video_widget, self.video_widget.seekbar, commentlist)
            self.__timer.start()
            self.__comment.start()
            self.video_widget.playButton.setText("STOP")

    def stop_play(self):
        self.__timer.stop()
        self.__comment.stop()
        self.video_widget.playButton.setText("PLAY")

    def dump_mail_password(self, mail, password):
        json_dict = {
            'mail' : mail,
            'password' : password
        }
        f = open(self.__account_file, 'w')
        json.dump(json_dict, f)

    # 設定ファイルがあるならメールとパスワードを返す
    # ないならナルを返す
    def load_mail_password(self):
        mail = ''
        password = ''
        if isfile(self.__account_file):
            f = open(self.__account_file, 'r')
            json_dict = json.load(f)
            mail = json_dict['mail']
            password = json_dict['password']
        return (mail, password)
        
    # 動画IDからコメントを取得
    # 成功したらTrue, 失敗したらFalseを返す
    def load_comment(self, videoid):
        mail, password = self.load_mail_password()
        if mail == '':
            QMessageBox.warning(self, "Nicoplayer", "メニューの設定からアカウントを設定してください")
            return False
        try:
            nico = NicoAPI.NicoNico()
            nico.loadCookieOrLogin(mail, password)
            nico.load_videoinfo(videoid)
            comment_xml = nico.get_comment()
        except NicoAPI.FailedLoginError:
            QMessageBox.warning(self, "Nicoplayer", "ログインに失敗しました")
            return False
        except NicoAPI.FailedVideoInfoDownloadError:
            QMessageBox.warning(self, "Nicoplayer", "動画情報の取得に失敗しました")
            return False
        except NicoAPI.FailedCommentDownloadError:
            QMessageBox.warning(self, "Nicoplayer", "コメントの取得に失敗しました")
            return False
        else:
            self.__comment.parseComment(ET.fromstring(comment_xml))
            videoinfo = nico.get_videoinfo_copy()
            self.setVideoTitle(videoinfo['video']['title'])
            self.setPlayTime(self.videoinfoOrLastComment(nico.get_video_length()))
            self.__videoid = videoid
            return True

    # XMLファイルからコメント情報を読み込み
    # 成功したらTrue, 失敗したらFalseを返す
    def load_comment_from_xml(self):
        mail, password = self.load_mail_password()
        if mail == '':
            QMessageBox.warning(self, "Nicoplayer", "メニューの設定からアカウントを設定してください")
            return False
        fd = QFileDialog()
        fp = fd.getOpenFileName(self, 'コメントファイルの読込', dirname(abspath(__file__)), "XML File (*.xml)")
        if fp[0] == '':
            return False

        videoid = self.__comment.parseComment(ET.parse(fp[0]))
        print(videoid)
        # 一般の動画でもhttp://www.nicovideo.jp/watch/threadid で動画情報を取得できる　ので、そうする
        try:
            nico = NicoAPI.NicoNico()
            nico.loadCookieOrLogin(mail, password)
            nico.load_videoinfo(videoid)
        except NicoAPI.FailedLoginError:
            QMessageBox.warning(self, "Nicoplayer", "ログインに失敗しました")
            return False
        except NicoAPI.FailedVideoInfoDownloadError:
            QMessageBox.warning(self, "Nicoplayer", "動画情報の取得に失敗しました")
            return False
        else:
            videoinfo = nico.get_videoinfo_copy()
            self.setVideoTitle(videoinfo['video']['title'])
            # 一般の動画だと、dmcInfoがNoneになるので、最後のコメントを動画の長さとする
            self.setPlayTime(self.videoinfoOrLastComment(nico.get_video_length()))
            self.__videoid = videoinfo['video']['id']
            return True

    # 動画情報の再生時間ないしコメントの動画位置を取得
    def videoinfoOrLastComment(self, info):
        if info != None:
            return info
        else:
            return self.__comment.getVposOfLastComment()

    def setVideoTitle(self, title):
        if title == '':
            self.setWindowTitle('Nicoplayer')
        else:
            self.setWindowTitle('Nicoplayer - %s' % title)
            print(title)
        
    # 再生時間をラベル、シークバーに適用
    def setPlayTime(self, playTime):
        print('再生時間を適用:%s' % playTime)
        self.__timer.setVpos(-self.__before_time)
        self.__timer.setPlayTime(playTime)
        self.video_widget.update_timerLabel(-self.__before_time)
        self.video_widget.update_playTimeLabel(self.__timer.playTime())
        self.video_widget.seekbar.setRange(-self.__before_time, self.__timer.playTime())
        self.video_widget.seekbar.setValue(-self.__before_time)
        self.video_widget.seekbar.setEnabled(True)

    # 再生と停止を制御
    def playButton_clicked(self):
        if self.__timer.isRunning():
            self.stop_play()
        else:
            self.start_play()

    # シーク位置が範囲内ならばストップ、ラベルを更新
    def seek_to(self, vpos):
        if vpos >= -self.__before_time and vpos <= self.__timer.playTime():
            self.__timer.setVpos(vpos)
            self.video_widget.update_timerLabel(self.__timer.vpos())
            print('シーク:%s' % self.__timer.vpos())

    def get_table_data(self):
        return self.__comment.get_table_data()


# 時間をカウントするためのスレッド
class TimerThread(threading.Thread):
    def __init__(self, main_window, vpos = 0, play_time = 0):
        threading.Thread.__init__(self)
        self.__running = False
        self.__vpos = vpos
        self.__play_time = play_time
        self.__main_window = main_window
 
    def setVpos(self, vpos):
        self.__vpos = vpos

    def vpos(self):
        return self.__vpos

    def setPlayTime(self, play_time):
        self.__play_time = play_time

    def playTime(self):
        return self.__play_time

    def isRunning(self):
        return self.__running

    def run(self):
        self.__running = True
        self.__start_vpos = self.__vpos
        self.__start_time = time.time()
        while self.__running and self.__vpos <= self.__play_time:
            time.sleep(0.008)
            self.__vpos = int(self.__start_vpos + (time.time() - self.__start_time) * 100)
        self.__main_window.stop_play()

    def stop(self):
        self.__running = False


# コメントを動かすためのスレッド
class CommentThread(threading.Thread):
    def __init__(self, timer, video_widget, seekbar, comment_list = []):
        threading.Thread.__init__(self)
        self.__running = False
        self.__comment_list = comment_list
        self.__timer = timer
        self.__video_widget = video_widget
        self.__seekbar = seekbar
        self.__index = 0    # コメントを探索するときのインデックス

    def commentList(self):
        return self.__comment_list

    def isRunning(self):
        return self.__running

    def run(self):
        self.__running = True
        while self.__running:
            time.sleep(0.008)
            self.__seekbar.setValue(self.__timer.vpos())
            self.comment_to_moving()
            self.__video_widget.move_comment()
            self.__video_widget.update_timerLabel(self.__timer.vpos())
            self.__video_widget.update()       # ウィンドウの再描画イベントを呼ぶ

    def stop(self):
        self.__running = False

    # XML形式からコメントをパース
    # thread_idを返す
    def parseComment(self, root):
        elelist = root.findall('.//chat')
        for ele in elelist:
            if ele.text == '' or ele.text == None:
                continue
            self.__comment_list.append(Nicomment(ele.get('vpos', 0), ele.text))
        self.__comment_list.sort()
        thread_elm = root.find('.//thread')
        return thread_elm.get('thread', '')

    # 最後のコメントの動画位置を取得
    def getVposOfLastComment(self):
        return self.__comment_list[-1].vpos()

    # コメントテーブルに設定するためのデータを返す
    def get_table_data(self):
        table_data = []
        for c in self.__comment_list:
            table_data.append(c.getList())
        return table_data

    # 再生時間が同じコメントを表示リストへ追加します
    def comment_to_moving(self):
        for i in range(self.__index, len(self.__comment_list)):
            comment = self.__comment_list[i]
            if comment <= self.__timer.vpos():
                self.__video_widget.add_comment(comment)
            else:
                self.__index = i
                break
        # for comment in self.__comment_list:
        #     if comment.isEqualVpos(self.__timer.vpos()):
        #         self.__video_widget.add_comment(comment)


# コメントを表示する画面のウィジェット
class VideoWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.__moving_list = []
        self.__parent = parent
        self.initUI()

    def initUI(self):
        # プレイヤー下部のステータス部分
        self.hbox = QHBoxLayout()
        # 再生ボタン追加
        self.playButton = QPushButton("PLAY")
        self.playButton.setFixedWidth(100)
        self.playButton.clicked.connect(self.__parent.playButton_clicked)
        self.hbox.addWidget(self.playButton)
        # 再生位置表示
        self.timerLabel = QLabel(self)
        self.timerLabel.setAutoFillBackground(True)
        qp = QPalette()
        qp.setColor(QPalette.Background, QColor("#000000"))
        qp.setColor(QPalette.Foreground, QColor("#FFFFFF"))
        self.timerLabel.setPalette(qp)
        self.timerLabel.setFixedWidth(45)
        self.timerLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.update_timerLabel(0)
        self.hbox.addWidget(self.timerLabel)
        # 再生時間表示
        self.playTimeLabel = QLabel(self)
        self.playTimeLabel.setAutoFillBackground(True)
        self.playTimeLabel.setPalette(qp)
        self.playTimeLabel.setFixedWidth(65)
        self.hbox.addWidget(self.playTimeLabel)
        # シークバー
        self.seekbar = QSlider(Qt.Horizontal)
        self.seekbar.setRange(0, 100)
        self.seekbar.setValue(0)
        self.seekbar.setStyleSheet(
            'QSlider::groove:horizontal {'
            'border: 1px solid #999999;'
            'height: 18px;'
            '}'
            'QSlider::handle:horizontal {'
            'background: silver;'
            'border: 1px solid #333333;'
            'border-radius: 8px;'
            'width: 16px;'
            '}'
            'QSlider::add-page:horizontal {'
            'background: white;'
            '}'
            'QSlider::sub-page:horizontal {'
            'background: blue;'
            '}'
            )
        self.seekbar.sliderReleased.connect(self.seekbar_released)
        self.seekbar.sliderPressed.connect(self.seekbar_pressed)
        self.seekbar.sliderMoved.connect(self.seekbar_moved)
        self.seekbar.setEnabled(False)
        self.hbox.addWidget(self.seekbar)

        # 再生画面とステータス部分
        self.vbox = QVBoxLayout()
        self.vbox.addStretch(1)
        self.vbox.addLayout(self.hbox)
        self.setLayout(self.vbox)

        # 背景を透明にする
        self.setAutoFillBackground(True)
        palette = QPalette()
        brush = QBrush(QColor(0,0,0,0))
        palette.setBrush(QPalette.Background, brush)
        self.setPalette(palette)

    # 描画するためのイベントハンドラ
    def paintEvent(self, event):
        qp = QPainter()
        qp.begin(self)
        # 透明色で塗りつぶし
        qp.setBrush(QColor(0, 0, 0, 0))
        qp.drawRect(event.rect())
        for comment in self.__moving_list:
            comment.drawComment(event, qp)
        # ステータス部分を黒で塗りつぶし
        qp.setBrush(QColor(0, 0, 0, 255))
        status_height = 60
        video_height = event.rect().height() - status_height
        qp.drawRect(event.rect().x(), video_height, event.rect().width(), status_height)
        qp.end()

    def update_timerLabel(self, vpos):
        self.timerLabel.setText(Nicomment.vpos_to_time(vpos))

    def update_playTimeLabel(self, vpos):
        self.playTimeLabel.setText("/  " + Nicomment.vpos_to_time(vpos))

    # 表示させるコメントを追加します
    def add_comment(self, comment):
        line = len(self.__moving_list)
        for m in self.__moving_list:
            if m.canFollow():
                line = m.follow()
                break
        self.__moving_list.append(comment.toMoving(self.frameGeometry().width(), line))
        #comment.printComment()

    # コメントを動かします
    def move_comment(self):
        for comment in self.__moving_list:
            comment.move()
        for i in range(len(self.__moving_list)-1, 0, -1):
            if self.__moving_list[i].isMustDie():
                del self.__moving_list[i]

    def seekbar_changed(self):
        pass

    def seekbar_pressed(self):
        self.__parent.stop_play()
        self.__moving_list = []

    def seekbar_released(self):
        print("released")

    def seekbar_moved(self):
        self.__parent.seek_to(self.seekbar.value())


class CommentWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.__parent = parent

        self.vbox = QVBoxLayout()
        self.hbox = QHBoxLayout()
        # 動画ID入力ボックス
        self.videoidBox = QLineEdit(self)
        self.videoidBox.resize(140, 20)
        self.hbox.addWidget(self.videoidBox)
        # コメント取得ボタン
        self.getButton = QPushButton("取得")
        self.getButton.clicked.connect(self.getButton_clicked)
        self.hbox.addWidget(self.getButton)
        # メニューボタン
        menuButton = QPushButton("メニュー", self)
        popMenu = QMenu(self)
        actLoad = QAction('コメントファイル読込', self)
        actLoad.triggered.connect(self.actLoad_clicked)
        popMenu.addAction(actLoad)
        actOption = QAction('設定', self)
        actOption.triggered.connect(self.actOption_clicked)
        popMenu.addAction(actOption)
        menuButton.setMenu(popMenu)
        self.hbox.addWidget(menuButton)

        self.vbox.addLayout(self.hbox)

        # テーブルの表示
        self.tableView = QTableView()
        self.setTableData([['', '']])
        self.tableView.verticalHeader().setDefaultSectionSize(18)
        self.tableView.verticalHeader().hide()
        self.tableView.setColumnWidth(0, 50)
        self.tableView.setColumnWidth(1, 200)
        self.tableView.setFont(QFont("メイリオ", 10))
        self.vbox.addWidget(self.tableView)

        self.setLayout(self.vbox)

    # コメントウィジェットの背景の描画
    def paintEvent(self, event):
        qp = QPainter()
        qp.begin(self)
        qp.setBrush(QColor(204, 204, 204, 255))
        qp.drawRect(event.rect())
        qp.end()

    def getButton_clicked(self):
        videoid = self.videoidBox.text()
        if videoid == "":
            QMessageBox.information(self, "Nicoplayer", "動画IDを入力してください")
            return

        if self.__parent.load_comment(videoid):
            self.setTableData(self.__parent.get_table_data())

    # コメントファイルの読込
    def actLoad_clicked(self):
        if self.__parent.load_comment_from_xml():
            self.setTableData(self.__parent.get_table_data())

    # アカウント設定
    def actOption_clicked(self):
        self.__setting_window = SettingWindow(self.__parent)
        self.__setting_window.show()

    def setTableData(self, new_tabledata):
        headers = ["位置", "コメント"]
        tableData = new_tabledata
        model = MyTableModel(tableData, headers)
        self.tableView.setModel(model)



class MyTableModel(QtCore.QAbstractTableModel):
    def __init__(self, list, headers = [], parent = None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self.list = list
        self.headers = headers

    def rowCount(self, parent):
        return len(self.list)

    def columnCount(self, parent):
        return len(self.list[0])

    def flags(self, index):
        return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable

    # 指定インデックスの値を取得
    # role:TextAlignmentRoleなら文字揃えを返す
    # DisplayRole or EditRoleならフィールドに格納された値を返す
    def data(self, index, role):
        if role == Qt.TextAlignmentRole and index.column() == 0:
            return int(Qt.AlignRight | Qt.AlignVCenter)

        if role == Qt.DisplayRole or role == Qt.EditRole:
            row = index.row()
            column = index.column()
            return self.list[row][column]

    # 指定インデックスへ値を格納（編集可能領域なら）
    def setData(self, index, value, role = Qt.EditRole):
        if role == Qt.EditRole:
            row = index.row()
            column = index.column()
            self.list[row][column] = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                if section < len(self.headers):
                    return self.headers[section]
                else:
                    return "not implemented"
            else:
                return "item %d" % section



class SettingWindow(QWidget):
    def __init__(self, parent=None):
        super(SettingWindow, self).__init__(parent)
        self.__parent = parent
        self.__w = QDialog(self.__parent)
        grid = QGridLayout()
        grid.setSpacing(10)

        mail, password = self.__parent.load_mail_password()
        mailLabel = QLabel('メール')
        passwordLabel = QLabel('パスワード')
        self.mailEdit = QLineEdit(mail)
        self.passwordEdit = QLineEdit(password)
        self.passwordEdit.setEchoMode(QLineEdit.Password)
        grid.addWidget(mailLabel, 1, 0)
        grid.addWidget(self.mailEdit, 1, 1, 1, 2)
        grid.addWidget(passwordLabel, 2, 0)
        grid.addWidget(self.passwordEdit, 2, 1, 1, 2)

        okButton = QPushButton('OK')
        okButton.clicked.connect(self.okButton_clicked)
        cancelButton = QPushButton('キャンセル')
        cancelButton.clicked.connect(self.cancelButton_clicked)
        grid.addWidget(okButton, 3, 1)
        grid.addWidget(cancelButton, 3, 2)

        self.__w.setLayout(grid)
        self.__w.setWindowTitle('アカウント設定')
        self.__w.resize(320, 100)

    def show(self):
        self.__w.exec_()

    def okButton_clicked(self):
        if self.mailEdit.text() == "":
            QMessageBox.information(self, "Nicoplayer", "メールアドレスを入力してください")
        elif self.passwordEdit.text() == "":
            QMessageBox.information(self, "Nicoplayer", "パスワードを入力してください")
        else:
            self.__parent.dump_mail_password(self.mailEdit.text(), self.passwordEdit.text())
            self.__w.close()

    def cancelButton_clicked(self):
        self.__w.close()



if __name__ == '__main__':
    chdir(dirname(abspath(__file__)))
    app = QApplication(sys.argv)
    player = Nicoplayer()
    player.show()
    sys.exit(app.exec_())