# Boris

- Automatically counts attempts and time spent

![Screenshot](https://media.discordapp.net/attachments/1053276619520888854/1404206094057738270/vlcsnap-2025-08-10-22h49m25s008.png?ex=689a5855&is=689906d5&hm=41093181348ef198e24118a0aa41d4e4c4f1ee6fc207d5c68c53c40aab57829a&=&format=webp&quality=lossless&width=2004&height=1128)

## Installation

### Self-contained exe (for Windows)

You can find a self-contained exe file in the [releases section](https://github.com/lambdan/Boris/releases).

Windows will likely scream about malware so you'll have to trust me.

### Manually

Prereqs: `pip3 install mss=10.0.0 numpy==2.2.6 opencv-python==4.12.0.88 pynput==1.8.1`

Then just download the repo and run `Boris.py` with Python 3.

### Calibration

If your capture quality is very different from mine you might have to replace `ohmss.png` and `black.png`

## Credits

- Image comparison function and general inspiration from [Auto-Split](https://github.com/Toufool/Auto-Split)
