# Boris

Automatic Goldeneye degen stats. A lot of stuff should be fixed and improved, but it seems good enough for now. I've done >2000 attempts on Bunker 1 with it. Here is one hour of me using it: [YouTube](https://www.youtube.com/watch?v=kUyHAwphZ1c).

## Features

- Automatically counts attempts and time spent
- End session/change level by going to level select screen

## Installation

Prereqs: `pip3 install mss numpy opencv-python pynput`

Then just download the repo (including the `screens/` folder) and run `Boris.py` with Python 3.

## Troubleshooting

- If it doesn't recognize level screens, you probably have much different color settings or worse quality capture than I have. Try adjusting the match threshold % using __-__ and __+__ keys on your keyboard. 

## Credits

- Image comparison function and general inspiration from [Auto-Split](https://github.com/Toufool/Auto-Split)
