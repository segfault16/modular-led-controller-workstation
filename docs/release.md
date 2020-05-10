````bash
pipenv install -d
pipenv run python setup.py egg_info
pipenv run pyinstaller server.spec
````