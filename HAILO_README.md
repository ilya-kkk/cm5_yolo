# Hailo YOLO для Raspberry Pi CM5

Этот проект обеспечивает запуск YOLO модели на Hailo-8L ускорителе для Raspberry Pi Compute Module 5.

## 🚀 Быстрый старт

### 1. Проверка Hailo
Сначала проверьте, что Hailo-8L ускоритель доступен:

```bash
# Запуск теста Hailo
docker compose run hailo-test
```

### 2. Запуск Hailo YOLO процессора
```bash
# Запуск в фоновом режиме
docker compose up -d yolo-camera-stream

# Или в интерактивном режиме
docker compose up yolo-camera-stream
```

### 3. Запуск камеры
```bash
# Сделать скрипт исполняемым
chmod +x start_hailo_camera.sh

# Запустить камеру
./start_hailo_camera.sh
```

## 📁 Структура проекта

- `hailo_yolo_main.py` - Основной файл для запуска YOLO на Hailo
- `test_hailo_basic.py` - Тест базовой функциональности Hailo
- `start_hailo_camera.sh` - Скрипт запуска камеры
- `yolov8n.hef` - Hailo модель YOLOv8n
- `docker-compose.yml` - Конфигурация Docker сервисов

## 🔧 Требования

- Raspberry Pi CM5 с Hailo-8L ускорителем
- OV5647 камера на MIPI0 интерфейсе
- Docker и Docker Compose
- Hailo Platform 4.15+ установлен в системе

## 📊 Мониторинг

### Проверка статуса
```bash
# Статус сервисов
docker compose ps

# Логи Hailo YOLO
docker compose logs yolo-camera-stream

# Проверка обработанных кадров
ls -la /tmp/yolo_frames/
```

### Веб-интерфейс
Веб-сервис доступен на порту 8080:
```bash
# Запуск веб-сервиса
docker compose up -d web-stream-service

# Открыть в браузере
http://localhost:8080
```

## 🐛 Устранение неполадок

### Hailo не инициализируется
1. Проверьте, что Hailo Platform установлен:
   ```bash
   python3 -c "import hailo_platform; print('OK')"
   ```

2. Проверьте PCI устройство:
   ```bash
   lspci | grep -i hailo
   ```

3. Проверьте загруженные модули:
   ```bash
   lsmod | grep -i hailo
   ```

### Камера не работает
1. Проверьте доступность камеры:
   ```bash
   v4l2-ctl --list-devices
   ```

2. Проверьте права доступа:
   ```bash
   sudo usermod -a -G video $USER
   ```

3. Перезагрузите систему для применения изменений

### Низкая производительность
1. Убедитесь, что PCIe Gen3 включен в `/boot/firmware/config.txt`:
   ```
   dtparam=pciex1_gen=3
   ```

2. Проверьте температуру Hailo:
   ```bash
   cat /sys/class/thermal/thermal_zone*/temp
   ```

## 📈 Производительность

Ожидаемая производительность на Hailo-8L:
- **FPS**: 30-60 FPS (зависит от модели)
- **Задержка**: <50ms
- **Точность**: COCO mAP 0.5:0.95

## 🔄 Обновление модели

Для использования другой YOLO модели:

1. Конвертируйте модель в HEF формат с помощью Hailo Model Zoo
2. Замените `yolov8n.hef` на новую модель
3. Обновите параметры в `hailo_yolo_main.py`:
   - `input_shape`
   - `postprocess_detections()`

## 📝 Логирование

Логи сохраняются в:
- Docker контейнер: `docker compose logs yolo-camera-stream`
- Обработанные кадры: `/tmp/yolo_frames/`
- Системные логи: `journalctl -u docker`

## 🆘 Поддержка

При возникновении проблем:

1. Запустите тест: `docker compose run hailo-test`
2. Проверьте логи: `docker compose logs yolo-camera-stream`
3. Убедитесь, что все зависимости установлены
4. Проверьте права доступа к устройствам

## 📚 Дополнительные ресурсы

- [Hailo Platform Documentation](https://docs.hailo.ai/)
- [Hailo Model Zoo](https://github.com/hailo-ai/hailo_model_zoo)
- [Raspberry Pi CM5 Documentation](https://www.raspberrypi.com/documentation/computers/compute-module-5.html) 