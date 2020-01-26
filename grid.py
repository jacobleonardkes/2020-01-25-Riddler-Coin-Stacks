import numpy as np
import os

RED_UNIT = 256 * 256
GREEN_UNIT = 256
BLUE_UNIT = 1
RED = 255 * RED_UNIT
GREEN = 255 * GREEN_UNIT
BLUE = 255 * BLUE_UNIT
BLACK = 0
WHITE = RED + GREEN + BLUE
GRAY_FACTOR = 190
GRAY = GRAY_FACTOR * (RED_UNIT + GREEN_UNIT + BLUE_UNIT)


class Canvas(object):
    def __init__(self, width, height, background=WHITE, filename='frame%03d.ppm'):
        self.pixels = np.zeros((width, height), type(0)) + background
        self.__filename = filename
        self.__frameNum = 0

    def width(self):
        return self.pixels.shape[1]

    def height(self):
        return self.pixels.shape[0]

    def renderPPM(self):
        filename = self.__filename % self.__frameNum
        file = open(filename, 'w')
        file.write('P3\n%d\n%d\n255\n' % (self.width(), self.height()))
        for row in reversed(range(self.height())):
            for col in range(self.width()):
                color = self.pixels[row, col]
                file.write('%d %d %d\n' % (color // RED_UNIT, color % RED_UNIT // GREEN_UNIT, color % GREEN_UNIT))
        file.close()
        print('Wrote ' + filename)
        self.__frameNum += 1

    def reset(self):
        self.pixels *= 0


class Widget(object):
    def __init__(self, width, height):
        self.__width = width
        self.__height = height
        self.pixels = np.zeros((width, height), type(0)) - 1

    def width(self):
        return self.__width

    def height(self):
        return self.__height

    def genPixels(self):
        raise BaseException('To be implemented in derived classes')

    def draw(self, canvas, offsetX=0, offsetY=0):
        self.genPixels()
        for (row, col), c in np.ndenumerate(self.pixels):
            if c >= 0:
                canvas.pixels[col + offsetX, row + offsetY] = c


class MonochromaticWidget(Widget):
    def __init__(self, width, height, color):
        Widget.__init__(self, width, height)
        self.__color = color

    def genPixels(self):
        self.genPixelsMono()
        self.pixels += 1 # transparent (-1) --> 0 and filled (1) --> 2
        self.pixels //= 2 # transparent --> 0 and filled --> 1
        self.pixels *= self.__color + 1 # transparent --> 0 and filled --> color+1
        self.pixels -= 1 # transparent --> -1 and filled --> color


class Rectangle(MonochromaticWidget):
    def __init__(self, width, height, color):
        MonochromaticWidget.__init__(self, width, height, color)

    def genPixelsMono(self):
        self.pixels *= 0
        self.pixels += 1


class Square(Rectangle):
    def __init__(self, dim, color):
        MonochromaticWidget.__init__(self, dim, dim, color)


class VerticalLine(Rectangle):
    def __init__(self, height, color):
        MonochromaticWidget.__init__(self, height, 1, color)


class HorizontalLine(Rectangle):
    def __init__(self, width, color):
        MonochromaticWidget.__init__(self, 1, width, color)


class LeftArrow(MonochromaticWidget):
    def __init__(self, width, arrowheadDim, color):
        MonochromaticWidget.__init__(self, width, 2*arrowheadDim+1, color)
        self.arrowheadDim = arrowheadDim

    def genPixelsMono(self):
        for col in range(self.width()):
            self.pixels[col, self.arrowheadDim] = 1
        for i in range(1, self.arrowheadDim+1):
            self.pixels[i, self.arrowheadDim+i] = 1
            self.pixels[i+1, self.arrowheadDim+i] = 1
            self.pixels[i, self.arrowheadDim-i] = 1
            self.pixels[i+1, self.arrowheadDim-i] = 1


class DownArrow(MonochromaticWidget):
    def __init__(self, height, arrowheadDim, color):
        MonochromaticWidget.__init__(self, 2*arrowheadDim+1, height, color)
        self.arrowheadDim = arrowheadDim

    def genPixelsMono(self):
        for row in range(self.height()):
            self.pixels[self.arrowheadDim, row] = 1
        for i in range(1, self.arrowheadDim+1):
            self.pixels[self.arrowheadDim+i, i] = 1
            self.pixels[self.arrowheadDim+i, i+1] = 1
            self.pixels[self.arrowheadDim-i, i] = 1
            self.pixels[self.arrowheadDim-i, i+1] = 1

class DownLeftArrow(MonochromaticWidget):
    def __init__(self, dim, arrowheadDim, color):
        MonochromaticWidget.__init__(self, dim, dim, color)
        self.arrowheadDim = arrowheadDim

    def genPixelsMono(self):
        for ix in range(self.height()):
            self.pixels[ix, ix] = 1
        for ix in range(1, self.arrowheadDim+1):
            self.pixels[ix, 0] = 1
            self.pixels[0, ix] = 1


class Grid(Canvas):
    def __init__(self, gridSize, tickSize, arrowheadDim, gridThickness):
        self.gridSize = gridSize
        self.tickSize = tickSize
        self.arrowheadDim = arrowheadDim
        self.pixelsThickness = gridThickness
        self.cellSizeInner = arrowheadDim * 2 + 3
        self.cellStep = self.cellSizeInner + gridThickness
        self.canvasSize = tickSize + self.cellStep * gridSize + gridThickness
        self.shapeCache = {}
        self.cells = np.zeros((self.gridSize, self.gridSize), type(0))
        self.leftArrows = []
        self.downArrows = []
        self.downLeftArrows = []
        self.highlightAntidiagonal = None
        Canvas.__init__(self, self.canvasSize, self.canvasSize, WHITE)
        self.initCells()
        self.draw()

    def initCells(self):
        self.cells *= 0
        self.cells += GRAY

    def draw(self):
        self.drawGridLines()
        self.drawCells()
        self.drawArrows()

    def renderPPM(self):
        self.draw()
        Canvas.renderPPM(self)

    def resetArrows(self):
        self.leftArrows = []
        self.downArrows = []
        self.downLeftArrows = []

    def drawGridLines(self):
        vert = VerticalLine(self.canvasSize, BLACK)
        horiz = HorizontalLine(self.canvasSize, BLACK)
        for i in range(self.gridSize + 1):
            vert.draw(self, self.tickSize-1 + i*self.cellStep, 0)
            horiz.draw(self, 0, self.tickSize-1 + i*self.cellStep)

    def drawCells(self):
        for (row, col), color in np.ndenumerate(self.cells):
            self.__drawCell(row, col, color)

    def __drawCell(self, row, col, color):
        if self.highlightAntidiagonal is not None and row + col != self.highlightAntidiagonal:
            # If not highlighting cell, then smoosh the color 2/3 of the way to gray
            redVal = color // RED_UNIT
            greenVal = color % RED_UNIT // GREEN_UNIT
            blueVal = color % GREEN_UNIT
            redValAdj = int(np.floor((2.0/3) * GRAY_FACTOR + (1.0/3) * redVal))
            greenValAdj = int(np.floor((2.0/3) * GRAY_FACTOR + (1.0/3) * greenVal))
            blueValAdj = int(np.floor((2.0/3) * GRAY_FACTOR + (1.0/3) * blueVal))
            colorAdj = redValAdj * RED_UNIT + greenValAdj * GREEN_UNIT + blueValAdj * BLUE_UNIT
        else:
            colorAdj = color

        key = 'cell%d' % colorAdj
        if key not in self.shapeCache:
            self.shapeCache[key] = Square(self.cellSizeInner, colorAdj)
        self.shapeCache[key].draw(self, self.tickSize + self.cellStep * row, self.tickSize + self.cellStep * col)

    def drawArrows(self):
        for arrow in self.leftArrows:
            LeftArrow(self.cellStep*(arrow['xRight']-arrow['xLeft']), self.arrowheadDim, arrow['color'])\
                .draw(self, self.tickSize+1+self.cellStep*arrow['y'], self.tickSize+(self.cellStep//2) + self.cellStep*arrow['xLeft'])
        for arrow in self.downArrows:
            DownArrow(self.cellStep*(arrow['yTop']-arrow['yBottom']), self.arrowheadDim, arrow['color'])\
                .draw(self, self.tickSize+(self.cellStep//2)+self.cellStep*arrow['yBottom'], self.tickSize+1+self.cellStep*arrow['x'])
        for arrow in self.downLeftArrows:
            DownLeftArrow(self.cellStep*(arrow['yTop']-arrow['yBottom']), self.arrowheadDim, arrow['color'])\
                .draw(self, self.tickSize+(self.cellStep//2)+self.cellStep*arrow['yBottom'], self.tickSize+(self.cellStep//2)+self.cellStep*arrow['xLeft'])

    def isDone(self):
        return np.min(self.cells != GRAY)

    def step(self):
        self.resetArrows()

        # Find new black cells, either (0, 0) at beginning, or otherwise when all to the left, down and diag are white
        newBlack = []
        if np.all(self.cells == GRAY):
            newBlack.append((0, 0))
        else:
            for (row, col), color in np.ndenumerate(self.cells):
                if color != GRAY:
                    continue
                if np.all(self.cells[0:col, row] == WHITE) \
                  and np.all(self.cells[col, 0:row] == WHITE) \
                  and np.all(self.cells.diagonal(row - col)[0:min(row, col)] == WHITE):
                    newBlack.append((row, col))
                    self.leftArrows.append({'xLeft': 0, 'xRight': col, 'color': RED, 'y': row})
                    self.downArrows.append({'x': col, 'yBottom': 0, 'yTop': row, 'color': RED})
                    self.downLeftArrows.append(
                        {'yTop': row, 'yBottom': max(0, row - col), 'xLeft': max(0, col - row), 'color': RED})

        for (row, col) in newBlack:
            self.cells[(row, col)] = BLACK
        self.renderPPM()

        # Color cells above, to the right or up-right of the new black cells as white
        self.resetArrows()
        for (col, row) in newBlack:
            for row2 in range(row+1, self.gridSize):
                self.cells[col, row2] = WHITE
            self.leftArrows.append({'xLeft': col, 'xRight': self.gridSize-1, 'y': row, 'color': BLUE})
        self.renderPPM()
        self.leftArrows = []

        for (col, row) in newBlack:
            for col2 in range(col+1, self.gridSize):
                self.cells[col2, row] = WHITE
            self.downArrows.append({'x': col, 'yBottom': row, 'yTop': self.gridSize-1, 'color': BLUE})
        self.renderPPM()
        self.downArrows = []

        for (col, row) in newBlack:
            for z in range(min(self.gridSize-row, self.gridSize-col)-1):
                self.cells[col+z+1, row+z+1] = WHITE
            self.downLeftArrows.append({'xLeft': col, 'yBottom': row, 'yTop': self.gridSize-1-max(0, col-row), 'color': BLUE})
        self.renderPPM()
        self.downLeftArrows = []


if __name__ == "__main__":
    print('Starting')
    g = Grid(31, 3, 4, 1)
    g.renderPPM()
    while not g.isDone():
        g.step()
    g.resetArrows()
    g.renderPPM()

    for numInitialCoins in range(20, 31):
        g.highlightAntidiagonal = numInitialCoins
        g.renderPPM()
        for row in range(numInitialCoins+1):
            col = numInitialCoins - row
            if g.cells[row, col] == BLACK:
                print('With %d coins, piles of %d and %d are a winning solution!' % (numInitialCoins, row, col))

    # Need imagemagick installed for this (works on Linux):
    os.system("convert -delay 100 -loop 0 frame*.ppm solution.gif")

    print('Done')
