import os
import numpy as np
import tensorflow as tf
from multi_speaker.models import create_model
from tacotron.utils.text import text_to_sequence
from tacotron.utils import plot
from datasets import audio
import pyaudio
import wave
from infolog import log
from tacotron.utils.text_kr import h2j, j2h


class Synthesizer:
    def load(self, checkpoint_path, hparams, gta=False, model_name='MultiSpeaker'):
        log('Constructing model: %s' % model_name)
        inputs = tf.placeholder(tf.int32, [1, None], 'inputs')
        input_lengths = tf.placeholder(tf.int32, [1], 'input_lengths')
        speaker_ids = tf.placeholder(tf.int32, [1], 'speaker_ids')
        targets = tf.placeholder(tf.float32, [1, None, hparams.num_mels], 'mel_targets')
        with tf.variable_scope('model') as scope:
            self.model = create_model(model_name, hparams)
            if gta:
                self.model.initialize(inputs, input_lengths, speaker_ids, targets, gta=gta)
            else:
                self.model.initialize(inputs, input_lengths, speaker_ids)
            self.mel_outputs = self.model.mel_outputs
            self.alignment = self.model.alignments[0]

        self.gta = gta
        self._hparams = hparams

        log('Loading checkpoint: %s' % checkpoint_path)
        self.session = tf.Session()
        self.session.run(tf.global_variables_initializer())
        saver = tf.train.Saver()
        saver.restore(self.session, checkpoint_path)

    def synthesize(self, text, index, out_dir, log_dir, mel_filename, speaker_id):
        hparams = self._hparams
        cleaner_names = [x.strip() for x in hparams.cleaners.split(',')]
        seq = text_to_sequence(text, cleaner_names)
        feed_dict = {
            self.model.inputs: [np.asarray(seq, dtype=np.int32)],
            self.model.input_lengths: np.asarray([len(seq)], dtype=np.int32),
            self.model.speaker_ids: np.asarray([speaker_id], dtype=np.int32)
        }

        if self.gta:
            feed_dict[self.model.mel_targets] = np.load(mel_filename).reshape(1, -1, 80)

        if self.gta or not hparams.predict_linear:
            mels, alignment = self.session.run([self.mel_outputs, self.alignment], feed_dict=feed_dict)

        else:
            linear, mels, alignment = self.session.run([self.linear_outputs, self.mel_outputs, self.alignment],
                                                       feed_dict=feed_dict)
            linear = linear.reshape(-1, hparams.num_freq)

        mels = mels.reshape(-1, hparams.num_mels)  # Thanks to @imdatsolak for pointing this out

        if index is None:
            # Generate wav and read it
            wav = audio.inv_mel_spectrogram(mels.T, hparams)
            audio.save_wav(wav, 'temp.wav', sr=hparams.sample_rate)  # Find a better way

            chunk = 512
            f = wave.open('temp.wav', 'rb')
            p = pyaudio.PyAudio()
            stream = p.open(format=p.get_format_from_width(f.getsampwidth()),
                            channels=f.getnchannels(),
                            rate=f.getframerate(),
                            output=True)
            data = f.readframes(chunk)
            while data:
                stream.write(data)
                data = f.readframes(chunk)

            stream.stop_stream()
            stream.close()

            p.terminate()
            return

        # Write the spectrogram to disk
        # Note: outputs mel-spectrogram files and target ones have same names, just different folders
        mel_filename = os.path.join(out_dir, 'speech-mel-{:05d}.npy'.format(index))
        np.save(mel_filename, mels, allow_pickle=False)

        if log_dir is not None:
            # save wav (mel -> wav)
            wav = audio.inv_mel_spectrogram(mels.T, hparams)
            audio.save_wav(wav, os.path.join(log_dir, 'wavs/speech-wav-{:05d}-mel.wav'.format(index)),
                           sr=hparams.sample_rate)

            if hparams.predict_linear:
                # save wav (linear -> wav)
                wav = audio.inv_linear_spectrogram(linear.T, hparams)
                audio.save_wav(wav, os.path.join(log_dir, 'wavs/speech-wav-{:05d}-linear.wav'.format(index)),
                               sr=hparams.sample_rate)

            if self._hparams.lang == 'kr':
                text = j2h(text)
            # save alignments
            plot.plot_alignment(alignment, os.path.join(log_dir, 'plots/speech-alignment-{:05d}.png'.format(index)),
                                info='{}'.format(text), split_title=True)

            # save mel spectrogram plot
            plot.plot_spectrogram(mels, os.path.join(log_dir, 'plots/speech-mel-{:05d}.png'.format(index)),
                                  info='{}'.format(text), split_title=True)

        return mel_filename

    def predict(self, text, out_dir, speaker_id):
        hparams = self._hparams
        cleaner_names = [x.strip() for x in hparams.cleaners.split(',')]
        seq = text_to_sequence(text, cleaner_names)
        feed_dict = {
            self.model.inputs: [np.asarray(seq, dtype=np.int32)],
            self.model.input_lengths: np.asarray([len(seq)], dtype=np.int32),
            self.model.speaker_ids: np.asarray([speaker_id], dtype=np.int32)
        }

        mels, alignment = self.session.run([self.mel_outputs, self.alignment], feed_dict=feed_dict)
        mels = mels.reshape(-1, hparams.num_mels)  # Thanks to @imdatsolak for pointing this out

        # Generate wav and read it
        wav = audio.inv_mel_spectrogram(mels.T, hparams)
        audio.save_wav(wav, out_dir, sr=hparams.sample_rate)  # Find a better way

        return out_dir
