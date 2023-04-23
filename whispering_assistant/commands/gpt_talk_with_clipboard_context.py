import time
import pyperclip
from whispering_assistant.commands.command_base_template import BaseCommand, command_types

GPT3_ALIAS = 'ruby'
GPT4_ALIAS = 'nora'
chatgpt_link_gpt3 = "https://chat.openai.com/chat?model=text-davinci-002-render-sha"
chatgpt_link_gpt4 = "https://chat.openai.com/chat?model=gpt-4"
root_dir = "../assets/images"

# Define the region to search in
x1, y1, width1, height1 = 0, 0, 3840, 130
region1 = (x1, y1, width1, height1)
image1_chat_logo = f'{root_dir}/CHAT_LOGO.png'

x2, y2, width2, height2 = 630, 0, 3840, 1200
region2 = (x2, y2, width2, height2)
image2_chat_box = f'{root_dir}/CHAT_BOX.png'

x3, y3, width3, height3 = 0, 0, 3840, 500
region3 = (x1, y1, width1, height1)
image3_gpt4_url = f'{root_dir}/CHAT_GPT4_URL.png'

x4, y4, width4, height4 = 630, 0, 3840, 1800
region4 = (x4, y4, width4, height4)
image4_chat_down_arrow = f'{root_dir}/CHAT_DOWN_ARROW.png'


def send_question_to_gpt(query, new_conversation=False, gpt_type='GPT3', check_gpt_type=False):
    import pyautogui
    new_conversation_2 = new_conversation
    chatgpt_link = chatgpt_link_gpt4 if 'GPT4' in gpt_type else chatgpt_link_gpt3

    # Press CTRL-ALT-SHIFT-Q to activate chrome with GPT
    pyautogui.hotkey('ctrl', 'alt', 'shift', 'q')
    print("CTRL-ALT-SHIFT-Q pressed.")
    time.sleep(1)

    if check_gpt_type:
        image3_location = pyautogui.locateOnScreen(image3_gpt4_url, region=region3, confidence=0.95)
        print("image3_location", image3_location)
        if image3_location is None:
            print("❌ CHAT GPT 4 not found on the screen.")
            new_conversation_2 = True

    if new_conversation_2:
        pyautogui.hotkey('ctrl', 't')
        time.sleep(0.5)
        pyautogui.typewrite(chatgpt_link)
        time.sleep(0.1)
        pyautogui.press('enter')
        time.sleep(2)

    # Check if image1_chat_logo exists on the screen
    image1_location = pyautogui.locateOnScreen(image1_chat_logo, region=region1, confidence=0.8)

    if image1_location is not None:
        print(f"Image 1 found at {image1_location}")

        # Look for image2_chat_box on the screen
        image2_location = pyautogui.locateOnScreen(image2_chat_box, region=region2, confidence=0.5)

        if image2_location is not None:
            print(f"Image 2 found at {image2_location}")

            # Click in the center of image2_chat_box
            image2_center = pyautogui.center(image2_location)
            pyautogui.click(image2_center)

            # Type the string
            old_clipboard = pyperclip.paste()
            pyperclip.copy(query.lstrip())
            time.sleep(0.5)
            pyautogui.hotkey('ctrl', 'v')
            pyperclip.copy(old_clipboard)
            time.sleep(0.5)

            # Press the enter key
            pyautogui.press('enter')
            print("Typing and pressing enter done.")

            time.sleep(0.5)
            image4_location = pyautogui.locateOnScreen(image4_chat_down_arrow, region=region4, confidence=0.95)

            if image4_location is not None:
                image4_center = pyautogui.center(image4_location)
                pyautogui.click(image4_center)
            else:
                print("Image 4 not found on the screen.")

        else:
            print("Image 2 not found on the screen.")
            send_question_to_gpt(query, new_conversation=True, gpt_type=gpt_type, check_gpt_type=check_gpt_type)
    else:
        print("❌ Image 1 logo not found on the screen.")


class TalkGPTWithClipboardContext(BaseCommand):
    trigger = "talk_gpt_with_clipboard_context"
    command_type = command_types['CHAINABLE_LONG']
    keywords = {"action": ["clipboard", "error", "context", "text", "condition", "relation", "question"],
                "subject": ["nora", "ruby"]}

    def run(self, text_parameter, raw_text, *args, **kwargs):
        modified_text = text_parameter

        chatgpt_type = 'GPT4' if GPT4_ALIAS in raw_text.lower() else 'GPT3'
        keywords = ['clipboard', 'context', 'relation']
        clipboard_needed = any(keyword in raw_text.lower() for keyword in keywords)

        # Handle Clipboard injection
        if clipboard_needed:
            curr_clipboard = pyperclip.paste()
            modified_text = curr_clipboard

            if text_parameter:
                modified_text = "Context:\n" + "```\n" + curr_clipboard + "\n```\n" + text_parameter

        # TODO: Handle comms without creating new conversation

        send_question_to_gpt(modified_text, gpt_type=chatgpt_type, check_gpt_type=True)