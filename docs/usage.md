```
 usage: pymterm [-h] [-s SESSION] [-p PORT] [-l LOG] [-t TERM_NAME]
               [--color_theme COLOR_THEME] [-d] [-dd] [--config CONFIG]
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
  -t TERM_NAME, --term_name TERM_NAME
                        the terminal type name
  --color_theme COLOR_THEME
                        the terminal color theme
  -d, --debug           show debug information in log file and console
  -dd, --debug_more     show more debug information in log file and console
  --config CONFIG       use the give file as config file, otherwise will find pymterm.json in current directory as config file
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
