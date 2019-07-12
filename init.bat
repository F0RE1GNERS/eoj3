@echo off
echo "Before you start, please make sure you have:"
echo "Copied the local_settings.py to /eoj3/local_settings.py"
echo "Copied the db.sqlite3 to /db.sqlite3"
echo "Redis is running at localhost:6379"
echo "=============================================================="

@echo on
pip install -r requirements.txt

cd static
npm install && npm install gulp-less && start npm start && python manage.py migrate && python manage.py makemigrations && python manage.py runserver