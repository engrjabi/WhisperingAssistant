import re
from fairseq.checkpoint_utils import load_model_ensemble_and_task_from_hf_hub
from fairseq.models.text_to_speech.hub_interface import TTSHubInterface
import soundfile as sf
import threading
from queue import Queue
from playsound import playsound
import time
# v 🚥🚥🚥

from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan
import torch
import soundfile as sf
from datasets import load_dataset

# https://github.com/microsoft/SpeechT5/issues/8 more fine tuned model
processor = SpeechT5Processor.from_pretrained("microsoft/speecht5_tts")
model = SpeechT5ForTextToSpeech.from_pretrained("microsoft/speecht5_tts")
vocoder = SpeechT5HifiGan.from_pretrained("microsoft/speecht5_hifigan")

# inputs = processor(text="Hello, my dog is cute", return_tensors="pt")

# load xvector containing speaker's voice characteristics from a dataset
embeddings_dataset = load_dataset("Matthijs/cmu-arctic-xvectors", split="validation")
speaker_embeddings = torch.tensor(embeddings_dataset[7306]["xvector"]).unsqueeze(0)

# speech = model.generate_speech(inputs["input_ids"], speaker_embeddings, vocoder=vocoder)

# sf.write("speech.wav", speech.numpy(), samplerate=16000)
# playsound("speech.wav")

# exit(0)

# v 🚥🚥🚥
# Alternatives
# speecht5 did not mention anything about inference so its better to just try it ourselves
# https://huggingface.co/blog/speecht5
# https://huggingface.co/spaces/SurendraKumarDhaka/Text-to-speech-converter
# https://huggingface.co/speechbrain/tts-tacotron2-ljspeech?text=A+quick+brown+fox+jumped+over+the+lazy+dog
# facebook/fastspeech2-en-200_speaker-cv4
# models, cfg, task = load_model_ensemble_and_task_from_hf_hub(
#     "facebook/fastspeech2-en-ljspeech",
#     arg_overrides={"vocoder": "hifigan", "fp16": False, "cpu": True}
# )
#
# model = models[0]
# TTSHubInterface.update_cfg_with_data_cfg(cfg, task.data_cfg)
# generator = task.build_generator([model], cfg)

# Define a special sentinel value
SENTINEL = 'STOP'


# Define a function to split text into chunks of a certain number of words
def split_into_chunks(text, max_words):
    words = text.split()
    for i in range(0, len(words), max_words):
        yield ' '.join(words[i:i + max_words])


# Define a function to generate speech
def generate_speech(i, chunk, queue):
    # Get the model input for this chunk

    # Generate the speech audio for this chunk
    start_time = time.time()
    # sample = TTSHubInterface.get_model_input(task, chunk)
    # wav, rate = TTSHubInterface.get_prediction(task, model, generator, sample)
    inputs = processor(text=chunk, return_tensors="pt")
    speech = model.generate_speech(inputs["input_ids"], speaker_embeddings, vocoder=vocoder)
    end_time = time.time()

    print(f'✅ Text-to-speech generation for chunk {i + 1} took {end_time - start_time} seconds')

    # Save the output wav file for this chunk
    output_file = f'tts_output_{i + 1}.wav'
    sf.write(output_file, speech.numpy(), samplerate=16000)
    # sf.write(output_file, wav, rate)

    # Put the filename into the queue
    queue.put(output_file)


# Define a function to play audio
def play_audio(queue):
    while True:
        # Wait for a filename to be added to the queue
        output_file = queue.get()

        # Break the loop if the sentinel value is seen
        if output_file == SENTINEL:
            break

        # Play the audio file
        playsound(output_file)


def contains_only_special_characters(string):
    pattern = r"^[^\w\s]*$"  # \w matches any word character (equal to [a-zA-Z0-9_]), \s matches any whitespace character (spaces, tabs, line breaks)
    match = re.match(pattern, string)
    return match is not None


def tts_chunk_by_chunk(input_text, callback=None, prefix=""):
    # Split the input text into chunks at stop characters
    chunks = re.split(r'(?<=\n)|(?<=[^.,!?\n\s][.,!?]\s)', input_text)

    # Process each chunk
    for i, chunk in enumerate(chunks):
        chunk_ingest = chunk.strip()
        print(f'Processing chunk {i + 1} of {len(chunks)}')

        print("chunk_ingest", chunk_ingest)

        if chunk_ingest and not contains_only_special_characters(chunk_ingest):
            # Get the model input for this chunk
            # sample = TTSHubInterface.get_model_input(task, chunk_ingest)



            # Generate the speech audio for this chunk
            start_time = time.time()
            inputs = processor(text=chunk_ingest, return_tensors="pt")
            speech = model.generate_speech(inputs["input_ids"], speaker_embeddings, vocoder=vocoder)
            # wav, rate = TTSHubInterface.get_prediction(task, model, generator, sample)
            end_time = time.time()

            print(f'Text-to-speech generation for chunk {i + 1} took {end_time - start_time} seconds')

            # Save the output wav file for this chunk
            output_file = f'tts_output_{prefix}_{i + 1}.wav'
            sf.write(output_file, speech.numpy(), samplerate=16000)
            # sf.write(output_file, wav, rate)

            # Add the filename to the audio queue
            audio_queue.put(output_file)

    # Call the callback function if it was provided
    if callback is not None:
        callback()


# 🚥🚥🚥

# Create two queues: one for text-to-speech conversion and another for playing audio files
tts_queue = Queue()
audio_queue = Queue()


def tts_worker():
    while True:
        # Wait for a chunk of text to be added to the queue
        text, callback = tts_queue.get()
        prefix = str(time.time())
        print('🎯 text for TTS', text)

        # Process the text
        tts_chunk_by_chunk(text, callback=callback, prefix=prefix)

        # Mark the task as done
        tts_queue.task_done()

        # Let's not hog the CPU
        time.sleep(0.1)


def audio_worker():
    while True:
        # Wait for a filename to be added to the queue
        output_file = audio_queue.get()

        print("output_file", output_file, output_file == SENTINEL)

        # Break the loop if the sentinel value is seen
        if output_file != SENTINEL:
            # Play the audio file
            playsound(output_file)

        # Mark the task as done
        audio_queue.task_done()

        # Let's not hog the CPU
        time.sleep(0.1)


# Start the worker threads
print("starting tts worker")
tts_worker_thread = threading.Thread(target=tts_worker, daemon=True)
tts_worker_thread.start()

print("starting audio worker")
audio_worker_thread = threading.Thread(target=audio_worker, daemon=True)
audio_worker_thread.start()
