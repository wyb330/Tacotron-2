import argparse
from hparams import hparams, hparams_debug_string
import tensorflow as tf
from infolog import log
from multi_speaker.synthesizer import Synthesizer
import os
import nltk
from konlpy.tag import Kkma
from tqdm import tqdm
import numpy as np
from datasets import audio


def generate_fast(model, text, speaker_id, play=True):
    mels = model.run(text, speaker_id, play)
    return mels


def open_file(filename):
    try:
        f = open(filename, encoding='utf8')
    except UnicodeDecodeError:
        f = open(filename)

    return f


def change_file_ext(file, new_ext):
    parts = file.split('.')
    parts[-1] = new_ext[1:]
    return '.'.join(parts)


def read(args, hparams, checkpoint_path):
    log(hparams_debug_string())
    if not os.path.exists(args.book):
        raise ValueError('{}: {}'.format('No such file or directory', args.book))

    speaker_id = args.speaker_id
    synth = Synthesizer()
    synth.load(checkpoint_path, hparams)

    with open_file(args.book) as f:
        text = f.read()
        if args.lang == 'kr':
            kkma = Kkma()
            sents = kkma.sentences(text)
        else:
            sents = nltk.sent_tokenize(text)

        for i, line in enumerate(sents):
            try:
                text = line.strip()
                if text:
                    log('{}/{}   {}'.format(i + 1, len(sents), text))
                    generate_fast(synth, text, speaker_id)
            except Exception as e:
                log(e)
                break


def publish(args, hparams, checkpoint_path):
    log(hparams_debug_string())
    if not os.path.exists(args.book):
        raise ValueError('{}: {}'.format('No such file or directory', args.book))

    speaker_id = args.speaker_id
    synth = Synthesizer()
    synth.load(checkpoint_path, hparams)

    with open_file(args.book) as f:
        text = f.read()
        if args.lang == 'kr':
            kkma = Kkma()
            sents = kkma.sentences(text)
        else:
            sents = nltk.sent_tokenize(text)

        full_mels = None
        silence = np.full((100, hparams.num_mels), hparams.min_level_db, np.float32)
        for i, line in enumerate(tqdm(sents)):
            text = line.strip()
            if text:
                mels = generate_fast(synth, text, speaker_id, play=False)
                if i > 0:
                    full_mels = np.concatenate((full_mels, silence), axis=0)  # padding silence between sents
                    full_mels = np.concatenate((full_mels, mels), axis=0)
                else:
                    full_mels = mels

        save_path = change_file_ext(args.book, '.wav')
        log('saving to wav file...')
        wav = audio.inv_mel_spectrogram(full_mels.T, hparams)
        audio.save_wav(wav, save_path, sr=hparams.sample_rate)


def prepare_run(args):
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

    run_name = args.model
    taco_checkpoint = os.path.join('logs-' + run_name, 'taco_' + args.checkpoint)
    return taco_checkpoint


def main():
    accepted_modes = ['read', 'publish']
    parser = argparse.ArgumentParser()
    parser.add_argument('--base_dir', default='D:/voice/MultiSpeaker')
    parser.add_argument('--checkpoint', default='pretrained/', help='Path to model checkpoint')
    parser.add_argument('--model', default='MultiSpeaker')
    parser.add_argument('--mode', default='publish', help='mode of run: can be one of {}'.format(accepted_modes))
    parser.add_argument('--book', default='D:/voice/MultiSpeaker/eval.txt', required=True,
                        help='Text file contains list of texts to be synthesized')
    parser.add_argument('--speaker_id', default=2, type=int)
    parser.add_argument('--lang', default='kr')
    args = parser.parse_args()

    accepted_models = ['Tacotron', 'WaveNet', 'Both', 'Tacotron-2', 'MultiSpeaker']

    if args.model not in accepted_models:
        raise ValueError('please enter a valid model to synthesize with: {}'.format(accepted_models))
    if args.mode not in accepted_modes:
        raise ValueError('please enter a valid mode to synthesize with: {}'.format(accepted_modes))

    checkpoint = prepare_run(args)
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

    if args.mode == 'read':
        read(args, hparams, checkpoint_path)
    elif args.mode == 'publish':
        publish(args, hparams, checkpoint_path)


if __name__ == '__main__':
    main()

