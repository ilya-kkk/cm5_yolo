# Настройка системы для YOLO Camera Stream с Hailo 8L

## 🖥️ Системные требования

### Аппаратное обеспечение
- **Raspberry Pi CM5** с модулем Hailo 8L
- **CSI камера** (совместимая с libcamera)
- **Минимум 4GB RAM**
- **Минимум 16GB SD карта** (рекомендуется 32GB+)
- **Сетевое подключение** для стриминга

### Программное обеспечение
- **Ubuntu 22.04** или совместимая ОС
- **Docker** версии 20.10+
- **Docker Compose** версии 2.0+
- **Python 3.8+**

## 🔧 Установка системы

### 1. Обновление системы
```bash
sudo apt update && sudo apt upgrade -y
sudo apt autoremove -y
```

### 2. Установка Docker
```bash
# Удаление старых версий Docker
sudo apt remove docker docker-engine docker.io containerd runc

# Установка зависимостей
sudo apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Добавление GPG ключа Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Добавление репозитория Docker
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Установка Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER

# Запуск Docker
sudo systemctl start docker
sudo systemctl enable docker

# Перезагрузка для применения изменений группы
sudo reboot
```

### 3. Установка Docker Compose
```bash
# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Проверка установки
docker-compose --version
```

### 4. Установка системных зависимостей
```bash
sudo apt install -y \
    python3 \
    python3-pip \
    python3-opencv \
    libcamera-tools \
    libcamera-apps \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    libcamera-dev \
    v4l-utils
```

## 📷 Настройка камеры

### 1. Проверка подключения CSI камеры
```bash
# Проверка устройств камеры
ls -la /dev/video*

# Проверка libcamera
libcamera-hello --list-cameras
```

### 2. Тестирование камеры
```bash
# Простой тест камеры
libcamera-still -o test.jpg

# Тест видео
libcamera-vid -t 5000 -o test.h264
```

### 3. Настройка разрешений
```bash
# Добавление пользователя в группу video
sudo usermod -aG video $USER

# Создание udev правила для камеры
echo 'SUBSYSTEM=="video4linux", GROUP="video", MODE="0666"' | sudo tee /etc/udev/rules.d/99-camera.rules

# Перезагрузка udev
sudo udevadm control --reload-rules
sudo udevadm trigger
```

## 🚀 Настройка Hailo 8L

### 1. Проверка подключения Hailo
```bash
# Проверка устройств Hailo
ls -la /dev/hailo*

# Проверка драйверов
dmesg | grep hailo
```

### 2. Установка Hailo Platform
```bash
# Установка Python SDK
pip3 install hailo-platform

# Проверка установки
python3 -c "import hailo_platform; print('Hailo Platform installed successfully')"
```

### 3. Тестирование Hailo
```bash
# Запуск теста Hailo
python3 test_hailo.py
```

## 🌐 Настройка сети

### 1. Статический IP (опционально)
```bash
# Редактирование сетевой конфигурации
sudo nano /etc/netplan/01-netcfg.yaml

# Пример конфигурации:
# network:
#   version: 2
#   renderer: networkd
#   ethernets:
#     eth0:
#       dhcp4: no
#       addresses:
#         - 192.168.0.100/24
#       gateway4: 192.168.0.1
#       nameservers:
#         addresses: [8.8.8.8, 8.8.4.4]

# Применение конфигурации
sudo netplan apply
```

### 2. Настройка файрвола
```bash
# Разрешение UDP порта 5000
sudo ufw allow 5000/udp

# Включение файрвола
sudo ufw enable
```

### 3. Проверка сетевого подключения
```bash
# Проверка доступности целевого IP
ping -c 4 192.168.0.173

# Проверка порта
nc -zu 192.168.0.173 5000
```

## 🔧 Настройка проекта

### 1. Клонирование проекта
```bash
git clone <repository-url>
cd hailo_compiler
```

### 2. Проверка файлов
```bash
# Проверка наличия HEF файла
ls -la *.hef

# Проверка Docker файлов
ls -la Dockerfile docker-compose.yml
```

### 3. Настройка прав доступа
```bash
# Сделать скрипты исполняемыми
chmod +x *.sh *.py

# Проверка прав
ls -la *.sh *.py
```

## 🧪 Тестирование компонентов

### 1. Тест камеры
```bash
python3 test_camera.py
```

### 2. Тест Hailo
```bash
python3 test_hailo.py
```

### 3. Тест Docker
```bash
# Проверка Docker
docker --version
docker-compose --version

# Тест Docker образа
docker run hello-world
```

## 🚀 Запуск системы

### 1. Первый запуск
```bash
# Полный запуск с проверками
./start_yolo_stream.sh
```

### 2. Быстрый запуск
```bash
# Быстрый запуск без проверок
./quick_start.sh
```

### 3. Ручной запуск
```bash
# Сборка образа
docker-compose build

# Запуск сервиса
docker-compose up
```

## 📊 Мониторинг и отладка

### 1. Просмотр логов
```bash
# Логи в реальном времени
docker-compose logs -f yolo-camera-stream

# Последние логи
docker-compose logs --tail=100 yolo-camera-stream
```

### 2. Мониторинг ресурсов
```bash
# Использование CPU и памяти
htop

# Использование диска
df -h

# Температура системы
vcgencmd measure_temp
```

### 3. Проверка сетевого трафика
```bash
# Мониторинг сетевого трафика
iftop -i eth0

# Проверка UDP портов
netstat -tulpn | grep :5000
```

## 🔍 Устранение неполадок

### Проблемы с камерой
```bash
# Проверка устройств
ls -la /dev/video*

# Проверка libcamera
libcamera-hello --list-cameras

# Проверка прав доступа
groups $USER
```

### Проблемы с Hailo
```bash
# Проверка устройств Hailo
ls -la /dev/hailo*

# Проверка драйверов
dmesg | grep hailo

# Проверка Python SDK
python3 -c "import hailo_platform"
```

### Проблемы с Docker
```bash
# Проверка статуса Docker
sudo systemctl status docker

# Перезапуск Docker
sudo systemctl restart docker

# Очистка Docker
docker system prune -a
```

### Проблемы с сетью
```bash
# Проверка сетевых интерфейсов
ip addr show

# Проверка маршрутизации
ip route show

# Тест подключения
ping -c 4 192.168.0.173
```

## 📚 Дополнительные ресурсы

- [Hailo Platform Documentation](https://docs.hailo.ai/)
- [libcamera Documentation](https://libcamera.org/)
- [Docker Documentation](https://docs.docker.com/)
- [Raspberry Pi Documentation](https://www.raspberrypi.org/documentation/)
- [Ubuntu Documentation](https://ubuntu.com/tutorials)

## 🆘 Получение помощи

При возникновении проблем:

1. **Проверьте логи** системы и Docker
2. **Запустите тесты** компонентов
3. **Проверьте документацию** Hailo
4. **Создайте issue** в репозитории проекта
5. **Обратитесь в поддержку** Hailo

## 📝 Чек-лист настройки

- [ ] Система обновлена
- [ ] Docker установлен и работает
- [ ] Docker Compose установлен
- [ ] CSI камера подключена и работает
- [ ] Hailo 8L подключен и определяется
- [ ] Сетевое подключение настроено
- [ ] Файрвол настроен
- [ ] Проект склонирован
- [ ] HEF файл загружен
- [ ] Тесты компонентов пройдены
- [ ] Система готова к запуску 