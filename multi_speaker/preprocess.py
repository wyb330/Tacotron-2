import argparse
from multiprocessing import cpu_count
import os
from tqdm import tqdm
from multi_speaker import preprocessor
from hparams import hparams
from datasets import vctk


def preprocess(args, input_folders, out_dir, hparams):
    mel_dir = os.path.join(out_dir, 'mels')
    wav_dir = os.path.join(out_dir, 'audio')
    linear_dir = os.path.join(out_dir, 'linear')
    os.makedirs(mel_dir, exist_ok=True)
    os.makedirs(wav_dir, exist_ok=True)
    os.makedirs(linear_dir, exist_ok=True)
    if len(input_folders) > 1:
        datasets = args.dataset.split(',')
        metadata = preprocessor.build_from_dirs(hparams, input_folders, datasets, mel_dir, linear_dir, wav_dir, args.n_jobs,
                                                tqdm=tqdm)
    elif args.dataset == 'VCTK':
        metadata = vctk.build_from_path(hparams, input_folders[0], mel_dir, linear_dir, wav_dir, args.n_jobs, tqdm=tqdm)
    else:
        raise ValueError('not support dataset')

    write_metadata(metadata, out_dir)


def write_metadata(metadata, out_dir):
    with open(os.path.join(out_dir, 'train.txt'), 'w', encoding='utf-8') as f:
        metadata = [m for m in metadata if m]
        for m in metadata:
            f.write('|'.join([str(x) for x in m]) + '\n')
    mel_frames = sum([int(m[4]) for m in metadata])
    timesteps = sum([int(m[3]) for m in metadata])
    sr = hparams.sample_rate
    hours = timesteps / sr / 3600
    print('Write {} utterances, {} mel frames, {} audio timesteps, ({:.2f} hours)'.format(
        len(metadata), mel_frames, timesteps, hours))
    print('Max input length (text chars): {}'.format(max(len(m[5]) for m in metadata)))
    print('Max mel frames length: {}'.format(max(int(m[4]) for m in metadata)))
    print('Max audio timesteps length: {}'.format(max(m[3] for m in metadata)))


def norm_data(args):
    print('Selecting data folders..')
    data_dirs = args.base_dir.split(',')
    if len(data_dirs) > 1:
        datasets = args.dataset.split(',')
        if len(data_dirs) != len(datasets):
            raise ValueError('mismatch len(base_dir) and len(dataset) ')
        return data_dirs

    supported_datasets = ['VCTK', 'LJSpeech-1.0', 'LJSpeech-1.1', 'M-AILABS', 'KRSPEECH']
    if args.dataset not in supported_datasets:
        raise ValueError('dataset value entered {} does not belong to supported datasets: {}'.format(
            args.dataset, supported_datasets))

    if args.dataset.startswith('VCTK'):
        return [args.base_dir]
    elif args.dataset == 'KRSPEECH':
        return [args.base_dir]


def run_preprocess(args, hparams):
    input_folders = norm_data(args)
    output_folder = args.output
    preprocess(args, input_folders, output_folder, hparams)


def main():
    print('initializing preprocessing..')
    parser = argparse.ArgumentParser()
    parser.add_argument('--base_dir', default='dataset/VCTK-Corpus', required=True)
    parser.add_argument('--dataset', default='VCTK', required=True)
    parser.add_argument('--hparams', default='',
                        help='Hyperparameter overrides as a comma-separated list of name=value pairs')
    parser.add_argument('--output', default='training_data')
    parser.add_argument('--n_jobs', type=int, default=cpu_count())
    args = parser.parse_args()

    modified_hp = hparams.parse(args.hparams)

    run_preprocess(args, modified_hp)


if __name__ == '__main__':
    main()
