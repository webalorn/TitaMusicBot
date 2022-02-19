import yaml, magic, random
from pathlib import Path

dir_path = Path(__file__).absolute().parent
pipe_path = "/tmp/titapipe"


def is_audio(audio):
    return audio.is_file() and magic.from_file(audio, mime=True).split('/')[0] == 'audio'

def read_config():
    with open(str(dir_path / 'config.yml')) as config_file:
        return yaml.load(config_file, Loader=yaml.FullLoader)

def get_files_in(path):
    if path.is_file():
        return [path]
    else:
        audio_files = []
        for audio in path.iterdir():
            if is_audio(audio):
                audio_files.append(audio)
        random.shuffle(audio_files)
        return audio_files