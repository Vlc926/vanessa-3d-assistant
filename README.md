# 🎀 Vanessa - Tu Asistente Maid Personal & IA Generativa

**Vanessa** es una asistente virtual y maid personal con estética anime, reconocimiento biométrico de voz y rostro, percepción de pantalla en tiempo real (revisa tu código, documentos y videos), reconocimiento de objetos mediante base de datos, generación de artefactos (Excel, Word, bases de datos y código), control total del sistema Linux (luces de teclado, Wi-Fi, Bluetooth y apagado del equipo), y modo de **ahorro de memoria RAM con desvanecimiento automático**.

---

## ⚡ Novedades y Capacidades Principales

### 1. 📴 Ejecución en Segundo Plano (Sin consola abierta)
Puedes correr a Vanessa en todo momento sin tener una terminal ocupando tu pantalla:

- **Inicio en segundo plano**:
  ```bash
  cd /home/victor/.gemini/antigravity/scratch/jarvis_assistant
  ./start_background.sh
  ```
- **Detener en segundo plano**:
  ```bash
  ./stop_background.sh
  ```
- **O como servicio Systemd de usuario (auto-arranque)**:
  ```bash
  systemctl --user enable vanessa
  systemctl --user start vanessa
  ```
  *(Te enviará una notificación nativa de escritorio indicando que está lista).*

---

### 2. 🎭 Personalidad Maid Adaptativa & Detección de Tono de Voz
- **Identidad**: Devota, leal, amable y cálida como una maid anime (*"Amo Víctor"*).
- **Sensibilidad al tono**:
  - **Tono Casual / Relajado**: Juguetona, cariñosa y con un sutil sarcasmo refinado.
  - **Tono Serio o Firme**: Si Vanessa detecta en tu tono de voz seriedad o urgencia, abandona el sarcasmo y actúa con precisión, eficiencia ejecutiva y respeto profesional inmediato.

---

### 3. 👤 Reconocimiento Facial Biométrico & 🗄️ Detección de Objetos
- **Reconocimiento Facial**: Modelo neural `SFace` integrado.
  - Pídele: *"Vanessa, memoriza mi rostro"* (o usa el botón en el panel).
  - Al sentarte frente a la cámara, Vanessa te identificará como su **Amo Víctor** y sabrá si hay personas desconocidas.
- **Base de Datos de Objetos (NanoDet)**:
  - Detecta objetos en tu mesa (tazas de café, teléfono celular, computadora portátil, libros, botellas).
  - Guarda los avistamientos con fecha y hora en SQLite (`data/assistant_memory.db`).
  - Pregúntale: *"Vanessa, ¿qué objetos ves en mi mesa?"*.

---

### 4. 🖥️ Percepción de Pantalla & Sugerencias (Código, Videos, Documentos)
- Diseñado para Wayland y Hyprland con captura instantánea mediante `grim`.
- Pregúntale por voz o presiona el botón:
  - *"Vanessa, ¿qué opinas de lo que veo en mi pantalla?"*
  - *"Vanessa, revisa mi código y dame sugerencias"*
  - *"Vanessa, ¿qué te parece este documento o video?"*
- Vanessa observará tu pantalla y te ofrecerá observaciones perspicaces y código mejorado.

---

### 5. 💤 Auto-Sleep: Desvanecimiento para Ahorro de Memoria RAM
- Si no interactúas con ella durante 25 segundos, el avatar entra en **Modo Reposo / Dormancy**:
  - Se desvanece suavemente (*fade-out* transparente).
  - Detiene los bucles pesados de animación para liberar ciclos de CPU y consumo de memoria RAM.
- Cuando la llamas diciendo **"Vanessa"** o haces clic en ella, **reaparece suavemente**, hace una reverencia de maid y te atiende: *"¿En qué puedo complacerlo, Amo Víctor?"*.

---

### 6. 📊 Modelo Generativo (Excel, Word, Bases de Datos, Código)
Puedes ordenarle generar archivos directamente en tu carpeta `~/Documentos`:
- **Excel (.xlsx)**:
  - *"Vanessa, genera un excel de presupuesto mensual"*
  - Genera archivos con encabezados estilizados, celdas alternadas y bordes profesionales.
- **Bases de Datos (.db & .sql)**:
  - *"Vanessa, crea una base de datos para usuarios y compras"*
  - Genera el archivo SQLite funcional y el script `.sql`.
- **Documentos Word (.docx)**:
  - *"Vanessa, crea un archivo Word sobre arquitectura de software"*
- **Código Fuente**:
  - *"Vanessa, genera código en Python para automatizar respaldos"*

---

### 7. 💻 Control de Hardware & Apagado del Sistema
- **Apagado de PC**:
  - *"Vanessa, apaga la computadora"* (ejecuta el apagado del sistema de inmediato).
- **Luces de Teclado**:
  - *"Vanessa, enciende/apaga las luces de mi teclado"*
- **Conectividad**:
  - *"Vanessa, activa o desactiva Wi-Fi / Bluetooth"*
- **YouTube & Música**:
  - *"Vanessa, abre YouTube con música"*
  - *"Vanessa, ¿qué canción está sonando?"* (Shazamio)

---

## 🌐 Panel Web Interactivo

Accede desde tu navegador en cualquier momento:
👉 **[http://127.0.0.1:8765](http://127.0.0.1:8765)**
