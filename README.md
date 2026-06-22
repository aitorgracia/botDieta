# Bot de Dieta — Telegram

Bot personal para seguimiento de peso semanal con collage fotográfico dominical.

## Estructura

```
botDieta/
├── main.py          # Arranque y registro de handlers
├── handlers.py      # Lógica de cada comando y mensaje
├── db.py            # Capa de base de datos (SQLite)
├── collage.py       # Generación del collage con Pillow
├── requirements.txt
├── .env             # Variables privadas (NO subir a git)
└── .env.example     # Plantilla pública
```

## Instalación

```bash
pip install -r requirements.txt
cp .env.example .env
# Edita .env con tu token y tu user_id
python main.py
```

## Cómo obtener tu ALLOWED_USER_ID

Escríbele a [@userinfobot](https://t.me/userinfobot) en Telegram — te responde con tu ID numérico.

## Comandos disponibles

| Comando | Descripción |
|---|---|
| `96.2` (número) | Guarda el peso del día |
| `/semana` | Ver todos los pesos de la semana actual |
| `/borrar` | Elimina el último peso (si te equivocaste) |
| `/domingo` | Cierre semanal — genera collage y guarda en histórico |
| `/historico` | Medias de las últimas 12 semanas |
| `/backup` | Recibe la base de datos como archivo |
| `/resetfotos` | Limpia fotos temporales si necesitas reenviarlas |

## Flujo semanal

1. **Lunes a domingo**: envía tu peso cada día (ej: `96.2`)
2. **El domingo**: manda 3 fotos seguidas (frente, perfil, espalda)
3. **Ejecuta `/domingo`**: genera el collage y archiva la semana

## Fuente personalizada

Si quieres una fuente propia en el collage, coloca un archivo `font.ttf` en la raíz del proyecto.

## Notas VPS

Para mantener el bot corriendo en segundo plano:
```bash
nohup python main.py &> /dev/null &
```
O mejor, crea un servicio systemd.
