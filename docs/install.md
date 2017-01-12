# Install dependcies
 - Install python 2.7
 - Install pygui
   - Clone/Download pygui from https://github.com/stonewell/pygui/
   - Install pygui
     ```
     cd pygui && python setup.py install
     ```
 - Install dependencies
   - Install libssl-dev,python-gtk2, python-gtkglext1 on linux(Ubuntu) before using pip to install dependency
  
 ```
 pip install paramiko appdirs pyopengl pyopengl-accelerate numpy functools32
 
 ```
 - Install Platform specific dependencies
   - Windows
   ```
   pip install pypiwin32
   
   ```
   - Mac OSX
   ```
   pip install pycoco
   ```
