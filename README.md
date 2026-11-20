# Usar este repositorio con GitHub y Visual Studio Code

Esta guía explica cómo conectar este repositorio con GitHub desde Visual Studio Code (VS Code), descargar cambios, subir tu trabajo y compilar un proyecto.

> **Git y VS Code tienen funciones distintas:** Git guarda el historial y sincroniza los cambios; VS Code es el editor donde abres y modificas los archivos. Para compilar también necesitas las herramientas del lenguaje del proyecto.

## 1. Instalar Git y VS Code

1. Instala [Git](https://git-scm.com/downloads).
2. Instala [Visual Studio Code](https://code.visualstudio.com/).
3. Abre una terminal y comprueba que Git esté instalado:

   ```bash
   git --version
   ```

   Deberías ver una versión, por ejemplo `git version 2.x.x`.

## 2. Conectar VS Code con GitHub y clonar el repositorio

1. Abre la página del repositorio en GitHub: [Aron-117/estidistica2](https://github.com/Aron-117/estidistica2).
2. Pulsa **Code** y copia la dirección HTTPS. Para este repositorio es:

   ```text
   https://github.com/Aron-117/estidistica2.git
   ```

3. Abre VS Code y pulsa **Ctrl + Mayús + P** para abrir la paleta de comandos.
4. Escribe y selecciona **Git: Clone**.
5. Pega la dirección copiada, selecciona una carpeta en tu computadora y pulsa **Open** cuando termine.
6. Si VS Code te pide iniciar sesión en GitHub, sigue las instrucciones del navegador. Para clonar un repositorio privado necesitas tener acceso a él.

También puedes clonar desde la terminal:

```bash
git clone https://github.com/Aron-117/estidistica2.git
cd estidistica2
code .
```

El comando `code .` abre la carpeta actual en VS Code. Si no se reconoce, abre la carpeta con **File > Open Folder**.

## 3. Descargar los cambios más recientes

Antes de empezar a trabajar, abre la terminal integrada con **Terminal > New Terminal** y ejecuta:

```bash
git pull
```

`git pull` descarga e integra cambios de GitHub. No sube los cambios de tu computadora.

## 4. Crear una rama de trabajo

Una rama te permite trabajar en cambios separados. Por ejemplo:

```bash
git switch -c mi-nueva-rama
```

Para ver las ramas:

```bash
git branch
```

La rama actual aparece con `*`. Para regresar a `main`:

```bash
git switch main
```

## 5. Guardar y subir cambios a GitHub

Después de editar archivos:

1. En VS Code, abre **Source Control** desde el icono de ramas en la barra lateral, o usa **Ctrl + Mayús + G**.
2. Revisa los archivos modificados y pulsa **+** junto a cada uno para prepararlos. También puedes preparar todos los archivos con el **+** de la sección **Changes**.
3. Escribe un mensaje que describa el cambio, por ejemplo `Agregar instrucciones al README`, y pulsa **Commit**.
4. Pulsa **Sync Changes** o abre la terminal y ejecuta:

   ```bash
   git push -u origin mi-nueva-rama
   ```

   Sustituye `mi-nueva-rama` por el nombre real de tu rama. Para subir cambios a `main`, cámbiate primero a `main` y usa `git push`.

También puedes realizar los pasos de preparación y confirmación desde la terminal:

```bash
git add README.md
git commit -m "Agregar instrucciones al README"
git push
```

Si es la primera vez que subes una rama, establece su conexión con GitHub con:

```bash
git push -u origin mi-nueva-rama
```

> **Importante:** `git push` solo sube confirmaciones (*commits*). Los cambios sin confirmar no se envían a GitHub.

## 6. Compilar o ejecutar el proyecto

El comando depende del lenguaje y de los archivos del proyecto. Abre **Terminal > New Terminal** en VS Code y usa el comando indicado por el proyecto. Ejemplos:

### Python

Si el proyecto tiene un archivo `main.py`, puedes ejecutarlo así:

```bash
python main.py
```

En Windows también puede funcionar `py main.py`. Python normalmente ejecuta el programa directamente; no usa un paso de compilación como C++ o C#.

### Node.js

Si el proyecto incluye un archivo `package.json`, instala sus dependencias y revisa sus scripts:

```bash
npm install
npm run
```

Si aparece un script `build`, ejecútalo con:

```bash
npm run build
```

### .NET

Desde la carpeta que contiene el archivo `.csproj` o `.sln`, ejecuta:

```bash
dotnet build
```

Para ejecutar un proyecto .NET, usa:

```bash
dotnet run
```

En VS Code, **Ctrl + Mayús + B** permite ejecutar una tarea de compilación si el proyecto ya tiene una configurada.

## Ejecutar los programas Python

Este repositorio contiene dos programas:

- `pg1.py`: aplicación de planificación de estudio; ejecútala con `python pg1.py` y abre `http://127.0.0.1:8000`.
- `est2.py`: procesamiento de una base SPSS. Instala sus dependencias y coloca `EH2025_Persona.sav` junto a `est2.py`:

  ```powershell
  python -m pip install pandas numpy pyreadstat
  python est2.py
  ```

  Si la base está en otra ubicación, indícala con `python est2.py --sav "C:\ruta\EH2025_Persona.sav"`. Los archivos CSV y el informe se guardan junto al script por defecto; puedes elegir otra carpeta con `--output-dir`.

El archivo de datos `.sav` no se incluye en el repositorio. Sin él, `est2.py` muestra un mensaje indicando dónde buscarlo y cómo especificar su ruta.
