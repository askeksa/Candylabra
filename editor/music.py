#!/usr/bin/env python

import pygame

global samples_per_beat
global samples_per_second
global music_start_pos
global music_is_playing

# todo: read from sync
samples_per_second = 44100
music_start_pos = 0
music_is_playing = False

def initMusic(filename):
    global music_start_pos
    global music_is_playing
    if music_is_playing:
        pos = getMusicPos()
        pygame.mixer.music.stop()
    pygame.mixer.init(samples_per_second, -16, 2, 2048)
    #pygame.mixer.music.load("j:\Shared\cs2.1.mp3")
    #pygame.mixer.music.load("test.ogg")
    #pygame.mixer.music.load("G:\musik\mod\mobyle.mod")
    #pygame.mixer.music.load("Silence.ogg")
    #pygame.mixer.music.load("solskogen3-clean.ogg")
    pygame.mixer.music.load(filename)
    if music_is_playing:
        playMusic(pos)

def playMusic(pos):
    global music_start_pos
    global music_is_playing
    music_start_pos = pos
    music_is_playing = True
    pygame.mixer.music.play(-1,pos)

def stopMusic():
    global music_is_playing
    music_is_playing = False
    pygame.mixer.music.stop()
    
def getMusicPos():
    return music_start_pos+(pygame.mixer.music.get_pos()/1000.-0.2)

def musicIsPlaying():
    return music_is_playing

def getMusicLength():
    return 600
