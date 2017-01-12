# Install dependcies
 - Install python 2.7
 - Install pygui
   - Clone/Download pygui from https://github.com/stonewell/pygui/
   - Install pygui
     ```
     cd pygui && python setup.py install
     ```
 - Install dependencies
 ```
 pip install paramiko appdirs pyopengl pyopengl-accelerate numpy functools32
 
 ```
 - Install Platform specific dependencies
   - Windows
   ```
   pip install pypiwin32
   
   ```
   - Linux
   ```
   pip install pygtk pycairo
   ```
   - Mac OSX
   ```
   pip install pycoco
   ```