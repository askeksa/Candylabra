#!/usr/bin/env python

import pygame

global samples_per_beat
global samples_per_second
global music_start_pos
global music_is_playing

# todo: read from sync
samples_per_beat = 5410*4
samples_per_second = 44100
music_start_pos = 0
#music_is_playing = False

def initMusic():
    pygame.mixer.init(samples_per_second, -16, 2, 4096)
    #pygame.mixer.music.load("j:\Shared\cs2.1.mp3")
    pygame.mixer.music.load("test.ogg")
    #pygame.mixer.music.load("G:\musik\mod\mobyle.mod")

def playMusic(pos):
    global music_start_pos
    music_start_pos = pos
    #    global music_is_playing
    #    music_is_playing = True
    pygame.mixer.music.play(-1,pos*samples_per_beat / float(samples_per_second))

def stopMusic():
    #global music_is_playing
    #music_is_playing = False
    pygame.mixer.music.stop()
    
def getMusicPos():
    #    return music_start_pos
    return music_start_pos+(pygame.mixer.music.get_pos()/1000.-0.2) * samples_per_second / samples_per_beat

#def musicIsPlaying():
#    return music_is_playing

def getMusicLength():
    return 800
