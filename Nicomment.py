#!/usr/bin/python3
# -*- coding: utf-8 -*-


from PyQt5.QtGui import QColor, QFont


class Nicomment(object):

    def __init__(self, vpos, comment):
        if comment == '' or comment == None:
            self.__comment = '　'
        else:
            self.__comment = comment
        self.__vpos = int(vpos)

    def __lt__(self, other):
        # self < other
        return self.__vpos < other.vpos()

    def __le__(self, other):
        # self <= other
        return self.__vpos <= other

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
        if vpos < 0:
            sign = '-'
            vpos = -vpos
        else:
            sign = ''
        s = int(vpos) // 100
        m = s // 60
        s = s % 60
        return '{2}{0:02d}:{1:02d}'.format(m, s, sign)



class NicommentMoving(object):

    def __init__(self, width, line, comment):
        self.__font_size = 20
        self.__comment = comment
        self.__width = width
        self.__line = line
        self.__x = self.__width
        self.__y = line * (self.__font_size + 5) + 5
        self.__speed = 2 + (len(self.__comment) // 8)
        self.__followed = False

    def move(self):
        self.__x -= self.__speed

    def isMustDie(self):
        return self.__x <= -(len(self.__comment) * self.__font_size)

    # このコメントの後に続いて別のコメントを流せるか
    def canFollow(self):
        if self.__followed:
            return False
        else:
            return self.__x + (len(self.__comment) * self.__font_size) <= self.__width / 2

    def follow(self):
        self.__followed = True
        return self.__line

    def drawComment(self, event, qp):
        qp.setPen(QColor(255, 255, 255))
        qp.setFont(QFont('メイリオ', self.__font_size))
        qp.drawText(self.__x, self.__y, self.__comment)


if __name__ == '__main__':
    # com1 = Nicomment(100, "Hello")
    # com1.printComment()
    print(Nicomment.vpos_to_time(300))
    print(Nicomment.vpos_to_time(-300))
    print(Nicomment.vpos_to_time(-1))
