# Code from https://github.com/carpedm20/multi-speaker-tacotron-tensorflow/blob/master/app.py

import argparse
import os,traceback
import hashlib
from flask_cors import CORS
from flask import Flask, request, render_template, jsonify, send_from_directory, send_file
from multi_speaker.synthesizer import Synthesizer
from hparams import hparams
from pydub import silence, AudioSegment
import tensorflow as tf
from tacotron.utils.text_kr import h2j

ROOT_PATH = "web"
AUDIO_DIR = "audio"
AUDIO_PATH = os.path.join(ROOT_PATH, AUDIO_DIR)

base_path = os.path.dirname(os.path.realpath(__file__))
static_path = os.path.join(base_path, 'web/static')

global_config = None
synthesizer = Synthesizer()
app = Flask(__name__, root_path=ROOT_PATH, static_url_path='')
CORS(app)


def add_postfix(path, postfix):
    path_without_ext, ext = path.rsplit('.', 1)
    return "{}.{}.{}".format(path_without_ext, postfix, ext)


def match_target_amplitude(sound, target_dBFS):
    change_in_dBFS = target_dBFS - sound.dBFS
    return sound.apply_gain(change_in_dBFS)


def amplify(path):
    sound = AudioSegment.from_file(path)

    nonsilent_ranges = silence.detect_nonsilent(
        sound, silence_thresh=-50, min_silence_len=300)

    idx = 0
    new_sound = None
    amplified_sound = None
    for idx, (start_i, end_i) in enumerate(nonsilent_ranges):
        if idx == len(nonsilent_ranges) - 1:
            end_i = None

        amplified_sound = match_target_amplitude(sound[start_i:end_i], -20.0)

    if idx == 0:
        new_sound = amplified_sound
    else:
        new_sound = new_sound.append(amplified_sound)

    if idx < len(nonsilent_ranges) - 1:
        new_sound = new_sound.append(sound[end_i:nonsilent_ranges[idx + 1][0]])
    return new_sound.export("out.mp3", format="mp3")


def generate_audio_response(text, speaker_id):
    global global_config

    hashed_text = hashlib.md5(text.encode('utf-8')).hexdigest()

    relative_dir_path = os.path.join(AUDIO_DIR, "{}.{}.wav".format(hashed_text, speaker_id))
    real_path = os.path.join(ROOT_PATH, relative_dir_path)
    os.makedirs(os.path.dirname(real_path), exist_ok=True)

    try:
        synthesizer.predict(text, real_path, speaker_id)
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False), 400

    if os.path.exists(real_path):
        return send_file(
            relative_dir_path,
            mimetype="audio/wav",
            as_attachment=True,
            attachment_filename=real_path)
    else:
        return jsonify(success=False), 500


@app.route('/')
def index():
    text = request.args.get('text') or "듣고 싶은 문장을 입력해 주세요."
    return render_template('index.html', text=text)


@app.route('/generate')
def view_method():
    text = request.args.get('text')
    jamo = h2j(text)
    speaker_id = int(request.args.get('speaker_id'))

    if text:
        return generate_audio_response(jamo, speaker_id)
    else:
        return jsonify(success=True), 200


@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory(
        os.path.join(static_path, 'js'), path)


@app.route('/css/<path:path>')
def send_css(path):
    return send_from_directory(
        os.path.join(static_path, 'css'), path)


@app.route('/audio/<path:path>')
def send_audio(path):
    return send_from_directory(
        os.path.join(static_path, 'audio'), path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--load_path', default='logs-MultiSpeaker/taco_pretrained/')
    parser.add_argument('--num_speakers', default=10, type=int)
    parser.add_argument('--port', default=51000, type=int)
    parser.add_argument('--debug', default=False, type=bool)
    config = parser.parse_args()

    if os.path.exists(config.load_path):
        checkpoint = config.load_path
        try:
            checkpoint_path = tf.train.get_checkpoint_state(checkpoint).model_checkpoint_path
        except AttributeError:
            raise RuntimeError('Failed to load checkpoint at {}'.format(checkpoint))

        global_config = config
        synthesizer.load(checkpoint_path, hparams)
    else:
        print(" [!] load_path not found: {}".format(config.load_path))

    app.run(host='127.0.0.1', port=config.port, debug=config.debug)
