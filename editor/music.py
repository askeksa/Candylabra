#!/usr/bin/env python

import pygame

global samples_per_beat
global samples_per_second
# todo: read from sync
samples_per_beat = 5410.*4
samples_per_second = 44100

def initMusic():
    pygame.mixer.init(samples_per_second, -16, 2, 4096)
    #pygame.mixer.music.load("j:\Shared\cs2.1.mp3")
    pygame.mixer.music.load("test.ogg")
    #pygame.mixer.music.load("G:\musik\mod\mobyle.mod")

def playMusic(pos):
    pygame.mixer.music.play(-1,pos)

def stopMusic():
    pygame.mixer.music.stop()
    
def getMusicPos():
    return (pygame.mixer.music.get_pos()/1000.-0.2) * samples_per_second / samples_per_beat
