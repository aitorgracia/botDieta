# Bot de Dieta — Telegram

Bot de Telegram personal y privado para el seguimiento diario de peso, cálculo automatizado de medias semanales y generación de collages fotográficos de progreso físico. Diseñado para ejecutarse de forma continua en un VPS bajo la zona horaria de Madrid.

## Estructura del Proyecto

botDieta/├── main.py          # Punto de entrada, configuración del logger rotativo y JobQueue├── handlers.py      # Controladores de comandos, mensajes de texto y procesamiento de fotos├── db.py            # Capa de persistencia (SQLite) con auto-cierre de semanas pendientes├── collage.py       # Procesamiento de imágenes y renderizado del collage con Pillow├── requirements.txt # Dependencias del entorno virtual (pytz, pillow, etc.)├── .env             # Variables de entorno privadas (NO subir a Git)└── .env.example     # Plantilla pública de configuración
## Características Principales

* **Cierre Semanal Automatizado:** Al registrar el peso el domingo, el bot detecta el cierre de la semana ISO, calcula la media y bloquea el estado a la espera de las fotos de progreso.
* **Auto-rellenado Histórico:** Si olvidas pesarte durante semanas enteras, la capa de datos detecta el hueco al volver a usar el bot y archiva las semanas pasadas de forma limpia con `0.0 kg` para no romper las métricas temporales.
* **Logger Inteligente:** El archivo `bot.log` rota automáticamente cada noche a las 00:00 y mantiene únicamente un histórico de 7 días para evitar saturar el almacenamiento del VPS.
* **Fugas de Memoria Blindadas:** El envío de copias de seguridad de la base de datos y collages visuales utiliza contextos seguros (`with open`) que cierran los descriptores de archivo del sistema operativo inmediatamente tras el envío.

## Instalación y Configuración

1. Clone el repositorio en su máquina local o VPS.
2. Cree y active su entorno virtual de Python:
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Linux/macOS
Instale las dependencias requeridas:Bashpip install -r requirements.txt
Configure sus variables de entorno:Bashcp .env.example .env
Edite el archivo .env introduciendo su token de Telegram y su ID de usuario de destino:Fragmento de códigoBOT_TOKEN="tu_token_de_telegram_aqui"
ALLOWED_USER_ID="tu_id_numerico_aqui"
💡 ¿Cómo obtener tu ALLOWED_USER_ID?Escríbele al bot oficial @userinfobot en Telegram y te responderá inmediatamente con tu ID numérico personal.Comandos DisponiblesEntrada / ComandoTipoDescripción96.2 (Cualquier número)MensajeRegistra el peso del día en la semana actual./semanaComandoMuestra la lista de pesos de la semana en curso y la media provisional./borrarComandoElimina de la base de datos el último peso introducido (útil para correcciones)./historicoComandoMuestra las medias de las últimas 12 semanas (incluyendo huecos vacíos)./backupComandoEnvía el archivo físico dieta.db actual a través del chat de forma segura./resetfotosComandoVacía el contenedor temporal de fotos en el VPS si se desea reiniciar el envío./helpComandoMuestra la guía rápida de comandos de la aplicación.Flujo de Trabajo SemanalDe Lunes a Sábado: Envía tu peso diario escribiendo simplemente el número en el chat (ej. 95.4). El bot te devolverá la media provisional de lo que va de semana.El Domingo (Cierre Automático):Al enviar tu peso, el bot detectará que es domingo, calculará la media final de la semana, archivará el registro en la tabla historico y abrirá la cola de imágenes.Envía 3 fotos seguidas (frente, perfil y espalda). El bot procesará las fotos en disco, escalándolas a un lienzo simétrico de 400x600 píxeles cada una.Al recibir la tercera foto, el bot genera el collage visual, incrusta la media de peso calculada de forma centrada en la banda inferior y te envía el edit final de vuelta, eliminando de forma inmediata los residuos fotográficos locales del VPS.Despliegue en Producción (VPS via systemd)Para garantizar que el bot se ejecute de forma ininterrumpida en segundo plano en tu servidor Linux y se reinicie automáticamente si el proceso se cae, se recomienda crear un servicio de systemd.Crea el archivo de configuración del servicio:Bashsudo nano /etc/systemd/system/botdieta.service
Pega el siguiente contenido adaptando las rutas locales a tu directorio de usuario:Ini, TOML[Unit]
Description=Bot de Telegram - Seguimiento de Dieta y Peso
After=network.target

[Service]
Type=simple
User=Aitor
WorkingDirectory=/home/Aitor/Projects/botDieta
ExecStart=/home/Aitor/Projects/botDieta/venv/bin/python main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
Recarga el demonio de sistema, activa el servicio para que arranque con el sistema y ejecútalo:Bashsudo systemctl daemon-reload
sudo systemctl enable botdieta.service
sudo systemctl start botdieta.service
Para auditar el comportamiento del bot en tiempo real:Bashsudo systemctl status botdieta.service
# O bien revisa el archivo de logs diario rotativo:
tail -f bot.log