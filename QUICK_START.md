# 🚀 Быстрый запуск CM5 YOLO проекта

## 📋 Требования
- Raspberry Pi Compute Module 5 (CM5)
- Hailo-8L accelerator
- CSI Camera (OV5647)
- Docker и Docker Compose

## 🎯 Запуск проекта

### 1. Клонирование и настройка
```bash
git clone https://github.com/ilya-kkk/cm5_yolo.git
cd cm5_yolo
```

### 2. Запуск всех сервисов
```bash
docker compose up --build -d
```

### 3. Запуск камеры на хосте (обязательно!)
```bash
# Остановить предыдущие процессы
pkill libcamera-vid

# Запустить стрим камеры
libcamera-vid -t 0 --codec h264 --width 640 --height 480 --framerate 30 --inline -o udp://127.0.0.1:5000 > /dev/null 2>&1 &
```

## 🌐 Доступ к сервисам

- **Веб-интерфейс**: http://localhost:8080
- **UDP поток**: udp://127.0.0.1:5000
- **Мобильный доступ**: http://[IP_CM5]:8080

## 📱 Особенности

- ✅ Простой веб-интерфейс без лишних кнопок
- ✅ Адаптирован для мобильных устройств
- ✅ YOLO обработка на Hailo-8L
- ✅ Автоматический перезапуск контейнеров
- ✅ Один `docker compose up` для запуска

## 🔧 Управление

```bash
# Остановить все сервисы
docker compose down

# Перезапустить
docker compose restart

# Просмотр логов
docker compose logs -f
```

## 📊 Статус сервисов

- **yolo-camera-stream**: Обрабатывает UDP поток с камеры
- **web-stream-service**: Веб-интерфейс для просмотра видео

## 🚨 Важно!

`libcamera-vid` должен быть запущен **на хосте CM5**, а не в Docker контейнере! 