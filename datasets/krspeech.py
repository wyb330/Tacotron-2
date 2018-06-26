from concurrent.futures import ProcessPoolExecutor
from functools import partial
import numpy as np
import os
import datasets.audio as audio
import json
from wavenet_vocoder.util import mulaw_quantize, mulaw, is_mulaw, is_mulaw_quantize


def build_from_path(hparams, input_dirs, mel_dir, linear_dir, wav_dir, n_jobs=12, tqdm=lambda x: x):
    '''Preprocesses the LJ Speech dataset from a given input path into a given output directory.

      Args:
        - hparams: hyper parameters
        - input_dir: input directory that contains the files to prerocess
        - mel_dir: output directory of the preprocessed speech mel-spectrogram dataset
        - linear_dir: output directory of the preprocessed speech linear-spectrogram dataset
        - wav_dir: output directory of the preprocessed speech audio dataset
        - n_jobs: Optional, number of worker process to parallelize across
        - tqdm: Optional, provides a nice progress bar

      Returns:
        A list of tuples describing the training examples. This should be written to train.txt
    '''

    # We use ProcessPoolExecutor to parallize across processes. This is just an optimization and you
    # can omit it and just call _process_utterance on each input if you want.
    executor = ProcessPoolExecutor(max_workers=n_jobs)
    futures = []
    index = 1
    with open(os.path.join(input_dirs, 'recognition.json'), encoding='utf-8') as f:
        content = f.read()
        info = json.loads(content)
        for wav_path, text in info.items():
            wav_path = os.path.join(input_dirs, wav_path)
            futures.append(executor.submit(
                partial(_process_utterance, mel_dir, linear_dir, wav_dir, index, wav_path, text, hparams)))
            index += 1
    return [future.result() for future in tqdm(futures)]


def _process_utterance(mel_dir, linear_dir, wav_dir, index, wav_path, text, hparams):
    '''Preprocesses a single utterance audio/text pair.

    This writes the mel and linear scale spectrograms to disk and returns a tuple to write
    to the train.txt file.

    Args:
      out_dir: The directory to write the spectrograms into
      index: The numeric index to use in the spectrogram filenames.
      wav_path: Path to the audio file containing the speech input
      text: The text spoken in the input audio file

    Returns:
        - A tuple: (audio_filename, mel_filename, linear_filename, time_steps, mel_frames, linear_frames, text)
    '''

    # Load the audio to a numpy array:
    wav = audio.load_wav(wav_path, sr=hparams.sample_rate)

    # Mu-law quantize
    if is_mulaw_quantize(hparams.input_type):
        # [0, quantize_channels)
        out = mulaw_quantize(wav, hparams.quantize_channels)

        # Trim silences
        start, end = audio.start_and_end_indices(out, hparams.silence_threshold)
        wav = wav[start: end]
        out = out[start: end]

        constant_values = mulaw_quantize(0, hparams.quantize_channels)
        out_dtype = np.int16

    elif is_mulaw(hparams.input_type):
        # [-1, 1]
        out = mulaw(wav, hparams.quantize_channels)
        constant_values = mulaw(0., hparams.quantize_channels)
        out_dtype = np.float32

    else:
        # [-1, 1]
        out = wav
        constant_values = 0.
        out_dtype = np.float32

    # Compute the mel scale spectrogram from the wav
    mel_spectrogram = audio.melspectrogram(wav, hparams).astype(np.float32)
    mel_frames = mel_spectrogram.shape[1]

    if mel_frames > hparams.max_mel_frames and hparams.clip_mels_length:
        return None

    # Compute the linear scale spectrogram from the wav
    linear_spectrogram = audio.linearspectrogram(wav, hparams).astype(np.float32)
    linear_frames = linear_spectrogram.shape[1]

    # sanity check
    assert linear_frames == mel_frames

    # Ensure time resolution adjustement between audio and mel-spectrogram
    fft_size = hparams.n_fft if hparams.win_size is None else hparams.win_size
    l, r = audio.pad_lr(wav, fft_size, audio.get_hop_size(hparams))

    # Zero pad for quantized signal
    out = np.pad(out, (l, r), mode='constant', constant_values=constant_values)
    assert len(out) >= mel_frames * audio.get_hop_size(hparams)

    # time resolution adjustement
    # ensure length of raw audio is multiple of hop size so that we can use
    # transposed convolution to upsample
    out = out[:mel_frames * audio.get_hop_size(hparams)]
    assert len(out) % audio.get_hop_size(hparams) == 0
    time_steps = len(out)

    # Write the spectrogram and audio to disk
    audio_filename = 'speech-audio-{:05d}.npy'.format(index)
    mel_filename = 'speech-mel-{:05d}.npy'.format(index)
    linear_filename = 'speech-linear-{:05d}.npy'.format(index)
    np.save(os.path.join(wav_dir, audio_filename), out.astype(out_dtype), allow_pickle=False)
    np.save(os.path.join(mel_dir, mel_filename), mel_spectrogram.T, allow_pickle=False)
    np.save(os.path.join(linear_dir, linear_filename), linear_spectrogram.T, allow_pickle=False)

    # Return a tuple describing this training example
    return (audio_filename, mel_filename, linear_filename, time_steps, mel_frames, text)
