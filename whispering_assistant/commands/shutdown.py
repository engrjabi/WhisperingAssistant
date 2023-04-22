from whispering_assistant.commands.command_base_template import BaseCommand, command_types


class Shutdown(BaseCommand):
    # Set the trigger for the 'Shutdown' command plugin
    trigger = "shutdown"
    command_type = command_types.ONE_SHOT
    keywords = {
        "action": ["shutdown", "power off", "turn off"],
        "subject": ["laptop", "computer"]
    }

    def run(self, *args, **kwargs):
        # Your command execution logic here
        pass