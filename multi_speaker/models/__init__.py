from .tacotron import MultiSpeakerTacotron


def create_model(name, hparams):
    if name == 'MultiSpeaker':
        return MultiSpeakerTacotron(hparams)
    else:
        raise Exception('Unknown model: ' + name)

