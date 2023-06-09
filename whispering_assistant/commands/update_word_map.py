from whispering_assistant.commands.command_base_template import BaseCommand, command_types
import subprocess


class UpdateWordMap(BaseCommand):
    trigger = "update_word_map"
    command_type = command_types['ONE_SHOT']
    keywords = {
        "action": ["update", "change"], "subject": ["word map", "wordmap"]}
    description = [
        "use the following tool for updating the official word map keyword list. example: 'update word map'"
    ]
    examples = [
        'update word map',
        'change word map',
        'change word list',
        'update the word map',
        'update the word list',
        'update the dictionary list'
    ]

    def run(self, text_parameter, raw_text, *args, **kwargs):
        file_path = "/home/joshua/extrafiles/projects/WhisperingAssistant/whispering_assistant/assets/docs/prompt.yml"
        subprocess.call(['atom', file_path])
