import re
import string

from whispering_assistant.commands.command_base_template import BaseCommand, FALL_BACK_COMMAND
import os
import importlib

from whispering_assistant.configs.config import load_os_display_env
from whispering_assistant.states_manager import global_var_state
from whispering_assistant.utils.clipboard_manager import ClipboardHandler
from whispering_assistant.utils.command_intent_detection import get_intent_from_text
from whispering_assistant.utils.command_keyword_matching import command_keyword_matching_top_match
from whispering_assistant.utils.commands_plugin_state import COMMAND_PLUGINS
from whispering_assistant.utils.open_ai_test import input_queue

clipboard_handler = ClipboardHandler()

load_os_display_env()

prev_text_parameter = ''

for file in os.listdir(os.path.dirname(__file__)):
    if file.endswith(".py") and file != "__init__.py" and file != "command_base_template.py":
        module_name = file[:-3]  # Remove the .py extension
        module = importlib.import_module(f"{__package__}.{module_name}")
        for attr_name in dir(module):
            attribute = getattr(module, attr_name)
            if isinstance(attribute, type) and issubclass(attribute, BaseCommand) and attribute is not BaseCommand:
                command_trigger = attribute.trigger.lower()
                COMMAND_PLUGINS[command_trigger] = attribute()


def execute_plugin(trigger, *args, **kwargs):
    plugin = COMMAND_PLUGINS.get(trigger.lower())
    if plugin:
        plugin.run(*args, **kwargs)
    else:
        print(f"No plugin found for trigger: {trigger}")


def remove_special_chars_regex(text):
    """
    Removes any special characters at the beginning and end of a string using a regular expression.
    """
    pattern = r'^[' + re.escape(string.punctuation) + r']+|[' + re.escape(string.punctuation) + r']+$'
    return re.sub(pattern, '', text)


def check_strings(text, keywords, raw_text=""):
    action_index = None
    action_found = False
    subject_index = None
    subject_found = False
    text_parameter = ""
    subject_length = 0
    action_length = 0

    words = text.split()
    limit_to_five_words = " ".join(words[:10]).lower()

    for action in keywords['action']:
        index_with_spaces = limit_to_five_words.find(action)
        index_without_spaces = limit_to_five_words.find(action.replace(" ", ""))

        if index_with_spaces != -1 or index_without_spaces != -1:
            action_found = True
            index = min(i for i in [index_with_spaces, index_without_spaces] if i != -1)
            if action_index is None or index < action_index:
                action_index = index
                action_length = len(action)
            break

    if len(keywords['subject']) == 0:
        subject_found = True
        subject_index = len(raw_text)

    for subject in keywords['subject']:
        index = limit_to_five_words.find(subject)
        if index != -1:
            subject_found = True
            if subject_index is None or index < subject_index:
                subject_index = index
                subject_length = len(subject)
            break

    if subject_found and subject_length > 0:
        text_parameter = raw_text[subject_index + subject_length:]
    elif action_found and action_length > 0:
        text_parameter = raw_text[action_index + action_length:]

    # 📌 TODO: fix this such that if at least one of the action is already before the subject, this should return true
    # print("action_found", action_found, subject_found, action_index, subject_index, (action_found and subject_found and action_index < subject_index),
    #       text_parameter)
    return (action_found and subject_found and action_index < subject_index), remove_special_chars_regex(text_parameter)


def execute_plugin_by_keyword(text, run_command=True, skip_fallback=False, intent_sensitivity=0, *args, **kwargs):
    global prev_text_parameter
    found = False
    plugin_used = None
    text_for_ingestion = text

    clipboard_handler.handle_clipboard(text_for_ingestion.strip())

    if global_var_state.continuous_conversation_mode:
        if run_command and not skip_fallback:
            input_queue.put(text)

    else:
        result_text_lower = text_for_ingestion.lower().strip()
        words_array = [word.strip() for word in re.split(r'[^\w\s]+|(?<=\s)', result_text_lower) if word.strip()]
        words_cleaned = ' '.join(words_array)
        detected_intent = None
        detected_intent_details = None
        text_parameter = None
        plugin_to_use = None

        # KW matching first
        kw_match_top_result = command_keyword_matching_top_match(' '.join(words_array[:5]))
        print("🎤🎤kw_match_top_result", kw_match_top_result)

        # Then intent analysis
        if not kw_match_top_result:
            detected_intent, detected_intent_details = get_intent_from_text(result_text_lower,
                                                                            intent_sensitivity=intent_sensitivity)
            print("detected_intent", detected_intent)
            print("detected_intent_details", detected_intent_details)

        for plugin in COMMAND_PLUGINS.values():
            if plugin.trigger.lower() != FALL_BACK_COMMAND:

                if kw_match_top_result:
                    plugin_to_use = kw_match_top_result
                else:
                    if detected_intent and detected_intent.lower() == plugin.trigger.lower():
                        print(type(plugin))
                        print("found plugin using intent", detected_intent)
                        print("text_parameter", text_parameter)
                        print("result_text_lower", result_text_lower)
                        parameter_checker_result = plugin.parameter_checker(raw_text=result_text_lower)
                        print("🤔 parameter_checker_result", parameter_checker_result)

                        if hasattr(plugin, 'required_keywords'):
                            if not any(
                                    required_keyword in result_text_lower for required_keyword in
                                    plugin.required_keywords):
                                print('missing required keywords for plugin', plugin.trigger.lower())
                                continue

                        if parameter_checker_result is None:
                            continue

                        plugin_used = plugin
                        plugin_to_use = plugin

                if plugin_to_use:
                    match, text_parameter = check_strings(words_cleaned, plugin_to_use.keywords,
                                                          raw_text=result_text_lower)
                    break

        if plugin_to_use:
            found = True
            if run_command:
                print('running plugin', plugin_to_use.trigger.lower())
                prev_text_parameter = text_parameter
                plugin_to_use.run(*args, text_parameter=text_parameter, raw_text=text_for_ingestion,
                                  command_intent=detected_intent_details, **kwargs)

        if not found:
            print(f"No plugin found for text: {text_for_ingestion}")
            fallback_plugin = COMMAND_PLUGINS.get(FALL_BACK_COMMAND.lower())
            if not skip_fallback and fallback_plugin:
                prev_text_parameter = text_for_ingestion
                fallback_plugin.run(*args, text_parameter=text_for_ingestion, raw_text=text_for_ingestion, **kwargs)
            else:
                print("No fallback plugin found.")

    return plugin_used


prompts_for_short_commands_cache = None


def generate_prompts_for_short_commands():
    global prompts_for_short_commands_cache

    if prompts_for_short_commands_cache:
        return prompts_for_short_commands_cache

    command_list = []

    for plugin in COMMAND_PLUGINS.values():
        command_list.extend(plugin.keywords['action'])
        command_list.extend(plugin.keywords['subject'])

    command_list = list(dict.fromkeys(command_list))
    command_list = [command for command in command_list if command != ""]
    command_list = ",".join(command_list)
    command_list = f"command list: {command_list}"

    print(command_list)
    prompts_for_short_commands_cache = command_list
    return command_list
