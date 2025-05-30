# Outlook Account Checker

![GitHub](https://img.shields.io/github/license/theazot/outlook-checker)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)

Мощный инструмент для проверки валидности аккаунтов Outlook/Hotmail.

## 📋 Описание

Outlook Account Checker - это скрипт для автоматизированной проверки большого количества аккаунтов Outlook/Hotmail (Microsoft) на валидность. Программа поддерживает работу через прокси, сохраняет cookies для валидных аккаунтов и включает дополнительную проверку доступа к почтовому ящику.

### 🔑 Возможности

- Проверка валидности логина и пароля для Outlook/Hotmail/Microsoft аккаунтов
- Поддержка HTTP, SOCKS4, SOCKS5 прокси
- Автоматическая проверка и фильтрация рабочих прокси
- Сохранение cookies валидных аккаунтов
- Расширенное логирование процесса проверки
- Опциональная проверка доступа к почтовому ящику
- Случайные User-Agent и Accept-Language заголовки для имитации реального браузера

## 🚀 Начало работы

### Предварительные требования

- Python 3.9 или выше
- Установленные зависимости (см. раздел установки)
- Файл с аккаунтами в формате `логин:пароль`
- Опционально: файл с прокси

### ⚙️ Установка

1. Клонируйте репозиторий

```bash
git clone https://github.com/yourusername/outlook-checker.git
cd outlook-checker
```

2. Установите необходимые зависимости

```bash
pip install -r requirmentes.txt
```


3. Создайте файлы с аккаунтами и прокси

Создайте файл `acc.txt` с аккаунтами в формате:
```
email1@outlook.com:password1
email2@hotmail.com:password2
```

Опционально создайте файл `proxies.txt` с прокси в формате:
```
ip:port
username:password@ip:port
```

### 🔧 Настройка

Откройте файл `outlook_checker.py` и настройте следующие параметры в начале файла:

```python
ACCOUNTS_FILE = "acc.txt"     # Файл с аккаунтами в формате логин:пароль
VALID_DIR = "valid"           # Директория для сохранения валидных аккаунтов
INVALID_FILE = "invalid.txt"  # Файл для невалидных аккаунтов
PROXIES_FILE = "proxies.txt"  # Файл с прокси в формате ip:port или user:pass@ip:port
USE_PROXIES = False           # Использовать ли прокси
PROXY_FORMAT = "http"         # Формат прокси (http, socks4, socks5)
CHECK_MAIL = False            # Проверять ли доступ к почтовому ящику (для подтверждения валидности)
```

### 🎮 Использование

Запустите скрипт командой:

```bash
python outlook_checker.py
```

## 📝 Структура проекта

- `outlook_checker.py` - основной скрипт
- `acc.txt` - файл со списком аккаунтов для проверки
- `proxies.txt` - файл со списком прокси (опционально)
- `valid/` - директория, куда сохраняются данные валидных аккаунтов
- `invalid.txt` - файл, куда записываются невалидные аккаунты
- `outlook_checker.log` - файл с подробными логами работы программы
- `working_proxies.txt` - файл с рабочими прокси (создается автоматически)

## 📊 Результаты работы

После выполнения скрипт выведет статистику проверки:
- Общее количество проверенных аккаунтов
- Количество и процент валидных аккаунтов
- Количество невалидных аккаунтов
- Время выполнения

Валидные аккаунты сохраняются в директории `valid/`, структурированные по имени пользователя, с файлами cookies для дальнейшего использования.

## 🔍 Как это работает

1. Скрипт загружает список аккаунтов и, если включено, прокси
2. Для каждого аккаунта:
   - Создает сессию с случайным User-Agent и Accept-Language
   - Выполняет процесс авторизации на Microsoft
   - Проверяет наличие аутентификационных cookies
   - Опционально проверяет доступ к почтовому ящику
   - Сохраняет результаты в соответствующие файлы


## 🛡 Требования

- Python 3.9+
- requests
- Дополнительно для SOCKS прокси: `pip install requests[socks]`

## 📄 Лицензия

Распространяется под лицензией MIT. См. файл `LICENSE` для получения дополнительной информации.

## 🤝 Вклад в проект

Вклады приветствуются! Пожалуйста, создавайте issue или pull request для любых предложений или исправлений.

## 📧 Контакты

- GitHub: [github.com/theazot](https://github.com/theazot)
- Telegram: @theazot

