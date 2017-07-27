#!/usr/bin/python3
# -*- coding: utf-8 -*-


from PyQt5.QtGui import QColor, QFont


class Nicomment(object):

    def __init__(self, vpos, comment):
        if comment == "" or comment == None:
            self.__comment = "　"
        else:
            self.__comment = comment
        self.__vpos = int(vpos)

    def __lt__(self, other):
        # self < other
        return self.__vpos < other.vpos()

    def vpos(self):
        return self.__vpos

    def isEqualVpos(self, vpos):
        return self.__vpos == vpos

    def toMoving(self, width, line):
        return NicommentMoving(width, line, self.__comment)

    def getList(self):
        return [self.vpos_to_time(self.__vpos), self.__comment]

    def printComment(self):
        print(self.__comment)

    @classmethod
    def vpos_to_time(self, vpos):
        s = int(vpos) // 100
        m = s // 60
        s = s % 60
        return "{0:02d}:{1:02d}".format(m, s)



class NicommentMoving(object):

    def __init__(self, width, line, comment):
        self.__font_size = 20
        self.__time_limit = 400     # 表示される時間(1/100秒)
        self.__comment = comment
        self.__life = self.__time_limit
        self.__width = width
        self.__x = self.__width
        self.__y = line * (self.__font_size + 5)
        self.__speed = self.__width / self.__time_limit

    def move(self):
        #self.__life -= 1 + (len(self.__comment) // 5)
        self.__life -= 2
        self.__x = self.__life * self.__speed

    def isMustDie(self):
        return self.__life <= -(len(self.__comment) * self.__font_size)

    def drawComment(self, event, qp):
        qp.setPen(QColor(255, 255, 255))
        qp.setFont(QFont('メイリオ', self.__font_size))
        qp.drawText(self.__x, self.__y, self.__comment)


if __name__ == '__main__':
    com1 = Nicomment(100, "Hello")
    com1.printComment()
