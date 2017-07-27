#!/usr/bin/python3
# -*- coding: utf-8 -*-


import sys
from os import (getcwd, chdir)
from os.path import (abspath, dirname)
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
        self.__vpos = 0             # 再生位置　1/100秒
        self.__play_time = 60*100   # 再生時間　1/100秒
        self.__is_playing = False
        self.__videoid = ""
        self.__comment_list = []
        # 再生時間の設定
        self.timer = QtCore.QTimer()
        self.timer.setInterval(10)  # 10msごとに呼ばれる
        self.timer.timeout.connect(self.do_play)

        self.setGeometry(100, 100, 1280, 640)
        self.setWindowTitle('Nicoplayer')
        # # メニューバー
        # menubar = self.menuBar()
        # AppMenu = menubar.addMenu('&App')
        # # Macでは項目がExit,Quitだと消えるので、他の名前にすること！
        # exitAction = QAction('&Settings', self)
        # exitAction.triggered.connect(qApp.quit)
        # AppMenu.addAction(exitAction)
        # ウィジェット
        self.video_widget = VideoWidget(self)
        self.video_widget.update_playTimeLabel(self.__play_time)
        self.setCentralWidget(self.video_widget)
        self.comment_dock = QDockWidget("Comment", self)
        self.comment_dock.setWidget(CommentWidget(self))
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.comment_dock)
        # 背景を透明にする
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)


    def do_play(self):
        if self.__is_playing:
            self.__vpos += 1
            if self.__vpos >= self.__play_time:
                self.stop_play()
            self.comment_to_moving()
            self.video_widget.move_comment()
            self.video_widget.update()       # ウィンドウの再描画イベントを呼ぶ
            self.video_widget.update_timerLabel(self.__vpos)


    def start_play(self):
        if self.__videoid != "" and self.__vpos < self.__play_time:
            self.__is_playing = True
            self.timer.start()
            self.video_widget.playButton.setText("STOP")


    def stop_play(self):
        self.__is_playing = False
        self.timer.stop()
        self.video_widget.playButton.setText("PLAY")

    # 動画IDからコメントを取得
    def load_comment(self, videoid):
        mail = ""
        password = ""
        try:
            nico = NicoAPI.NicoNico()
            nico.loadCookieOrLogin(mail, password)
            nico.load_videoinfo(videoid)
            comment_xml = nico.get_comment()
        except NicoAPI.FailedLoginError:
            QMessageBox.warning(self, "Nicoplayer", "ログインに失敗しました")
        except NicoAPI.FailedVideoInfoDownloadError:
            QMessageBox.warning(self, "Nicoplayer", "動画情報の取得に失敗しました")
        except NicoAPI.FailedCommentDownloadError:
            QMessageBox.warning(self, "Nicoplayer", "コメントの取得に失敗しました")
        else:
            root = ET.fromstring(comment_xml)
            elelist = root.findall(".//chat")
            for ele in elelist:
                if ele.text == "" or ele.text == None:
                    continue
                self.__comment_list.append(Nicomment(ele.get("vpos", 0), ele.text))
            self.__comment_list.sort()
            videoinfo = nico.get_videoinfo_copy()
            self.setWindowTitle('Nicoplayer - %s' % videoinfo['video']['title'])
            self.__play_time = int(videoinfo['video']['dmcInfo']['video']['length_seconds']) * 100
            self.video_widget.update_playTimeLabel(self.__play_time)
            self.__videoid = videoid

    # コメントテーブルに設定するためのデータを返す
    def get_table_data(self):
        table_data = []
        for c in self.__comment_list:
            table_data.append(c.getList())
        return table_data

    # 再生時間が同じコメントを表示リストへ追加します
    def comment_to_moving(self):
        for comment in self.__comment_list:
            if comment.isEqualVpos(self.__vpos):
                self.video_widget.add_comment(comment)


    def playButton_clicked(self):
        if self.__is_playing:
            self.stop_play()
        else:
            self.start_play()



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
        self.update_timerLabel(0)
        self.timerLabel.setContentsMargins(5, 5, 5, 5)
        self.hbox.addWidget(self.timerLabel)
        # 再生時間表示
        self.playTimeLabel = QLabel(self)
        self.playTimeLabel.setAutoFillBackground(True)
        qp.setColor(QPalette.Background, QColor("#000000"))
        qp.setColor(QPalette.Foreground, QColor("#FFFFFF"))
        self.playTimeLabel.setPalette(qp)
        self.playTimeLabel.setContentsMargins(5, 5, 5, 5)
        self.hbox.addWidget(self.playTimeLabel)
        # 右側余白
        self.hbox.addStretch(1)

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
        qp.end()


    def update_timerLabel(self, vpos):
        self.timerLabel.setText(Nicomment.vpos_to_time(vpos))

    def update_playTimeLabel(self, vpos):
        self.playTimeLabel.setText("-  " + Nicomment.vpos_to_time(vpos))

    # 表示させるコメントを追加します
    def add_comment(self, comment):
        line = len(self.__moving_list) + 1
        self.__moving_list.append(comment.toMoving(self.frameGeometry().width(), line))
        comment.printComment()

    # コメントを動かします
    def move_comment(self):
        for comment in self.__moving_list:
            comment.move()
        for i in range(len(self.__moving_list)-1, 0, -1):
            if self.__moving_list[i].isMustDie():
                del self.__moving_list[i]



class CommentWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.__parent = parent
        self.vbox = QVBoxLayout()
        self.hbox = QHBoxLayout()
        self.textbox = QLineEdit(self)
        self.textbox.resize(140,20)
        self.hbox.addWidget(self.textbox)
        self.getButton = QPushButton("取得")
        self.getButton.clicked.connect(self.getButton_clicked)
        self.hbox.addWidget(self.getButton)
        self.settingButton = QPushButton("設定")
        self.hbox.addWidget(self.settingButton)
        self.vbox.addLayout(self.hbox)
        # テーブルの表示
        self.tableView = QTableView()
        headers = ["位置", "コメント"]
        tableData = [
            ["", ""]
        ]
        model = MyTableModel(tableData, headers)
        self.tableView.setModel(model)
        self.tableView.verticalHeader().setDefaultSectionSize(18)
        self.tableView.verticalHeader().hide()
        self.tableView.setColumnWidth(0, 50)
        self.tableView.setColumnWidth(1, 200)
        self.tableView.setFont(QFont("メイリオ", 10))
        self.vbox.addWidget(self.tableView)
        self.setLayout(self.vbox)


    def paintEvent(self, event):
        qp = QPainter()
        qp.begin(self)
        qp.setBrush(QColor(204, 204, 204, 255))
        qp.drawRect(event.rect())
        qp.end()


    def getButton_clicked(self):
        videoid = self.textbox.text()
        if videoid == "":
            QMessageBox.information(self, "Nicoplayer", "動画IDを入力してください")
            return

        self.__parent.load_comment(videoid)
        headers = ["位置", "コメント"]
        tableData = self.__parent.get_table_data()
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



if __name__ == '__main__':
    chdir(dirname(abspath(__file__)))
    app = QApplication(sys.argv)
    player = Nicoplayer()
    player.show()
    sys.exit(app.exec_())