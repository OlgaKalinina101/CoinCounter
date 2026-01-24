#!/bin/bash

SESSION="coin"

# Удалить сессию, если она уже есть
tmux has-session -t $SESSION 2>/dev/null
if [ $? -eq 0 ]; then
    echo "Killing existing session..."
    tmux kill-session -t $SESSION
fi

# Создать новую сессию и окно для Django
tmux new-session -d -s $SESSION -n django
tmux send-keys -t $SESSION:0 'source venv/bin/activate && python manage.py runserver 0.0.0.0:8001' C-m

# Окно 2: Celery worker
tmux new-window -t $SESSION -n celery
tmux send-keys -t $SESSION:1 'source venv/bin/activate && celery -A coin_counter worker --loglevel=info' C-m

# Окно 3: Celery beat
tmux new-window -t $SESSION -n beat
tmux send-keys -t $SESSION:2 'source venv/bin/activate && celery -A coin_counter beat --loglevel=info' C-m

# Окно 4: Telegram бот
tmux new-window -t $SESSION -n bot
tmux send-keys -t $SESSION:3 'source venv/bin/activate && python manage.py run_telegram_bot' C-m

echo "All services started in tmux session '$SESSION'"

