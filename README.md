# pymterm
A multiple tab terminal emulator implemented in python

Render system can using native, opengl, will first try opengl when available otherwise fall back to native render
OpenGL render
 - pygame backend
 - pycairo + pango backend
 - kivy backend
 
UI framework 
 - https://kivy.org
 - https://github.com/stonewell/pygui/

ssh library 
 - https://github.com/paramiko/paramiko

## Dependecy
 - paramiko
 - appdirs
 - pypiwin32/pygtk/pycoco
 - pyopengl pyopengl-accelerate
 - pygame
 - numpy
 - functools32
 - pygtk(pango) pycairo

   
## TODO
- [X] UTF-8 handling
- [X] Scroll history
- [ ] Search in history
- [X] Selection
- [ ] Save sessions
- [ ] whole application configuration
- [ ] IME
- [X] Copy and Paste
- [X] local pty (windows using pipe)
- [X] sftp file transfer
- [ ] X forwarding

## Tools
 - tools/pymter_transfer.py
 ```
usage: pymterm_transfer.py [-h] {upload,download} ...

helper scripts for upload/download files using sftp in command line

positional arguments:
  {upload,download}  transfer action help
    upload           upload file from local system to remote
    download         download file from remote system to local

optional arguments:
  -h, --help         show this help message and exit
 ``` 
 ```
usage: pymterm_transfer.py download [-h] target

positional arguments:
  target      download file remote path

optional arguments:
  -h, --help  show this help message and exit
  ```
  ```
usage: pymterm_transfer.py upload [-h] [target]

positional arguments:
  target      upload target file remote path

optional arguments:
  -h, --help  show this help message and exit
 ```
