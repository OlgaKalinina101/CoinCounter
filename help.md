Создать новый архив
Compress-Archive -Path * -DestinationPath CoinCounter.zip -Force

Get-ChildItem -Path . -Exclude '.venv', '.idea', 'CoinCounter.zip' |
Where-Object { $_.Name -ne 'CoinCounter.zip' } |
Compress-Archive -DestinationPath 'CoinCounter.zip' -Force


Отправить архив на сервер
scp CoinCounter.zip root@89.22.229.123:/opt/

Разархивировать на сервере
mkdir CoinCounter
unzip CoinCounter.zip -d CoinCounter
cd CoinCounter

pip show django-celery-beat

python manage.py createsuperuser

Создать и активировать заново виртуальное окружение (если надо)
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

Запустить Django
python manage.py migrate
python manage.py collectstatic --noinput

dos2unix run.sh
chmod +x run.sh
./run.sh

tmux kill-session

sudo lsof -i :8001

kill 3162871
kill -9 3162871




Выйти из tmux, не останавливая процессы:
Ctrl + b, затем d

Вернуться:
tmux attach -t coin

Проверить список:
tmux ls

Чтобы полностью убить все процессы:
tmux kill-session -t coin


sudo systemctl start redis-server
sudo systemctl enable redis-server

python manage.py fetch_bank_data

Зайти в доску управления Django
source venv/bin/activate
python manage.py shell
Выйти - ctrl + D

from coin_desk.models import Transaction
Transaction.objects.all().delete()



from coin_desk.tasks import fetch_and_save_statements_task
fetch_and_save_statements_task.delay()

from coin_desk.tasks import notify_about_new_transactions
notify_about_new_transactions.delay()

from coin_desk.tasks import export_new_transactions_to_sheets
export_new_transactions_to_sheets.delay()


Зайти в доску управления sqlite3
cd /opt/CoinCounter
sqlite3 db.sqlite3

.tables                         -- список таблиц
.schema coin_desk_transaction  -- структура таблицы
SELECT * FROM coin_desk_transaction LIMIT 5;

или просто скопировать БД на локалку: scp root@89.22.229.123:/opt/CoinCounter/db.sqlite3 ~/Downloads
Если пишет что сервер уже запущен:
ss -ltnp | grep :8000
kill -9 12345

 

root@89.22.229.123
3ChS4g7C1tl4

Проверить доступное место на сервере:
df -h

python3 manage.py shell
Если потерялась: 
cd /opt/CoinCounter
ls /opt

cd /opt
ls -la

Где питон: Get-Command python

Если добавить что-то в .env
nano /opt/CoinCounter/.env

Виртуальное окружение у нас на виндовс, а на сервере на линукс - удаляем старое и делаем новое
cd /opt
rm -rf venv  # Удалим старое 
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

Обновить requirements - осторожно! Только после установки 
pip freeze > requirements.txt


sudo apt update
sudo apt install python3.12-venv -y


Запуск воркера и beat
celery -A coin_counter worker --loglevel=info
celery -A coin_counter beat --loglevel=info


Зарегистрируй задачу через админку
Перейди в админку /admin/.

Найди раздел Periodic tasks.

Создай новый периодический таск:

Name: fetch bank

Task: coin_desk.tasks.fetch_and_save_statements_task

Frequency: через Crontab (*/5 * * * * — каждые 5 минут).


Перегрузить файл на сервер
scp .\coin_desk\scripts\bank_fetch.py root@89.22.229.123:/opt/CoinCounter/coin_desk/scripts/
scp coin_desk/tasks.py root@89.22.229.123:/opt/CoinCounter/coin_desk/tasks.py

scp coin_desk/telegram_bot/utils.py root@89.22.229.123:/opt/CoinCounter/coin_desk/telegram_bot/utils.py

scp coin_desk/views.py root@89.22.229.123:/opt/CoinCounter/coin_desk/views.py

scp coin_counter/settings.py root@89.22.229.123:/opt/CoinCounter/coin_counter/settings.py

scp .env root@89.22.229.123:/opt/CoinCounter/.env

scp run.sh root@89.22.229.123:/opt/CoinCounter/run.sh

scp README.md root@89.22.229.123:/opt/CoinCounter

scp coin_desk/models.py root@89.22.229.123:/opt/CoinCounter/coin_desk/models.py

scp coin_desk/admin.py root@89.22.229.123:/opt/CoinCounter/coin_desk/admin.py

scp coin_desk/management/commands/run_telegram_bot.py root@89.22.229.123:/opt/CoinCounter/coin_desk/management/commands/run_telegram_bot.py

scp coin_desk/management/commands/notify_about_new_transactions.py root@89.22.229.123:/opt/CoinCounter/coin_desk/management/commands

scp coin_desk/scripts/bank_fetch.py root@89.22.229.123:/opt/CoinCounter/coin_desk/scripts/bank_fetch.py

scp coin_desk/admin.py root@89.22.229.123:/opt/CoinCounter/coin_desk/admin.py

scp coin_desk/templatetags/__init__.py root@89.22.229.123:/opt/CoinCounter/coin_desk/templatetags

scp coin_desk/templatetags/dashboard_filters.py root@89.22.229.123:/opt/CoinCounter/coin_desk/templatetags/dashboard_filters.py

scp coin_desk/telegram_bot/utils.py root@89.22.229.123:/opt/CoinCounter/coin_desk/telegram_bot/utils.py

scp coin_counter/urls.py root@89.22.229.123:/opt/CoinCounter/coin_counter/urls.py

scp config/coincounter-sheets-credentials.json root@89.22.229.123:/opt/CoinCounter/config

scp coin_desk/management/commands/notify_about_new_transactions.py root@89.22.229.123:/opt/CoinCounter/coin_desk/management/commands/notify_about_new_transactions.py

scp dashboard/templates/dashboard/dashboard.html root@89.22.229.123:/opt/CoinCounter/dashboard/templates/dashboard/dashboard.html

scp dashboard/dashboard_transactions.py root@89.22.229.123:/opt/CoinCounter/dashboard/dashboard_transactions.py

scp dashboard/views.py root@89.22.229.123:/opt/CoinCounter/dashboard/views.py

scp dashboard/signals.py root@89.22.229.123:/opt/CoinCounter/dashboard/signals.py

scp coin_desk/tasks.py root@89.22.229.123:/opt/CoinCounter/coin_desk/tasks.py

scp coin_desk/telegram_bot/bot.py root@89.22.229.123:/opt/CoinCounter/coin_desk/telegram_bot/bot.py

Удалить БД:

rm db.sqlite3
python manage.py makemigrations
python manage.py migrate


