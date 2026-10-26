# Avian TF-box Annotator

A Codex skill for marking bird sounds on spectrograms.

Codex looks at your audio's spectrogram and draws boxes around visible sounds. Open the review page to listen, check the boxes, and leave notes.

- **Cyan boxes** show individual sounds.
- **Orange dashed boxes** combine sounds with gaps of up to 0.5 seconds.
- Export the boxes and audio for use in Raven.

## Install

```sh
git clone https://github.com/Fly-Carrot/avian-tfbox-annotator.git
cd avian-tfbox-annotator
```

Copy the `avian-tfbox-annotator` folder into your Codex skills folder, usually `~/.codex/skills/`.

You need Python 3.10 or later, FFmpeg, NumPy, and Pillow. To set up the Python packages:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Use it

Give Codex your audio folder and ask:

> Use $avian-tfbox-annotator to mark bird sounds in these 3-second recordings. Show the original boxes and the 0.5-second merged boxes. Create a review page and Raven tables.

The skill also supports 10-second clips. Codex keeps the source audio and saves the results in a new folder.

## Review the results

Open the generated `index.html` in your browser. Play the audio, switch between recordings, compare boxes, and add notes. Export your notes to keep a copy.

## Try an example

```sh
.venv/bin/python examples/make_demo.py --out demo
```

Open `demo/review/index.html`. The example uses three synthetic chirps.

[More options and commands](avian-tfbox-annotator/references/guide.md)

## License

[MIT](LICENSE) · David Chen. Icon credits are in the [Lucide license](avian-tfbox-annotator/assets/lucide.LICENSE).
