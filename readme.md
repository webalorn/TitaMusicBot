# Tita music bot

A bot to play audio files stored on your computer to a discord channel.

## Dependencies

```bash
python3 -m pip install -U discord.py[voice] pyyaml python-magic
```

You should also have the command `tree` installed (`apt install tree` on Ubuntu/Debian).

## Configuration

Create a bot on the [discord applications page](https://discord.com/developers/applications) and copy the token. You will find plenty of tutorials online.

Then, create a `config.yml` file with the following format:

```yaml
token: '[TOKEN]'
admin_id: [ID]
```

- `token` should be the bot token
- `admin_id` is optional. If set, the bot will automatically join the audio channel where the specified user is. You can find instruction online on how to find you user id.

### Alias

I recommend setting an alias like `alias pt='python3 /absolute/path/to/play-music.py'`.

## Usage

First, launch the bot as a background process or in another terminal (`python3 titaMusic.py`).

Then, use the command `python3 /absolute/path/to/play-music.py path/of/music` or `pt path/of/music`. Tita will play all the musics in the directory `music`, or play the `music` file if it is an audio file. You can use this command. The files are played in a random order and in a loop.

### Bot commands

The bot also accepts some commands over the terminal : `join`, `music`, `stop`, `pause`, `resume`, `skip`.