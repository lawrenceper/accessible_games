"""
accessible_games - tools for multi-sound audio playback, keyboard input using pygame, and most importantly, making games accessible to visually impaired users through spoken prompts by espeak-ng.

This module simplifies playback of multiple audio files with context manager
support and clear exception handling. It also facilitates keyboard input from within a window.

    The most important part of the module, while Small, is the speak function, which facilitates spoken prompts with voice interrupt support. This means that you can call speak and automatically interrupt the voice that's currently speaking, making it very easy to implement into your accessible game. This is how modern screen readers usually interact when you press the keys on your keyboard.

    This module additionally supports easily compiling with pyinstaller, to allow your game sounds to be discovered regardless if your game is running directly within Python, or if your game executable includes your sounds. This is optional.

Functions:
    speak(text): a function to speak text aloud.
    load(channels=16): Initializes pygame mixer with N playback channels.
    exit(): Shuts down pygame mixer.
    pause(seconds): pauses the game rather than attempting to receive input. Useful for things like un skippable audio animations or pausing for the to allow the speech to finish.
    input(): facilitates keyboard input functionality within a window.

Classes:
    Player: Load and control playback of one audio file per instance.

Example usage:
    import accessible_games

    accessible_games.load(channels=16)

    with accessible_games.Player("kick.wav") as kick, accessible_games.Player("snare.wav") as snare:
        kick.play()
        snare.play()
        accessible_games.speak("Press Enter to stop.")
        input()

    accessible_games.exit()
"""



import os
# following line is no longer needed, because this time I'm building a self voicing app. But I'm keeping them here just in case I need to quickly make a new terminal based pygame app, or for quick reference later.
# os.environ["SDL_VIDEODRIVER"] = "dummy"  # Prevent graphical window
import time
import pygame
import subprocess
import shutil
import sys

# Variables
_initialized = False
_process = None # Used by espeak-ng.

def load(channels=16):
    """
    Initializes pygame mixer with a given number of channels.

    Args:
        channels (int): The number of channels for simultaneous playback. Default is 16.

    Raises:
        RuntimeError: If already initialized.
    """
    global _initialized
    if _initialized:
        raise RuntimeError("pygame mixer is already initialized.")
    # Initialize the window
    pygame.init()
    pygame.display.set_mode((400, 200))
    # now initialize the mixer
    pygame.mixer.init()
    pygame.mixer.set_num_channels(channels)
    _initialized = True

def exit():
    """
    Shuts down pygame mixer and frees audio resources.

    Raises:
        RuntimeError: If not initialized.
    """
    global _initialized
    if not _initialized:
        raise RuntimeError("pygame mixer is not initialized.")
    pygame.mixer.quit()
    pygame.quit()
    _initialized = False

def get_working_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def speak(text):
    """ Speaks with the Espeak-NG package.
    Espeak-NG is a required component of this software, and it can't be included in the installed binary.
    
    Args:
        text: The text to speak to
    returns:
        True if Espeak-NG package is installed and ready, otherwise returns False.
    Note, this function uses subprocess.Popen() to make espeak run in the background, so it doesn't freeze the game. Every time this function is started, the function replaces process.Popen(), which makes it easier to add speech interupt and background processes that can run without freezing the game.
    """
    global _process
    command_path = shutil.which("espeak-NG")
    if command_path == None:
        return False
    else:
        try: # try to terminate speech**before*starting speech again. Needed so that old speech is stopped before speaking, otherwise speech will overlap.
            _process.terminate()
        except:
            print("No process to terminate") # rather than raise an exception here, we want to gracefully move on with the game in case the process has already been terminated, meaning that it's done speaking.
        _process = subprocess.Popen([command_path, "-s = 200", text])
        return True

def pause(seconds, update_callback=None):
    """ A function that's almost like time.sleep() but doesn't cause the game to hang."""
    start = time.time()
    clock = pygame.time.Clock()

    while time.time() - start < seconds:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

        if update_callback:
            update_callback()

        pygame.display.flip()
        clock.tick(60)  # Limit to 60 FPS


def input():

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            if event.type == pygame.KEYDOWN:
                key = event.unicode if event.unicode else pygame.key.name(event.key)
                return key


class Player:
    """
    AudioPlayer(filename)

    A class to manage the playback of an audio file on its own channel.

    Args:
        filename (str): Path to the audio file (e.g., .wav, .mp3, .ogg)

    Methods:
        play(): Start or resume playback.
        pause(): Pause playback.
        stop(): Stop playback.
        volume(percentage) - Changes the volume of the track.

    Usage:
        with AudioPlayer("sound.wav") as player:
            player.play()
    """

    def __init__(self, filename):
        if not _initialized:
            raise RuntimeError("pygame mixer must be initialized using pyaudio.load().")

        self.filename = filename
        self.sound = pygame.mixer.Sound(filename)
        self.channel = pygame.mixer.find_channel()
        if self.channel is None:
            raise RuntimeError("No available audio channel.")
        self._paused = False

    def play(self):
        """
        Starts or resumes playback of the audio.

        Raises:
            RuntimeError: If pygame is not initialized.
        """
        if not _initialized:
            raise RuntimeError("pygame mixer is not initialized.")
        if self._paused:
            self.channel.unpause()
        else:
            self.channel.play(self.sound)
        self._paused = False

    def pause(self):
        """
        Pauses playback.

        Raises:
            RuntimeError: If nothing is currently playing.
        """
        if not self.channel.get_busy():
            raise RuntimeError("No audio is currently playing.")
        self.channel.pause()
        self._paused = True

    def stop(self):
        """
        Stops playback.

        Raises:
            RuntimeError: If nothing is currently playing.
        """
        if not self.channel.get_busy():
            raise RuntimeError("No audio is currently playing.")
        self.channel.stop()
        self._paused = False

    def volume(self, percentage):
        """
        Sets the volume of the current audio track as a percentage.

        Args:
            percentage (float): Volume as a percentage, where 100 is the original volume.
            
        Raises:
            ValueError: If the percentage is not between 0 and 100.
        """
        if not (0 <= percentage <= 100):
            raise ValueError("Percentage must be between 0 and 100.")
        
        # Set the volume by scaling the percentage to a 0.0 to 1.0 range
        self.sound.set_volume(percentage / 100.0)

    def __enter__(self):
        """
        Enters context manager and returns the AudioPlayer instance.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Ensures playback is stopped when exiting context manager.
        """
        if self.channel.get_busy():
            self.channel.stop()
