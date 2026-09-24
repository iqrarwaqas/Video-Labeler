# Video Speaker Labeler

A small local tool for labeling **who speaks first** in each video: the **on-screen** actor or the **off-screen** speaker.
The label tells the model which diarized audio track belongs to the on-screen actor (diarization tags the first speaker as **A**):

| Who speaks first | On-screen actor's diarized track |
|---|---|
| On-screen  | **A** |
| Off-screen | **B** |
| Unclear    | (blank; leave it out of training) |

## Setup (once)

```bash
pip install -r requirements.txt
```

## Run

```bash
python main.py --videos "D:\data\videos"
```

The app opens in your browser at http://127.0.0.1:5000. You can also run `python main.py` with no arguments and type the folder path on the start screen. The app remembers the last folder you used.

Options:

| Flag | Meaning |
|---|---|
| `--videos DIR` | Folder with the videos (`.mp4 .mov .webm .mkv .avi .m4v`) |
| `--output DIR` | Where `labels.xlsx` is written (default: an `output` folder next to the videos folder) |
| `--import FILE` | Seed labels from the old sheet (`Video_Name`, `Onscreen_Speaker` = a/b). Existing labels are never overwritten. |
| `--port N` | Port (default 5000) |
| `--host 0.0.0.0` | Let other PCs on the network open the app |

## How to label

1. Watch the video.
2. Click **On-screen**, **Off-screen** or **Unclear / Skip** (or press `1` / `2` / `3`).
3. The label is saved straight away and the next video opens.

Shortcuts: `←` / `→` previous/next · `Space` play/pause · `R` replay · `N` next unlabeled video.
The sidebar lists every video with a colored dot (green = on-screen, orange = off-screen, grey = unclear).

**Resume:** open the same folder again and the app continues at the first unlabeled video. If you go back to a video you already labeled, its label is highlighted. Click another option to change it, or click **Clear label**.

## Output: `output/labels.xlsx`

| Video_Name | Video_File | First_Speaker | Onscreen_Diarized_Label | Labeled_At |
|---|---|---|---|---|
| video1 | video1.mp4 | onscreen | A | 2026-09-24 13:20:00 |
| video4 | video4.mp4 | offscreen | B | 2026-09-24 13:21:10 |

- The file is updated after every click, and each video has only one row (changing a label updates that row).
- **Close `labels.xlsx` in Excel while labeling.** Excel locks the file. If it's open, the app shows a warning and nothing is lost: close Excel and click the label again.
- Use one project folder per person. Two people must not label into the same `labels.xlsx` at the same time.

## Troubleshooting

- **"This video can't be played in the browser"**: use Chrome or Edge. `.avi` and some `.mkv`/`.mov` codecs don't play in browsers. Convert them to MP4:
  `ffmpeg -i in.avi -c:v libx264 -c:a aac out.mp4`
