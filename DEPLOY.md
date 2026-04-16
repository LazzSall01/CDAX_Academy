# Guía de Despliegue - CDAX Academy

## Requisitos Previos

- Servidor VPS con Ubuntu 24.04
- Python 3.12
- Git
- Acceso SSH (root)

---

## 一、Configuración Inicial del Servidor

### 1. Conectar al VPS

```bash
ssh root@68.183.125.114
```

### 2. Instalar dependencias

```bash
apt update
apt install python3-pip git python3-venv
```

### 3. Instalar pipx y uv

```bash
apt install pipx
pipx install uv
pipx install uvicorn
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

### 4. Crear directorio del proyecto

```bash
mkdir -p /var/www
cd /var/www
git clone https://github.com/LazzSall01/CDAX_Academy.git
cd CDAX_Academy
```

### 5. Configurar variables de entorno

```bash
cp .env.production .env
# Editar .env y agregar SECRET_KEY generada:
python3 -c "import secrets; print(secrets.token_hex(32))"
# Copiar el resultado en SECRET_KEY=...
nano .env
```

### 6. Crear entorno virtual e instalar

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install uv
uv sync
```

---

## 二、Desactivar Nginx (opcional)

Si nginx está bloqueando el puerto 80:

```bash
systemctl stop nginx
systemctl disable nginx
```

---

## 三、Desplegar la Aplicación

### Método 1: Ejecución directa (recomendado)

```bash
cd /var/www/CDAX_Academy
source .venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 80 > app.log 2>&1 &
```

### Método 2: Con path completo

```bash
cd /var/www/CDAX_Academy
nohup /var/www/CDAX_Academy/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 80 > app.log 2>&1 &
```

### Verificar que está corriendo

```bash
curl http://localhost:80
ps aux | grep uvicorn
```

---

## 四、Actualizar la Aplicación

### 1. Actualizar código desde GitHub

```bash
cd /var/www/CDAX_Academy
git pull
```

### 2. Actualizar la base de datos

```bash
# Opción A: Copiar desde PC local
# En tu PC:
scp D:\00-PY\school\dental_academia.db root@68.183.125.114:/var/www/CDAX_Academy/

# Opción B: Si está en GitHub
git pull
```

### 3. Reiniciar la aplicación

```bash
pkill -f uvicorn
sleep 1
cd /var/www/CDAX_Academy
nohup /var/www/CDAX_Academy/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 80 > app.log 2>&1 &
```

### 4. Verificar

```bash
curl http://localhost:80
tail -20 app.log
```

---

## 五、Comandos Útiles

### Ver logs en tiempo real

```bash
tail -f /var/www/CDAX_Academy/app.log
```

### Ver procesos corriendo

```bash
ps aux | grep uvicorn
```

### Ver puertos en uso

```bash
ss -tlnp | grep :80
```

### Matar la aplicación

```bash
pkill -f uvicorn
```

### Reiniciar completamente

```bash
pkill -f uvicorn
cd /var/www/CDAX_Academy
git pull
nohup /var/www/CDAX_Academy/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 80 > app.log 2>&1 &
```

---

## 六、Estructura de Archivos

```
/var/www/CDAX_Academy/
├── app/                    # Código de la aplicación
│   ├── api/               # Endpoints de API
│   ├── gui/               # Plantillas y rutas web
│   ├── servicios/         # Lógica de negocio
│   ├── config.py          # Configuración
│   └── main.py           # Punto de entrada
├── docker/                # Dockerfiles
├── dep/                  # Scripts de debug
├── dental_academia.db     # Base de datos SQLite
├── pyproject.toml       # Dependencias
├── .env              # Variables de entorno
└── app.log            # Logs de la app
```

---

## 七、Configuración de Dominio

El dominio cdaxacademy.net debe apuntar a:

- ** IP**: 68.183.125.114
- ** Puerto**: 80

---

## 八、Producción vs Desarrollo

| Variable | Desarrollo | Producción |
|----------|-----------|------------|
| MODO_DESARROLLO | true | false |
| Puerto | 8000 | 80 |
| SECRET_KEY | dev-key | clave-segura-generada |
| CORS | localhost:* | cdaxacademy.net |

---

## 九、Solución de Problemas

### "Address already in use"

```bash
pkill -f uvicorn
ss -tlnp | grep :80
```

### "No module named 'fastapi'"

```bash
source .venv/bin/activate
uv sync
```

### "uv: command not found"

```bash
export PATH="$HOME/.local/bin:$PATH"
# O usar path completo:
/var/www/CDAX_Academy/.venv/bin/uvicorn
```

---

## 十, Acceso

- **Producción**: http://cdaxacademy.net
- **Admin**: http://cdaxacademy.net/admin
- **Login**: http://cdaxacademy.net/login

### Credenciales por defecto

- **Email**: admin@cdaxacademy.com
- **Password**: La que configuraste al crear el usuario admin

---

Actualizado: Abril 2026