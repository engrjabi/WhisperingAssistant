import os
import subprocess

from whispering_assistant.commands.command_base_template import BaseCommand, command_types


class LockScreen(BaseCommand):
    # Set the trigger for the 'Shutdown' command plugin
    trigger = "lock_screen"
    command_type = command_types['ONE_SHOT']
    keywords = {
        "action": ["lock", "lock screen"],
        "subject": ["laptop", "computer"]
    }
    description = [
        "use the following tool for locking the screen of computer or laptop"
    ]
    required_keywords = ['computer', 'laptop', 'screen']
    examples = [
        'lock screen computer',
        'lock the screen'
    ]

    def run(self, *args, **kwargs):
        subprocess.run(['xdotool', 'key', 'Super+Escape'])

