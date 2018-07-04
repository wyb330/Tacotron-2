import os
from hparams import hparams_debug_string
from multi_speaker.synthesizer import Synthesizer
from tqdm import tqdm
from time import sleep
from infolog import log
import tensorflow as tf
import random
from tacotron.utils.text_kr import h2j, is_hanguel, normalize_number


def generate_fast(model, text, speaker_id=1):
    model.synthesize(text, None, None, None, None, speaker_id)


def run_live(args, checkpoint_path, hparams):
    # Log to Terminal without keeping any records in files
    log(hparams_debug_string())
    synth = Synthesizer()
    synth.load(checkpoint_path, hparams)

    # Generate fast greeting message
    greetings = 'Hello, Welcome to the Live testing tool. Please type a message and I will try to read it!'
    log(greetings)
    generate_fast(synth, greetings)

    # Interaction loop
    while True:
        try:
            text = input()
            if text == 'quit':
                break
            if args.speaker_id is None:
                speaker_id = random.choice(list(range(1, args.num_speakers)))
            else:
                speaker_id = args.speaker_id
            if text:
                generate_fast(synth, text, speaker_id)

        except KeyboardInterrupt:
            leave = 'Thank you for testing our features. see you soon.'
            log(leave)
            generate_fast(synth, leave)
            sleep(2)
            break


def run_eval(args, checkpoint_path, output_dir, hparams, sentences):
    eval_dir = os.path.join(output_dir, 'eval')
    log_dir = os.path.join(output_dir, 'logs-eval')

    if args.model in ('Both', 'Tacotron-2'):
        assert os.path.normpath(eval_dir) == os.path.normpath(args.mels_dir)  # mels_dir = wavenet_input_dir

    # Create output path if it doesn't exist
    os.makedirs(eval_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(os.path.join(log_dir, 'wavs'), exist_ok=True)
    os.makedirs(os.path.join(log_dir, 'plots'), exist_ok=True)

    log(hparams_debug_string())
    synth = Synthesizer()
    synth.load(checkpoint_path, hparams)

    with open(os.path.join(eval_dir, 'map.txt'), 'w') as file:
        for i, text in enumerate(tqdm(sentences)):
            values = text.split('|')
            if len(values) == 1:
                raise ValueError('invalid "speaker_id|text" format')
            speak_id = values[0]
            text = values[1]
            if is_hanguel(text):
                text = normalize_number(text)
                # 한글을 자소 단위로 쪼갠다.
                text = h2j(text)
            mel_filename = synth.synthesize(text, i + 1, eval_dir, log_dir, None, speak_id)

            file.write('{}|{}\n'.format(text, mel_filename))
    log('synthesized mel spectrograms at {}'.format(eval_dir))
    return eval_dir


def run_synthesis(args, checkpoint_path, output_dir, hparams):
    GTA = (args.GTA == 'True')
    if GTA:
        synth_dir = os.path.join(output_dir, 'gta')

        # Create output path if it doesn't exist
        os.makedirs(synth_dir, exist_ok=True)
    else:
        synth_dir = os.path.join(output_dir, 'natural')

        # Create output path if it doesn't exist
        os.makedirs(synth_dir, exist_ok=True)

    metadata_filename = os.path.join(args.base_dir, args.input_dir, 'train.txt')
    log(hparams_debug_string())
    synth = Synthesizer()
    synth.load(checkpoint_path, hparams, gta=GTA)
    with open(metadata_filename, encoding='utf-8') as f:
        metadata = [line.strip().split('|') for line in f]
        frame_shift_ms = hparams.hop_size / hparams.sample_rate
        hours = sum([int(x[4]) for x in metadata]) * frame_shift_ms / (3600)
        log('Loaded metadata for {} examples ({:.2f} hours)'.format(len(metadata), hours))

    log('starting synthesis')
    mel_dir = os.path.join(args.base_dir, args.input_dir, 'mels')
    wav_dir = os.path.join(args.base_dir, args.input_dir, 'audio')
    with open(os.path.join(synth_dir, 'map.txt'), 'w') as file:
        for i, meta in enumerate(tqdm(metadata)):
            speaker_id = int(meta[5])
            text = meta[6]
            mel_filename = os.path.join(mel_dir, meta[1])
            wav_filename = os.path.join(wav_dir, meta[0])
            mel_output_filename = synth.synthesize(text, i + 1, synth_dir, None, mel_filename, speaker_id)

            file.write('{}|{}|{}|{}|{}\n'.format(wav_filename, mel_filename, mel_output_filename, speaker_id, text))
    log('synthesized mel spectrograms at {}'.format(synth_dir))
    return os.path.join(synth_dir, 'map.txt')


def multispeaker_synthesize(args, hparams, checkpoint, sentences=None):
    output_dir = 'tacotron_' + args.output_dir

    try:
        checkpoint_path = tf.train.get_checkpoint_state(checkpoint).model_checkpoint_path
        log('loaded model at {}'.format(checkpoint_path))
    except AttributeError:
        # Swap logs dir name in case user used Tacotron-2 for train and Both for test (and vice versa)
        if 'Both' in checkpoint:
            checkpoint = checkpoint.replace('Both', 'Tacotron-2')
        elif 'Tacotron-2' in checkpoint:
            checkpoint = checkpoint.replace('Tacotron-2', 'Both')
        else:
            raise AssertionError('Cannot restore checkpoint: {}, did you train a model?'.format(checkpoint))

        try:
            # Try loading again
            checkpoint_path = tf.train.get_checkpoint_state(checkpoint).model_checkpoint_path
            log('loaded model at {}'.format(checkpoint_path))
        except:
            raise RuntimeError('Failed to load checkpoint at {}'.format(checkpoint))

    if args.mode == 'eval':
        return run_eval(args, checkpoint_path, output_dir, hparams, sentences)
    elif args.mode == 'synthesis':
        return run_synthesis(args, checkpoint_path, output_dir, hparams)
    else:
        run_live(args, checkpoint_path, hparams)
