# -*- coding: utf-8 -*-
"""Oddiy, tasodifiy labirint o'yin mantig'i (audio bilan ishlash uchun mos)."""
import random

DIRS = {
    "up": (0, 1),
    "down": (0, -1),
    "left": (-1, 0),
    "right": (1, 0),
}

DIR_NAMES_UZ = {
    "up": "yuqoriga",
    "down": "pastga",
    "left": "chapga",
    "right": "o'ngga",
}


class Maze:
    def __init__(self, width=6, height=6, coin_count=3):
        self.width = width
        self.height = height
        self.player = [0, 0]
        self.exit = [width - 1, height - 1]
        self.coins = set()
        while len(self.coins) < coin_count:
            c = (random.randint(0, width - 1), random.randint(0, height - 1))
            if c != tuple(self.player) and c != tuple(self.exit):
                self.coins.add(c)
        self.score = 0

    def move(self, direction):
        if direction not in DIRS:
            return "invalid"
        dx, dy = DIRS[direction]
        nx, ny = self.player[0] + dx, self.player[1] + dy

        if nx < 0 or nx >= self.width or ny < 0 or ny >= self.height:
            return "wall"

        self.player = [nx, ny]

        if tuple(self.player) in self.coins:
            self.coins.remove(tuple(self.player))
            self.score += 1
            return "coin"

        if self.player == self.exit:
            return "win"

        return "moved"

    def describe_position(self):
        px, py = self.player
        ex, ey = self.exit
        remaining = len(self.coins)
        dist = abs(ex - px) + abs(ey - py)
        return (
            f"Siz {px} qator, {py} ustunda turibsiz. "
            f"Chiqishgacha {dist} qadam qoldi. "
            f"Yig'ilmagan tangalar soni: {remaining}."
        )
