* install XCode

* in the preferences, downloads, install Command Line Tools

* install homebrew

* install python

```
brew install python
```

* clean up some things

```
pip install pip --upgrade

# yes this is necessary
pip uninstall setuptools
pip install setuptools
```

* install PostgreSQL latest

```
brew install --no-tcl postgresql
```

* install virtualenv

```
pip install virtualenv
```

* download helios-server

```
git clone git@github.com:benadida/helios-server
```

* cd into the helios-server directory

* create a virtualenv:

```
virtualenv venv
```

* activate virtual environment

```
source venv/bin/activate
````

* install requirements

```
pip install -r requirements.txt
```

* reset database

```
./reset.sh
```

* start server

```
python manage.py runserver
```
