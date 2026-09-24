# Video Speaker Labeler

A small local tool for labeling **who speaks first** in each video: the **on-screen** actor or the **off-screen** speaker.
The label tells the model which diarized audio track belongs to the on-screen actor (diarization tags the first speaker as **A**):

| Who speaks first | On-screen actor's diarized track |
|---|---|
| On-screen  | **A** |
| Off-screen | **B** |
| Unclear    | (blank; leave it out of training) |

## Install (Windows app)

1. Download `VideoLabeler-Setup-<version>.exe` from the [latest release](https://github.com/iqrarwaqas/Video-Labeler/releases/latest) and run it. No admin rights are needed.
2. Start **Video Speaker Labeler** from the Start menu. A console window opens along with the app in your browser. Keep the window open while labeling and close it to quit.

**Updates:** when a new version is released, the app shows a banner. Click **Update now**: the app closes, installs the new version and reopens. Your labels and settings are kept.

Windows may show "Windows protected your PC" because the installer isn't code-signed. Click **More info → Run anyway**.

## Setup from source (once)

```bash
pip install -r requirements.txt
```

## Run

```bash
python main.py --videos "D:\data\videos" --project "Batch_01"
```

The app opens in your browser at http://127.0.0.1:5000. You can also run `python main.py` with no arguments and fill in the project name and folders on the start screen. The app remembers the last project you used.

Options:

| Flag | Meaning |
|---|---|
| `--videos DIR` | Folder with the videos (`.mp4 .mov .webm .mkv .avi .m4v`) |
| `--project NAME` | Project name, shown in the app and used for the output file name (default: the videos folder name) |
| `--output DIR` | Where `<project>_labels.xlsx` is written (default: an `output` folder next to the videos folder) |
| `--import FILE` | Seed labels from the old sheet (`Video_Name`, `Onscreen_Speaker` = a/b). Existing labels are never overwritten. |
| `--port N` | Port (default 5000) |
| `--host 0.0.0.0` | Let other PCs on the network open the app |

## How to label

1. Watch the video.
2. Click **On-screen**, **Off-screen** or **Unclear / Skip** (or press `1` / `2` / `3`).
3. The label is saved straight away and the next video opens.

Shortcuts: `←` / `→` previous/next · `Space` play/pause · `R` replay · `N` next unlabeled video.
The sidebar lists every video with a colored dot (green = on-screen, orange = off-screen, grey = unclear).

**Resume:** open the same project again and the app continues at the first unlabeled video. If you go back to a video you already labeled, its label is highlighted. Click another option to change it, or click **Clear label**.

## Output: `output/<project>_labels.xlsx`

| Project | Video_Name | Video_File | First_Speaker | Onscreen_Diarized_Label | Labeled_At |
|---|---|---|---|---|---|
| Batch_01 | video1 | video1.mp4 | onscreen | A | 2026-09-24 13:20:00 |
| Batch_01 | video4 | video4.mp4 | offscreen | B | 2026-09-24 13:21:10 |

- The file is updated after every click, and each video has only one row (changing a label updates that row).
- Each project has its own file, so several projects can share one output folder.
- If the output folder has an old `labels.xlsx` from before project names existed, its labels are copied into the first project you open there. The old file is left untouched.
- **Close the labels file in Excel while labeling.** Excel locks the file. If it's open, the app shows a warning and nothing is lost: close Excel and click the label again.
- Use one project per person. Two people must not label into the same project file at the same time.

## Troubleshooting

- **"This video can't be played in the browser"**: use Chrome or Edge. `.avi` and some `.mkv`/`.mov` codecs don't play in browsers. Convert them to MP4:
  `ffmpeg -i in.avi -c:v libx264 -c:a aac out.mp4`

## Releasing a new version (maintainers)

1. Update `__version__` in `main.py`, e.g. `"1.1.0"`, and commit.
2. Tag and push the tag:
   ```bash
   git tag v1.1.0
   git push origin v1.1.0
   ```
3. The **Release** GitHub Action builds `VideoLabeler-Setup-1.1.0.exe` and publishes it as a GitHub Release. Installed apps see the update the next time they start.

The tag must match `__version__`, or the build fails. The repo must be public so that installed apps can check for updates and download them.

To build the installer locally, install [Inno Setup 6](https://jrsoftware.org/isdl.php) and run:

```bash
pip install pyinstaller
pyinstaller packaging/VideoLabeler.spec --noconfirm
iscc /DAppVersion=1.1.0 installer\VideoLabeler.iss
```

The installer is written to `dist/`.
