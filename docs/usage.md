```
usage: pymterm [-h] [-s SESSION] [-p PORT] [-l LOG] [-t {xterm-256color}]
               [--color_theme {tango,solarized_dark,solarized_light,terminal}]
               [-d] [-dd] [--config CONFIG]
               [--render {cairo,pygame,native,kivy,console}]
               [--font_file FONT_FILE] [--font_name FONT_NAME]
               [--font_size FONT_SIZE] [--session_type {ssh,pty}]
               [user@host]

a multiple tab terminal emulator in python

positional arguments:
  user@host

optional arguments:
  -h, --help            show this help message and exit
  -s SESSION, --session SESSION
                        name of session to use
  -p PORT, --port PORT  port of host to connect to
  -l LOG, --log LOG     logging file path
  -t {xterm-256color}, --term_name {xterm-256color}
                        the terminal type name
  --color_theme {tango,solarized_dark,solarized_light,terminal}
                        the terminal color theme, default is tango
  -d, --debug           show debug information in log file and console
  -dd, --debug_more     show more debug information in log file and console
  --config CONFIG       use the give file as config file, otherwise will find
                        pymterm.json in save directory with pymterm.py or
                        pymterm directory in user config directroy or parent
                        directory of pymterm.py as config file
  --render {cairo,pygame,native,kivy,console}
                        choose a render system
  --font_file FONT_FILE
                        provide a font file
  --font_name FONT_NAME
                        provide a font name
  --font_size FONT_SIZE
                        given a font size
  --session_type {ssh,pty}
```
# Keyboard shortcuts
```
shift+Pgup scroll history up
shift+Pgdown scroll history down
ctrl+Ins copy
shift+Ins paste
```
# Examples
## Run as local terminal
```
python pymterm.py --session_type pty
```
## Connect to remote sever through ssh
```
python pymterm.py --session_type ssh user@remote
```
