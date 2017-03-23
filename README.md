# ECNU Online Judge
eoj3: A new version of eoj.

## TODO
+ rewrite hint messages
+ allowed_lang in Contest
+ pagination on standings page
+ friendly time input
+ markdown safe
+ csrf_protect on function-based views
+ remember me on login page
+ a lot about contest todo: privilege, public/private
+ images and files in problems
+ submission privileges

## Installation

Make sure things like apache2, mysql and python3 are already installed and well updated.

1. Install wsgi: `sudo apt-get install libapache2-mod-wsgi-py3`
2. Create a config: `sudo vi /etc/apache2/sites-available/eoj.conf`, and put the following inside:
```
<VirtualHost *:80>
    ServerName www.yourdomain.com
    <Directory /home/eoj3/static>
        Require all granted
    </Directory>
    WSGIScriptAlias / /home/eoj3/eoj3/wsgi.py
    <Directory /home/eoj3/eoj3>
        <Files wsgi.py>
            Require all granted
        </Files>
    </Directory>
</VirtualHost>
```
3. Config locally: `cp local_settings.example.py local_settings.py` and change it if you want.
4. Create data dir and add privilege:
```
cd eoj3
mkdir data
sudo chgrp -R www-data data
sudo chmod -R g+w data
```
5. Migrate Now!
```
python3 manage.py makemigrations
python3 manage.py migrate
```
6. Enable: `sudo a2ensite eoj`.

So close! You still have to create a judge server.

## Judge Server
Unfortunately, the judge server is somehow isolated from judge website
for future convenience. Judge Server can be found at [eJudge](https://github.com/ultmaster/ejudge).
For more information about Judge Server, please read the `README` there, but note that the
`README` is also yet to be accomplished.

## Usage

TODO